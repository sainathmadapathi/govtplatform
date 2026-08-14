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
  diffSummary: string; // e.g. "Application deadline extended from 20 Sep → 27 Sep"
}

export interface ImportantDate {
  id: string;
  type: 'NOTIFICATION' | 'APPLICATION_OPEN' | 'APPLICATION_CLOSE' | 'ADMIT_CARD' | 'EXAM_TIER1' | 'EXAM_TIER2' | 'ANSWER_KEY' | 'RESULT';
  label: string;
  dateTimeStr: string; // e.g. "2026-09-27 23:59:00"
  timezone: string; // e.g. "Asia/Kolkata (IST)"
  isTentative: boolean;
  status: 'AVAILABLE' | 'NOT_YET_ANNOUNCED' | 'SUPERSEDED';
  provenance: DataProvenance;
}

export interface PostRequirement {
  id: string;
  postName: string;
  department: string;
  payLevel: string;
  classification: string;
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
  subject: 'Quantitative Aptitude' | 'Reasoning & General Intelligence' | 'English Comprehension' | 'General Awareness' | 'Computer Proficiency';
  topicName: string;
  parentId?: string;
  subtopics?: SyllabusTopic[];
  weightagePercentage: number;
  isCompleted?: boolean;
  officialProvenance: DataProvenance;
  weightageProvenance?: DataProvenance; // GovOS Analysis (Type D)
}

export interface ExamStage {
  id: string;
  stageNumber: number;
  stageName: string;
  durationMinutes: number;
  totalQuestions: number;
  totalMarks: number;
  negativeMarking: string;
  languages: string[];
  provenance: DataProvenance;
}

export interface QuestionOption {
  id: number;
  text: string;
}

export interface PracticeQuestion {
  id: string;
  topicId: string;
  subject: string;
  topicName: string;
  questionType: 'OFFICIAL_PYQ' | 'USER_SUBMITTED' | 'GOVOS_CREATED' | 'AI_GENERATED' | 'REFERENCE_SOURCE';
  questionText: string;
  options: QuestionOption[];
  correctOptionIndex: number;
  explanation: string;
  year?: number;
  provenance?: DataProvenance;
}

export interface CutoffEntry {
  year: number;
  category: string;
  tier1Cutoff: number;
  tier2Cutoff: number;
  provenance: DataProvenance;
}

export interface ResourceItem {
  id: string;
  title: string;
  type: 'OFFICIAL_PDF' | 'SIMPLIFIED_GUIDE' | 'RECOMMENDED_BOOK' | 'VIDEO_LECTURE';
  url: string;
  description: string;
  provenance?: DataProvenance;
}

export interface FAQItem {
  id: string;
  question: string;
  answer: string;
  officialClause: string;
  provenance: DataProvenance;
}

export interface Exam {
  id: string;
  code: string;
  title: string;
  authorityName: string;
  officialDomain: string;
  isGoldenJourney: boolean;
  isDemoData: boolean;
  overviewDescription: string;
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
  applicationSteps: {
    stepNumber: number;
    title: string;
    description: string;
    documentRequired: string;
  }[];
}

export interface UserProfile {
  dateOfBirth: string; // YYYY-MM-DD
  degree: string;
  branch: string;
  percentage: number;
  category: 'GENERAL' | 'OBC' | 'SC' | 'ST' | 'PwBD' | 'EWS';
  gender: 'Male' | 'Female' | 'Other';
  domicileState: string;
  nationality: string;
}

export interface EligibilityDiagnostic {
  isEligible: boolean;
  status: 'ELIGIBLE' | 'CONDITIONAL' | 'INELIGIBLE';
  legalClauses: string[];
  plainEnglishExplanation: string;
  postVerdicts: {
    postName: string;
    department: string;
    eligible: boolean;
    reason: string;
    clause: string;
  }[];
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

export interface SourceHealthLog {
  id: string;
  endpointUrl: string;
  authorityCode: string;
  httpStatus: number;
  checkedAt: string;
  rawContentHash: string;
  normalizedContentHash: string;
  textChanged: boolean;
  adminReviewStatus: 'HEALTHY' | 'CONFLICT_DETECTED' | 'REVIEWED';
  previousValue?: string;
  newValue?: st