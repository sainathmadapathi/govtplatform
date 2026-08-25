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
  type: 'NOTIFICATION' | 'APPLICATION_OPEN' | 'APPLICATION_CLOSE' | 'ADMIT_CARD' | 'EXAM_TIER1' | 'EXAM_TIER2' | 'ANSWER_KEY' | 'RESULT';
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
  classification: 'Group B (Gazetted)' | 'Group B (Non-Gazetted)' | 'Group C';
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

export interface PracticeQuestion {
  id: string;
  topicId: string;
  subject: string;
  topicName: string;
  tier: 'TIER_1' | 'TIER_2';
  shiftInfo: string;
  questionType: 'OFFICIAL_PYQ' | 'USER_SUBMITTED' | 'GOVOS_CREATED' | 'AI_GENERATED' | 'REFERENCE_SOURCE';
  questionText: string;
  options: QuestionOption[];
  correctOptionIndex: number;
  explanation: string;
  year?: number;
  difficulty: 'EASY' | 'MEDIUM' | 'HARD';
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
  subject: 'Quantitative Aptitude' | 'English Comprehension' | 'Reasoning' | 'General Awareness & Static GK' | 'Computer & Typing' | 'Official Gazette';
  author: string;
  type: 'OFFICIAL_PDF' | 'SIMPLIFIED_GUIDE' | 'RECOMMENDED_BOOK' | 'VIDEO_LECTURE' | 'ONLINE_TOOL';
  resourceFormat: 'DIRECT_PDF' | 'YOUTUBE_COURSE' | 'INTERACTIVE_HANDBOOK' | 'ONLINE_TOOL';
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
}

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

export interface Exam {
  id: string;
  code: string;
  title: string;
  authorityName: string;
  officialDomain: string;
  crucialEligibilityDate: string;
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

export interface UserReport {
  id: string;
  entityType: string;
  entityId: string;
  issueCategory: 'WRONG_ELIGIBILITY' | 'OUTDATED_DATE' | 'BROKEN_LINK' | 'INCORRECT_QUESTION';
  description: string;
  createdAt: string;
  adminStatus: 'PENDING' | 'RESOLVED' | 'REJECTED';
}
