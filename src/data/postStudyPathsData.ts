import { PostStudyPath, StudyModuleRequirement, ExcludedModule, DataProvenance } from '../types/exam';

const sscGazetteProvenance: DataProvenance = {
  id: 'prov-ssc-cgl-scheme-sec13',
  documentTitle: 'SSC CGL 2026 Official Gazette Notification',
  officialUrl: 'https://ssc.gov.in',
  pageNumber: 16,
  clauseNumber: 'Section 13.1 - 13.4',
  publishedDate: '2026-06-24',
  verifiedDate: '2026-08-24',
  verifiedBy: 'GovOS Legal & Directorate Verification Team',
  taxonomyType: 'FACT',
  verificationLevel: 'OFFICIALLY_VERIFIED',
  excerptText: 'The Examination will be conducted in two tiers: Tier-I (Computer Based Examination) and Tier-II (Computer Based Examination). Paper-I is compulsory for all posts. Paper-II will be for candidates who apply for the posts of Junior Statistical Officer (JSO).'
};

// ==========================================
// 1. REUSABLE CORE STUDY MODULES
// ==========================================

export const MODULE_TIER1_REASONING: StudyModuleRequirement = {
  id: 'mod-t1-reas',
  title: 'General Intelligence & Reasoning',
  subject: 'Reasoning & General Intelligence',
  stage: 'TIER_1',
  requirementType: 'OFFICIAL_REQUIREMENT',
  officialClause: 'Section 13.1.1',
  questionsCount: 25,
  marks: 50,
  negativeMarking: '-0.50 per wrong answer',
  highYieldTopics: ['Analogies (Semantic & Figural)', 'Syllogisms & Venn Diagrams', 'Coded Blood Relations', 'Number & Alphabet Series', 'Paper Folding & Mirror Images', 'Coding-Decoding'],
  keyTakeaways: 'Target score: 45+ marks. High scoring section tested with standard TCS patterns.',
  provenance: sscGazetteProvenance
};

export const MODULE_TIER1_GA: StudyModuleRequirement = {
  id: 'mod-t1-ga',
  title: 'General Awareness & Static GK',
  subject: 'General Awareness',
  stage: 'TIER_1',
  requirementType: 'OFFICIAL_REQUIREMENT',
  officialClause: 'Section 13.1.2',
  questionsCount: 25,
  marks: 50,
  negativeMarking: '-0.50 per wrong answer',
  highYieldTopics: ['Indian Polity & Constitution (Articles 14-32, Writs)', 'Static GK (Classical Dances, Gharanas, Festivals)', 'Modern History & National Movement', 'Physical & Indian Geography', 'General Science (Biology, Chemistry, Physics)', 'Recent 8-Month Current Affairs'],
  keyTakeaways: 'Focus on high-yield static GK and Constitution to secure 35+ marks quickly.',
  provenance: sscGazetteProvenance
};

export const MODULE_TIER1_QUANT: StudyModuleRequirement = {
  id: 'mod-t1-quant',
  title: 'Quantitative Aptitude',
  subject: 'Quantitative Aptitude',
  stage: 'TIER_1',
  requirementType: 'OFFICIAL_REQUIREMENT',
  officialClause: 'Section 13.1.3',
  questionsCount: 25,
  marks: 50,
  negativeMarking: '-0.50 per wrong answer',
  highYieldTopics: ['Arithmetic (Percentage, Profit & Loss, SI/CI, Ratio & Proportion)', 'Algebra (Identities, Linear & Quadratic equations)', 'Geometry (Triangles, Circles, Tangents, Similarity)', 'Trigonometry & Heights/Distances', 'Mensuration 2D & 3D', 'Data Interpretation (Bar/Pie charts)'],
  keyTakeaways: 'Master calculation shortcuts (fraction-to-percent, triplets) to complete in <22 mins.',
  provenance: sscGazetteProvenance
};

export const MODULE_TIER1_ENGLISH: StudyModuleRequirement = {
  id: 'mod-t1-eng',
  title: 'English Comprehension',
  subject: 'English Comprehension',
  stage: 'TIER_1',
  requirementType: 'OFFICIAL_REQUIREMENT',
  officialClause: 'Section 13.1.4',
  questionsCount: 25,
  marks: 50,
  negativeMarking: '-0.50 per wrong answer',
  highYieldTopics: ['60 Core Rules of Grammar (Subject-Verb, Prepositions)', 'Error Spotting & Sentence Improvement', 'Active/Passive Voice & Direct/Indirect Speech', 'Vocabulary (Synonyms, Antonyms, One Word Substitution, Idioms)', 'Cloze Test & Reading Comprehension Passages'],
  keyTakeaways: 'Highest return on investment. Daily reading and BlackBook root words guarantee 45+ marks.',
  provenance: sscGazetteProvenance
};

// --- Tier 2 Paper 1 (Common to All Posts) ---
export const MODULE_TIER2_PAPER1_MATH: StudyModuleRequirement = {
  id: 'mod-t2-p1-math',
  title: 'Tier-2 Section I Module 1: Mathematical Abilities',
  subject: 'Quantitative Aptitude',
  stage: 'TIER_2',
  requirementType: 'OFFICIAL_REQUIREMENT',
  officialClause: 'Section 13.2 (Session I Section I)',
  questionsCount: 30,
  marks: 90,
  negativeMarking: '-1.00 per wrong answer',
  highYieldTopics: ['Advanced Arithmetic & Commercial Math', 'Coordinate Geometry & Straight Lines', 'Probability & Statistics Fundamentals (Mean, Median, Mode, Variance, Standard Deviation)', 'Geometry & Circle Tangents', 'Trigonometry & Heights'],
  keyTakeaways: 'Combined with Reasoning in Section I (1 Hour total for 60 Questions, 180 Marks). Crucial for merit rank.',
  provenance: sscGazetteProvenance
};

export const MODULE_TIER2_PAPER1_REASONING: StudyModuleRequirement = {
  id: 'mod-t2-p1-reas',
  title: 'Tier-2 Section I Module 2: Reasoning and General Intelligence',
  subject: 'Reasoning & General Intelligence',
  stage: 'TIER_2',
  requirementType: 'OFFICIAL_REQUIREMENT',
  officialClause: 'Section 13.2 (Session I Section I)',
  questionsCount: 30,
  marks: 90,
  negativeMarking: '-1.00 per wrong answer',
  highYieldTopics: ['Statement & Assumptions / Course of Action', 'Critical & Analytical Reasoning', 'Complex Syllogisms & Logic Puzzles', 'Matrix & Coded Relations', 'Direction & Distance with Angle rotations'],
  keyTakeaways: 'TCS introduced critical reasoning in Tier-2. Practice statement-conclusion daily.',
  provenance: sscGazetteProvenance
};

export const MODULE_TIER2_PAPER1_ENGLISH: StudyModuleRequirement = {
  id: 'mod-t2-p1-eng',
  title: 'Tier-2 Section II Module 1: English Language and Comprehension',
  subject: 'English Comprehension',
  stage: 'TIER_2',
  requirementType: 'OFFICIAL_REQUIREMENT',
  officialClause: 'Section 13.2 (Session I Section II)',
  questionsCount: 45,
  marks: 135,
  negativeMarking: '-1.00 per wrong answer',
  highYieldTopics: ['Complex Reading Comprehension (Editorial Passages)', 'Cloze Tests (15+ blanks)', 'Para Jumbles (Sentence Rearrangement)', 'Advanced Grammar & Error Spotting', 'Idiomatic Expressions & Nuanced Vocab'],
  keyTakeaways: 'Weightiest single module in Tier-2 (135 Marks out of 390 total merit).',
  provenance: sscGazetteProvenance
};

export const MODULE_TIER2_PAPER1_GA: StudyModuleRequirement = {
  id: 'mod-t2-p1-ga',
  title: 'Tier-2 Section II Module 2: General Awareness',
  subject: 'General Awareness',
  stage: 'TIER_2',
  requirementType: 'OFFICIAL_REQUIREMENT',
  officialClause: 'Section 13.2 (Session I Section II)',
  questionsCount: 25,
  marks: 75,
  negativeMarking: '-1.00 per wrong answer',
  highYieldTopics: ['In-depth Indian Polity & Governance Acts', 'Economic Concepts (GDP, Inflation, Monetary Policy, Five Year Plans)', 'Ancient, Medieval & Modern Indian History', 'World & Indian Physical Geography', 'Environmental Treaties & Science in Everyday Life'],
  keyTakeaways: 'Decisive tie-breaker module in final merit calculation.',
  provenance: sscGazetteProvenance
};

export const MODULE_TIER2_COMPUTER_CKT: StudyModuleRequirement = {
  id: 'mod-t2-p1-comp',
  title: 'Tier-2 Section III Module 1: Computer Knowledge Test (CKT)',
  subject: 'Computer Proficiency',
  stage: 'TIER_2',
  requirementType: 'OFFICIAL_REQUIREMENT',
  officialClause: 'Section 13.2 (Session I Section III Module 1)',
  questionsCount: 20,
  marks: 60,
  negativeMarking: '-1.00 per wrong answer (Qualifying Nature)',
  highYieldTopics: ['Computer Hardware & CPU Architecture (RAM, ROM, Cache)', 'MS Office 365 (Word, Excel Formulas like VLOOKUP/XLOOKUP, PowerPoint)', 'Operating Systems (Windows 11, Linux CLI commands)', 'Internet & Networking (TCP/IP, OSI model, DNS, Cyber Security Protocols, Malware/Phishing)'],
  keyTakeaways: 'Mandatory qualifying test. Score at least 18/60 (UR), but target 30+ marks because top posts (ASO, Excise, Examiner) enforce higher qualifying cutoff.',
  provenance: sscGazetteProvenance
};

export const MODULE_TIER2_DEST_TYPING: StudyModuleRequirement = {
  id: 'mod-t2-p1-dest',
  title: 'Tier-2 Section III Module 2: Data Entry Speed Test (DEST)',
  subject: 'Computer Proficiency',
  stage: 'TIER_2',
  requirementType: 'OFFICIAL_REQUIREMENT',
  officialClause: 'Section 13.2 (Session II)',
  questionsCount: 1,
  marks: 0,
  negativeMarking: 'Qualifying (Error % calculated against 2000 keystrokes)',
  highYieldTopics: ['Typing passage of ~2000 key depressions in 15 minutes (~27 Words Per Minute)', 'Backspace key management and accuracy control', 'Mastering punctuation symbols and numerical keys'],
  keyTakeaways: 'Conducted on the same day in Session II. Permissible error: UR: 5%, OBC/EWS: 7%, SC/ST: 10%.',
  provenance: sscGazetteProvenance
};

// --- Tier 2 Paper 2 (Post-Specific for JSO ONLY) ---
export const MODULE_TIER2_PAPER2_STATISTICS: StudyModuleRequirement = {
  id: 'mod-t2-p2-stats',
  title: 'Tier-2 Paper-II: Statistics (Junior Statistical Officer ONLY)',
  subject: 'Statistics',
  stage: 'TIER_2',
  requirementType: 'OFFICIAL_REQUIREMENT',
  officialClause: 'Section 13.3 (Paper-II)',
  questionsCount: 100,
  marks: 200,
  negativeMarking: '-0.50 per wrong answer',
  highYieldTopics: ['Collection, Classification and Presentation of Statistical Data', 'Measures of Central Tendency & Dispersion (Mean, Median, Skewness, Kurtosis)', 'Correlation and Regression Analysis', 'Probability Theory & Probability Distributions (Binomial, Poisson, Normal)', 'Sampling Theory & Standard Errors', 'Index Numbers, Time Series Analysis, and Vital Statistics'],
  keyTakeaways: 'Required ONLY for candidates who opted and qualified for Junior Statistical Officer (JSO). Not applicable to any other post.',
  provenance: sscGazetteProvenance
};

// ==========================================
// 2. EXCLUDED MODULES CATALOGUE
// ==========================================

export const EXCLUDED_STATISTICS: ExcludedModule = {
  moduleId: 'mod-t2-p2-stats',
  moduleName: 'Tier-2 Paper-II: Statistics (100 Questions, 200 Marks)',
  reason: 'Not required for this post. Paper-II Statistics is strictly evaluated only for Junior Statistical Officer (JSO) in MoSPI.',
  applicableOnlyTo: 'Junior Statistical Officer (JSO) — Ministry of Statistics and Programme Implementation'
};

// ==========================================
// 3. POST-SPECIFIC TARGETED STUDY PATHS
// ==========================================

export const ALL_POST_STUDY_PATHS: Record<string, PostStudyPath> = {
  // Post 1: Assistant Section Officer (Central Secretariat Service)
  'post-aso-css': {
    postId: 'post-aso-css',
    postName: 'Assistant Section Officer (ASO)',
    department: 'Central Secretariat Service (DoPT / Government of India)',
    classification: 'Group B (Non-Gazetted)',
    payLevel: 'Pay Level 7 (₹44,900 – ₹1,42,400)',
    tier1: {
      commonModules: [MODULE_TIER1_REASONING, MODULE_TIER1_GA, MODULE_TIER1_QUANT, MODULE_TIER1_ENGLISH],
      additionalModules: [],
      excludedModules: []
    },
    tier2: {
      paper1Mandatory: true,
      paper2StatisticsRequired: false,
      computerQualifyingThreshold: 'HIGHER_CUTOFF_MANDATED_CPT',
      destTypingThreshold: 'STANDARD_QUALIFYING',
      commonModules: [
        MODULE_TIER2_PAPER1_MATH,
        MODULE_TIER2_PAPER1_REASONING,
        MODULE_TIER2_PAPER1_ENGLISH,
        MODULE_TIER2_PAPER1_GA,
        MODULE_TIER2_COMPUTER_CKT,
        MODULE_TIER2_DEST_TYPING
      ],
      additionalModules: [],
      excludedModules: [EXCLUDED_STATISTICS]
    },
    physicalMedical: {
      required: false,
      colorBlindnessAllowed: true
    }
  },

  // Post 2: Inspector of Income Tax (CBDT)
  'post-iti': {
    postId: 'post-iti',
    postName: 'Inspector of Income Tax',
    department: 'Central Board of Direct Taxes (CBDT), Department of Revenue',
    classification: 'Group B (Non-Gazetted)',
    payLevel: 'Pay Level 7 (₹44,900 – ₹1,42,400)',
    tier1: {
      commonModules: [MODULE_TIER1_REASONING, MODULE_TIER1_GA, MODULE_TIER1_QUANT, MODULE_TIER1_ENGLISH],
      additionalModules: [],
      excludedModules: []
    },
    tier2: {
      paper1Mandatory: true,
      paper2StatisticsRequired: false,
      computerQualifyingThreshold: 'STANDARD_18_MARKS_QUALIFYING',
      destTypingThreshold: 'STANDARD_QUALIFYING',
      commonModules: [
        MODULE_TIER2_PAPER1_MATH,
        MODULE_TIER2_PAPER1_REASONING,
        MODULE_TIER2_PAPER1_ENGLISH,
        MODULE_TIER2_PAPER1_GA,
        MODULE_TIER2_COMPUTER_CKT,
        MODULE_TIER2_DEST_TYPING
      ],
      additionalModules: [],
      excludedModules: [EXCLUDED_STATISTICS]
    },
    physicalMedical: {
      required: false,
      colorBlindnessAllowed: true
    }
  },

  // Post 3: Inspector (Central Excise / GST)
  'post-excise': {
    postId: 'post-excise',
    postName: 'Inspector (Central Excise & GST)',
    department: 'Central Board of Indirect Taxes and Customs (CBIC)',
    classification: 'Group B (Non-Gazetted)',
    payLevel: 'Pay Level 7 (₹44,900 – ₹1,42,400)',
    tier1: {
      commonModules: [MODULE_TIER1_REASONING, MODULE_TIER1_GA, MODULE_TIER1_QUANT, MODULE_TIER1_ENGLISH],
      additionalModules: [],
      excludedModules: []
    },
    tier2: {
      paper1Mandatory: true,
      paper2StatisticsRequired: false,
      computerQualifyingThreshold: 'HIGHER_CUTOFF_MANDATED_CPT',
      destTypingThreshold: 'STANDARD_QUALIFYING',
      commonModules: [
        MODULE_TIER2_PAPER1_MATH,
        MODULE_TIER2_PAPER1_REASONING,
        MODULE_TIER2_PAPER1_ENGLISH,
        MODULE_TIER2_PAPER1_GA,
        MODULE_TIER2_COMPUTER_CKT,
        MODULE_TIER2_DEST_TYPING
      ],
      additionalModules: [],
      excludedModules: [EXCLUDED_STATISTICS]
    },
    physicalMedical: {
      required: true,
      maleHeightChest: 'Height: 157.5 cm (relaxable by 5cm for ST/Hill areas) | Chest: 81 cm (fully expanded with min. 5cm expansion)',
      femaleHeightWeight: 'Height: 152 cm (relaxable by 2.5cm) | Weight: 48 kg (relaxable by 2kg)',
      physicalTest: 'Male: Walking 1600 meters in 15 mins, Cycling 8 km in 30 mins | Female: Walking 1 km in 20 mins, Cycling 3 km in 25 mins',
      colorBlindnessAllowed: false
    }
  },

  // Post 4: Junior Statistical Officer (JSO) - THE ONLY POST REQUIRING STATISTICS
  'post-jso': {
    postId: 'post-jso',
    postName: 'Junior Statistical Officer (JSO)',
    department: 'Ministry of Statistics and Programme Implementation (MoSPI)',
    classification: 'Group B (Non-Gazetted)',
    payLevel: 'Pay Level 6 (₹35,400 – ₹1,12,400)',
    tier1: {
      commonModules: [MODULE_TIER1_REASONING, MODULE_TIER1_GA, MODULE_TIER1_QUANT, MODULE_TIER1_ENGLISH],
      additionalModules: [],
      excludedModules: []
    },
    tier2: {
      paper1Mandatory: true,
      paper2StatisticsRequired: true,
      computerQualifyingThreshold: 'STANDARD_18_MARKS_QUALIFYING',
      destTypingThreshold: 'STANDARD_QUALIFYING',
      commonModules: [
        MODULE_TIER2_PAPER1_MATH,
        MODULE_TIER2_PAPER1_REASONING,
        MODULE_TIER2_PAPER1_ENGLISH,
        MODULE_TIER2_PAPER1_GA,
        MODULE_TIER2_COMPUTER_CKT,
        MODULE_TIER2_DEST_TYPING
      ],
      additionalModules: [MODULE_TIER2_PAPER2_STATISTICS], // MANDATORY SPECIAL PAPER
      excludedModules: [] // Nothing excluded, both Paper 1 & Paper 2 required
    },
    physicalMedical: {
      required: false,
      colorBlindnessAllowed: true
    }
  },

  // Post 5: Sub-Inspector (Central Bureau of Investigation - CBI)
  'post-cbi-si': {
    postId: 'post-cbi-si',
    postName: 'Sub-Inspector (CBI)',
    department: 'Central Bureau of Investigation (CBI), Department of Personnel and Training',
    classification: 'Group B (Non-Gazetted)',
    payLevel: 'Pay Level 7 (₹44,900 – ₹1,42,400)',
    tier1: {
      commonModules: [MODULE_TIER1_REASONING, MODULE_TIER1_GA, MODULE_TIER1_QUANT, MODULE_TIER1_ENGLISH],
      additionalModules: [],
      excludedModules: []
    },
    tier2: {
      paper1Mandatory: true,
      paper2StatisticsRequired: false,
      computerQualifyingThreshold: 'STANDARD_18_MARKS_QUALIFYING',
      destTypingThreshold: 'STANDARD_QUALIFYING',
      commonModules: [
        MODULE_TIER2_PAPER1_MATH,
        MODULE_TIER2_PAPER1_REASONING,
        MODULE_TIER2_PAPER1_ENGLISH,
        MODULE_TIER2_PAPER1_GA,
        MODULE_TIER2_COMPUTER_CKT,
        MODULE_TIER2_DEST_TYPING
      ],
      additionalModules: [],
      excludedModules: [EXCLUDED_STATISTICS]
    },
    physicalMedical: {
      required: true,
      maleHeightChest: 'Height: 165 cm (Male) | Chest: 76 cm with expansion',
      femaleHeightWeight: 'Height: 150 cm (Female)',
      physicalTest: 'Vision standard: Distant vision 6/6 in one and 6/9 in other eye with or without correction. Near vision: 0.6 in one and 0.8 in other.',
      colorBlindnessAllowed: false
    }
  },

  // Post 6: Tax Assistant (CBDT / CBIC)
  'post-tax-asst': {
    postId: 'post-tax-asst',
    postName: 'Tax Assistant (TA)',
    department: 'Central Board of Direct Taxes (CBDT) & Central Board of Indirect Taxes (CBIC)',
    classification: 'Group C',
    payLevel: 'Pay Level 4 (₹25,500 – ₹81,100)',
    tier1: {
      commonModules: [MODULE_TIER1_REASONING, MODULE_TIER1_GA, MODULE_TIER1_QUANT, MODULE_TIER1_ENGLISH],
      additionalModules: [],
      excludedModules: []
    },
    tier2: {
      paper1Mandatory: true,
      paper2StatisticsRequired: false,
      computerQualifyingThreshold: 'STANDARD_18_MARKS_QUALIFYING',
      destTypingThreshold: 'HIGHER_ACCURACY_MANDATED', // High accuracy required
      commonModules: [
        MODULE_TIER2_PAPER1_MATH,
        MODULE_TIER2_PAPER1_REASONING,
        MODULE_TIER2_PAPER1_ENGLISH,
        MODULE_TIER2_PAPER1_GA,
        MODULE_TIER2_COMPUTER_CKT,
        MODULE_TIER2_DEST_TYPING
      ],
      additionalModules: [],
      excludedModules: [EXCLUDED_STATISTICS]
    },
    physicalMedical: {
      required: false,
      colorBlindnessAllowed: true
    }
  },

  // Post 7: Auditor (Office of C&AG / CGA / CGDA)
  'post-auditor': {
    postId: 'post-auditor',
    postName: 'Auditor',
    department: 'Comptroller and Auditor General of India (C&AG) / CGA',
    classification: 'Group C',
    payLevel: 'Pay Level 5 (₹29,200 – ₹92,300)',
    tier1: {
      commonModules: [MODULE_TIER1_REASONING, MODULE_TIER1_GA, MODULE_TIER1_QUANT, MODULE_TIER1_ENGLISH],
      additionalModules: [],
      excludedModules: []
    },
    tier2: {
      paper1Mandatory: true,
      paper2StatisticsRequired: false,
      computerQualifyingThreshold: 'STANDARD_18_MARKS_QUALIFYING',
      destTypingThreshold: 'STANDARD_QUALIFYING',
      commonModules: [
        MODULE_TIER2_PAPER1_MATH,
        MODULE_TIER2_PAPER1_REASONING,
        MODULE_TIER2_PAPER1_ENGLISH,
        MODULE_TIER2_PAPER1_GA,
        MODULE_TIER2_COMPUTER_CKT,
        MODULE_TIER2_DEST_TYPING
      ],
      additionalModules: [],
      excludedModules: [EXCLUDED_STATISTICS]
    },
    physicalMedical: {
      required: false,
      colorBlindnessAllowed: true
    }
  }
};
