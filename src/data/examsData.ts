import { Exam, DataProvenance } from '../types/exam';

const sscProvenanceOverview: DataProvenance = {
  id: 'prov-ssc-01',
  documentTitle: 'SSC CGL 2026 Official Notice.pdf',
  officialUrl: 'https://ssc.gov.in/api/attachment/notice/ssc_cgl_2026_notification.pdf',
  pageNumber: 1,
  clauseNumber: 'Section 1.1',
  publishedDate: '2026-08-10',
  verifiedDate: '2026-08-11',
  verifiedBy: 'Senior Verification Officer #104',
  taxonomyType: 'FACT',
  verificationLevel: 'OFFICIALLY_VERIFIED'
};

const sscProvenanceEligibility: DataProvenance = {
  id: 'prov-ssc-02',
  documentTitle: 'SSC CGL 2026 Official Notice.pdf',
  officialUrl: 'https://ssc.gov.in/api/attachment/notice/ssc_cgl_2026_notification.pdf',
  pageNumber: 12,
  clauseNumber: 'Section 3.1 (Age & Education Criteria)',
  publishedDate: '2026-08-10',
  verifiedDate: '2026-08-11',
  verifiedBy: 'Senior Verification Officer #104',
  taxonomyType: 'FACT',
  verificationLevel: 'OFFICIALLY_VERIFIED'
};

const sscProvenanceDates: DataProvenance = {
  id: 'prov-ssc-03',
  documentTitle: 'SSC CGL 2026 Corrigendum Notice #02.pdf',
  officialUrl: 'https://ssc.gov.in/api/attachment/notice/cgl_2026_corrigendum_02.pdf',
  pageNumber: 1,
  clauseNumber: 'Clause 2 (Extended Deadline)',
  publishedDate: '2026-08-22',
  verifiedDate: '2026-08-22',
  verifiedBy: 'Senior Verification Officer #104',
  taxonomyType: 'FACT',
  verificationLevel: 'OFFICIALLY_VERIFIED'
};

const sscProvenanceGovOSAnalysis: DataProvenance = {
  id: 'prov-ssc-04',
  documentTitle: 'GovOS PYQ Trend Analysis (2021-2025)',
  officialUrl: 'https://ssc.gov.in',
  publishedDate: '2026-08-14',
  verifiedDate: '2026-08-14',
  verifiedBy: 'GovOS Research Team',
  taxonomyType: 'RECOMMENDATION',
  verificationLevel: 'OFFICIALLY_VERIFIED'
};

export const SSC_CGL_EXAM: Exam = {
  id: 'exam-ssc-cgl-2026',
  code: 'SSC_CGL_2026',
  title: 'SSC Combined Graduate Level (CGL) 2026',
  authorityName: 'Staff Selection Commission (SSC)',
  officialDomain: 'https://ssc.gov.in',
  isGoldenJourney: true,
  isDemoData: true,
  overviewDescription: 'The SSC CGL Examination is conducted annually for recruitment to various Group B and Group C Non-Technical gazetted and non-gazetted posts across Ministries, Departments, and Secretariats of the Government of India (Pay Level 4 to Pay Level 8).',
  
  posts: [
    {
      id: 'post-aso',
      postName: 'Assistant Section Officer (ASO)',
      department: 'Central Secretariat Service (CSS) / MEA / IB',
      payLevel: 'Pay Level 7 (₹44,900 to ₹1,42,400)',
      classification: 'Group B (Non-Gazetted)',
      provenance: sscProvenanceEligibility
    },
    {
      id: 'post-iti',
      postName: 'Inspector of Income Tax',
      department: 'Central Board of Direct Taxes (CBDT)',
      payLevel: 'Pay Level 7 (₹44,900 to ₹1,42,400)',
      classification: 'Group B (Non-Gazetted)',
      provenance: sscProvenanceEligibility
    },
    {
      id: 'post-excise',
      postName: 'Inspector (Central Excise / GST)',
      department: 'Central Board of Indirect Taxes & Customs (CBIC)',
      payLevel: 'Pay Level 7 (₹44,900 to ₹1,42,400)',
      classification: 'Group B (Non-Gazetted)',
      provenance: sscProvenanceEligibility
    },
    {
      id: 'post-jso',
      postName: 'Junior Statistical Officer (JSO)',
      department: 'Ministry of Statistics & Programme Implementation (MoSPI)',
      payLevel: 'Pay Level 6 (₹35,400 to ₹1,12,400)',
      classification: 'Group B (Non-Gazetted)',
      ruleGroup: {
        id: 'rg-jso',
        operator: 'OR',
        rules: [
          {
            id: 'rule-jso-math',
            ruleType: 'DEGREE_REQUIRED',
            operator: '=',
            ruleValue: 'Bachelor Degree with 60% in Mathematics at 12th standard',
            category: 'GENERAL',
            provenance: sscProvenanceEligibility
          },
          {
            id: 'rule-jso-stat',
            ruleType: 'DEGREE_REQUIRED',
            operator: '=',
            ruleValue: 'Bachelor Degree with Statistics as a subject in all 3 years',
            category: 'GENERAL',
            provenance: sscProvenanceEligibility
          }
        ]
      },
      provenance: sscProvenanceEligibility
    },
    {
      id: 'post-auditor',
      postName: 'Auditor / Accountant',
      department: 'Offices under C&AG / CGDA',
      payLevel: 'Pay Level 5 (₹29,200 to ₹92,300)',
      classification: 'Group C',
      provenance: sscProvenanceEligibility
    }
  ],

  dates: [
    {
      id: 'date-01',
      type: 'NOTIFICATION',
      label: 'Official Notification Release',
      dateTimeStr: '2026-08-10 17:00:00',
      timezone: 'Asia/Kolkata (IST)',
      isTentative: false,
      status: 'AVAILABLE',
      provenance: sscProvenanceOverview
    },
    {
      id: 'date-02',
      type: 'APPLICATION_OPEN',
      label: 'Online Application Window Opens',
      dateTimeStr: '2026-08-15 10:00:00',
      timezone: 'Asia/Kolkata (IST)',
      isTentative: false,
      status: 'AVAILABLE',
      provenance: sscProvenanceOverview
    },
    {
      id: 'date-03',
      type: 'APPLICATION_CLOSE',
      label: 'Online Application Deadline (Extended via Corrigendum #02)',
      dateTimeStr: '2026-09-27 23:59:00',
      timezone: 'Asia/Kolkata (IST)',
      isTentative: false,
      status: 'AVAILABLE',
      provenance: sscProvenanceDates
    },
    {
      id: 'date-04',
      type: 'ADMIT_CARD',
      label: 'Tier-1 City Intimation & Admit Card Release',
      dateTimeStr: '2026-10-15 10:00:00',
      timezone: 'Asia/Kolkata (IST)',
      isTentative: true,
      status: 'AVAILABLE',
      provenance: sscProvenanceOverview
    },
    {
      id: 'date-05',
      type: 'EXAM_TIER1',
      label: 'Tier-1 Computer Based Exam Window',
      dateTimeStr: '2026-10-28 09:00:00',
      timezone: 'Asia/Kolkata (IST)',
      isTentative: false,
      status: 'AVAILABLE',
      provenance: sscProvenanceOverview
    },
    {
      id: 'date-06',
      type: 'ANSWER_KEY',
      label: 'Tentative Answer Key & Objection Window',
      dateTimeStr: '2026-11-12 14:00:00',
      timezone: 'Asia/Kolkata (IST)',
      isTentative: true,
      status: 'AVAILABLE',
      provenance: sscProvenanceOverview
    },
    {
      id: 'date-07',
      type: 'RESULT',
      label: 'Tier-1 Official Result Declaration',
      dateTimeStr: '2026-12-05 18:00:00',
      timezone: 'Asia/Kolkata (IST)',
      isTentative: true,
      status: 'AVAILABLE',
      provenance: sscProvenanceOverview
    }
  ],

  globalRuleGroup: {
    id: 'rg-cgl-global',
    operator: 'AND',
    rules: [
      {
        id: 'rule-age-min',
        ruleType: 'AGE_MIN',
        operator: '>=',
        ruleValue: 18,
        category: 'GENERAL',
        provenance: sscProvenanceEligibility
      },
      {
        id: 'rule-age-max',
        ruleType: 'AGE_MAX',
        operator: '<=',
        ruleValue: 27,
        category: 'GENERAL',
        provenance: sscProvenanceEligibility
      },
      {
        id: 'rule-dob-cutoff',
        ruleType: 'DOB_CUTOFF',
        operator: '=',
        ruleValue: '01-08-2026',
        category: 'GENERAL',
        provenance: sscProvenanceEligibility
      },
      {
        id: 'rule-degree',
        ruleType: 'DEGREE_REQUIRED',
        operator: '=',
        ruleValue: ['Bachelor Degree', 'Graduation', 'B.Tech', 'B.E', 'B.Sc', 'B.Com', 'B.A', 'BBA', 'BCA'],
        category: 'GENERAL',
        provenance: sscProvenanceEligibility
      },
      {
        id: 'rule-nationality',
        ruleType: 'NATIONALITY',
        operator: '=',
        ruleValue: 'Citizen of India',
        category: 'GENERAL',
        provenance: sscProvenanceEligibility
      }
    ]
  },

  stages: [
    {
      id: 'stage-tier-1',
      stageNumber: 1,
      stageName: 'Tier 1 — Preliminary Computer Based Test (Screening)',
      durationMinutes: 60,
      totalQuestions: 100,
      totalMarks: 200,
      negativeMarking: '0.50 marks deducted per wrong answer',
      languages: ['English', 'Hindi'],
      provenance: sscProvenanceOverview
    },
    {
      id: 'stage-tier-2',
      stageNumber: 2,
      stageName: 'Tier 2 — Mains Examination (Session I: Math, Reasoning, English, GA, Computer + Session II: Data Entry)',
      durationMinutes: 150,
      totalQuestions: 130,
      totalMarks: 390,
      negativeMarking: '1.00 mark deducted per wrong answer in Section I & II',
      languages: ['English', 'Hindi'],
      provenance: sscProvenanceOverview
    }
  ],

  syllabus: [
    {
      id: 'syl-quant',
      subject: 'Quantitative Aptitude',
      topicName: 'Quantitative Aptitude (Mathematics)',
      weightagePercentage: 25.0,
      officialProvenance: sscProvenanceOverview,
      weightageProvenance: sscProvenanceGovOSAnalysis,
      subtopics: [
        {
          id: 'syl-quant-1',
          subject: 'Quantitative Aptitude',
          topicName: 'Number Systems & Simplification',
          weightagePercentage: 4.0,
          isCompleted: true,
          officialProvenance: sscProvenanceOverview,
          weightageProvenance: sscProvenanceGovOSAnalysis
        },
        {
          id: 'syl-quant-2',
          subject: 'Quantitative Aptitude',
          topicName: 'Percentage, Ratio & Proportion',
          weightagePercentage: 5.0,
          isCompleted: true,
          officialProvenance: sscProvenanceOverview,
          weightageProvenance: sscProvenanceGovOSAnalysis
        },
        {
          id: 'syl-quant-3',
          subject: 'Quantitative Aptitude',
          topicName: 'Profit, Loss & Discount',
          weightagePercentage: 4.0,
          isCompleted: false,
          officialProvenance: sscProvenanceOverview,
          weightageProvenance: sscProvenanceGovOSAnalysis
        },
        {
          id: 'syl-quant-4',
          subject: 'Quantitative Aptitude',
          topicName: 'Time & Work, Pipes & Cisterns',
          weightagePercentage: 4.0,
          isCompleted: false,
          officialProvenance: sscProvenanceOverview,
          weightageProvenance: sscProvenanceGovOSAnalysis
        },
        {
          id: 'syl-quant-5',
          subject: 'Quantitative Aptitude',
          topicName: 'Algebra & Quadratic Equations',
          weightagePercentage: 4.0,
          isCompleted: false,
          officialProvenance: sscProvenanceOverview,
          weightageProvenance: sscProvenanceGovOSAnalysis
        },
        {
          id: 'syl-quant-6',
          subject: 'Quantitative Aptitude',
          topicName: 'Geometry & Mensuration (2D & 3D)',
          weightagePercentage: 4.0,
          isCompleted: false,
          officialProvenance: sscProvenanceOverview,
          weightageProvenance: sscProvenanceGovOSAnalysis
        }
      ]
    },
    {
      id: 'syl-reasoning',
      subject: 'Reasoning & General Intelligence',
      topicName: 'Reasoning & General Intelligence',
      weightagePercentage: 25.0,
      officialProvenance: sscProvenanceOverview,
      weightageProvenance: sscProvenanceGovOSAnalysis,
      subtopics: [
        {
          id: 'syl-reas-1',
          subject: 'Reasoning & General Intelligence',
          topicName: 'Analogy & Classification',
          weightagePercentage: 5.0,
          isCompleted: true,
          officialProvenance: sscProvenanceOverview,
          weightageProvenance: sscProvenanceGovOSAnalysis
        },
        {
          id: 'syl-reas-2',
          subject: 'Reasoning & General Intelligence',
          topicName: 'Coding-Decoding & Series Completion',
          weightagePercentage: 6.0,
          isCompleted: true,
          officialProvenance: sscProvenanceOverview,
          weightageProvenance: sscProvenanceGovOSAnalysis
        },
        {
          id: 'syl-reas-3',
          subject: 'Reasoning & General Intelligence',
          topicName: 'Syllogism & Venn Diagrams',
          weightagePercentage: 4.0,
          isCompleted: false,
          officialProvenance: sscProvenanceOverview,
          weightageProvenance: sscProvenanceGovOSAnalysis
        },
        {
          id: 'syl-reas-4',
          subject: 'Reasoning & General Intelligence',
          topicName: 'Blood Relations & Direction Sense',
          weightagePercentage: 4.0,
          isCompleted: false,
          officialProvenance: sscProvenanceOverview,
          weightageProvenance: sscProvenanceGovOSAnalysis
        },
        {
          id: 'syl-reas-5',
          subject: 'Reasoning & General Intelligence',
          topicName: 'Non-Verbal Reasoning (Paper Folding, Mirror Images)',
          weightagePercentage: 6.0,
          isCompleted: false,
          officialProvenance: sscProvenanceOverview,
          weightageProvenance: sscProvenanceGovOSAnalysis
        }
      ]
    },
    {
      id: 'syl-english',
      subject: 'English Comprehension',
      topicName: 'English Language & Comprehension',
      weightagePercentage: 25.0,
      officialProvenance: sscProvenanceOverview,
      weightageProvenance: sscProvenanceGovOSAnalysis,
      subtopics: [
        {
          id: 'syl-eng-1',
          subject: 'English Comprehension',
          topicName: 'Reading Comprehension & Cloze Test',
          weightagePercentage: 8.0,
          isCompleted: true,
          officialProvenance: sscProvenanceOverview,
          weightageProvenance: sscProvenanceGovOSAnalysis
        },
        {
          id: 'syl-eng-2',
          subject: 'English Comprehension',
          topicName: 'Error Spotting & Sentence Improvement',
          weightagePercentage: 6.0,
          isCompleted: false,
          officialProvenance: sscProvenanceOverview,
          weightageProvenance: sscProvenanceGovOSAnalysis
        },
        {
          id: 'syl-eng-3',
          subject: 'English Comprehension',
          topicName: 'Idioms, Phrases & One Word Substitutions',
          weightagePercentage: 6.0,
          isCompleted: false,
          officialProvenance: sscProvenanceOverview,
          weightageProvenance: sscProvenanceGovOSAnalysis
        },
        {
          id: 'syl-eng-4',
          subject: 'English Comprehension',
          topicName: 'Synonyms & Antonyms',
          weightagePercentage: 5.0,
          isCompleted: false,
          officialProvenance: sscProvenanceOverview,
          weightageProvenance: sscProvenanceGovOSAnalysis
        }
      ]
    },
    {
      id: 'syl-ga',
      subject: 'General Awareness',
      topicName: 'General Awareness & Current Affairs',
      weightagePercentage: 25.0,
      officialProvenance: sscProvenanceOverview,
      weightageProvenance: sscProvenanceGovOSAnalysis,
      subtopics: [
        {
          id: 'syl-ga-1',
          subject: 'General Awareness',
          topicName: 'Indian Polity & Constitution',
          weightagePercentage: 6.0,
          isCompleted: false,
          officialProvenance: sscProvenanceOverview,
          weightageProvenance: sscProvenanceGovOSAnalysis
        },
        {
          id: 'syl-ga-2',
          subject: 'General Awareness',
          topicName: 'Indian History & Culture',
          weightagePercentage: 5.0,
          isCompleted: false,
          officialProvenance: sscProvenanceOverview,
          weightageProvenance: sscProvenanceGovOSAnalysis
        },
        {
          id: 'syl-ga-3',
          subject: 'General Awareness',
          topicName: 'Geography & Economy',
          weightagePercentage: 5.0,
          isCompleted: false,
          officialProvenance: sscProvenanceOverview,
          weightageProvenance: sscProvenanceGovOSAnalysis
        },
        {
          id: 'syl-ga-4',
          subject: 'General Awareness',
          topicName: 'General Science (Physics, Chemistry, Biology)',
          weightagePercentage: 4.0,
          isCompleted: false,
          officialProvenance: sscProvenanceOverview,
          weightageProvenance: sscProvenanceGovOSAnalysis
        },
        {
          id: 'syl-ga-5',
          subject: 'General Awareness',
          topicName: 'National & International Current Affairs (Last 6 Months)',
          weightagePercentage: 5.0,
          isCompleted: false,
          officialProvenance: sscProvenanceOverview,
          weightageProvenance: sscProvenanceGovOSAnalysis
        }
      ]
    }
  ],

  practiceQuestions: [
    {
      id: 'q-quant-01',
      topicId: 'syl-quant-2',
      subject: 'Quantitative Aptitude',
      topicName: 'Percentage & Ratio',
      questionType: 'OFFICIAL_PYQ',
      questionText: 'If 20% of A = 50% of B, then what percentage of A is B?',
      options: [
        { id: 1, text: '20%' },
        { id: 2, text: '40%' },
        { id: 3, text: '50%' },
        { id: 4, text: '60%' }
      ],
      correctOptionIndex: 1,
      explanation: '20% of A = 50% of B ⇒ 0.20 A = 0.50 B ⇒ B/A = 0.20/0.50 = 2/5 = 40%. Thus B is 40% of A.',
      year: 2024,
      provenance: sscProvenanceOverview
    },
    {
      id: 'q-quant-02',
      topicId: 'syl-quant-4',
      subject: 'Quantitative Aptitude',
      topicName: 'Time & Work',
      questionType: 'OFFICIAL_PYQ',
      questionText: 'A can complete a piece of work in 12 days and B can do it in 18 days. Working together, in how many days can they complete the work?',
      options: [
        { id: 1, text: '6.5 days' },
        { id: 2, text: '7.2 days' },
        { id: 3, text: '8.0 days' },
        { id: 4, text: '9.0 days' }
      ],
      correctOptionIndex: 1,
      explanation: 'Combined 1 day work = 1/12 + 1/18 = (3 + 2)/36 = 5/36. Total days = 36/5 = 7.2 days.',
      year: 2024,
      provenance: sscProvenanceOverview
    },
    {
      id: 'q-reas-01',
      topicId: 'syl-reas-2',
      subject: 'Reasoning & General Intelligence',
      topicName: 'Coding-Decoding',
      questionType: 'OFFICIAL_PYQ',
      questionText: 'In a certain code language, "SYSTEM" is written as "SYSMET". How is "FRACTION" written in that code?',
      options: [
        { id: 1, text: 'CARFNOIT' },
        { id: 2, text: 'NOITCARF' },
        { id: 3, text: 'ARFCNOIT' },
        { id: 4, text: 'CARFTION' }
      ],
      correctOptionIndex: 0,
      explanation: 'The word is divided into two halves of 4 letters: FRAC → CARF and TION → NOIT. Combining yields CARFNOIT.',
      year: 2023,
      provenance: sscProvenanceOverview
    },
    {
      id: 'q-eng-01',
      topicId: 'syl-eng-3',
      subject: 'English Comprehension',
      topicName: 'Idioms & Phrases',
      questionType: 'OFFICIAL_PYQ',
      questionText: 'Select the most appropriate meaning of the idiom: "To burn the midnight oil".',
      options: [
        { id: 1, text: 'To work or study late into the night' },
        { id: 2, text: 'To waste fuel recklessly' },
        { id: 3, text: 'To start a fire in the dark' },
        { id: 4, text: 'To perform an unnecessary action' }
      ],
      correctOptionIndex: 0,
      explanation: '"To burn the midnight oil" means to read or work late into the night.',
      year: 2024,
      provenance: sscProvenanceOverview
    },
    {
      id: 'q-ga-01',
      topicId: 'syl-ga-1',
      subject: 'General Awareness',
      topicName: 'Polity & Constitution',
      questionType: 'OFFICIAL_PYQ',
      questionText: 'Which Article of the Constitution of India provides for the Fundamental Right to Freedom of Speech and Expression?',
      options: [
        { id: 1, text: 'Article 14' },
        { id: 2, text: 'Article 19(1)(a)' },
        { id: 3, text: 'Article 21' },
        { id: 4, text: 'Article 32' }
      ],
      correctOptionIndex: 1,
      explanation: 'Article 19(1)(a) guarantees to all citizens the right to freedom of speech and expression.',
      year: 2024,
      provenance: sscProvenanceOverview
    }
  ],

  corrigendums: [
    {
      id: 'corr-cgl-02',
      title: 'Corrigendum #02: Extension of Online Application Deadline',
      noticeNumber: 'F.No. 3/1/2026-P&P-I (Vol.II)',
      publishedDate: '2026-08-22',
      effectiveDate: '2026-08-22',
      summary: 'The Staff Selection Commission has extended the closing date for submission of online applications for SSC CGL 2026 from 20 September 2026 (23:59 Hrs) to 27 September 2026 (23:59 Hrs).',
      pdfUrl: 'https://ssc.gov.in/api/attachment/notice/cgl_2026_corrigendum_02.pdf',
      status: 'ACTIVE',
      diffSummary: 'Application deadline extended from 20 Sep 2026 → 27 Sep 2026 (23:59 IST)'
    }
  ],

  cutoffsHistory: [
    { year: 2024, category: 'UR (General)', tier1Cutoff: 150.04, tier2Cutoff: 308.5, provenance: sscProvenanceOverview },
    { year: 2024, category: 'OBC', tier1Cutoff: 145.80, tier2Cutoff: 302.0, provenance: sscProvenanceOverview },
    { year: 2024, category: 'EWS', tier1Cutoff: 143.20, tier2Cutoff: 298.5, provenance: sscProvenanceOverview },
    { year: 2024, category: 'SC', tier1Cutoff: 126.50, tier2Cutoff: 275.0, provenance: sscProvenanceOverview },
    { year: 2024, category: 'ST', tier1Cutoff: 118.20, tier2Cutoff: 261.0, provenance: sscProvenanceOverview }
  ],

  resources: [
    {
      id: 'res-pdf-01',
      title: 'SSC CGL 2026 Official Gazette Notification (PDF)',
      type: 'OFFICIAL_PDF',
      url: 'https://ssc.gov.in/api/attachment/notice/ssc_cgl_2026_notification.pdf',
      description: 'Authoritative official notification issued by Staff Selection Commission detailing eligibility, posts, pay scales, and exam schemes.'
    },
    {
      id: 'res-guide-01',
      title: 'GovOS Simplified SSC CGL Application & Document Checklist',
      type: 'SIMPLIFIED_GUIDE',
      url: 'https://ssc.gov.in',
      description: 'Step-by-step guidance on photograph specifications, live webcam photo upload rules, signature dimension requirements, and fee payment modes.'
    },
    {
      id: 'res-book-01',
      title: 'Recommended Reference: NCERT Mathematics (Class 9-10) & RS Aggarwal Quant',
      type: 'RECOMMENDED_BOOK',
      url: 'https://ssc.gov.in',
      description: 'Foundational mathematics textbooks covering arithmetic, algebra, geometry, and trigonometry.'
    }
  ],

  faqs: [
    {
      id: 'faq-01',
      question: 'Are final year degree students eligible to apply for SSC CGL 2026?',
      answer: 'Yes, candidates appearing in their final year of graduation can apply, provided they acquire the essential educational qualification degree on or before the cutoff date specified in the notification (01-08-2026).',
      officialClause: 'Section 3.1, Clause (b)',
      provenance: sscProvenanceEligibility
    },
    {
      id: 'faq-02',
      question: 'Is there any negative marking in SSC CGL Tier 1?',
      answer: 'Yes. There is a negative marking of 0.50 marks for each wrong answer in Tier 1 CBR examination across all 4 sections.',
      officialClause: 'Section 4.2, Sub-clause (a)',
      provenance: sscProvenanceOverview
    },
    {
      id: 'faq-03',
      question: 'What is the application fee for female and reserved category candidates?',
      answer: 'Women candidates and candidates belonging to Scheduled Castes (SC), Scheduled Tribes (ST), Persons with Benchmark Disabilities (PwBD), and Ex-Servicemen (ESM) eligible for reservation are exempted from payment of fee.',
      officialClause: 'Section 5.1, Clause (c)',
      provenance: sscProvenanceOverview
    }
  ],

  applicationSteps: [
    {
      stepNumber: 1,
      title: 'One-Time Registration (OTR) on ssc.gov.in',
      description: 'Visit the official portal https://ssc.gov.in, click "Login or Register", and complete OTR with Aadhaar number, Mobile OTP, and Email OTP.',
      documentRequired: 'Aadhaar Card / ID Proof, Active Mobile & Email'
    },
    {
      stepNumber: 2,
      title: 'Live Photo Capture & Signature Upload',
      description: 'Capture live photograph using webcam/mobile camera in clear lighting with plain background. Upload signature image (10 KB to 20 KB in JPEG format).',
      documentRequired: 'Live Webcam Photo, Signature JPEG (10-20 KB)'
    },
    {
      stepNumber: 3,
      title: 'Select Exam Center Preferences & Post Preferences',
      description: 'Choose 3 preferred examination cities within your SSC regional zone and select post cadres.',
      documentRequired: 'Educational Marksheet Details'
    },
    {
      stepNumber: 4,
      title: 'Fee Payment & Final Submission',
      description: 'Pay ₹100 fee via BHIM UPI, Net Banking, or Credit/Debit Card (Exempt for SC/ST/Women/PwBD). Download final application PDF.',
      documentRequired: 'UPI / NetBanking / Debit Card'
    }
  ]
};

export const PROTOTYPE_COMPANION_EXAMS: Exam[] = [
  {
    id: 'exam-upsc-cse-2026',
    code: 'UPSC_CSE_2026',
    title: 'UPSC Civil Services Examination (CSE) 2026',
    authorityName: 'Union Public Service Commission (UPSC)',
    officialDomain: 'https://upsc.gov.in',
    isGoldenJourney: false,
    isDemoData: true,
    overviewDescription: 'India\'s premier examination for recruitment to IAS, IPS, IFS, IRS, and Central Group A Civil Services.',
    posts: [
      { id: 'p-ias', postName: 'Indian Administrative Service (IAS)', department: 'Cabinet Secretariat', payLevel: 'Pay Level 10', classification: 'Group A', provenance: sscProvenanceOverview },
      { id: 'p-ips', postName: 'Indian Police Service (IPS)', department: 'Ministry of Home Affairs', payLevel: 'Pay Level 10', classification: 'Group A', provenance: sscProvenanceOverview }
    ],
    dates: [
      { id: 'ud-01', type: 'NOTIFICATION', label: 'Official Notification', dateTimeStr: '2026-02-14 10:00:00', timezone: 'Asia/Kolkata (IST)', isTentative: false, status: 'AVAILABLE', provenance: sscProvenanceOverview },
      { id: 'ud-02', type: 'EXAM_TIER1', label: 'Prelims Examination', dateTimeStr: '2026-05-24 09:30:00', timezone: 'Asia/Kolkata (IST)', isTentative: false, status: 'AVAILABLE', provenance: sscProvenanceOverview }
    ],
    globalRuleGroup: {
      id: 'rg-upsc-global',
      operator: 'AND',
      rules: [
        { id: 'ur-min', ruleType: 'AGE_MIN', operator: '>=', ruleValue: 21, category: 'GENERAL', provenance: sscProvenanceOverview },
        { id: 'ur-max', ruleType: 'AGE_MAX', operator: '<=', ruleValue: 32, category: 'GENERAL', provenance: sscProvenanceOverview },
        { id: 'ur-deg', ruleType: 'DEGREE_REQUIRED', operator: '=', ruleValue: ['Bachelor Degree'], category: 'GENERAL', provenance: sscProvenanceOverview }
      ]
    },
    stages: [],
    syllabus: [],
    practiceQuestions: [],
    corrigendums: [],
    cutoffsHistory: [],
    resources: [],
    faqs: [],
    applicationSteps: []
  },
  {
    id: 'exam-ibps-po-2026',
    code: 'IBPS_PO_2026',
    title: 'IBPS Probationary Officer (PO / MT) 2026',
    authorityName: 'Institute of Banking Personnel Selection (IBPS)',
    officialDomain: 'https://ibps.in',
    isGoldenJourney: false,
    isDemoData: true,
    overviewDescription: 'Recruitment of Probationary Officers / Management Trainees in 11 Participating Public Sector Banks across India.',
    posts: [
      { id: 'p-ibps-po', postName: 'Probationary Officer / Management Trainee', department: 'Public Sector Banks (Bank of Baroda, PNB, Canara, etc.)', payLevel: '₹36,000 Basic Pay', classification: 'Officer Scale I', provenance: sscProvenanceOverview }
    ],
    dates: [
      { id: 'ib-01', type: 'NOTIFICATION', label: 'Official Notification', dateTimeStr: '2026-08-01 10:00:00', timezone: 'Asia/Kolkata (IST)', isTentative: false, status: 'AVAILABLE', provenance: sscProvenanceOverview }
    ],
    globalRuleGroup: {
      id: 'rg-ibps-global',
      operator: 'AND',
      rules: [
        { id: 'ir-min', ruleType: 'AGE_MIN', operator: '>=', ruleValue: 20, category: 'GENERAL', provenance: sscProvenanceOverview },
        { id: 'ir-max', ruleType: 'AGE_MAX', operator: '<=', ruleValue: 30, category: 'GENERAL', provenance: sscProvenanceOverview },
        { id: 'ir-deg', ruleType: 'DEGREE_REQUIRED', operator: '=', ruleValue: ['Bachelor Degree'], category: 'GENERAL', provenance: sscProvenanceOverview }
      ]
    },
    stages: [],
    syllabus: [],
    practiceQuestions: [],
    corrigendums: [],
    cutoffsHistory: [],
    resources: [],
    faqs: [],
    applicationSteps: []
  }
];

export const ALL_EXAMS: Exam[] = [SSC_CGL_EXAM, ...PROTOTYPE_COMPANION_EXAMS];
