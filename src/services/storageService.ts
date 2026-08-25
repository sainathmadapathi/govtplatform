/**
 * GovOS Dual-Persistence Storage Service
 * Handles instant offline browser localStorage caching + background SQLite synchronization.
 */

export interface CandidateProfile {
  username: string;
  target_post_id: string;
  target_exam_id: string;
  category: string;
  qualification: string;
}

export interface MockAttemptRecord {
  id: string;
  exam_id: string;
  topic_id?: string;
  subject: string;
  score: number;
  total_marks: number;
  correct_count: number;
  incorrect_count: number;
  unattempted_count: number;
  time_taken_seconds: number;
  attempted_at?: string;
}

const STORAGE_KEYS = {
  TARGET_POST: 'govos_target_post_id',
  COMPLETED_MODULES: 'govos_completed_modules',
  MOCK_ATTEMPTS: 'govos_mock_attempts',
  PROFILE: 'govos_candidate_profile',
  BOOKMARKS: 'govos_bookmarked_resources'
};

class StorageService {
  private userId: string = 'default-candidate';

  // --- 1. Target Post Persistence ---
  getTargetPost(): string {
    try {
      const saved = localStorage.getItem(STORAGE_KEYS.TARGET_POST);
      return saved || 'post-aso-css';
    } catch {
      return 'post-aso-css';
    }
  }

  setTargetPost(postId: string): void {
    try {
      localStorage.setItem(STORAGE_KEYS.TARGET_POST, postId);
      this.syncProfileToSQLite({ target_post_id: postId });
    } catch (e) {
      console.warn('LocalStorage error:', e);
    }
  }

  // --- 2. Completed Study Modules Progress ---
  getCompletedModules(): Record<string, boolean> {
    try {
      const raw = localStorage.getItem(STORAGE_KEYS.COMPLETED_MODULES);
      if (raw) {
        return JSON.parse(raw);
      }
    } catch (e) {
      console.warn('LocalStorage parse error:', e);
    }
    // Default initial baseline
    return {
      'mod-t1-reas': true,
      'mod-t1-ga': true,
      'mod-t1-quant': false,
      'mod-t1-eng': false
    };
  }

  setCompletedModule(moduleId: string, isCompleted: boolean): Record<string, boolean> {
    const current = this.getCompletedModules();
    current[moduleId] = isCompleted;
    try {
      localStorage.setItem(STORAGE_KEYS.COMPLETED_MODULES, JSON.stringify(current));
      this.syncProgressToSQLite(moduleId, isCompleted);
    } catch (e) {
      console.warn('LocalStorage save error:', e);
    }
    return current;
  }

  toggleCompletedModule(moduleId: string): Record<string, boolean> {
    const current = this.getCompletedModules();
    const nextState = !current[moduleId];
    return this.setCompletedModule(moduleId, nextState);
  }

  // --- 3. Mock Test Attempts & Practice History ---
  getMockAttempts(): MockAttemptRecord[] {
    try {
      const raw = localStorage.getItem(STORAGE_KEYS.MOCK_ATTEMPTS);
      if (raw) {
        return JSON.parse(raw);
      }
    } catch (e) {
      console.warn('LocalStorage mock parse error:', e);
    }
    return [];
  }

  saveMockAttempt(attempt: MockAttemptRecord): void {
    const attempts = this.getMockAttempts();
    attempts.unshift(attempt);
    try {
      localStorage.setItem(STORAGE_KEYS.MOCK_ATTEMPTS, JSON.stringify(attempts.slice(0, 50)));
      this.syncMockAttemptToSQLite(attempt);
    } catch (e) {
      console.warn('LocalStorage save error:', e);
    }
  }

  // --- 4. Background SQLite Synchronization API Calls ---

  private async syncProfileToSQLite(profileUpdate: Partial<CandidateProfile>): Promise<void> {
    try {
      await fetch('/api/sqlite/profile', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(profileUpdate)
      });
    } catch {
      // Offline fallback, localStorage retains state
    }
  }

  private async syncProgressToSQLite(moduleId: string, isCompleted: boolean): Promise<void> {
    try {
      await fetch('/api/sqlite/progress', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ module_id: moduleId, is_completed: isCompleted })
      });
    } catch {
      // Offline fallback
    }
  }

  private async syncMockAttemptToSQLite(attempt: MockAttemptRecord): Promise<void> {
    try {
      await fetch('/api/sqlite/mock-attempts', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(attempt)
      });
    } catch {
      // Offline fallback
    }
  }

  async syncAllToSQLite(): Promise<{ success: boolean; message: string }> {
    try {
      const payload = {
        user_id: this.userId,
        profile: {
          target_post_id: this.getTargetPost()
        },
        completed_modules: this.getCompletedModules(),
        mock_attempts: this.getMockAttempts()
      };

      const res = await fetch('/api/sqlite/sync-all', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });

      if (res.ok) {
        return { success: true, message: 'All LocalStorage state synced to SQLite database (govos.db)' };
      }
      return { success: false, message: 'SQLite endpoint reachable but returned error' };
    } catch (e: any) {
      return { success: false, message: `SQLite sync offline: ${e.message}` };
    }
  }

  async checkSQLiteHealth(): Promise<any> {
    try {
      const res = await fetch('/api/sqlite/status');
      if (res.ok) {
        return await res.json();
      }
      return { status: 'offline' };
    } catch {
      return { status: 'offline' };
    }
  }
}

export const storageService = new StorageService();
