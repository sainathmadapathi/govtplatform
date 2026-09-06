import { Exam, CandidateNotification, NotificationPreference, NotificationChannel } from '../types/exam';

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
  userAnswers?: Record<number, number>;
  paperData?: any;
  details?: {
    userAnswers?: Record<number, number>;
    paperData?: any;
    [key: string]: any;
  };
}

const STORAGE_KEYS = {
  TARGET_POST: 'govos_target_post_id',
  COMPLETED_MODULES: 'govos_completed_modules',
  MOCK_ATTEMPTS: 'govos_mock_attempts',
  PROFILE: 'govos_candidate_profile',
  BOOKMARKS: 'govos_bookmarked_resources',
  TRACKED_EXAMS: 'govos_tracked_exams',
  NOTIFICATION_PREFERENCES: 'govos_notification_preferences',
  NOTIFICATIONS: 'govos_candidate_notifications'
};

export const DEFAULT_NOTIFICATION_PREFERENCES: NotificationPreference = {
  channels: {
    inApp: true,
    browserPush: false,
    email: false,
    whatsapp: false
  },
  contactInfo: {
    email: '',
    phone: '',
    whatsappVerified: false
  },
  eventSubscriptions: {
    applicationOpening: true,
    applicationDeadlines: true,
    correctionWindows: true,
    admitCards: true,
    examDates: true,
    results: true
  },
  reminderSchedule: {
    sevenDaysBefore: true,
    threeDaysBefore: true,
    oneDayBefore: true,
    lastDayHoursBefore: true
  }
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

  async loadMockAttemptsFromSQLite(): Promise<MockAttemptRecord[]> {
    try {
      const res = await fetch('/api/sqlite/mock-attempts');
      if (res.ok) {
        const data = await res.json();
        if (data.attempts && Array.isArray(data.attempts)) {
          const loaded: MockAttemptRecord[] = data.attempts.map((a: any) => ({
            ...a,
            userAnswers: a.userAnswers || a.details?.userAnswers,
            paperData: a.paperData || a.details?.paperData
          }));
          if (loaded.length > 0) {
            // Update localStorage with fresh remote records while preserving local items
            const currentLocal = this.getMockAttempts();
            const map = new Map<string, MockAttemptRecord>();
            currentLocal.forEach(att => map.set(att.id, att));
            loaded.forEach(att => {
              const existing = map.get(att.id);
              map.set(att.id, {
                ...att,
                userAnswers: att.userAnswers || existing?.userAnswers,
                paperData: att.paperData || existing?.paperData
              });
            });
            const merged = Array.from(map.values());
            localStorage.setItem(STORAGE_KEYS.MOCK_ATTEMPTS, JSON.stringify(merged.slice(0, 50)));
            return merged;
          }
        }
      }
    } catch {
      // Offline fallback
    }
    return this.getMockAttempts();
  }

  // --- 4. Candidate Tracked Exams ("My Exam Timeline") ---

  getTrackedExams(): string[] {
    try {
      const raw = localStorage.getItem(STORAGE_KEYS.TRACKED_EXAMS);
      if (raw) {
        const parsed = JSON.parse(raw);
        if (Array.isArray(parsed) && parsed.length > 0) {
          return parsed;
        }
      }
    } catch (e) {
      console.warn('LocalStorage parse error for tracked exams:', e);
    }
    // Default initial tracking: SSC CGL 2026
    return ['exam-ssc-cgl-2026'];
  }

  setTrackedExams(examIds: string[]): void {
    try {
      localStorage.setItem(STORAGE_KEYS.TRACKED_EXAMS, JSON.stringify(examIds));
    } catch (e) {
      console.warn('LocalStorage save error for tracked exams:', e);
    }
  }

  isTracked(examId: string): boolean {
    return this.getTrackedExams().includes(examId);
  }

  async toggleTrackExam(examId: string): Promise<string[]> {
    const current = this.getTrackedExams();
    let updated: string[];
    const isNowTracked = !current.includes(examId);
    if (current.includes(examId)) {
      updated = current.filter(id => id !== examId);
    } else {
      updated = [...current, examId];
    }
    this.setTrackedExams(updated);

    // Sync to SQLite
    try {
      await fetch('/api/sqlite/tracked-exams', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ exam_id: examId, is_tracked: isNowTracked })
      });
    } catch {
      // Offline fallback
    }

    return updated;
  }

  async loadTrackedExamsFromSQLite(): Promise<string[]> {
    try {
      const res = await fetch('/api/sqlite/tracked-exams');
      if (res.ok) {
        const data = await res.json();
        const list = data.tracked_exam_ids || data.tracked_exams;
        if (Array.isArray(list) && list.length > 0) {
          this.setTrackedExams(list);
          return list;
        }
      }
    } catch {
      // Offline fallback
    }
    return this.getTrackedExams();
  }

  // --- 5. Personalized Notification Preferences ---

  getNotificationPreferences(): NotificationPreference {
    try {
      const raw = localStorage.getItem(STORAGE_KEYS.NOTIFICATION_PREFERENCES);
      if (raw) {
        const parsed = JSON.parse(raw);
        return {
          ...DEFAULT_NOTIFICATION_PREFERENCES,
          ...parsed,
          channels: { ...DEFAULT_NOTIFICATION_PREFERENCES.channels, ...parsed.channels },
          contactInfo: { ...DEFAULT_NOTIFICATION_PREFERENCES.contactInfo, ...parsed.contactInfo },
          eventSubscriptions: { ...DEFAULT_NOTIFICATION_PREFERENCES.eventSubscriptions, ...parsed.eventSubscriptions },
          reminderSchedule: { ...DEFAULT_NOTIFICATION_PREFERENCES.reminderSchedule, ...parsed.reminderSchedule }
        };
      }
    } catch (e) {
      console.warn('LocalStorage error for notification preferences:', e);
    }
    return { ...DEFAULT_NOTIFICATION_PREFERENCES };
  }

  async saveNotificationPreferences(prefs: NotificationPreference): Promise<void> {
    try {
      localStorage.setItem(STORAGE_KEYS.NOTIFICATION_PREFERENCES, JSON.stringify(prefs));
      await fetch('/api/sqlite/notifications/preferences', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(prefs)
      });
    } catch (e) {
      console.warn('Preferences save/sync error:', e);
    }
  }

  async loadNotificationPreferencesFromSQLite(): Promise<NotificationPreference> {
    try {
      const res = await fetch('/api/sqlite/notifications/preferences');
      if (res.ok) {
        const data = await res.json();
        const raw = data.preferences || data;
        if (raw && (raw.channels || raw.eventSubscriptions)) {
          const loaded = {
            ...DEFAULT_NOTIFICATION_PREFERENCES,
            ...raw,
            channels: { ...DEFAULT_NOTIFICATION_PREFERENCES.channels, ...raw.channels },
            contactInfo: { ...DEFAULT_NOTIFICATION_PREFERENCES.contactInfo, ...raw.contactInfo },
            eventSubscriptions: { ...DEFAULT_NOTIFICATION_PREFERENCES.eventSubscriptions, ...raw.eventSubscriptions },
            reminderSchedule: { ...DEFAULT_NOTIFICATION_PREFERENCES.reminderSchedule, ...raw.reminderSchedule }
          };
          localStorage.setItem(STORAGE_KEYS.NOTIFICATION_PREFERENCES, JSON.stringify(loaded));
          return loaded;
        }
      }
    } catch {
      // Offline fallback
    }
    return this.getNotificationPreferences();
  }

  // --- 6. Candidate Notifications Queue & History ---

  getNotifications(): CandidateNotification[] {
    try {
      const raw = localStorage.getItem(STORAGE_KEYS.NOTIFICATIONS);
      if (raw) {
        return JSON.parse(raw);
      }
    } catch (e) {
      console.warn('LocalStorage error for notifications:', e);
    }
    return [];
  }

  saveNotifications(notifs: CandidateNotification[]): void {
    try {
      localStorage.setItem(STORAGE_KEYS.NOTIFICATIONS, JSON.stringify(notifs));
    } catch (e) {
      console.warn('LocalStorage save error for notifications:', e);
    }
  }

  async markNotificationAsRead(id: string): Promise<void> {
    const current = this.getNotifications();
    const updated = current.map(n => {
      if (id === 'ALL' || n.id === id) {
        return { ...n, isRead: true };
      }
      return n;
    });
    this.saveNotifications(updated);

    try {
      await fetch('/api/sqlite/notifications/read', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ notification_id: id })
      });
    } catch {
      // Offline fallback
    }
  }

  async clearAllNotifications(): Promise<void> {
    this.saveNotifications([]);
    try {
      await fetch('/api/sqlite/notifications', { method: 'DELETE' });
    } catch {
      // Offline fallback
    }
  }

  // --- 7. Personalized Notification Generation Engine ---

  generatePersonalizedNotificationsForTrackedExams(allExams: Exam[]): CandidateNotification[] {
    const trackedExamIds = this.getTrackedExams();
    const prefs = this.getNotificationPreferences();
    const currentNotifs = this.getNotifications();

    // Map existing notifications to preserve read status and original creation dates
    const existingMap = new Map<string, CandidateNotification>();
    currentNotifs.forEach(n => existingMap.set(n.id, n));

    // Determine active delivery channels
    const channels: NotificationChannel[] = ['IN_APP'];
    if (prefs.channels.browserPush) channels.push('PUSH');
    if (prefs.channels.email && prefs.contactInfo.email) channels.push('EMAIL');
    if (prefs.channels.whatsapp && prefs.contactInfo.whatsappVerified) channels.push('WHATSAPP');

    const generated: CandidateNotification[] = [];

    allExams.forEach(exam => {
      // Only generate personalized alerts for exams the candidate is actively tracking
      if (!trackedExamIds.includes(exam.id)) {
        return;
      }

      exam.dates.forEach(d => {
        if (d.status === 'SUPERSEDED') return;

        // 1. Application Opening Event
        if (d.type === 'APPLICATION_OPEN' && prefs.eventSubscriptions.applicationOpening) {
          const id = `notif-${exam.id}-app-open`;
          generated.push({
            id,
            examId: exam.id,
            examCode: exam.code,
            examTitle: exam.title,
            eventType: 'APPLICATION_OPEN',
            title: `📢 ${exam.title}: Application Portal Open!`,
            message: `Online application submission is now open on the official portal (${exam.officialDomain}). Ensure your documents and OTR details are verified before applying.`,
            channelsDelivered: channels,
            actionType: 'EXAM_DETAIL',
            actionPayload: { section: 4 },
            priority: 'HIGH',
            createdAt: d.dateTimeStr,
            scheduledDateStr: d.dateTimeStr,
            isRead: false
          });
        }

        // 2. Application Deadlines (Multi-stage reminders)
        if (d.type === 'APPLICATION_CLOSE' && prefs.eventSubscriptions.applicationDeadlines) {
          // 7 Days Before
          if (prefs.reminderSchedule.sevenDaysBefore) {
            const id = `notif-${exam.id}-deadline-7d`;
            generated.push({
              id,
              examId: exam.id,
              examCode: exam.code,
              examTitle: exam.title,
              eventType: 'APPLICATION_DEADLINE',
              title: `⏳ 7 Days Left: ${exam.title} Application Deadline`,
              message: `Only 7 days remaining until online application closes on ${d.dateTimeStr}. Complete your fee payment and submit before the final rush.`,
              channelsDelivered: channels,
              actionType: 'EXAM_DETAIL',
              actionPayload: { section: 4 },
              priority: 'HIGH',
              createdAt: '2026-09-20 10:00:00',
              scheduledDateStr: d.dateTimeStr,
              isRead: false
            });
          }

          // 3 Days Before
          if (prefs.reminderSchedule.threeDaysBefore) {
            const id = `notif-${exam.id}-deadline-3d`;
            generated.push({
              id,
              examId: exam.id,
              examCode: exam.code,
              examTitle: exam.title,
              eventType: 'APPLICATION_DEADLINE',
              title: `🚨 Urgent: 3 Days Left for ${exam.title}!`,
              message: `Application closes in 3 days (${d.dateTimeStr}). Check that your live photograph, running signature, and category certificates are compliant.`,
              channelsDelivered: channels,
              actionType: 'EXAM_DETAIL',
              actionPayload: { section: 4 },
              priority: 'CRITICAL',
              createdAt: '2026-09-24 10:00:00',
              scheduledDateStr: d.dateTimeStr,
              isRead: false
            });
          }

          // 1 Day Before
          if (prefs.reminderSchedule.oneDayBefore) {
            const id = `notif-${exam.id}-deadline-1d`;
            generated.push({
              id,
              examId: exam.id,
              examCode: exam.code,
              examTitle: exam.title,
              eventType: 'APPLICATION_DEADLINE',
              title: `⚠️ 24 Hours Left: Final Call for ${exam.title}`,
              message: `The application portal closes tomorrow (${d.dateTimeStr})! Confirm payment status and download your application acknowledgment receipt immediately.`,
              channelsDelivered: channels,
              actionType: 'EXAM_DETAIL',
              actionPayload: { section: 4 },
              priority: 'CRITICAL',
              createdAt: '2026-09-26 10:00:00',
              scheduledDateStr: d.dateTimeStr,
              isRead: false
            });
          }

          // Final Day / Closing Hours
          if (prefs.reminderSchedule.lastDayHoursBefore) {
            const id = `notif-${exam.id}-deadline-lastday`;
            generated.push({
              id,
              examId: exam.id,
              examCode: exam.code,
              examTitle: exam.title,
              eventType: 'APPLICATION_DEADLINE',
              title: `🔥 Final Hours: ${exam.title} Closes Tonight!`,
              message: `The application window terminates strictly at ${d.dateTimeStr.split(' ')[1] || '23:59'} IST today. No extensions are guaranteed. Finish submission now!`,
              channelsDelivered: channels,
              actionType: 'EXAM_DETAIL',
              actionPayload: { section: 4 },
              priority: 'CRITICAL',
              createdAt: '2026-09-27 12:00:00',
              scheduledDateStr: d.dateTimeStr,
              isRead: false
            });
          }
        }

        // 3. Correction Window
        if (d.type === 'CORRECTION_WINDOW' && prefs.eventSubscriptions.correctionWindows) {
          const id = `notif-${exam.id}-correction`;
          generated.push({
            id,
            examId: exam.id,
            examCode: exam.code,
            examTitle: exam.title,
            eventType: 'CORRECTION_WINDOW',
            title: `✏️ Correction Window Open: ${exam.title}`,
            message: `The official application correction facility is active from ${d.dateTimeStr}. Review your uploaded photograph, post preferences, and exam center choices.`,
            channelsDelivered: channels,
            actionType: 'EXAM_DETAIL',
            actionPayload: { section: 4 },
            priority: 'HIGH',
            createdAt: d.dateTimeStr,
            scheduledDateStr: d.dateTimeStr,
            isRead: false
          });
        }

        // 4. Admit Card / City Slip
        if (d.type === 'ADMIT_CARD' && prefs.eventSubscriptions.admitCards) {
          const id = `notif-${exam.id}-admit-card`;
          generated.push({
            id,
            examId: exam.id,
            examCode: exam.code,
            examTitle: exam.title,
            eventType: 'ADMIT_CARD',
            title: `🎟️ Admit Card & City Slip: ${exam.title}`,
            message: `Tier 1 Exam City Intimation & e-Admit Card released on ${d.dateTimeStr}. Check your examination date, shift time, and exam center address.`,
            channelsDelivered: channels,
            actionType: 'CALENDAR',
            actionPayload: { examCode: exam.code },
            priority: 'CRITICAL',
            createdAt: d.dateTimeStr,
            scheduledDateStr: d.dateTimeStr,
            isRead: false
          });
        }

        // 5. Exam Date
        if (d.type === 'EXAM_TIER1' && prefs.eventSubscriptions.examDates) {
          const id = `notif-${exam.id}-exam-tier1`;
          generated.push({
            id,
            examId: exam.id,
            examCode: exam.code,
            examTitle: exam.title,
            eventType: 'EXAM_DATE',
            title: `🎯 Exam Day Announcement: ${exam.title}`,
            message: `The Computer Based Test commences on ${d.dateTimeStr}. Remember to carry your original Photo ID, two passport photos, and printed Admit Card.`,
            channelsDelivered: channels,
            actionType: 'EXAM_DETAIL',
            actionPayload: { section: 5 },
            priority: 'HIGH',
            createdAt: d.dateTimeStr,
            scheduledDateStr: d.dateTimeStr,
            isRead: false
          });
        }

        // 6. Answer Key
        if (d.type === 'ANSWER_KEY' && prefs.eventSubscriptions.results) {
          const id = `notif-${exam.id}-anskey`;
          generated.push({
            id,
            examId: exam.id,
            examCode: exam.code,
            examTitle: exam.title,
            eventType: 'ANSWER_KEY',
            title: `🔑 Tentative Answer Key Released: ${exam.title}`,
            message: `Response sheet and tentative answer keys are available on ${d.dateTimeStr}. Calculate your score and raise challenges if questions contain errors.`,
            channelsDelivered: channels,
            actionType: 'EXAM_DETAIL',
            actionPayload: { section: 9 },
            priority: 'NORMAL',
            createdAt: d.dateTimeStr,
            scheduledDateStr: d.dateTimeStr,
            isRead: false
          });
        }

        // 7. Result
        if (d.type === 'RESULT' && prefs.eventSubscriptions.results) {
          const id = `notif-${exam.id}-result`;
          generated.push({
            id,
            examId: exam.id,
            examCode: exam.code,
            examTitle: exam.title,
            eventType: 'RESULT',
            title: `🏆 Official Result Declared: ${exam.title}`,
            message: `Official shortlisted roll numbers and category cut-off marks announced on ${d.dateTimeStr}. Check your merit status for the next stage!`,
            channelsDelivered: channels,
            actionType: 'EXAM_DETAIL',
            actionPayload: { section: 10 },
            priority: 'CRITICAL',
            createdAt: d.dateTimeStr,
            scheduledDateStr: d.dateTimeStr,
            isRead: false
          });
        }
      });
    });

    // Merge: preserve isRead and original createdAt for existing notifications
    const mergedList: CandidateNotification[] = generated.map(notif => {
      const existing = existingMap.get(notif.id);
      if (existing) {
        return {
          ...notif,
          isRead: existing.isRead,
          createdAt: existing.createdAt
        };
      }
      return notif;
    });

    // Preserve any custom test alerts sent by the user
    currentNotifs.forEach(n => {
      if (n.id.startsWith('notif-test-') && !mergedList.some(m => m.id === n.id)) {
        mergedList.unshift(n);
      }
    });

    // Sort: unread first, then by priority (CRITICAL > HIGH > NORMAL), then newest
    const priorityWeight: Record<string, number> = { CRITICAL: 3, HIGH: 2, NORMAL: 1 };
    mergedList.sort((a, b) => {
      if (a.isRead !== b.isRead) return a.isRead ? 1 : -1;
      const pDiff = (priorityWeight[b.priority] || 1) - (priorityWeight[a.priority] || 1);
      if (pDiff !== 0) return pDiff;
      return b.createdAt.localeCompare(a.createdAt);
    });

    this.saveNotifications(mergedList);

    // Asynchronously synchronize with SQLite in background
    fetch('/api/sqlite/notifications', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ notifications: mergedList })
    }).catch(() => {
      // Offline fallback
    });

    return mergedList;
  }

  // --- 8. Background SQLite Synchronization API Calls ---

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
      const payload = {
        ...attempt,
        details: {
          userAnswers: attempt.userAnswers,
          paperData: attempt.paperData
        }
      };
      await fetch('/api/sqlite/mock-attempts', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
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
        mock_attempts: this.getMockAttempts().map(att => ({
          ...att,
          details: {
            userAnswers: att.userAnswers,
            paperData: att.paperData
          }
        })),
        tracked_exams: this.getTrackedExams(),
        notification_preferences: this.getNotificationPreferences()
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
