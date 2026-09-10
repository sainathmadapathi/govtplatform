// GovOS services: age/profile maths, eligibility engine, dual-persistence storage.

import {
  ResourceLinkCheck,
  ResearchExtractResult,
  ResearchFinding,
  ResearchMode,
  ResearchOutcome,
  ResearchReviewStatus,
  ResearchRun,
  ResearchSearchResult,
  ResearchStatus,
  CandidateNotification,
  EligibilityDiagnostic,
  Exam,
  NotificationChannel,
  NotificationPreference,
  PostRequirement,
  PostVerdict,
  UserProfile,
  ChannelUploadFeed,
  LiveResourceStatus,
  ResourceAddition,
  ResourceHealthSync,
  SscNoticeFeed,
  ExamCategoryTag,
  ExamRecommendation,
  UserInteractionEvent,
  UserInteractionType
} from './types';

// ==========================================================================
// profileUtils.ts
// ==========================================================================
/**
 * Utility functions for UserProfile calculations
 */

export interface DetailedAge {
  years: number;
  months: number;
  days: number;
  formatted: string;
}

/**
 * Calculates candidate age in completed years based on Date of Birth and a Reference Cutoff Date.
 * @param dateOfBirth Candidate DOB in YYYY-MM-DD format
 * @param referenceDate Official cutoff date in YYYY-MM-DD format
 */
export function calculateAge(dateOfBirth: string, referenceDate: string = '2026-08-01'): number {
  const dob = new Date(dateOfBirth);
  const reference = new Date(referenceDate);

  if (Number.isNaN(dob.getTime()) || Number.isNaN(reference.getTime())) {
    return 0;
  }

  let age = reference.getFullYear() - dob.getFullYear();
  const monthDifference = reference.getMonth() - dob.getMonth();

  if (
    monthDifference < 0 ||
    (monthDifference === 0 && reference.getDate() < dob.getDate())
  ) {
    age--;
  }

  return Math.max(0, age);
}

/**
 * Calculates detailed age in years, months, and days as of crucial cutoff date.
 */
export function calculateDetailedAge(dateOfBirth: string, referenceDate: string = '2026-08-01'): DetailedAge {
  const dob = new Date(dateOfBirth);
  const ref = new Date(referenceDate);

  if (Number.isNaN(dob.getTime()) || Number.isNaN(ref.getTime())) {
    return { years: 0, months: 0, days: 0, formatted: '0 yrs' };
  }

  let years = ref.getFullYear() - dob.getFullYear();
  let months = ref.getMonth() - dob.getMonth();
  let days = ref.getDate() - dob.getDate();

  if (days < 0) {
    months -= 1;
    // Get days in previous month
    const prevMonthLastDay = new Date(ref.getFullYear(), ref.getMonth(), 0).getDate();
    days += prevMonthLastDay;
  }

  if (months < 0) {
    years -= 1;
    months += 12;
  }

  return {
    years: Math.max(0, years),
    months: Math.max(0, months),
    days: Math.max(0, days),
    formatted: `${years} yrs, ${months} mos, ${days} days`
  };
}

/**
 * Returns Category Age Relaxation in years as per official SSC CGL rules.
 */
export function getCategoryAgeRelaxation(category: string): number {
  switch (category) {
    case 'OBC':
      return 3;
    case 'SC':
    case 'ST':
      return 5;
    case 'PwBD':
      return 10;
    default:
      return 0;
  }
}


// ==========================================================================
// eligibilityEngine.ts
// ==========================================================================
export function normalizeDegree(value: string): string {
  const normalized = (value || '').toLowerCase().trim();
  if (normalized.includes('b.tech') || normalized.includes('b.e') || normalized.includes('engineering')) {
    return 'bachelor';
  }
  if (
    normalized.includes('b.sc') ||
    normalized.includes('b.a') ||
    normalized.includes('b.com') ||
    normalized.includes('bba') ||
    normalized.includes('bca') ||
    normalized.includes('bachelor') ||
    normalized.includes('graduation') ||
    normalized.includes('degree')
  ) {
    return 'bachelor';
  }
  return normalized;
}

export function evaluatePostEligibility(
  post: PostRequirement,
  profile: UserProfile,
  crucialDate: string = '2026-08-01'
): PostVerdict {
  const age = calculateAge(profile.dateOfBirth, crucialDate);
  const relaxation = getCategoryAgeRelaxation(profile.category);
  const maxPermissibleAge = post.maxAge + relaxation;
  const userDegreeNorm = normalizeDegree(profile.degree);
  const isBachelor = userDegreeNorm.includes('bachelor') || userDegreeNorm.includes('degree');

  let ageStatus: 'OK' | 'EXCEEDED' | 'UNDERAGE' = 'OK';
  let qualStatus: 'OK' | 'DISQUALIFIED' = 'OK';
  let physicalStatus: 'OK' | 'RESTRICTED' = 'OK';
  const reasons: string[] = [];

  // 1. Age Verification
  if (age < post.minAge) {
    ageStatus = 'UNDERAGE';
    reasons.push(`Underage: ${age} yrs is below minimum requirement of ${post.minAge} yrs`);
  } else if (age > maxPermissibleAge) {
    ageStatus = 'EXCEEDED';
    reasons.push(
      `Age Exceeded: ${age} yrs exceeds permissible limit of ${maxPermissibleAge} yrs (${post.maxAge} base + ${relaxation} yrs ${profile.category} relaxation)`
    );
  } else {
    reasons.push(
      `Age Verified: ${age} yrs (as of ${crucialDate}) is within ${post.minAge}-${maxPermissibleAge} yrs limit`
    );
  }

  // 2. Educational Qualification Verification
  if (!isBachelor && !profile.degree.toLowerCase().includes('final year')) {
    qualStatus = 'DISQUALIFIED';
    reasons.push(`Qualification: Requires Bachelor's Degree from recognized university`);
  } else {
    // Check post-specific specialized qualifications
    if (post.id === 'post-jso') {
      const hasMaths = profile.mathsIn12thWith60Percent === true;
      const hasStats = profile.statisticsInDegree === true || (profile.branch || '').toLowerCase().includes('stat');
      if (!hasMaths && !hasStats) {
        qualStatus = 'DISQUALIFIED';
        reasons.push(`JSO Special Criteria: Requires 60% in Maths in 12th OR Statistics as a subject in Degree`);
      } else {
        reasons.push(`JSO Criteria Satisfied: ${hasMaths ? '60%+ in 12th Maths' : 'Statistics in Degree'} verified`);
      }
    } else if (post.id === 'post-stat-inv') {
      const hasStatsDegree = profile.statisticsInDegree === true || (profile.branch || '').toLowerCase().includes('stat');
      if (!hasStatsDegree) {
        qualStatus = 'DISQUALIFIED';
        reasons.push(`Statistical Investigator Gr II: Requires Statistics as a subject in all 3 years of Degree`);
      } else {
        reasons.push(`Statistical Criteria Satisfied: Statistics in all semesters verified`);
      }
    } else {
      reasons.push(`Essential Qualification: Bachelor's Degree verified`);
    }
  }

  // 3. Physical Standards Check
  if (post.physicalRequired) {
    if (profile.physicalFitnessDeclared === false) {
      physicalStatus = 'RESTRICTED';
      reasons.push(`Physical Criteria: Requires mandatory physical fitness standards (${post.physicalNote || 'Physical test & measurement'})`);
    }
    if (post.colorBlindnessAllowed === false && profile.colorBlind === true) {
      physicalStatus = 'RESTRICTED';
      reasons.push(`Medical Criteria: Color blindness is NOT permitted for this enforcement post`);
    }
  }

  const eligible = ageStatus === 'OK' && qualStatus === 'OK' && physicalStatus === 'OK';

  return {
    postId: post.id,
    postName: post.postName,
    department: post.department,
    payLevel: post.payLevel,
    eligible,
    ageStatus,
    calculatedAge: age,
    maxPermissibleAge,
    qualStatus,
    physicalStatus,
    reason: reasons.join(' • '),
    officialClause: post.provenance.clauseNumber || 'Section 3.1 & Annexure-VII'
  };
}

export function evaluateEligibility(exam: Exam, profile: UserProfile): EligibilityDiagnostic {
  const crucialDate = exam.crucialEligibilityDate || '2026-08-01';
  const detailedAge = calculateDetailedAge(profile.dateOfBirth, crucialDate);
  const relaxation = getCategoryAgeRelaxation(profile.category);
  const userAge = detailedAge.years;

  const legalClauses: string[] = [
    'SSC CGL Notification Section 3.1: Crucial date for age limit calculation is 01-08-2026',
    `Section 3.2: Permissible upper age relaxation for ${profile.category} candidates is +${relaxation} years`,
    'Section 8.1: Essential Educational Qualification: Bachelor’s Degree from a recognized University or equivalent (as on 01-08-2026)'
  ];

  const postVerdicts: PostVerdict[] = exam.posts.map(post =>
    evaluatePostEligibility(post, profile, crucialDate)
  );

  const eligibleCount = postVerdicts.filter(p => p.eligible).length;
  const totalCount = postVerdicts.length;

  let status: 'ELIGIBLE' | 'CONDITIONAL' | 'INELIGIBLE' = 'INELIGIBLE';
  let plainEnglishExplanation = '';

  if (eligibleCount === totalCount) {
    status = 'ELIGIBLE';
    plainEnglishExplanation = `Congratulations! Based on official SSC CGL 2026 rules, you are fully eligible for ALL ${totalCount} posts (including Group B Gazetted & Non-Gazetted posts) with your calculated age of ${detailedAge.formatted} as on ${crucialDate}.`;
  } else if (eligibleCount > 0) {
    status = 'CONDITIONAL';
    plainEnglishExplanation = `You are eligible for ${eligibleCount} out of ${totalCount} posts. Some posts (like JSO, Statistical Investigator, or 18-27 age bracket posts) have specific age brackets or subject requirements that you do not satisfy.`;
  } else {
    status = 'INELIGIBLE';
    if (userAge < 18) {
      plainEnglishExplanation = `You are currently ${userAge} years old as of the crucial cutoff date (${crucialDate}). Minimum age required for SSC CGL is 18 years.`;
    } else {
      plainEnglishExplanation = `Your calculated age (${userAge} years as of ${crucialDate}) exceeds the upper age limit for all SSC CGL posts even after applying ${profile.category} category relaxation (+${relaxation} years).`;
    }
  }

  return {
    isEligible: eligibleCount > 0,
    status,
    calculatedAgeOnCutoff: {
      years: detailedAge.years,
      months: detailedAge.months,
      days: detailedAge.days,
      crucialDate
    },
    categoryRelaxationApplied: `${profile.category} (+${relaxation} Years Relaxation Applied)`,
    totalEligiblePosts: eligibleCount,
    totalAvailablePosts: totalCount,
    legalClauses,
    plainEnglishExplanation,
    postVerdicts
  };
}

export const evaluateCandidateEligibility = evaluateEligibility;


// ==========================================================================
// storageService.ts
// ==========================================================================
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
  NOTIFICATIONS: 'govos_candidate_notifications',
  COMPLETED_TOPICS: 'govos_completed_syllabus_topics',
  ROADMAP_GOALS: 'govos_roadmap_goals',
  PENDING_REPORTS: 'govos_pending_reports',
  USER_INTERACTIONS: 'govos_user_interactions'
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

    if (isNowTracked) {
      this.recordInteraction({
        type: 'FOLLOW',
        examId: examId
      });
    }

    return updated;
  }

  // --- 4b. Bookmarked Exams ---
  getBookmarkedExams(): string[] {
    try {
      const raw = localStorage.getItem(STORAGE_KEYS.BOOKMARKS);
      if (raw) {
        const parsed = JSON.parse(raw);
        if (Array.isArray(parsed)) return parsed;
      }
    } catch (e) {
      console.warn('LocalStorage parse error for bookmarked exams:', e);
    }
    return [];
  }

  isBookmarked(examId: string): boolean {
    return this.getBookmarkedExams().includes(examId);
  }

  toggleBookmarkExam(examId: string): string[] {
    const current = this.getBookmarkedExams();
    let updated: string[];
    const isNowBookmarked = !current.includes(examId);
    if (current.includes(examId)) {
      updated = current.filter(id => id !== examId);
    } else {
      updated = [...current, examId];
      this.recordInteraction({
        type: 'BOOKMARK',
        examId: examId
      });
    }
    try {
      localStorage.setItem(STORAGE_KEYS.BOOKMARKS, JSON.stringify(updated));
    } catch (e) {
      console.warn('LocalStorage save error for bookmarked exams:', e);
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

  // --- 7b. Syllabus Topic Checkboxes (per exam) ---

  getCompletedTopics(examId: string): Record<string, boolean> {
    try {
      const raw = localStorage.getItem(STORAGE_KEYS.COMPLETED_TOPICS);
      if (raw) {
        const all = JSON.parse(raw);
        if (all && typeof all === 'object' && all[examId]) {
          return all[examId];
        }
      }
    } catch (e) {
      console.warn('LocalStorage parse error for completed topics:', e);
    }
    return {};
  }

  toggleCompletedTopic(examId: string, topicId: string): Record<string, boolean> {
    const current = this.getCompletedTopics(examId);
    const next = { ...current, [topicId]: !current[topicId] };
    try {
      const raw = localStorage.getItem(STORAGE_KEYS.COMPLETED_TOPICS);
      const all = raw ? JSON.parse(raw) : {};
      all[examId] = next;
      localStorage.setItem(STORAGE_KEYS.COMPLETED_TOPICS, JSON.stringify(all));
      // Reuse the study_progress table so topic ticks survive a browser reset too.
      this.syncProgressToSQLite(`topic:${examId}:${topicId}`, next[topicId]);
    } catch (e) {
      console.warn('LocalStorage save error for completed topics:', e);
    }
    return next;
  }

  // --- 7c. Roadmap Weekly Goal Checkboxes (per exam) ---

  getRoadmapGoals(examId: string): Record<string, boolean> {
    try {
      const raw = localStorage.getItem(STORAGE_KEYS.ROADMAP_GOALS);
      if (raw) {
        const all = JSON.parse(raw);
        if (all && typeof all === 'object' && all[examId]) {
          return all[examId];
        }
      }
    } catch (e) {
      console.warn('LocalStorage parse error for roadmap goals:', e);
    }
    return {};
  }

  toggleRoadmapGoal(examId: string, goalKey: string): Record<string, boolean> {
    const current = this.getRoadmapGoals(examId);
    const next = { ...current, [goalKey]: !current[goalKey] };
    try {
      const raw = localStorage.getItem(STORAGE_KEYS.ROADMAP_GOALS);
      const all = raw ? JSON.parse(raw) : {};
      all[examId] = next;
      localStorage.setItem(STORAGE_KEYS.ROADMAP_GOALS, JSON.stringify(all));
      this.syncProgressToSQLite(`goal:${examId}:${goalKey}`, next[goalKey]);
    } catch (e) {
      console.warn('LocalStorage save error for roadmap goals:', e);
    }
    return next;
  }

  // --- 7d. Data Accuracy Reports (queued offline, flushed when server returns) ---

  private getPendingReports(): any[] {
    try {
      const raw = localStorage.getItem(STORAGE_KEYS.PENDING_REPORTS);
      if (raw) {
        const parsed = JSON.parse(raw);
        if (Array.isArray(parsed)) return parsed;
      }
    } catch (e) {
      console.warn('LocalStorage parse error for pending reports:', e);
    }
    return [];
  }

  private setPendingReports(reports: any[]): void {
    try {
      localStorage.setItem(STORAGE_KEYS.PENDING_REPORTS, JSON.stringify(reports.slice(0, 50)));
    } catch (e) {
      console.warn('LocalStorage save error for pending reports:', e);
    }
  }

  /**
   * Sends a data-accuracy report to the admin audit queue.
   * Falls back to a local queue when the server is unreachable, so the report is
   * never silently discarded.
   */
  async submitReport(report: { entityType: string; entityId: string; description: string }): Promise<{ delivered: boolean }> {
    const payload = { ...report, createdAt: new Date().toISOString() };
    try {
      const res = await fetch('/api/reports', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });
      if (res.ok) {
        return { delivered: true };
      }
    } catch {
      // fall through to local queue
    }
    this.setPendingReports([payload, ...this.getPendingReports()]);
    return { delivered: false };
  }

  /** Retries any reports queued while the server was unreachable. */
  async flushPendingReports(): Promise<number> {
    const pending = this.getPendingReports();
    if (pending.length === 0) return 0;

    const stillPending: any[] = [];
    let sent = 0;
    for (const report of pending) {
      try {
        const res = await fetch('/api/reports', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(report)
        });
        if (res.ok) {
          sent++;
        } else {
          stillPending.push(report);
        }
      } catch {
        stillPending.push(report);
      }
    }
    this.setPendingReports(stillPending);
    return sent;
  }

  // --- 7e. Bookmarked Resources ("Saved for later" shelf) ---

  getBookmarkedResourceIds(): string[] {
    try {
      const raw = localStorage.getItem(STORAGE_KEYS.BOOKMARKS);
      if (raw) {
        const parsed = JSON.parse(raw);
        if (Array.isArray(parsed)) return parsed;
      }
    } catch (e) {
      console.warn('LocalStorage parse error for bookmarks:', e);
    }
    return [];
  }

  private setBookmarkedResourceIds(ids: string[]): void {
    try {
      localStorage.setItem(STORAGE_KEYS.BOOKMARKS, JSON.stringify(ids));
    } catch (e) {
      console.warn('LocalStorage save error for bookmarks:', e);
    }
  }

  isResourceBookmarked(resourceId: string): boolean {
    return this.getBookmarkedResourceIds().includes(resourceId);
  }

  /** Toggles a bookmark locally and mirrors it to SQLite. Returns the new id list. */
  toggleResourceBookmark(resource: { id: string; title: string; type: string; url: string }): string[] {
    const current = this.getBookmarkedResourceIds();
    const isNowSaved = !current.includes(resource.id);
    const updated = isNowSaved ? [...current, resource.id] : current.filter(id => id !== resource.id);
    this.setBookmarkedResourceIds(updated);

    fetch('/api/sqlite/bookmarks', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        resource_id: resource.id,
        title: resource.title,
        resource_type: resource.type,
        url: resource.url,
        is_bookmarked: isNowSaved
      })
    }).catch(() => {
      // Offline fallback: localStorage already holds the change
    });

    return updated;
  }

  async loadBookmarksFromSQLite(): Promise<string[]> {
    try {
      const res = await fetch('/api/sqlite/bookmarks');
      if (res.ok) {
        const data = await res.json();
        if (Array.isArray(data.resource_ids)) {
          // Union with local so an offline save is never dropped
          const merged = Array.from(new Set([...this.getBookmarkedResourceIds(), ...data.resource_ids]));
          this.setBookmarkedResourceIds(merged);
          return merged;
        }
      }
    } catch {
      // Offline fallback
    }
    return this.getBookmarkedResourceIds();
  }

  // --- 7f. Resource Link Health Check (server performs the HTTP requests) ---

  async verifyResourceLinks(urls: string[]): Promise<ResourceLinkCheck[]> {
    try {
      const res = await fetch('/api/resources/verify-links', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ urls })
      });
      if (res.ok) {
        const data = await res.json();
        if (Array.isArray(data.results)) return data.results;
      }
    } catch {
      // Server unreachable: caller shows "could not verify"
    }
    return [];
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

  // --- 8. Behavioral Interaction History & Recommendations (Time-Decayed BPR) ---

  getUserInteractions(): UserInteractionEvent[] {
    try {
      const raw = localStorage.getItem(STORAGE_KEYS.USER_INTERACTIONS);
      if (raw) {
        const parsed = JSON.parse(raw);
        if (Array.isArray(parsed)) return parsed;
      }
    } catch (e) {
      console.warn('LocalStorage parse error for user interactions:', e);
    }
    return [];
  }

  recordInteraction(event: Omit<UserInteractionEvent, 'id' | 'timestamp'>): UserInteractionEvent {
    const fullEvent: UserInteractionEvent = {
      targetId: event.targetId || event.examId || 'unknown',
      targetType: event.targetType || 'EXAM',
      ...event,
      id: `act-${Date.now()}-${Math.random().toString(36).substring(2, 7)}`,
      timestamp: Date.now()
    };

    try {
      const current = this.getUserInteractions();
      // Keep most recent 100 interaction events
      const updated = [fullEvent, ...current.filter(e => e.id !== fullEvent.id)].slice(0, 100);
      localStorage.setItem(STORAGE_KEYS.USER_INTERACTIONS, JSON.stringify(updated));
      this.syncInteractionToSQLite(fullEvent);
    } catch (e) {
      console.warn('LocalStorage save error for user interaction:', e);
    }

    return fullEvent;
  }

  clearUserInteractions(): void {
    try {
      localStorage.removeItem(STORAGE_KEYS.USER_INTERACTIONS);
      fetch(`/api/sqlite/interactions?user_id=${this.userId}`, { method: 'DELETE' }).catch(() => {});
    } catch (e) {
      console.warn('Error clearing user interactions:', e);
    }
  }

  async syncInteractionToSQLite(event: UserInteractionEvent): Promise<void> {
    try {
      await fetch('/api/sqlite/interactions', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ ...event, user_id: this.userId })
      });
    } catch {
      // Offline fallback
    }
  }

  async loadInteractionsFromSQLite(): Promise<UserInteractionEvent[]> {
    try {
      const res = await fetch(`/api/sqlite/interactions?user_id=${this.userId}`);
      if (res.ok) {
        const data = await res.json();
        if (Array.isArray(data.interactions)) {
          const local = this.getUserInteractions();
          const localIds = new Set(local.map(i => i.id));
          const merged = [...local, ...data.interactions.filter((i: UserInteractionEvent) => !localIds.has(i.id))]
            .sort((a, b) => b.timestamp - a.timestamp)
            .slice(0, 100);
          localStorage.setItem(STORAGE_KEYS.USER_INTERACTIONS, JSON.stringify(merged));
          return merged;
        }
      }
    } catch {
      // Offline fallback
    }
    return this.getUserInteractions();
  }

  getProfile(): UserProfile | null {
    try {
      const raw = localStorage.getItem(STORAGE_KEYS.PROFILE);
      if (raw) return JSON.parse(raw);
    } catch (e) {
      console.warn('LocalStorage parse error for profile:', e);
    }
    return null;
  }

  saveProfile(profile: UserProfile): void {
    try {
      localStorage.setItem(STORAGE_KEYS.PROFILE, JSON.stringify(profile));
      this.syncProfileToSQLite({
        category: profile.category,
        qualification: profile.degree
      });
    } catch (e) {
      console.warn('LocalStorage save error for profile:', e);
    }
  }

  getPersonalizedRecommendations(allExams: Exam[], profile?: UserProfile, referenceTime?: number): ExamRecommendation[] {
    const interactions = this.getUserInteractions();
    return computePersonalizedRecommendations(allExams, interactions, profile || this.getProfile() || undefined, referenceTime);
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

// ============================================================================
// Time-Aware Behaviour-Based Recommendation Engine
// (Inspired by Time-Decayed Bayesian Personalized Ranking Principles)
// ============================================================================

export const INTERACTION_WEIGHTS: Record<UserInteractionType, number> = {
  FOLLOW: 4.0,           // Explicitly tracking exam in timeline
  BOOKMARK: 3.5,         // Bookmarking exam or key study resource
  SYLLABUS_READ: 5.0,    // Deep reading of exam blueprint / syllabus (active preparation)
  RESOURCE_ACCESS: 4.0,  // Accessing exam study material, PYQ, or portal
  VIEW: 2.5,             // Opening full exam guide
  SEARCH: 1.5            // Searching exam keywords or career goals
};

/**
 * Interaction-specific half-life decay in hours tailored to competitive exam preparation cycles:
 * - SEARCH: 24h (1 day) - immediate, temporary curiosity query
 * - VIEW: 72h (3 days) - fleeting exploratory guide overview
 * - RESOURCE_ACCESS: 336h (14 days / 2 weeks) - targeted study notes/PYQ material
 * - SYLLABUS_READ: 504h (21 days / 3 weeks) - in-depth curriculum examination
 * - BOOKMARK: 1440h (60 days / 2 months) - deliberate shortlisting interest
 * - FOLLOW: 4320h (180 days / 6 months) - active exam-cycle timeline tracking
 */
export const INTERACTION_HALF_LIVES_HOURS: Record<UserInteractionType, number> = {
  SEARCH: 24,            // 1 day
  VIEW: 72,              // 3 days
  RESOURCE_ACCESS: 336,  // 14 days (2 weeks)
  SYLLABUS_READ: 504,    // 21 days (3 weeks)
  BOOKMARK: 1440,        // 60 days (2 months)
  FOLLOW: 4320           // 180 days (6 months)
};

/**
 * Intrinsic signal strength multiplier capturing commitment fidelity:
 * High-commitment explicit tracking actions (FOLLOW, BOOKMARK, SYLLABUS_READ) carry significantly higher
 * persistence and fidelity than transient exploratory clicks (VIEW, SEARCH).
 */
export const SIGNAL_STRENGTH_MULTIPLIER: Record<UserInteractionType, number> = {
  FOLLOW: 1.6,           // Active goal commitment: 4.0 * 1.6 = 6.4 base
  BOOKMARK: 1.4,         // High-intent shortlisting: 3.5 * 1.4 = 4.9 base
  SYLLABUS_READ: 1.6,    // Deep curriculum engagement: 5.0 * 1.6 = 8.0 base
  RESOURCE_ACCESS: 1.3,  // Specific material consumption: 4.0 * 1.3 = 5.2 base
  VIEW: 1.0,             // Passive guide exploration: 2.5 * 1.0 = 2.5 base
  SEARCH: 1.0            // Discovery keyword query: 1.5 * 1.0 = 1.5 base
};

/** Legacy default half-life (maintained for backwards compatibility) */
export const RECOMMENDATION_HALF_LIFE_HOURS = 48;

export function calculateTimeDecay(
  timestamp: number, 
  type?: UserInteractionType, 
  customHalfLife?: number,
  referenceTime?: number
): number {
  if (!timestamp || isNaN(timestamp) || timestamp <= 0) return 0.0;
  const now = referenceTime !== undefined ? referenceTime : Date.now();
  const elapsedHours = Math.max(0, (now - timestamp) / (1000 * 60 * 60));
  const halfLife = customHalfLife || (type && INTERACTION_HALF_LIVES_HOURS[type] ? INTERACTION_HALF_LIVES_HOURS[type] : RECOMMENDATION_HALF_LIFE_HOURS);
  return Math.pow(2, -elapsedHours / halfLife);
}

/**
 * Domain & Category similarity matrix between exams for transfer learning.
 * Computes cross-exam affinity based on Commission type, Administrative level, and Syllabus overlap.
 */
export function getExamAffinitySimilarity(examA: Exam, examB: Exam): number {
  if (examA.id === examB.id) return 1.0;

  let similarity = 0.0;

  // 1. Same Commission / Authority (e.g. APPSC Group 1 & APPSC Group 2 sister exams)
  if (examA.authorityName && examB.authorityName && examA.authorityName === examB.authorityName) {
    similarity += 0.35;
  }

  // 2. Category cluster alignment (e.g. Civil Services & State PSC)
  const isCivilServicesA = examA.categoryTag === 'CIVIL_SERVICES' || examA.categoryTag === 'STATE_PSC';
  const isCivilServicesB = examB.categoryTag === 'CIVIL_SERVICES' || examB.categoryTag === 'STATE_PSC';

  if (isCivilServicesA && isCivilServicesB) {
    if (examA.categoryTag === examB.categoryTag) {
      similarity += 0.50; // Same category, e.g. State PSC & State PSC
    } else {
      similarity += 0.40; // Civil Services & State PSC (e.g. UPSC CSE & APPSC Group 1)
    }
  }

  // 3. Career fields overlap
  const fieldsA = examA.careerFields || [];
  const fieldsB = examB.careerFields || [];
  const sharedFields = fieldsA.filter(f => fieldsB.includes(f));
  if (sharedFields.length > 0) {
    similarity += 0.15 * Math.min(2, sharedFields.length);
  }

  // 4. Educational requirement overlap (Graduation)
  if (examA.minimumQualification && examA.minimumQualification === examB.minimumQualification) {
    similarity += 0.05;
  }

  // 5. Aptitude CBT cluster (SSC CGL & IBPS PO)
  const isCbtSpeedA = examA.categoryTag === 'STAFF_SELECTION' || examA.categoryTag === 'BANKING';
  const isCbtSpeedB = examB.categoryTag === 'STAFF_SELECTION' || examB.categoryTag === 'BANKING';
  if (isCbtSpeedA && isCbtSpeedB) {
    similarity += 0.40;
  }

  return Math.min(1.0, Math.max(0.0, similarity));
}

/**
 * Computes personalized exam recommendations based on user interaction history
 * with time-decay and collaborative category transfer.
 */
export function computePersonalizedRecommendations(
  allExams: Exam[],
  interactions: UserInteractionEvent[],
  profile?: UserProfile,
  referenceTime?: number
): ExamRecommendation[] {
  if (!allExams || !Array.isArray(allExams) || allExams.length === 0) return [];

  // Map exam IDs to accumulators tracking direct, transferred, and profile components
  const examScores: Record<string, {
    directScore: number;
    transferScore: number;
    profileScore: number;
    totalScore: number;
    directHits: number;
    relatedHits: number;
    recentActions: string[];
    topSignal: string;
  }> = {};

  allExams.forEach(e => {
    examScores[e.id] = {
      directScore: 0,
      transferScore: 0,
      profileScore: 0,
      totalScore: 0,
      directHits: 0,
      relatedHits: 0,
      recentActions: [],
      topSignal: 'Discovery Baseline'
    };
  });

  const validInteractions = Array.isArray(interactions) ? interactions : [];
  const sortedInteractions = [...validInteractions]
    .filter(ev => ev && typeof ev === 'object' && ev.timestamp && !isNaN(ev.timestamp) && ev.timestamp > 0)
    .sort((a, b) => b.timestamp - a.timestamp);

  // 1. Process DIRECT behavioral interactions with time decay and commitment multipliers
  for (const event of sortedInteractions) {
    if (!event.type || !INTERACTION_WEIGHTS[event.type]) continue;
    const weight = INTERACTION_WEIGHTS[event.type] || 1.0;
    const decay = calculateTimeDecay(event.timestamp, event.type, undefined, referenceTime);
    if (isNaN(decay) || decay <= 0) continue;
    const signalStrength = SIGNAL_STRENGTH_MULTIPLIER[event.type] || 1.0;
    const eventScore = weight * decay * signalStrength;
    if (isNaN(eventScore) || eventScore <= 0) continue;

    // Check direct target exam
    let directTargetExam: Exam | undefined = undefined;
    if (event.examId) {
      directTargetExam = allExams.find(e => e.id === event.examId);
    } else if (event.targetType === 'EXAM') {
      directTargetExam = allExams.find(e => e.id === event.targetId);
    }

    if (directTargetExam) {
      const targetId = directTargetExam.id;
      const targetAcc = examScores[targetId];

      if (targetAcc) {
        targetAcc.directScore += eventScore;
        targetAcc.directHits++;

        let actionDesc = '';
        if (event.type === 'VIEW') actionDesc = `Viewed ${directTargetExam.title}`;
        else if (event.type === 'BOOKMARK') actionDesc = `Saved ${directTargetExam.title}`;
        else if (event.type === 'FOLLOW') actionDesc = `Tracking ${directTargetExam.title} in timeline`;
        else if (event.type === 'SYLLABUS_READ') actionDesc = `Read ${directTargetExam.title} syllabus`;
        else if (event.type === 'RESOURCE_ACCESS') actionDesc = `Explored ${directTargetExam.title} resources`;

        if (actionDesc && !targetAcc.recentActions.includes(actionDesc) && targetAcc.recentActions.length < 3) {
          targetAcc.recentActions.push(actionDesc);
        }
      }
    }

    // Check query matches if SEARCH
    if (event.type === 'SEARCH') {
      const q = (event.metadata?.query || event.targetId || '').toLowerCase().trim();
      for (const exam of allExams) {
        const titleMatch = exam.title.toLowerCase().includes(q) || exam.code.toLowerCase().includes(q);
        const authMatch = exam.authorityName.toLowerCase().includes(q);
        const civilMatch = (q.includes('civil') || q.includes('upsc') || q.includes('ias') || q.includes('appsc') || q.includes('psc') || q.includes('group 1') || q.includes('group 2')) &&
                           (exam.categoryTag === 'CIVIL_SERVICES' || exam.categoryTag === 'STATE_PSC');
        const sscMatch = (q.includes('ssc') || q.includes('cgl')) && exam.categoryTag === 'STAFF_SELECTION';
        const bankMatch = (q.includes('bank') || q.includes('ibps') || q.includes('po')) && exam.categoryTag === 'BANKING';

        if (titleMatch || authMatch || civilMatch || sscMatch || bankMatch) {
          const acc = examScores[exam.id];
          if (acc) {
            acc.directScore += eventScore;
            acc.directHits++;
            const actionText = `Searched "${event.targetId}"`;
            if (!acc.recentActions.includes(actionText) && acc.recentActions.length < 3) {
              acc.recentActions.push(actionText);
            }
          }
        }
      }
    }
  }

  // 2. Transferred Affinity pass with strict Hierarchy Enforcement:
  // DirectInterest > TransferredAffinity > ProfilePrior
  const maxDirectScore = Math.max(...Object.values(examScores).map(a => a.directScore), 0);
  // An un-interacted exam's transfer cannot exceed 80% of the active lead direct engagement
  const MAX_TRANSFER_CAP = maxDirectScore > 0 ? maxDirectScore * 0.80 : 0;

  for (const sourceExam of allExams) {
    const sourceAcc = examScores[sourceExam.id];
    if (!sourceAcc || sourceAcc.directScore <= 0) continue;

    for (const targetExam of allExams) {
      if (targetExam.id === sourceExam.id) continue;
      const affinity = getExamAffinitySimilarity(sourceExam, targetExam);
      if (affinity > 0.3) {
        // Damping factor 0.65 guarantees transferred interest remains subordinate to direct source
        const transferContribution = sourceAcc.directScore * affinity * 0.65;
        const targetAcc = examScores[targetExam.id];
        if (targetAcc) {
          targetAcc.transferScore += transferContribution;
          targetAcc.relatedHits++;

          let relatedReason = '';
          if (sourceExam.categoryTag === 'CIVIL_SERVICES' || sourceExam.categoryTag === 'STATE_PSC') {
            relatedReason = `Related to ${sourceExam.code.replace(/_/g, ' ')} (Civil & State Services)`;
          } else if (sourceExam.categoryTag === 'STAFF_SELECTION' || sourceExam.categoryTag === 'BANKING') {
            relatedReason = `Overlapping CBT syllabus with ${sourceExam.code.replace(/_/g, ' ')}`;
          }

          if (relatedReason && !targetAcc.recentActions.includes(relatedReason) && targetAcc.recentActions.length < 3) {
            targetAcc.recentActions.push(relatedReason);
          }
        }
      }
    }
  }

  // Cap transfer for exams without direct interaction so pure transfer never eclipses direct interest
  for (const exam of allExams) {
    const acc = examScores[exam.id];
    if (!acc) continue;
    if (MAX_TRANSFER_CAP > 0 && acc.directHits === 0) {
      acc.transferScore = Math.min(acc.transferScore, MAX_TRANSFER_CAP);
    }
  }

  // 3. Add profile prior (cold start fallback & gentle tiebreaker: 1.0 - 1.5 pts)
  for (const exam of allExams) {
    const acc = examScores[exam.id];
    if (!acc) continue;

    if (profile) {
      if (exam.minimumQualification === 'GRADUATION') {
        acc.profileScore += 1.5;
      }
      if (exam.isGoldenJourney) {
        acc.profileScore += 0.5;
      }
    }

    acc.totalScore = acc.directScore + acc.transferScore + acc.profileScore;
  }

  // 4. Normalise and sort recommendations
  // Normalization floor ensures faded/decayed micro-actions don't artificially blow up to 100%
  const activeDenominator = maxDirectScore > 0 ? Math.max(...Object.values(examScores).map(a => a.totalScore), 5.0) : Math.max(...Object.values(examScores).map(a => a.totalScore), 1.0);

  const recommendations: ExamRecommendation[] = allExams.map(exam => {
    const acc = examScores[exam.id] || { directScore: 0, transferScore: 0, profileScore: 0, totalScore: 0, directHits: 0, relatedHits: 0, recentActions: [], topSignal: '' };
    const normalisedScore = Math.min(100, Math.round((acc.totalScore / activeDenominator) * 100));

    let matchStrength: ExamRecommendation['matchStrength'] = 'EXPLORATORY';
    if (normalisedScore >= 70 && (acc.directScore >= 2.5 || acc.directHits >= 1)) matchStrength = 'STRONG';
    else if (normalisedScore >= 40 && (acc.directScore >= 1.0 || acc.transferScore >= 2.0)) matchStrength = 'MODERATE';

    const reasons: string[] = [];
    if (acc.recentActions.length > 0) {
      reasons.push(...acc.recentActions);
    }

    if (reasons.length === 0) {
      if (exam.categoryTag === 'CIVIL_SERVICES' || exam.categoryTag === 'STATE_PSC') {
        reasons.push('Premier Civil Services recruitment matching Graduate qualification');
      } else if (exam.categoryTag === 'STAFF_SELECTION') {
        reasons.push('High-volume Central Ministries recruitment with verified CBT curriculum');
      } else if (exam.categoryTag === 'BANKING') {
        reasons.push('Fast-track Public Sector Banking probationary officer examination');
      } else {
        reasons.push('Verified recruitment examination matching graduation eligibility');
      }
    }

    let primarySignal = 'Active Exploration';
    if (acc.directHits > 0 && acc.relatedHits > 0) primarySignal = 'Direct Engagement + Cluster Affinity';
    else if (acc.directHits > 0) primarySignal = 'Direct Candidate Action';
    else if (acc.relatedHits > 0) primarySignal = 'Transferred Cluster Affinity';
    else primarySignal = 'Academic Profile Baseline';

    return {
      exam,
      score: normalisedScore,
      reasons,
      matchStrength,
      primarySignal
    };
  });

  recommendations.sort((a, b) => {
    if (b.score !== a.score) return b.score - a.score;
    // Tie-breaker: direct engagement always outranks transferred engagement
    const accA = examScores[a.exam.id];
    const accB = examScores[b.exam.id];
    if (accB && accA && accB.directHits !== accA.directHits) {
      return accB.directHits - accA.directHits;
    }
    return 0;
  });

  return recommendations;
}

export const storageService = new StorageService();

/**
 * GovOS Live Source Research — thin client over the server's Tavily pipeline.
 * The API key never reaches the browser; every call goes through app.py, which
 * classifies results by domain and stores them for human review.
 */
async function researchOutcome<T>(res: Response): Promise<ResearchOutcome<T>> {
  let body: any = null;
  try {
    body = await res.json();
  } catch {
    body = null;
  }
  if (res.ok) {
    return { ok: true, data: body as T };
  }
  return {
    ok: false,
    error: (body && (body.detail || body.error)) || `Server returned HTTP ${res.status}`,
    setup: body && body.setup,
    notConfigured: res.status === 503 && !!(body && body.setup)
  };
}

export const researchService = {
  async getStatus(): Promise<ResearchStatus | null> {
    try {
      const res = await fetch('/api/research/status');
      if (res.ok) return await res.json();
    } catch {
      // server offline
    }
    return null;
  },

  async search(
    query: string,
    mode: ResearchMode = 'OFFICIAL',
    examId?: string,
    maxResults: number = 8
  ): Promise<ResearchOutcome<ResearchSearchResult>> {
    try {
      const res = await fetch('/api/research/search', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query, mode, exam_id: examId, max_results: maxResults })
      });
      return await researchOutcome<ResearchSearchResult>(res);
    } catch (e: any) {
      return { ok: false, error: `GovOS server unreachable: ${e?.message || 'network error'}` };
    }
  },

  async extract(urls: string[], findingId?: number): Promise<ResearchOutcome<ResearchExtractResult[]>> {
    try {
      const res = await fetch('/api/research/extract', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ urls, finding_id: findingId })
      });
      const outcome = await researchOutcome<{ results: ResearchExtractResult[] }>(res);
      if (outcome.ok) return { ok: true, data: outcome.data.results || [] };
      return outcome;
    } catch (e: any) {
      return { ok: false, error: `GovOS server unreachable: ${e?.message || 'network error'}` };
    }
  },

  async history(limit: number = 15): Promise<ResearchRun[]> {
    try {
      const res = await fetch(`/api/research/history?limit=${limit}`);
      if (res.ok) {
        const data = await res.json();
        if (Array.isArray(data.runs)) return data.runs;
      }
    } catch {
      // server offline
    }
    return [];
  },

  async getFinding(id: number): Promise<ResearchFinding | null> {
    try {
      const res = await fetch(`/api/research/findings/${id}`);
      if (res.ok) return await res.json();
    } catch {
      // server offline
    }
    return null;
  },

  async setFindingStatus(id: number, status: ResearchReviewStatus): Promise<boolean> {
    try {
      const res = await fetch(`/api/research/findings/${id}/status`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ status })
      });
      return res.ok;
    } catch {
      return false;
    }
  }
};

// ==========================================================================
// Live resources — the Resource Library's server-refreshed parts
// ==========================================================================
export const resourceLiveService = {
  /** Register the library's links for scheduled checking; returns what the server knows now. */
  async healthSync(urls: string[]): Promise<ResourceHealthSync | null> {
    try {
      const res = await fetch('/api/resources/health/sync', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ urls })
      });
      if (res.ok) return await res.json();
    } catch {
      // server offline: the library shows its last static verification dates instead
    }
    return null;
  },

  /** Force an immediate sweep; results are stored so the next visitor sees them too. */
  async recheck(urls: string[]): Promise<ResourceLinkCheck[]> {
    try {
      const res = await fetch('/api/resources/health/recheck', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ urls })
      });
      if (res.ok) {
        const data = await res.json();
        if (Array.isArray(data.results)) return data.results;
      }
    } catch {
      // caller shows "could not verify"
    }
    return [];
  },

  async sscNotices(scope: 'cgl' | 'all' = 'cgl', limit: number = 8): Promise<SscNoticeFeed | null> {
    try {
      const res = await fetch(`/api/resources/live/ssc-notices?scope=${scope}&limit=${limit}`);
      if (res.ok) return await res.json();
    } catch {
      // server offline
    }
    return null;
  },

  async channelUploads(channelIds: string[]): Promise<Record<string, ChannelUploadFeed>> {
    if (channelIds.length === 0) return {};
    try {
      const res = await fetch(`/api/resources/live/channel-uploads?ids=${encodeURIComponent(channelIds.join(','))}`);
      if (res.ok) {
        const data = await res.json();
        return data.channels || {};
      }
    } catch {
      // server offline
    }
    return {};
  },

  async additions(): Promise<ResourceAddition[]> {
    try {
      const res = await fetch('/api/resources/additions');
      if (res.ok) {
        const data = await res.json();
        if (Array.isArray(data.additions)) return data.additions;
      }
    } catch {
      // server offline
    }
    return [];
  },

  async addResource(payload: { title: string; url: string; subject?: string; resourceFormat?: string; author?: string; description?: string; findingId?: number; addedFrom?: string }): Promise<ResourceAddition | null> {
    try {
      const res = await fetch('/api/resources/additions', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });
      if (res.ok) {
        const data = await res.json();
        return data.addition || null;
      }
    } catch {
      // server offline
    }
    return null;
  },

  async retireResource(id: string): Promise<boolean> {
    try {
      const res = await fetch(`/api/resources/additions/${encodeURIComponent(id)}/retire`, { method: 'POST' });
      return res.ok;
    } catch {
      return false;
    }
  },

  async status(): Promise<LiveResourceStatus | null> {
    try {
      const res = await fetch('/api/resources/live/status');
      if (res.ok) return await res.json();
    } catch {
      // server offline
    }
    return null;
  }
};
