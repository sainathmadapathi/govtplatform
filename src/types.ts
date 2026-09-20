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
  type: 'NOTIFICATION' | 'APPLICATION_OPEN' | 'APPLICATION_CLOSE' | 'CORRECTION_WINDOW' | 'ADMIT_CARD' | 'EXAM_TIER1' | 'EXAM_TIER2' | 'ANSWER_KEY' | 'RESULT' | 'INTERVIEW';
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

/**
 * One age relaxation exactly as an authority published it.
 *
 * Both printed forms are kept because authorities use both and converting between them
 * needs the base limit plus arithmetic nobody published: `years` is an increment on the
 * upper limit ("relaxable by 5 years"), `maximumAge` is the limit itself ("the upper age
 * limit for X is 40 years").
 *
 * `category` is the authority's own wording, not a code. `NOT_PUBLISHED` is used where a
 * notice states that a group receives no relaxation, which is a fact about the authority
 * and different from the platform simply not having one.
 */
export interface AgeRelaxationEntry {
  category: string;
  years?: number;
  maximumAge?: number;
  condition?: string;
  /** Present only where the authority scoped the relaxation to one post. */
  appliesToPostId?: string;
  status: 'VERIFIED' | 'NEEDS_REVIEW' | 'NOT_PUBLISHED';
  provenance: DataProvenance;
}

export interface RuleGroup {
  id: string;
  operator: 'AND' | 'OR';
  rules: EligibilityRule[];
  childGroups?: RuleGroup[];
}

/**
 * Every subject a syllabus topic may belong to. The first six are SSC CGL's sections; the
 * rest are the areas UPSC's notice names for the Preliminary and Main examinations.
 */
export type SyllabusSubject =
  | 'Quantitative Aptitude' | 'Reasoning & General Intelligence' | 'English Comprehension'
  | 'General Awareness' | 'Computer Proficiency' | 'Statistics'
  | 'History & Culture' | 'Geography' | 'Polity & Governance' | 'Economy'
  | 'Environment & Ecology' | 'Science & Technology' | 'Current Affairs'
  | 'CSAT (Aptitude & Reasoning)' | 'Ethics, Integrity & Aptitude' | 'Essay & Answer Writing'
  | 'International Relations & Security' | 'Optional Subject' | 'Indian Language & English (Qualifying)';

export interface SyllabusTopic {
  id: string;
  subject: SyllabusSubject;
  tier: 'TIER_1' | 'TIER_2' | 'BOTH';
  topicName: string;
  parentId?: string;
  subtopics?: string[];
  weightagePercentage: number;
  avgQuestions: number;
  isHighYield: boolean;
  officialProvenance: DataProvenance;
  weightageProvenance?: DataProvenance;
  /** Set when a verifier changed this topic at runtime; names the notice it came from. */
  revision?: {
    id: string;
    kind: 'ADD' | 'AMEND';
    noticeTitle?: string | null;
    noticeUrl?: string | null;
    noticeDate?: string | null;
    appliedAt: string;
    appliedBy: string;
  };
}

export interface ExamStage {
  id: string;
  stageNumber: number;
  stageName: string;
  /** TIER_1 / TIER_2 are the written stages; INTERVIEW is a personality test with no paper. */
  tier: 'TIER_1' | 'TIER_2' | 'INTERVIEW';
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

export interface MultiTierResultEntry {
  marks: number;
  category: string;
  source: string;
  declared?: string;
  examId?: string;
  examType?: 'SSC_CGL' | 'UPSC_CSE' | 'IBPS_PO' | 'APPSC' | 'GENERIC';
  // SSC specific
  tier1Marks?: number;
  tier2Marks?: number;
  computerKnowledgeMarks?: number;
  destMistakesPercent?: number;
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
  // Common metadata
  examYear?: number;
  rollNumber?: string;
  candidateName?: string;
  allocatedPost?: string;
}

export interface InAppChapter {
  chapterTitle: string;
  contentMarkdown: string;
}

/**
 * A question taken from an authority's own published question paper.
 *
 * Three rules this type exists to enforce:
 *   - `examId` is the exact register id and is stored on the record. A question's exam is never
 *     inferred from its subject, its wording, its paper title or the screen it is shown on.
 *   - `officialAnswerKey` is `null` wherever the authority has not published a key. It is never
 *     filled in by inference — an unkeyed question is shown unkeyed, or not shown at all.
 *   - `provenance` names the exact document and page, so every item can be checked against the
 *     original before it is trusted.
 */
export interface OfficialPaperQuestion {
  id: string;
  /** The exact exam this belongs to. Only that exam's engine may load it. */
  examId: string;
  /** The paper it was printed in, as the authority names it. */
  paperName: string;
  paperYear: number;
  stage: 'PRELIMS' | 'MAINS';
  section?: string;
  questionNumber: number;
  /** The question as printed. English text only; bilingual papers keep their English side. */
  promptEnglish: string;
  marks: number;
  /**
   * DESCRIPTIVE papers have no option key and are not machine-scored — that is how the
   * authority marks them too, so GovOS does not invent a score for them.
   */
  answerFormat: 'DESCRIPTIVE' | 'MCQ';
  options?: string[];
  /** null when the authority has published no answer key. Never guessed. */
  officialAnswerKey: string | null;
  officialAnswerKeyNote?: string;
  provenance: DataProvenance;
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
    | 'Official Gazette'
    | 'History & Culture'
    | 'Geography & Environment'
    | 'Polity & Governance'
    | 'Economy'
    | 'Science & Technology'
    | 'Ethics, Essay & Answer Writing'
    | 'CSAT & Aptitude'
    | 'Previous Year Papers'
    | 'Optional Subjects';
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
  subject: SyllabusSubject;
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

/**
 * A mock application form, authored from one exam's own notice.
 *
 * The simulator component holds no form content of its own: every module, field, option
 * and trap below is read from the authority's document and names the page it came from,
 * so the practice form cannot drift from the real one and cannot inherit another exam's
 * shape. `examId` is checked before anything renders — a spec is served to exactly one exam.
 */
export interface ApplicationSimulatorField {
  id: string;
  label: string;
  kind: 'TEXT' | 'DATE' | 'SELECT' | 'RADIO';
  /** Prefilled so the candidate edits a realistic form rather than typing one from blank. */
  defaultValue: string;
  options?: { value: string; label: string }[];
  /** What the notice itself says about this field, shown under the input. */
  noteFromNotice?: string;
}

export interface ApplicationSimulatorModule {
  moduleNumber: number;
  /** The portal's own name for this card/module, not a name GovOS invented. */
  cardName: string;
  title: string;
  introduction: string;
  /** Where in the source document this module is described. */
  noticeReference: string;
  fields: ApplicationSimulatorField[];
}

/**
 * When a mistake fires. Every rule is a fact the notice states, never a guess:
 * - VALUE_IN      the candidate picked an option the notice rules out
 * - VALUE_IN_ALL  a combination the notice rules out (e.g. claiming a fee exemption
 *                 that the candidate's own category does not carry)
 * - DATE_OUTSIDE  a date outside the window the notice prints
 */
export type ApplicationSimulatorRule =
  | { kind: 'VALUE_IN'; fieldId: string; values: string[] }
  | { kind: 'VALUE_IN_ALL'; conditions: { fieldId: string; values: string[] }[] }
  | { kind: 'DATE_OUTSIDE'; fieldId: string; earliest: string; latest: string };

export interface ApplicationSimulatorTrap {
  id: string;
  rule: ApplicationSimulatorRule;
  severity: 'CRITICAL' | 'WARNING';
  title: string;
  problem: string;
  whyItMatters: string;
  rememberRule: string;
  /** The notice's own wording, and where it sits. */
  officialClause: string;
  noticeReference: string;
}

export interface ApplicationSimulatorSpec {
  /** The one exam this form belongs to. Checked before render; never defaulted. */
  examId: string;
  portalName: string;
  portalUrl: string;
  sourceDocumentTitle: string;
  sourceDocumentUrl: string;
  /** One line naming what the mock form is modelled on, shown above it. */
  modelledOnNote: string;
  modules: ApplicationSimulatorModule[];
  traps: ApplicationSimulatorTrap[];
  /** Shown when a submission trips no trap at all. */
  cleanSubmissionNote: string;
  provenance: DataProvenance;
}

export interface ApplicationGuideData {
  officialPortal: string;
  /** Present only where the exam's own form has been authored from its own notice. */
  simulator?: ApplicationSimulatorSpec;
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
  /** The eligibility cards shown in section 03 — each exam states its own rules, cited. */
  eligibilityHighlights?: { title: string; body: string; provenance: DataProvenance }[];
  /** The portals listed in section 12 — the authority's own, plus the ones its notice sends candidates to. */
  officialLinks?: { title: string; url: string; note: string }[];
  /** One line naming the document and section the syllabus was read from. */
  syllabusSourceNote?: string;
  /**
   * Age relaxations this authority published, each cited. Absent where the exam's notice
   * has not been read for them — which is not the same as the authority granting none, and
   * the UI must not present it as such.
   */
  ageRelaxations?: AgeRelaxationEntry[];
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

/** The fields a verifier may set when adding or amending a syllabus topic. */
export interface SyllabusRevisionTopic {
  subject?: SyllabusTopic['subject'];
  tier?: SyllabusTopic['tier'];
  topicName?: string;
  subtopics?: string[];
  weightagePercentage?: number | null;
  avgQuestions?: number | null;
  isHighYield?: boolean | null;
}

/**
 * One verifier decision about the syllabus, stored on the server and merged over the
 * register's seed at runtime. ADD brings a topic in, AMEND changes fields of an existing
 * one, RETIRE hides one. Each cites the notice it was read from.
 */
export interface SyllabusRevision {
  id: string;
  examId: string;
  kind: 'ADD' | 'AMEND' | 'RETIRE';
  topicId?: string | null;
  topic?: SyllabusRevisionTopic | null;
  note?: string | null;
  noticeTitle?: string | null;
  noticeUrl?: string | null;
  noticeDate?: string | null;
  appliedAt: string;
  appliedBy: string;
}

/** Notices on the live board that may change a syllabus, dated after it was verified. */
export interface SyllabusWatch {
  items: SscNotice[];
  fetchedAt: string | null;
  stale: boolean;
  error: string | null;
  /** null when no live board is wired for the exam. */
  source: string | null;
  note?: string;
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

// --- Conversation context, shared by every chat in the platform ---------------------------

/** Which chat a turn belongs to. History is kept per channel, context is shared. */
export type ChatChannel = 'ASSISTANT' | 'PRACTICE' | 'RESOURCES';

/** Where the candidate stands in this exam's cycle, derived from the exam's own dates. */
export type CandidateStage =
  | 'BEFORE_NOTIFICATION'
  | 'APPLICATION_OPEN'
  | 'APPLICATION_CLOSED'
  | 'PRE_EXAM'
  | 'POST_EXAM';

/**
 * One turn of a conversation. The assistant records what it took the turn to be about, so
 * the next message ("when is it?", "make it harder") can inherit that subject instead of
 * being read as a fresh, contextless question.
 */
export interface ConversationTurn {
  role: 'user' | 'assistant';
  text: string;
  /** Intent the assistant settled on: 'dates', 'eligibility', 'practice', 'resource'… */
  intent?: string;
  /** Plain-language subject of the turn, used to expand a later follow-up. */
  subject?: string;
  examId?: string;
  /** Practice chat only: what was built, so "20 of those, harder" works. */
  topics?: string[];
  count?: number;
  difficulty?: string;
  at: string;
}

/**
 * Everything a chat should weigh before answering, in the platform's priority order:
 * the message, then recent turns, then the active exam/post, then the candidate's own
 * profile and progress, then the verified register.
 */
export interface ChatContext {
  channel: ChatChannel;
  exam: Exam;
  targetPost?: PostRequirement;
  profile?: UserProfile | null;
  stage: CandidateStage;
  /** Days until the application closes; negative once it has closed. Null when unknown. */
  daysToApplicationClose?: number | null;
  history: ConversationTurn[];
}
