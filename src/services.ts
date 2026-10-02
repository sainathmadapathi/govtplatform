// GovOS services: age/profile maths, eligibility engine, dual-persistence storage.

import type { ImportantDate } from './types';

/**
 * A date as the authority stated it. `displayWhen` is the printed form where the notice gave a
 * month or a range; otherwise the day, and the time only where one was read. A reader writes
 * "00:00:00" when the notice printed a date and no time, so that value is never shown: it would
 * state a precision the source does not have.
 */
export function statedWhen(d: Pick<ImportantDate, 'dateTimeStr' | 'displayWhen'>, withTime = false): string {
  if (d.displayWhen) return d.displayWhen;
  const [day, time = ''] = (d.dateTimeStr || '').split(' ');
  return withTime && time && !/^00:00(?::00)?$/.test(time) ? `${day} ${time}` : day;
}

import {
  ClaudeHealth,
  ClaudeJob,
  ClaudeJobTicket,
  ClaudeOutcome,
  ResourceLinkCheck,
  ResearchExtractResult,
  ResearchFact,
  ResearchFactStatus,
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
  DataProvenance,
  SyllabusRevision,
  SyllabusRevisionTopic,
  DiscoveredSources,
  SyllabusTopic,
  SyllabusWatch,
  ResourceHealthSync,
  SscNoticeFeed,
  ExamCategoryTag,
  ExamRecommendation,
  UserInteractionEvent,
  UserInteractionType,
  CandidateStage,
  ChatChannel,
  ChatContext,
  ConversationTurn,
  MultiTierResultEntry,
  AgeRelaxationEntry,
  ExamFactOverlay,
  ExamFactOverlayKind,
  ExamOverlayScope,
  DiscoveryProfile,
  DiscoveryProfileField,
  DiscoveryRule,
  DiscoveryReason,
  DiscoveryPostResult,
  DiscoveryPostVerdict,
  DiscoveryExamResult,
  DiscoveryVerdict,
  DiscoveryResult
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
/** No default reference date: an exam that states no crucial date has no age to reckon. */
export function calculateAge(dateOfBirth: string, referenceDate: string): number {
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
export function calculateDetailedAge(dateOfBirth: string, referenceDate: string): DetailedAge {
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
/**
 * The words authorities use for the categories a candidate can pick in their profile.
 *
 * This table supplies **no values**. It exists only so that the code a candidate selected
 * can be matched against the wording their authority printed — "SC" against "Scheduled
 * Castes". Every number comes from the exam's own published relaxation, or there is none.
 */
const CATEGORY_WORDINGS: Record<string, string[]> = {
  OBC: ['obc', 'other backward class', 'other backward classes', 'non-creamy layer'],
  SC: ['sc', 'sc/st', 'scheduled caste', 'scheduled castes'],
  ST: ['st', 'sc/st', 'scheduled tribe', 'scheduled tribes'],
  PwBD: ['pwbd', 'pwd', 'person with benchmark disability', 'persons with benchmark disabilities'],
  EWS: ['ews', 'economically weaker section', 'economically weaker sections'],
  GENERAL: ['general', 'unreserved', 'ur']
};

/**
 * The relaxation this exam published for this category, or null.
 *
 * Null means the exam's record holds no such rule, and a caller must say so rather than
 * substituting a figure. This replaced a function that returned OBC +3 / SC,ST +5 /
 * PwBD +10 for every exam in the country with no source at all.
 */
export function findAgeRelaxation(
  exam: Exam | null | undefined,
  category: string,
  postId?: string
): AgeRelaxationEntry | null {
  const published = exam?.ageRelaxations;
  if (!published || published.length === 0) return null;
  const wordings = CATEGORY_WORDINGS[category] || [category.toLowerCase()];
  const matches = published.filter(entry => {
    const label = entry.category.toLowerCase();
    if (!wordings.some(w => label === w || label.includes(w))) return false;
    if (entry.appliesToPostId && postId && entry.appliesToPostId !== postId) return false;
    return true;
  });
  // A post-specific rule is the more precise statement where the authority made one.
  return matches.find(m => m.appliesToPostId && m.appliesToPostId === postId)
    || matches.find(m => !m.appliesToPostId)
    || matches[0]
    || null;
}

/**
 * Years to add to this exam's upper age limit for this candidate, from the exam's own
 * notice. Zero when the authority published nothing — callers must not describe that as a
 * relaxation of zero, only as an absence, which is what the reasons below do.
 */
export function getCategoryAgeRelaxation(
  exam: Exam | null | undefined,
  category: string,
  postId?: string
): number {
  const entry = findAgeRelaxation(exam, category, postId);
  // Only a VERIFIED figure is added to a limit. A figure the notice qualifies ("up to",
  // "& length of service") or a rule stated in words is shown, never computed with.
  if (!entry || entry.status !== 'VERIFIED') return 0;
  return entry.years ?? 0;
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
  /** The exam's own crucial date. '' when the record states none: age is then not evaluated. */
  crucialDate: string,
  /** The exam whose published rules govern this verdict. Without it there is no relaxation. */
  exam?: Exam | null
): PostVerdict {
  const age = crucialDate ? calculateAge(profile.dateOfBirth, crucialDate) : 0;
  const relaxationEntry = findAgeRelaxation(exam, profile.category, post.id);
  const relaxation = getCategoryAgeRelaxation(exam, profile.category, post.id);
  const maxPermissibleAge = post.maxAge + relaxation;
  const userDegreeNorm = normalizeDegree(profile.degree);
  const isBachelor = userDegreeNorm.includes('bachelor') || userDegreeNorm.includes('degree');

  let ageStatus: 'OK' | 'EXCEEDED' | 'UNDERAGE' | 'UNKNOWN' = 'OK';
  let qualStatus: 'OK' | 'DISQUALIFIED' = 'OK';
  let physicalStatus: 'OK' | 'RESTRICTED' = 'OK';
  const reasons: string[] = [];

  // 1. Age Verification. A post with no published upper limit (0), or an exam with no date to
  // reckon age on, is not evaluated: a limit of zero would declare every candidate over-age.
  if (!crucialDate || !(post.maxAge > 0)) {
    ageStatus = 'UNKNOWN';
    reasons.push(!crucialDate
      ? `Age not evaluated: the record states no date on which age is reckoned`
      : `Age not evaluated: the record carries no upper age limit for ${post.postName}`);
  } else if (age < post.minAge) {
    ageStatus = 'UNDERAGE';
    reasons.push(`Underage: ${age} yrs is below minimum requirement of ${post.minAge} yrs`);
  } else if (age > maxPermissibleAge) {
    ageStatus = 'EXCEEDED';
    reasons.push(
      `Age Exceeded: ${age} yrs exceeds permissible limit of ${maxPermissibleAge} yrs ` +
      (relaxationEntry
        ? `(${post.maxAge} base + ${relaxation} yrs ${profile.category} relaxation, as published in ${relaxationEntry.provenance.documentTitle})`
        : `(${post.maxAge} as published; this exam's record carries no age relaxation for ${profile.category}, so none was applied)`)
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
      // SSC CGL 2026 notice, Para 8.3.1: a Bachelor degree in any of these subjects.
      const branch = (profile.branch || '').toLowerCase();
      const SI_SUBJECTS = ['stat', 'math', 'economic', 'demograph', 'population', 'operation research', 'information technology',
        'computer', 'data science', 'artificial intelligence'];
      const hasQualifyingDegree = profile.statisticsInDegree === true || SI_SUBJECTS.some(sub => branch.includes(sub));
      if (!hasQualifyingDegree) {
        qualStatus = 'DISQUALIFIED';
        reasons.push(`Statistical Investigator Gr II: requires a Bachelor degree in Statistics, Mathematics, Economics, Demography, Population Studies, Operation Research, IT, Computer Science/Engineering/Technology/Application, Data Science or AI (Para 8.3.1)`);
      } else {
        reasons.push(`Statistical Investigator Gr II: degree subject is among those listed in Para 8.3.1`);
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
    officialClause: post.provenance?.clauseNumber || 'the notice'
  };
}

export function evaluateEligibility(exam: Exam, profile: UserProfile): EligibilityDiagnostic {
  // The exam's own date, or none. There is no fallback date: another exam's cut-off date
  // would compute an age this exam never asked about.
  const crucialDate = exam.crucialEligibilityDate || '';
  const detailedAge = crucialDate
    ? calculateDetailedAge(profile.dateOfBirth, crucialDate)
    : { years: 0, months: 0, days: 0, formatted: 'not computed' };
  const relaxationEntry = findAgeRelaxation(exam, profile.category);
  const relaxation = getCategoryAgeRelaxation(exam, profile.category);
  const userAge = detailedAge.years;

  // The clauses cited must be this exam's. They used to name SSC's notification sections
  // for every exam in the register, so a candidate looking at a state commission's exam was
  // shown an SSC clause number as the basis of their own verdict.
  const legalClauses: string[] = [
    crucialDate
      ? `${exam.title}: age is reckoned as on ${crucialDate}`
      : `${exam.title}: the record states no date on which age is reckoned, so age is not evaluated.`,
    relaxationEntry
      ? `Age relaxation for ${profile.category}: ${relaxationEntry.years !== undefined ? `+${relaxationEntry.years} years` : relaxationEntry.maximumAge !== undefined ? `upper limit ${relaxationEntry.maximumAge} years` : 'stated without a figure'} — ${relaxationEntry.provenance.documentTitle}`
      : `No age relaxation for ${profile.category} is recorded from ${exam.authorityName}'s own documents, so none has been applied.`,
    ...(exam.eligibilityHighlights || [])
      .filter(card => /qualification|degree|education/i.test(card.title))
      .map(card => `${card.title}: ${card.body}`)
  ];

  const postVerdicts: PostVerdict[] = exam.posts.map(post =>
    evaluatePostEligibility(post, profile, crucialDate, exam)
  );

  const eligibleCount = postVerdicts.filter(p => p.eligible).length;
  const totalCount = postVerdicts.length;
  const unknownCount = postVerdicts.filter(p => p.ageStatus === 'UNKNOWN').length;
  const evaluableCount = totalCount - unknownCount;

  let status: EligibilityDiagnostic['status'] = 'INELIGIBLE';
  let plainEnglishExplanation = '';

  // Zero posts, or no post whose rules the record carries, is not "eligible for all of them":
  // an empty set satisfies "every post" trivially, and that used to read as ELIGIBLE.
  if (totalCount === 0 || evaluableCount === 0) {
    status = 'NOT_EVALUABLE';
    plainEnglishExplanation = totalCount === 0
      ? `The ${exam.title} record carries no posts yet, so eligibility cannot be evaluated. Read the notice's own eligibility clauses.`
      : !crucialDate
        ? `The ${exam.title} record states no date on which age is reckoned, so eligibility cannot be evaluated.`
        : `None of the ${totalCount} posts on record carries a published age limit, so eligibility cannot be evaluated.`;
  } else if (eligibleCount === totalCount) {
    status = 'ELIGIBLE';
    plainEnglishExplanation = `On the rules in the ${exam.title} record you meet the age and qualification conditions for all ${totalCount} posts, with your age of ${detailedAge.formatted} as on ${crucialDate}.`;
  } else if (eligibleCount > 0 || unknownCount > 0) {
    status = eligibleCount > 0 ? 'CONDITIONAL' : 'NOT_EVALUABLE';
    plainEnglishExplanation = eligibleCount > 0
      ? `You meet the conditions for ${eligibleCount} of ${totalCount} posts in the ${exam.title} record.${unknownCount ? ` ${unknownCount} post(s) have no published age limit in the record and were not evaluated.` : ' The others set age limits or subject requirements you do not meet — see each post below.'}`
      : `You do not meet the published conditions for the ${evaluableCount} post(s) whose rules the record carries; ${unknownCount} other post(s) have no published age limit and were not evaluated.`;
  } else {
    status = 'INELIGIBLE';
    const minAge = Math.min(...exam.posts.map(p => p.minAge).filter(a => a > 0));
    plainEnglishExplanation = Number.isFinite(minAge) && userAge < minAge
      ? `You are ${userAge} years old as on ${crucialDate}; the youngest minimum age for any ${exam.title} post on record is ${minAge}.`
      : `Your age (${userAge} years as on ${crucialDate}) or qualification does not meet the published conditions for any ${exam.title} post on record${relaxation ? `, after the ${profile.category} relaxation of +${relaxation} years` : ''}.`;
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
// Exam-day checklist verification status (Section 12).
// A pure projection over the exam's own authored `examDayChecklist`, so the UI can decide
// honestly what to show and never present generic content as an official, exam-specific
// protocol. It reads only the passed exam — no cross-exam data, no hardcoded exam branch.
//   NONE       — the authority's exam-day instructions have not been extracted for this exam.
//   UNVERIFIED — items are authored but not (all) backed by an OFFICIALLY_VERIFIED source.
//   VERIFIED   — every item carries a provenance verified as OFFICIALLY_VERIFIED.
// ==========================================================================
export type ExamDayChecklistStatus = 'VERIFIED' | 'UNVERIFIED' | 'NONE';

export function examDayChecklistStatus(exam: Exam): ExamDayChecklistStatus {
  const items = exam.examDayChecklist ?? [];
  if (items.length === 0) return 'NONE';
  const allVerified = items.every(
    (i) => i.provenance?.verificationLevel === 'OFFICIALLY_VERIFIED'
  );
  return allVerified ? 'VERIFIED' : 'UNVERIFIED';
}


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

/**
 * Exam ids that were written by an earlier build and mean a current exam. This is a record of
 * a *known* association, not a guess: the Application Practice Simulator only ever ran for SSC
 * CGL and wrote a short id. An attempt whose exam is genuinely unknown is never mapped here —
 * it simply fails to match and is left out of every exam's history.
 */
const LEGACY_ATTEMPT_EXAM_IDS: Record<string, string> = {
  'ssc-cgl-2026': 'exam-ssc-cgl-2026'
};

/** The id an attempt should be matched on, after legacy ids are resolved. */
export const canonicalExamId = (examId: string | undefined): string =>
  !examId ? '' : (LEGACY_ATTEMPT_EXAM_IDS[examId] || examId);

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
  CURRENT_EXAM: 'govos_current_exam_id',
  TARGET_POST: 'govos_target_post_id',
  DAILY_HOURS: 'govos_daily_study_hours',
  RESULT_ENTRY: 'govos_result_entry',
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
  /** The post the candidate chose, or '' — never an invented default. */
  getTargetPost(): string {
    try {
      return localStorage.getItem(STORAGE_KEYS.TARGET_POST) || '';
    } catch {
      return '';
    }
  }

  /**
   * The exam the candidate is currently working inside. Every exam-scoped feature —
   * resources, practice, mocks, timeline, application, both chats — is handed this exam,
   * so "when is it?" means this exam and nothing else. Empty until they open one.
   */
  getCurrentExamId(): string {
    try {
      return localStorage.getItem(STORAGE_KEYS.CURRENT_EXAM) || '';
    } catch {
      return '';
    }
  }

  setCurrentExamId(examId: string): void {
    try {
      localStorage.setItem(STORAGE_KEYS.CURRENT_EXAM, examId);
    } catch (e) {
      console.warn('LocalStorage save error:', e);
    }
  }

  /** The marks and category the candidate entered or confirmed from their scorecard, isolated per exam. */
  getResultEntry(examId?: string): MultiTierResultEntry | null {
    try {
      const key = examId ? `${STORAGE_KEYS.RESULT_ENTRY}_${examId}` : STORAGE_KEYS.RESULT_ENTRY;
      const raw = localStorage.getItem(key);
      return raw ? JSON.parse(raw) : null;
    } catch {
      return null;
    }
  }

  setResultEntry(entry: MultiTierResultEntry | null, examId?: string): void {
    try {
      const key = examId ? `${STORAGE_KEYS.RESULT_ENTRY}_${examId}` : STORAGE_KEYS.RESULT_ENTRY;
      if (entry) localStorage.setItem(key, JSON.stringify(entry));
      else localStorage.removeItem(key);
    } catch (e) {
      console.warn('LocalStorage save error:', e);
    }
  }

  /**
   * Send a scorecard to the server to be read. The file is parsed in memory and never
   * stored — GovOS keeps no candidate documents.
   */
  async parseResultDocument(file: File, examId?: string): Promise<{
    ok: boolean; reason?: string; message?: string; confidence?: string; method?: 'TEXT_LAYER' | 'OCR';
    fields?: {
      marks?: number;
      marksCandidates?: number[];
      category?: string;
      rollNumber?: string;
      candidateName?: string;
      examYear?: number;
      declared?: string;
      marksLabel?: string;
      marksRaw?: string;
      examType?: 'SSC_CGL' | 'UPSC_CSE' | 'IBPS_PO' | 'APPSC' | 'GENERIC';
      // SSC specific
      tier1Marks?: number;
      tier2Marks?: number;
      computerKnowledgeMarks?: number;
      destMistakesPercent?: number;
      allocatedPost?: string;
      // UPSC specific
      upscPrelimsGs1Marks?: number;
      upscPrelimsCsatMarks?: number;
      upscMainsWrittenMarks?: number;
      upscInterviewMarks?: number;
      upscFinalTotalMarks?: number;
      allocatedService?: string;
      // IBPS specific
      ibpsPrelimsMarks?: number;
      ibpsMainsMarks?: number;
      ibpsInterviewMarks?: number;
      ibpsFinalScore?: number;
    };
    notes?: string[]; excerpt?: string;
  }> {
    try {
      const buffer = await file.arrayBuffer();
      let binary = '';
      const bytes = new Uint8Array(buffer);
      for (let i = 0; i < bytes.length; i += 8192) {
        binary += String.fromCharCode(...bytes.subarray(i, i + 8192));
      }
      const res = await fetch('/api/results/parse', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ filename: file.name, contentBase64: btoa(binary), examId: examId || '' })
      });
      return await res.json();
    } catch (e: any) {
      return { ok: false, reason: 'SERVER_UNREACHABLE', message: `Could not reach the GovOS server to read the file (${e?.message || 'network error'}). Type your marks in instead.` };
    }
  }

  hasTargetPost(): boolean {
    return this.getTargetPost() !== '';
  }

  /** Hours a day the candidate says they can study. Null until they tell us. */
  getDailyStudyHours(): number | null {
    try {
      const saved = localStorage.getItem(STORAGE_KEYS.DAILY_HOURS);
      const parsed = saved ? parseFloat(saved) : Number.NaN;
      return Number.isFinite(parsed) && parsed > 0 ? parsed : null;
    } catch {
      return null;
    }
  }

  setDailyStudyHours(hours: number): void {
    try {
      localStorage.setItem(STORAGE_KEYS.DAILY_HOURS, String(hours));
    } catch (e) {
      console.warn('LocalStorage save error:', e);
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
  /**
   * Practice history is per exam. `getMockAttempts(examId)` returns only that exam's attempts;
   * calling it with no id returns everything and is for the sync/export paths alone, never for
   * anything a candidate sees — an exam must never show another exam's scores.
   *
   * The filter is defensive on purpose: a record whose `exam_id` does not match is dropped and
   * logged rather than shown or quietly re-labelled, because a wrong exam association is worse
   * than a missing row.
   */
  getMockAttempts(examId?: string): MockAttemptRecord[] {
    let all: MockAttemptRecord[] = [];
    try {
      const raw = localStorage.getItem(STORAGE_KEYS.MOCK_ATTEMPTS);
      if (raw) all = JSON.parse(raw);
    } catch (e) {
      console.warn('LocalStorage mock parse error:', e);
    }
    if (!examId) return all;
    const wanted = canonicalExamId(examId);
    const mine = all.filter(a => canonicalExamId(a.exam_id) === wanted);
    const strays = all.length - mine.length;
    if (strays > 0) {
      console.debug(`[GovOS] practice history: ${strays} attempt(s) belong to another exam and were not shown for ${examId}.`);
    }
    return mine;
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

  async loadMockAttemptsFromSQLite(examId?: string): Promise<MockAttemptRecord[]> {
    try {
      // Scoped in the query, not in the UI: the server must not hand back another exam's rows.
      const qs = examId ? `?exam_id=${encodeURIComponent(canonicalExamId(examId))}` : '';
      const res = await fetch(`/api/sqlite/mock-attempts${qs}`);
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
            // The store holds every exam; the caller only ever receives the exam it asked for.
            return this.getMockAttempts(examId);
          }
        }
      }
    } catch {
      // Offline fallback
    }
    return this.getMockAttempts(examId);
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
              message: `Only 7 days remaining until online application closes on ${statedWhen(d, true)}. Complete your fee payment and submit before the final rush.`,
              channelsDelivered: channels,
              actionType: 'EXAM_DETAIL',
              actionPayload: { section: 4 },
              priority: 'HIGH',
              createdAt: new Date(Date.parse(d.dateTimeStr.replace(' ', 'T')) - 7 * 864e5).toISOString().slice(0, 19).replace('T', ' '),
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
              message: `Application closes in 3 days (${statedWhen(d, true)}). Check that your live photograph, running signature, and category certificates are compliant.`,
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
              message: `The application portal closes tomorrow (${statedWhen(d, true)})! Confirm payment status and download your application acknowledgment receipt immediately.`,
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
              createdAt: `${d.dateTimeStr.slice(0, 10)} 00:00:00`,
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
            message: `The official application correction facility is active from ${statedWhen(d, true)}. Review your uploaded photograph, post preferences, and exam center choices.`,
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
            message: `Tier 1 Exam City Intimation & e-Admit Card released on ${statedWhen(d, true)}. Check your examination date, shift time, and exam center address.`,
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
            message: d.displayWhen
              // Printed without a day: say so, and do not name one.
              ? `${d.label}: ${d.displayWhen}${d.isTentative ? ' (tentative)' : ''}. No exact date has been announced yet; GovOS will show it when ${exam.authorityName} publishes it.`
              : `The Computer Based Test commences on ${statedWhen(d, true)}. Remember to carry your original Photo ID, two passport photos, and printed Admit Card.`,
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
            message: `Response sheet and tentative answer keys are available on ${statedWhen(d, true)}. Calculate your score and raise challenges if questions contain errors.`,
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
            message: `Official shortlisted roll numbers and category cut-off marks announced on ${statedWhen(d, true)}. Check your merit status for the next stage!`,
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
 * GovOS Live Source Research — thin client over the server's Claude discovery pipeline.
 *
 * Claude runs only on the server: the installed Claude CLI, behind a persistent job queue. The
 * browser never sees a prompt, a command line, an account or a key. A discovery run is a job —
 * Claude proposes candidate sources, the server checks every one — and its results are stored for
 * human review. Trust Panel operations carry the admin token when the server demands one (see
 * CLAUDE_CLI_INTEGRATION.md; that guard is local protection, not user authentication).
 */
const ADMIN_TOKEN_KEY = 'govos_admin_token';

/** The Trust Panel's admin token, kept for this browser tab only (sessionStorage), never persisted. */
export const adminToken = {
  get(): string {
    try { return sessionStorage.getItem(ADMIN_TOKEN_KEY) || ''; } catch { return ''; }
  },
  set(value: string): void {
    try {
      if (value) sessionStorage.setItem(ADMIN_TOKEN_KEY, value);
      else sessionStorage.removeItem(ADMIN_TOKEN_KEY);
    } catch {
      // storage blocked: the token simply is not remembered
    }
  }
};

/** Headers for a Trust Panel operation: the admin token, when one has been entered. */
export const adminHeaders = (): Record<string, string> => {
  const token = adminToken.get();
  return token ? { 'X-GovOS-Admin-Token': token } : {};
};

const jsonHeaders = (): Record<string, string> => ({ 'Content-Type': 'application/json', ...adminHeaders() });

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
  const refused = body && body.error === 'ADMIN_REQUIRED';
  return {
    ok: false,
    error: refused
      ? `${body.message || 'Admin access is required'}. ${body.hint || ''}`.trim()
      : (body && (body.message || body.detail || body.error)) || `Server returned HTTP ${res.status}`,
    setup: body && body.setup,
    claudeUnavailable: res.status === 503 && !!(body && body.error === 'CLAUDE_UNAVAILABLE'),
    status: body && body.status
  };
}

const NETWORK_ERROR = (e: any) => `GovOS server unreachable: ${e?.message || 'network error'}`;

let _healthCache: { at: number; value: ClaudeHealth | null } | null = null;

const isTerminal = (status: string) => status === 'SUCCEEDED' || status === 'FAILED' || status === 'CANCELLED';

/**
 * Claude jobs: health, polling, cancel, retry, and the two candidate-facing operations. Every call
 * swallows network errors into an `ok: false` outcome, so a feature that depends on Claude can
 * always fall back to the deterministic one.
 */
export const claudeService = {
  async health(): Promise<ClaudeHealth | null> {
    try {
      const res = await fetch('/api/claude/health');
      if (res.ok) return await res.json();
    } catch {
      // server offline
    }
    return null;
  },

  /** `health()`, remembered for `maxAgeMs`, so a chat that asks before every unplaced question does not poll. */
  async healthCached(maxAgeMs = 30_000): Promise<ClaudeHealth | null> {
    if (_healthCache && Date.now() - _healthCache.at < maxAgeMs) return _healthCache.value;
    const value = await claudeService.health();
    _healthCache = { at: Date.now(), value };
    return value;
  },

  async getJob<R = any>(jobId: string, token?: string): Promise<ClaudeJob<R> | null> {
    try {
      const res = await fetch(`/api/claude/jobs/${encodeURIComponent(jobId)}`, {
        headers: { ...adminHeaders(), ...(token ? { 'X-GovOS-Job-Token': token } : {}) }
      });
      if (res.ok) return await res.json();
    } catch {
      // server offline
    }
    return null;
  },

  /**
   * Poll a job until it finishes. Gives up (ok: false, fallback: true) after `timeoutMs` so a slow
   * Claude never blocks a candidate: the caller shows its deterministic answer instead. The job is
   * left running on the server unless the caller cancels it.
   */
  async waitForJob<R = any>(jobId: string, opts: {
    token?: string; intervalMs?: number; timeoutMs?: number; signal?: AbortSignal; onUpdate?: (job: ClaudeJob<R>) => void;
  } = {}): Promise<ClaudeOutcome<ClaudeJob<R>>> {
    const interval = opts.intervalMs ?? 1200;
    const deadline = Date.now() + (opts.timeoutMs ?? 120_000);
    while (Date.now() < deadline) {
      if (opts.signal?.aborted) return { ok: false, error: 'Stopped waiting.', status: 'ABORTED' };
      const job = await claudeService.getJob<R>(jobId, opts.token);
      if (job) {
        opts.onUpdate?.(job);
        if (isTerminal(job.status)) return { ok: true, data: job };
      }
      await new Promise(resolve => setTimeout(resolve, interval));
    }
    return { ok: false, error: 'Claude is taking too long to answer.', status: 'TIMEOUT', fallback: true };
  },

  async cancel(jobId: string, token?: string): Promise<ClaudeJob | null> {
    try {
      const res = await fetch(`/api/claude/jobs/${encodeURIComponent(jobId)}/cancel`, {
        method: 'POST',
        headers: { ...adminHeaders(), ...(token ? { 'X-GovOS-Job-Token': token } : {}) }
      });
      if (res.ok) return await res.json();
    } catch {
      // server offline
    }
    return null;
  },

  async retry(jobId: string): Promise<ClaudeOutcome<ClaudeJobTicket>> {
    return claudeService._post(`/api/claude/jobs/${encodeURIComponent(jobId)}/retry`, {});
  },

  /** Recent jobs, newest first, with a count per status. Admin only. */
  async listJobs(limit = 30): Promise<{ jobs: ClaudeJob[]; counts: Record<string, number> } | null> {
    try {
      const res = await fetch(`/api/claude/jobs?limit=${limit}`, { headers: adminHeaders() });
      if (res.ok) return await res.json();
    } catch {
      // server offline
    }
    return null;
  },

  /** Queue a question about ONE exam. The server builds the facts Claude may use; the answer is checked against them. */
  async ask(examId: string, question: string, history: { role: 'user' | 'assistant'; text: string }[] = []): Promise<ClaudeOutcome<ClaudeJobTicket>> {
    return claudeService._post('/api/claude/ask', { examId, question, history });
  },

  /** Queue practice questions on one topic of an exam's verified syllabus. */
  async practice(examId: string, topic: string, count = 3, difficulty: 'EASY' | 'MEDIUM' | 'HARD' = 'MEDIUM'): Promise<ClaudeOutcome<ClaudeJobTicket>> {
    return claudeService._post('/api/claude/practice', { examId, topic, count, difficulty });
  },

  async _post(url: string, body: unknown): Promise<ClaudeOutcome<ClaudeJobTicket>> {
    try {
      const res = await fetch(url, { method: 'POST', headers: jsonHeaders(), body: JSON.stringify(body) });
      let data: any = null;
      try { data = await res.json(); } catch { data = null; }
      if (res.ok) return { ok: true, data: data as ClaudeJobTicket };
      return {
        ok: false,
        error: (data && (data.message || data.error)) || `Server returned HTTP ${res.status}`,
        status: data && data.status,
        fallback: !!(data && data.fallback) || res.status === 503 || res.status === 429,
        retryAfter: data && data.retryAfter
      };
    } catch (e: any) {
      return { ok: false, error: NETWORK_ERROR(e), fallback: true };
    }
  }
};

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

  /** Queue a discovery job. Claude proposes sources; the server checks each one. Admin only. */
  async startSearch(
    query: string,
    mode: ResearchMode = 'OFFICIAL',
    examId?: string,
    maxResults: number = 8
  ): Promise<ResearchOutcome<ClaudeJobTicket>> {
    try {
      const res = await fetch('/api/research/search', {
        method: 'POST',
        headers: jsonHeaders(),
        body: JSON.stringify({ query, mode, exam_id: examId, max_results: maxResults })
      });
      return await researchOutcome<ClaudeJobTicket>(res);
    } catch (e: any) {
      return { ok: false, error: NETWORK_ERROR(e) };
    }
  },

  /** A stored run and its findings (what a finished discovery job produced). */
  async getRun(runId: number): Promise<ResearchSearchResult | null> {
    try {
      const res = await fetch(`/api/research/runs/${runId}`);
      if (!res.ok) return null;
      const run = (await res.json()).run as ResearchRun;
      return { runId: run.id, query: run.query, mode: run.mode, examId: run.examId, engine: run.engine, jobId: run.jobId, results: run.findings };
    } catch {
      return null;
    }
  },

  /** Fetch and store a finding's page text, deterministically, on the server. No Claude call. */
  async extract(findingId: number): Promise<ResearchOutcome<ResearchExtractResult[]>> {
    try {
      const res = await fetch('/api/research/extract', {
        method: 'POST',
        headers: jsonHeaders(),
        body: JSON.stringify({ finding_id: findingId })
      });
      const outcome = await researchOutcome<{ results: ResearchExtractResult[] }>(res);
      if (outcome.ok) return { ok: true, data: outcome.data.results || [] };
      return outcome;
    } catch (e: any) {
      return { ok: false, error: NETWORK_ERROR(e) };
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
        headers: jsonHeaders(),
        body: JSON.stringify({ status })
      });
      return res.ok;
    } catch {
      return false;
    }
  },

  // --- Field-level validation layer (RESEARCH_VALIDATION_DESIGN.md) ---
  // These sit beside the existing finding review and never publish. The rule-based reader runs
  // immediately; reading with Claude is a job whose proposals are kept only where their quotation
  // is printed in the page text the server fetched.

  /** Extract + validate typed facts, rule-based, from findings already stored for a run or one finding. */
  async extractFacts(target: { runId?: number; findingId?: number }): Promise<ResearchFact[]> {
    try {
      const res = await fetch('/api/research/facts/extract', {
        method: 'POST',
        headers: jsonHeaders(),
        body: JSON.stringify({ run_id: target.runId, finding_id: target.findingId })
      });
      if (res.ok) {
        const data = await res.json();
        if (Array.isArray(data.facts)) return data.facts;
      }
    } catch {
      // server offline
    }
    return [];
  },

  /** Queue Claude's reading of one finding's page text. Needs the page text to have been fetched first. */
  async extractFactsWithClaude(findingId: number): Promise<ResearchOutcome<ClaudeJobTicket>> {
    try {
      const res = await fetch('/api/research/facts/extract', {
        method: 'POST',
        headers: jsonHeaders(),
        body: JSON.stringify({ finding_id: findingId, claude: true })
      });
      return await researchOutcome<ClaudeJobTicket>(res);
    } catch (e: any) {
      return { ok: false, error: NETWORK_ERROR(e) };
    }
  },

  /** List extracted facts for the Trust Panel, filtered by run / status / exam. */
  async listFacts(filter: { runId?: number; status?: string; examId?: string } = {}): Promise<ResearchFact[]> {
    try {
      const qs = new URLSearchParams();
      if (filter.runId) qs.set('run_id', String(filter.runId));
      if (filter.status) qs.set('status', filter.status);
      if (filter.examId) qs.set('exam_id', filter.examId);
      const res = await fetch(`/api/research/facts?${qs.toString()}`);
      if (res.ok) {
        const data = await res.json();
        if (Array.isArray(data.facts)) return data.facts;
      }
    } catch {
      // server offline
    }
    return [];
  },

  /** Human review of a fact. `approved` only marks eligibility for the existing promote gate. */
  async setFactStatus(id: number, status: ResearchFactStatus): Promise<boolean> {
    try {
      const res = await fetch(`/api/research/facts/${id}/status`, {
        method: 'POST',
        headers: jsonHeaders(),
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
// ---------------------------------------------------------------------------
// Syllabus: watched on the notice board, changed only by a verifier
// ---------------------------------------------------------------------------

export const syllabusLiveService = {
  /** Notices that may change this exam's syllabus, published after `since` (YYYY-MM-DD). */
  async watch(examId: string, since?: string): Promise<SyllabusWatch | null> {
    try {
      const qs = new URLSearchParams({ exam_id: examId });
      if (since) qs.set('since', since);
      const res = await fetch(`/api/syllabus/watch?${qs.toString()}`);
      if (res.ok) return await res.json();
    } catch {
      // server offline: the section shows the seed and says the board is not being read
    }
    return null;
  },

  async revisions(examId: string): Promise<SyllabusRevision[]> {
    try {
      const res = await fetch(`/api/syllabus/revisions?exam_id=${encodeURIComponent(examId)}`);
      if (res.ok) {
        const data = await res.json();
        if (Array.isArray(data.revisions)) return data.revisions;
      }
    } catch {
      // server offline: the seed stands
    }
    return [];
  },

  async addRevision(input: {
    examId: string;
    kind: SyllabusRevision['kind'];
    topicId?: string;
    topic?: SyllabusRevisionTopic;
    note?: string;
    noticeTitle?: string;
    noticeUrl?: string;
    noticeDate?: string;
    appliedBy?: string;
  }): Promise<{ revision?: SyllabusRevision; error?: string }> {
    try {
      const res = await fetch('/api/syllabus/revisions', {
        method: 'POST',
        headers: jsonHeaders(),
        body: JSON.stringify(input)
      });
      const data = await res.json();
      if (res.ok && data.revision) return { revision: data.revision };
      return { error: data.error || `Server answered ${res.status}` };
    } catch {
      return { error: 'The GovOS server is not reachable, so the revision was not saved.' };
    }
  },

  async retireRevision(id: string): Promise<boolean> {
    try {
      const res = await fetch(`/api/syllabus/revisions/${encodeURIComponent(id)}/retire`, { method: 'POST', headers: adminHeaders() });
      return res.ok;
    } catch {
      return false;
    }
  }
};

/**
 * Merge the server's revisions over the register's syllabus. Returns the very same exam
 * object when there is nothing to apply, so callers can pass the result down without
 * causing re-renders. Applied in the order the verifier made them.
 */
export function applySyllabusRevisions(exam: Exam, revisions: SyllabusRevision[]): Exam {
  const mine = revisions.filter(r => r.examId === exam.id);
  if (mine.length === 0) return exam;

  let topics: SyllabusTopic[] = [...exam.syllabus];
  const seedProvenance = exam.syllabus[0]?.officialProvenance;

  const provenanceFor = (r: SyllabusRevision): DataProvenance => ({
    id: `prov-${r.id}`,
    documentTitle: r.noticeTitle || seedProvenance?.documentTitle || `${exam.title} notice`,
    officialUrl: r.noticeUrl || seedProvenance?.officialUrl || exam.officialDomain,
    clauseNumber: 'Syllabus revision recorded by the GovOS verifier',
    publishedDate: r.noticeDate || r.appliedAt.slice(0, 10),
    verifiedDate: r.appliedAt.slice(0, 10),
    verifiedBy: r.appliedBy,
    taxonomyType: 'FACT',
    // A change with a notice behind it is verified; a change on a note alone is not yet.
    verificationLevel: r.noticeUrl ? 'OFFICIALLY_VERIFIED' : 'UNDER_VERIFICATION',
    excerptText: r.note || `Applied at runtime from ${r.noticeTitle || 'a verifier note'}, not from a code edit.`
  });

  mine.forEach(r => {
    if (r.kind === 'RETIRE') {
      topics = topics.filter(t => t.id !== r.topicId);
      return;
    }
    const meta = {
      id: r.id, kind: r.kind, noticeTitle: r.noticeTitle, noticeUrl: r.noticeUrl,
      noticeDate: r.noticeDate, appliedAt: r.appliedAt, appliedBy: r.appliedBy
    } as const;
    const fields = r.topic || {};
    if (r.kind === 'AMEND') {
      topics = topics.map(t => t.id !== r.topicId ? t : {
        ...t,
        ...(fields.subject ? { subject: fields.subject } : {}),
        ...(fields.tier ? { tier: fields.tier } : {}),
        ...(fields.topicName ? { topicName: fields.topicName } : {}),
        ...(fields.subtopics && fields.subtopics.length > 0 ? { subtopics: fields.subtopics } : {}),
        ...(typeof fields.weightagePercentage === 'number' ? { weightagePercentage: fields.weightagePercentage } : {}),
        ...(typeof fields.avgQuestions === 'number' ? { avgQuestions: fields.avgQuestions } : {}),
        ...(typeof fields.isHighYield === 'boolean' ? { isHighYield: fields.isHighYield } : {}),
        officialProvenance: provenanceFor(r),
        revision: meta
      });
      return;
    }
    // ADD
    topics = [...topics, {
      id: r.id,
      subject: fields.subject || 'General Awareness',
      tier: fields.tier || 'BOTH',
      topicName: fields.topicName || 'Untitled topic',
      subtopics: fields.subtopics && fields.subtopics.length > 0 ? fields.subtopics : undefined,
      weightagePercentage: typeof fields.weightagePercentage === 'number' ? fields.weightagePercentage : 0,
      avgQuestions: typeof fields.avgQuestions === 'number' ? fields.avgQuestions : 0,
      isHighYield: fields.isHighYield === true,
      officialProvenance: provenanceFor(r),
      revision: meta
    }];
  });

  return { ...exam, syllabus: topics };
}

/**
 * Authority source discovery (tools/exam_builder/authority_discovery.py): what the latest bounded walk
 * of an exam's authority found, projected onto that exam. Read-only for candidates; starting a walk is
 * an admin job. Every call fails soft: offline means "not discovered here", never "not published".
 */
export const sourceDiscoveryService = {
  async forExam(examId: string): Promise<DiscoveredSources | null> {
    try {
      const res = await fetch(`/api/sources/exam/${encodeURIComponent(examId)}`);
      if (res.ok) return await res.json();
    } catch {
      // server offline: the sections show the register's own entries only
    }
    return null;
  },

  /** Queue a walk of this exam's authority from its official address. Admin only. */
  async discover(examId: string, useClaude: boolean = false): Promise<ResearchOutcome<ClaudeJobTicket>> {
    try {
      const res = await fetch('/api/sources/discover', {
        method: 'POST',
        headers: jsonHeaders(),
        body: JSON.stringify({ examId, useClaude })
      });
      return await researchOutcome<ClaudeJobTicket>(res);
    } catch {
      return { ok: false, error: 'Could not reach the GovOS server. Start "python app.py" and try again.' };
    }
  },

  async runs(limit: number = 10): Promise<Array<{ id: string; estate: string; authorityName: string; startedAt: string; endedAt: string; jobId: string; nodes: number; exhaustive: boolean; repositories: number }>> {
    try {
      const res = await fetch(`/api/sources/runs?limit=${limit}`, { headers: adminHeaders() });
      if (res.ok) {
        const data = await res.json();
        if (Array.isArray(data.runs)) return data.runs;
      }
    } catch {
      // server offline
    }
    return [];
  }
};

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

  /** UPSC's What's New list, mapped to the same shape as SSC's board; items are dated by first sighting. */
  async upscNotices(scope: 'cse' | 'all' = 'cse', limit: number = 8): Promise<SscNoticeFeed | null> {
    try {
      const res = await fetch(`/api/resources/live/upsc-notices?scope=${scope}&limit=${limit}`);
      if (!res.ok) return null;
      const data = await res.json();
      return {
        items: (data.items || []).map((i: { id: string; headline: string; firstSeen: string; url: string; kind: string }) => ({
          id: i.id, headline: i.headline, createdAt: i.firstSeen, isCgl: false,
          files: [{ name: i.kind || 'Open', url: i.url, sizeKb: 0 }]
        })),
        total: data.total || 0,
        scope: 'all',
        fetchedAt: data.fetchedAt || null,
        stale: !!data.stale,
        error: data.error || null,
        source: data.source || 'https://www.upsc.gov.in/whats-new',
        intervalHours: data.intervalHours || 6
      };
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

  /** The verifier-added entries for ONE exam (or every exam's, for the Trust Panel, when no exam is given). */
  async additions(examId?: string): Promise<ResourceAddition[]> {
    try {
      const res = await fetch(examId ? `/api/resources/additions?exam_id=${encodeURIComponent(examId)}` : '/api/resources/additions');
      if (res.ok) {
        const data = await res.json();
        if (Array.isArray(data.additions)) return data.additions;
      }
    } catch {
      // server offline
    }
    return [];
  },

  async addResource(payload: { title: string; url: string; examId: string; subject?: string; resourceFormat?: string; author?: string; description?: string; findingId?: number; addedFrom?: string }): Promise<ResourceAddition | null> {
    try {
      const res = await fetch('/api/resources/additions', {
        method: 'POST',
        headers: jsonHeaders(),
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
      const res = await fetch(`/api/resources/additions/${encodeURIComponent(id)}/retire`, { method: 'POST', headers: adminHeaders() });
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

// ==========================================================================
// Conversation context — one lightweight model shared by every chat
//
// A chat that reads each message in isolation cannot answer "am I eligible?" or "when is
// it?", because the subject lives in the previous turn and in whatever the candidate has
// selected in the platform. These helpers keep that context in one place: recent turns per
// chat, plus the active exam, target post, journey stage and profile.
// ==========================================================================

const CHAT_HISTORY_KEY = 'govos_chat_history';
const MAX_TURNS_PER_CHANNEL = 12;

type ChatHistoryStore = Partial<Record<ChatChannel, ConversationTurn[]>>;

const readHistoryStore = (): ChatHistoryStore => {
  try {
    const raw = localStorage.getItem(CHAT_HISTORY_KEY);
    return raw ? JSON.parse(raw) as ChatHistoryStore : {};
  } catch {
    return {};
  }
};

const writeHistoryStore = (store: ChatHistoryStore): void => {
  try {
    localStorage.setItem(CHAT_HISTORY_KEY, JSON.stringify(store));
  } catch {
    // storage unavailable: conversation still works for this page view
  }
};

export const conversationService = {
  /** Recent turns for one chat, oldest first. */
  history(channel: ChatChannel): ConversationTurn[] {
    return readHistoryStore()[channel] || [];
  },

  /** Record a turn and return the trimmed history. */
  append(channel: ChatChannel, turn: Omit<ConversationTurn, 'at'> & { at?: string }): ConversationTurn[] {
    const store = readHistoryStore();
    const next = [...(store[channel] || []), { ...turn, at: turn.at || new Date().toISOString() }];
    const trimmed = next.slice(-MAX_TURNS_PER_CHANNEL);
    store[channel] = trimmed;
    writeHistoryStore(store);
    return trimmed;
  },

  /** The most recent turn of a role, if any. */
  last(channel: ChatChannel, role: ConversationTurn['role']): ConversationTurn | undefined {
    const turns = this.history(channel).filter(t => t.role === role);
    return turns.length > 0 ? turns[turns.length - 1] : undefined;
  },

  clear(channel: ChatChannel): void {
    const store = readHistoryStore();
    delete store[channel];
    writeHistoryStore(store);
  },

  /** Switching exam invalidates what "it" referred to; drop the thread rather than mislead. */
  clearAll(): void {
    writeHistoryStore({});
  }
};

const parseExamDate = (value?: string): Date | null => {
  if (!value) return null;
  const parsed = new Date(value.replace(' ', 'T'));
  return Number.isNaN(parsed.getTime()) ? null : parsed;
};

const liveDate = (exam: Exam, type: string): Date | null => {
  const row = exam.dates.find(d => d.type === type && d.status !== 'SUPERSEDED')
    || exam.dates.find(d => d.type === type);
  return parseExamDate(row?.dateTimeStr);
};

/**
 * Where the candidate is in this exam's cycle, read from the exam's own dates — never
 * guessed. Used to make "what should I do next?" answerable.
 */
export function deriveCandidateStage(exam: Exam, now: Date = new Date()): CandidateStage {
  const open = liveDate(exam, 'APPLICATION_OPEN');
  const close = liveDate(exam, 'APPLICATION_CLOSE');
  const tier1 = liveDate(exam, 'EXAM_TIER1');
  if (tier1 && now > tier1) return 'POST_EXAM';
  if (close && now > close) return tier1 ? 'PRE_EXAM' : 'APPLICATION_CLOSED';
  if (open && now >= open) return 'APPLICATION_OPEN';
  return 'BEFORE_NOTIFICATION';
}

/** Whole days until applications close; negative once past. Null when the date is unknown. */
export function daysToApplicationClose(exam: Exam, now: Date = new Date()): number | null {
  const close = liveDate(exam, 'APPLICATION_CLOSE');
  if (!close) return null;
  return Math.round((close.getTime() - now.getTime()) / 86400000);
};

/**
 * Assemble the context one chat should answer with. Cheap enough to call per message:
 * localStorage reads plus a date comparison.
 */
export function buildChatContext(exam: Exam, channel: ChatChannel): ChatContext {
  const targetPostId = storageService.getTargetPost();
  const targetPost = exam.posts.find(p => p.id === targetPostId);
  return {
    channel,
    exam,
    targetPost,
    profile: storageService.getProfile(),
    stage: deriveCandidateStage(exam),
    daysToApplicationClose: daysToApplicationClose(exam),
    history: conversationService.history(channel)
  };
}

// ==========================================================================
// Universal Canonical Exam Fact Overlay Engine (Phase 1)
// ==========================================================================

export const examOverlayService = {
  async getOverlays(examId: string, cycle?: string, domain?: string): Promise<ExamFactOverlay[]> {
    try {
      let url = `/api/exams/${encodeURIComponent(examId)}/overlays`;
      const params = new URLSearchParams();
      if (cycle) params.append('cycle', cycle);
      if (domain) params.append('domain', domain);
      const qs = params.toString();
      if (qs) url += `?${qs}`;
      const res = await fetch(url);
      if (!res.ok) return [];
      const data = await res.json();
      return Array.isArray(data.overlays) ? data.overlays : [];
    } catch {
      return [];
    }
  },

  async addOverlay(examId: string, overlay: Partial<ExamFactOverlay>): Promise<ExamFactOverlay | null> {
    try {
      const res = await fetch(`/api/exams/${encodeURIComponent(examId)}/overlays`, {
        method: 'POST',
        headers: jsonHeaders(),
        body: JSON.stringify(overlay)
      });
      if (!res.ok) return null;
      const data = await res.json();
      return data.overlay || null;
    } catch {
      return null;
    }
  },

  async retireOverlay(overlayId: string): Promise<boolean> {
    try {
      const res = await fetch(`/api/exams/overlays/${encodeURIComponent(overlayId)}/retire`, {
        method: 'POST',
        headers: adminHeaders()
      });
      return res.ok;
    } catch {
      return false;
    }
  }
};

// ==========================================================================
// Runtime Exam Registry (Phase 3) — machine-acquired exams served at runtime.
//
// The exam universe a candidate can discover, open and track is:
//     authored ALL_EXAMS (compiled from src/data.ts)  UNION  published runtime registry exams
// Authored records always win on an id collision, and the registry is read best-effort: if the
// server is unreachable the authored register still stands, so the app never shows "no exams".
// ==========================================================================

let runtimeRegistryExams: Exam[] = [];

export const examRegistryService = {
  /** Every published runtime exam. Caches the result for getExamUniverse(); [] on any failure. */
  async load(): Promise<Exam[]> {
    try {
      const res = await fetch('/api/exams');
      if (!res.ok) return [];
      const data = await res.json();
      const exams: Exam[] = Array.isArray(data.exams) ? data.exams : [];
      runtimeRegistryExams = exams.map(e => ({ ...e, origin: 'MACHINE_ACQUIRED' as const }));
      return runtimeRegistryExams;
    } catch {
      return [];
    }
  },

  async get(examId: string, cycle?: string): Promise<Exam | null> {
    try {
      const qs = cycle ? `?cycle=${encodeURIComponent(cycle)}` : '';
      const res = await fetch(`/api/exams/${encodeURIComponent(examId)}${qs}`);
      if (!res.ok) return null;
      const data = await res.json();
      return data.exam ? { ...data.exam, origin: 'MACHINE_ACQUIRED' as const } : null;
    } catch {
      return null;
    }
  },

  /** The runtime exams loaded so far (synchronous read of the cache). */
  loaded(): Exam[] {
    return runtimeRegistryExams;
  }
};

/**
 * authored ∪ runtime, authored winning on an id collision. Pure over its inputs; pass the
 * authored register (ALL_EXAMS) and, optionally, an explicit runtime list — otherwise the
 * cache filled by examRegistryService.load() is used.
 */
export function getExamUniverse(authored: Exam[], runtime?: Exam[]): Exam[] {
  const extra = runtime ?? runtimeRegistryExams;
  if (!extra || extra.length === 0) return authored;
  const seen = new Set(authored.map(e => e.id));
  return [...authored, ...extra.filter(e => e && e.id && !seen.has(e.id))];
}

export function getExamCycle(exam: Exam): string {
  const idMatch = exam.id.match(/\b(20\d\d)\b/);
  if (idMatch) return idMatch[1];
  const titleMatch = exam.title.match(/\b(20\d\d)\b/);
  if (titleMatch) return titleMatch[1];
  return '';
}

/**
 * Pure, non-destructive projection of canonical exam fact overlays over an authored Exam record.
 * 
 * Rules (Phase 1):
 * 1. If overlays is empty or has no active entries for this exam, returns the exact same Exam reference.
 * 2. Preserves strict exam isolation (o.examId === exam.id).
 * 3. Preserves strict cycle/year isolation (o.cycle === getExamCycle(exam)).
 * 4. Only VERIFIED and unretired overlays enter the live projection (never CONFLICT or unverified).
 * 5. Never mutates the original Exam object.
 * 6. Preserves historical values when superseded (marking old with status 'SUPERSEDED').
 * 7. Preserves authored provenance and appends/updates verified provenance on machine items.
 */
function upsertById<T extends { id?: string }>(list: T[], item: T): T[] {
  if (!item.id) return [...list, item];
  const idx = list.findIndex(x => x.id === item.id);
  if (idx >= 0) {
    const next = [...list];
    next[idx] = item;
    return next;
  }
  return [...list, item];
}

export function applyExamOverlays(exam: Exam, overlays: ExamFactOverlay[]): Exam {
  if (!overlays || overlays.length === 0) return exam;

  const cycle = getExamCycle(exam);
  const active = overlays.filter(o => 
    o.examId === exam.id &&
    (!o.cycle || !cycle || o.cycle === cycle) &&
    !o.retired &&
    o.kind !== 'CONFLICT' &&
    (o.status === 'VERIFIED' || o.status === 'NOT_PUBLISHED')
  );

  if (active.length === 0) return exam;

  let projected: Exam = { ...exam };

  for (const o of active) {
    const val = o.value;
    const targetId = o.targetId;
    const targetScope = o.targetScope;

    switch (o.domain) {
      case 'dates': {
        let dates = [...projected.dates];
        if (o.kind === 'SUPERSEDE') {
          const supId = o.supersedesId || targetId;
          dates = dates.map(d => d.id === supId ? { ...d, status: 'SUPERSEDED' } : d);
          dates = upsertById(dates, {
            id: o.id,
            type: val.type || 'NOTIFICATION',
            label: val.label || 'Revised Date',
            dateTimeStr: val.dateTimeStr,
            timezone: val.timezone || 'IST',
            isTentative: Boolean(val.isTentative),
            status: 'AVAILABLE',
            provenance: o.provenance
          });
        } else if (o.kind === 'AMEND') {
          dates = dates.map(d => d.id === targetId ? { ...d, ...val, provenance: o.provenance } : d);
        } else if (o.kind === 'ADD') {
          dates = upsertById(dates, {
            id: targetId || o.id,
            type: val.type || 'NOTIFICATION',
            label: val.label || 'Important Date',
            dateTimeStr: val.dateTimeStr,
            timezone: val.timezone || 'IST',
            isTentative: Boolean(val.isTentative),
            status: val.status || 'AVAILABLE',
            provenance: o.provenance
          });
        }
        projected.dates = dates;
        break;
      }

      case 'posts': {
        let posts = [...projected.posts];
        if (o.kind === 'ADD') {
          posts = upsertById(posts, { ...val, id: targetId || o.id, provenance: o.provenance });
        } else if (o.kind === 'AMEND') {
          posts = posts.map(p => {
            const matches = p.id === targetId || (targetScope?.postId && p.id === targetScope.postId);
            return matches ? { ...p, ...val, provenance: o.provenance } : p;
          });
        } else if (o.kind === 'SUPERSEDE') {
          const supId = o.supersedesId || targetId;
          posts = posts.filter(p => p.id !== supId);
          posts = upsertById(posts, { ...val, id: o.id, provenance: o.provenance });
        }
        projected.posts = posts;
        break;
      }

      case 'eligibility': {
        if (val.category || val.years || val.maximumAge) {
          let relax = [...(projected.ageRelaxations || [])];
          const cat = val.category;
          if (o.kind === 'ADD') {
            const item = { ...val, provenance: o.provenance };
            if (cat) {
              const idx = relax.findIndex(r => r.category === cat);
              if (idx >= 0) relax[idx] = item;
              else relax.push(item);
            } else {
              relax.push(item);
            }
          } else if (o.kind === 'AMEND') {
            const idx = relax.findIndex(r => r.category === val.category);
            if (idx >= 0) relax[idx] = { ...relax[idx], ...val, provenance: o.provenance };
            else relax.push({ ...val, provenance: o.provenance });
          }
          projected.ageRelaxations = relax;
        }
        break;
      }

      case 'syllabus': {
        let topics = [...projected.syllabus];
        if (o.kind === 'ADD') {
          topics = upsertById(topics, { ...val, id: targetId || o.id, officialProvenance: o.provenance });
        } else if (o.kind === 'AMEND') {
          topics = topics.map(t => {
            const matches = t.id === targetId || (targetScope?.topicId && t.id === targetScope.topicId);
            return matches ? { ...t, ...val, officialProvenance: o.provenance } : t;
          });
        }
        projected.syllabus = topics;
        break;
      }

      case 'resources': {
        let resList = [...(projected.resources || [])];
        if (o.kind === 'ADD') {
          resList = upsertById(resList, { ...val, id: targetId || o.id, provenance: o.provenance });
        }
        projected.resources = resList;
        break;
      }

      case 'officialPapers': {
        let papers = [...(projected.officialPapers || [])];
        if (o.kind === 'ADD') {
          papers = upsertById(papers, { ...val, id: targetId || o.id });
        }
        projected.officialPapers = papers;
        break;
      }

      case 'answerKeys': {
        let keys = [...(projected.answerKeys || [])];
        if (o.kind === 'SUPERSEDE') {
          const supId = o.supersedesId || targetId;
          keys = keys.filter(k => k.id !== supId);
          keys = upsertById(keys, { ...val, id: o.id });
        } else if (o.kind === 'ADD') {
          keys = upsertById(keys, { ...val, id: targetId || o.id });
        }
        projected.answerKeys = keys;
        break;
      }

      case 'admitCard': {
        let events = [...(projected.admitCardEvents || [])];
        if (o.kind === 'ADD') {
          events = upsertById(events, { ...val, id: targetId || o.id });
        }
        projected.admitCardEvents = events;
        break;
      }

      case 'results': {
        let resList = [...(projected.resultDeclarations || [])];
        if (o.kind === 'ADD') {
          resList = upsertById(resList, { ...val, id: targetId || o.id });
        }
        projected.resultDeclarations = resList;
        break;
      }

      case 'cutoffsHistory': {
        let cuts = [...(projected.cutoffsHistory || [])];
        if (o.kind === 'ADD') {
          cuts = upsertById(cuts, { ...val, id: targetId || o.id });
        }
        projected.cutoffsHistory = cuts;
        break;
      }

      case 'faqs': {
        let faqs = [...(projected.faqs || [])];
        if (o.kind === 'ADD') {
          faqs = upsertById(faqs, { ...val, id: targetId || o.id });
        }
        projected.faqs = faqs;
        break;
      }

      case 'officialLinks': {
        const links = [...(projected.officialLinks || [])];
        if (o.kind === 'ADD') {
          const item = { ...val };
          const idx = links.findIndex(l => (item.url && l.url === item.url) || (item.title && l.title === item.title));
          if (idx >= 0) links[idx] = item;
          else links.push(item);
        }
        projected.officialLinks = links;
        break;
      }

      case 'corrigendums': {
        let corrs = [...(projected.corrigendums || [])];
        if (o.kind === 'ADD') {
          corrs = upsertById(corrs, { ...val, id: targetId || o.id });
        }
        projected.corrigendums = corrs;
        break;
      }

      case 'examDayChecklist': {
        let checklist = [...(projected.examDayChecklist || [])];
        if (o.kind === 'ADD') {
          checklist = upsertById(checklist, { ...val, id: targetId || o.id });
        }
        projected.examDayChecklist = checklist;
        break;
      }

      case 'overview': {
        if (val.overviewDescription) projected.overviewDescription = val.overviewDescription;
        if (val.vacanciesTotal) projected.vacanciesTotal = val.vacanciesTotal;
        break;
      }

      case 'roadmapTracks': {
        let tracks = [...(projected.roadmapTracks || [])];
        if (o.kind === 'ADD') {
          tracks = upsertById(tracks, { ...val, id: targetId || o.id });
        }
        projected.roadmapTracks = tracks;
        break;
      }
    }
  }

  return projected;
}


// ==========================================================================
// DISCOVERY ENGINE (begin) — naive-student exam discovery
// ==========================================================================
//
// `discoverExams(profile, exams)` answers "which government exams can I consider, and why?"
// for a student who may know nothing yet. It is a pure, deterministic projection of the
// EXISTING eligibility engine over the exam universe (authored ∪ published runtime exams):
//
//   * `evaluatePostEligibility` is the only authority on age, qualification and physical
//     outcomes. This block never re-implements a rule; it decides which of the engine's
//     outcomes may be *asserted* given what the student actually supplied.
//   * A profile field the engine needs and the student has not given makes that rule UNKNOWN
//     (INSUFFICIENT_INFORMATION), never INELIGIBLE. Whether a missing field matters is found by
//     asking the engine itself — running it once per possible value and seeing whether the
//     outcome changes — rather than by keeping a second copy of its rules here.
//   * A rule the exam's verified record does not carry (no age limit, no crucial date, no
//     posts) is RULES_NOT_AVAILABLE, a fact about the record, never about the student.
//   * Every reason is the engine's own wording or a statement of what is absent, and carries
//     the record's provenance. Nothing is ranked, scored or recommended; results are in the
//     universe's own order. Nothing here names an exam, an authority or a post id.
// ==========================================================================

const DISCOVERY_CATEGORIES: UserProfile['category'][] = ['GENERAL', 'OBC', 'SC', 'ST', 'PwBD', 'EWS'];

/**
 * The `UserProfile` handed to the engine. Fields the student has not given receive a neutral
 * placeholder ONLY so the engine's input type is satisfied; every outcome that depends on a
 * placeholder is masked as UNKNOWN by the caller and never read as a verdict.
 */
function discoveryEngineInput(p: DiscoveryProfile, overrides: Partial<UserProfile> = {}): UserProfile {
  return {
    dateOfBirth: p.dateOfBirth || '',
    degree: p.degree || '',
    branch: p.branch || '',
    mathsIn12thWith60Percent: p.mathsIn12thWith60Percent,
    statisticsInDegree: p.statisticsInDegree,
    percentage: 0,
    category: p.category || 'GENERAL',
    gender: 'Other',
    domicileState: '',
    nationality: '',
    physicalFitnessDeclared: p.physicalFitnessDeclared,
    colorBlind: p.colorBlind,
    ...overrides
  };
}

/** The engine joins its per-rule sentences with ' • '; this reads them back by rule. */
function discoverySplitReasons(verdict: PostVerdict): Record<DiscoveryRule, string[]> {
  const out: Record<DiscoveryRule, string[]> = { AGE: [], QUALIFICATION: [], PHYSICAL: [] };
  for (const seg of verdict.reason.split(' • ')) {
    const s = seg.trim();
    if (!s) continue;
    if (/^(age|underage)/i.test(s)) out.AGE.push(s);
    else if (/^(physical|medical)/i.test(s)) out.PHYSICAL.push(s);
    else out.QUALIFICATION.push(s);
  }
  return out;
}

function discoveryHasValue(v: unknown): boolean {
  return v !== undefined && v !== null && v !== '';
}

/**
 * Does the engine's outcome for `rule` depend on `field`, given everything else the student
 * gave? Answered by running the engine with each possible value of the field. If every run
 * agrees, the field is not needed for this post and the shared outcome is returned; if they
 * disagree, the rule cannot be asserted without the field.
 */
function discoveryProbe(
  run: (overrides: Partial<UserProfile>) => PostVerdict,
  field: DiscoveryProfileField,
  values: unknown[],
  read: (v: PostVerdict) => string
): { settled: boolean; verdict: PostVerdict } {
  const runs = values.map(val => run({ [field]: val } as Partial<UserProfile>));
  const first = read(runs[0]);
  return { settled: runs.every(r => read(r) === first), verdict: runs[0] };
}

function discoveryPost(exam: Exam, post: PostRequirement, profile: DiscoveryProfile, crucialDate: string): DiscoveryPostResult {
  const run = (overrides: Partial<UserProfile> = {}) =>
    evaluatePostEligibility(post, discoveryEngineInput(profile, overrides), crucialDate || '0000-00-00', exam);
  const reasons: DiscoveryReason[] = [];
  const cite = (...p: (DataProvenance | undefined | null)[]) => p.filter((x): x is DataProvenance => !!x && !!x.id);
  let engineVerdict: PostVerdict | null = null;

  // ---- AGE: the post's own limit, reckoned on the exam's own crucial date, relaxed only by the
  // ---- exam's own published entry for the student's category.
  const ageRulePublished = post.maxAge > 0 && !!crucialDate;
  if (!ageRulePublished) {
    reasons.push({
      rule: 'AGE', outcome: 'UNKNOWN', missingFields: [], ruleNotPublished: true,
      text: !crucialDate
        ? `${exam.authorityName}'s record for this cycle carries no date on which age is reckoned, so the age rule cannot be applied.`
        : `The verified record carries no upper age limit for ${post.postName}, so the age rule cannot be applied.`,
      provenance: cite(post.provenance)
    });
  } else if (!discoveryHasValue(profile.dateOfBirth)) {
    reasons.push({
      rule: 'AGE', outcome: 'UNKNOWN', missingFields: ['dateOfBirth'],
      text: `${post.postName}: age must be ${post.minAge}–${post.maxAge} years as on ${crucialDate}; your date of birth is needed to check it.`,
      provenance: cite(post.provenance)
    });
  } else {
    let v: PostVerdict;
    let categoryNeeded = false;
    if (!discoveryHasValue(profile.category)) {
      const probe = discoveryProbe(run, 'category', DISCOVERY_CATEGORIES, r => r.ageStatus);
      categoryNeeded = !probe.settled;
      v = probe.verdict;
    } else {
      v = run();
    }
    engineVerdict = v;
    const relax = discoveryHasValue(profile.category) ? findAgeRelaxation(exam, profile.category as string, post.id) : null;
    if (categoryNeeded) {
      reasons.push({
        rule: 'AGE', outcome: 'UNKNOWN', missingFields: ['category'],
        text: `${post.postName}: whether your age (${v.calculatedAge} as on ${crucialDate}) is within the limit depends on the age relaxation ${exam.authorityName} publishes for your category; your category is needed.`,
        provenance: cite(post.provenance, ...(exam.ageRelaxations || []).map(e => e.provenance))
      });
    } else {
      reasons.push({
        rule: 'AGE', outcome: v.ageStatus === 'OK' ? 'PASS' : 'FAIL', missingFields: [],
        text: discoverySplitReasons(v).AGE.join(' ') +
          (discoveryHasValue(profile.category) ? '' : ' (The outcome is the same for every category, so your category was not needed here.)'),
        provenance: cite(post.provenance, relax?.provenance)
      });
    }
  }

  // ---- QUALIFICATION: the engine's degree check, plus any special qualification it applies to
  // ---- this post. Which optional fields matter is asked of the engine, not assumed.
  if (!discoveryHasValue(profile.degree)) {
    reasons.push({
      rule: 'QUALIFICATION', outcome: 'UNKNOWN', missingFields: ['degree'],
      text: `${post.postName}: your educational qualification is needed to check the degree requirement${post.specialQualification ? ` (${post.specialQualification})` : ''}.`,
      provenance: cite(post.provenance)
    });
  } else {
    const missing: DiscoveryProfileField[] = [];
    let v = run();
    for (const f of ['statisticsInDegree', 'mathsIn12thWith60Percent'] as const) {
      if (discoveryHasValue(profile[f])) continue;
      const probe = discoveryProbe(run, f, [true, false], r => r.qualStatus);
      if (!probe.settled) missing.push(f);
    }
    // The engine reads a statistics branch as an alternative to the statistics answer, so the
    // branch is only asked for when the student has not answered the statistics question at all.
    if (!discoveryHasValue(profile.branch) && !discoveryHasValue(profile.statisticsInDegree)) {
      const probe = discoveryProbe(run, 'branch', ['statistics', ''], r => r.qualStatus);
      if (!probe.settled) missing.push('branch');
    }
    engineVerdict = engineVerdict || v;
    if (missing.length) {
      reasons.push({
        rule: 'QUALIFICATION', outcome: 'UNKNOWN', missingFields: missing,
        text: `${post.postName}: ${post.specialQualification || 'a special qualification'} — the answer depends on ${missing.join(', ')}, which you have not given.`,
        provenance: cite(post.provenance)
      });
    } else {
      reasons.push({
        rule: 'QUALIFICATION', outcome: v.qualStatus === 'OK' ? 'PASS' : 'FAIL', missingFields: [],
        text: discoverySplitReasons(v).QUALIFICATION.join(' '),
        provenance: cite(post.provenance)
      });
    }
  }

  // ---- PHYSICAL: only where the record says the post has physical standards.
  if (post.physicalRequired) {
    const missing: DiscoveryProfileField[] = [];
    for (const f of ['physicalFitnessDeclared', 'colorBlind'] as const) {
      if (discoveryHasValue(profile[f])) continue;
      const probe = discoveryProbe(run, f, [true, false], r => r.physicalStatus);
      if (!probe.settled) missing.push(f);
    }
    const v = run();
    engineVerdict = engineVerdict || v;
    if (missing.length) {
      reasons.push({
        rule: 'PHYSICAL', outcome: 'UNKNOWN', missingFields: missing,
        text: `${post.postName} has physical standards (${post.physicalNote || 'as published'}); ${missing.join(' and ')} needed to check them.`,
        provenance: cite(post.provenance)
      });
    } else {
      reasons.push({
        rule: 'PHYSICAL', outcome: v.physicalStatus === 'OK' ? 'PASS' : 'FAIL', missingFields: [],
        text: discoverySplitReasons(v).PHYSICAL.join(' ') || `Physical standards (${post.physicalNote || 'as published'}): your declaration satisfies them.`,
        provenance: cite(post.provenance)
      });
    }
  }

  // A known failure is decisive whatever else is unknown. Otherwise a rule the record lacks
  // cannot be resolved by the student, so it outranks a missing field; only a post every rule
  // of which passed is ELIGIBLE.
  let verdict: DiscoveryPostVerdict;
  if (reasons.some(r => r.outcome === 'FAIL')) verdict = 'INELIGIBLE';
  else if (reasons.some(r => r.ruleNotPublished)) verdict = 'RULES_NOT_AVAILABLE';
  else if (reasons.some(r => r.missingFields.length > 0)) verdict = 'INSUFFICIENT_INFORMATION';
  else verdict = 'ELIGIBLE';

  return {
    postId: post.id, postName: post.postName, department: post.department,
    verdict, reasons, provenance: post.provenance,
    engineVerdict: verdict === 'ELIGIBLE' || verdict === 'INELIGIBLE' ? engineVerdict : null
  };
}

function discoveryExam(exam: Exam, profile: DiscoveryProfile): DiscoveryExamResult {
  const crucialDate = exam.crucialEligibilityDate || '';
  const cycle = getExamCycle(exam);
  const posts = (exam.posts || []).map(p => discoveryPost(exam, p, profile, crucialDate));

  const counts = {
    eligible: posts.filter(p => p.verdict === 'ELIGIBLE').length,
    ineligible: posts.filter(p => p.verdict === 'INELIGIBLE').length,
    insufficient: posts.filter(p => p.verdict === 'INSUFFICIENT_INFORMATION').length,
    rulesNotAvailable: posts.filter(p => p.verdict === 'RULES_NOT_AVAILABLE').length,
    total: posts.length
  };

  let verdict: DiscoveryVerdict;
  if (counts.total === 0) verdict = 'RULES_NOT_AVAILABLE';
  else if (counts.eligible === counts.total) verdict = 'ELIGIBLE';
  else if (counts.eligible > 0) verdict = 'CONDITIONAL';
  else if (counts.insufficient > 0) verdict = 'INSUFFICIENT_INFORMATION';
  else if (counts.rulesNotAvailable > 0) verdict = 'RULES_NOT_AVAILABLE';
  else verdict = 'INELIGIBLE';

  const missingFields = Array.from(new Set(posts.flatMap(p => p.reasons.flatMap(r => r.missingFields)))) as DiscoveryProfileField[];
  const provenanceRefs: DataProvenance[] = [];
  const seen = new Set<string>();
  for (const p of posts) for (const r of p.reasons) for (const prov of r.provenance) {
    if (!seen.has(prov.id)) { seen.add(prov.id); provenanceRefs.push(prov); }
  }

  const summary: string[] = [];
  if (counts.total === 0) {
    summary.push(`${exam.title}: the verified record for cycle ${cycle || '(unknown)'} carries no post-level eligibility rules, so no verdict can be given yet.`);
  } else {
    summary.push(crucialDate
      ? `${exam.title}: age is reckoned as on ${crucialDate}.`
      : `${exam.title}: the record carries no date on which age is reckoned.`);
    if (discoveryHasValue(profile.category)) {
      const relax = findAgeRelaxation(exam, profile.category as string);
      summary.push(relax
        ? `Age relaxation for ${profile.category}: ${relax.years !== undefined ? `+${relax.years} years` : relax.maximumAge !== undefined ? `upper limit ${relax.maximumAge} years` : 'stated without a figure'} — ${relax.provenance.documentTitle}.`
        : `No age relaxation for ${profile.category} is recorded from ${exam.authorityName}'s own documents, so none has been applied.`);
    }
    summary.push(`${counts.eligible} of ${counts.total} posts: eligible on the rules checked` +
      (counts.ineligible ? `; ${counts.ineligible} not eligible` : '') +
      (counts.insufficient ? `; ${counts.insufficient} need more information` : '') +
      (counts.rulesNotAvailable ? `; ${counts.rulesNotAvailable} have rules not yet in the record` : '') + '.');
  }

  return {
    examId: exam.id, examTitle: exam.title, authorityName: exam.authorityName,
    cycle, origin: exam.origin === 'MACHINE_ACQUIRED' ? 'MACHINE_ACQUIRED' : 'AUTHORED',
    crucialDate, verdict, posts, summary, missingFields, provenanceRefs, counts
  };
}

/**
 * Which exams can this student consider, and why — over the whole universe handed in
 * (`getExamUniverse(authoredRegister, registryExams)`), in that order, with no ranking.
 * Pure: same inputs, same output; reads no storage, no clock, no network.
 */
export function discoverExams(profile: DiscoveryProfile, exams: Exam[]): DiscoveryResult {
  const results = exams.map(e => discoveryExam(e, profile));
  return {
    profile: { ...profile },
    exams: results,
    universe: {
      authored: exams.filter(e => e.origin !== 'MACHINE_ACQUIRED').length,
      machineAcquired: exams.filter(e => e.origin === 'MACHINE_ACQUIRED').length,
      total: exams.length
    },
    missingFields: Array.from(new Set(results.flatMap(r => r.missingFields))) as DiscoveryProfileField[]
  };
}

/** The discovery inputs a saved candidate profile already answers, so the student is not asked twice. */
export function discoveryProfileFromUserProfile(p: UserProfile | null | undefined): DiscoveryProfile {
  if (!p) return {};
  const out: DiscoveryProfile = {};
  if (p.dateOfBirth) out.dateOfBirth = p.dateOfBirth;
  if (p.category) out.category = p.category;
  if (p.degree) out.degree = p.degree;
  if (p.branch) out.branch = p.branch;
  if (p.statisticsInDegree !== undefined) out.statisticsInDegree = p.statisticsInDegree;
  if (p.mathsIn12thWith60Percent !== undefined) out.mathsIn12thWith60Percent = p.mathsIn12thWith60Percent;
  if (p.physicalFitnessDeclared !== undefined) out.physicalFitnessDeclared = p.physicalFitnessDeclared;
  if (p.colorBlind !== undefined) out.colorBlind = p.colorBlind;
  return out;
}
// ==========================================================================
// DISCOVERY ENGINE (end)
// ==========================================================================

