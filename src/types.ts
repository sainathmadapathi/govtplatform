// GovOS shared type definitions.

export type DataTaxonomyType = 'FACT' | 'INTERPRETATION' | 'EXPLANATION' | 'RECOMMENDATION';

export type VerificationLevel = 'OFFICIALLY_VERIFIED' | 'UNDER_VERIFICATION' | 'SUPERSEDED';

export interface DataProvenance {
  id: string;
  documentTitle: string;
  officialUrl: string;
  pageNumber?: number;
  clauseNumber?: string;
  publishedDate: string;
  verifiedDate: string;
  verifiedBy: string;
  taxonomyType: DataTaxonomyType;
  verificationLevel: VerificationLevel;
  excerptText?: string; // Direct quoted legal text from official gazette
}

export interface CorrigendumNotice {
  id: string;
  title: string;
  noticeNumber: string;
  publishedDate: string;
  effectiveDate: string;
  summary: string;
  pdfUrl: string;
  status: 'ACTIVE' | 'SUPERSEDED';
  diffSummary: string;
}

export interface ImportantDate {
  id: string;
  type: 'NOTIFICATION' | 'APPLICATION_OPEN' | 'APPLICATION_CLOSE' | 'CORRECTION_WINDOW' | 'ADMIT_CARD' | 'EXAM_TIER1' | 'EXAM_TIER2' | 'ANSWER_KEY' | 'RESULT';
  label: string;
  dateTimeStr: string;
  timezone: string;
  isTentative: boolean;
  status: 'AVAILABLE' | 'NOT_YET_ANNOUNCED' | 'SUPERSEDED';
  provenance: DataProvenance;
}

export interface PostRequirement {
  id: string;
  postName: string;
  department: string;
  ministry?: string;
  payLevel: string;
  payScale: string;
  gradePay?: number;
  classification: 'Group A (Gazetted)' | 'Group B (Gazetted)' | 'Group B (Non-Gazetted)' | 'Group C';
  minAge: number;
  maxAge: number;
  specialQualification?: string;
  physicalRequired?: boolean;
  physicalNote?: string;
  colorBlindnessAllowed?: boolean;
  natureOfWork?: string;
  ruleGroup?: RuleGroup;
  provenance: DataProvenance;
}

export interface EligibilityRule {
  id: string;
  ruleType: 'AGE_MIN' | 'AGE_MAX' | 'DOB_CUTOFF' | 'DEGREE_REQUIRED' | 'BRANCH_SPECIALIZATION' | 'PERCENTAGE_MIN' | 'NATIONALITY' | 'CATEGORY_RELAXATION';
  operator: '>=' | '<=' | '=' | 'IN' | 'BETWEEN';
  ruleValue: string | number | string[];
  category: 'GENERAL' | 'OBC' | 'SC' | 'ST' | 'PwBD' | 'EWS';
  provenance: DataProvenance;
}

export interface RuleGroup {
  id: string;
  operator: 'AND' | 'OR';
  rules: EligibilityRule[];
  childGroups?: RuleGroup[];
}

export interface SyllabusTopic {
  id: string;
  subject: 'Quantitative Aptitude' | 'Reasoning & General Intelligence' | 'English Comprehension' | 'General Awareness' | 'Computer Proficiency' | 'Statistics';
  tier: 'TIER_1' | 'TIER_2' | 'BOTH';
  topicName: string;
  parentId?: string;
  subtopics?: string[];
  weightagePercentage: number;
  avgQuestions: number;
  isHighYield: boolean;
  officialProvenance: DataProvenance;
  weightageProvenance?: DataProvenance;
}

export interface ExamStage {
  id: string;
  stageNumber: number;
  stageName: string;
  tier: 'TIER_1' | 'TIER_2';
  durationMinutes: number;
  totalQuestions: number;
  totalMarks: number;
  negativeMarking: string;
  mode: string;
  qualifyingNature: string;
  sections: {
    sectionName: string;
    modules: string[];
    questions: number;
    marks: number;
    durationMinutes: number;
    negativeMarking: string;
  }[];
  provenance: DataProvenance;
}

export interface QuestionOption {
  id: number;
  text: string;
}

export interface ShortcutTrick {
  name: string;
  formula?: string;
  /** Long-form prose explanation of the trick. Optional: some entries use `trickSteps` instead. */
  explanation?: string;
  /** Condensed one-line form of the trick, used by the animated shortcut cards. */
  trickSteps?: string;
  timeSaved: string;
}

export interface TechnicalTermDefinition {
  term: string;
  meaning: string;
}

export interface DetailedExplanation {
  simpleExplanation: string;
  coreConcept: string;
  technicalTerms?: TechnicalTermDefinition[];
  stepByStepMethod: string[];
  shortcutTrick?: ShortcutTrick;
  eliminationStrategy?: string;
  crucialTakeaway: string;
}

export interface PracticeQuestion {
  id: string;
  topicId: string;
  subject: string;
  topicName: string;
  tier: 'TIER_1' | 'TIER_2';
  shiftInfo: string;
  questionType:
    | 'OFFICIAL_PYQ'
    | 'USER_SUBMITTED'
    | 'GOVOS_CREATED'
    | 'AI_GENERATED'
    | 'CUSTOM_AI_GENERATED'
    | 'SECTIONAL_MOCK'
    | 'TOPIC_DRILL'
    | 'REFERENCE_SOURCE';
  questionText: string;
  options: QuestionOption[];
  correctOptionIndex: number;
  explanation: string;
  detailedExplanation?: DetailedExplanation;
  year?: number;
  difficulty: 'EASY' | 'MEDIUM' | 'HARD' | 'ADAPTIVE';
  provenance: DataProvenance;
}

export interface CutoffEntry {
  year: number;
  category: string;
  tier1Cutoff: number;
  tier2Cutoff?: number;
  postsEligible?: string;
  provenance: DataProvenance;
}

export interface InAppChapter {
  chapterTitle: string;
  contentMarkdown: string;
}

export interface ResourceItem {
  id: string;
  title: string;
  subject:
    | 'Quantitative Aptitude'
    | 'English Comprehension'
    | 'Reasoning'
    | 'General Awareness & Static GK'
    | 'Current Affairs & Governance'
    | 'Banking & Financial Awareness'
    | 'Foundation Textbooks & Open Courses'
    | 'Computer & Typing'
    | 'Official Gazette';
  author: string;
  type: 'OFFICIAL_PDF' | 'OFFICIAL_PORTAL' | 'SIMPLIFIED_GUIDE' | 'RECOMMENDED_BOOK' | 'VIDEO_LECTURE' | 'ONLINE_TOOL';
  resourceFormat: 'DIRECT_PDF' | 'YOUTUBE_COURSE' | 'YOUTUBE_CHANNEL' | 'INTERACTIVE_HANDBOOK' | 'ONLINE_TOOL' | 'OFFICIAL_PORTAL';
  url: string;
  directPdfUrl?: string;
  youtubeUrl?: string;
  youtubeEmbedId?: string;
  inAppHandbookContent?: {
    summary: string;
    chapters: InAppChapter[];
  };
  downloadFileName?: string;
  description: string;
  recommendedFor: string;
  rating?: string;
  officialTag?: string;
  provenance?: DataProvenance;
  /** Pinned to the "Start here" shelf at the top of the resource library. */
  isEssential?: boolean;
  /** Date (YYYY-MM-DD) the URL last returned a healthy HTTP response from GovOS's link check. */
  linkVerifiedDate?: string;
}

export type ResourceLinkStatus = 'HEALTHY' | 'REDIRECT' | 'BLOCKED' | 'BROKEN' | 'UNREACHABLE';

export interface ResourceLinkCheck {
  url: string;
  status: ResourceLinkStatus;
  httpCode: number;
  checkedAt: string;
}

// --- Live Source Research (Tavily) ---

/** How much a search result can be trusted, decided purely from its domain. */
export type ResearchTrustLevel = 'OFFICIAL' | 'TRUSTED_PUBLIC' | 'UNVERIFIED';

/** OFFICIAL restricts Tavily to government/statutory domains; NEWS is the last 30 days; WEB is unrestricted. */
export type ResearchMode = 'OFFICIAL' | 'NEWS' | 'WEB';

export type ResearchReviewStatus = 'PENDING_REVIEW' | 'REVIEWED' | 'PROMOTED' | 'REJECTED';

export interface ResearchFinding {
  id: number;
  runId: number;
  title: string;
  url: string;
  snippet: string;
  trustLevel: ResearchTrustLevel;
  score: number;
  publishedDate?: string | null;
  reviewStatus: ResearchReviewStatus;
  hasExtractedText?: boolean;
  extractedText?: string;
  createdAt?: string;
}

export interface ResearchRun {
  id: number;
  query: string;
  mode: ResearchMode;
  examId?: string | null;
  answer?: string | null;
  resultCount: number;
  createdAt: string;
  findings: ResearchFinding[];
}

export interface ResearchStatus {
  configured: boolean;
  baseUrl: string;
  officialDomains: string[];
  runCount: number;
  pendingReview: number;
}

export interface ResearchSearchResult {
  runId: number;
  query: string;
  mode: ResearchMode;
  examId?: string | null;
  answer?: string | null;
  results: ResearchFinding[];
  /** Results Tavily returned that were dropped because OFFICIAL scope only keeps official domains. */
  filteredOut?: number;
  responseTime?: number;
}

export interface ResearchExtractResult {
  url: string;
  rawContent: string;
  chars: number;
  failed: boolean;
  reason?: string;
}

/** Discriminated result so callers can render a setup notice instead of a generic error. */
export type ResearchOutcome<T> =
  | { ok: true; data: T }
  | { ok: false; error: string; setup?: string; notConfigured?: boolean };

export interface FAQItem {
  id: string;
  question: string;
  answer: string;
  officialClause: string;
  provenance: DataProvenance;
}

export interface OTRStep {
  stepNumber: number;
  title: string;
  portalUrl: string;
  instructions: string[];
  mandatoryFields: string[];
  commonMistakesToAvoid: string[];
}

export interface DocumentSpecification {
  documentType: string;
  dimensions: string;
  fileFormat: string;
  fileSize: string;
  rules: string[];
  sampleDescription: string;
}

export interface CertificateValidityRule {
  category: 'OBC_NCL' | 'EWS' | 'SC_ST' | 'PwBD' | 'ESM';
  title: string;
  issuingAuthority: string[];
  financialYearValidity: string;
  crucialDate: string;
  officialAnnexure: string;
  keyConditions: string[];
}

export type RequirementProvenanceType = 
  | 'OFFICIAL_REQUIREMENT'      // Government notification/syllabus explicitly requires it
  | 'PREPARATION_TOPIC'        // Topic derived from official syllabus
  | 'RECOMMENDED_PREPARATION'  // GovOS recommendation for preparation
  | 'OPTIONAL_RESOURCE';       // Helpful but not required

export interface StudyModuleRequirement {
  id: string;
  title: string;
  subject: 'Quantitative Aptitude' | 'Reasoning & General Intelligence' | 'English Comprehension' | 'General Awareness' | 'Computer Proficiency' | 'Statistics';
  stage: 'TIER_1' | 'TIER_2' | 'BOTH';
  requirementType: RequirementProvenanceType;
  officialClause: string;
  questionsCount: number;
  marks: number;
  negativeMarking: string;
  highYieldTopics: string[];
  keyTakeaways: string;
  provenance: DataProvenance;
}

export interface ExcludedModule {
  moduleId: string;
  moduleName: string;
  reason: string;
  applicableOnlyTo: string;
}

export interface PostStudyPath {
  postId: string;
  postName: string;
  department: string;
  classification: string;
  payLevel: string;
  tier1: {
    commonModules: StudyModuleRequirement[];
    additionalModules: StudyModuleRequirement[];
    excludedModules: ExcludedModule[];
  };
  tier2: {
    paper1Mandatory: boolean;
    paper2StatisticsRequired: boolean;
    computerQualifyingThreshold: 'STANDARD_18_MARKS_QUALIFYING' | 'HIGHER_CUTOFF_MANDATED_CPT';
    destTypingThreshold: 'STANDARD_QUALIFYING' | 'HIGHER_ACCURACY_MANDATED';
    commonModules: StudyModuleRequirement[];
    additionalModules: StudyModuleRequirement[];
    excludedModules: ExcludedModule[];
  };
  physicalMedical?: {
    required: boolean;
    maleHeightChest?: string;
    femaleHeightWeight?: string;
    physicalTest?: string;
    colorBlindnessAllowed: boolean;
  };
}

export interface ApplicationGuideData {
  officialPortal: string;
  otrSteps: OTRStep[];
  photoRules: DocumentSpecification;
  signatureRules: DocumentSpecification;
  certificateRules: CertificateValidityRule[];
  rejectionPitfalls: {
    pitfall: string;
    consequence: string;
    prevention: string;
  }[];
}

export interface RoadmapPhase {
  phaseNumber: number;
  phaseTitle: string;
  durationWeeks: number;
  focusArea: string;
  weeklySchedule: {
    weekNumber: number;
    weekTitle: string;
    goals: string[];
    suggestedDailyHours: number;
    milestoneTest: string;
  }[];
}

export interface RoadmapTrack {
  id: 'TRACK_90_DAYS' | 'TRACK_180_DAYS' | 'TRACK_WORKING_PRO';
  name: string;
  subtitle: string;
  targetDailyHours: number;
  suitableFor: string;
  phases: RoadmapPhase[];
  dailyTimetable: {
    timeSlot: string;
    activity: string;
    focus: string;
  }[];
}

export interface AdmitCardDetails {
  status: 'AVAILABLE' | 'NOT_YET_ANNOUNCED' | 'EXPIRED';
  releaseDateStr: string;
  officialPortalUrl: string;
  loginCredentialsRequired: string[];
  instructions: string[];
  cityIntimationAvailable: boolean;
  cityIntimationUrl?: string;
  regionPortals?: {
    regionName: string;
    regionCode: string;
    statesCovered: string;
    portalUrl: string;
    status: 'ACTIVE' | 'SOON';
  }[];
}

export interface ExamDayChecklistItem {
  id: string;
  category: 'DOCUMENTS' | 'TIMING' | 'ITEMS_ALLOWED' | 'ITEMS_PROHIBITED' | 'CENTRE_INSTRUCTIONS';
  title: string;
  description: string;
  isMandatory: boolean;
}

export interface ResultActionOption {
  title: string;
  description: string;
  badge?: string;
  linkSection?: number;
  recommendedTimeline?: string;
}

export interface ResultNextStepStage {
  status: 'QUALIFIED' | 'NOT_QUALIFIED' | 'AWAITING_RESULT' | 'SKILL_TEST' | 'DOCUMENT_VERIFICATION';
  headline: string;
  summary: string;
  actions: ResultActionOption[];
  contingencyPlan?: {
    summary: string;
    alternativeExams: string[];
    weakAreaStrategy: string;
  };
}

/** Minimum qualification a candidate needs before this exam is worth showing them. */
export type ExamQualificationLevel = 'CLASS_10' | 'CLASS_12' | 'GRADUATION' | 'POST_GRADUATION';

/** Career field buckets used by the Exam Finder discovery filters. */
export type ExamCareerField =
  | 'Government Job'
  | 'Civil Services & Governance'
  | 'Banking & Financial Sector'
  | 'Indian Railways'
  | 'Defence & Armed Forces'
  | 'State Public Services';

export type ExamCategoryTag =
  | 'CIVIL_SERVICES'
  | 'STATE_PSC'
  | 'STAFF_SELECTION'
  | 'BANKING'
  | 'RAILWAYS'
  | 'DEFENCE';

export interface Exam {
  id: string;
  code: string;
  title: string;
  authorityName: string;
  officialDomain: string;
  crucialEligibilityDate: string;
  /** Minimum qualification level accepted. Used by the Exam Finder persona filter. */
  minimumQualification?: ExamQualificationLevel;
  /** Career fields this exam leads to. Used by the Exam Finder interest filter. */
  careerFields?: ExamCareerField[];
  /** Major exam cluster category used for behavioral recommendation and transfer learning */
  categoryTag?: ExamCategoryTag;
  isGoldenJourney: boolean;
  isDemoData: boolean;
  overviewDescription: string;
  vacanciesTotal?: string;
  posts: PostRequirement[];
  dates: ImportantDate[];
  globalRuleGroup: RuleGroup;
  stages: ExamStage[];
  syllabus: SyllabusTopic[];
  practiceQuestions: PracticeQuestion[];
  corrigendums: CorrigendumNotice[];
  cutoffsHistory: CutoffEntry[];
  resources: ResourceItem[];
  faqs: FAQItem[];
  applicationGuide: ApplicationGuideData;
  roadmapTracks: RoadmapTrack[];
  admitCardDetails?: AdmitCardDetails;
  examDayChecklist?: ExamDayChecklistItem[];
  resultNextSteps?: ResultNextStepStage[];
}

export interface UserProfile {
  dateOfBirth: string;
  degree: string;
  branch: string;
  mathsIn12thWith60Percent?: boolean;
  statisticsInDegree?: boolean;
  percentage: number;
  category: 'GENERAL' | 'OBC' | 'SC' | 'ST' | 'PwBD' | 'EWS';
  gender: 'Male' | 'Female' | 'Other';
  domicileState: string;
  nationality: string;
  physicalFitnessDeclared?: boolean;
  colorBlind?: boolean;
}

export interface PostVerdict {
  postId: string;
  postName: string;
  department: string;
  payLevel: string;
  eligible: boolean;
  ageStatus: 'OK' | 'EXCEEDED' | 'UNDERAGE';
  calculatedAge: number;
  maxPermissibleAge: number;
  qualStatus: 'OK' | 'DISQUALIFIED';
  physicalStatus: 'OK' | 'RESTRICTED';
  reason: string;
  officialClause: string;
}

export interface EligibilityDiagnostic {
  isEligible: boolean;
  status: 'ELIGIBLE' | 'CONDITIONAL' | 'INELIGIBLE';
  calculatedAgeOnCutoff: {
    years: number;
    months: number;
    days: number;
    crucialDate: string;
  };
  categoryRelaxationApplied: string;
  totalEligiblePosts: number;
  totalAvailablePosts: number;
  legalClauses: string[];
  plainEnglishExplanation: string;
  postVerdicts: PostVerdict[];
}

/** Trust-pipeline monitoring record for one official source endpoint (Admin Trust Panel). */
export interface SourceHealthLog {
  id: string;
  endpointUrl: string;
  authorityCode: string;
  httpStatus: number;
  checkedAt: string;
  rawContentHash: string;
  normalizedContentHash: string;
  textChanged: boolean;
  adminReviewStatus: 'HEALTHY' | 'CONFLICT_DETECTED' | 'REVIEWED' | 'FAILED';
  previousValue?: string;
  newValue?: string;
}

export interface UserReport {
  id: string;
  entityType: string;
  entityId: string;
  issueCategory: 'WRONG_ELIGIBILITY' | 'OUTDATED_DATE' | 'BROKEN_LINK' | 'INCORRECT_QUESTION';
  description: string;
  createdAt: string;
  adminStatus: 'PENDING' | 'RESOLVED' | 'REJECTED';
}

// --- Notification & Timeline Types ---

export type NotificationChannel = 'IN_APP' | 'PUSH' | 'EMAIL' | 'WHATSAPP';

export type NotificationEventType = 
  | 'APPLICATION_OPEN' 
  | 'APPLICATION_DEADLINE' 
  | 'CORRECTION_WINDOW' 
  | 'ADMIT_CARD' 
  | 'EXAM_DATE' 
  | 'ANSWER_KEY' 
  | 'RESULT';

export interface NotificationPreference {
  channels: {
    inApp: boolean; // default: true
    browserPush: boolean; // default: false
    email: boolean; // default: false
    whatsapp: boolean; // default: false
  };
  contactInfo: {
    email: string;
    phone: string;
    whatsappVerified: boolean;
  };
  eventSubscriptions: {
    applicationOpening: boolean;
    applicationDeadlines: boolean;
    correctionWindows: boolean;
    admitCards: boolean;
    examDates: boolean;
    results: boolean;
  };
  reminderSchedule: {
    sevenDaysBefore: boolean;
    threeDaysBefore: boolean;
    oneDayBefore: boolean;
    lastDayHoursBefore: boolean;
  };
}

export interface CandidateNotification {
  id: string; // Unique deterministic key e.g. "notif-ssc-cgl-2026-APPLICATION_DEADLINE-3D"
  examId: string;
  examCode: string;
  examTitle: string;
  eventType: NotificationEventType;
  title: string;
  message: string;
  channelsDelivered: NotificationChannel[];
  actionType: 'EXAM_DETAIL' | 'APPLICATION_GUIDE' | 'CALENDAR' | 'TIMELINE' | 'ADMIT_CARD' | 'RESULT';
  actionPayload?: any;
  priority: 'CRITICAL' | 'HIGH' | 'NORMAL';
  createdAt: string;
  scheduledDateStr?: string;
  isRead: boolean;
}

export interface TrackedExamRecord {
  examId: string;
  trackedAt: string;
}

// --- Live resources (server-refreshed, cached in SQLite) --------------------------------

/** One attachment on an SSC notice-board entry, as an absolute link on ssc.gov.in. */
export interface SscNoticeFile {
  name: string;
  url: string;
  sizeKb: number;
}

/** An entry from SSC's own notice board, read from the portal's public API. */
export interface SscNotice {
  id: string;
  headline: string;
  /** YYYY-MM-DD */
  createdAt: string;
  files: SscNoticeFile[];
  isCgl: boolean;
}

export interface SscNoticeFeed {
  items: SscNotice[];
  total: number;
  scope: 'cgl' | 'all';
  fetchedAt: string | null;
  stale: boolean;
  error: string | null;
  source: string;
  intervalHours: number;
}

/** A recent upload from a YouTube channel's public Atom feed. */
export interface ChannelUpload {
  videoId: string;
  title: string;
  /** YYYY-MM-DD */
  published: string;
  url: string;
}

export interface ChannelUploadFeed {
  items: ChannelUpload[];
  fetchedAt: string | null;
  error?: string;
}

/** A resource the verifier added at runtime from the Trust Panel — no code edit involved. */
export interface ResourceAddition {
  id: string;
  title: string;
  url: string;
  subject: string;
  resourceFormat: ResourceItem['resourceFormat'];
  author: string;
  description: string;
  addedAt: string;
  addedFrom: string;
  findingId?: number | null;
}

export interface ResourceHealthSync {
  results: ResourceLinkCheck[];
  pending: number;
  lastRun: string | null;
  intervalHours: number;
}

export interface LiveResourceStatus {
  sscFetchedAt: string | null;
  healthLastRun: string | null;
  healthTracked: number;
  healthPending: number;
  feedIntervalHours: number;
  healthIntervalHours: number;
}

// ============================================================================
// Time-Aware Behaviour-Based Recommendations
// (Inspired by Time-Decayed Bayesian Personalized Ranking Principles)
// ============================================================================

export type UserInteractionType =
  | 'SEARCH'
  | 'VIEW'
  | 'BOOKMARK'
  | 'FOLLOW'
  | 'RESOURCE_ACCESS'
  | 'SYLLABUS_READ';

export interface UserInteractionEvent {
  id: string;
  type: UserInteractionType;
  targetId?: string;
  targetType?: 'EXAM' | 'RESOURCE' | 'TOPIC' | 'SEARCH_QUERY';
  examId?: string;
  categoryTag?: ExamCategoryTag;
  timestamp: number;
  metadata?: Record<string, any>;
}

export interface ExamRecommendation {
  exam: Exam;
  /**
   * Normalized recommendation relevance score (0 - 100).
   * Represents relative relevance derived from candidate behavioral signals, time decay,
   * exam cluster affinity, and educational profile information.
   * NOT a probability of selection or an eligibility guarantee.
   */
  score: number;
  reasons: string[];
  matchStrength: 'STRONG' | 'MODERATE' | 'EXPLORATORY';
  primarySignal: string;
}

