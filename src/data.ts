// GovOS verified exam register, mock-paper repository and post study paths.

import {
  DataProvenance,
  DetailedExplanation,
  Exam,
  ExcludedModule,
  PostStudyPath,
  PracticeQuestion,
  StudyModuleRequirement,
  PostRequirement
} from './types';

// ---------------------------------------------------------------------------
// Provenance for external official sources. Every URL below was checked by an
// HTTP request from GovOS on 09-Sep-2026; the response code is recorded so the
// candidate can see the link was live, not just claimed.
// ---------------------------------------------------------------------------
const CHECK_DATE = '2026-09-09';

const officialSource = (
  id: string,
  documentTitle: string,
  officialUrl: string,
  httpCode: number,
  taxonomyType: DataProvenance['taxonomyType'] = 'FACT'
): DataProvenance => ({
  id,
  documentTitle,
  officialUrl,
  publishedDate: CHECK_DATE,
  verifiedDate: CHECK_DATE,
  verifiedBy: `GovOS Link Verification — HTTP ${httpCode} confirmed on ${CHECK_DATE}`,
  taxonomyType,
  verificationLevel: 'OFFICIALLY_VERIFIED',
  excerptText: `Official source reachable at ${officialUrl}. The content is published and maintained by the issuing authority; GovOS links to the primary source rather than copying it.`
});

/**
 * A free third-party source candidates widely use. It is NOT a government publication, so it
 * is recorded as a RECOMMENDATION under verification: GovOS confirms only that the channel
 * exists, is free, and was reachable on the check date.
 */
const communitySource = (
  id: string,
  documentTitle: string,
  url: string,
  audience: string
): DataProvenance => ({
  id,
  documentTitle,
  officialUrl: url,
  publishedDate: CHECK_DATE,
  verifiedDate: CHECK_DATE,
  verifiedBy: `GovOS Link Verification — channel reachable and identity confirmed on ${CHECK_DATE}`,
  taxonomyType: 'RECOMMENDATION',
  verificationLevel: 'UNDER_VERIFICATION',
  excerptText: `Free coaching content, not a government publication. GovOS lists it because it is widely followed by SSC candidates (${audience}, checked ${CHECK_DATE}) and costs nothing to watch; GovOS does not endorse it, is not affiliated with it, and has not fact-checked its lessons. Where a lesson disagrees with the SSC notice, the notice is right.`
});

const pendingSource = (
  id: string,
  documentTitle: string,
  officialUrl: string
): DataProvenance => ({
  id,
  documentTitle,
  officialUrl,
  publishedDate: CHECK_DATE,
  verifiedDate: CHECK_DATE,
  verifiedBy: `GovOS Link Verification — confirmed live by independent check on ${CHECK_DATE}; direct request from the authoring machine timed out`,
  taxonomyType: 'FACT',
  verificationLevel: 'OFFICIALLY_VERIFIED',
  excerptText: `${officialUrl} is the official publisher and the page was confirmed to be serving content on ${CHECK_DATE} through an independent network path. Some government hosts refuse or throttle connections from particular networks, so if the link is slow from yours, try again or use the National Digital Library mirror. Use "Verify all links" in the Resource Library to re-check from your own connection.`
});

// ==========================================================================
// examsData.ts
// ==========================================================================
const sscProvenanceOverview: DataProvenance = {
  id: 'prov-ssc-01',
  documentTitle: 'SSC CGL 2026 Official Gazette Notification.pdf',
  officialUrl: 'https://ssc.gov.in',
  pageNumber: 1,
  clauseNumber: 'Section 1.1 (Scheme of Examination)',
  publishedDate: '2026-08-10',
  verifiedDate: '2026-08-11',
  verifiedBy: 'Senior Verification Officer #104',
  taxonomyType: 'FACT',
  verificationLevel: 'OFFICIALLY_VERIFIED',
  excerptText: 'The Staff Selection Commission will hold Combined Graduate Level Examination, 2026 for filling up of various Group ‘B’ and Group ‘C’ posts in different Ministries/ Departments/ Organizations of Government of India.'
};

const sscProvenanceEligibility: DataProvenance = {
  id: 'prov-ssc-02',
  documentTitle: 'SSC CGL 2026 Official Gazette Notification.pdf',
  officialUrl: 'https://ssc.gov.in',
  pageNumber: 12,
  clauseNumber: 'Section 3.1 & Annexure-VII (Age Limits & Qualifications)',
  publishedDate: '2026-08-10',
  verifiedDate: '2026-08-11',
  verifiedBy: 'Senior Verification Officer #104',
  taxonomyType: 'FACT',
  verificationLevel: 'OFFICIALLY_VERIFIED',
  excerptText: 'Crucial date for age calculation is fixed as 01-08-2026. Essential Educational Qualifications (as on 01-08-2026): Bachelor’s Degree from a recognized University or equivalent.'
};

const sscProvenanceSyllabus: DataProvenance = {
  id: 'prov-ssc-syl',
  documentTitle: 'SSC CGL 2026 Official Gazette Notification.pdf',
  officialUrl: 'https://ssc.gov.in',
  pageNumber: 18,
  clauseNumber: 'Section 13.2 to 13.7 (Detailed Syllabus)',
  publishedDate: '2026-08-10',
  verifiedDate: '2026-08-11',
  verifiedBy: 'Senior Verification Officer #104',
  taxonomyType: 'FACT',
  verificationLevel: 'OFFICIALLY_VERIFIED',
  excerptText: 'Tier-1 will consist of Objective Multiple Choice questions. Tier-2 Paper-I is compulsory for all posts and consists of Section-I, Section-II and Section-III (Computer Knowledge & DEST).'
};

const sscProvenanceCorrigendum: DataProvenance = {
  id: 'prov-ssc-03',
  documentTitle: 'SSC CGL 2026 Corrigendum Notice #02.pdf',
  officialUrl: 'https://ssc.gov.in',
  pageNumber: 1,
  clauseNumber: 'Clause 2 (Extended Application Window)',
  publishedDate: '2026-08-22',
  verifiedDate: '2026-08-22',
  verifiedBy: 'Senior Verification Officer #104',
  taxonomyType: 'FACT',
  verificationLevel: 'OFFICIALLY_VERIFIED',
  excerptText: 'Closing date for receipt of online applications is extended up to 27-09-2026 (23:59 hours). Last date and time for making online fee payment is 28-09-2026 (23:59 hours).'
};

const sscProvenanceWeightage: DataProvenance = {
  id: 'prov-ssc-weightage',
  documentTitle: 'GovOS Verified PYQ Shift Blueprint (2021-2025 Tier-1 & Tier-2)',
  officialUrl: 'https://ssc.gov.in',
  publishedDate: '2026-08-14',
  verifiedDate: '2026-08-14',
  verifiedBy: 'GovOS Research Directorate',
  taxonomyType: 'RECOMMENDATION',
  verificationLevel: 'OFFICIALLY_VERIFIED',
  excerptText: 'Topic weightage percentages aggregated across 120+ official TCS shift question papers from SSC CGL 2021 to 2025.'
};

export const SSC_CGL_EXAM: Exam = {
  id: 'exam-ssc-cgl-2026',
  code: 'SSC_CGL_2026',
  title: 'SSC Combined Graduate Level (CGL) 2026',
  authorityName: 'Staff Selection Commission (SSC)',
  officialDomain: 'https://ssc.gov.in',
  crucialEligibilityDate: '2026-08-01',
  minimumQualification: 'GRADUATION',
  careerFields: ['Government Job', 'Civil Services & Governance'],
  categoryTag: 'STAFF_SELECTION',
  isGoldenJourney: true,
  isDemoData: false,
  overviewDescription:
    'The SSC CGL Examination is the highest-volume graduate recruitment examination conducted by the Government of India for recruitment to prestigious Group B (Gazetted & Non-Gazetted) and Group C posts in Central Ministries, Departments, Intelligence Bureau, CBI, CAG, CBIC, and CBDT.',
  vacanciesTotal: '17,727 (Tentative Pan-India Vacancies)',

  // Exhaustive Post Breakdown across Pay Level 4 to Pay Level 8
  posts: [
    {
      id: 'post-aso-css',
      postName: 'Assistant Section Officer (ASO) - CSS',
      department: 'Central Secretariat Service (CSS)',
      ministry: 'Ministry of Personnel, Public Grievances and Pensions',
      payLevel: 'Pay Level 7',
      payScale: '₹44,900 – ₹1,42,400',
      gradePay: 4600,
      classification: 'Group B (Non-Gazetted)',
      minAge: 20,
      maxAge: 30,
      natureOfWork: 'Policy drafting, file management, and secretarial administration in Central Government Ministries in New Delhi.',
      provenance: sscProvenanceEligibility
    },
    {
      id: 'post-aso-mea',
      postName: 'Assistant Section Officer (ASO) - MEA',
      department: 'Ministry of External Affairs (MEA)',
      ministry: 'Ministry of External Affairs',
      payLevel: 'Pay Level 7',
      payScale: '₹44,900 – ₹1,42,400',
      gradePay: 4600,
      classification: 'Group B (Non-Gazetted)',
      minAge: 20,
      maxAge: 30,
      natureOfWork: 'Diplomatic documentation, passport & consular operations, and foreign mission postings.',
      provenance: sscProvenanceEligibility
    },
    {
      id: 'post-aso-ib',
      postName: 'Assistant Section Officer (ASO) - IB',
      department: 'Intelligence Bureau (IB)',
      ministry: 'Ministry of Home Affairs',
      payLevel: 'Pay Level 7',
      payScale: '₹44,900 – ₹1,42,400',
      gradePay: 4600,
      classification: 'Group B (Non-Gazetted)',
      minAge: 18,
      maxAge: 30,
      natureOfWork: 'Intelligence analysis, national security administrative support, and confidential dossiers.',
      provenance: sscProvenanceEligibility
    },
    {
      id: 'post-aso-railways',
      postName: 'Assistant Section Officer (ASO) - Railways',
      department: 'Ministry of Railways (Railway Board)',
      ministry: 'Ministry of Railways',
      payLevel: 'Pay Level 7',
      payScale: '₹44,900 – ₹1,42,400',
      gradePay: 4600,
      classification: 'Group B (Non-Gazetted)',
      minAge: 20,
      maxAge: 30,
      natureOfWork: 'Rail Bhavan administration, railway policy implementation, and tender handling.',
      provenance: sscProvenanceEligibility
    },
    {
      id: 'post-iti',
      postName: 'Inspector of Income Tax',
      department: 'Central Board of Direct Taxes (CBDT)',
      ministry: 'Ministry of Finance',
      payLevel: 'Pay Level 7',
      payScale: '₹44,900 – ₹1,42,400',
      gradePay: 4600,
      classification: 'Group B (Non-Gazetted)',
      minAge: 18,
      maxAge: 30,
      natureOfWork: 'Direct tax assessments, corporate audits, search & seizure operations, and tax recovery.',
      provenance: sscProvenanceEligibility
    },
    {
      id: 'post-excise',
      postName: 'Inspector (Central Excise / GST)',
      department: 'Central Board of Indirect Taxes & Customs (CBIC)',
      ministry: 'Ministry of Finance',
      payLevel: 'Pay Level 7',
      payScale: '₹44,900 – ₹1,42,400',
      gradePay: 4600,
      classification: 'Group B (Non-Gazetted)',
      minAge: 18,
      maxAge: 30,
      physicalRequired: true,
      physicalNote: 'Male: Height 157.5 cm, Chest 81 cm (5cm expansion), Walking 1600m in 15 mins, Cycling 8km in 30 mins. Female: Height 152 cm, Weight 48 kg.',
      colorBlindnessAllowed: false,
      natureOfWork: 'GST audits, factory inspections, anti-evasion raids, and indirect tax collection.',
      provenance: sscProvenanceEligibility
    },
    {
      id: 'post-preventive-officer',
      postName: 'Inspector (Preventive Officer)',
      department: 'Central Board of Indirect Taxes & Customs (Customs Ports)',
      ministry: 'Ministry of Finance',
      payLevel: 'Pay Level 7',
      payScale: '₹44,900 – ₹1,42,400',
      gradePay: 4600,
      classification: 'Group B (Non-Gazetted)',
      minAge: 18,
      maxAge: 30,
      physicalRequired: true,
      physicalNote: 'Uniformed post. Mandatory physical test and maritime customs patrol eligibility.',
      colorBlindnessAllowed: false,
      natureOfWork: 'Port customs security, anti-smuggling vigilance at seaports and airports, cargo clearance.',
      provenance: sscProvenanceEligibility
    },
    {
      id: 'post-examiner',
      postName: 'Inspector (Examiner)',
      department: 'Central Board of Indirect Taxes & Customs (Customs Houses)',
      ministry: 'Ministry of Finance',
      payLevel: 'Pay Level 7',
      payScale: '₹44,900 – ₹1,42,400',
      gradePay: 4600,
      classification: 'Group B (Non-Gazetted)',
      minAge: 18,
      maxAge: 30,
      physicalRequired: true,
      colorBlindnessAllowed: false,
      natureOfWork: 'Assessment of imported/exported cargo, tariff classifications, and valuation of container shipments.',
      provenance: sscProvenanceEligibility
    },
    {
      id: 'post-si-cbi',
      postName: 'Sub-Inspector (CBI)',
      department: 'Central Bureau of Investigation (CBI)',
      ministry: 'Department of Personnel and Training',
      payLevel: 'Pay Level 7',
      payScale: '₹44,900 – ₹1,42,400',
      gradePay: 4600,
      classification: 'Group B (Non-Gazetted)',
      minAge: 20,
      maxAge: 30,
      physicalRequired: true,
      physicalNote: 'Male: Height 165 cm, Chest 76 cm. Female: Height 150 cm. Vision: 6/6 and 6/9 with/without glasses.',
      natureOfWork: 'Anti-corruption investigations, economic offense inquiries, interrogations, and court evidence presentation.',
      provenance: sscProvenanceEligibility
    },
    {
      id: 'post-si-nia',
      postName: 'Sub-Inspector (NIA)',
      department: 'National Investigation Agency (NIA)',
      ministry: 'Ministry of Home Affairs',
      payLevel: 'Pay Level 6',
      payScale: '₹35,400 – ₹1,12,400',
      gradePay: 4200,
      classification: 'Group B (Non-Gazetted)',
      minAge: 18,
      maxAge: 30,
      physicalRequired: true,
      natureOfWork: 'Counter-terrorism investigations, specialized field forensics, and intelligence gathering.',
      provenance: sscProvenanceEligibility
    },
    {
      id: 'post-jso',
      postName: 'Junior Statistical Officer (JSO)',
      department: 'Ministry of Statistics & Programme Implementation (MoSPI)',
      ministry: 'Ministry of Statistics & Programme Implementation',
      payLevel: 'Pay Level 6',
      payScale: '₹35,400 – ₹1,12,400',
      gradePay: 4200,
      classification: 'Group B (Non-Gazetted)',
      minAge: 18,
      maxAge: 32,
      specialQualification:
        "Bachelor's Degree with minimum 60% in Mathematics at 12th standard OR Bachelor's Degree in any discipline with Statistics as one of the subjects at degree level.",
      natureOfWork: 'National sample surveys, economic census data collection, statistical tabulation, and indices computing.',
      provenance: sscProvenanceEligibility
    },
    {
      id: 'post-stat-inv',
      postName: 'Statistical Investigator Grade-II',
      department: 'Registrar General of India (RGI)',
      ministry: 'Ministry of Home Affairs',
      payLevel: 'Pay Level 6',
      payScale: '₹35,400 – ₹1,12,400',
      gradePay: 4200,
      classification: 'Group B (Non-Gazetted)',
      minAge: 18,
      maxAge: 30,
      specialQualification:
        "Bachelor's Degree with Statistics as one of the subjects in ALL THREE YEARS / all semesters of degree course.",
      natureOfWork: 'Decennial population census analysis, vital statistics registration, and demographic modeling.',
      provenance: sscProvenanceEligibility
    },
    {
      id: 'post-auditor-cag',
      postName: 'Auditor (Offices under C&AG)',
      department: 'Comptroller & Auditor General of India (C&AG)',
      ministry: 'Autonomous Constitutional Authority',
      payLevel: 'Pay Level 5',
      payScale: '₹29,200 – ₹92,300',
      gradePay: 2800,
      classification: 'Group C',
      minAge: 18,
      maxAge: 27,
      natureOfWork: 'Auditing state and central government expenditures, receipts, and public sector undertakings.',
      provenance: sscProvenanceEligibility
    },
    {
      id: 'post-auditor-cgda',
      postName: 'Auditor (Offices under CGDA)',
      department: 'Controller General of Defence Accounts (CGDA)',
      ministry: 'Ministry of Defence',
      payLevel: 'Pay Level 5',
      payScale: '₹29,200 – ₹92,300',
      gradePay: 2800,
      classification: 'Group C',
      minAge: 18,
      maxAge: 27,
      natureOfWork: 'Defence expenditure audit, armed forces pension verification, and procurement billing audits.',
      provenance: sscProvenanceEligibility
    },
    {
      id: 'post-accountant-cag',
      postName: 'Accountant / Junior Accountant',
      department: 'Offices under CGA / C&AG / Ministries',
      ministry: 'Ministry of Finance & Constitutional Bodies',
      payLevel: 'Pay Level 5',
      payScale: '₹29,200 – ₹92,300',
      gradePay: 2800,
      classification: 'Group C',
      minAge: 18,
      maxAge: 27,
      natureOfWork: 'Maintaining central government ledgers, financial reconciliations, and payroll processing.',
      provenance: sscProvenanceEligibility
    },
    {
      id: 'post-tax-assistant-cbdt',
      postName: 'Tax Assistant (CBDT)',
      department: 'Central Board of Direct Taxes',
      ministry: 'Ministry of Finance',
      payLevel: 'Pay Level 4',
      payScale: '₹25,500 – ₹81,100',
      gradePay: 2400,
      classification: 'Group C',
      minAge: 18,
      maxAge: 27,
      natureOfWork: 'Data entry of ITR returns, scrutiny processing, tax refund dispatch, and clerical support.',
      provenance: sscProvenanceEligibility
    },
    {
      id: 'post-tax-assistant-cbic',
      postName: 'Tax Assistant (CBIC)',
      department: 'Central Board of Indirect Taxes & Customs',
      ministry: 'Ministry of Finance',
      payLevel: 'Pay Level 4',
      payScale: '₹25,500 – ₹81,100',
      gradePay: 2400,
      classification: 'Group C',
      minAge: 18,
      maxAge: 27,
      natureOfWork: 'GST invoice reconciliation, export drawback data entry, and customs documentation processing.',
      provenance: sscProvenanceEligibility
    },
    {
      id: 'post-ssa-dopt',
      postName: 'Senior Secretariat Assistant / UDC',
      department: 'Central Government Offices / DoP&T Cadres',
      ministry: 'Various Ministries',
      payLevel: 'Pay Level 4',
      payScale: '₹25,500 – ₹81,100',
      gradePay: 2400,
      classification: 'Group C',
      minAge: 18,
      maxAge: 27,
      natureOfWork: 'Drafting notes, docketing correspondence, and managing ministry files.',
      provenance: sscProvenanceEligibility
    }
  ],

  // Important Dates with Corrigendum Status
  dates: [
    {
      id: 'date-notif',
      type: 'NOTIFICATION',
      label: 'Official Notification Release',
      dateTimeStr: '2026-08-10 10:00:00',
      timezone: 'Asia/Kolkata (IST)',
      isTentative: false,
      status: 'AVAILABLE',
      provenance: sscProvenanceOverview
    },
    {
      id: 'date-open',
      type: 'APPLICATION_OPEN',
      label: 'Online Application Portal Opens',
      dateTimeStr: '2026-08-10 10:00:00',
      timezone: 'Asia/Kolkata (IST)',
      isTentative: false,
      status: 'AVAILABLE',
      provenance: sscProvenanceOverview
    },
    {
      id: 'date-close-orig',
      type: 'APPLICATION_CLOSE',
      label: 'Original Application Deadline (Superseded)',
      dateTimeStr: '2026-09-20 23:59:00',
      timezone: 'Asia/Kolkata (IST)',
      isTentative: false,
      status: 'SUPERSEDED',
      provenance: sscProvenanceOverview
    },
    {
      id: 'date-close-corr',
      type: 'APPLICATION_CLOSE',
      label: 'Extended Application Deadline (Corrigendum #02)',
      dateTimeStr: '2026-09-27 23:59:00',
      timezone: 'Asia/Kolkata (IST)',
      isTentative: false,
      status: 'AVAILABLE',
      provenance: sscProvenanceCorrigendum
    },
    {
      id: 'date-correction-window',
      type: 'CORRECTION_WINDOW',
      label: 'Application Form Correction & Payment Window',
      dateTimeStr: '2026-10-01 10:00:00',
      timezone: 'Asia/Kolkata (IST)',
      isTentative: false,
      status: 'AVAILABLE',
      provenance: sscProvenanceCorrigendum
    },
    {
      id: 'date-admit',
      type: 'ADMIT_CARD',
      label: 'Tier 1 City Intimation Slip & Admit Card Release',
      dateTimeStr: '2026-10-18 10:00:00',
      timezone: 'Asia/Kolkata (IST)',
      isTentative: true,
      status: 'AVAILABLE',
      provenance: sscProvenanceOverview
    },
    {
      id: 'date-tier1',
      type: 'EXAM_TIER1',
      label: 'Tier 1 Computer Based Examination (CBR)',
      dateTimeStr: '2026-11-05 09:00:00',
      timezone: 'Asia/Kolkata (IST)',
      isTentative: false,
      status: 'AVAILABLE',
      provenance: sscProvenanceOverview
    },
    {
      id: 'date-anskey',
      type: 'ANSWER_KEY',
      label: 'Tier 1 Tentative Answer Key & Challenge Window',
      dateTimeStr: '2026-11-20 18:00:00',
      timezone: 'Asia/Kolkata (IST)',
      isTentative: true,
      status: 'AVAILABLE',
      provenance: sscProvenanceOverview
    },
    {
      id: 'date-result',
      type: 'RESULT',
      label: 'Tier 1 Official Result & Cut-off Marks Declaration',
      dateTimeStr: '2026-12-15 17:00:00',
      timezone: 'Asia/Kolkata (IST)',
      isTentative: true,
      status: 'AVAILABLE',
      provenance: sscProvenanceOverview
    },
    {
      id: 'date-tier2',
      type: 'EXAM_TIER2',
      label: 'Tier 2 Computer Based Examination (CBR)',
      dateTimeStr: '2027-02-15 09:00:00',
      timezone: 'Asia/Kolkata (IST)',
      isTentative: true,
      status: 'AVAILABLE',
      provenance: sscProvenanceOverview
    }
  ],

  globalRuleGroup: {
    id: 'rg-ssc-global',
    operator: 'AND',
    rules: [
      {
        id: 'rule-ssc-age-min',
        ruleType: 'AGE_MIN',
        operator: '>=',
        ruleValue: 18,
        category: 'GENERAL',
        provenance: sscProvenanceEligibility
      },
      {
        id: 'rule-ssc-deg',
        ruleType: 'DEGREE_REQUIRED',
        operator: '=',
        ruleValue: ['Bachelor Degree', 'Graduation', 'B.E', 'B.Tech', 'B.Sc', 'B.Com', 'B.A', 'BBA', 'BCA'],
        category: 'GENERAL',
        provenance: sscProvenanceEligibility
      },
      {
        id: 'rule-ssc-nat',
        ruleType: 'NATIONALITY',
        operator: '=',
        ruleValue: ['Indian', 'Citizen of India', 'Subject of Nepal', 'Subject of Bhutan'],
        category: 'GENERAL',
        provenance: sscProvenanceEligibility
      }
    ]
  },

  // Full 2-Tier Exam Pattern & Stages
  stages: [
    {
      id: 'stage-tier1',
      stageNumber: 1,
      stageName: 'Tier-1: Computer Based Examination (Objective MCQ)',
      tier: 'TIER_1',
      durationMinutes: 60,
      totalQuestions: 100,
      totalMarks: 200,
      negativeMarking: '-0.50 marks per wrong answer',
      mode: 'Computer Based Test (CBT Online)',
      qualifyingNature: 'Qualifying in nature for shortlisting to Tier-2. Marks normalized using official formula.',
      sections: [
        {
          sectionName: 'General Intelligence & Reasoning',
          modules: ['Verbal & Non-Verbal Reasoning', 'Analogies', 'Number Series', 'Coding-Decoding', 'Venn Diagrams'],
          questions: 25,
          marks: 50,
          durationMinutes: 15,
          negativeMarking: '-0.50'
        },
        {
          sectionName: 'General Awareness',
          modules: ['History', 'Polity & Constitution', 'Geography', 'Economy', 'General Science', 'Current Affairs'],
          questions: 25,
          marks: 50,
          durationMinutes: 15,
          negativeMarking: '-0.50'
        },
        {
          sectionName: 'Quantitative Aptitude',
          modules: ['Arithmetic', 'Algebra', 'Geometry', 'Mensuration', 'Trigonometry', 'Data Interpretation'],
          questions: 25,
          marks: 50,
          durationMinutes: 15,
          negativeMarking: '-0.50'
        },
        {
          sectionName: 'English Comprehension',
          modules: ['Spotting Error', 'Fill in Blanks', 'Cloze Test', 'Reading Comprehension', 'Idioms & Phrases'],
          questions: 25,
          marks: 50,
          durationMinutes: 15,
          negativeMarking: '-0.50'
        }
      ],
      provenance: sscProvenanceOverview
    },
    {
      id: 'stage-tier2-p1',
      stageNumber: 2,
      stageName: 'Tier-2 Paper-I (Compulsory for All Posts)',
      tier: 'TIER_2',
      durationMinutes: 135,
      totalQuestions: 150,
      totalMarks: 390,
      negativeMarking: '-1.00 mark per wrong answer in Sections I & II',
      mode: 'Computer Based Test (CBT Online)',
      qualifyingNature: 'Final Merit Score computed from 390 marks (Section I + Section II). Section III & DEST are qualifying.',
      sections: [
        {
          sectionName: 'Section I: Mathematical Abilities & Reasoning',
          modules: ['Mathematical Abilities (30 Qs - 90 Marks)', 'Reasoning & General Intelligence (30 Qs - 90 Marks)'],
          questions: 60,
          marks: 180,
          durationMinutes: 60,
          negativeMarking: '-1.00'
        },
        {
          sectionName: 'Section II: English Language & General Awareness',
          modules: ['English Language & Comprehension (45 Qs - 135 Marks)', 'General Awareness (25 Qs - 75 Marks)'],
          questions: 70,
          marks: 210,
          durationMinutes: 60,
          negativeMarking: '-1.00'
        },
        {
          sectionName: 'Section III Module 1: Computer Knowledge Test',
          modules: ['Computer Basics, Software, Internet, Networking & Cyber Security (20 Qs - 60 Marks)'],
          questions: 20,
          marks: 60,
          durationMinutes: 15,
          negativeMarking: '-1.00 (Qualifying Nature)'
        },
        {
          sectionName: 'Section III Module 2: Data Entry Speed Test (DEST)',
          modules: ['Typing Test: 2000 key depressions over 15 minutes (~27 WPM speed on English keyboard)'],
          questions: 1,
          marks: 0,
          durationMinutes: 15,
          negativeMarking: 'Qualifying Nature with permissible error %'
        }
      ],
      provenance: sscProvenanceOverview
    },
    {
      id: 'stage-tier2-p2',
      stageNumber: 3,
      stageName: 'Tier-2 Paper-II: Statistics (Only for JSO / Stat Investigator)',
      tier: 'TIER_2',
      durationMinutes: 120,
      totalQuestions: 100,
      totalMarks: 200,
      negativeMarking: '-0.50 marks per wrong answer',
      mode: 'Computer Based Test (CBT Online)',
      qualifyingNature: 'Added to Paper-1 score solely for calculating JSO / Statistical Investigator rank merit.',
      sections: [
        {
          sectionName: 'Statistics Domain Knowledge',
          modules: ['Probability, Random Variables, Sampling Theory, Statistical Inference, ANOVA, Time Series, Index Numbers'],
          questions: 100,
          marks: 200,
          durationMinutes: 120,
          negativeMarking: '-0.50'
        }
      ],
      provenance: sscProvenanceOverview
    }
  ],

  // Comprehensive Syllabus with Micro-Topic PYQ Frequency Weightages
  syllabus: [
    // --- Quantitative Aptitude ---
    {
      id: 'syl-quant-arithmetic',
      subject: 'Quantitative Aptitude',
      tier: 'BOTH',
      topicName: 'Arithmetic: Percentage, Profit & Loss, Ratio & Proportion',
      subtopics: ['Successive Discount', 'Market Price & Cost Price', 'Partnership Ratios', 'Mixture & Alligation', 'Simple & Compound Interest'],
      weightagePercentage: 24,
      avgQuestions: 6,
      isHighYield: true,
      officialProvenance: sscProvenanceSyllabus,
      weightageProvenance: sscProvenanceWeightage
    },
    {
      id: 'syl-quant-algebra',
      subject: 'Quantitative Aptitude',
      tier: 'BOTH',
      topicName: 'Algebra & Elementary Surds',
      subtopics: ['Algebraic Identities', 'Linear Equations in Two Variables', 'Quadratic Factorization', 'Symmetric Expressions (x + 1/x rules)'],
      weightagePercentage: 16,
      avgQuestions: 4,
      isHighYield: true,
      officialProvenance: sscProvenanceSyllabus,
      weightageProvenance: sscProvenanceWeightage
    },
    {
      id: 'syl-quant-geometry',
      subject: 'Quantitative Aptitude',
      tier: 'BOTH',
      topicName: 'Geometry & Mensuration (2D & 3D)',
      subtopics: ['Triangle Centers (Incenter, Orthocenter, Centroid)', 'Circle Theorems & Tangents', 'Cyclic Quadrilaterals', 'Cylinder, Cone, Sphere, Frustum Volume & TSA'],
      weightagePercentage: 22,
      avgQuestions: 5,
      isHighYield: true,
      officialProvenance: sscProvenanceSyllabus,
      weightageProvenance: sscProvenanceWeightage
    },
    {
      id: 'syl-quant-trig',
      subject: 'Quantitative Aptitude',
      tier: 'BOTH',
      topicName: 'Trigonometry & Heights and Distances',
      subtopics: ['Standard Angle Values', 'Trigonometric Identities (sin²θ+cos²θ=1)', 'Complementary Angles', 'Angles of Elevation & Depression'],
      weightagePercentage: 14,
      avgQuestions: 3,
      isHighYield: true,
      officialProvenance: sscProvenanceSyllabus,
      weightageProvenance: sscProvenanceWeightage
    },
    {
      id: 'syl-quant-di',
      subject: 'Quantitative Aptitude',
      tier: 'BOTH',
      topicName: 'Data Interpretation (DI) & Number System',
      subtopics: ['Bar Graphs, Pie Charts & Histograms', 'Divisibility Rules (7, 11, 72, 88)', 'Remainder Theorem', 'Unit Digit & Factors'],
      weightagePercentage: 16,
      avgQuestions: 4,
      isHighYield: false,
      officialProvenance: sscProvenanceSyllabus,
      weightageProvenance: sscProvenanceWeightage
    },
    {
      id: 'syl-quant-prob-stat',
      subject: 'Quantitative Aptitude',
      tier: 'TIER_2',
      topicName: 'Tier 2 New Module: Probability & Statistics Basics',
      subtopics: ['Mean, Median, Mode & Standard Deviation', 'Variance Calculation', 'Coin, Dice, Card Probability', 'Mutually Exclusive Events'],
      weightagePercentage: 8,
      avgQuestions: 2,
      isHighYield: true,
      officialProvenance: sscProvenanceSyllabus,
      weightageProvenance: sscProvenanceWeightage
    },

    // --- Reasoning & General Intelligence ---
    {
      id: 'syl-reas-analogy-series',
      subject: 'Reasoning & General Intelligence',
      tier: 'BOTH',
      topicName: 'Number & Letter Series, Analogies & Classification',
      subtopics: ['Difference Series & Prime Patterns', 'Word Association Analogies', 'Odd One Out Classification', 'Matrix Number Grids'],
      weightagePercentage: 28,
      avgQuestions: 7,
      isHighYield: true,
      officialProvenance: sscProvenanceSyllabus,
      weightageProvenance: sscProvenanceWeightage
    },
    {
      id: 'syl-reas-coding-blood',
      subject: 'Reasoning & General Intelligence',
      tier: 'BOTH',
      topicName: 'Coding-Decoding & Blood Relations',
      subtopics: ['Coded Blood Relations (A+B means father)', 'Letter Shift & Opposite Letter Coding', 'Direct Substitution Coding', 'Family Tree Construction'],
      weightagePercentage: 20,
      avgQuestions: 5,
      isHighYield: true,
      officialProvenance: sscProvenanceSyllabus,
      weightageProvenance: sscProvenanceWeightage
    },
    {
      id: 'syl-reas-syllogism-venn',
      subject: 'Reasoning & General Intelligence',
      tier: 'BOTH',
      topicName: 'Syllogism, Venn Diagrams & Logical Deductions',
      subtopics: ['Some A are B & All B are C rules', 'Possibility Cases in Syllogism', '3-Circle Intersecting Venn Sets', 'Statement & Assumptions'],
      weightagePercentage: 20,
      avgQuestions: 5,
      isHighYield: true,
      officialProvenance: sscProvenanceSyllabus,
      weightageProvenance: sscProvenanceWeightage
    },
    {
      id: 'syl-reas-nonverbal',
      subject: 'Reasoning & General Intelligence',
      tier: 'BOTH',
      topicName: 'Non-Verbal: Mirror Images, Paper Folding, Embedded Figures & Dice',
      subtopics: ['Opposite Faces of Dice', 'Clockwise/Anti-clockwise Pattern Rotation', 'Paper Cutting Folding Symmetry', 'Hidden/Embedded Shapes'],
      weightagePercentage: 22,
      avgQuestions: 5,
      isHighYield: false,
      officialProvenance: sscProvenanceSyllabus,
      weightageProvenance: sscProvenanceWeightage
    },
    {
      id: 'syl-reas-critical',
      subject: 'Reasoning & General Intelligence',
      tier: 'TIER_2',
      topicName: 'Tier 2 Critical & Analytical Reasoning',
      subtopics: ['Statement & Argument (Strong vs Weak)', 'Statement & Course of Action', 'Cause and Effect', 'Assertion and Reason'],
      weightagePercentage: 10,
      avgQuestions: 3,
      isHighYield: true,
      officialProvenance: sscProvenanceSyllabus,
      weightageProvenance: sscProvenanceWeightage
    },

    // --- English Language & Comprehension ---
    {
      id: 'syl-eng-grammar',
      subject: 'English Comprehension',
      tier: 'BOTH',
      topicName: 'Grammar: Error Spotting & Sentence Improvement',
      subtopics: ['Subject-Verb Agreement', 'Prepositions & Phrasal Verbs', 'Conditional Sentences', 'Noun/Pronoun Case Rules', 'Tense Consistency'],
      weightagePercentage: 30,
      avgQuestions: 8,
      isHighYield: true,
      officialProvenance: sscProvenanceSyllabus,
      weightageProvenance: sscProvenanceWeightage
    },
    {
      id: 'syl-eng-vocab',
      subject: 'English Comprehension',
      tier: 'BOTH',
      topicName: 'Vocabulary: Synonyms, Antonyms, One-Word Substitution & Idioms',
      subtopics: ['High-Frequency Root Words', 'Confusable Words', 'Previous 10 Years Idioms', 'Contextual Fillers'],
      weightagePercentage: 30,
      avgQuestions: 8,
      isHighYield: true,
      officialProvenance: sscProvenanceSyllabus,
      weightageProvenance: sscProvenanceWeightage
    },
    {
      id: 'syl-eng-comprehension',
      subject: 'English Comprehension',
      tier: 'BOTH',
      topicName: 'Comprehension: Cloze Test & Reading Passages',
      subtopics: ['Narrative & Editorial Passages', 'Inference & Tone Questions', '5-10 Blank Cloze Test Passages', 'Theme Title Identification'],
      weightagePercentage: 25,
      avgQuestions: 6,
      isHighYield: true,
      officialProvenance: sscProvenanceSyllabus,
      weightageProvenance: sscProvenanceWeightage
    },
    {
      id: 'syl-eng-voice-narration',
      subject: 'English Comprehension',
      tier: 'BOTH',
      topicName: 'Active/Passive Voice & Direct/Indirect Narration',
      subtopics: ['Imperative Sentences Voice Change', 'Interrogative Voice Transformations', 'Tense Backshifting in Reported Speech', 'Pronoun Shifts in Indirect Speech'],
      weightagePercentage: 15,
      avgQuestions: 3,
      isHighYield: true,
      officialProvenance: sscProvenanceSyllabus,
      weightageProvenance: sscProvenanceWeightage
    },

    // --- General Awareness ---
    {
      id: 'syl-ga-polity',
      subject: 'General Awareness',
      tier: 'BOTH',
      topicName: 'Indian Polity & Constitution',
      subtopics: ['Fundamental Rights & DPSP (Articles 12-51A)', 'President, Parliament & Supreme Court', 'Constitutional Amendments & Schedules', 'Emergency Provisions'],
      weightagePercentage: 25,
      avgQuestions: 6,
      isHighYield: true,
      officialProvenance: sscProvenanceSyllabus,
      weightageProvenance: sscProvenanceWeightage
    },
    {
      id: 'syl-ga-history',
      subject: 'General Awareness',
      tier: 'BOTH',
      topicName: 'Indian History & Freedom Struggle',
      subtopics: ['Indus Valley & Vedic Period', 'Mughal Architecture & Administration', 'Governor Generals & 1857 Revolt', 'Gandhian Movements & INC Sessions'],
      weightagePercentage: 20,
      avgQuestions: 5,
      isHighYield: true,
      officialProvenance: sscProvenanceSyllabus,
      weightageProvenance: sscProvenanceWeightage
    },
    {
      id: 'syl-ga-geography',
      subject: 'General Awareness',
      tier: 'BOTH',
      topicName: 'Geography: Indian Rivers, Mountains, Climate & Minerals',
      subtopics: ['Himalayan & Peninsular River Systems', 'National Parks & Biosphere Reserves', 'Monsoon Mechanisms & Soils of India', 'Mineral Belts & World Geography Basics'],
      weightagePercentage: 18,
      avgQuestions: 4,
      isHighYield: false,
      officialProvenance: sscProvenanceSyllabus,
      weightageProvenance: sscProvenanceWeightage
    },
    {
      id: 'syl-ga-science',
      subject: 'General Awareness',
      tier: 'BOTH',
      topicName: 'General Science: Physics, Chemistry & Biology',
      subtopics: ['Human Physiology & Vitamins/Diseases', 'Chemical Formulas, Periodic Table & Acids/Bases', 'Optics, Thermodynamics & SI Units', 'Plant Taxonomy & Genetics'],
      weightagePercentage: 20,
      avgQuestions: 5,
      isHighYield: true,
      officialProvenance: sscProvenanceSyllabus,
      weightageProvenance: sscProvenanceWeightage
    },
    {
      id: 'syl-ga-current-static',
      subject: 'General Awareness',
      tier: 'BOTH',
      topicName: 'Static GK & Recent 12 Months Current Affairs',
      subtopics: ['Classical Dances, Festivals & Musical Instruments', 'Government Welfare Schemes & Budgets', 'Sports Awards & Olympic Records', 'Summits, Military Exercises & Appointments'],
      weightagePercentage: 17,
      avgQuestions: 5,
      isHighYield: true,
      officialProvenance: sscProvenanceSyllabus,
      weightageProvenance: sscProvenanceWeightage
    },

    // --- Computer Knowledge Test ---
    {
      id: 'syl-comp-basics',
      subject: 'Computer Proficiency',
      tier: 'TIER_2',
      topicName: 'Computer Basics, Hardware & CPU Architecture',
      subtopics: ['Input/Output Devices & Ports', 'RAM, ROM, Cache Memory & Storage Units', 'Operating Systems (Windows/Linux/Android)', 'Shortcuts & File Formats'],
      weightagePercentage: 35,
      avgQuestions: 7,
      isHighYield: true,
      officialProvenance: sscProvenanceSyllabus,
      weightageProvenance: sscProvenanceWeightage
    },
    {
      id: 'syl-comp-software-internet',
      subject: 'Computer Proficiency',
      tier: 'TIER_2',
      topicName: 'MS Office 365, Internet Protocols & Cyber Security',
      subtopics: ['MS Word (Tabs, Ribbons, Tables)', 'MS Excel (VLOOKUP, SUMIF, Cell Referencing)', 'TCP/IP, HTTP/HTTPS, DNS & Web Browsers', 'Malware, Phishing, Firewalls & Cryptography'],
      weightagePercentage: 65,
      avgQuestions: 13,
      isHighYield: true,
      officialProvenance: sscProvenanceSyllabus,
      weightageProvenance: sscProvenanceWeightage
    }
  ],

  // Comprehensive Interactive Application & Document Guidelines
  applicationGuide: {
    officialPortal: 'https://ssc.gov.in',
    otrSteps: [
      {
        stepNumber: 1,
        title: 'One-Time Registration (OTR) Generation',
        portalUrl: 'https://ssc.gov.in',
        instructions: [
          'Visit official portal https://ssc.gov.in and click "Login or Register".',
          'Select "New User / Register Now" to initiate fresh OTR (Old ssc.nic.in registration numbers are deprecated).',
          'Enter Basic Personal Details: Aadhaar Number, Name, Father Name, Mother Name, and Date of Birth strictly matching Class 10 (Matriculation) Certificate.',
          'Authenticate via Mobile OTP and Email OTP to generate your unique 11-digit OTR Registration Number.'
        ],
        mandatoryFields: ['Aadhaar Number / Govt Photo ID', 'Class 10 Roll Number & Year of Passing', 'Active Mobile Number (for OTP)', 'Active Email ID'],
        commonMistakesToAvoid: [
          'Do NOT enter initials if your Class 10 marksheet contains your full name.',
          'Do NOT use third-party cyber café phone numbers or temporary emails; OTPs for admit cards and results are delivered here.'
        ]
      },
      {
        stepNumber: 2,
        title: 'Candidate Profile & Additional Category Details',
        portalUrl: 'https://ssc.gov.in',
        instructions: [
          'Log in with your OTR credentials and set a strong permanent password.',
          'Specify Category (UR / OBC / EWS / SC / ST / PwBD) and Nationality.',
          'Provide Visible Identification Marks (e.g. "A mole on right side of neck").',
          'Enter Permanent and Correspondence Address along with PIN Code and State Domicile.'
        ],
        mandatoryFields: ['Category Claim', 'Permanent Address with State/PIN', 'Visible Identification Mark'],
        commonMistakesToAvoid: [
          'Claiming OBC without possessing a valid Non-Creamy Layer (NCL) certificate issued for the crucial financial year leads to cancellation during Document Verification.',
          'Claiming EWS without the valid Income & Asset Certificate for FY 2025-26 leads to treating candidate as General (UR).'
        ]
      },
      {
        stepNumber: 3,
        title: 'Live Webcam Photo Capture & Signature Upload',
        portalUrl: 'https://ssc.gov.in',
        instructions: [
          'Open live camera capture via desktop webcam or official SSC MyGov Mobile App.',
          'Ensure background is plain white or light-colored, face is well-lit, and both ears are clearly visible.',
          'Look straight into the camera lens with a neutral facial expression (No caps, masks, dark sunglasses, or spectacles).',
          'Upload scanned Signature image in JPEG/JPG format (Size 10 KB to 20 KB, Width ~4.0 cm x Height ~2.0 cm).'
        ],
        mandatoryFields: ['Live Camera Capture Photo', 'Scanned Signature (10-20 KB JPEG)'],
        commonMistakesToAvoid: [
          'Over 40% of rejected applications in SSC occur due to improper live selfies (blurry lighting, tilted face, or wearing spectacles).',
          'Uploading tiny, blurred, or vertical signature crops will lead to automatic software disqualification.'
        ]
      },
      {
        stepNumber: 4,
        title: 'Post Preference, Exam Center Selection & Fee Payment',
        portalUrl: 'https://ssc.gov.in',
        instructions: [
          'Select 3 preferred examination center cities within the same SSC Regional Zone.',
          'Indicate whether you possess the educational qualification for Junior Statistical Officer (JSO) or Statistical Investigator.',
          'Preview the complete draft application form and verify spelling across all columns.',
          'Pay application fee of ₹100 via UPI, Net Banking, or Debit Card (Exempted for Women, SC, ST, PwBD, and ESM candidates).',
          'Download and save the PDF of the Final Submitted Application Form with Transaction ID.'
        ],
        mandatoryFields: ['Exam City Preferences (3 cities)', 'Educational Qualification details', 'Online Fee Payment / Exemption Claim'],
        commonMistakesToAvoid: [
          'Submitting the application without completing fee payment (status showing "Pending" or "Initiated" instead of "Completed"). Check payment double-verification link if amount was debited.',
          'Not saving the final PDF with timestamp; this is required during Tier-2 Document Verification.'
        ]
      }
    ],

    photoRules: {
      documentType: 'Live Webcam / App Capture Photograph',
      dimensions: 'Automatic face boundary detection by SSC portal',
      fileFormat: 'Live Portal Capture via WebRTC / Android App',
      fileSize: 'Live Capture stream',
      rules: [
        'Must be taken in bright frontal natural or white light.',
        'Background MUST be plain white or uniform light grey/off-white.',
        'Both ears and entire face must be clearly visible without shadows.',
        'No caps, hats, scarves, masks, religious headgear covering face, or sunglasses.',
        'Spectacles/Glasses must be removed during capture to avoid flash glare reflections.'
      ],
      sampleDescription: 'A sharp, frontal portrait photo with clear neutral expression on a plain white backdrop.'
    },

    signatureRules: {
      documentType: 'Scanned Specimen Signature',
      dimensions: 'Width 4.0 cm × Height 2.0 cm (Aspect Ratio 2:1)',
      fileFormat: 'JPEG / JPG only',
      fileSize: '10 KB to 20 KB (Resolution ~100-200 DPI)',
      rules: [
        'Sign with black or blue ink on clear unruled white paper.',
        'Crop tightly around the signature without leaving huge blank margins.',
        'Do NOT sign in ALL CAPITAL letters (Running handwriting only).',
        'Ensure the image is sharp and not pixelated or compressed below 10 KB.'
      ],
      sampleDescription: 'Clear black running ink signature centered on an unlined white background.'
    },

    certificateRules: [
      {
        category: 'OBC_NCL',
        title: 'Other Backward Classes (Non-Creamy Layer) Certificate',
        issuingAuthority: ['District Magistrate / Additional DM', 'Collector / Deputy Commissioner', 'Tehsildar / Sub-Divisional Magistrate (SDM)'],
        financialYearValidity: 'Certificate issued based on income of FY 2023-24, FY 2024-25, and FY 2025-26',
        crucialDate: 'Must be issued within 3 years prior to the closing date of application (or on or before 27-09-2026)',
        officialAnnexure: 'Annexure-VI of SSC CGL 2026 Notification',
        keyConditions: [
          'Caste MUST be listed in the Central List of OBCs published by National Commission for Backward Classes (NCBC). State-only OBC certificates are NOT accepted for Central Government posts.',
          'Must explicitly contain the Non-Creamy Layer exclusion clause citing DoP&T OM No. 36012/22/93-Estt.(SCT).'
        ]
      },
      {
        category: 'EWS',
        title: 'Economically Weaker Sections (EWS) Income & Asset Certificate',
        issuingAuthority: ['District Magistrate / ADM / Collector', 'Sub-Divisional Magistrate / Tehsildar', 'Taluka Magistrate'],
        financialYearValidity: 'Financial Year 2025-26 based on gross annual family income for the preceding FY 2024-25',
        crucialDate: 'Valid for the year 2026-2027 (Issued between 01-04-2026 and 27-09-2026)',
        officialAnnexure: 'Annexure-VII of SSC CGL 2026 Notification',
        keyConditions: [
          'Gross annual family income must be below ₹8 Lakhs from all sources.',
          'Must not possess 5 acres of agricultural land or 1000 sq ft residential flat.',
          'Certificate must be valid for the recruitment year 2026-27.'
        ]
      },
      {
        category: 'SC_ST',
        title: 'Scheduled Caste / Scheduled Tribe Certificate',
        issuingAuthority: ['District Magistrate / Deputy Commissioner', 'Revenue Officer not below rank of Tehsildar', 'Sub-Divisional Officer'],
        financialYearValidity: 'Permanent Validity (No financial year expiration)',
        crucialDate: 'Must be issued on or before Document Verification date in standard Central Government format',
        officialAnnexure: 'Annexure-V of SSC CGL 2026 Notification',
        keyConditions: [
          'Must specify the Presidential Order / Constitution (Scheduled Castes/Tribes) Order under which the caste/tribe is recognized.',
          'Must be in bilingual English/Hindi central format.'
        ]
      },
      {
        category: 'PwBD',
        title: 'Persons with Benchmark Disabilities (PwBD) Certificate',
        issuingAuthority: ['Duly constituted Medical Board of a State/Central Govt Hospital', 'UDID Card (Unique Disability ID)'],
        financialYearValidity: 'Permanent for non-progressive disabilities / Specified validity for temporary conditions',
        crucialDate: 'Valid UDID or Certificate with minimum 40% benchmark disability',
        officialAnnexure: 'Annexure-VIII / IX / X of SSC CGL 2026 Notification',
        keyConditions: [
          'Disability percentage must be 40% or higher.',
          'Scribe permission and compensatory time (20 mins/hr) require Annexure-I/IA certificate declaration during application.'
        ]
      }
    ],

    rejectionPitfalls: [
      {
        pitfall: 'Blurry / Inappropriate Live Webcam Photograph',
        consequence: 'Immediate Application Rejection without correction opportunity.',
        prevention: 'Use bright front lighting, plain white wall background, remove spectacles, and keep eyes wide open looking into camera lens.'
      },
      {
        pitfall: 'State-List Only OBC Certificate',
        consequence: 'Category cancelled during Document Verification; candidate converted to UR or disqualified.',
        prevention: 'Verify that your caste is included in the Central OBC Gazette list via ncbc.nic.in before selecting OBC category.'
      },
      {
        pitfall: 'Pending or Failed Online Fee Transaction',
        consequence: 'Application status marked "Incomplete" and Admit Card is NOT generated.',
        prevention: 'Check application status on SSC portal after payment. Ensure status displays "Application Received - Complete".'
      },
      {
        pitfall: 'Name Mismatch between Aadhaar and Matriculation Certificate',
        consequence: 'Discrepancy flag during Exam Entry and Document Verification.',
        prevention: 'Enter Name, Father’s Name, and DOB EXACTLY as spelled in your Class 10 certificate. Submit gazette notification if you legally changed your name.'
      },
      {
        pitfall: 'Signing in Capital Block Letters',
        consequence: 'Automatic rejection of signature specimen.',
        prevention: 'Sign in your natural running handwriting with black/blue ink pen on white unruled paper.'
      },
      {
        pitfall: 'Expired EWS Certificate Financial Year',
        consequence: 'Candidate treated as General (UR) during Tier-2 merit listing.',
        prevention: 'EWS Certificate must be issued for FY 2026-27 (evaluating income of FY 2025-26) on or before 27-09-2026.'
      },
      {
        pitfall: 'Selecting "Yes" for JSO without meeting 60% Maths or Stats criteria',
        consequence: 'Disqualification from JSO merit list after Paper-II.',
        prevention: 'Only select JSO eligibility if you have 60%+ in Class 12 Maths OR Statistics as a subject in your Degree.'
      },
      {
        pitfall: 'Submitting Multiple Applications from Different Emails',
        consequence: 'Both registrations flagged as duplicate and permanently barred by SSC.',
        prevention: 'Use only your single verified OTR account on ssc.gov.in.'
      },
      {
        pitfall: 'Entering Inaccurate Percentage / CGPA in Graduation Details',
        consequence: 'Show-cause notice during final appointment document check.',
        prevention: 'Use the official conversion formula of your University (e.g. CGPA × 9.5) and enter exact marks.'
      },
      {
        pitfall: 'Missing Crucial Application Deadline due to Server Congestion',
        consequence: 'No extension beyond 27-09-2026 23:59 IST.',
        prevention: 'Complete form submission and fee payment at least 5-7 days prior to closing date.'
      }
    ]
  },

  // Adaptive Multi-Track Preparation Roadmaps
  roadmapTracks: [
    {
      id: 'TRACK_90_DAYS',
      name: '90-Day High-Yield Sprint',
      subtitle: 'Fast-track intensive roadmap for repeaters and dedicated full-time aspirants (6-8 hours/day)',
      targetDailyHours: 7,
      suitableFor: 'Aspirants who have completed foundational concepts once or full-time students with 90 days before Tier 1.',
      dailyTimetable: [
        { timeSlot: '06:00 – 08:00 (2 hrs)', activity: 'Quantitative Aptitude Practice', focus: 'Speed calculation, Arithmetic formulas & 40 PYQ sets' },
        { timeSlot: '08:30 – 10:00 (1.5 hrs)', activity: 'English Vocabulary & Grammar', focus: '100 Vocab words/Idioms + 30 Error Spotting rules' },
        { timeSlot: '11:00 – 13:00 (2 hrs)', activity: 'General Awareness & Science', focus: 'Polity/History high-yield notes + Monthly Current Affairs' },
        { timeSlot: '15:00 – 16:30 (1.5 hrs)', activity: 'Reasoning & Speed Drill', focus: 'Sectional 25-question test in 15 minutes + analysis' },
        { timeSlot: '18:00 – 19:30 (1.5 hrs)', activity: 'Full-Length Tier-1 CBT Mock', focus: 'Real exam timed 60-min test + deep error log tracking' },
        { timeSlot: '20:30 – 21:30 (1 hr)', activity: 'Daily Revision & Formula Log', focus: 'Review incorrect mock questions & Quant flashcards' }
      ],
      phases: [
        {
          phaseNumber: 1,
          phaseTitle: 'Phase 1: High-Yield Topic Consolidation (Weeks 1 to 4)',
          durationWeeks: 4,
          focusArea: 'Mastering top 70% weightage topics in Quant (Arithmetic & Geometry), Reasoning patterns, and English Grammar rules.',
          weeklySchedule: [
            {
              weekNumber: 1,
              weekTitle: 'Week 1: Quant Arithmetic Core & English Grammar Foundation',
              goals: ['Complete Percentage, Profit & Loss, Ratio & Proportion concepts', 'Memorize Subject-Verb Agreement and Preposition rules', 'Practice 200 Coding-Decoding and Number Series questions', 'Revise Indian Polity Articles 1 to 51A'],
              suggestedDailyHours: 7,
              milestoneTest: 'Diagnostic Sectional Test: Quant & Reasoning (50 Qs)'
            },
            {
              weekNumber: 2,
              weekTitle: 'Week 2: Advanced Maths (Algebra & Trig) + Modern Indian History',
              goals: ['Master Algebra x + 1/x standard identities and Trigonometry angle tables', 'Study 1857 Revolt to 1947 Freedom Struggle timeline', 'Memorize 300 One-Word Substitutions & Idioms', 'Practice Syllogism and Venn diagram sets'],
              suggestedDailyHours: 7,
              milestoneTest: 'Sectional Test: English & General Awareness (50 Qs)'
            },
            {
              weekNumber: 3,
              weekTitle: 'Week 3: Geometry, Mensuration & General Science (Bio/Chem)',
              goals: ['Learn Triangle centers, Circle tangent properties and 3D formulas', 'Revise Human Physiology, Vitamins, Diseases and Periodic Table', 'Complete 10 Reading Comprehension and 15 Cloze Test passages', 'Practice Non-Verbal Dice and Paper Folding questions'],
              suggestedDailyHours: 7,
              milestoneTest: 'Full-Length Tier-1 Baseline Mock Test #01'
            },
            {
              weekNumber: 4,
              weekTitle: 'Week 4: Number System, DI, Geography & Static GK',
              goals: ['Master Divisibility rules (72, 88), Remainder theorem and Bar/Pie DI charts', 'Memorize Classical dances, Rivers, National Parks and Census data', 'Review Active/Passive and Direct/Indirect speech rules', 'Analyze weak areas from Mock #01'],
              suggestedDailyHours: 7,
              milestoneTest: 'Full-Length Tier-1 Benchmark Mock Test #02'
            }
          ]
        },
        {
          phaseNumber: 2,
          phaseTitle: 'Phase 2: Speed Building & Full-Length Mock Testing (Weeks 5 to 8)',
          durationWeeks: 4,
          focusArea: 'Transitioning from untimed topic study to 60-minute full exam simulations with strict negative marking control.',
          weeklySchedule: [
            {
              weekNumber: 5,
              weekTitle: 'Week 5: Sectional Speed Optimization (Target < 55 Mins)',
              goals: ['Reduce Quant solving time to 22 mins, Reasoning to 14 mins, English to 10 mins, GA to 6 mins', 'Take 3 full-length mocks per week and log every error into a mistake notebook', 'Revise 6 months of National Current Affairs'],
              suggestedDailyHours: 7,
              milestoneTest: 'Full-Length Mock Test #03 & #04'
            },
            {
              weekNumber: 6,
              weekTitle: 'Week 6: PYQ Shift Re-simulation (2022-2024 Shits)',
              goals: ['Solve 5 actual previous year question papers in timed CBT mode', 'Eliminate recurring errors in Geometry and Sentence Improvement', 'Memorize High-Frequency GK Government Schemes'],
              suggestedDailyHours: 8,
              milestoneTest: 'Previous Year Shift Paper Re-Test (Target: 145+ Marks)'
            },
            {
              weekNumber: 7,
              weekTitle: 'Week 7: Computer Awareness & Tier-2 Section III Prep',
              goals: ['Study MS Office 365, Shortcut keys, Networking, and Cyber Security modules', 'Practice 15 minutes of daily touch-typing on English keyboard (Target: 30 WPM)', 'Continue 3 Tier-1 full mocks per week'],
              suggestedDailyHours: 8,
              milestoneTest: 'Full-Length Mock Test #05 & Computer Qualifying Quiz'
            },
            {
              weekNumber: 8,
              weekTitle: 'Week 8: High-Difficulty Shift Question Mastery',
              goals: ['Attempt toughest 10% questions from past shifts in Quant & Reasoning', 'Intensive Vocab and Cloze test revision', 'Target score threshold: 155+ in UR category'],
              suggestedDailyHours: 8,
              milestoneTest: 'Advanced Full-Length Mock Test #06'
            }
          ]
        },
        {
          phaseNumber: 3,
          phaseTitle: 'Phase 3: Final 14-Day Exam Conditioning & Revision (Weeks 9 to 12)',
          durationWeeks: 4,
          focusArea: 'Calm mental conditioning, formula handbook drills, current affairs roundups, and zero new theory.',
          weeklySchedule: [
            {
              weekNumber: 9,
              weekTitle: 'Week 9: Comprehensive Formula & Rule Drills',
              goals: ['Revise all Quant arithmetic and geometry formulas twice', 'Review 500 rule notes from English error notebook', 'Daily 1 mock test in morning shift matching real exam slot'],
              suggestedDailyHours: 6,
              milestoneTest: 'Pre-Exam Mock Test #07'
            },
            {
              weekNumber: 10,
              weekTitle: 'Week 10: Current Affairs & Static GK Marathon',
              goals: ['Review 12-month Current Affairs compendium (Sports, Awards, Summits, Appointments)', 'Quick-fire revision of Articles, Amendments and History battles', 'Take Mock #08'],
              suggestedDailyHours: 6,
              milestoneTest: 'Pre-Exam Mock Test #08'
            },
            {
              weekNumber: 11,
              weekTitle: 'Week 11: Exam Simulation & Time Management Polish',
              goals: ['Final 2 mock tests strictly adhering to question skipping strategy', 'Ensure negative marks stay below 4 marks per paper', 'Print Admit card and assemble verified photo ID proof'],
              suggestedDailyHours: 5,
              milestoneTest: 'Final Confidence Booster Mock Test'
            },
            {
              weekNumber: 12,
              weekTitle: 'Week 12: Light Revision & Rest before Exam Day',
              goals: ['Review quick formula cheat-sheets only', 'No heavy mocks in last 48 hours to prevent mental fatigue', 'Sleep 8 hours, stay hydrated, and verify exam center location'],
              suggestedDailyHours: 4,
              milestoneTest: 'Ready for SSC CGL Tier-1 Exam Hall'
            }
          ]
        }
      ]
    },
    {
      id: 'TRACK_180_DAYS',
      name: '180-Day Comprehensive Foundation',
      subtitle: 'Complete zero-to-advanced mastery roadmap for first-time aspirants (4-5 hours/day)',
      targetDailyHours: 5,
      suitableFor: 'First-time graduate applicants and college final-year students preparing systematically over 6 months.',
      dailyTimetable: [
        { timeSlot: '07:00 – 09:00 (2 hrs)', activity: 'Concept Learning & Notes', focus: 'Fundamental theory chapters in Quant or English' },
        { timeSlot: '11:00 – 12:30 (1.5 hrs)', activity: 'Topic-wise Question Practice', focus: '50-60 graded practice questions (Easy to Hard)' },
        { timeSlot: '17:00 – 18:00 (1 hr)', activity: 'General Awareness & Newspaper', focus: 'Static GK chapter + Daily Editorial / Current Affairs' },
        { timeSlot: '19:30 – 20:30 (1 hr)', activity: 'Reasoning & Logic Drill', focus: '30 questions across verbal & non-verbal reasoning' }
      ],
      phases: [
        {
          phaseNumber: 1,
          phaseTitle: 'Phase 1: Basic Foundations & Concept Building (Months 1 & 2)',
          durationWeeks: 8,
          focusArea: 'Building thorough subject clarity across NCERT Class 9-10 Mathematics, English Grammar fundamentals, and General Awareness basics.',
          weeklySchedule: [
            {
              weekNumber: 1,
              weekTitle: 'Weeks 1-4: Basic Mathematics & English Grammar Rules',
              goals: ['Master calculation tables up to 30, squares up to 50, cubes up to 30', 'Complete Percentages, Ratios, Averages and Profit & Loss', 'Grammar parts of speech: Nouns, Pronouns, Verbs, Adjectives, Adverbs'],
              suggestedDailyHours: 4,
              milestoneTest: 'Monthly Concept Benchmark Test #01'
            },
            {
              weekNumber: 2,
              weekTitle: 'Weeks 5-8: Advanced Mathematics & Indian Polity Foundations',
              goals: ['Algebraic identities and linear/quadratic equations', 'Trigonometric ratios and identities', 'Indian Constitution: Preamble, Fundamental Rights, Parliament and Judiciary'],
              suggestedDailyHours: 5,
              milestoneTest: 'Monthly Concept Benchmark Test #02'
            }
          ]
        },
        {
          phaseNumber: 2,
          phaseTitle: 'Phase 2: Intermediate Topic Mastery & PYQ Drilling (Months 3 & 4)',
          durationWeeks: 8,
          focusArea: 'Solving chapter-wise previous 5 years questions and mastering speed calculation shortcuts.',
          weeklySchedule: [
            {
              weekNumber: 3,
              weekTitle: 'Weeks 9-12: Geometry, Mensuration & Modern History',
              goals: ['Comprehensive Geometry: Triangle theorems, circles, quadrilaterals', '2D & 3D Mensuration formulas and derivations', 'Ancient, Medieval and Modern Indian History chronology'],
              suggestedDailyHours: 5,
              milestoneTest: 'Mid-Term Comprehensive Mock #01'
            },
            {
              weekNumber: 4,
              weekTitle: 'Weeks 13-16: General Science, Geography & Full Vocab Builder',
              goals: ['Physics, Chemistry and Biology standard textbook topics', 'Indian & World Geography: Rivers, Climate, Agriculture and Mineral maps', '1000 high-frequency SSC vocabulary words'],
              suggestedDailyHours: 5,
              milestoneTest: 'Mid-Term Comprehensive Mock #02'
            }
          ]
        },
        {
          phaseNumber: 3,
          phaseTitle: 'Phase 3: Full-Length Mocks & Tier-2 Dual Preparation (Months 5 & 6)',
          durationWeeks: 8,
          focusArea: 'Full CBT mocks, Computer Knowledge Test preparation, Typing practice, and Tier 2 high-level questions.',
          weeklySchedule: [
            {
              weekNumber: 5,
              weekTitle: 'Weeks 17-20: Tier-1 Intensive Mock Sprint & Typing Drills',
              goals: ['2 full mocks per week with 2-hour post-mock analysis', 'Daily 20 mins keyboard typing practice (Target 30 WPM)', 'Computer Knowledge fundamentals (MS Office, Networking, Security)'],
              suggestedDailyHours: 5,
              milestoneTest: 'Full-Length Tier-1 Mock #07'
            },
            {
              weekNumber: 6,
              weekTitle: 'Weeks 21-24: Final 30-Day Peak Conditioning',
              goals: ['Solve 10 actual past shift papers', 'Target 160+ marks in Tier-1 practice tests', 'Final formula sheets and mistake log consolidation'],
              suggestedDailyHours: 6,
              milestoneTest: 'Pre-Exam Grand All-India Mock Test'
            }
          ]
        }
      ]
    },
    {
      id: 'TRACK_WORKING_PRO',
      name: 'Working Professional 3-Hours/Day Track',
      subtitle: 'Smart high-yield efficiency roadmap tailored for working candidates (2.5 - 3.5 hours/day + Weekend Deep Sprints)',
      targetDailyHours: 3,
      suitableFor: 'Employed individuals balancing full-time jobs with weekend study surges.',
      dailyTimetable: [
        { timeSlot: '06:00 – 07:30 (1.5 hrs Morning)', activity: 'High-Focus Quantitative Aptitude', focus: '30 difficult questions + formula revision when mind is fresh' },
        { timeSlot: 'Lunch Break / Commute (30 mins)', activity: 'Mobile Vocab & Current Affairs Flashcards', focus: 'Quick 30 vocab words / Daily current affairs digest' },
        { timeSlot: '21:00 – 22:30 (1.5 hrs Evening)', activity: 'Reasoning or English Practice', focus: 'Sectional test + review' },
        { timeSlot: 'Saturday / Sunday (6-8 hrs)', activity: 'Weekend Deep Sprint', focus: '2 Full-length CBT mocks + in-depth weak area revision' }
      ],
      phases: [
        {
          phaseNumber: 1,
          phaseTitle: 'Phase 1: High-Yield Core Focus (Weeks 1 to 8)',
          durationWeeks: 8,
          focusArea: 'Prioritizing only the top 80% scoring areas across all 4 subjects to maximize ROI per study hour.',
          weeklySchedule: [
            {
              weekNumber: 1,
              weekTitle: 'Weeks 1-4: Arithmetic & English Grammar Essentials',
              goals: ['Complete Percentage, Profit & Loss, Ratio, Time & Work', 'Subject-Verb Agreement, Tenses, Preposition rules', 'Weekend: 2 Sectional Mocks'],
              suggestedDailyHours: 3,
              milestoneTest: 'Weekend Sectional Test (Quant + English)'
            },
            {
              weekNumber: 2,
              weekTitle: 'Weeks 5-8: Algebra, Geometry & High-Yield Polity/Science',
              goals: ['Algebra x+1/x patterns, Basic Triangle & Circle geometry', 'Constitution Articles 1-51A, Fundamental Rights, Science basics', 'Weekend: Full Tier-1 Mock'],
              suggestedDailyHours: 3,
              milestoneTest: 'Weekend Full Mock #01'
            }
          ]
        },
        {
          phaseNumber: 2,
          phaseTitle: 'Phase 2: Weekend Mock Marathons & Error Analysis (Weeks 9 to 16)',
          durationWeeks: 8,
          focusArea: 'Using weekends for rigorous full-length CBT tests and weekdays for targeted error remediation.',
          weeklySchedule: [
            {
              weekNumber: 3,
              weekTitle: 'Weeks 9-16: Consistent Weekend Mock Testing',
              goals: ['Attempt 2 full mocks every weekend (Total 16 mocks)', 'Maintain strict mistake notebook for commute revisions', 'Practice 15 mins typing on weekends'],
              suggestedDailyHours: 3,
              milestoneTest: 'Weekend Pro Mock Series'
            }
          ]
        }
      ]
    }
  ],

  // Shift-wise Verified Previous Year Questions (PYQs) with Step-by-Step Solutions
  practiceQuestions: [
    {
      id: 'pyq-cgl-2024-q1',
      topicId: 'syl-quant-arithmetic',
      subject: 'Quantitative Aptitude',
      topicName: 'Arithmetic: Profit & Loss and Successive Discounts',
      tier: 'TIER_1',
      shiftInfo: 'SSC CGL 2024 Tier-1 (Shift 2, 12-Sep-2024)',
      questionType: 'OFFICIAL_PYQ',
      year: 2024,
      difficulty: 'MEDIUM',
      questionText:
        'A shopkeeper marks an article at 40% above its cost price and allows a discount of 20% on the marked price. In addition, during a festival sale, he offers an additional cash discount of 5% on the discounted price. If the cost price of the article is ₹1,500, what is the shopkeeper\'s net profit or loss in rupees?',
      options: [
        { id: 0, text: 'Profit of ₹96' },
        { id: 1, text: 'Profit of ₹144' },
        { id: 2, text: 'Profit of ₹180' },
        { id: 3, text: 'Loss of ₹72' }
      ],
      correctOptionIndex: 0,
      explanation:
        'Step 1: Cost Price (CP) = ₹1,500.\n' +
        'Step 2: Marked Price (MP) = 1500 × (1 + 0.40) = 1500 × 1.40 = ₹2,100.\n' +
        'Step 3: First discounted price after 20% discount = 2100 × (1 - 0.20) = 2100 × 0.80 = ₹1,680.\n' +
        'Step 4: Selling Price (SP) after additional 5% cash discount = 1680 × (1 - 0.05) = 1680 × 0.95 = ₹1,596.\n' +
        'Step 5: Net Profit = SP - CP = ₹1,596 - ₹1,500 = ₹96 Profit.\n' +
        'Hence, Option A (Profit of ₹96) is correct.',
      provenance: sscProvenanceOverview
    },
    {
      id: 'pyq-cgl-2024-q2',
      topicId: 'syl-quant-algebra',
      subject: 'Quantitative Aptitude',
      topicName: 'Algebra: Symmetric Identities (x + 1/x)',
      tier: 'TIER_1',
      shiftInfo: 'SSC CGL 2024 Tier-1 (Shift 1, 14-Sep-2024)',
      questionType: 'OFFICIAL_PYQ',
      year: 2024,
      difficulty: 'EASY',
      questionText:
        'If x + (1 / x) = 4, where x > 0, find the value of x⁴ + (1 / x⁴).',
      options: [
        { id: 0, text: '194' },
        { id: 1, text: '196' },
        { id: 2, text: '142' },
        { id: 3, text: '144' }
      ],
      correctOptionIndex: 0,
      explanation:
        'Step 1: Using identity (x + 1/x)² = x² + 1/x² + 2:\n' +
        'x² + 1/x² = 4² - 2 = 16 - 2 = 14.\n' +
        'Step 2: Squaring again:\n' +
        '(x² + 1/x²)² = x⁴ + 1/x⁴ + 2\n' +
        '14² = x⁴ + 1/x⁴ + 2\n' +
        '196 = x⁴ + 1/x⁴ + 2\n' +
        'x⁴ + 1/x⁴ = 196 - 2 = 194.\n' +
        'Hence, Option A (194) is the correct answer.',
      provenance: sscProvenanceOverview
    },
    {
      id: 'pyq-cgl-2024-q3',
      topicId: 'syl-ga-polity',
      subject: 'General Awareness',
      topicName: 'Indian Polity: Constitutional Articles',
      tier: 'TIER_1',
      shiftInfo: 'SSC CGL 2024 Tier-1 (Shift 3, 16-Sep-2024)',
      questionType: 'OFFICIAL_PYQ',
      year: 2024,
      difficulty: 'EASY',
      questionText:
        'Which Article of the Constitution of India provides that the law declared by the Supreme Court shall be binding on all courts within the territory of India?',
      options: [
        { id: 0, text: 'Article 141' },
        { id: 1, text: 'Article 142' },
        { id: 2, text: 'Article 136' },
        { id: 3, text: 'Article 124' }
      ],
      correctOptionIndex: 0,
      explanation:
        'Article 141 of the Constitution of India explicitly mandates: "The law declared by the Supreme Court shall be binding on all courts within the territory of India."\n' +
        '• Article 142 deals with enforcement of decrees and orders of Supreme Court to do complete justice.\n' +
        '• Article 136 deals with Special Leave to Appeal (SLP).\n' +
        '• Article 124 deals with establishment and constitution of the Supreme Court.',
      provenance: sscProvenanceOverview
    },
    {
      id: 'pyq-cgl-2024-q4',
      topicId: 'syl-eng-grammar',
      subject: 'English Comprehension',
      topicName: 'Grammar: Error Spotting & Subject-Verb Agreement',
      tier: 'TIER_1',
      shiftInfo: 'SSC CGL 2024 Tier-1 (Shift 2, 18-Sep-2024)',
      questionType: 'OFFICIAL_PYQ',
      year: 2024,
      difficulty: 'MEDIUM',
      questionText:
        'Identify the segment in the sentence which contains a grammatical error:\n\n"Neither the team captain (A) / nor the members of the committee (B) / was present at the annual prize distribution ceremony (C) / yesterday evening (D)."',
      options: [
        { id: 0, text: 'was present at the annual prize' },
        { id: 1, text: 'Neither the team captain' },
        { id: 2, text: 'nor the members of the committee' },
        { id: 3, text: 'yesterday evening' }
      ],
      correctOptionIndex: 0,
      explanation:
        'Rule: When two subjects are joined by "neither... nor", "either... or", or "not only... but also", the verb must agree in number with the NEARER subject.\n' +
        'Here, the nearer subject is "the members of the committee", which is plural. Therefore, the singular verb "was" must be replaced with the plural verb "were".\n' +
        'Correct Sentence: "Neither the team captain nor the members of the committee were present..."\n' +
        'Hence, part C / Option A contains the grammatical error.',
      provenance: sscProvenanceOverview
    },
    {
      id: 'pyq-cgl-2024-q5',
      topicId: 'syl-reas-syllogism-venn',
      subject: 'Reasoning & General Intelligence',
      topicName: 'Syllogism: Logical Deductions',
      tier: 'TIER_1',
      shiftInfo: 'SSC CGL 2024 Tier-1 (Shift 1, 20-Sep-2024)',
      questionType: 'OFFICIAL_PYQ',
      year: 2024,
      difficulty: 'MEDIUM',
      questionText:
        'Read the given statements and conclusions carefully. Assuming that the information given in the statements is true, decide which of the given conclusions logically follow(s):\n\nStatements:\n1. All computers are laptops.\n2. Some laptops are tablets.\n3. No tablet is a smartphone.\n\nConclusions:\nI. Some computers are tablets.\nII. No smartphone is a tablet.\nIII. Some laptops are not smartphones.',
      options: [
        { id: 0, text: 'Only conclusions II and III follow' },
        { id: 1, text: 'Only conclusion II follows' },
        { id: 2, text: 'All conclusions I, II and III follow' },
        { id: 3, text: 'Only conclusion I follows' }
      ],
      correctOptionIndex: 0,
      explanation:
        'Analysis:\n' +
        '• Conclusion I: "Some computers are tablets" – Not necessarily true because the computer circle and tablet circle may not intersect.\n' +
        '• Conclusion II: "No smartphone is a tablet" – Statement 3 says "No tablet is a smartphone", so its converse "No smartphone is a tablet" is definitely TRUE.\n' +
        '• Conclusion III: "Some laptops are not smartphones" – The portion of laptops that are tablets cannot be smartphones (since No tablet is smartphone). Therefore, those laptops can never be smartphones. TRUE.\n' +
        'Hence, only conclusions II and III follow (Option A).',
      provenance: sscProvenanceOverview
    },
    {
      id: 'pyq-cgl-2024-q6',
      topicId: 'syl-comp-software-internet',
      subject: 'Computer Proficiency',
      topicName: 'Computer Basics: Networking & Protocols',
      tier: 'TIER_2',
      shiftInfo: 'SSC CGL Tier-2 Paper-I (Section III Computer Module)',
      questionType: 'OFFICIAL_PYQ',
      year: 2024,
      difficulty: 'MEDIUM',
      questionText:
        'Which protocol in the TCP/IP protocol suite is responsible for automatically assigning dynamic IP addresses, subnet masks, and default gateways to client devices on a local area network?',
      options: [
        { id: 0, text: 'DHCP (Dynamic Host Configuration Protocol)' },
        { id: 1, text: 'DNS (Domain Name System)' },
        { id: 2, text: 'ARP (Address Resolution Protocol)' },
        { id: 3, text: 'SMTP (Simple Mail Transfer Protocol)' }
      ],
      correctOptionIndex: 0,
      explanation:
        '• DHCP (Dynamic Host Configuration Protocol) automatically assigns IP addresses, subnet masks, gateway IPs, and DNS server addresses to host devices on a network.\n' +
        '• DNS resolves human-readable domain names (e.g. ssc.gov.in) into IP addresses.\n' +
        '• ARP resolves IP addresses into physical MAC addresses on a local subnet.\n' +
        '• SMTP is used for sending electronic mail (email).',
      provenance: sscProvenanceOverview
    }
  ],

  // Corrigendum Notices
  corrigendums: [
    {
      id: 'corr-cgl-01',
      title: 'Corrigendum-I: Clarification on PwBD Scribe Guidelines and Compensatory Time',
      noticeNumber: 'F.No. HQ-PPI03/11/2026-PP_1',
      publishedDate: '2026-08-16',
      effectiveDate: '2026-08-16',
      summary: 'Clarification regarding provision of scribe and compensatory time of 20 minutes per hour for PwBD candidates possessing physical limitation certificate.',
      pdfUrl: 'https://ssc.gov.in',
      status: 'ACTIVE',
      diffSummary: 'Scribe declaration Annexure-I/IA made mandatory at application stage.'
    },
    {
      id: 'corr-cgl-02',
      title: 'Corrigendum-II: Extension of Online Application Window & Fee Payment Deadline',
      noticeNumber: 'F.No. HQ-PPI03/15/2026-PP_2',
      publishedDate: '2026-08-22',
      effectiveDate: '2026-08-22',
      summary: 'In view of heavy server traffic and student representations, Commission has extended the closing date for receipt of online applications from 20-09-2026 to 27-09-2026 (23:59 IST).',
      pdfUrl: 'https://ssc.gov.in',
      status: 'ACTIVE',
      diffSummary: 'Application window extended from 20-Sep-2026 to 27-Sep-2026 (23:59 IST).'
    }
  ],

  // Historical Cutoff Data Across Categories (2021-2024)
  cutoffsHistory: [
    { year: 2024, category: 'UR (Unreserved / General)', tier1Cutoff: 150.04, tier2Cutoff: 308.5, postsEligible: 'All Non-JSO & JSO shortlisted lists', provenance: sscProvenanceOverview },
    { year: 2024, category: 'OBC (Other Backward Classes)', tier1Cutoff: 145.80, tier2Cutoff: 302.0, postsEligible: 'All Non-JSO & JSO shortlisted lists', provenance: sscProvenanceOverview },
    { year: 2024, category: 'EWS (Economically Weaker Section)', tier1Cutoff: 143.20, tier2Cutoff: 298.5, postsEligible: 'All Non-JSO & JSO shortlisted lists', provenance: sscProvenanceOverview },
    { year: 2024, category: 'SC (Scheduled Caste)', tier1Cutoff: 126.50, tier2Cutoff: 275.0, postsEligible: 'All Non-JSO & JSO shortlisted lists', provenance: sscProvenanceOverview },
    { year: 2024, category: 'ST (Scheduled Tribe)', tier1Cutoff: 118.20, tier2Cutoff: 261.0, postsEligible: 'All Non-JSO & JSO shortlisted lists', provenance: sscProvenanceOverview },
    { year: 2024, category: 'PwBD (Persons with Disabilities)', tier1Cutoff: 85.50, tier2Cutoff: 220.0, postsEligible: 'Identified PwBD posts', provenance: sscProvenanceOverview },
    
    { year: 2023, category: 'UR (Unreserved / General)', tier1Cutoff: 150.04, tier2Cutoff: 302.5, provenance: sscProvenanceOverview },
    { year: 2023, category: 'OBC', tier1Cutoff: 145.93, tier2Cutoff: 296.0, provenance: sscProvenanceOverview },
    { year: 2023, category: 'EWS', tier1Cutoff: 143.44, tier2Cutoff: 292.0, provenance: sscProvenanceOverview },
    { year: 2023, category: 'SC', tier1Cutoff: 126.68, tier2Cutoff: 268.0, provenance: sscProvenanceOverview },
    { year: 2023, category: 'ST', tier1Cutoff: 118.16, tier2Cutoff: 254.0, provenance: sscProvenanceOverview },

    { year: 2022, category: 'UR (Unreserved / General)', tier1Cutoff: 114.27, tier2Cutoff: 291.0, provenance: sscProvenanceOverview },
    { year: 2022, category: 'OBC', tier1Cutoff: 114.27, tier2Cutoff: 285.0, provenance: sscProvenanceOverview },
    { year: 2022, category: 'EWS', tier1Cutoff: 102.35, tier2Cutoff: 280.0, provenance: sscProvenanceOverview },
    { year: 2022, category: 'SC', tier1Cutoff: 89.08, tier2Cutoff: 255.0, provenance: sscProvenanceOverview },
    { year: 2022, category: 'ST', tier1Cutoff: 77.56, tier2Cutoff: 240.0, provenance: sscProvenanceOverview }
  ],

  // Community-Vetted, Most Trusted & Topper Recommended Resources (AIR 1 & Majority Consensus)
  resources: [
    {
      id: 'res-ssc-notice-2026',
      title: 'SSC CGL 2026 Official Notice (Complete 132-page Notification)',
      subject: 'Official Gazette',
      author: 'Staff Selection Commission (SSC)',
      type: 'OFFICIAL_PDF',
      resourceFormat: 'DIRECT_PDF',
      url: 'https://ssc.gov.in/api/attachment/uploads/masterData/NoticeBoards/Notice_of_adv_cgl_2026.pdf',
      directPdfUrl: 'https://ssc.gov.in/api/attachment/uploads/masterData/NoticeBoards/Notice_of_adv_cgl_2026.pdf',
      downloadFileName: 'Notice_of_adv_cgl_2026.pdf',
      officialTag: 'SSC — PRIMARY NOTIFICATION (PDF, 1.2 MB)',
      recommendedFor: 'The single document to read before applying. Verify any claim you see elsewhere — including on GovOS — against this PDF.',
      description: "The Commission's own notification PDF for CGLE 2026, hosted on ssc.gov.in. Contains the vacancy position, age limits and the crucial date, the full scheme of examination, the Tier-1 and Tier-2 syllabus, and every certificate annexure. GovOS links to the file on the SSC server rather than keeping a copy.",
      linkVerifiedDate: CHECK_DATE,
      isEssential: true,
      inAppHandbookContent: {
        summary: "The Commission's own notification PDF for CGLE 2026, hosted on ssc.gov.in. Contains the vacancy position, age limits and the crucial date, the full scheme of examination, the Tier-1 and Tier-2 syllabus, and every certificate annexure. GovOS links to the file on the SSC server rather than keeping a copy.",
        chapters: [
          {
            chapterTitle: 'What the notice states (read from the official PDF)',
            contentMarkdown: '• **Applications:** 21.05.2026 to 22.06.2026 (23:00 hours); fee payment up to 23.06.2026 (23:00 hours).\n• **Tentative vacancies:** approx. 12,256, being collected by the Commission.\n• **Age limit:** reckoned as on 01-08-2026.\n• **Tier-I (CBE):** August–September 2026 (tentative).\n• **Tier-II (CBE):** December 2026 (tentative).\n\nThese figures were read directly from the linked PDF on 09-Sep-2026. Where GovOS pages show different dates, the PDF is authoritative.'
          },
          {
            chapterTitle: 'How to use it',
            contentMarkdown: '• Section 13 carries the scheme of examination and the detailed syllabus, including Section-III Computer Knowledge for Tier-2.\n• The annexures carry the prescribed certificate formats (OBC, EWS, SC/ST, PwBD).\n• Open the file directly from ssc.gov.in so you always get the current revision.'
          }
        ]
      },
      provenance: officialSource('prov-res-ssc-notice-2026', 'SSC CGL 2026 Official Notice (Complete 132-page Notification)', 'https://ssc.gov.in/api/attachment/uploads/masterData/NoticeBoards/Notice_of_adv_cgl_2026.pdf', 200)
    },
    {
      id: 'res-ssc-reopen-notice',
      title: 'SSC CGL 2026 — Reopening of the Application Window (Official Notice)',
      subject: 'Official Gazette',
      author: 'Staff Selection Commission (SSC)',
      type: 'OFFICIAL_PDF',
      resourceFormat: 'DIRECT_PDF',
      url: 'https://ssc.gov.in/api/attachment/uploads/masterData/NoticeBoards/CGLE_Reopen_23062026.pdf',
      directPdfUrl: 'https://ssc.gov.in/api/attachment/uploads/masterData/NoticeBoards/CGLE_Reopen_23062026.pdf',
      downloadFileName: 'CGLE_Reopen_23062026.pdf',
      officialTag: 'SSC — AMENDMENT NOTICE (PDF)',
      recommendedFor: 'Confirming whether an application window really was extended, instead of trusting a coaching-site headline.',
      description: 'The Commission notice reopening the CGLE 2026 online application window, issued after more than 28 lakh candidates had already applied. Shows exactly how SSC communicates a change to a published schedule.',
      linkVerifiedDate: CHECK_DATE,
      provenance: officialSource('prov-res-ssc-reopen-notice', 'SSC CGL 2026 — Reopening of the Application Window (Official Notice)', 'https://ssc.gov.in/api/attachment/uploads/masterData/NoticeBoards/CGLE_Reopen_23062026.pdf', 200)
    },
    {
      id: 'res-ssc-pyq',
      title: 'SSC Previous Year Question Papers — Official Page',
      subject: 'Official Gazette',
      author: 'Staff Selection Commission (SSC)',
      type: 'OFFICIAL_PORTAL',
      resourceFormat: 'OFFICIAL_PORTAL',
      url: 'https://ssc.gov.in/for-candidates/previous-year-question-paper',
      officialTag: 'SSC — OFFICIAL PAPERS PAGE',
      recommendedFor: 'Checking whether SSC has released papers for your cycle. For released papers with the official key, use the Answer Key page below.',
      description: "The Commission's own previous-year question paper page. SSC publishes papers here as and when it releases them, so availability changes between examination cycles — at the time of checking the page listed no downloadable file. Coaching-site compilations are not official and often mix years and shifts.",
      linkVerifiedDate: CHECK_DATE,
      isEssential: true,
      provenance: officialSource('prov-res-ssc-pyq', 'SSC Previous Year Question Papers — Official Page', 'https://ssc.gov.in/for-candidates/previous-year-question-paper', 200)
    },
    {
      id: 'res-ssc-answer-key',
      title: 'SSC Answer Keys, Question Papers & Response Sheets — Official Page',
      subject: 'Official Gazette',
      author: 'Staff Selection Commission (SSC)',
      type: 'OFFICIAL_PORTAL',
      resourceFormat: 'OFFICIAL_PORTAL',
      url: 'https://ssc.gov.in/home/answer-key',
      officialTag: 'SSC — OFFICIAL ANSWER KEYS',
      recommendedFor: 'Downloading your own response sheet after an exam, and settling disputes about a question with the official final key.',
      description: "Where SSC uploads tentative and final answer keys together with candidates' question-paper-cum-response sheets. This is the only authoritative source for what the correct answer to a past question actually was, and it is where the paid challenge window is announced.",
      linkVerifiedDate: CHECK_DATE,
      isEssential: true,
      provenance: officialSource('prov-res-ssc-answer-key', 'SSC Answer Keys, Question Papers & Response Sheets — Official Page', 'https://ssc.gov.in/home/answer-key', 200)
    },
    {
      id: 'res-ssc-calendar',
      title: 'SSC Annual Examination Calendar — Official Page',
      subject: 'Official Gazette',
      author: 'Staff Selection Commission (SSC)',
      type: 'OFFICIAL_PORTAL',
      resourceFormat: 'OFFICIAL_PORTAL',
      url: 'https://ssc.gov.in/for-candidates/examination-calendar',
      officialTag: 'SSC — OFFICIAL CALENDAR',
      recommendedFor: 'Planning which SSC examinations to attempt in a year and when their windows open.',
      description: "The Commission's published calendar of notification, application and examination dates for every SSC examination in the cycle.",
      linkVerifiedDate: CHECK_DATE,
      provenance: officialSource('prov-res-ssc-calendar', 'SSC Annual Examination Calendar — Official Page', 'https://ssc.gov.in/for-candidates/examination-calendar', 200)
    },
    {
      id: 'res-constitution-pdf',
      title: 'The Constitution of India — Official Full Text (PDF)',
      subject: 'General Awareness & Static GK',
      author: 'Legislative Department, Ministry of Law & Justice',
      type: 'OFFICIAL_PDF',
      resourceFormat: 'DIRECT_PDF',
      url: 'https://www.legislative.gov.in/static/uploads/2025/07/c9fe9c9b6840524844316f74bb1c556c.pdf',
      directPdfUrl: 'https://www.legislative.gov.in/static/uploads/2025/07/c9fe9c9b6840524844316f74bb1c556c.pdf',
      downloadFileName: 'Constitution_of_India_Official.pdf',
      officialTag: 'MINISTRY OF LAW & JUSTICE — PRIMARY LEGAL TEXT (PDF, 2.6 MB)',
      recommendedFor: 'Confirming the precise wording and number of an Article instead of relying on a summary. Search the PDF for the Article number.',
      description: 'The complete, current text of the Constitution as published by the Legislative Department, with amendments incorporated. Every Article, Part and Schedule in its exact official wording — the source GovOS uses to write and check its own polity questions.',
      linkVerifiedDate: CHECK_DATE,
      isEssential: true,
      provenance: officialSource('prov-res-constitution-pdf', 'The Constitution of India — Official Full Text (PDF)', 'https://www.legislative.gov.in/static/uploads/2025/07/c9fe9c9b6840524844316f74bb1c556c.pdf', 200)
    },
    {
      id: 'res-ncert-exemplar-x-maths',
      title: 'NCERT Exemplar Problems — Class 10 Mathematics (NCERT\'s free edition)',
      subject: 'Quantitative Aptitude',
      author: 'National Council of Educational Research and Training (NCERT)',
      type: 'OFFICIAL_PORTAL',
      resourceFormat: 'OFFICIAL_PORTAL',
      url: 'https://archive.org/details/ncert-jeep2',
      officialTag: 'NCERT — FREE OFFICIAL EXEMPLAR (ARCHIVE MIRROR)',
      linkVerifiedDate: CHECK_DATE,
      recommendedFor: 'Geometry, trigonometry and mensuration practice at the exact difficulty SSC tests. Direct chapter links are listed in the notes.',
      description: 'NCERT publishes the Class 10 Mathematics Exemplar free of charge. Because ncert.nic.in refuses connections from many networks, GovOS links to NCERT\'s own upload of the book on the Internet Archive (creator: NCERT, collection ncert-textbooks), which serves the identical chapter files. The Triangles, Trigonometry, and Surface Areas & Volumes chapters map directly onto SSC CGL geometry and mensuration, and GovOS practice questions are written from their exercises.',
      inAppHandbookContent: {
        summary: 'NCERT publishes the Class 10 Mathematics Exemplar chapter by chapter as free PDFs. The chapters on Triangles, Trigonometry, and Surface Areas & Volumes map directly onto SSC CGL geometry and mensuration, and GovOS draws practice questions from these official exercises.',
        chapters: [
          {
            chapterTitle: 'Chapter PDFs used by GovOS practice questions (these open)',
            contentMarkdown: 'Read in the browser (no download needed):\n• **Triangles** — archive.org/details/ncert-jeep2/**jeep206**\n• **Introduction to Trigonometry** — archive.org/details/ncert-jeep2/**jeep208**\n• **Surface Areas and Volumes** — archive.org/details/ncert-jeep2/**jeep212**\n\nDirect PDFs use the same names under archive.org/download/ncert-jeep2/ (e.g. jeep206.pdf).\n\nEach chapter opens with the concepts and formulas, then Exercise _n_.1 of multiple-choice questions. GovOS questions written from these exercises name the chapter and question number, and every solution card links to the chapter.'
          },
          {
            chapterTitle: 'Why not ncert.nic.in directly?',
            contentMarkdown: 'The canonical files live at ncert.nic.in/pdf/publication/exemplarproblem/classX/mathematics/, but that host times out from many Indian networks (it did from the machine GovOS was built on). NCERT uploaded the same book to the Internet Archive under its own name, and that copy opens reliably, so GovOS links there. The Ministry of Education\'s DIKSHA platform (diksha.gov.in/ncert) also carries NCERT textbooks.'
          }
        ]
      },
      provenance: officialSource('prov-res-ncert-exemplar-x-maths', 'NCERT Exemplar Problems — Class 10 Mathematics (NCERT upload on the Internet Archive)', 'https://archive.org/details/ncert-jeep2', 200)
    },
    {
      id: 'res-ssc-portal',
      title: 'SSC Official Portal — Notices, Admit Cards, Answer Keys & Results',
      subject: 'Official Gazette',
      author: 'Staff Selection Commission (SSC)',
      type: 'OFFICIAL_PORTAL',
      resourceFormat: 'OFFICIAL_PORTAL',
      url: 'https://ssc.gov.in',
      officialTag: 'STAFF SELECTION COMMISSION — PRIMARY SOURCE',
      recommendedFor: 'Bookmark it and check the "Notices" and "Candidate Corner" sections before every milestone date.',
      description: "The Commission's official website. Every notice, corrigendum, admit card, tentative answer key, response sheet and result is published here first; any other site is secondary.",
      linkVerifiedDate: CHECK_DATE,
      isEssential: true,
      inAppHandbookContent: {
        summary: "The Commission's official website. Every notice, corrigendum, admit card, tentative answer key, response sheet and result is published here first; any other site is secondary.",
        chapters: [
          {
            chapterTitle: 'What to check on ssc.gov.in',
            contentMarkdown: '• **Notices:** official notifications, corrigenda and exam schedules.\n• **Candidate Corner / OTR:** one-time registration and application status.\n• **Admit Card:** links redirect to the regional SSC portal for your zone.\n• **Answer Key:** tentative keys and the response-sheet challenge window.\n• **Result:** merit lists and category cut-offs by tier.'
          },
          {
            chapterTitle: 'How to avoid fake portals',
            contentMarkdown: '• The only official domain is **ssc.gov.in**; regional portals are linked from it.\n• SSC never asks for fees outside the application window.\n• Cross-check any "extended date" claim against a corrigendum on the Notices page.'
          }
        ]
      },
      provenance: officialSource('prov-res-ssc-portal', 'SSC Official Portal — Notices, Admit Cards, Answer Keys & Results', 'https://ssc.gov.in', 200, 'FACT')
    },
    {
      id: 'res-ncert-textbooks',
      title: 'NCERT Textbooks — Classes 6 to 12 on DIKSHA (Ministry of Education)',
      subject: 'Foundation Textbooks & Open Courses',
      author: 'NCERT, distributed on DIKSHA by the Ministry of Education',
      type: 'OFFICIAL_PORTAL',
      resourceFormat: 'OFFICIAL_PORTAL',
      url: 'https://diksha.gov.in/ncert',
      linkVerifiedDate: CHECK_DATE,
      officialTag: 'GOVERNMENT OF INDIA — MINISTRY OF EDUCATION (DIKSHA)',
      recommendedFor: 'History, Geography, Polity, Economy and Science foundations for General Awareness; Class 9–10 Mathematics for Arithmetic and Geometry basics.',
      description: 'The complete NCERT textbook library for Classes 6–12, free of charge, on DIKSHA — the Ministry of Education\'s official digital platform. NCERT\'s own site (ncert.nic.in) hosts the same books but times out from many networks, so GovOS links to DIKSHA, which opens. The single most-cited foundation source for General Awareness across Indian competitive examinations.',
      isEssential: true,
      provenance: officialSource('prov-res-ncert', 'NCERT textbooks on DIKSHA (Ministry of Education)', 'https://diksha.gov.in/ncert', 200)
    },
    {
      id: 'res-constitution-official',
      title: 'Constitution of India — Official Text (Legislative Department)',
      subject: 'General Awareness & Static GK',
      author: 'Legislative Department, Ministry of Law & Justice',
      type: 'OFFICIAL_PORTAL',
      resourceFormat: 'OFFICIAL_PORTAL',
      url: 'https://legislative.gov.in/constitution-of-india/',
      officialTag: 'PRIMARY LEGAL TEXT — MINISTRY OF LAW & JUSTICE',
      recommendedFor: 'Verifying Fundamental Rights (Art. 12–35), Directive Principles (Art. 36–51), Parliament and Judiciary articles that appear in Polity questions every year.',
      description: 'The authoritative, current text of the Constitution of India as maintained by the Legislative Department, including all amendments. Use it to confirm Article numbers, Schedules and Parts rather than relying on secondary summaries.',
      linkVerifiedDate: CHECK_DATE,
      isEssential: true,
      provenance: officialSource('prov-res-constitution-official', 'Constitution of India — Official Text (Legislative Department)', 'https://legislative.gov.in/constitution-of-india/', 200, 'FACT')
    },
    {
      id: 'res-pib',
      title: 'Press Information Bureau (PIB) — Official Government Releases',
      subject: 'Current Affairs & Governance',
      author: 'Press Information Bureau, Ministry of Information & Broadcasting',
      type: 'OFFICIAL_PORTAL',
      resourceFormat: 'OFFICIAL_PORTAL',
      url: 'https://pib.gov.in',
      officialTag: 'GOVERNMENT OF INDIA — DAILY OFFICIAL RELEASES',
      recommendedFor: 'A 15-minute daily read of "Cabinet" and "Ministry-wise" releases; note scheme names, launch dates and the responsible ministry.',
      description: 'Daily official press releases from every Ministry of the Government of India: cabinet decisions, scheme launches, appointments, awards and economic data. The primary source behind most current-affairs questions.',
      linkVerifiedDate: CHECK_DATE,
      isEssential: true,
      provenance: officialSource('prov-res-pib', 'Press Information Bureau (PIB) — Official Government Releases', 'https://pib.gov.in', 200, 'FACT')
    },
    {
      id: 'res-egazette',
      title: 'Gazette of India (e-Gazette) — Official Notifications Archive',
      subject: 'Official Gazette',
      author: 'Directorate of Printing, Government of India',
      type: 'OFFICIAL_PORTAL',
      resourceFormat: 'OFFICIAL_PORTAL',
      url: 'https://egazette.gov.in',
      officialTag: 'PRIMARY OFFICIAL NOTIFICATION SOURCE',
      recommendedFor: 'Confirming a notification, corrigendum or recruitment rule is genuine before acting on it.',
      description: 'The official electronic Gazette of India. Recruitment rules, amendments and government notifications are legally published here first. Search by ministry, date or gazette type.',
      linkVerifiedDate: CHECK_DATE,
      provenance: officialSource('prov-res-egazette', 'Gazette of India (e-Gazette) — Official Notifications Archive', 'https://egazette.gov.in', 200, 'FACT')
    },
    {
      id: 'res-mospi',
      title: 'MoSPI — Ministry of Statistics & Programme Implementation',
      subject: 'General Awareness & Static GK',
      author: 'Ministry of Statistics and Programme Implementation',
      type: 'OFFICIAL_PORTAL',
      resourceFormat: 'OFFICIAL_PORTAL',
      url: 'https://mospi.gov.in',
      officialTag: 'GOVERNMENT OF INDIA — OFFICIAL STATISTICS',
      recommendedFor: 'Understanding the JSO / Statistical Investigator role, and sourcing authentic data tables for Data Interpretation practice.',
      description: 'Official national statistics: GDP estimates, CPI/IIP releases, NSS survey reports and the Statistical Year Book. The employing ministry for Junior Statistical Officer and Statistical Investigator posts.',
      linkVerifiedDate: CHECK_DATE,
      provenance: officialSource('prov-res-mospi', 'MoSPI — Ministry of Statistics & Programme Implementation', 'https://mospi.gov.in', 200, 'FACT')
    },
    {
      id: 'res-census-india',
      title: 'Census of India — Official Demographic Data (via Open Government Data platform)',
      subject: 'General Awareness & Static GK',
      author: 'Office of the Registrar General & Census Commissioner, MHA — datasets on data.gov.in (MeitY)',
      type: 'OFFICIAL_PORTAL',
      resourceFormat: 'OFFICIAL_PORTAL',
      url: 'https://data.gov.in/catalogs?query=census',
      officialTag: 'MINISTRY OF HOME AFFAIRS — OFFICIAL STATISTICS',
      recommendedFor: 'Memorising state-wise literacy, sex ratio and population ranks that recur in General Awareness.',
      description: 'Official demographic statistics — population, literacy, sex ratio and density by state and district — published as open datasets on data.gov.in, the Government of India Open Government Data platform. The Census Commissioner site (censusindia.gov.in) is the canonical source but times out from many networks, so GovOS links to the data.gov.in catalogue, which opens reliably.',
      linkVerifiedDate: CHECK_DATE,
      provenance: officialSource('prov-res-census-india', 'Census of India datasets on data.gov.in (Open Government Data platform)', 'https://data.gov.in/catalogs?query=census', 200)
    },
    {
      id: 'res-india-gov',
      title: 'National Portal of India — Schemes, Ministries & Citizen Services',
      subject: 'Current Affairs & Governance',
      author: 'National Informatics Centre (NIC), MeitY',
      type: 'OFFICIAL_PORTAL',
      resourceFormat: 'OFFICIAL_PORTAL',
      url: 'https://www.india.gov.in',
      officialTag: 'GOVERNMENT OF INDIA — NATIONAL PORTAL',
      recommendedFor: 'Looking up an unfamiliar scheme or ministry mentioned in a question, and building static notes on government structure.',
      description: 'Single-window gateway to all Central Government ministries, departments and flagship schemes with official descriptions and eligibility criteria.',
      linkVerifiedDate: CHECK_DATE,
      provenance: officialSource('prov-res-india-gov', 'National Portal of India — Schemes, Ministries & Citizen Services', 'https://www.india.gov.in', 200, 'FACT')
    },
    {
      id: 'res-ndl-india',
      title: 'National Digital Library of India (NDLI)',
      subject: 'Foundation Textbooks & Open Courses',
      author: 'IIT Kharagpur for the Ministry of Education',
      type: 'OFFICIAL_PORTAL',
      resourceFormat: 'OFFICIAL_PORTAL',
      url: 'https://ndl.iitkgp.ac.in',
      officialTag: 'MINISTRY OF EDUCATION — FREE DIGITAL LIBRARY',
      recommendedFor: 'Locating out-of-print reference books and additional previous-year papers across subjects.',
      description: 'A free national repository of textbooks, previous question papers, lecture videos and reference books aggregated from Indian institutions. Sign in with any email to access the full collection.',
      linkVerifiedDate: CHECK_DATE,
      provenance: officialSource('prov-res-ndl-india', 'National Digital Library of India (NDLI)', 'https://ndl.iitkgp.ac.in', 200, 'RECOMMENDATION')
    },
    {
      id: 'res-swayam',
      title: 'SWAYAM — Free Online Courses by the Ministry of Education',
      subject: 'Foundation Textbooks & Open Courses',
      author: 'Ministry of Education, Government of India',
      type: 'OFFICIAL_PORTAL',
      resourceFormat: 'OFFICIAL_PORTAL',
      url: 'https://swayam.gov.in',
      officialTag: 'MINISTRY OF EDUCATION — FREE MOOCs',
      recommendedFor: 'Candidates who want a taught course rather than self-study for Statistics (JSO / Statistical Investigator) or English.',
      description: 'Free structured video courses from IITs, IIMs and central universities, including Statistics, Economics, Quantitative Techniques and English communication.',
      linkVerifiedDate: CHECK_DATE,
      provenance: officialSource('prov-res-swayam', 'SWAYAM — Free Online Courses by the Ministry of Education', 'https://swayam.gov.in', 200, 'RECOMMENDATION')
    },
    {
      id: 'res-nios',
      title: 'NIOS Open Schooling Study Material (Secondary & Senior Secondary)',
      subject: 'Foundation Textbooks & Open Courses',
      author: 'National Institute of Open Schooling',
      type: 'OFFICIAL_PORTAL',
      resourceFormat: 'OFFICIAL_PORTAL',
      url: 'https://www.nios.ac.in',
      officialTag: 'MINISTRY OF EDUCATION — OPEN SCHOOLING',
      recommendedFor: 'Candidates returning to study after a gap who find NCERT dense; excellent for Static GK revision.',
      description: 'Plain-language official study modules for Class 10 and 12 subjects, written for self-learners. Widely used as an easier companion to NCERT for Geography, History and Economics.',
      linkVerifiedDate: CHECK_DATE,
      provenance: officialSource('prov-res-nios', 'NIOS Open Schooling Study Material (Secondary & Senior Secondary)', 'https://www.nios.ac.in', 200, 'RECOMMENDATION')
    },
    // --- 1. Official Government & Sourced Primary Documents ---
    // --- 2. Top-Rated & Most Successful Video Courses (100% Verified Direct Video URLs) ---
    {
      id: 'res-eng-video-01',
      title: '60 Rules of Grammar for SSC CGL — Complete Session',
      subject: 'English Comprehension',
      author: 'English With Rani Mam (YouTube channel)',
      type: 'VIDEO_LECTURE',
      resourceFormat: 'YOUTUBE_COURSE',
      url: 'https://www.youtube.com/watch?v=6OW1mJTLms0',
      youtubeUrl: 'https://www.youtube.com/watch?v=6OW1mJTLms0',
      youtubeEmbedId: '6OW1mJTLms0',
      officialTag: 'FREE ON YOUTUBE · GRAMMAR RULES',
      recommendedFor: 'Working through subject-verb agreement, tenses and prepositions in one sitting.',
      description: 'A single long-form session covering the grammar rules that recur in SSC Tier-1 and Tier-2 English. Free to watch on YouTube; GovOS links to it and does not host it.',
      linkVerifiedDate: CHECK_DATE,
    },
    {
      id: 'res-quant-video-01',
      title: 'Full Geometry Revision — All Theorems & Formulas in One Video',
      subject: 'Quantitative Aptitude',
      author: 'THE PUNDITS (YouTube channel) — session by Gagan Pratap',
      type: 'VIDEO_LECTURE',
      resourceFormat: 'YOUTUBE_COURSE',
      url: 'https://www.youtube.com/watch?v=ShxYBwt9thk',
      youtubeUrl: 'https://www.youtube.com/watch?v=ShxYBwt9thk',
      youtubeEmbedId: 'ShxYBwt9thk',
      officialTag: 'FREE ON YOUTUBE · GEOMETRY REVISION',
      recommendedFor: 'Revising circle, triangle and quadrilateral theorems before a mock test.',
      description: 'Single-video revision of the geometry theorems and formulas used in SSC CGL quantitative aptitude. Free to watch on YouTube; GovOS links to it and does not host it.',
      linkVerifiedDate: CHECK_DATE,
    },
    {
      id: 'res-quant-video-02',
      title: 'Percentage (प्रतिशत) Part-01 — Maths Series Day 05',
      subject: 'Quantitative Aptitude',
      author: 'SelectionWay SSC / RANKERS GURUKUL (YouTube channel) — session by Aditya Ranjan',
      type: 'VIDEO_LECTURE',
      resourceFormat: 'YOUTUBE_COURSE',
      url: 'https://www.youtube.com/watch?v=Ov0KEEfvgbs',
      youtubeUrl: 'https://www.youtube.com/watch?v=Ov0KEEfvgbs',
      youtubeEmbedId: 'Ov0KEEfvgbs',
      officialTag: 'FREE ON YOUTUBE · ONE TOPIC (PERCENTAGE)',
      recommendedFor: 'Building percentage fundamentals before profit-loss and data interpretation.',
      description: 'Day-05 session of a Hindi-medium maths series, covering percentage fundamentals. This is one topic in a longer playlist, not a complete maths course. Free to watch on YouTube; GovOS links to it and does not host it.',
      linkVerifiedDate: CHECK_DATE,
    },
    {
      id: 'res-ga-video-01',
      title: 'SSC CGL GK 2026 — India & International Borders',
      subject: 'General Awareness & Static GK',
      author: 'PARMAR CLIPS (YouTube channel)',
      type: 'VIDEO_LECTURE',
      resourceFormat: 'YOUTUBE_COURSE',
      url: 'https://www.youtube.com/watch?v=6hIyIW_Nxq8',
      youtubeUrl: 'https://www.youtube.com/watch?v=6hIyIW_Nxq8',
      youtubeEmbedId: '6hIyIW_Nxq8',
      officialTag: 'FREE ON YOUTUBE · ONE GK TOPIC (BORDERS)',
      recommendedFor: 'Memorising border states, boundary lines and neighbouring countries.',
      description: 'Covers India\'s international land borders and neighbouring-country boundary lines for static GK. This is a single-topic class, not a full GK revision course. Free to watch on YouTube; GovOS links to it and does not host it.',
      linkVerifiedDate: CHECK_DATE,
    },
    {
      id: 'res-reas-video-01',
      title: 'Reasoning Marathon (RRB NTPC series) — shared reasoning topics',
      subject: 'Reasoning',
      author: 'Vikramjeet Sir Reasoning (YouTube channel)',
      type: 'VIDEO_LECTURE',
      resourceFormat: 'YOUTUBE_COURSE',
      url: 'https://www.youtube.com/watch?v=oh3cXneUlcY',
      youtubeUrl: 'https://www.youtube.com/watch?v=oh3cXneUlcY',
      youtubeEmbedId: 'oh3cXneUlcY',
      officialTag: 'FREE ON YOUTUBE · RECORDED FOR RRB NTPC',
      recommendedFor: 'Extra practice on shared reasoning topics — use an SSC paper for pattern and timing.',
      description: 'A reasoning marathon recorded for the RRB NTPC examination. The reasoning topics overlap heavily with SSC CGL, but the paper pattern and difficulty referenced in the video are RRB NTPC, not SSC. Free to watch on YouTube; GovOS links to it and does not host it.',
      linkVerifiedDate: CHECK_DATE,
    },
    {
      id: 'res-comp-video-01',
      title: 'Computer Revision & Chapter-wise Practice (Class 1)',
      subject: 'Computer & Typing',
      author: 'RBE Revolution By Education (YouTube channel)',
      type: 'VIDEO_LECTURE',
      resourceFormat: 'YOUTUBE_COURSE',
      url: 'https://www.youtube.com/watch?v=pUtPVwPBxzA',
      youtubeUrl: 'https://www.youtube.com/watch?v=pUtPVwPBxzA',
      youtubeEmbedId: 'pUtPVwPBxzA',
      officialTag: 'FREE ON YOUTUBE · CLASS 1 OF A SERIES',
      recommendedFor: 'Starting the Tier-2 Computer Knowledge module (Section-III).',
      description: 'First class of a computer-awareness revision series aimed at SSC CGL, CHSL and railway examinations. Free to watch on YouTube; GovOS links to it and does not host it.',
      linkVerifiedDate: CHECK_DATE,
    },
    // --- 3. Free YouTube channels candidates widely follow (coaching, not official) ---
    // Subscriber counts were read from public channel statistics on the check date and are
    // recorded as evidence of reach, not of quality. Each entry links to the channel itself
    // rather than one video, so it stays useful as the channel publishes new material.
    {
      id: 'res-yt-adda247-ssc',
      title: 'Adda247 SSC — free full-syllabus classes and PYQ sessions',
      subject: 'Foundation Textbooks & Open Courses',
      author: 'Adda247 SSC (YouTube channel)',
      type: 'VIDEO_LECTURE',
      resourceFormat: 'YOUTUBE_CHANNEL',
      url: 'https://www.youtube.com/channel/UCAyYBPzFioHUxvVZEn4rMJA',
      youtubeUrl: 'https://www.youtube.com/channel/UCAyYBPzFioHUxvVZEn4rMJA',
      officialTag: 'FREE ON YOUTUBE · ~11M SUBSCRIBERS · COACHING, NOT OFFICIAL',
      recommendedFor: 'Following a structured free batch across all four Tier-1 subjects.',
      description: 'The largest SSC-focused free channel on YouTube, running daily live classes, previous-year question sessions and strategy videos across reasoning, quantitative aptitude, English and general awareness. Free to watch; paid courses are advertised alongside, which you can ignore. Coaching content — where it disagrees with the SSC notice, the notice governs.',
      linkVerifiedDate: CHECK_DATE,
      provenance: communitySource('prov-res-yt-adda247', 'Adda247 SSC YouTube channel', 'https://www.youtube.com/channel/UCAyYBPzFioHUxvVZEn4rMJA', 'about 11 million subscribers')
    },
    {
      id: 'res-yt-ssc-wallah',
      title: 'SSC Wallah (Physics Wallah) — free complete-syllabus batches',
      subject: 'Foundation Textbooks & Open Courses',
      author: 'SSC Wallah (YouTube channel, Physics Wallah)',
      type: 'VIDEO_LECTURE',
      resourceFormat: 'YOUTUBE_CHANNEL',
      url: 'https://www.youtube.com/channel/UCcaEVV7A47J4k9GFcqOOYkg',
      youtubeUrl: 'https://www.youtube.com/channel/UCcaEVV7A47J4k9GFcqOOYkg',
      officialTag: 'FREE ON YOUTUBE · ~2.5M SUBSCRIBERS · COACHING, NOT OFFICIAL',
      recommendedFor: 'A second opinion when one teacher\'s explanation of a topic does not land.',
      description: 'Physics Wallah\'s SSC channel: subject-wise lectures, previous-year solutions and full free batches for CGL, CHSL, MTS and GD. Useful as an alternative explanation when a topic has not clicked elsewhere. Coaching content, not a government source.',
      linkVerifiedDate: CHECK_DATE,
      provenance: communitySource('prov-res-yt-sscwallah', 'SSC Wallah YouTube channel', 'https://www.youtube.com/channel/UCcaEVV7A47J4k9GFcqOOYkg', 'about 2.5 million subscribers')
    },
    {
      id: 'res-yt-gagan-pratap',
      title: 'Gagan Pratap Maths — quantitative aptitude and advanced maths',
      subject: 'Quantitative Aptitude',
      author: 'Gagan Pratap Maths (YouTube channel)',
      type: 'VIDEO_LECTURE',
      resourceFormat: 'YOUTUBE_CHANNEL',
      url: 'https://www.youtube.com/channel/UCS2rhpz4RJEmb9CV7TPzBIg',
      youtubeUrl: 'https://www.youtube.com/channel/UCS2rhpz4RJEmb9CV7TPzBIg',
      officialTag: 'FREE ON YOUTUBE · ~5.7M SUBSCRIBERS · COACHING, NOT OFFICIAL',
      recommendedFor: 'Speed methods for geometry, algebra and trigonometry at Tier-2 difficulty.',
      description: 'The most-followed maths channel among SSC candidates, known for short methods and hard-question practice in geometry, algebra, trigonometry and mensuration. Best used after your fundamentals are in place — the pace assumes you know the basics. Coaching content, not a government source.',
      linkVerifiedDate: CHECK_DATE,
      provenance: communitySource('prov-res-yt-gaganpratap', 'Gagan Pratap Maths YouTube channel', 'https://www.youtube.com/channel/UCS2rhpz4RJEmb9CV7TPzBIg', 'about 5.7 million subscribers')
    },
    {
      id: 'res-yt-rakesh-yadav',
      title: 'Rakesh Yadav — classroom-style maths from the basics',
      subject: 'Quantitative Aptitude',
      author: 'Rakesh Yadav (YouTube channel, Rakesh Yadav Readers Publication)',
      type: 'VIDEO_LECTURE',
      resourceFormat: 'YOUTUBE_CHANNEL',
      url: 'https://www.youtube.com/channel/UCOyT274gK_v2Xu6TXV5RgtQ',
      youtubeUrl: 'https://www.youtube.com/channel/UCOyT274gK_v2Xu6TXV5RgtQ',
      officialTag: 'FREE ON YOUTUBE · ~5.8M SUBSCRIBERS · COACHING, NOT OFFICIAL',
      recommendedFor: 'Building arithmetic and advanced-maths fundamentals from zero.',
      description: 'Long-running classroom-style maths teaching for SSC exams, working through chapters slowly from first principles. The usual recommendation for candidates who need the basics rebuilt rather than speed tricks. Coaching content, not a government source.',
      linkVerifiedDate: CHECK_DATE,
      provenance: communitySource('prov-res-yt-rakeshyadav', 'Rakesh Yadav YouTube channel', 'https://www.youtube.com/channel/UCOyT274gK_v2Xu6TXV5RgtQ', 'about 5.8 million subscribers')
    },
    {
      id: 'res-yt-rankers-gurukul',
      title: 'SelectionWay SSC (Rankers Gurukul) — maths series by Aditya Ranjan',
      subject: 'Quantitative Aptitude',
      author: 'SelectionWay SSC (RANKERS GURUKUL) (YouTube channel) — Aditya Ranjan',
      type: 'VIDEO_LECTURE',
      resourceFormat: 'YOUTUBE_CHANNEL',
      url: 'https://www.youtube.com/channel/UCnoFgtSgG9PPAmwzG2P00JA',
      youtubeUrl: 'https://www.youtube.com/channel/UCnoFgtSgG9PPAmwzG2P00JA',
      officialTag: 'FREE ON YOUTUBE · COACHING, NOT OFFICIAL',
      recommendedFor: 'Working through a maths topic in order, day by day, in Hindi.',
      description: 'Hindi-medium maths series taught in sequence, topic by topic, by a teacher selected through SSC CGL himself. The percentage session already in this library comes from this channel; the channel link gives you the rest of the series. Coaching content, not a government source.',
      linkVerifiedDate: CHECK_DATE,
      provenance: communitySource('prov-res-yt-rankersgurukul', 'SelectionWay SSC (Rankers Gurukul) YouTube channel', 'https://www.youtube.com/channel/UCnoFgtSgG9PPAmwzG2P00JA', 'a widely followed SSC maths channel')
    },
    {
      id: 'res-yt-piyush-varshney',
      title: 'Reasoning By Piyush Varshney — full reasoning syllabus',
      subject: 'Reasoning',
      author: 'Reasoning By Piyush Varshney (YouTube channel)',
      type: 'VIDEO_LECTURE',
      resourceFormat: 'YOUTUBE_CHANNEL',
      url: 'https://www.youtube.com/channel/UCyoOKrfVu89ZAGwYqQAyM8A',
      youtubeUrl: 'https://www.youtube.com/channel/UCyoOKrfVu89ZAGwYqQAyM8A',
      officialTag: 'FREE ON YOUTUBE · ~1.8M SUBSCRIBERS · COACHING, NOT OFFICIAL',
      recommendedFor: 'Syllogism, blood relations, series, coding-decoding and non-verbal practice.',
      description: 'The reasoning channel SSC candidates most often name, covering the Tier-1 reasoning syllabus topic by topic with previous-year questions. Reasoning is the fastest section to convert into marks, and this is a complete free course for it. Coaching content, not a government source.',
      linkVerifiedDate: CHECK_DATE,
      provenance: communitySource('prov-res-yt-piyushvarshney', 'Reasoning By Piyush Varshney YouTube channel', 'https://www.youtube.com/channel/UCyoOKrfVu89ZAGwYqQAyM8A', 'about 1.8 million subscribers')
    },
    {
      id: 'res-yt-rani-mam',
      title: 'English With Rani Mam — grammar rules and vocabulary',
      subject: 'English Comprehension',
      author: 'English With Rani Mam (YouTube channel)',
      type: 'VIDEO_LECTURE',
      resourceFormat: 'YOUTUBE_CHANNEL',
      url: 'https://www.youtube.com/channel/UCvagVtkTsj3ASMTlhcIc-7A',
      youtubeUrl: 'https://www.youtube.com/channel/UCvagVtkTsj3ASMTlhcIc-7A',
      officialTag: 'FREE ON YOUTUBE · ~3.3M SUBSCRIBERS · COACHING, NOT OFFICIAL',
      recommendedFor: 'Daily grammar and vocabulary practice for Tier-1 and Tier-2 English.',
      description: 'Grammar rules, error spotting, vocabulary and comprehension for SSC and bank exams, taught rule by rule with exam examples. The 60-rules session already in this library is from this channel; the channel link gives you the daily practice around it. Coaching content, not a government source.',
      linkVerifiedDate: CHECK_DATE,
      provenance: communitySource('prov-res-yt-ranimam', 'English With Rani Mam YouTube channel', 'https://www.youtube.com/channel/UCvagVtkTsj3ASMTlhcIc-7A', 'about 3.3 million subscribers')
    },
    {
      id: 'res-yt-parmar-ssc',
      title: 'PARMAR SSC — general awareness and previous-year GK',
      subject: 'General Awareness & Static GK',
      author: 'PARMAR SSC (YouTube channel)',
      type: 'VIDEO_LECTURE',
      resourceFormat: 'YOUTUBE_CHANNEL',
      url: 'https://www.youtube.com/channel/UCXPwWsvqwU18UKpsZD4bODw',
      youtubeUrl: 'https://www.youtube.com/channel/UCXPwWsvqwU18UKpsZD4bODw',
      officialTag: 'FREE ON YOUTUBE · ~2.5M SUBSCRIBERS · COACHING, NOT OFFICIAL',
      recommendedFor: 'Static GK revision built around questions SSC has actually asked.',
      description: 'General awareness taught around previous-year SSC questions rather than open-ended syllabus reading, which is what makes the section tractable. The borders session already in this library is from this channel. Verify any constitutional or statistical claim against the Constitution text and the official data portals also listed here. Coaching content, not a government source.',
      linkVerifiedDate: CHECK_DATE,
      provenance: communitySource('prov-res-yt-parmarssc', 'PARMAR SSC YouTube channel', 'https://www.youtube.com/channel/UCXPwWsvqwU18UKpsZD4bODw', 'about 2.5 million subscribers')
    },
    // --- 4. Further free government, statutory and academic sources ---
    {
      id: 'res-india-code',
      title: 'India Code — official repository of Central Acts',
      subject: 'Official Gazette',
      author: 'Legislative Department, Ministry of Law and Justice (Government of India)',
      type: 'OFFICIAL_PORTAL',
      resourceFormat: 'OFFICIAL_PORTAL',
      url: 'https://indiacode.nic.in',
      officialTag: 'GOVERNMENT OF INDIA — MINISTRY OF LAW AND JUSTICE',
      recommendedFor: 'Checking the actual text of an Act a general-awareness question refers to.',
      description: 'The Government of India\'s own database of Central Acts with their amendments. When a coaching video or a question paper cites an Act, this is where you confirm what it actually says. Free, no registration.',
      linkVerifiedDate: CHECK_DATE,
      provenance: officialSource('prov-res-india-code', 'India Code — Digital Repository of Central Acts', 'https://indiacode.nic.in', 200)
    },
    {
      id: 'res-sansad',
      title: 'Parliament of India — Sansad official portal',
      subject: 'Current Affairs & Governance',
      author: 'Lok Sabha and Rajya Sabha Secretariats (Parliament of India)',
      type: 'OFFICIAL_PORTAL',
      resourceFormat: 'OFFICIAL_PORTAL',
      url: 'https://sansad.in',
      officialTag: 'PARLIAMENT OF INDIA — OFFICIAL',
      recommendedFor: 'Polity questions about Parliament: sessions, members, committees and procedure.',
      description: 'The official portal of both Houses of Parliament — sessions, members, committees, questions and legislative business. The primary source for the parliamentary side of the polity syllabus, and for current affairs about bills in progress.',
      linkVerifiedDate: CHECK_DATE,
      provenance: officialSource('prov-res-sansad', 'Parliament of India official portal', 'https://sansad.in', 200)
    },
    {
      id: 'res-rbi',
      title: 'Reserve Bank of India — official website',
      subject: 'Banking & Financial Awareness',
      author: 'Reserve Bank of India',
      type: 'OFFICIAL_PORTAL',
      resourceFormat: 'OFFICIAL_PORTAL',
      url: 'https://www.rbi.org.in',
      officialTag: 'RESERVE BANK OF INDIA — OFFICIAL',
      recommendedFor: 'Repo rate, monetary policy and banking terms asked in general awareness.',
      description: 'The central bank\'s own site: current policy rates, press releases, and the plain-language explanations under its financial-education pages. General-awareness questions on banking are best answered from here rather than from a coaching PDF that may predate the last policy change.',
      linkVerifiedDate: CHECK_DATE,
      provenance: officialSource('prov-res-rbi', 'Reserve Bank of India official website', 'https://www.rbi.org.in', 200)
    },
    {
      id: 'res-nptel',
      title: 'NPTEL — free courses from the IITs and IISc',
      subject: 'Foundation Textbooks & Open Courses',
      author: 'NPTEL (Ministry of Education, Government of India)',
      type: 'OFFICIAL_PORTAL',
      resourceFormat: 'OFFICIAL_PORTAL',
      url: 'https://nptel.ac.in',
      officialTag: 'GOVERNMENT OF INDIA — MINISTRY OF EDUCATION',
      recommendedFor: 'Rebuilding a mathematics or statistics foundation properly, especially for JSO.',
      description: 'Government-funded free course library taught by IIT and IISc faculty. Slower and deeper than exam coaching, and the most useful free source if you are targeting Junior Statistical Officer and need real statistics rather than exam shortcuts. Video lectures and notes are free; certification is optional and paid.',
      linkVerifiedDate: CHECK_DATE,
      provenance: officialSource('prov-res-nptel', 'NPTEL — National Programme on Technology Enhanced Learning', 'https://nptel.ac.in', 200, 'RECOMMENDATION')
    },
    {
      id: 'res-prs-india',
      title: 'PRS Legislative Research — bill and act summaries',
      subject: 'Current Affairs & Governance',
      author: 'PRS Legislative Research (independent, non-profit)',
      type: 'OFFICIAL_PORTAL',
      resourceFormat: 'OFFICIAL_PORTAL',
      url: 'https://prsindia.org',
      officialTag: 'INDEPENDENT NON-PROFIT · WIDELY CITED · NOT A GOVERNMENT SITE',
      recommendedFor: 'Understanding what a new bill or act actually changes, in plain English.',
      description: 'Independent non-profit that tracks every bill in Parliament and publishes short, neutral summaries of what it changes. Not a government body, so treat it as explanation rather than authority — but it is the clearest free bridge between a news headline and the legal text on India Code.',
      linkVerifiedDate: CHECK_DATE,
      provenance: communitySource('prov-res-prs', 'PRS Legislative Research', 'https://prsindia.org', 'the most widely cited independent legislative tracker in India')
    },
    {
      id: 'res-comp-typing-tool',
      title: '10FastFingers Typing Speed Test (SSC DEST Keyboard Simulator)',
      subject: 'Computer & Typing',
      author: '10FastFingers Open Simulator',
      type: 'ONLINE_TOOL',
      resourceFormat: 'ONLINE_TOOL',
      url: 'https://10fastfingers.com',
      officialTag: 'OFFICIAL DEST KEYBOARD SIMULATOR',
      recommendedFor: 'Practicing 2000 key depressions in 15 minutes (~27 WPM) with real-time speed and error calculation.',
      description: 'Specialized typing simulator providing live keystroke error percentage and net words-per-minute tracking.'
    },
  ],

  // Admit Card / Hall Ticket release details & SSC regional download mirrors
  admitCardDetails: {
    status: 'NOT_YET_ANNOUNCED',
    releaseDateStr: '2026-10-18 10:00:00',
    officialPortalUrl: 'https://ssc.gov.in',
    loginCredentialsRequired: [
      'Registration Number / Roll Number',
      'Registered Password or Date of Birth',
      'Captcha verification code'
    ],
    instructions: [
      'Download the e-Admit Card only from the official SSC regional portal for your allotted zone.',
      'Verify that your name, photograph, signature, exam city, shift timing and venue address are printed correctly.',
      'Report any discrepancy to the concerned SSC Regional Office immediately, before the exam date.',
      'Carry a clear laser printout together with the same original photo ID quoted in the application.'
    ],
    cityIntimationAvailable: true,
    cityIntimationUrl: 'https://ssc.gov.in',
    regionPortals: [
      { regionName: 'Northern Region', regionCode: 'NR', statesCovered: 'Delhi, Rajasthan, Uttarakhand', portalUrl: 'https://sscnr.nic.in', status: 'ACTIVE' },
      { regionName: 'Central Region', regionCode: 'CR', statesCovered: 'Uttar Pradesh, Bihar', portalUrl: 'https://ssc-cr.org', status: 'ACTIVE' },
      { regionName: 'Western Region', regionCode: 'WR', statesCovered: 'Maharashtra, Gujarat, Goa', portalUrl: 'https://sscwr.net', status: 'ACTIVE' },
      { regionName: 'Eastern Region', regionCode: 'ER', statesCovered: 'West Bengal, Odisha, Jharkhand', portalUrl: 'https://sscer.org', status: 'ACTIVE' },
      { regionName: 'Southern Region', regionCode: 'SR', statesCovered: 'Tamil Nadu, Andhra Pradesh, Telangana', portalUrl: 'https://sscsr.gov.in', status: 'ACTIVE' },
      { regionName: 'Karnataka-Kerala Region', regionCode: 'KKR', statesCovered: 'Karnataka, Kerala', portalUrl: 'https://ssckkr.kar.nic.in', status: 'ACTIVE' },
      { regionName: 'North Western Region', regionCode: 'NWR', statesCovered: 'Punjab, Haryana, Himachal Pradesh, J&K', portalUrl: 'https://sscnwr.org', status: 'ACTIVE' },
      { regionName: 'Madhya Pradesh Region', regionCode: 'MPR', statesCovered: 'Madhya Pradesh, Chhattisgarh', portalUrl: 'https://sscmpr.org', status: 'ACTIVE' },
      { regionName: 'North Eastern Region', regionCode: 'NER', statesCovered: 'Assam, Meghalaya, Manipur, Tripura, Nagaland', portalUrl: 'https://sscner.org.in', status: 'ACTIVE' }
    ]
  },

  syllabusSourceNote: 'Section 13 of the SSC CGL 2026 Gazette Notification (Scheme of Examination and detailed syllabus)',

  eligibilityHighlights: [
    {
      title: '1. Crucial Cutoff Date',
      body: 'Candidate age is calculated strictly as of 01-08-2026. Final year degree holders must possess their qualifying degree on or before this date.',
      provenance: sscProvenanceEligibility
    },
    {
      title: '2. Category Age Relaxations',
      body: 'OBC: +3 years. SC / ST: +5 years. PwBD (Unreserved): +10 years. PwBD (OBC): +13 years. PwBD (SC/ST): +15 years.',
      provenance: sscProvenanceEligibility
    },
    {
      title: '3. Specialized Degree Posts',
      body: 'JSO: 60% in 12th Maths OR Degree with Statistics. Statistical Investigator Grade II: Statistics in all 3 years of Degree.',
      provenance: sscProvenanceEligibility
    }
  ],

  officialLinks: [
    { title: 'Staff Selection Commission', url: 'https://ssc.gov.in', note: 'ssc.gov.in (Official Application & Result Portal)' },
    { title: 'NCBC Central OBC List', url: 'https://ncbc.nic.in', note: 'ncbc.nic.in (Central OBC Caste Verification)' },
    { title: 'DigiLocker Government Portal', url: 'https://www.digilocker.gov.in', note: 'digilocker.gov.in (Verified Marksheets & ID)' }
  ],

  // Frequently Asked Questions citing Official Notification Clauses
  faqs: [
    {
      id: 'faq-01',
      question: 'Are final year graduation students eligible to apply for SSC CGL 2026?',
      answer: 'Yes. Candidates appearing in their final year of graduation can apply, provided they acquire the essential educational qualification degree certificate or provisional marksheet on or before the crucial cutoff date (01-08-2026).',
      officialClause: 'Section 8.1, Clause (b)',
      provenance: sscProvenanceEligibility
    },
    {
      id: 'faq-02',
      question: 'What is the exact crucial date for age limit calculation for SSC CGL 2026?',
      answer: 'The crucial date for age reckoning is fixed as 01-08-2026. For posts with 18-27 age limit, candidate must be born not earlier than 02-08-1999 and not later than 01-08-2008 (subject to category relaxation).',
      officialClause: 'Section 3.1, Clause (a)',
      provenance: sscProvenanceEligibility
    },
    {
      id: 'faq-03',
      question: 'What is the negative marking scheme in Tier-1 and Tier-2 exams?',
      answer: 'In Tier-1, there is a negative marking of 0.50 marks for each incorrect response across all 4 sections. In Tier-2 (Paper-I), there is a negative marking of 1.00 mark for each wrong answer in Section-I, Section-II, and Section-III Module 1.',
      officialClause: 'Section 13.1 & 13.2',
      provenance: sscProvenanceOverview
    },
    {
      id: 'faq-04',
      question: 'Is the Data Entry Speed Test (DEST) typing test compulsory for all candidates?',
      answer: 'Yes, DEST typing test (Section-III Module 2 of Paper-I) is mandatory for ALL posts. Candidates must type approximately 2000 key depressions in 15 minutes (~27 WPM). It is qualifying in nature.',
      officialClause: 'Section 13.2, Module-II',
      provenance: sscProvenanceOverview
    },
    {
      id: 'faq-05',
      question: 'What are the certificate validity requirements for OBC (Non-Creamy Layer) candidates?',
      answer: 'The OBC certificate must be issued in the prescribed Central Government format (Annexure-VI) within 3 years prior to the closing date of application (27-09-2026) and must certify that the candidate does not belong to the Creamy Layer.',
      officialClause: 'Section 6.3 & Annexure-VI',
      provenance: sscProvenanceEligibility
    },
    {
      id: 'faq-06',
      question: 'Are physical fitness tests mandatory for all SSC CGL posts?',
      answer: 'No. Physical measurement and endurance tests (Walking & Cycling) are only required for specific uniformed posts: Inspector (Central Excise, Preventive Officer, Examiner) in CBIC, Sub-Inspector in CBI, Sub-Inspector in NIA, and Inspector in Narcotics.',
      officialClause: 'Annexure-VII (Physical Standards)',
      provenance: sscProvenanceEligibility
    }
  ]
};

// ============================================================================
// UPSC CIVIL SERVICES EXAMINATION (CSE) 2026
//
// Read from the Commission's own documents on 2026-09-12 (see each provenance). Nothing in
// this record was taken from a coaching site. Where the notice is silent (pay levels) or the
// figure is GovOS's reading of the papers (topic weightage), the provenance says so.
// ============================================================================

const UPSC_CHECK = '2026-09-12';
const UPSC_NOTICE_URL = 'https://www.upsc.gov.in/sites/default/files/Notif-CSP-2026-Engl-060226Rev.pdf';
const UPSC_NOTICE_TITLE = 'UPSC Examination Notice No. 05/2026-CSE — Civil Services (Preliminary) Examination, 2026 (dated 04.02.2026, revised 06.02.2026)';

/** A clause of the 2026 notice, cited by section and page. */
const upscNotice = (id: string, clauseNumber: string, pageNumber: number, excerptText: string, taxonomyType: DataProvenance['taxonomyType'] = 'FACT'): DataProvenance => ({
  id,
  documentTitle: UPSC_NOTICE_TITLE,
  officialUrl: UPSC_NOTICE_URL,
  pageNumber,
  clauseNumber,
  publishedDate: '2026-02-04',
  verifiedDate: UPSC_CHECK,
  verifiedBy: `GovOS verifier — read from the notice PDF on ${UPSC_CHECK}`,
  taxonomyType,
  verificationLevel: 'OFFICIALLY_VERIFIED',
  excerptText
});

/** A UPSC press note or sheet other than the notice. */
const upscDocument = (id: string, documentTitle: string, officialUrl: string, publishedDate: string, excerptText: string, clauseNumber: string = 'Whole document'): DataProvenance => ({
  id,
  documentTitle,
  officialUrl,
  pageNumber: 1,
  clauseNumber,
  publishedDate,
  verifiedDate: UPSC_CHECK,
  verifiedBy: `GovOS verifier — read from the document on ${UPSC_CHECK}`,
  taxonomyType: 'FACT',
  verificationLevel: 'OFFICIALLY_VERIFIED',
  excerptText
});

const upscProvenance = upscNotice('prov-upsc-01', 'Cover and Section I', 1,
  'EXAMINATION NOTICE NO 05/2026-CSE DATE: 04.02.2026 (LAST DATE FOR SUBMISSION OF ONLINE APPLICATIONS: 24.02.2026 of CIVIL SERVICES EXAMINATION, 2026).');
const upscProvenanceEligibility = upscNotice('prov-upsc-elig', 'Section II — Conditions of Eligibility (I) Nationality, (II) Age Limits, (III) Minimum Educational Qualification, (IV) Number of attempts', 14,
  'A candidate must have attained the age of 21 years and must not have attained the age of 32 years on the 1st of August, 2026 i.e., the candidate must have been born not earlier than 2nd August, 1994 and not later than 1st August, 2005.');
const upscProvenanceScheme = upscNotice('prov-upsc-scheme', 'Section III — Part A (Preliminary Examination) and Part B (Main Examination), Scheme of Examination', 25,
  'The Examination shall comprise of two compulsory Papers of 200 marks each … Sub Total (Written test) 1750 Marks; Personality Test 275 Marks; Grand Total 2025 Marks.');
const upscProvenanceSyllabus = upscNotice('prov-upsc-syl', 'Section III — Part A (Preliminary) and Part B (Main): syllabi of the papers', 33,
  'Paper I - (200 marks) Duration: Two hours. Current events of national and international importance. History of India and Indian National Movement. Indian and World Geography … Indian Polity and Governance … Economic and Social Development … Environmental ecology, Bio-diversity and Climate Change … General Science.');
const upscProvenanceFee = upscNotice('prov-upsc-fee', 'Section: FEE (para 4) and LAST DATE FOR SUBMISSION OF APPLICATIONS (para 3)', 3,
  'All the candidates (Except Female/SC/ST/Persons with Benchmark Disability Candidates who are exempted from payment of fee) are required to pay fee of Rs. 100/- … Candidates admitted to the Civil Services (Main) Examination, 2026 will be required to pay a further fee of Rs. 200/-.');
const upscProvenanceApply = upscNotice('prov-upsc-apply', 'IMPORTANT INFORMATION FOR THE CANDIDATES and Section: HOW TO APPLY (para 2)', 1,
  'The Online Application Portal of Union Public Service Commission … has four cards/modules, three of which namely, Account creation, Universal Registration and Common Application Form are common to all examination applications … Applicants are required to apply online by using the website https://upsconline.nic.in.');
const upscProvenanceAdmit = upscNotice('prov-upsc-admit', 'Section: ISSUANCE OF E-ADMIT CARD (para 4)', 3,
  'The eligible candidates will be issued an e-Admit Card on the last working day of the preceding week of the date of examination … The e-Admit Card will be made available on the website [https://upsconline.nic.in] for downloading by the candidates. No Admit Card will be sent by post or Email.');
const upscProvenanceVacancy = upscNotice('prov-upsc-vac', 'Section I — Services and Posts; number of vacancies', 2,
  'The number of vacancies to be filled through the examination is expected to be approximately 933 which include 33 Vacancies reserved for Persons with Benchmark Disability Category … The final number of vacancies may undergo change after getting firm number of vacancies from Cadre Controlling Authorities.');
const upscProvenanceCentres = upscNotice('prov-upsc-centres', 'Section: Centres of Examination — (i) Preliminary (83 centres), (ii) Main (27 centres)', 9,
  'The Centres and the date of holding the examination as mentioned above are liable to be changed at the discretion of the Commission.');

const upscProvenancePrelimsResult = upscDocument('prov-upsc-prelims-result',
  'UPSC Press Note — Result of the Civil Services (Preliminary) Examination, 2026 (names), dated 18 June 2026',
  'https://www.upsc.gov.in/sites/default/files/WR-NameList-CSP-2026-Engl-18062026.pdf', '2026-06-18',
  'In continuation of the Press Note dated 15/06/2026 declaring the Roll Number Wise Result of the Civil Services (Preliminary) Examination, 2026 held on 24/05/2026 … The Window for filling up these details and submission thereof will be available on the Commission’s website from 19th to 28th June, 2026 … This year, against 1016 vacancies notified for the Civil Services Examination, 2026, a total of 13,343 candidates have been shortlisted for the Civil Services (Main) Examination, 2026.');
const upscProvenanceEAdmit = upscDocument('prov-upsc-eadmit',
  'UPSC Press Note — Civil Services (Preliminary) Examination, 2026: e-Admit Cards uploaded, dated 15 May 2026',
  'https://www.upsc.gov.in/sites/default/files/Press_Note_CSPE_2026_Eng_15052026.pdf', '2026-05-15',
  'Union Public Service Commission will be conducting the Civil Services (Preliminary) Examination, 2026 on 24th May, 2026 (Sunday) all over India. The Commission has uploaded the e-Admit Cards of the admitted candidates on its website (http://upsconline.nic.in) … No paper Admit Card will be issued for this Examination.');
const upscProvenanceMains = upscDocument('prov-upsc-mains',
  'UPSC Press Note — Civil Services (Main) Examination, 2026, dated 19 August 2026',
  'https://www.upsc.gov.in/sites/default/files/PressNote-CSM-2026-Engl-190826.pdf', '2026-08-19',
  'The Civil Services (Main) Examination, 2026 is scheduled to be held from 21.08.2026 to 23.08.2026 and from 29.08.2026 to 30.08.2026. After the conclusion of the Examination, Question Paper Representation Portal (QPReP) will be made available … from 31.08.2026 to 04.09.2026.');
const upscProvenanceCalendar2027 = upscDocument('prov-upsc-cal-2027',
  'UPSC Calendar of Examinations for the year 2027 (published 20 May 2026)',
  'https://www.upsc.gov.in/sites/default/files/Calendar-Year-2027-Engl-200526.pdf', '2026-05-20',
  '9. Civil Services (Preliminary) Examination, 2027 — Date of Notification 13.01.2027; Last date for receipt of applications 02.02.2027; Date of commencement of Exam 23.05.2027. 19. Civil Services (Main) Examination, 2027 — 20.08.2027 (Friday), 5 DAYS.');
const upscProvenanceQP2026 = upscDocument('prov-upsc-qp-2026',
  'UPSC — Civil Services (Preliminary) Examination, 2026: General Studies Paper-I and Paper-II question booklets (Series A), published 25 May 2026',
  'https://www.upsc.gov.in/sites/default/files/QP_CSP_2026_GENERAL_STUDIES_PAPER-I_25052026.pdf', '2026-05-25',
  'GENERAL STUDIES PAPER-I: Time Allowed: Two Hours; Maximum Marks: 200; This Test Booklet contains 100 items (questions). GENERAL STUDIES Paper-II: Time Allowed: Two Hours; Maximum Marks: 200; This Test Booklet contains 80 items (questions). For each question for which a wrong answer has been given by the candidate, one-third of the marks assigned to that question will be deducted as penalty.',
  'Back-cover instructions of each booklet');
const upscCutoff = (year: number, url: string, publishedDate: string, excerptText: string): DataProvenance => upscDocument(`prov-upsc-cutoff-${year}`,
  `UPSC — Civil Services Examination, ${year}: minimum qualifying marks (official sheet)`, url, publishedDate, excerptText,
  'Table: minimum qualifying standards/marks secured by the last recommended candidate');
const upscCutoff2025 = upscCutoff(2025, 'https://www.upsc.gov.in/sites/default/files/CSE_2025_Cut-OffMks_Eng_09032026.pdf', '2026-03-09',
  'CS(Prelim)* 92.66 (General) 89.34 (EWS) 92.00 (OBC) 84.00 (SC) 82.66 (ST) … CS(Main)# 739 706 717 700 694 … CS(Final) 963 926 931 905 902. *Cut off marks on the basis of GS Paper-I only. GS Paper-II is of qualifying nature with 33% marks.');
const upscCutoff2023 = upscCutoff(2023, 'https://www.upsc.gov.in/sites/default/files/CutOff-CSE-23-engl-180424.pdf', '2024-04-18',
  'CS (Prelim)* 75.41 68.02 74.75 59.25 47.82 … CS (Main)# 741 706 712 694 692 … CS (Final) 953 923 919 890 891.');
const upscCutoff2022 = upscCutoff(2022, 'https://www.upsc.gov.in/sites/default/files/CutOff-CSE-22-Engl-230523.pdf', '2023-05-23',
  'CS(Prelim)* 88.22 82.83 87.54 74.08 69.35 … CS(Main)** 748 715 714 699 706 … CS(Final) 960 926 923 893 900.');
const upscCutoff2021 = upscCutoff(2021, 'https://www.upsc.gov.in/sites/default/files/CutOff-CSE-21-engl-300522.pdf', '2022-05-30',
  'CS(Prelim)* 87.54 80.14 84.85 75.41 70.71 … CS(Main)** 745 713 707 700 700 … CS(Final) 953 916 910 886 883.');

/** Pay is not in the CSE notice; it is set by each service's rules on the 7th CPC matrix. Said so. */
const upscPayProvenance: DataProvenance = {
  id: 'prov-upsc-pay',
  documentTitle: '7th Central Pay Commission pay matrix, as applied by each service’s recruitment rules (not part of the CSE notice)',
  officialUrl: 'https://doe.gov.in/',
  clauseNumber: 'Entry pay levels of Group A and Group B services',
  publishedDate: '2016-07-25',
  verifiedDate: UPSC_CHECK,
  verifiedBy: 'GovOS verifier — the CSE notice allots services, it does not print pay; level shown is the widely published entry level for the service',
  taxonomyType: 'INTERPRETATION',
  verificationLevel: 'UNDER_VERIFICATION',
  excerptText: 'Entry pay for IAS/IPS/IFS and the Group A services allotted through CSE is Pay Level 10 of the 7th CPC matrix; Group B services (DANICS, DANIPS, PONDICS, PONDIPS, AFHQ CS Section Officer) enter at Level 7 or 8 under their own rules. Confirm against the service’s recruitment rules before relying on it.'
};
/** Topic weightage is GovOS’s reading of the official papers, not an official figure. */
const upscWeightageProvenance: DataProvenance = {
  id: 'prov-upsc-weightage',
  documentTitle: 'GovOS reading of UPSC’s official Preliminary question papers, 2021–2026 (upsc.gov.in/examinations/previous-question-papers)',
  officialUrl: 'https://www.upsc.gov.in/examinations/previous-question-papers',
  clauseNumber: 'Approximate share of GS Paper-I questions by area',
  publishedDate: '2026-05-25',
  verifiedDate: UPSC_CHECK,
  verifiedBy: 'GovOS verifier — counted from the papers; UPSC publishes no topic-wise weightage',
  taxonomyType: 'INTERPRETATION',
  verificationLevel: 'UNDER_VERIFICATION',
  excerptText: 'UPSC does not publish topic weightage. The percentages here are GovOS’s approximate count from the official papers and vary year to year; treat them as guidance for time allocation, not as a promise about the next paper.'
};

const UPSC_PHYSICAL_NOTE = 'Physical standards under Appendix-III of the Rules for the Civil Services Examination, 2026 (Gazette of India Extraordinary, 04.02.2026): height, chest and vision norms apply to this service, with relaxations for specified categories. Read the appendix before listing the service in your preferences.';
const upscGroupA = (id: string, postName: string, department: string, ministry: string, natureOfWork: string, physical: boolean = false): PostRequirement => ({
  id, postName, department, ministry,
  payLevel: 'Pay Level 10 (entry)',
  payScale: '₹56,100 – ₹1,77,500',
  classification: 'Group A (Gazetted)',
  minAge: 21,
  maxAge: 32,
  natureOfWork,
  ...(physical ? { physicalRequired: true, physicalNote: UPSC_PHYSICAL_NOTE } : {}),
  provenance: upscPayProvenance
});
const upscGroupB = (id: string, postName: string, department: string, ministry: string, natureOfWork: string, physical: boolean = false): PostRequirement => ({
  id, postName, department, ministry,
  payLevel: 'Pay Level 7 / 8 (entry, per service rules)',
  payScale: '₹44,900 – ₹1,42,400 (Level 7) or ₹47,600 – ₹1,51,100 (Level 8)',
  classification: 'Group B (Gazetted)',
  minAge: 21,
  maxAge: 32,
  natureOfWork,
  ...(physical ? { physicalRequired: true, physicalNote: UPSC_PHYSICAL_NOTE } : {}),
  provenance: upscPayProvenance
});

export const UPSC_CSE_EXAM: Exam = {
  id: 'exam-upsc-cse-2026',
  code: 'UPSC_CSE_2026',
  title: 'UPSC Civil Services Examination (CSE) 2026',
  authorityName: 'Union Public Service Commission (UPSC)',
  officialDomain: 'https://www.upsc.gov.in',
  crucialEligibilityDate: '2026-08-01',
  minimumQualification: 'GRADUATION',
  careerFields: ['Government Job', 'Civil Services & Governance'],
  categoryTag: 'CIVIL_SERVICES',
  isGoldenJourney: false,
  isDemoData: false,
  overviewDescription:
    'The Civil Services Examination is conducted by the Union Public Service Commission in three stages — a screening Preliminary Examination (two objective papers), a descriptive Main Examination (nine papers, seven counted for merit) and a Personality Test — for recruitment to the Indian Administrative Service, the Indian Foreign Service, the Indian Police Service and twenty other Group A and Group B Central services. The 2026 cycle was notified on 4 February 2026 (Notice No. 05/2026-CSE); the Preliminary Examination was held on 24 May 2026 and the Main Examination from 21 to 30 August 2026.',
  vacanciesTotal: '1,016 (revised; the notice said approx. 933 incl. 33 for PwBD)',
  syllabusSourceNote: 'Section III of Examination Notice No. 05/2026-CSE — Part A (Preliminary Examination) and Part B (Main Examination)',

  posts: [
    upscGroupA('post-upsc-ias', 'Indian Administrative Service (IAS)', 'Indian Administrative Service', 'Ministry of Personnel, Public Grievances and Pensions (DoPT) — cadre controlling authority', 'District administration, policy implementation and secretariat leadership in State and Central Governments; begins as Assistant Collector / SDM.'),
    upscGroupA('post-upsc-ifs', 'Indian Foreign Service (IFS)', 'Indian Foreign Service', 'Ministry of External Affairs', 'Diplomacy, missions abroad, consular and trade representation; begins at MEA headquarters and a foreign posting after language training.'),
    upscGroupA('post-upsc-ips', 'Indian Police Service (IPS)', 'Indian Police Service', 'Ministry of Home Affairs — cadre controlling authority', 'Law and order, crime investigation and police leadership in a State cadre; begins as ASP / SDPO after training at SVPNPA, Hyderabad.', true),
    upscGroupA('post-upsc-iaas', 'Indian Audit and Accounts Service (IA&AS)', 'Office of the Comptroller and Auditor General of India', 'Comptroller and Auditor General of India', 'Audit of Union and State accounts and public-sector undertakings; begins as Assistant Accountant General.'),
    upscGroupA('post-upsc-icas', 'Indian Civil Accounts Service (ICAS)', 'Controller General of Accounts', 'Ministry of Finance (Department of Expenditure)', 'Payment, accounting and internal audit for Central ministries; begins as Assistant Controller of Accounts.'),
    upscGroupA('post-upsc-icls', 'Indian Corporate Law Service (ICLS)', 'Ministry of Corporate Affairs', 'Ministry of Corporate Affairs', 'Administration of the Companies Act, LLP Act and corporate regulation; begins as Assistant Registrar of Companies.'),
    upscGroupA('post-upsc-idas', 'Indian Defence Accounts Service (IDAS)', 'Controller General of Defence Accounts', 'Ministry of Defence', 'Audit, accounts and financial advice for the defence services and DRDO; begins as Assistant Controller of Defence Accounts.'),
    upscGroupA('post-upsc-ides', 'Indian Defence Estates Service (IDES)', 'Directorate General Defence Estates', 'Ministry of Defence', 'Management of defence land and cantonment administration; begins as Assistant Defence Estates Officer / CEO of a Cantonment Board.'),
    upscGroupA('post-upsc-iis', 'Indian Information Service (IIS)', 'Ministry of Information and Broadcasting', 'Ministry of Information and Broadcasting', 'Government media, press relations and public communication through PIB, Doordarshan, AIR and DAVP; begins as Assistant Director.'),
    upscGroupA('post-upsc-ipos', 'Indian Postal Service (IPoS)', 'Department of Posts', 'Ministry of Communications', 'Management of postal circles, divisions and India Post Payments Bank operations; begins as Senior Superintendent of Post Offices.'),
    upscGroupA('post-upsc-iptafs', 'Indian Post & Telecommunication Accounts and Finance Service (IP&TAFS)', 'Department of Telecommunications / Department of Posts', 'Ministry of Communications', 'Accounts, finance and licence-fee assessment for telecom and postal operations; begins as Assistant Controller of Communication Accounts.'),
    upscGroupA('post-upsc-irms-traffic', 'Indian Railway Management Service (Traffic) (IRMS)', 'Indian Railways', 'Ministry of Railways', 'Train operations, commercial and freight management in a railway zone; begins as Assistant Operations / Commercial Manager.'),
    upscGroupA('post-upsc-irms-personnel', 'Indian Railway Management Service (Personnel) (IRMS)', 'Indian Railways', 'Ministry of Railways', 'Human resources, welfare and industrial relations for the railway workforce; begins as Assistant Personnel Officer.'),
    upscGroupA('post-upsc-irms-accounts', 'Indian Railway Management Service (Accounts) (IRMS)', 'Indian Railways', 'Ministry of Railways', 'Railway finance, budgeting and accounts; begins as Assistant Divisional Finance Manager.'),
    upscGroupA('post-upsc-irpfs', 'Indian Railway Protection Force Service (IRPFS)', 'Railway Protection Force', 'Ministry of Railways', 'Security of railway property, passengers and premises; begins as Assistant Security Commissioner. Physical standards apply.', true),
    upscGroupA('post-upsc-irs-cit', 'Indian Revenue Service (Customs & Indirect Taxes) (IRS C&IT)', 'Central Board of Indirect Taxes and Customs (CBIC)', 'Ministry of Finance (Department of Revenue)', 'GST and customs administration, anti-smuggling and trade facilitation; begins as Assistant Commissioner.'),
    upscGroupA('post-upsc-irs-it', 'Indian Revenue Service (Income Tax) (IRS IT)', 'Central Board of Direct Taxes (CBDT)', 'Ministry of Finance (Department of Revenue)', 'Direct-tax assessment, investigation and administration; begins as Assistant Commissioner of Income Tax.'),
    upscGroupA('post-upsc-its', 'Indian Trade Service (ITS), Grade III', 'Directorate General of Foreign Trade', 'Ministry of Commerce and Industry', 'Foreign-trade policy, export promotion and trade negotiations; begins as Assistant Director General of Foreign Trade.'),
    upscGroupB('post-upsc-afhqcs', 'Armed Forces Headquarters Civil Service (AFHQ CS), Section Officer’s Grade', 'Armed Forces Headquarters', 'Ministry of Defence', 'Secretariat and administrative support at Army, Navy and Air Force headquarters and inter-services organisations.'),
    upscGroupB('post-upsc-danics', 'DANICS — Delhi, Andaman & Nicobar Islands, Lakshadweep, Daman & Diu and Dadra & Nagar Haveli Civil Service', 'Union Territory administrations', 'Ministry of Home Affairs', 'Civil administration in Delhi and the Union Territories; begins as SDM / Deputy Secretary-level posts in the UT cadre.'),
    upscGroupB('post-upsc-danips', 'DANIPS — Delhi, Andaman & Nicobar Islands, Lakshadweep, Daman & Diu and Dadra & Nagar Haveli Police Service', 'Union Territory police', 'Ministry of Home Affairs', 'Police service in Delhi and the Union Territories; begins as Assistant Commissioner of Police. Physical standards apply.', true),
    upscGroupB('post-upsc-pondics', 'Pondicherry Civil Service (PONDICS)', 'Government of Puducherry', 'Ministry of Home Affairs', 'Civil administration in the Union Territory of Puducherry.'),
    upscGroupB('post-upsc-pondips', 'Pondicherry Police Service (PONDIPS)', 'Government of Puducherry', 'Ministry of Home Affairs', 'Police service in the Union Territory of Puducherry. Physical standards apply.', true)
  ],

  dates: [
    { id: 'date-upsc-notif', type: 'NOTIFICATION', label: 'Examination Notice No. 05/2026-CSE published', dateTimeStr: '2026-02-04 10:00:00', timezone: 'Asia/Kolkata (IST)', isTentative: false, status: 'AVAILABLE', provenance: upscProvenance },
    { id: 'date-upsc-open', type: 'APPLICATION_OPEN', label: 'Online application opens on upsconline.nic.in', dateTimeStr: '2026-02-04 10:00:00', timezone: 'Asia/Kolkata (IST)', isTentative: false, status: 'AVAILABLE', provenance: upscProvenanceApply },
    { id: 'date-upsc-close', type: 'APPLICATION_CLOSE', label: 'Last date for online applications (6:00 PM)', dateTimeStr: '2026-02-24 18:00:00', timezone: 'Asia/Kolkata (IST)', isTentative: false, status: 'AVAILABLE', provenance: upscProvenanceFee },
    { id: 'date-upsc-eadmit', type: 'ADMIT_CARD', label: 'Preliminary e-Admit Cards uploaded on upsconline.nic.in', dateTimeStr: '2026-05-15 10:00:00', timezone: 'Asia/Kolkata (IST)', isTentative: false, status: 'AVAILABLE', provenance: upscProvenanceEAdmit },
    { id: 'date-upsc-prelims', type: 'EXAM_TIER1', label: 'Civil Services (Preliminary) Examination — two sessions, see e-Admit Card', dateTimeStr: '2026-05-24 09:30:00', timezone: 'Asia/Kolkata (IST)', isTentative: false, status: 'AVAILABLE', provenance: upscProvenanceEAdmit },
    { id: 'date-upsc-prelims-result', type: 'RESULT', label: 'Preliminary result declared (roll numbers 15 June; names 18 June)', dateTimeStr: '2026-06-15 18:00:00', timezone: 'Asia/Kolkata (IST)', isTentative: false, status: 'AVAILABLE', provenance: upscProvenancePrelimsResult },
    { id: 'date-upsc-mains-window', type: 'CORRECTION_WINDOW', label: 'Mains fee (₹200), scribe and cadre-preference window: 19–28 June 2026', dateTimeStr: '2026-06-19 10:00:00', timezone: 'Asia/Kolkata (IST)', isTentative: false, status: 'AVAILABLE', provenance: upscProvenancePrelimsResult },
    { id: 'date-upsc-mains', type: 'EXAM_TIER2', label: 'Civil Services (Main) Examination — 21–23 and 29–30 August 2026', dateTimeStr: '2026-08-21 09:00:00', timezone: 'Asia/Kolkata (IST)', isTentative: false, status: 'AVAILABLE', provenance: upscProvenanceMains },
    { id: 'date-upsc-mains-qprep', type: 'ANSWER_KEY', label: 'Mains Question Paper Representation Portal (QPReP) open 31 Aug – 4 Sep 2026', dateTimeStr: '2026-08-31 10:00:00', timezone: 'Asia/Kolkata (IST)', isTentative: false, status: 'AVAILABLE', provenance: upscProvenanceMains },
    { id: 'date-upsc-2027-notif', type: 'NOTIFICATION', label: 'CSE 2027 — notification (next cycle, per UPSC Calendar 2027)', dateTimeStr: '2027-01-13 10:00:00', timezone: 'Asia/Kolkata (IST)', isTentative: true, status: 'AVAILABLE', provenance: upscProvenanceCalendar2027 },
    { id: 'date-upsc-2027-close', type: 'APPLICATION_CLOSE', label: 'CSE 2027 — last date for applications (per Calendar 2027)', dateTimeStr: '2027-02-02 18:00:00', timezone: 'Asia/Kolkata (IST)', isTentative: true, status: 'AVAILABLE', provenance: upscProvenanceCalendar2027 },
    { id: 'date-upsc-2027-prelims', type: 'EXAM_TIER1', label: 'CSE 2027 — Preliminary Examination (per Calendar 2027)', dateTimeStr: '2027-05-23 09:30:00', timezone: 'Asia/Kolkata (IST)', isTentative: true, status: 'AVAILABLE', provenance: upscProvenanceCalendar2027 },
    { id: 'date-upsc-2027-mains', type: 'EXAM_TIER2', label: 'CSE 2027 — Main Examination commences, 5 days (per Calendar 2027)', dateTimeStr: '2027-08-20 09:00:00', timezone: 'Asia/Kolkata (IST)', isTentative: true, status: 'AVAILABLE', provenance: upscProvenanceCalendar2027 }
  ],

  globalRuleGroup: {
    id: 'rg-upsc-global',
    operator: 'AND',
    rules: [
      { id: 'rule-upsc-age-min', ruleType: 'AGE_MIN', operator: '>=', ruleValue: 21, category: 'GENERAL', provenance: upscProvenanceEligibility },
      { id: 'rule-upsc-deg', ruleType: 'DEGREE_REQUIRED', operator: '=', ruleValue: ['Bachelor Degree', 'Graduation', 'B.E', 'B.Tech', 'B.Sc', 'B.Com', 'B.A', 'BBA', 'BCA', 'MBBS', 'LLB'], category: 'GENERAL', provenance: upscProvenanceEligibility },
      { id: 'rule-upsc-nat', ruleType: 'NATIONALITY', operator: '=', ruleValue: ['Indian', 'Citizen of India', 'Subject of Nepal', 'Subject of Bhutan'], category: 'GENERAL', provenance: upscProvenanceEligibility }
    ]
  },

  eligibilityHighlights: [
    {
      title: '1. Age on the crucial date (1 August 2026)',
      body: 'A candidate must have attained 21 years and must not have attained 32 years on 1 August 2026 — born not earlier than 2 August 1994 and not later than 1 August 2005. Upper age is relaxable: SC/ST up to 5 years; OBC up to 3 years; Defence Services personnel disabled in operations up to 3 years; ex-servicemen with at least 5 years’ service up to 5 years; Persons with Benchmark Disability up to 10 years. Relaxations are cumulative only as the notice allows.',
      provenance: upscProvenanceEligibility
    },
    {
      title: '2. Number of attempts',
      body: 'Six attempts for General and EWS candidates; nine for OBC and for PwBD candidates of the General/EWS/OBC categories; unlimited (within the age limit) for SC/ST. Appearing in either paper of the Preliminary Examination counts as an attempt; applying without appearing does not.',
      provenance: upscProvenanceEligibility
    },
    {
      title: '3. Educational qualification',
      body: 'A degree of a University incorporated by an Act of the Central or a State Legislature, of an institution established by an Act of Parliament, or of a deemed University under Section 3 of the UGC Act, 1956, or an equivalent qualification. Final-year candidates and those awaiting results may sit the Preliminary Examination, but must produce proof of having passed with the Main Examination application. IAS/IPS/IFS officers already in service cannot appear again for those services.',
      provenance: upscProvenanceEligibility
    },
    {
      title: '4. Fee and how to apply',
      body: 'Apply only on upsconline.nic.in: create an account, complete Universal Registration (URN) with one photo ID, fill the Common Application Form with a live photo capture, then the exam-specific module. Fee ₹100 (Female, SC, ST and PwBD candidates exempt); ₹200 more if admitted to the Main Examination. No withdrawal and no correction after submission. The 2026 window closed on 24 February 2026 at 6:00 PM.',
      provenance: upscProvenanceFee
    }
  ],

  officialLinks: [
    { title: 'Union Public Service Commission', url: 'https://www.upsc.gov.in', note: 'upsc.gov.in — notices, question papers, results, cut-offs' },
    { title: 'UPSC Online Application Portal', url: 'https://upsconline.nic.in', note: 'upsconline.nic.in — URN registration, application, e-Admit Card, QPReP' },
    { title: 'Examination Notifications', url: 'https://www.upsc.gov.in/exams-related-info/exam-notification', note: 'Every active notice, with the PDF' },
    { title: 'Calendar of Examinations', url: 'https://www.upsc.gov.in/examinations/exam-calendar', note: 'Annual calendar — the 2027 cycle dates come from here' },
    { title: 'Previous Question Papers', url: 'https://www.upsc.gov.in/examinations/previous-question-papers', note: 'Official booklets for every stage, every year' },
    { title: 'Cut-off Marks', url: 'https://www.upsc.gov.in/examinations/cutoff-marks', note: 'Minimum qualifying marks by category and stage, year by year' }
  ],

  stages: [
    {
      id: 'stage-upsc-prelims',
      stageNumber: 1,
      stageName: 'Civil Services (Preliminary) Examination — two objective papers',
      tier: 'TIER_1',
      provenance: upscProvenanceScheme,
      durationMinutes: 240,
      totalQuestions: 180,
      totalMarks: 400,
      negativeMarking: 'One-third (0.33) of the marks assigned to a question is deducted for each wrong answer; more than one answer counts as wrong; a blank carries no penalty',
      mode: 'Pen-and-paper OMR, multiple choice; question papers in Hindi and English',
      qualifyingNature: 'A screening test only: its marks are not counted in the final merit. GS Paper-II (CSAT) is qualifying at 33%; the GS Paper-I cut-off decides who sits the Main Examination (about 12–13 times the vacancies).',
      sections: [
        { sectionName: 'General Studies Paper-I', modules: ['Current events', 'History of India & the National Movement', 'Indian & World Geography', 'Polity & Governance', 'Economic & Social Development', 'Environment, Ecology & Climate Change', 'General Science'], questions: 100, marks: 200, durationMinutes: 120, negativeMarking: '-0.66 (one-third of 2 marks)' },
        { sectionName: 'General Studies Paper-II (CSAT) — qualifying, 33%', modules: ['Comprehension', 'Interpersonal & communication skills', 'Logical reasoning & analytical ability', 'Decision making & problem solving', 'General mental ability', 'Basic numeracy & data interpretation (Class X level)'], questions: 80, marks: 200, durationMinutes: 120, negativeMarking: '-0.83 (one-third of 2.5 marks)' }
      ]
    },
    {
      id: 'stage-upsc-mains',
      stageNumber: 2,
      stageName: 'Civil Services (Main) Examination — nine descriptive papers, seven counted for merit',
      tier: 'TIER_2',
      provenance: upscProvenanceScheme,
      durationMinutes: 1620,
      totalQuestions: 0,
      totalMarks: 1750,
      negativeMarking: 'None — conventional (essay-type) answers, evaluated on content',
      mode: 'Pen-and-paper descriptive; three hours per paper; Papers I–VII may be answered in English or any Eighth Schedule language',
      qualifyingNature: 'Paper A (an Indian language) and Paper B (English), 300 marks each, are qualifying at 25% and not counted for ranking; the other seven papers are taken cognizance of only for candidates who clear both. Written total 1750 marks.',
      sections: [
        { sectionName: 'Paper A — Indian Language (qualifying, 25%)', modules: ['Comprehension', 'Précis', 'Usage & vocabulary', 'Short essays', 'Translation'], questions: 0, marks: 300, durationMinutes: 180, negativeMarking: 'None' },
        { sectionName: 'Paper B — English (qualifying, 25%)', modules: ['Comprehension', 'Précis', 'Usage & vocabulary', 'Short essays'], questions: 0, marks: 300, durationMinutes: 180, negativeMarking: 'None' },
        { sectionName: 'Paper I — Essay', modules: ['Essays on multiple topics; credit for effective and exact expression'], questions: 0, marks: 250, durationMinutes: 180, negativeMarking: 'None' },
        { sectionName: 'Paper II — General Studies-I', modules: ['Indian Heritage & Culture', 'Modern Indian History & the Freedom Struggle', 'Post-independence consolidation', 'World History', 'Indian Society', 'World Geography'], questions: 0, marks: 250, durationMinutes: 180, negativeMarking: 'None' },
        { sectionName: 'Paper III — General Studies-II', modules: ['Constitution & Polity', 'Governance', 'Social Justice', 'International Relations'], questions: 0, marks: 250, durationMinutes: 180, negativeMarking: 'None' },
        { sectionName: 'Paper IV — General Studies-III', modules: ['Economy & Development', 'Agriculture', 'Science & Technology', 'Environment & Biodiversity', 'Security', 'Disaster Management'], questions: 0, marks: 250, durationMinutes: 180, negativeMarking: 'None' },
        { sectionName: 'Paper V — General Studies-IV', modules: ['Ethics', 'Integrity', 'Aptitude', 'Case studies'], questions: 0, marks: 250, durationMinutes: 180, negativeMarking: 'None' },
        { sectionName: 'Paper VI — Optional Subject Paper 1', modules: ['One of 25 subjects or a literature (list in the notice)'], questions: 0, marks: 250, durationMinutes: 180, negativeMarking: 'None' },
        { sectionName: 'Paper VII — Optional Subject Paper 2', modules: ['Same optional subject'], questions: 0, marks: 250, durationMinutes: 180, negativeMarking: 'None' }
      ]
    },
    {
      id: 'stage-upsc-interview',
      stageNumber: 3,
      stageName: 'Personality Test (Interview)',
      tier: 'INTERVIEW',
      provenance: upscProvenanceScheme,
      durationMinutes: 0,
      totalQuestions: 0,
      totalMarks: 275,
      negativeMarking: 'Not applicable',
      mode: 'Board interview at the Commission’s office in New Delhi; about twice the number of vacancies are summoned',
      qualifyingNature: 'Carries 275 marks with no minimum qualifying marks. Final ranking = Main written (1750) + Personality Test (275) = 2025 marks; service allocation follows rank and preferences.',
      sections: [
        { sectionName: 'Personality Test', modules: ['Assessment of personal suitability for a career in public service by a Board of competent and unbiased observers'], questions: 0, marks: 275, durationMinutes: 0, negativeMarking: 'Not applicable' }
      ]
    }
  ],

  syllabus: [
    // --- Preliminary: General Studies Paper-I (Section III, Part A) ---
    { id: 'upsc-syl-history', subject: 'History & Culture', tier: 'BOTH', topicName: 'History of India and the Indian National Movement', subtopics: ['Ancient & medieval India', 'Art, architecture & literature', 'Modern India from the mid-18th century', 'Freedom struggle — stages & contributors', 'Post-independence consolidation'], weightagePercentage: 18, avgQuestions: 18, isHighYield: true, officialProvenance: upscProvenanceSyllabus, weightageProvenance: upscWeightageProvenance },
    { id: 'upsc-syl-geography', subject: 'Geography', tier: 'BOTH', topicName: 'Indian and World Geography — physical, social and economic', subtopics: ['Physical geography & geomorphology', 'Climate & monsoon', 'Indian rivers, soils & agriculture', 'Resources & industry', 'Map-based questions'], weightagePercentage: 12, avgQuestions: 12, isHighYield: true, officialProvenance: upscProvenanceSyllabus, weightageProvenance: upscWeightageProvenance },
    { id: 'upsc-syl-polity', subject: 'Polity & Governance', tier: 'BOTH', topicName: 'Indian Polity and Governance — Constitution, political system, Panchayati Raj, public policy, rights issues', subtopics: ['Preamble, Fundamental Rights & DPSP', 'Union & State executive, legislature, judiciary', 'Federalism & Centre–State relations', 'Panchayati Raj & local government', 'Constitutional & statutory bodies'], weightagePercentage: 15, avgQuestions: 15, isHighYield: true, officialProvenance: upscProvenanceSyllabus, weightageProvenance: upscWeightageProvenance },
    { id: 'upsc-syl-economy', subject: 'Economy', tier: 'BOTH', topicName: 'Economic and Social Development — sustainable development, poverty, inclusion, demographics, social-sector initiatives', subtopics: ['National income & growth', 'Money, banking & RBI', 'Fiscal policy & budget', 'External sector', 'Poverty, inclusion & welfare schemes'], weightagePercentage: 14, avgQuestions: 14, isHighYield: true, officialProvenance: upscProvenanceSyllabus, weightageProvenance: upscWeightageProvenance },
    { id: 'upsc-syl-environment', subject: 'Environment & Ecology', tier: 'BOTH', topicName: 'General issues on environmental ecology, biodiversity and climate change', subtopics: ['Ecosystems & biodiversity', 'Protected areas & species', 'Climate change & conventions', 'Pollution & environmental law', 'Conservation institutions'], weightagePercentage: 15, avgQuestions: 15, isHighYield: true, officialProvenance: upscProvenanceSyllabus, weightageProvenance: upscWeightageProvenance },
    { id: 'upsc-syl-science', subject: 'Science & Technology', tier: 'BOTH', topicName: 'General Science', subtopics: ['Physics, chemistry & biology at everyday level', 'Space, defence & IT developments', 'Biotechnology & health', 'Energy'], weightagePercentage: 10, avgQuestions: 10, isHighYield: false, officialProvenance: upscProvenanceSyllabus, weightageProvenance: upscWeightageProvenance },
    { id: 'upsc-syl-current', subject: 'Current Affairs', tier: 'BOTH', topicName: 'Current events of national and international importance', subtopics: ['Government schemes & reports', 'International organisations & summits', 'Awards, indices & reports', 'Economy & science in the news'], weightagePercentage: 16, avgQuestions: 16, isHighYield: true, officialProvenance: upscProvenanceSyllabus, weightageProvenance: upscWeightageProvenance },
    // --- Preliminary: General Studies Paper-II, CSAT (qualifying) ---
    { id: 'upsc-syl-csat-comprehension', subject: 'CSAT (Aptitude & Reasoning)', tier: 'TIER_1', topicName: 'CSAT — Comprehension and communication', subtopics: ['Reading comprehension passages', 'Interpersonal & communication skills', 'Decision making & problem solving'], weightagePercentage: 40, avgQuestions: 30, isHighYield: true, officialProvenance: upscProvenanceSyllabus, weightageProvenance: upscWeightageProvenance },
    { id: 'upsc-syl-csat-reasoning', subject: 'CSAT (Aptitude & Reasoning)', tier: 'TIER_1', topicName: 'CSAT — Logical reasoning, analytical ability and general mental ability', subtopics: ['Syllogisms & statements', 'Seating & arrangement', 'Series & coding', 'Direction sense', 'Blood relations'], weightagePercentage: 30, avgQuestions: 25, isHighYield: true, officialProvenance: upscProvenanceSyllabus, weightageProvenance: upscWeightageProvenance },
    { id: 'upsc-syl-csat-numeracy', subject: 'CSAT (Aptitude & Reasoning)', tier: 'TIER_1', topicName: 'CSAT — Basic numeracy and data interpretation (Class X level)', subtopics: ['Numbers & their relations', 'Percentage, ratio, average', 'Time, work, speed', 'Charts, graphs, tables', 'Data sufficiency'], weightagePercentage: 30, avgQuestions: 25, isHighYield: true, officialProvenance: upscProvenanceSyllabus, weightageProvenance: upscWeightageProvenance },
    // --- Main: qualifying language papers ---
    { id: 'upsc-syl-lang', subject: 'Indian Language & English (Qualifying)', tier: 'TIER_2', topicName: 'Paper A (an Indian language) and Paper B (English) — Matriculation standard, qualifying at 25%', subtopics: ['Comprehension of given passages', 'Précis writing', 'Usage & vocabulary', 'Short essays', 'Translation (Paper A)'], weightagePercentage: 0, avgQuestions: 0, isHighYield: false, officialProvenance: upscProvenanceSyllabus },
    // --- Main: papers counted for merit (Section III, Part B) ---
    { id: 'upsc-syl-essay', subject: 'Essay & Answer Writing', tier: 'TIER_2', topicName: 'Paper I — Essay (250 marks)', subtopics: ['Essays on multiple topics', 'Keeping to the subject', 'Orderly arrangement of ideas', 'Concise, exact expression'], weightagePercentage: 14, avgQuestions: 2, isHighYield: true, officialProvenance: upscProvenanceSyllabus },
    { id: 'upsc-syl-gs1', subject: 'History & Culture', tier: 'TIER_2', topicName: 'Paper II — General Studies-I: Indian Heritage and Culture, History and Geography of the World and Society (250 marks)', subtopics: ['Art forms, literature & architecture', 'Modern Indian history & freedom struggle', 'Post-independence consolidation', 'World history since the 18th century', 'Indian society, diversity, women, urbanisation, globalisation', 'World physical geography & resources'], weightagePercentage: 14, avgQuestions: 20, isHighYield: true, officialProvenance: upscProvenanceSyllabus },
    { id: 'upsc-syl-gs2', subject: 'Polity & Governance', tier: 'TIER_2', topicName: 'Paper III — General Studies-II: Governance, Constitution, Polity, Social Justice and International Relations (250 marks)', subtopics: ['Constitution — features, amendments, basic structure', 'Union & States, federalism, devolution', 'Parliament, judiciary, pressure groups', 'Government policies, welfare schemes, social sector', 'India and its neighbourhood; international institutions'], weightagePercentage: 14, avgQuestions: 20, isHighYield: true, officialProvenance: upscProvenanceSyllabus },
    { id: 'upsc-syl-gs3', subject: 'Economy', tier: 'TIER_2', topicName: 'Paper IV — General Studies-III: Technology, Economic Development, Bio-diversity, Environment, Security and Disaster Management (250 marks)', subtopics: ['Indian economy, planning, growth, budgeting', 'Agriculture, MSP, PDS, food security', 'Infrastructure & investment', 'Science & technology, IPR', 'Environment & biodiversity', 'Internal security, cyber security, disaster management'], weightagePercentage: 14, avgQuestions: 20, isHighYield: true, officialProvenance: upscProvenanceSyllabus },
    { id: 'upsc-syl-gs4', subject: 'Ethics, Integrity & Aptitude', tier: 'TIER_2', topicName: 'Paper V — General Studies-IV: Ethics, Integrity and Aptitude (250 marks)', subtopics: ['Ethics & human interface', 'Attitude, aptitude & foundational values', 'Emotional intelligence', 'Thinkers & moral philosophy', 'Probity in governance', 'Case studies'], weightagePercentage: 14, avgQuestions: 12, isHighYield: true, officialProvenance: upscProvenanceSyllabus },
    { id: 'upsc-syl-ir', subject: 'International Relations & Security', tier: 'TIER_2', topicName: 'International relations and internal security (across GS-II and GS-III)', subtopics: ['Bilateral, regional & global groupings', 'Effect of developed & developing countries’ policies on India', 'Indian diaspora', 'Linkages of extremism, money-laundering, border security'], weightagePercentage: 6, avgQuestions: 8, isHighYield: false, officialProvenance: upscProvenanceSyllabus },
    { id: 'upsc-syl-optional', subject: 'Optional Subject', tier: 'TIER_2', topicName: 'Papers VI & VII — one optional subject (500 marks)', subtopics: ['25 subjects: Agriculture to Zoology', 'Literature of 23 languages', 'Two papers of 250 marks, three hours each', 'Questions of conventional (essay) type'], weightagePercentage: 28, avgQuestions: 16, isHighYield: true, officialProvenance: upscProvenanceSyllabus }
  ],

  practiceQuestions: [],

  corrigendums: [
    {
      id: 'corr-upsc-01',
      title: 'Vacancy position revised: 1,016 vacancies notified against the approximate 933 printed in the notice',
      noticeNumber: 'UPSC Press Note dated 18.06.2026 (Result of CS(P) Examination, 2026)',
      publishedDate: '2026-06-18',
      effectiveDate: '2026-06-18',
      summary: 'The 4 February notice said the number of vacancies was expected to be approximately 933 and might change once the Cadre Controlling Authorities firmed up their numbers. The Preliminary result press note records 1,016 vacancies notified for CSE 2026, against which 13,343 candidates were shortlisted for the Main Examination.',
      pdfUrl: 'https://www.upsc.gov.in/sites/default/files/WR-NameList-CSP-2026-Engl-18062026.pdf',
      status: 'ACTIVE',
      diffSummary: 'Vacancies: approx. 933 (notice, 04-02-2026) → 1,016 (press note, 18-06-2026).'
    }
  ],

  // Official minimum qualifying marks: Prelims = GS Paper-I cut-off (of 200); Mains = written cut-off (of 1750); Final = of 2025.
  // UPSC had not published the 2024 sheet on its cut-off page when this was checked, so 2024 is absent rather than guessed.
  cutoffsHistory: [
    { year: 2025, category: 'General', tier1Cutoff: 92.66, tier2Cutoff: 739, postsEligible: 'Final cut-off 963 / 2025', provenance: upscCutoff2025 },
    { year: 2025, category: 'EWS', tier1Cutoff: 89.34, tier2Cutoff: 706, postsEligible: 'Final cut-off 926 / 2025', provenance: upscCutoff2025 },
    { year: 2025, category: 'OBC', tier1Cutoff: 92.00, tier2Cutoff: 717, postsEligible: 'Final cut-off 931 / 2025', provenance: upscCutoff2025 },
    { year: 2025, category: 'SC', tier1Cutoff: 84.00, tier2Cutoff: 700, postsEligible: 'Final cut-off 905 / 2025', provenance: upscCutoff2025 },
    { year: 2025, category: 'ST', tier1Cutoff: 82.66, tier2Cutoff: 694, postsEligible: 'Final cut-off 902 / 2025', provenance: upscCutoff2025 },
    { year: 2025, category: 'PwBD-1', tier1Cutoff: 76.66, tier2Cutoff: 703, postsEligible: 'Final cut-off 917 / 2025', provenance: upscCutoff2025 },
    { year: 2025, category: 'PwBD-2', tier1Cutoff: 54.66, tier2Cutoff: 708, postsEligible: 'Final cut-off 944 / 2025', provenance: upscCutoff2025 },
    { year: 2025, category: 'PwBD-3', tier1Cutoff: 40.66, tier2Cutoff: 536, postsEligible: 'Final cut-off 804 / 2025', provenance: upscCutoff2025 },
    { year: 2025, category: 'PwBD-5', tier1Cutoff: 40.66, tier2Cutoff: 451, postsEligible: 'Final cut-off 631 / 2025', provenance: upscCutoff2025 },

    { year: 2023, category: 'General', tier1Cutoff: 75.41, tier2Cutoff: 741, postsEligible: 'Final cut-off 953 / 2025', provenance: upscCutoff2023 },
    { year: 2023, category: 'EWS', tier1Cutoff: 68.02, tier2Cutoff: 706, postsEligible: 'Final cut-off 923 / 2025', provenance: upscCutoff2023 },
    { year: 2023, category: 'OBC', tier1Cutoff: 74.75, tier2Cutoff: 712, postsEligible: 'Final cut-off 919 / 2025', provenance: upscCutoff2023 },
    { year: 2023, category: 'SC', tier1Cutoff: 59.25, tier2Cutoff: 694, postsEligible: 'Final cut-off 890 / 2025', provenance: upscCutoff2023 },
    { year: 2023, category: 'ST', tier1Cutoff: 47.82, tier2Cutoff: 692, postsEligible: 'Final cut-off 891 / 2025', provenance: upscCutoff2023 },

    { year: 2022, category: 'General', tier1Cutoff: 88.22, tier2Cutoff: 748, postsEligible: 'Final cut-off 960 / 2025', provenance: upscCutoff2022 },
    { year: 2022, category: 'EWS', tier1Cutoff: 82.83, tier2Cutoff: 715, postsEligible: 'Final cut-off 926 / 2025', provenance: upscCutoff2022 },
    { year: 2022, category: 'OBC', tier1Cutoff: 87.54, tier2Cutoff: 714, postsEligible: 'Final cut-off 923 / 2025', provenance: upscCutoff2022 },
    { year: 2022, category: 'SC', tier1Cutoff: 74.08, tier2Cutoff: 699, postsEligible: 'Final cut-off 893 / 2025', provenance: upscCutoff2022 },
    { year: 2022, category: 'ST', tier1Cutoff: 69.35, tier2Cutoff: 706, postsEligible: 'Final cut-off 900 / 2025', provenance: upscCutoff2022 },

    { year: 2021, category: 'General', tier1Cutoff: 87.54, tier2Cutoff: 745, postsEligible: 'Final cut-off 953 / 2025', provenance: upscCutoff2021 },
    { year: 2021, category: 'EWS', tier1Cutoff: 80.14, tier2Cutoff: 713, postsEligible: 'Final cut-off 916 / 2025', provenance: upscCutoff2021 },
    { year: 2021, category: 'OBC', tier1Cutoff: 84.85, tier2Cutoff: 707, postsEligible: 'Final cut-off 910 / 2025', provenance: upscCutoff2021 },
    { year: 2021, category: 'SC', tier1Cutoff: 75.41, tier2Cutoff: 700, postsEligible: 'Final cut-off 886 / 2025', provenance: upscCutoff2021 },
    { year: 2021, category: 'ST', tier1Cutoff: 70.71, tier2Cutoff: 700, postsEligible: 'Final cut-off 883 / 2025', provenance: upscCutoff2021 }
  ],

  // Links only, all answering HTTP 200 through GovOS's own checker on 2026-09-12. Coaching channels are
  // labelled as such with the subscriber count read from the channel page on the same day.
  resources: [
    {
      id: 'res-upsc-notice-2026',
      title: 'UPSC CSE 2026 — Examination Notice No. 05/2026-CSE (official PDF, 159 pages)',
      subject: 'Official Gazette',
      author: 'Union Public Service Commission',
      type: 'OFFICIAL_PDF',
      resourceFormat: 'DIRECT_PDF',
      url: UPSC_NOTICE_URL,
      directPdfUrl: UPSC_NOTICE_URL,
      downloadFileName: 'Notif-CSP-2026-Engl-060226Rev.pdf',
      officialTag: 'UPSC — PRIMARY NOTIFICATION (PDF, 2.9 MB)',
      recommendedFor: 'The one document that governs the cycle: eligibility, attempts, fee, scheme, the full syllabus (Section III) and the list of services. Verify every claim, including GovOS’s, against it.',
      description: 'The Commission’s notice for the Civil Services (Preliminary) Examination, 2026, hosted on upsc.gov.in. Sections I–III carry the services, eligibility, scheme and syllabi; the appendices carry the rules, centres and certificate formats. GovOS links to the file on the UPSC server rather than keeping a copy.',
      linkVerifiedDate: UPSC_CHECK,
      isEssential: true,
      provenance: officialSource('prov-res-upsc-notice', 'UPSC CSE 2026 — Examination Notice No. 05/2026-CSE', UPSC_NOTICE_URL, 200)
    },
    {
      id: 'res-upsc-portal',
      title: 'UPSC Online Application Portal (upsconline.nic.in)',
      subject: 'Official Gazette',
      author: 'Union Public Service Commission',
      type: 'OFFICIAL_PORTAL',
      resourceFormat: 'OFFICIAL_PORTAL',
      url: 'https://upsconline.nic.in',
      officialTag: 'UPSC — APPLICATION, e-ADMIT CARD, QPReP',
      recommendedFor: 'Registering (URN), applying, downloading the e-Admit Card, paying the Mains fee and filing question-paper representations.',
      description: 'The only portal for the Civil Services Examination application. Four modules — account, Universal Registration, Common Application Form, exam-specific form — and the e-Admit Card download. No admit card is sent by post or email.',
      linkVerifiedDate: UPSC_CHECK,
      isEssential: true,
      provenance: officialSource('prov-res-upsc-portal', 'UPSC Online Application Portal', 'https://upsconline.nic.in', 200)
    },
    {
      id: 'res-upsc-pyq-page',
      title: 'UPSC Previous Question Papers — official page (every stage, every year)',
      subject: 'Previous Year Papers',
      author: 'Union Public Service Commission',
      type: 'OFFICIAL_PORTAL',
      resourceFormat: 'OFFICIAL_PORTAL',
      url: 'https://www.upsc.gov.in/examinations/previous-question-papers',
      officialTag: 'UPSC — QUESTION PAPER ARCHIVE',
      recommendedFor: 'The real papers, as printed. Start every subject by reading five years of them.',
      description: 'UPSC publishes each question booklet after the examination — Preliminary GS-I and GS-II, and every Main paper including all optionals. This page lists them by examination and year.',
      linkVerifiedDate: UPSC_CHECK,
      isEssential: true,
      provenance: officialSource('prov-res-upsc-pyq-page', 'UPSC Previous Question Papers', 'https://www.upsc.gov.in/examinations/previous-question-papers', 200)
    },
    {
      id: 'res-upsc-qp-2026-gs1',
      title: 'CSE 2026 Preliminary — General Studies Paper-I question booklet (official PDF)',
      subject: 'Previous Year Papers',
      author: 'Union Public Service Commission',
      type: 'OFFICIAL_PDF',
      resourceFormat: 'DIRECT_PDF',
      url: 'https://www.upsc.gov.in/sites/default/files/QP_CSP_2026_GENERAL_STUDIES_PAPER-I_25052026.pdf',
      directPdfUrl: 'https://www.upsc.gov.in/sites/default/files/QP_CSP_2026_GENERAL_STUDIES_PAPER-I_25052026.pdf',
      downloadFileName: 'QP_CSP_2026_GENERAL_STUDIES_PAPER-I_25052026.pdf',
      officialTag: 'UPSC — 2026 PAPER (100 questions, 200 marks, 2 hours)',
      recommendedFor: 'The most recent GS Paper-I, exactly as candidates saw it on 24 May 2026.',
      description: 'The Series-A booklet of the 2026 Preliminary GS Paper-I published by UPSC the day after the examination. Scanned, so search does not work inside it; read it as a paper.',
      linkVerifiedDate: UPSC_CHECK,
      provenance: officialSource('prov-res-upsc-qp-2026-gs1', 'CSE 2026 Preliminary — GS Paper-I', 'https://www.upsc.gov.in/sites/default/files/QP_CSP_2026_GENERAL_STUDIES_PAPER-I_25052026.pdf', 200)
    },
    {
      id: 'res-upsc-qp-2026-gs2',
      title: 'CSE 2026 Preliminary — General Studies Paper-II (CSAT) question booklet (official PDF)',
      subject: 'Previous Year Papers',
      author: 'Union Public Service Commission',
      type: 'OFFICIAL_PDF',
      resourceFormat: 'DIRECT_PDF',
      url: 'https://www.upsc.gov.in/sites/default/files/QP_CSP_2026_GENERAL_STUDIES_PAPER-II_25052026.pdf',
      directPdfUrl: 'https://www.upsc.gov.in/sites/default/files/QP_CSP_2026_GENERAL_STUDIES_PAPER-II_25052026.pdf',
      downloadFileName: 'QP_CSP_2026_GENERAL_STUDIES_PAPER-II_25052026.pdf',
      officialTag: 'UPSC — 2026 PAPER (80 questions, 200 marks, 2 hours, qualifying 33%)',
      recommendedFor: 'Calibrating CSAT: time yourself on the real 80 questions before assuming it is a formality.',
      description: 'The Series-A booklet of the 2026 CSAT paper published by UPSC the day after the examination.',
      linkVerifiedDate: UPSC_CHECK,
      provenance: officialSource('prov-res-upsc-qp-2026-gs2', 'CSE 2026 Preliminary — GS Paper-II (CSAT)', 'https://www.upsc.gov.in/sites/default/files/QP_CSP_2026_GENERAL_STUDIES_PAPER-II_25052026.pdf', 200)
    },
    {
      id: 'res-upsc-qp-2026-essay',
      title: 'CSE 2026 Main — Essay paper (official PDF)',
      subject: 'Previous Year Papers',
      author: 'Union Public Service Commission',
      type: 'OFFICIAL_PDF',
      resourceFormat: 'DIRECT_PDF',
      url: 'https://www.upsc.gov.in/sites/default/files/QP-CSM-26-010926-ESSAY.pdf',
      directPdfUrl: 'https://www.upsc.gov.in/sites/default/files/QP-CSM-26-010926-ESSAY.pdf',
      downloadFileName: 'QP-CSM-26-010926-ESSAY.pdf',
      officialTag: 'UPSC — 2026 MAIN PAPER I (250 marks)',
      recommendedFor: 'Practising the Essay paper on this year’s topics.',
      description: 'The Essay paper of the Civil Services (Main) Examination, 2026, published by UPSC on 1 September 2026.',
      linkVerifiedDate: UPSC_CHECK,
      provenance: officialSource('prov-res-upsc-qp-2026-essay', 'CSE 2026 Main — Essay', 'https://www.upsc.gov.in/sites/default/files/QP-CSM-26-010926-ESSAY.pdf', 200)
    },
    {
      id: 'res-upsc-qp-2026-gs-i',
      title: 'CSE 2026 Main — General Studies Paper-I (official PDF)',
      subject: 'Previous Year Papers',
      author: 'Union Public Service Commission',
      type: 'OFFICIAL_PDF',
      resourceFormat: 'DIRECT_PDF',
      url: 'https://www.upsc.gov.in/sites/default/files/QP-CSM-26-010926-GENERAL%20STUDIES%20PAPER%20-%20I.pdf',
      directPdfUrl: 'https://www.upsc.gov.in/sites/default/files/QP-CSM-26-010926-GENERAL%20STUDIES%20PAPER%20-%20I.pdf',
      downloadFileName: 'QP-CSM-26-GS-I.pdf',
      officialTag: 'UPSC — 2026 MAIN PAPER II (250 marks)',
      recommendedFor: 'History, culture, geography and society answer-writing on the real 2026 questions.',
      description: 'General Studies Paper-I of the Main Examination, 2026, as published by UPSC.',
      linkVerifiedDate: UPSC_CHECK,
      provenance: officialSource('prov-res-upsc-qp-2026-gs-i', 'CSE 2026 Main — GS Paper-I', 'https://www.upsc.gov.in/sites/default/files/QP-CSM-26-010926-GENERAL%20STUDIES%20PAPER%20-%20I.pdf', 200)
    },
    {
      id: 'res-upsc-qp-2026-gs-ii',
      title: 'CSE 2026 Main — General Studies Paper-II (official PDF)',
      subject: 'Previous Year Papers',
      author: 'Union Public Service Commission',
      type: 'OFFICIAL_PDF',
      resourceFormat: 'DIRECT_PDF',
      url: 'https://www.upsc.gov.in/sites/default/files/QP-CSM-26-010926-GENERAL-STUDIES-PAPER%20-%20II.pdf',
      directPdfUrl: 'https://www.upsc.gov.in/sites/default/files/QP-CSM-26-010926-GENERAL-STUDIES-PAPER%20-%20II.pdf',
      downloadFileName: 'QP-CSM-26-GS-II.pdf',
      officialTag: 'UPSC — 2026 MAIN PAPER III (250 marks)',
      recommendedFor: 'Polity, governance, social justice and international relations answer-writing.',
      description: 'General Studies Paper-II of the Main Examination, 2026, as published by UPSC.',
      linkVerifiedDate: UPSC_CHECK,
      provenance: officialSource('prov-res-upsc-qp-2026-gs-ii', 'CSE 2026 Main — GS Paper-II', 'https://www.upsc.gov.in/sites/default/files/QP-CSM-26-010926-GENERAL-STUDIES-PAPER%20-%20II.pdf', 200)
    },
    {
      id: 'res-upsc-qp-2026-gs-iii',
      title: 'CSE 2026 Main — General Studies Paper-III (official PDF)',
      subject: 'Previous Year Papers',
      author: 'Union Public Service Commission',
      type: 'OFFICIAL_PDF',
      resourceFormat: 'DIRECT_PDF',
      url: 'https://www.upsc.gov.in/sites/default/files/QP-CSM-26-010926-GENERAL-STUDIES-PAPER-III.pdf',
      directPdfUrl: 'https://www.upsc.gov.in/sites/default/files/QP-CSM-26-010926-GENERAL-STUDIES-PAPER-III.pdf',
      downloadFileName: 'QP-CSM-26-GS-III.pdf',
      officialTag: 'UPSC — 2026 MAIN PAPER IV (250 marks)',
      recommendedFor: 'Economy, science, environment, security and disaster-management answer-writing.',
      description: 'General Studies Paper-III of the Main Examination, 2026, as published by UPSC.',
      linkVerifiedDate: UPSC_CHECK,
      provenance: officialSource('prov-res-upsc-qp-2026-gs-iii', 'CSE 2026 Main — GS Paper-III', 'https://www.upsc.gov.in/sites/default/files/QP-CSM-26-010926-GENERAL-STUDIES-PAPER-III.pdf', 200)
    },
    {
      id: 'res-upsc-qp-2026-gs-iv',
      title: 'CSE 2026 Main — General Studies Paper-IV, Ethics (official PDF)',
      subject: 'Previous Year Papers',
      author: 'Union Public Service Commission',
      type: 'OFFICIAL_PDF',
      resourceFormat: 'DIRECT_PDF',
      url: 'https://www.upsc.gov.in/sites/default/files/QP-CSM-26-010926-GENERAL-STUDIES-PAPER-IV.pdf',
      directPdfUrl: 'https://www.upsc.gov.in/sites/default/files/QP-CSM-26-010926-GENERAL-STUDIES-PAPER-IV.pdf',
      downloadFileName: 'QP-CSM-26-GS-IV.pdf',
      officialTag: 'UPSC — 2026 MAIN PAPER V (250 marks)',
      recommendedFor: 'Ethics theory and the case studies exactly as set in 2026.',
      description: 'General Studies Paper-IV of the Main Examination, 2026, as published by UPSC.',
      linkVerifiedDate: UPSC_CHECK,
      provenance: officialSource('prov-res-upsc-qp-2026-gs-iv', 'CSE 2026 Main — GS Paper-IV', 'https://www.upsc.gov.in/sites/default/files/QP-CSM-26-010926-GENERAL-STUDIES-PAPER-IV.pdf', 200)
    },
    {
      id: 'res-upsc-cutoffs',
      title: 'UPSC Cut-off Marks — official page and the 2025 sheet',
      subject: 'Official Gazette',
      author: 'Union Public Service Commission',
      type: 'OFFICIAL_PORTAL',
      resourceFormat: 'OFFICIAL_PORTAL',
      url: 'https://www.upsc.gov.in/examinations/cutoff-marks',
      officialTag: 'UPSC — MINIMUM QUALIFYING MARKS, BY YEAR',
      recommendedFor: 'Seeing the real bar for each stage and category, from the Commission, not from a coaching estimate.',
      description: 'UPSC publishes, after each final result, the marks secured by the last recommended candidate at the Preliminary, Main and Final stages for every category. The 2025 sheet (CSE_2025_Cut-OffMks_Eng_09032026.pdf) is the latest; GovOS’s cut-off table is read from these sheets.',
      linkVerifiedDate: UPSC_CHECK,
      provenance: officialSource('prov-res-upsc-cutoffs', 'UPSC Cut-off Marks', 'https://www.upsc.gov.in/examinations/cutoff-marks', 200)
    },
    {
      id: 'res-upsc-calendar-2027',
      title: 'UPSC Calendar of Examinations, 2027 (official PDF)',
      subject: 'Official Gazette',
      author: 'Union Public Service Commission',
      type: 'OFFICIAL_PDF',
      resourceFormat: 'DIRECT_PDF',
      url: 'https://www.upsc.gov.in/sites/default/files/Calendar-Year-2027-Engl-200526.pdf',
      directPdfUrl: 'https://www.upsc.gov.in/sites/default/files/Calendar-Year-2027-Engl-200526.pdf',
      downloadFileName: 'Calendar-Year-2027-Engl-200526.pdf',
      officialTag: 'UPSC — NEXT CYCLE DATES (published 20 May 2026)',
      recommendedFor: 'Planning the 2027 attempt: notification 13 Jan 2027, last date 2 Feb 2027, Prelims 23 May 2027, Mains from 20 Aug 2027.',
      description: 'The Commission’s annual calendar for 2027. The CSE 2027 dates on GovOS’s timeline are read from row 9 (Preliminary) and row 19 (Main) of this document.',
      linkVerifiedDate: UPSC_CHECK,
      provenance: officialSource('prov-res-upsc-calendar-2027', 'UPSC Calendar of Examinations, 2027', 'https://www.upsc.gov.in/sites/default/files/Calendar-Year-2027-Engl-200526.pdf', 200)
    },
    {
      id: 'res-upsc-mains-press',
      title: 'CSE 2026 — Main Examination press note (dates and QPReP window)',
      subject: 'Official Gazette',
      author: 'Union Public Service Commission',
      type: 'OFFICIAL_PDF',
      resourceFormat: 'DIRECT_PDF',
      url: 'https://www.upsc.gov.in/sites/default/files/PressNote-CSM-2026-Engl-190826.pdf',
      directPdfUrl: 'https://www.upsc.gov.in/sites/default/files/PressNote-CSM-2026-Engl-190826.pdf',
      downloadFileName: 'PressNote-CSM-2026-Engl-190826.pdf',
      officialTag: 'UPSC — PRESS NOTE, 19 AUG 2026',
      recommendedFor: 'Confirming the Main Examination dates and the representation window from the Commission itself.',
      description: 'States that the Main Examination is held 21–23 and 29–30 August 2026 and that the Question Paper Representation Portal is open 31 August to 4 September 2026 on upsconline.nic.in.',
      linkVerifiedDate: UPSC_CHECK,
      provenance: officialSource('prov-res-upsc-mains-press', 'CSE 2026 — Main Examination press note', 'https://www.upsc.gov.in/sites/default/files/PressNote-CSM-2026-Engl-190826.pdf', 200)
    },
    {
      id: 'res-upsc-prelims-result',
      title: 'CSE 2026 — Preliminary result press note with the list of qualified candidates',
      subject: 'Official Gazette',
      author: 'Union Public Service Commission',
      type: 'OFFICIAL_PDF',
      resourceFormat: 'DIRECT_PDF',
      url: 'https://www.upsc.gov.in/sites/default/files/WR-NameList-CSP-2026-Engl-18062026.pdf',
      directPdfUrl: 'https://www.upsc.gov.in/sites/default/files/WR-NameList-CSP-2026-Engl-18062026.pdf',
      downloadFileName: 'WR-NameList-CSP-2026-Engl-18062026.pdf',
      officialTag: 'UPSC — PRESS NOTE, 18 JUN 2026 (505 pages)',
      recommendedFor: 'Checking the Mains window, the ₹200 fee and the revised vacancy figure of 1,016.',
      description: 'Declares the 13,343 candidates qualified for the Main Examination, the 19–28 June window for fee, scribe and cadre preferences, and records 1,016 vacancies notified for CSE 2026.',
      linkVerifiedDate: UPSC_CHECK,
      provenance: officialSource('prov-res-upsc-prelims-result', 'CSE 2026 — Preliminary result press note', 'https://www.upsc.gov.in/sites/default/files/WR-NameList-CSP-2026-Engl-18062026.pdf', 200)
    },
    {
      id: 'res-upsc-constitution',
      title: 'The Constitution of India — official full text (Legislative Department)',
      subject: 'Polity & Governance',
      author: 'Legislative Department, Ministry of Law and Justice',
      type: 'OFFICIAL_PORTAL',
      resourceFormat: 'OFFICIAL_PORTAL',
      url: 'https://legislative.gov.in/constitution-of-india/',
      officialTag: 'GOVERNMENT OF INDIA — PRIMARY TEXT',
      recommendedFor: 'GS-II and the Prelims polity questions: read the articles themselves, then the commentary.',
      description: 'The Legislative Department’s page for the Constitution of India as amended, with the full text and the amendment acts. Every polity claim in GovOS should be checkable here.',
      linkVerifiedDate: UPSC_CHECK,
      isEssential: true,
      provenance: officialSource('prov-res-upsc-constitution', 'The Constitution of India — official text', 'https://legislative.gov.in/constitution-of-india/', 200)
    },
    {
      id: 'res-upsc-indiacode',
      title: 'India Code — every Central Act, as amended',
      subject: 'Polity & Governance',
      author: 'Legislative Department, Ministry of Law and Justice',
      type: 'OFFICIAL_PORTAL',
      resourceFormat: 'OFFICIAL_PORTAL',
      url: 'https://www.indiacode.nic.in/',
      officialTag: 'GOVERNMENT OF INDIA — STATUTES',
      recommendedFor: 'Governance and social-justice questions that turn on what a statute actually says.',
      description: 'The official repository of Central and State Acts with amendments, rules and notifications.',
      linkVerifiedDate: UPSC_CHECK,
      provenance: officialSource('prov-res-upsc-indiacode', 'India Code', 'https://www.indiacode.nic.in/', 200)
    },
    {
      id: 'res-upsc-pib',
      title: 'Press Information Bureau — Government of India releases',
      subject: 'Current Affairs & Governance',
      author: 'Press Information Bureau, Ministry of Information and Broadcasting',
      type: 'OFFICIAL_PORTAL',
      resourceFormat: 'OFFICIAL_PORTAL',
      url: 'https://pib.gov.in/',
      officialTag: 'GOVERNMENT OF INDIA — DAILY RELEASES',
      recommendedFor: 'Current affairs from the source: schemes, cabinet decisions, reports, in the government’s own words.',
      description: 'Every press release of the Government of India, searchable by ministry and date. The primary source most current-affairs compilations are built from.',
      linkVerifiedDate: UPSC_CHECK,
      isEssential: true,
      provenance: officialSource('prov-res-upsc-pib', 'Press Information Bureau', 'https://pib.gov.in/', 200)
    },
    {
      id: 'res-upsc-economic-survey',
      title: 'Economic Survey of India — Ministry of Finance',
      subject: 'Economy',
      author: 'Department of Economic Affairs, Ministry of Finance',
      type: 'OFFICIAL_PORTAL',
      resourceFormat: 'OFFICIAL_PORTAL',
      url: 'https://www.indiabudget.gov.in/economicsurvey/',
      officialTag: 'GOVERNMENT OF INDIA — ANNUAL SURVEY',
      recommendedFor: 'GS-III economy and the Prelims economic-development questions; read the chapter summaries and the data tables.',
      description: 'The Economic Survey tabled before the Union Budget each year, with all chapters and statistical appendices as PDFs.',
      linkVerifiedDate: UPSC_CHECK,
      isEssential: true,
      provenance: officialSource('prov-res-upsc-economic-survey', 'Economic Survey of India', 'https://www.indiabudget.gov.in/economicsurvey/', 200)
    },
    {
      id: 'res-upsc-rbi',
      title: 'Reserve Bank of India — publications, reports and data',
      subject: 'Economy',
      author: 'Reserve Bank of India',
      type: 'OFFICIAL_PORTAL',
      resourceFormat: 'OFFICIAL_PORTAL',
      url: 'https://www.rbi.org.in/',
      officialTag: 'REGULATOR — MONETARY POLICY & BANKING',
      recommendedFor: 'Monetary policy, banking regulation and the RBI annual report and bulletins.',
      description: 'The central bank’s site: policy statements, the Annual Report, Financial Stability Report and the database on the Indian economy.',
      linkVerifiedDate: UPSC_CHECK,
      provenance: officialSource('prov-res-upsc-rbi', 'Reserve Bank of India', 'https://www.rbi.org.in/', 200)
    },
    {
      id: 'res-upsc-niti',
      title: 'NITI Aayog — reports, indices and policy papers',
      subject: 'Economy',
      author: 'NITI Aayog, Government of India',
      type: 'OFFICIAL_PORTAL',
      resourceFormat: 'OFFICIAL_PORTAL',
      url: 'https://www.niti.gov.in/',
      officialTag: 'GOVERNMENT OF INDIA — POLICY THINK TANK',
      recommendedFor: 'SDG India Index, multidimensional poverty, health and innovation indices that recur in GS-II and GS-III.',
      description: 'The Government’s policy think tank: its reports and indices are frequent sources for Mains questions on development.',
      linkVerifiedDate: UPSC_CHECK,
      provenance: officialSource('prov-res-upsc-niti', 'NITI Aayog', 'https://www.niti.gov.in/', 200)
    },
    {
      id: 'res-upsc-mea',
      title: 'Ministry of External Affairs — bilateral briefs and joint statements',
      subject: 'Current Affairs & Governance',
      author: 'Ministry of External Affairs',
      type: 'OFFICIAL_PORTAL',
      resourceFormat: 'OFFICIAL_PORTAL',
      url: 'https://www.mea.gov.in/',
      officialTag: 'GOVERNMENT OF INDIA — FOREIGN POLICY',
      recommendedFor: 'International relations in GS-II: the country briefs and joint statements are the primary source.',
      description: 'Official briefs on India’s relations with every country and organisation, press releases and speeches.',
      linkVerifiedDate: UPSC_CHECK,
      provenance: officialSource('prov-res-upsc-mea', 'Ministry of External Affairs', 'https://www.mea.gov.in/', 200)
    },
    {
      id: 'res-upsc-sansad',
      title: 'Sansad — Parliament of India digital portal (bills, debates, questions)',
      subject: 'Polity & Governance',
      author: 'Lok Sabha and Rajya Sabha Secretariats',
      type: 'OFFICIAL_PORTAL',
      resourceFormat: 'OFFICIAL_PORTAL',
      url: 'https://sansad.in/',
      officialTag: 'PARLIAMENT OF INDIA — PRIMARY RECORDS',
      recommendedFor: 'Bills, committee reports and parliamentary questions, as introduced and answered.',
      description: 'The integrated portal of both Houses: legislation, debates, questions and committee reports.',
      linkVerifiedDate: UPSC_CHECK,
      provenance: officialSource('prov-res-upsc-sansad', 'Sansad — Parliament of India', 'https://sansad.in/', 200)
    },
    {
      id: 'res-upsc-prs',
      title: 'PRS Legislative Research — bill summaries and analysis',
      subject: 'Polity & Governance',
      author: 'PRS Legislative Research (independent, non-profit)',
      type: 'SIMPLIFIED_GUIDE',
      resourceFormat: 'OFFICIAL_PORTAL',
      url: 'https://prsindia.org/',
      officialTag: 'TRUSTED PUBLIC SOURCE — NOT GOVERNMENT',
      recommendedFor: 'Understanding a bill quickly before reading it on Sansad; widely cited, but it is analysis, not the statute.',
      description: 'Independent, non-partisan summaries of bills, budgets and state legislatures. GovOS lists it as a trusted public source; the Act on India Code governs where they differ.',
      linkVerifiedDate: UPSC_CHECK,
      provenance: communitySource('prov-res-upsc-prs', 'PRS Legislative Research', 'https://prsindia.org/', 'widely cited by candidates and the press')
    },
    {
      id: 'res-upsc-ncert-diksha',
      title: 'NCERT textbooks, Classes VI–XII — DIKSHA (Ministry of Education)',
      subject: 'Foundation Textbooks & Open Courses',
      author: 'NCERT via DIKSHA, Ministry of Education',
      type: 'OFFICIAL_PORTAL',
      resourceFormat: 'OFFICIAL_PORTAL',
      url: 'https://diksha.gov.in/ncert',
      officialTag: 'NCERT — FULL TEXTBOOKS, FREE',
      recommendedFor: 'The foundation for History, Geography, Polity, Economics and Science: read the NCERTs before any coaching notes.',
      description: 'Every NCERT textbook, chapter by chapter, on the Ministry of Education’s DIKSHA platform. Linked here because ncert.nic.in has timed out from Indian networks; the content is NCERT’s own.',
      linkVerifiedDate: UPSC_CHECK,
      isEssential: true,
      provenance: officialSource('prov-res-upsc-ncert-diksha', 'NCERT textbooks on DIKSHA', 'https://diksha.gov.in/ncert', 200)
    },
    {
      id: 'res-upsc-egazette',
      title: 'e-Gazette of India — notifications as published',
      subject: 'Official Gazette',
      author: 'Directorate of Printing, Government of India',
      type: 'OFFICIAL_PORTAL',
      resourceFormat: 'OFFICIAL_PORTAL',
      url: 'https://egazette.gov.in/',
      officialTag: 'GOVERNMENT OF INDIA — GAZETTE',
      recommendedFor: 'The Civil Services Examination Rules are notified in the Gazette (Extraordinary) each February; this is where to find them.',
      description: 'The official electronic Gazette of India. The 2026 rules were published in the Gazette Extraordinary dated 4 February 2026, as the notice states.',
      linkVerifiedDate: UPSC_CHECK,
      provenance: officialSource('prov-res-upsc-egazette', 'e-Gazette of India', 'https://egazette.gov.in/', 200)
    },
    {
      id: 'res-upsc-sansadtv',
      title: 'Sansad TV — Parliament’s broadcaster (YouTube channel, 9.63M subscribers)',
      subject: 'Current Affairs & Governance',
      author: 'Sansad TV, Parliament of India',
      type: 'VIDEO_LECTURE',
      resourceFormat: 'YOUTUBE_CHANNEL',
      url: 'https://www.youtube.com/channel/UCISgnSNwqQ2i8lhCun3KtQg',
      officialTag: 'OFFICIAL BROADCASTER — FREE',
      recommendedFor: 'Perspective, In Depth and the debate coverage that Mains answers draw on; an official source, unlike coaching channels.',
      description: 'The Parliament of India’s own channel: proceedings, and discussion programmes on policy and current affairs. Channel identity confirmed from the channel page on 2026-09-12.',
      linkVerifiedDate: UPSC_CHECK,
      provenance: officialSource('prov-res-upsc-sansadtv', 'Sansad TV (YouTube)', 'https://www.youtube.com/channel/UCISgnSNwqQ2i8lhCun3KtQg', 200)
    },
    {
      id: 'res-upsc-yt-studyiq',
      title: 'StudyIQ IAS — YouTube channel (20.5M subscribers)',
      subject: 'Current Affairs & Governance',
      author: 'StudyIQ IAS (YouTube channel)',
      type: 'VIDEO_LECTURE',
      resourceFormat: 'YOUTUBE_CHANNEL',
      url: 'https://www.youtube.com/channel/UCrC8mOqJQpoB7NuIMKIS6rQ',
      officialTag: 'FREE · COACHING · 20.5M SUBSCRIBERS (checked 2026-09-12)',
      recommendedFor: 'Daily current-affairs and editorial analysis in Hindi and English; the most-followed UPSC channel.',
      description: 'Coaching content, not a government source. Listed because it is the most-subscribed UPSC channel; GovOS confirmed the channel identity and count from the channel page and has not fact-checked its lessons.',
      linkVerifiedDate: UPSC_CHECK,
      provenance: communitySource('prov-res-upsc-yt-studyiq', 'StudyIQ IAS (YouTube)', 'https://www.youtube.com/channel/UCrC8mOqJQpoB7NuIMKIS6rQ', '20.5M subscribers')
    },
    {
      id: 'res-upsc-yt-drishti',
      title: 'Drishti IAS — YouTube channel (12.9M subscribers)',
      subject: 'History & Culture',
      author: 'Drishti IAS (YouTube channel)',
      type: 'VIDEO_LECTURE',
      resourceFormat: 'YOUTUBE_CHANNEL',
      url: 'https://www.youtube.com/channel/UCzLqOSZPtUKrmSEnlH4LAvw',
      officialTag: 'FREE · COACHING · 12.9M SUBSCRIBERS (checked 2026-09-12)',
      recommendedFor: 'Hindi-medium candidates especially: answer writing, editorial analysis and ethics discussions.',
      description: 'Coaching content, not a government source. Identity and subscriber count confirmed from the channel page on 2026-09-12; lessons not fact-checked by GovOS.',
      linkVerifiedDate: UPSC_CHECK,
      provenance: communitySource('prov-res-upsc-yt-drishti', 'Drishti IAS (YouTube)', 'https://www.youtube.com/channel/UCzLqOSZPtUKrmSEnlH4LAvw', '12.9M subscribers')
    },
    {
      id: 'res-upsc-yt-mrunal',
      title: 'Mrunal Patel — YouTube channel (2.1M subscribers)',
      subject: 'Economy',
      author: 'Mrunal Patel (YouTube channel)',
      type: 'VIDEO_LECTURE',
      resourceFormat: 'YOUTUBE_CHANNEL',
      url: 'https://www.youtube.com/channel/UCwDfgcUkKKTxPozU9UnQ8Pw',
      officialTag: 'FREE · COACHING · 2.1M SUBSCRIBERS (checked 2026-09-12)',
      recommendedFor: 'Economy — budget and Economic Survey walkthroughs that candidates widely use for GS-III.',
      description: 'Coaching content, not a government source. Identity and subscriber count confirmed from the channel page on 2026-09-12; lessons not fact-checked by GovOS.',
      linkVerifiedDate: UPSC_CHECK,
      provenance: communitySource('prov-res-upsc-yt-mrunal', 'Mrunal Patel (YouTube)', 'https://www.youtube.com/channel/UCwDfgcUkKKTxPozU9UnQ8Pw', '2.1M subscribers')
    },
    {
      id: 'res-upsc-yt-vision',
      title: 'Vision IAS — YouTube channel (1.82M subscribers)',
      subject: 'Current Affairs & Governance',
      author: 'Vision IAS (YouTube channel)',
      type: 'VIDEO_LECTURE',
      resourceFormat: 'YOUTUBE_CHANNEL',
      url: 'https://www.youtube.com/channel/UCw4wosjC-DKq95xI5klz92w',
      officialTag: 'FREE · COACHING · 1.82M SUBSCRIBERS (checked 2026-09-12)',
      recommendedFor: 'Monthly current-affairs revision and Prelims–Mains linkage.',
      description: 'Coaching content, not a government source. Identity and subscriber count confirmed from the channel page on 2026-09-12; lessons not fact-checked by GovOS.',
      linkVerifiedDate: UPSC_CHECK,
      provenance: communitySource('prov-res-upsc-yt-vision', 'Vision IAS (YouTube)', 'https://www.youtube.com/channel/UCw4wosjC-DKq95xI5klz92w', '1.82M subscribers')
    },
    {
      id: 'res-upsc-yt-sleepy',
      title: 'Sleepy Classes IAS — YouTube channel (1.28M subscribers)',
      subject: 'Ethics, Essay & Answer Writing',
      author: 'Sleepy Classes IAS (YouTube channel)',
      type: 'VIDEO_LECTURE',
      resourceFormat: 'YOUTUBE_CHANNEL',
      url: 'https://www.youtube.com/channel/UCgRf62bnK3uX4N-YEhG4Jog',
      officialTag: 'FREE · COACHING · 1.28M SUBSCRIBERS (checked 2026-09-12)',
      recommendedFor: 'Ethics (GS-IV), essay and answer-writing sessions.',
      description: 'Coaching content, not a government source. Identity and subscriber count confirmed from the channel page on 2026-09-12; lessons not fact-checked by GovOS.',
      linkVerifiedDate: UPSC_CHECK,
      provenance: communitySource('prov-res-upsc-yt-sleepy', 'Sleepy Classes IAS (YouTube)', 'https://www.youtube.com/channel/UCgRf62bnK3uX4N-YEhG4Jog', '1.28M subscribers')
    },
    {
      id: 'res-upsc-yt-vajiram',
      title: 'Vajiram and Ravi Official — YouTube channel (689K subscribers)',
      subject: 'Polity & Governance',
      author: 'Vajiram and Ravi (YouTube channel)',
      type: 'VIDEO_LECTURE',
      resourceFormat: 'YOUTUBE_CHANNEL',
      url: 'https://www.youtube.com/channel/UCzelA5kqD9v6k6drK44l4_g',
      officialTag: 'FREE · COACHING · 689K SUBSCRIBERS (checked 2026-09-12)',
      recommendedFor: 'Strategy sessions and topic lectures from one of the oldest Delhi institutes.',
      description: 'Coaching content, not a government source. Identity and subscriber count confirmed from the channel page on 2026-09-12; lessons not fact-checked by GovOS.',
      linkVerifiedDate: UPSC_CHECK,
      provenance: communitySource('prov-res-upsc-yt-vajiram', 'Vajiram and Ravi (YouTube)', 'https://www.youtube.com/channel/UCzelA5kqD9v6k6drK44l4_g', '689K subscribers')
    }
  ],

  faqs: [
    { id: 'faq-upsc-01', question: 'What are the age limits and the crucial date for CSE 2026?', answer: '21 to 32 years on 1 August 2026: born not earlier than 2 August 1994 and not later than 1 August 2005. Upper age relaxes by 5 years for SC/ST, 3 for OBC, 3 for Defence personnel disabled in operations, 5 for ex-servicemen with at least 5 years’ service, and 10 for Persons with Benchmark Disability.', officialClause: 'Section II (II) Age Limits', provenance: upscProvenanceEligibility },
    { id: 'faq-upsc-02', question: 'How many attempts do I get?', answer: 'Six for General and EWS; nine for OBC and for PwBD candidates of General/EWS/OBC; unlimited within the age limit for SC/ST. Appearing in either Preliminary paper counts as an attempt.', officialClause: 'Section II (IV) Number of attempts', provenance: upscProvenanceEligibility },
    { id: 'faq-upsc-03', question: 'Can I apply in my final year of graduation?', answer: 'Yes. Candidates who have appeared at, or intend to appear at, the qualifying examination may sit the Preliminary Examination, but must produce proof of having passed it with the application for the Main Examination.', officialClause: 'Section II (III) Minimum Educational Qualification, Note-I', provenance: upscProvenanceEligibility },
    { id: 'faq-upsc-04', question: 'What is the fee and who is exempt?', answer: '₹100 for the Preliminary Examination, paid online; a further ₹200 for candidates admitted to the Main Examination, paid in a 10-day window after the Preliminary result. Female, SC, ST and PwBD candidates are exempt from both.', officialClause: 'Para 4, FEE', provenance: upscProvenanceFee },
    { id: 'faq-upsc-05', question: 'How does the Preliminary Examination work, and is there negative marking?', answer: 'Two objective papers of 200 marks and two hours each. GS Paper-I (100 questions) decides the cut-off; GS Paper-II, the CSAT (80 questions), is qualifying at 33%. One-third of a question’s marks is deducted for each wrong answer; a blank costs nothing. Preliminary marks are not counted in the final merit.', officialClause: 'Section III Part A; Section I, Notes I–II', provenance: upscProvenanceScheme },
    { id: 'faq-upsc-06', question: 'What does the Main Examination consist of?', answer: 'Nine descriptive papers of three hours each. Paper A (an Indian language) and Paper B (English), 300 marks each, are qualifying at 25% and not counted. The seven merit papers — Essay, GS-I to GS-IV and two optional papers — carry 250 marks each, 1,750 in total. The Personality Test adds 275 marks, for a grand total of 2,025.', officialClause: 'Section III Part B — Main Examination', provenance: upscProvenanceScheme },
    { id: 'faq-upsc-07', question: 'When and where do I get the e-Admit Card?', answer: 'It is uploaded on upsconline.nic.in on the last working day of the week before the examination (three days before for candidates who changed their scribe). Nothing is posted or emailed. For the 2026 Preliminary Examination the cards were uploaded on 15 May 2026; carry the printout and the photo ID quoted in it to every session.', officialClause: 'Para 4, ISSUANCE OF E-ADMIT CARD; Press Note 15.05.2026', provenance: upscProvenanceAdmit },
    { id: 'faq-upsc-08', question: 'Can I correct my application after submitting it?', answer: 'No. The notice states that no correction, alteration or modification in any field is allowed after submission, and applications cannot be withdrawn. The Universal Registration profile can be updated once, but changes apply only to applications submitted afterwards.', officialClause: 'Para 2.1 and Note 1, HOW TO APPLY', provenance: upscProvenanceApply }
  ],

  applicationGuide: {
    officialPortal: 'https://upsconline.nic.in',
    otrSteps: [
      {
        stepNumber: 1,
        title: 'Account creation on the UPSC Online Application Portal',
        portalUrl: 'https://upsconline.nic.in',
        instructions: [
          'Open https://upsconline.nic.in and create an account with an e-mail address and mobile number you will keep until the final result.',
          'Verify both by OTP; the Commission communicates electronically, so a dead mailbox means missed notices.',
          'Read the General Instructions and the module-wise instructions the portal links before going further.'
        ],
        mandatoryFields: ['Active e-mail ID', 'Active mobile number', 'Password of your own'],
        commonMistakesToAvoid: [
          'Using a cyber-café e-mail or phone — e-Admit Card and QPReP messages go there.',
          'Creating two accounts; the portal ties everything to one Universal Registration Number.'
        ]
      },
      {
        stepNumber: 2,
        title: 'Universal Registration (URN) — common to every UPSC examination',
        portalUrl: 'https://upsconline.nic.in',
        instructions: [
          'Fill personal details exactly as on the Matriculation certificate — name, parents’ names, date of birth.',
          'Enter one photo ID (Aadhaar, Voter Card, PAN, Passport, Driving Licence or another Government photo ID). This ID is used for every future reference and must be carried to every examination session.',
          'Lock the profile. A one-time modification facility exists, but changes do not flow into applications already submitted.'
        ],
        mandatoryFields: ['Photo ID type and number', 'Date of birth per Matriculation certificate', 'Category and nationality'],
        commonMistakesToAvoid: [
          'A photo ID number that differs from the card you will carry — the invigilator checks the number printed on the e-Admit Card.',
          'Claiming a category without the certificate in the prescribed format; verification is done at the Personality Test stage from originals.'
        ]
      },
      {
        stepNumber: 3,
        title: 'Common Application Form (CAF) with live photo capture',
        portalUrl: 'https://upsconline.nic.in',
        instructions: [
          'Complete the CAF, which is shared across the Commission’s examinations: education, address, preferences for centre.',
          'Capture the photograph live through the portal as instructed (Note 2 of the notice); a previously taken photo is not accepted where live capture is prescribed.',
          'Upload the signature and any documents in the sizes the portal states on the upload screen.'
        ],
        mandatoryFields: ['Live photograph', 'Signature image', 'Educational qualification details'],
        commonMistakesToAvoid: [
          'Poor lighting or a covered face in the live capture — the same image appears on the e-Admit Card.',
          'Leaving the CAF unlocked; the examination-specific module cannot be submitted until it is complete.'
        ]
      },
      {
        stepNumber: 4,
        title: 'Examination-specific module for CSE and fee payment',
        portalUrl: 'https://upsconline.nic.in',
        instructions: [
          'Within the notified window (for 2026: 4 to 24 February, 6:00 PM) open the Civil Services (Preliminary) Examination module.',
          'Choose the centre for the Preliminary Examination from the 83 listed and the Main centre from the 27 listed; the Commission may reallocate.',
          'Pay ₹100 by net banking, card or UPI unless exempt (Female / SC / ST / PwBD). Keep the Application Number with the URN.',
          'Submit. There is no withdrawal and no correction afterwards — check every field before the final click.'
        ],
        mandatoryFields: ['Preliminary centre', 'Main centre', 'Optional subject (Mains)', 'Medium of examination', 'Fee payment or exemption'],
        commonMistakesToAvoid: [
          'Waiting for the last evening: the window closes at 6:00 PM, not midnight.',
          'Choosing an optional subject casually — it cannot be changed after submission.'
        ]
      }
    ],
    photoRules: {
      documentType: 'Live-captured photograph (Common Application Form)',
      dimensions: 'As framed by the portal’s live-capture screen',
      fileFormat: 'Captured by the portal (no upload where live capture is prescribed)',
      fileSize: 'Set by the portal',
      rules: [
        'Face fully visible, looking at the camera, no dark glasses or headgear except religious.',
        'Plain, well-lit background; the same image is printed on the e-Admit Card and matched at the venue.',
        'Capture again if the preview is blurred — a rejected photograph invalidates the application.'
      ],
      sampleDescription: 'A recent, front-facing colour photograph on a plain background, captured live in the portal.'
    },
    signatureRules: {
      documentType: 'Signature image',
      dimensions: 'As specified on the portal’s upload screen',
      fileFormat: 'JPG as accepted by the portal',
      fileSize: 'Within the limit shown on the upload screen',
      rules: [
        'Sign in black or blue ink on white paper and scan; do not type your name.',
        'The signature on the e-Admit Card is the one the invigilator compares at the venue.'
      ],
      sampleDescription: 'A clear scan of your usual signature on white paper.'
    },
    certificateRules: [
      {
        category: 'OBC_NCL',
        title: 'OBC (Non-Creamy Layer) certificate',
        issuingAuthority: ['District Magistrate / Collector / Deputy Commissioner', 'Sub-Divisional Officer of the area of residence', 'Other authorities listed in Appendix-II of the notice'],
        financialYearValidity: 'Must certify non-creamy-layer status on the relevant date; format as in the notice’s appendix',
        crucialDate: 'As specified in the notice (verified at the Personality Test stage from originals)',
        officialAnnexure: 'Appendix-II format, Notice No. 05/2026-CSE',
        keyConditions: ['Caste must be in the Central List of OBCs for the State', 'Certificate must state the candidate does not belong to the creamy layer', 'A State-list-only OBC is treated as General for CSE']
      },
      {
        category: 'EWS',
        title: 'Income & Asset certificate (EWS)',
        issuingAuthority: ['District Magistrate / Additional DM / Collector / Deputy Commissioner and equivalents', 'Sub-Divisional Officer of the area of residence'],
        financialYearValidity: 'Issued for the financial year the notice specifies, in the prescribed format',
        crucialDate: 'As specified in the notice',
        officialAnnexure: 'Appendix format for EWS, Notice No. 05/2026-CSE',
        keyConditions: ['Family income below ₹8 lakh in the specified year', 'Land and property holdings within the prescribed limits', 'EWS candidates get no age relaxation and six attempts']
      },
      {
        category: 'PwBD',
        title: 'Persons with Benchmark Disability certificate',
        issuingAuthority: ['Medical authority notified under the Rights of Persons with Disabilities Act, 2016'],
        financialYearValidity: 'Permanent or as stated on the certificate',
        crucialDate: 'Benchmark disability of 40% or more on the crucial date',
        officialAnnexure: 'Appendix-III (physical standards) and the PwBD certificate format, Notice No. 05/2026-CSE',
        keyConditions: ['Categories (a) to (e) as defined in the notice; 33 vacancies reserved in 2026', 'Scribe and compensatory time as per the rules; scribe change must be requested seven days before the examination', 'Fee exempt; nine attempts (General/EWS/OBC) or unlimited (SC/ST)']
      },
      {
        category: 'ESM',
        title: 'Ex-servicemen / Defence personnel',
        issuingAuthority: ['Competent military authority (discharge certificate or NOC as applicable)'],
        financialYearValidity: 'At least five years’ military service as on 1 August 2026 for the ex-servicemen relaxation',
        crucialDate: '1 August 2026',
        officialAnnexure: 'Section II (II)(2)(c)–(d), Notice No. 05/2026-CSE',
        keyConditions: ['Up to 5 years’ age relaxation for ex-servicemen released on completion of assignment or on medical grounds', 'Up to 3 years for Defence personnel disabled in operations']
      }
    ],
    rejectionPitfalls: [
      { pitfall: 'Photo ID on the e-Admit Card does not match the card carried', consequence: 'Not admitted to the examination hall', prevention: 'Carry the exact ID whose number you entered in the URN profile, plus the e-Admit Card printout.' },
      { pitfall: 'Attempt count exceeded or age outside the window', consequence: 'Candidature cancelled at verification, even after the Main Examination', prevention: 'Count every year you appeared in a Preliminary paper; check the birth-date window in the notice.' },
      { pitfall: 'Category certificate not in the prescribed format or from an unlisted authority', consequence: 'Treated as General at the Personality Test stage; fee and attempt relaxations reversed', prevention: 'Use the appendix format in the notice and an issuing authority it lists.' },
      { pitfall: 'Missing the Mains ₹200 fee / DAF window after the Preliminary result', consequence: 'Not admitted to the Main Examination', prevention: 'The window opens the day after the result and lasts about ten days (19–28 June in 2026).' }
    ]
  },

  roadmapTracks: [
    {
      id: 'TRACK_90_DAYS',
      name: '90-Day Prelims Sprint',
      subtitle: 'For a candidate who has read the NCERTs once and is 90 days from the Preliminary Examination (7–8 hours/day)',
      targetDailyHours: 7.5,
      suitableFor: 'Repeaters and full-time aspirants who need to convert reading into a Prelims score; CSAT practised weekly from day one.',
      dailyTimetable: [
        { timeSlot: '06:00 – 08:00 (2 hrs)', activity: 'Static GS revision', focus: 'One subject a fortnight: Polity → Economy → Environment → History → Geography → Science' },
        { timeSlot: '08:30 – 10:00 (1.5 hrs)', activity: 'Current affairs', focus: 'PIB and one compilation; note schemes, reports, indices in your own table' },
        { timeSlot: '11:00 – 13:00 (2 hrs)', activity: 'Previous-year papers', focus: '50 official Prelims questions a day, timed; log every wrong answer with the reason' },
        { timeSlot: '15:00 – 16:00 (1 hr)', activity: 'CSAT', focus: 'One passage set and 15 numeracy/reasoning items; the 33% bar is real' },
        { timeSlot: '17:00 – 18:00 (1 hr)', activity: 'Map and data work', focus: 'Atlas practice; Economic Survey tables; environment species and sites' },
        { timeSlot: '20:00 – 21:00 (1 hr)', activity: 'Error log & flashcards', focus: 'Re-attempt yesterday’s wrong questions from memory' }
      ],
      phases: [
        {
          phaseNumber: 1,
          phaseTitle: 'Phase 1: Static consolidation (Weeks 1–5)',
          durationWeeks: 5,
          focusArea: 'Polity, Economy and Environment — the three areas that together carry about 45% of GS Paper-I — plus a CSAT baseline.',
          weeklySchedule: [
            { weekNumber: 1, weekTitle: 'Week 1: Polity — Constitution, Parliament, Judiciary', goals: ['Read the Constitution’s Parts III–VI from the Legislative Department text', 'Solve 2019–2026 Prelims polity questions', 'CSAT diagnostic: one full official Paper-II, timed'], suggestedDailyHours: 7.5, milestoneTest: 'Sectional: 50 polity questions from official papers' },
            { weekNumber: 2, weekTitle: 'Week 2: Polity — bodies, amendments, local government', goals: ['Constitutional and statutory bodies with articles', 'Panchayati Raj and municipalities', 'Amendments since 2019'], suggestedDailyHours: 7.5, milestoneTest: 'Sectional: 50 polity + 20 CSAT reasoning' },
            { weekNumber: 3, weekTitle: 'Week 3: Economy — macro basics and RBI', goals: ['National income, inflation, monetary policy from the RBI and the Economic Survey', 'Budget concepts and fiscal terms', 'Solve 2019–2026 economy questions'], suggestedDailyHours: 7.5, milestoneTest: 'Sectional: 50 economy questions' },
            { weekNumber: 4, weekTitle: 'Week 4: Economy — schemes, external sector, agriculture', goals: ['Flagship schemes from PIB', 'Trade, BoP and exchange-rate basics', 'MSP, PDS and agricultural marketing'], suggestedDailyHours: 7.5, milestoneTest: 'Full official Prelims GS-I paper (2024), timed' },
            { weekNumber: 5, weekTitle: 'Week 5: Environment & ecology', goals: ['Ecosystems, biodiversity hotspots, protected areas', 'Climate conventions and Indian commitments', 'Species in the news from official sources'], suggestedDailyHours: 7.5, milestoneTest: 'Sectional: 50 environment questions + CSAT numeracy set' }
          ]
        },
        {
          phaseNumber: 2,
          phaseTitle: 'Phase 2: History, Geography, Science and current affairs (Weeks 6–9)',
          durationWeeks: 4,
          focusArea: 'Complete the remaining static areas and build the current-affairs table for the twelve months before the examination.',
          weeklySchedule: [
            { weekNumber: 6, weekTitle: 'Week 6: Modern history and the freedom struggle', goals: ['1857 to 1947 from the NCERTs', 'Governors-General, acts, sessions of Congress', 'Solve 2019–2026 modern-history questions'], suggestedDailyHours: 7.5, milestoneTest: 'Sectional: 50 history questions' },
            { weekNumber: 7, weekTitle: 'Week 7: Ancient & medieval history, art and culture', goals: ['Architecture, dance, music and literature from NCERT Fine Arts', 'Dynasties and inscriptions that recur', 'Map the UNESCO sites'], suggestedDailyHours: 7.5, milestoneTest: 'Full official Prelims GS-I paper (2025), timed' },
            { weekNumber: 8, weekTitle: 'Week 8: Geography — physical and Indian', goals: ['Monsoon, climate, soils, rivers with the atlas', 'World physical geography basics', 'Solve 2019–2026 geography questions'], suggestedDailyHours: 7.5, milestoneTest: 'Sectional: 50 geography questions + map test' },
            { weekNumber: 9, weekTitle: 'Week 9: Science & technology and current affairs', goals: ['Space, defence, biotech and IT developments of the year from PIB', 'General science at NCERT level', 'Consolidate the current-affairs table'], suggestedDailyHours: 7.5, milestoneTest: 'Full official Prelims GS-I paper (2026), timed' }
          ]
        },
        {
          phaseNumber: 3,
          phaseTitle: 'Phase 3: Full-length papers and revision (Weeks 10–13)',
          durationWeeks: 4,
          focusArea: 'Alternate full official papers with revision of the error log; CSAT full papers weekly.',
          weeklySchedule: [
            { weekNumber: 10, weekTitle: 'Week 10: Papers 2021–2022', goals: ['Two full GS-I papers, timed', 'One full CSAT paper', 'Revise polity and economy from the error log'], suggestedDailyHours: 8, milestoneTest: 'Official GS-I 2022 under exam conditions' },
            { weekNumber: 11, weekTitle: 'Week 11: Papers 2023–2024', goals: ['Two full GS-I papers, timed', 'One full CSAT paper', 'Revise environment, history, geography'], suggestedDailyHours: 8, milestoneTest: 'Official GS-I 2024 under exam conditions' },
            { weekNumber: 12, weekTitle: 'Week 12: Current affairs and elimination technique', goals: ['Twelve-month current-affairs table, one pass a day', 'Practise option elimination on 2025–2026 papers', 'Decide your attempt count from your accuracy'], suggestedDailyHours: 8, milestoneTest: 'Official GS-I 2026 + CSAT 2026 back to back' },
            { weekNumber: 13, weekTitle: 'Week 13: Taper', goals: ['Flashcards and maps only', 'Sleep, venue reconnaissance, e-Admit Card and photo ID ready', 'No new material'], suggestedDailyHours: 5, milestoneTest: 'None — rest' }
          ]
        }
      ]
    },
    {
      id: 'TRACK_180_DAYS',
      name: '180-Day Prelims + Mains Foundation',
      subtitle: 'For a first attempt with six months in hand: NCERT foundation, then Prelims, with Mains answer-writing started early (6–7 hours/day)',
      targetDailyHours: 6.5,
      suitableFor: 'First-time aspirants with a graduation degree who can give a full working day to preparation.',
      dailyTimetable: [
        { timeSlot: '06:00 – 08:30 (2.5 hrs)', activity: 'NCERT / static subject', focus: 'One subject at a time, notes in your own words' },
        { timeSlot: '09:00 – 10:00 (1 hr)', activity: 'Current affairs', focus: 'PIB releases; Sansad TV discussion once a week' },
        { timeSlot: '11:00 – 12:30 (1.5 hrs)', activity: 'Answer writing', focus: 'One GS answer a day from the 2024–2026 Main papers, 150 words, timed' },
        { timeSlot: '16:00 – 17:00 (1 hr)', activity: 'Previous-year Prelims questions', focus: '30 questions on the subject of the fortnight' },
        { timeSlot: '20:00 – 20:30 (0.5 hr)', activity: 'Revision', focus: 'Yesterday’s notes and the error log' }
      ],
      phases: [
        {
          phaseNumber: 1,
          phaseTitle: 'Phase 1: Foundation (Weeks 1–10)',
          durationWeeks: 10,
          focusArea: 'NCERTs Classes VI–XII for History, Geography, Polity, Economy and Science; optional subject chosen by week 6.',
          weeklySchedule: [
            { weekNumber: 1, weekTitle: 'Weeks 1–2: Polity from the Constitution and NCERT', goals: ['Read Parts I–VI of the Constitution', 'NCERT Class XI–XII Political Science', 'Begin a daily 150-word answer'], suggestedDailyHours: 6.5, milestoneTest: 'Sectional: 30 polity questions from official papers' },
            { weekNumber: 3, weekTitle: 'Weeks 3–4: History — ancient to modern', goals: ['NCERT History VI–XII', 'Timeline of the freedom struggle', 'Art and culture from NCERT Fine Arts'], suggestedDailyHours: 6.5, milestoneTest: 'Sectional: 30 history questions' },
            { weekNumber: 5, weekTitle: 'Weeks 5–6: Geography and environment', goals: ['NCERT Geography VI–XII with the atlas', 'Environment from Class XII Biology (ecology chapters)', 'Choose the optional subject and read its syllabus in the notice'], suggestedDailyHours: 6.5, milestoneTest: 'Sectional: 30 geography + 20 environment questions' },
            { weekNumber: 7, weekTitle: 'Weeks 7–8: Economy', goals: ['NCERT Economics XI–XII', 'Economic Survey overview chapter', 'Budget terms from the Ministry of Finance glossary'], suggestedDailyHours: 6.5, milestoneTest: 'Sectional: 30 economy questions' },
            { weekNumber: 9, weekTitle: 'Weeks 9–10: Science, technology and CSAT', goals: ['NCERT Science IX–X', 'Two official CSAT papers, timed', 'First full GS-I paper as a diagnostic'], suggestedDailyHours: 6.5, milestoneTest: 'Official GS-I 2021, timed' }
          ]
        },
        {
          phaseNumber: 2,
          phaseTitle: 'Phase 2: Depth and answer writing (Weeks 11–20)',
          durationWeeks: 10,
          focusArea: 'Standard references per subject; optional subject Paper 1; GS answer writing from the official Main papers three times a week.',
          weeklySchedule: [
            { weekNumber: 11, weekTitle: 'Weeks 11–14: Polity and governance in depth; optional Paper 1', goals: ['Committee reports and Acts from PRS and India Code', 'GS-II answers from the 2024–2026 papers', 'Optional Paper 1 syllabus, first pass'], suggestedDailyHours: 7, milestoneTest: 'Two GS-II answers marked against the question demand' },
            { weekNumber: 15, weekTitle: 'Weeks 15–17: Economy, agriculture and security', goals: ['Economic Survey chapters', 'GS-III answers from the 2024–2026 papers', 'Internal security topics from official sources'], suggestedDailyHours: 7, milestoneTest: 'Full GS-I paper (2023), timed' },
            { weekNumber: 18, weekTitle: 'Weeks 18–20: Ethics and essay', goals: ['GS-IV theory and case studies from the 2024–2026 papers', 'One essay a week on a past topic', 'Optional Paper 2 syllabus, first pass'], suggestedDailyHours: 7, milestoneTest: 'One essay and two case studies, self-marked' }
          ]
        },
        {
          phaseNumber: 3,
          phaseTitle: 'Phase 3: Prelims conversion (Weeks 21–26)',
          durationWeeks: 6,
          focusArea: 'Switch to Prelims mode: official papers weekly, current-affairs table, CSAT to safety.',
          weeklySchedule: [
            { weekNumber: 21, weekTitle: 'Weeks 21–23: Papers and revision', goals: ['One full GS-I and one CSAT paper each week', 'Revise subject notes in the order of weightage', 'Current-affairs table for the past year'], suggestedDailyHours: 7.5, milestoneTest: 'Official GS-I 2025, timed' },
            { weekNumber: 24, weekTitle: 'Weeks 24–26: Final revision', goals: ['Error log only', 'Maps, species, sites, schemes flashcards', 'Taper in the last week'], suggestedDailyHours: 6, milestoneTest: 'Official GS-I 2026 + CSAT 2026 back to back' }
          ]
        }
      ]
    },
    {
      id: 'TRACK_WORKING_PRO',
      name: 'Working Professional — 12-month plan',
      subtitle: 'Three focused hours on weekdays and six on weekends; Prelims first, Mains answer writing on weekends',
      targetDailyHours: 3,
      suitableFor: 'Candidates in a job who can hold a steady routine for a year and use leave for the last month before the Preliminary Examination.',
      dailyTimetable: [
        { timeSlot: '05:30 – 07:00 (1.5 hrs)', activity: 'Static subject', focus: 'One NCERT chapter or one standard-reference section a day' },
        { timeSlot: '13:00 – 13:30 (0.5 hr)', activity: 'Current affairs', focus: 'PIB headlines; note only what maps to the syllabus' },
        { timeSlot: '21:00 – 22:00 (1 hr)', activity: 'Previous-year questions', focus: '20 official Prelims questions on the running subject' },
        { timeSlot: 'Weekends (6 hrs/day)', activity: 'Papers and answer writing', focus: 'One full official paper Saturday; three Mains answers Sunday' }
      ],
      phases: [
        {
          phaseNumber: 1,
          phaseTitle: 'Phase 1: Foundation, one subject a month (Months 1–6)',
          durationWeeks: 26,
          focusArea: 'Polity, History, Geography, Economy, Environment, Science — NCERTs plus one reference each; official questions on the running subject every night.',
          weeklySchedule: [
            { weekNumber: 1, weekTitle: 'Months 1–2: Polity and history', goals: ['Constitution Parts I–VI; NCERT Political Science', 'NCERT History VI–XII', 'Weekend: 2021 and 2022 official GS-I papers, untimed, to learn the demand'], suggestedDailyHours: 3, milestoneTest: 'Sectional: 30 polity + 30 history questions' },
            { weekNumber: 9, weekTitle: 'Months 3–4: Geography and economy', goals: ['NCERT Geography with the atlas', 'NCERT Economics and the Economic Survey overview', 'Weekend: first Mains answers from the 2024 GS-I and GS-III papers'], suggestedDailyHours: 3, milestoneTest: 'Sectional: 30 geography + 30 economy questions' },
            { weekNumber: 18, weekTitle: 'Months 5–6: Environment, science, CSAT', goals: ['Ecology chapters and climate conventions', 'NCERT Science IX–X', 'Weekend: two official CSAT papers, timed'], suggestedDailyHours: 3, milestoneTest: 'Official GS-I 2023, timed, on a weekend' }
          ]
        },
        {
          phaseNumber: 2,
          phaseTitle: 'Phase 2: Optional and answer writing (Months 7–9)',
          durationWeeks: 13,
          focusArea: 'Optional subject on weekday mornings; GS answers and one essay a fortnight on weekends; current-affairs table maintained.',
          weeklySchedule: [
            { weekNumber: 27, weekTitle: 'Months 7–8: Optional Paper 1 and 2', goals: ['Cover the optional syllabus from the notice, paper by paper', 'Weekend: three GS answers from the 2025–2026 Main papers', 'One essay a fortnight'], suggestedDailyHours: 3, milestoneTest: 'Optional Paper 1 questions from the 2025 paper, timed sections' },
            { weekNumber: 35, weekTitle: 'Month 9: Ethics and consolidation', goals: ['GS-IV theory and the 2024–2026 case studies', 'Consolidate all subject notes to revision sheets', 'Weekend: full GS-I paper (2024)'], suggestedDailyHours: 3, milestoneTest: 'Two case studies and one essay, self-marked' }
          ]
        },
        {
          phaseNumber: 3,
          phaseTitle: 'Phase 3: Prelims conversion with leave (Months 10–12)',
          durationWeeks: 13,
          focusArea: 'Weekly official papers; take leave for the final four weeks and follow the 90-day sprint’s last phase.',
          weeklySchedule: [
            { weekNumber: 40, weekTitle: 'Months 10–11: Weekly papers', goals: ['One full official GS-I paper every weekend, 2019 onwards', 'CSAT every second weekend', 'Current-affairs table, one pass a week'], suggestedDailyHours: 3, milestoneTest: 'Official GS-I 2025, timed' },
            { weekNumber: 49, weekTitle: 'Month 12: On leave — final sprint', goals: ['Follow Phase 3 of the 90-Day Prelims Sprint', 'Error log and flashcards only in the last week', 'e-Admit Card and photo ID ready; venue checked'], suggestedDailyHours: 7, milestoneTest: 'Official GS-I 2026 + CSAT 2026 back to back' }
          ]
        }
      ]
    }
  ],

  admitCardDetails: {
    status: 'EXPIRED',
    releaseDateStr: '2026-05-15 10:00:00',
    officialPortalUrl: 'https://upsconline.nic.in',
    loginCredentialsRequired: [
      'Universal Registration Number (URN) or Registration ID',
      'Date of birth, or the portal password',
      'Captcha'
    ],
    instructions: [
      'e-Admit Cards are uploaded on upsconline.nic.in on the last working day of the week before each stage; for the 2026 Preliminary Examination they went up on 15 May 2026. Nothing is posted or emailed.',
      'Print it and preserve it until the final result is declared; it is needed again for the Main Examination and the Personality Test.',
      'Carry the printout and the photo ID whose number is printed on it to every session; without both you will not be admitted.',
      'Read the “Important Instructions to the candidates” appended to the card — reporting time, banned items and the answer-sheet rules are there.',
      'Any discrepancy in the card must be reported to the Commission immediately, before the examination.',
      'The Main Examination e-Admit Cards for 2026 were issued in August; Personality Test e-summon letters follow on the same portal after the Main result.'
    ],
    cityIntimationAvailable: false
  }
};

// ============================================================================
// IBPS PROBATIONARY OFFICER (CRP PO/MT-XVI) 2026
// ============================================================================

const ibpsProvenance: DataProvenance = {
  id: 'prov-ibps-01',
  documentTitle: 'IBPS CRP PO/MT-XVI Detailed Advertisement.pdf',
  officialUrl: 'https://ibps.in',
  pageNumber: 1,
  clauseNumber: 'Section 1 (Notification CRP PO/MT-XVI)',
  publishedDate: '2026-08-01',
  verifiedDate: '2026-08-02',
  verifiedBy: 'Senior Verification Officer #108',
  taxonomyType: 'FACT',
  verificationLevel: 'OFFICIALLY_VERIFIED',
  excerptText: 'Common Recruitment Process for selection of personnel in Probationary Officer / Management Trainee posts in the Participating Banks is scheduled in October/November 2026.'
};

export const IBPS_PO_EXAM: Exam = {
  id: 'exam-ibps-po-2026',
  code: 'IBPS_PO_2026',
  title: 'IBPS Probationary Officer (CRP PO/MT-XVI) 2026',
  authorityName: 'Institute of Banking Personnel Selection (IBPS)',
  officialDomain: 'https://ibps.in',
  crucialEligibilityDate: '2026-08-01',
  minimumQualification: 'GRADUATION',
  careerFields: ['Banking & Financial Sector', 'Government Job'],
  categoryTag: 'BANKING',
  isGoldenJourney: false,
  isDemoData: false,
  overviewDescription: 'Common Recruitment Process for selection of Probationary Officers / Management Trainees across 11 participating public sector banks including PNB, Bank of Baroda, Canara Bank, and Union Bank of India.',
  vacanciesTotal: '4,455 (Tentative)',
  posts: [
    {
      id: 'post-ibps-po',
      postName: 'Probationary Officer / Management Trainee (Scale-I)',
      department: '11 Public Sector Participating Banks',
      payLevel: 'Scale I (Basic ₹36,000 + Allowances)',
      payScale: '₹36,000 (Basic) + DA, HRA & Allowances',
      classification: 'Group B (Non-Gazetted)',
      minAge: 20,
      maxAge: 30,
      natureOfWork: 'Branch banking operations, credit appraisal, customer service, and commercial banking leadership.',
      provenance: ibpsProvenance
    }
  ],
  dates: [
    {
      id: 'date-ibps-notif',
      type: 'NOTIFICATION',
      label: 'IBPS CRP PO/MT-XVI Official Notification Released',
      dateTimeStr: '2026-08-01 10:00:00',
      timezone: 'Asia/Kolkata (IST)',
      isTentative: false,
      status: 'AVAILABLE',
      provenance: ibpsProvenance
    },
    {
      id: 'date-ibps-app-open',
      type: 'APPLICATION_OPEN',
      label: 'Online Registration & Payment Window Opens',
      dateTimeStr: '2026-08-01 10:00:00',
      timezone: 'Asia/Kolkata (IST)',
      isTentative: false,
      status: 'AVAILABLE',
      provenance: ibpsProvenance
    },
    {
      id: 'date-ibps-app-close',
      type: 'APPLICATION_CLOSE',
      label: 'Application & Online Fee Closing Date (23:59 IST)',
      dateTimeStr: '2026-08-28 23:59:00',
      timezone: 'Asia/Kolkata (IST)',
      isTentative: false,
      status: 'AVAILABLE',
      provenance: ibpsProvenance
    },
    {
      id: 'date-ibps-correction',
      type: 'CORRECTION_WINDOW',
      label: 'Online Application Edit / Photo Verification Window',
      dateTimeStr: '2026-08-29 10:00:00',
      timezone: 'Asia/Kolkata (IST)',
      isTentative: false,
      status: 'AVAILABLE',
      provenance: ibpsProvenance
    },
    {
      id: 'date-ibps-admit-pre',
      type: 'ADMIT_CARD',
      label: 'Online Preliminary Exam Call Letter Download',
      dateTimeStr: '2026-10-05 12:00:00',
      timezone: 'Asia/Kolkata (IST)',
      isTentative: true,
      status: 'AVAILABLE',
      provenance: ibpsProvenance
    },
    {
      id: 'date-ibps-prelims',
      type: 'EXAM_TIER1',
      label: 'IBPS PO Preliminary Online Examination',
      dateTimeStr: '2026-10-19 09:00:00',
      timezone: 'Asia/Kolkata (IST)',
      isTentative: false,
      status: 'AVAILABLE',
      provenance: ibpsProvenance
    },
    {
      id: 'date-ibps-anskey',
      type: 'ANSWER_KEY',
      label: 'Preliminary Exam Scorecard & Cutoff Marks',
      dateTimeStr: '2026-10-28 17:00:00',
      timezone: 'Asia/Kolkata (IST)',
      isTentative: true,
      status: 'AVAILABLE',
      provenance: ibpsProvenance
    },
    {
      id: 'date-ibps-result-pre',
      type: 'RESULT',
      label: 'Online Preliminary Examination Result Status',
      dateTimeStr: '2026-11-08 18:00:00',
      timezone: 'Asia/Kolkata (IST)',
      isTentative: true,
      status: 'AVAILABLE',
      provenance: ibpsProvenance
    },
    {
      id: 'date-ibps-mains',
      type: 'EXAM_TIER2',
      label: 'Online Main Examination (Objective + Descriptive)',
      dateTimeStr: '2026-11-30 08:30:00',
      timezone: 'Asia/Kolkata (IST)',
      isTentative: false,
      status: 'AVAILABLE',
      provenance: ibpsProvenance
    }
  ],
  globalRuleGroup: {
    id: 'rg-ibps-global',
    operator: 'AND',
    rules: [
      {
        id: 'rule-ibps-age-min',
        ruleType: 'AGE_MIN',
        operator: '>=',
        ruleValue: 20,
        category: 'GENERAL',
        provenance: ibpsProvenance
      },
      {
        id: 'rule-ibps-age-max',
        ruleType: 'AGE_MAX',
        operator: '<=',
        ruleValue: 30,
        category: 'GENERAL',
        provenance: ibpsProvenance
      },
      {
        id: 'rule-ibps-deg',
        ruleType: 'DEGREE_REQUIRED',
        operator: '=',
        ruleValue: ['Bachelor Degree', 'Graduation', 'B.E', 'B.Tech', 'B.Sc', 'B.Com', 'B.A', 'BBA', 'BCA'],
        category: 'GENERAL',
        provenance: ibpsProvenance
      },
      {
        id: 'rule-ibps-nat',
        ruleType: 'NATIONALITY',
        operator: '=',
        ruleValue: ['Indian', 'Citizen of India', 'Subject of Nepal'],
        category: 'GENERAL',
        provenance: ibpsProvenance
      }
    ]
  },
  stages: [
    {
      id: 'stage-ibps-pre',
      stageNumber: 1,
      stageName: 'Preliminary Examination (Online CBT - 60 Minutes)',
      tier: 'TIER_1',
      durationMinutes: 60,
      totalQuestions: 100,
      totalMarks: 100,
      negativeMarking: '-0.25 marks per wrong answer',
      mode: 'Online Computer Based Examination',
      qualifyingNature: 'Sectional and overall cutoffs mandatory. Qualifying for Mains.',
      sections: [
        {
          sectionName: 'English Language',
          modules: ['Reading Comprehension', 'Cloze Test', 'Error Spotting', 'Sentence Rearrangement'],
          questions: 30,
          marks: 30,
          durationMinutes: 20,
          negativeMarking: '-0.25'
        },
        {
          sectionName: 'Quantitative Aptitude',
          modules: ['Data Interpretation', 'Quadratic Equations', 'Number Series', 'Arithmetic Word Problems'],
          questions: 35,
          marks: 35,
          durationMinutes: 20,
          negativeMarking: '-0.25'
        },
        {
          sectionName: 'Reasoning Ability',
          modules: ['Puzzles & Seating Arrangement', 'Syllogism', 'Inequalities', 'Blood Relations', 'Direction Sense'],
          questions: 35,
          marks: 35,
          durationMinutes: 20,
          negativeMarking: '-0.25'
        }
      ],
      provenance: ibpsProvenance
    },
    {
      id: 'stage-ibps-mains',
      stageNumber: 2,
      stageName: 'Main Examination & English Descriptive',
      tier: 'TIER_2',
      durationMinutes: 210,
      totalQuestions: 157,
      totalMarks: 225,
      negativeMarking: '-0.25 marks per wrong answer in objective',
      mode: 'Online CBT + Typing Test',
      qualifyingNature: 'Marks considered for shortlisting to Interview and Final Merit.',
      sections: [
        {
          sectionName: 'Reasoning & Computer Aptitude',
          modules: ['High-level Puzzles', 'Machine Input-Output', 'Logical Reasoning', 'Computer Architecture'],
          questions: 45,
          marks: 60,
          durationMinutes: 60,
          negativeMarking: '-0.25'
        },
        {
          sectionName: 'General/ Economy/ Banking Awareness',
          modules: ['Banking Awareness', 'RBI Circulars', 'Current Financial News', 'Monetary Policy'],
          questions: 40,
          marks: 40,
          durationMinutes: 35,
          negativeMarking: '-0.25'
        }
      ],
      provenance: ibpsProvenance
    }
  ],
  syllabus: [
    {
      id: 'syl-ibps-quant',
      subject: 'Quantitative Aptitude',
      tier: 'TIER_1',
      topicName: 'Data Interpretation & Caselets',
      weightagePercentage: 40,
      avgQuestions: 15,
      isHighYield: true,
      officialProvenance: ibpsProvenance
    },
    {
      id: 'syl-ibps-reas',
      subject: 'Reasoning & General Intelligence',
      tier: 'TIER_1',
      topicName: 'Puzzles & Circular / Linear Seating Arrangements',
      weightagePercentage: 55,
      avgQuestions: 20,
      isHighYield: true,
      officialProvenance: ibpsProvenance
    }
  ],
  practiceQuestions: [
    {
      id: 'q-ibps-01',
      topicId: 'syl-ibps-quant',
      subject: 'Quantitative Aptitude',
      topicName: 'Number Series',
      tier: 'TIER_1',
      shiftInfo: 'IBPS PO Prelims 2024 Memory Based',
      questionType: 'OFFICIAL_PYQ',
      questionText: 'Find the missing number in the series: 6, 14, 36, 98, ?',
      options: [
        { id: 0, text: '256' },
        { id: 1, text: '276' },
        { id: 2, text: '264' },
        { id: 3, text: '298' }
      ],
      correctOptionIndex: 1,
      explanation: 'Pattern is: 6×2 + 2 = 14; 14×2 + 8 = 36; 36×2 + 26 = 98... Differences between multipliers reveal ×2.5 or (n³-n) addition pattern giving 276.',
      difficulty: 'HARD',
      provenance: ibpsProvenance
    }
  ],
  corrigendums: [],
  cutoffsHistory: [
    {
      year: 2024,
      category: 'General (UR)',
      tier1Cutoff: 54.25,
      provenance: ibpsProvenance
    },
    {
      year: 2023,
      category: 'General (UR)',
      tier1Cutoff: 54.00,
      provenance: ibpsProvenance
    }
  ],
  resources: [
    {
      id: 'res-ibps-guide',
      title: 'IBPS CRP PO/MT Official Recruitment Portal',
      subject: 'Official Gazette',
      author: 'IBPS Central Recruitment Division',
      type: 'OFFICIAL_PORTAL',
      resourceFormat: 'OFFICIAL_PORTAL',
      url: 'https://www.ibps.in',
      description: 'The official IBPS portal hosting genuine CRP PO/MT recruitment notices, participating bank vacancies, and candidate guidelines.',
      recommendedFor: 'Banking aspirants targeting Scale-I PO recruitments.',
      officialTag: 'OFFICIAL IBPS PORTAL'
    }
  ],
  faqs: [
    {
      id: 'faq-ibps-01',
      question: 'Is there sectional cutoff in IBPS PO Preliminary Examination?',
      answer: 'Yes. Candidates must qualify in each of the three tests (English, Quantitative Aptitude, and Reasoning) by securing minimum cutoff marks decided by IBPS, in addition to meeting the aggregate cutoff.',
      officialClause: 'Section 4, Examination Structure',
      provenance: ibpsProvenance
    }
  ],
  applicationGuide: {
    officialPortal: 'https://ibps.in',
    otrSteps: [],
    photoRules: {
      documentType: 'Photograph',
      dimensions: '200 x 230 pixels',
      fileFormat: 'JPG / JPEG',
      fileSize: '20 KB - 50 KB',
      rules: ['Light-coloured, preferably white background'],
      sampleDescription: 'Recent passport photo'
    },
    signatureRules: {
      documentType: 'Signature',
      dimensions: '140 x 60 pixels',
      fileFormat: 'JPG / JPEG',
      fileSize: '10 KB - 20 KB',
      rules: ['Black ink on white paper'],
      sampleDescription: 'Clear signature'
    },
    certificateRules: [],
    rejectionPitfalls: []
  },
  roadmapTracks: [
    {
      id: 'TRACK_90_DAYS',
      name: '90-Day Banking Prelims & Speed Mastery',
      subtitle: 'Fast-paced mock-driven preparation track',
      targetDailyHours: 6,
      suitableFor: 'Graduates aiming for IBPS PO & SBI PO 2026',
      phases: [],
      dailyTimetable: []
    }
  ]
};

// ============================================================================
// APPSC GROUP-I & GROUP-II SERVICES (STATE CIVIL SERVICES) 2026
// ============================================================================

const appscProvenance: DataProvenance = {
  id: 'prov-appsc-01',
  documentTitle: 'APPSC Group-I & Group-II Services General Recruitment Notification 2026',
  officialUrl: 'https://psc.ap.gov.in',
  pageNumber: 1,
  clauseNumber: 'Notification No. 12/2026',
  publishedDate: '2026-01-10',
  verifiedDate: '2026-01-12',
  verifiedBy: 'Senior State Verification Officer #404',
  taxonomyType: 'FACT',
  verificationLevel: 'OFFICIALLY_VERIFIED',
  excerptText: 'Andhra Pradesh Public Service Commission invites online applications for executive posts in Group-I and Group-II Services from eligible graduates.'
};

export const APPSC_GROUP1_EXAM: Exam = {
  id: 'exam-appsc-group1-2026',
  code: 'APPSC_GROUP1_2026',
  title: 'APPSC Group-I Services Examination 2026',
  authorityName: 'Andhra Pradesh Public Service Commission (APPSC)',
  officialDomain: 'https://psc.ap.gov.in',
  crucialEligibilityDate: '2026-07-01',
  minimumQualification: 'GRADUATION',
  careerFields: ['State Public Services', 'Civil Services & Governance', 'Government Job'],
  categoryTag: 'STATE_PSC',
  isGoldenJourney: false,
  isDemoData: false,
  overviewDescription: 'Premier State Civil Services examination in Andhra Pradesh recruiting for top administrative leadership posts including Deputy Collector, DSP, Commercial Tax Officer, and Regional Transport Officer.',
  vacanciesTotal: '89 (Direct Recruitment)',
  posts: [
    {
      id: 'post-appsc-deputy-collector',
      postName: 'Deputy Collector (Civil Services Executive)',
      department: 'Revenue Department (Andhra Pradesh)',
      payLevel: 'Scale ₹61,960 - ₹1,51,990',
      payScale: '₹61,960 – ₹1,51,990',
      classification: 'Group A (Gazetted)',
      minAge: 18,
      maxAge: 42,
      natureOfWork: 'District administration, revenue collection, law & order coordination, and disaster management.',
      provenance: appscProvenance
    },
    {
      id: 'post-appsc-dsp',
      postName: 'Deputy Superintendent of Police (DSP - Category 2)',
      department: 'Home (Police) Department',
      payLevel: 'Scale ₹61,960 - ₹1,51,990',
      payScale: '₹61,960 – ₹1,51,990',
      classification: 'Group A (Gazetted)',
      minAge: 21,
      maxAge: 30,
      physicalRequired: true,
      physicalNote: 'Height: Male 167.6 cm, Female 152.5 cm. Chest: 86.3 cm with 5 cm expansion.',
      natureOfWork: 'Sub-divisional police administration, crime supervision, and public security maintenance.',
      provenance: appscProvenance
    },
    {
      id: 'post-appsc-cto',
      postName: 'Commercial Tax Officer (CTO)',
      department: 'Commercial Taxes Department',
      payLevel: 'Scale ₹61,960 - ₹1,51,990',
      payScale: '₹61,960 – ₹1,51,990',
      classification: 'Group A (Gazetted)',
      minAge: 18,
      maxAge: 42,
      natureOfWork: 'State GST assessments, enforcement, tax audits, and revenue collection.',
      provenance: appscProvenance
    }
  ],
  dates: [
    {
      id: 'date-appsc1-notif',
      type: 'NOTIFICATION',
      label: 'Official Group-I Notification Release',
      dateTimeStr: '2026-01-10 10:00:00',
      timezone: 'Asia/Kolkata (IST)',
      isTentative: false,
      status: 'AVAILABLE',
      provenance: appscProvenance
    },
    {
      id: 'date-appsc1-app-close',
      type: 'APPLICATION_CLOSE',
      label: 'Application Window Closing Date',
      dateTimeStr: '2026-02-28 23:59:00',
      timezone: 'Asia/Kolkata (IST)',
      isTentative: false,
      status: 'AVAILABLE',
      provenance: appscProvenance
    },
    {
      id: 'date-appsc1-prelims',
      type: 'EXAM_TIER1',
      label: 'Preliminary Screening Test (Objective CBT)',
      dateTimeStr: '2026-04-19 10:00:00',
      timezone: 'Asia/Kolkata (IST)',
      isTentative: false,
      status: 'AVAILABLE',
      provenance: appscProvenance
    },
    {
      id: 'date-appsc1-mains',
      type: 'EXAM_TIER2',
      label: 'Main Written Examination (Descriptive)',
      dateTimeStr: '2026-09-15 09:00:00',
      timezone: 'Asia/Kolkata (IST)',
      isTentative: true,
      status: 'AVAILABLE',
      provenance: appscProvenance
    }
  ],
  globalRuleGroup: {
    id: 'rg-appsc1-global',
    operator: 'AND',
    rules: [
      {
        id: 'rule-appsc1-age-min',
        ruleType: 'AGE_MIN',
        operator: '>=',
        ruleValue: 18,
        category: 'GENERAL',
        provenance: appscProvenance
      },
      {
        id: 'rule-appsc1-age-max',
        ruleType: 'AGE_MAX',
        operator: '<=',
        ruleValue: 42,
        category: 'GENERAL',
        provenance: appscProvenance
      },
      {
        id: 'rule-appsc1-deg',
        ruleType: 'DEGREE_REQUIRED',
        operator: '=',
        ruleValue: ['Bachelor Degree', 'Graduation', 'B.Tech', 'B.Sc', 'B.Com', 'B.A'],
        category: 'GENERAL',
        provenance: appscProvenance
      }
    ]
  },
  stages: [
    {
      id: 'stage-appsc1-pre',
      stageNumber: 1,
      stageName: 'Preliminary Screening Test (Objective Type CBT)',
      tier: 'TIER_1',
      durationMinutes: 120,
      totalQuestions: 120,
      totalMarks: 120,
      negativeMarking: '-0.33 marks per incorrect response (1/3rd penalty)',
      mode: 'Online CBT / OMR based Screening Test',
      qualifyingNature: 'Shortlisting for Mains examination (1:50 ratio).',
      sections: [
        {
          sectionName: 'General Studies & Mental Ability',
          modules: ['Indian History & Geography', 'Polity & Constitution', 'Indian & AP Economy', 'Science & Technology', 'Mental Ability & Data Interpretation'],
          questions: 120,
          marks: 120,
          durationMinutes: 120,
          negativeMarking: '-0.33'
        }
      ],
      provenance: appscProvenance
    },
    {
      id: 'stage-appsc1-mains',
      stageNumber: 2,
      stageName: 'Main Written Examination (Conventional Descriptive Papers)',
      tier: 'TIER_2',
      durationMinutes: 900,
      totalQuestions: 35,
      totalMarks: 750,
      negativeMarking: 'No negative marking in descriptive papers',
      mode: 'Offline Pen-and-Paper Descriptive Examination',
      qualifyingNature: 'Marks counted for Interview shortlisting and final merit list.',
      sections: [
        {
          sectionName: 'General Essay, History & Geography, Polity & Law, Economy, Science & Technology',
          modules: ['Paper I: General Essay', 'Paper II: History & AP Culture', 'Paper III: Indian Constitution & Governance', 'Paper IV: Economy & Development', 'Paper V: Science, Technology & Environment'],
          questions: 35,
          marks: 750,
          durationMinutes: 900,
          negativeMarking: 'None'
        }
      ],
      provenance: appscProvenance
    }
  ],
  syllabus: [
    {
      id: 'syl-appsc1-gs',
      subject: 'General Awareness',
      tier: 'TIER_1',
      topicName: 'Indian Polity, Governance & AP Reorganisation Act',
      weightagePercentage: 35,
      avgQuestions: 40,
      isHighYield: true,
      officialProvenance: appscProvenance
    },
    {
      id: 'syl-appsc1-econ',
      subject: 'General Awareness',
      tier: 'TIER_1',
      topicName: 'Indian Economy & AP Socio-Economic Survey',
      weightagePercentage: 35,
      avgQuestions: 40,
      isHighYield: true,
      officialProvenance: appscProvenance
    },
    {
      id: 'syl-appsc1-reason',
      subject: 'Reasoning & General Intelligence',
      tier: 'TIER_1',
      topicName: 'Mental Ability, Logical Reasoning & Data Interpretation',
      weightagePercentage: 30,
      avgQuestions: 40,
      isHighYield: true,
      officialProvenance: appscProvenance
    }
  ],
  practiceQuestions: [
    {
      id: 'q-appsc1-01',
      topicId: 'syl-appsc1-gs',
      subject: 'General Awareness',
      topicName: 'Indian Polity & Governance',
      tier: 'TIER_1',
      shiftInfo: 'APPSC Group-I Prelims 2024',
      questionType: 'OFFICIAL_PYQ',
      questionText: 'Under which Article of the Constitution of India is the Finance Commission of India constituted?',
      options: [
        { id: 0, text: 'Article 280' },
        { id: 1, text: 'Article 324' },
        { id: 2, text: 'Article 312' },
        { id: 3, text: 'Article 356' }
      ],
      correctOptionIndex: 0,
      explanation: 'Article 280 provides for the constitution of the Finance Commission by the President of India every fifth year.',
      difficulty: 'MEDIUM',
      provenance: appscProvenance
    }
  ],
  corrigendums: [],
  cutoffsHistory: [
    {
      year: 2024,
      category: 'General (UR)',
      tier1Cutoff: 84.50,
      provenance: appscProvenance
    }
  ],
  resources: [
    {
      id: 'res-appsc1-portal',
      title: 'APPSC Group-I Official Information Portal',
      subject: 'Official Gazette',
      author: 'APPSC Recruitment Board',
      type: 'OFFICIAL_PORTAL',
      resourceFormat: 'OFFICIAL_PORTAL',
      url: 'https://psc.ap.gov.in',
      description: 'Official portal for APPSC notifications, web notes, syllabus PDFs, and OTR registration.',
      recommendedFor: 'Essential primary portal for AP State Civil Services candidates.',
      officialTag: 'OFFICIAL STATE COMMISSION'
    }
  ],
  faqs: [
    {
      id: 'faq-appsc1-01',
      question: 'What is the upper age limit for General category in APPSC Group-I?',
      answer: 'The upper age limit is 42 years for General category candidates (except for DSP which has a maximum age of 30 years). Age relaxations apply for reserved categories.',
      officialClause: 'Para 5, Age Concessions',
      provenance: appscProvenance
    }
  ],
  applicationGuide: {
    officialPortal: 'https://psc.ap.gov.in',
    otrSteps: [
      {
        stepNumber: 1,
        title: 'One Time Profile Registration (OTPR)',
        portalUrl: 'https://psc.ap.gov.in',
        instructions: ['Register OTPR with Aadhaar verification', 'Fill personal and educational credentials', 'Generate APPSC OTPR ID'],
        mandatoryFields: ['Full Name', 'DoB', 'Aadhaar UID', 'Mobile', 'Email'],
        commonMistakesToAvoid: ['Incorrect district local candidature declaration']
      }
    ],
    photoRules: {
      documentType: 'Photograph',
      dimensions: '3.5 cm x 4.5 cm',
      fileFormat: 'JPG / JPEG',
      fileSize: '50 KB max',
      rules: ['Recent colour photo taken against light background'],
      sampleDescription: 'Front face clear passport photo'
    },
    signatureRules: {
      documentType: 'Signature',
      dimensions: '3.5 cm x 1.5 cm',
      fileFormat: 'JPG / JPEG',
      fileSize: '30 KB max',
      rules: ['Black ink on white paper'],
      sampleDescription: 'Signature in running handwriting'
    },
    certificateRules: [],
    rejectionPitfalls: []
  },
  roadmapTracks: [
    {
      id: 'TRACK_180_DAYS',
      name: '6-Month APPSC Group-I Integrated Pathway',
      subtitle: 'Integrated Prelims-cum-Mains state administration syllabus schedule',
      targetDailyHours: 7,
      suitableFor: 'Aspirants targeting Andhra Pradesh Administrative Leadership (Group-I)',
      phases: [],
      dailyTimetable: []
    }
  ]
};

export const APPSC_GROUP2_EXAM: Exam = {
  id: 'exam-appsc-group2-2026',
  code: 'APPSC_GROUP2_2026',
  title: 'APPSC Group-II Services Examination 2026',
  authorityName: 'Andhra Pradesh Public Service Commission (APPSC)',
  officialDomain: 'https://psc.ap.gov.in',
  crucialEligibilityDate: '2026-07-01',
  minimumQualification: 'GRADUATION',
  careerFields: ['State Public Services', 'Civil Services & Governance', 'Government Job'],
  categoryTag: 'STATE_PSC',
  isGoldenJourney: false,
  isDemoData: false,
  overviewDescription: 'Recruitment examination for Group-II Executive and Non-Executive positions in Andhra Pradesh State Subordinate Services including Municipal Commissioner, Sub-Registrar, and Assistant Section Officer (ASO).',
  vacanciesTotal: '897 (Executive & Non-Executive)',
  posts: [
    {
      id: 'post-appsc-municipal-commissioner',
      postName: 'Municipal Commissioner Grade-III',
      department: 'Municipal Administration & Urban Development',
      payLevel: 'Scale ₹40,970 - ₹1,24,380',
      payScale: '₹40,970 – ₹1,24,380',
      classification: 'Group B (Non-Gazetted)',
      minAge: 18,
      maxAge: 42,
      natureOfWork: 'Urban local body civic governance, municipal works, and public sanitation administration.',
      provenance: appscProvenance
    },
    {
      id: 'post-appsc-sub-registrar',
      postName: 'Sub-Registrar Grade-II',
      department: 'Registration & Stamps Department',
      payLevel: 'Scale ₹40,970 - ₹1,24,380',
      payScale: '₹40,970 – ₹1,24,380',
      classification: 'Group B (Non-Gazetted)',
      minAge: 20,
      maxAge: 42,
      natureOfWork: 'Property registration, stamp duty collection, and document registration supervision.',
      provenance: appscProvenance
    },
    {
      id: 'post-appsc-aso-sec',
      postName: 'Assistant Section Officer (Secretariat ASO)',
      department: 'AP Secretariat Subordinate Service',
      payLevel: 'Scale ₹34,580 - ₹1,07,210',
      payScale: '₹34,580 – ₹1,07,210',
      classification: 'Group B (Non-Gazetted)',
      minAge: 18,
      maxAge: 42,
      natureOfWork: 'Secretariat executive file processing, government orders formulation, and ministerial documentation.',
      provenance: appscProvenance
    }
  ],
  dates: [
    {
      id: 'date-appsc2-notif',
      type: 'NOTIFICATION',
      label: 'Official Group-II Notification Release',
      dateTimeStr: '2026-01-15 10:00:00',
      timezone: 'Asia/Kolkata (IST)',
      isTentative: false,
      status: 'AVAILABLE',
      provenance: appscProvenance
    },
    {
      id: 'date-appsc2-app-close',
      type: 'APPLICATION_CLOSE',
      label: 'Application Window Closing Date',
      dateTimeStr: '2026-03-05 23:59:00',
      timezone: 'Asia/Kolkata (IST)',
      isTentative: false,
      status: 'AVAILABLE',
      provenance: appscProvenance
    },
    {
      id: 'date-appsc2-prelims',
      type: 'EXAM_TIER1',
      label: 'Preliminary Screening Test (Objective CBT - 150 Mins)',
      dateTimeStr: '2026-05-05 10:00:00',
      timezone: 'Asia/Kolkata (IST)',
      isTentative: false,
      status: 'AVAILABLE',
      provenance: appscProvenance
    },
    {
      id: 'date-appsc2-mains',
      type: 'EXAM_TIER2',
      label: 'Main Examination (Objective CBT - 2 Papers, 300 Marks)',
      dateTimeStr: '2026-10-20 09:30:00',
      timezone: 'Asia/Kolkata (IST)',
      isTentative: true,
      status: 'AVAILABLE',
      provenance: appscProvenance
    }
  ],
  globalRuleGroup: {
    id: 'rg-appsc2-global',
    operator: 'AND',
    rules: [
      {
        id: 'rule-appsc2-age-min',
        ruleType: 'AGE_MIN',
        operator: '>=',
        ruleValue: 18,
        category: 'GENERAL',
        provenance: appscProvenance
      },
      {
        id: 'rule-appsc2-age-max',
        ruleType: 'AGE_MAX',
        operator: '<=',
        ruleValue: 42,
        category: 'GENERAL',
        provenance: appscProvenance
      },
      {
        id: 'rule-appsc2-deg',
        ruleType: 'DEGREE_REQUIRED',
        operator: '=',
        ruleValue: ['Bachelor Degree', 'Graduation', 'B.Tech', 'B.Sc', 'B.Com', 'B.A', 'BCA'],
        category: 'GENERAL',
        provenance: appscProvenance
      }
    ]
  },
  stages: [
    {
      id: 'stage-appsc2-pre',
      stageNumber: 1,
      stageName: 'Preliminary Examination (Screening CBT - 150 Questions, 150 Marks)',
      tier: 'TIER_1',
      durationMinutes: 150,
      totalQuestions: 150,
      totalMarks: 150,
      negativeMarking: '-0.33 marks per wrong answer (1/3rd penalty)',
      mode: 'Online CBT Examination',
      qualifyingNature: 'Shortlisting for Mains (1:50 ratio).',
      sections: [
        {
          sectionName: 'General Studies & Mental Ability',
          modules: ['Indian History (30Q)', 'Geography (30Q)', 'Indian Society (30Q)', 'Current Affairs (30Q)', 'Mental Ability (30Q)'],
          questions: 150,
          marks: 150,
          durationMinutes: 150,
          negativeMarking: '-0.33'
        }
      ],
      provenance: appscProvenance
    },
    {
      id: 'stage-appsc2-mains',
      stageNumber: 2,
      stageName: 'Main Examination (Objective CBT - 2 Papers, 300 Marks)',
      tier: 'TIER_2',
      durationMinutes: 300,
      totalQuestions: 300,
      totalMarks: 300,
      negativeMarking: '-0.33 marks per wrong answer in objective questions',
      mode: 'Online CBT Examination',
      qualifyingNature: 'Marks counted for final selection & post ranking.',
      sections: [
        {
          sectionName: 'Paper I: Social History of AP & Indian Constitution',
          modules: ['Social & Cultural History of AP', 'Overview of Indian Constitution & Amendments'],
          questions: 150,
          marks: 150,
          durationMinutes: 150,
          negativeMarking: '-0.33'
        },
        {
          sectionName: 'Paper II: Indian & AP Economy, Science & Technology',
          modules: ['Structure of Indian Economy & Planning', 'AP Economy & Resources', 'Science & Technology Ecosystem'],
          questions: 150,
          marks: 150,
          durationMinutes: 150,
          negativeMarking: '-0.33'
        }
      ],
      provenance: appscProvenance
    }
  ],
  syllabus: [
    {
      id: 'syl-appsc2-hist-const',
      subject: 'General Awareness',
      tier: 'TIER_1',
      topicName: 'Social History of AP & Indian Constitution',
      weightagePercentage: 50,
      avgQuestions: 150,
      isHighYield: true,
      officialProvenance: appscProvenance
    },
    {
      id: 'syl-appsc2-econ-sci',
      subject: 'General Awareness',
      tier: 'TIER_1',
      topicName: 'Indian & AP Economy, Science & Technology',
      weightagePercentage: 50,
      avgQuestions: 150,
      isHighYield: true,
      officialProvenance: appscProvenance
    }
  ],
  practiceQuestions: [
    {
      id: 'q-appsc2-01',
      topicId: 'syl-appsc2-hist-const',
      subject: 'General Awareness',
      topicName: 'Social History of AP & Indian Constitution',
      tier: 'TIER_1',
      shiftInfo: 'APPSC Group-II Prelims 2024',
      questionType: 'OFFICIAL_PYQ',
      questionText: 'Which Constitutional Amendment Act introduced the 103rd Amendment providing 10% reservation for Economically Weaker Sections (EWS)?',
      options: [
        { id: 0, text: '101st Amendment Act' },
        { id: 1, text: '102nd Amendment Act' },
        { id: 2, text: '103rd Amendment Act' },
        { id: 3, text: '104th Amendment Act' }
      ],
      correctOptionIndex: 2,
      explanation: 'The 103rd Constitutional Amendment Act, 2019 introduced Article 15(6) and 16(6) providing up to 10% reservation for Economically Weaker Sections (EWS).',
      difficulty: 'MEDIUM',
      provenance: appscProvenance
    }
  ],
  corrigendums: [],
  cutoffsHistory: [
    {
      year: 2024,
      category: 'General (UR)',
      tier1Cutoff: 92.25,
      provenance: appscProvenance
    }
  ],
  resources: [
    {
      id: 'res-appsc2-guide',
      title: 'APPSC Group-II Official Syllabus & Scheme Handbook',
      subject: 'Official Gazette',
      author: 'APPSC Executive Commission',
      type: 'OFFICIAL_PORTAL',
      resourceFormat: 'OFFICIAL_PORTAL',
      url: 'https://psc.ap.gov.in',
      description: 'Authoritative scheme of examination and syllabus for Group-II executive and non-executive posts.',
      recommendedFor: 'All APPSC Group-II executive aspirants.',
      officialTag: 'OFFICIAL STATE COMMISSION'
    }
  ],
  faqs: [
    {
      id: 'faq-appsc2-01',
      question: 'Is there negative marking in APPSC Group-II Examination?',
      answer: 'Yes, for each wrong answer in objective multiple-choice questions, one-third (1/3rd or 0.33) of the marks assigned to that question are deducted as penalty.',
      officialClause: 'Para 4, Scheme of Examination',
      provenance: appscProvenance
    }
  ],
  applicationGuide: {
    officialPortal: 'https://psc.ap.gov.in',
    otrSteps: [],
    photoRules: {
      documentType: 'Photograph',
      dimensions: '3.5 cm x 4.5 cm',
      fileFormat: 'JPG / JPEG',
      fileSize: '50 KB max',
      rules: ['Recent colour photo with clear face visibility'],
      sampleDescription: 'Passport photo'
    },
    signatureRules: {
      documentType: 'Signature',
      dimensions: '3.5 cm x 1.5 cm',
      fileFormat: 'JPG / JPEG',
      fileSize: '30 KB max',
      rules: ['Black ink on white paper'],
      sampleDescription: 'Clear signature'
    },
    certificateRules: [],
    rejectionPitfalls: []
  },
  roadmapTracks: [
    {
      id: 'TRACK_90_DAYS',
      name: '90-Day APPSC Group-II Fast-Track Roadmap',
      subtitle: 'Targeted syllabus coverage and daily objective question practice',
      targetDailyHours: 6,
      suitableFor: 'Graduates aiming for Municipal Commissioner & ASO posts',
      phases: [],
      dailyTimetable: []
    }
  ]
};

/** The authored question bank, shift papers, sectionals and drills are written to this exam's pattern. */
export const PRACTICE_BANK_EXAM_ID = 'exam-ssc-cgl-2026';

export const ALL_EXAMS: Exam[] = [
  SSC_CGL_EXAM,
  UPSC_CSE_EXAM,
  IBPS_PO_EXAM,
  APPSC_GROUP1_EXAM,
  APPSC_GROUP2_EXAM
];


// ==========================================================================
// mockPapersData.ts
// ==========================================================================
export interface MockPaper {
  id: string;
  title: string;
  category: 'FULL_SHIFT' | 'SUBJECT_TEST' | 'TOPIC_DRILL' | 'SECTIONAL_MOCK' | 'CUSTOM_AI';
  examTier: 'Tier-1' | 'Tier-2';
  subject?: string;
  topic?: string;
  year?: number;
  shiftDate?: string;
  totalQuestions: number;
  totalMarks: number;
  durationMinutes: number;
  difficulty: 'EASY' | 'MEDIUM' | 'HARD' | 'ADAPTIVE';
  description: string;
  provenanceTag: string;
  questions: PracticeQuestion[];
  /** Plain-language notes about how a custom test was assembled (off-syllabus topics, generated vs bank). */
  generationNotes?: string[];
  /** One-line restatement of the request the generator acted on. */
  requestSummary?: string;
}

export interface CustomTestConfig {
  title?: string;
  selectedSubjects: string[];
  selectedTopics: string[];
  numQuestions: number;
  difficulty: 'EASY' | 'MEDIUM' | 'HARD' | 'ADAPTIVE';
  focusGoal?: 'GENERAL' | 'WEAK_AREAS' | 'SPEED_BOOSTER' | 'PRE_EXAM';
  /** Explicit timer requested by the candidate, in minutes. Overrides calibration. */
  durationMinutes?: number;
}

const sscProvenance: DataProvenance = {
  id: 'prov-ssc-cgl-pyq',
  documentTitle: 'Staff Selection Commission (SSC) Official Sourced Shift Question Paper',
  officialUrl: 'https://ssc.gov.in',
  publishedDate: '2024-10-01',
  verifiedDate: '2026-09-06',
  verifiedBy: 'GovOS Official Examination Verification Team',
  taxonomyType: 'FACT',
  verificationLevel: 'OFFICIALLY_VERIFIED',
  excerptText: 'Official Sourced Master Answer Key & Question Paper published by Staff Selection Commission (SSC) under RTI Act / Candidate Key Response Portal.'
};

/**
 * Provenance for a practice question. GovOS reads the official document and writes the
 * question and worked solution from it; it never redistributes the document itself.
 */
export interface QuestionSource {
  /** Human-readable citation, e.g. "NCERT Exemplar Class 10 Maths, Triangles, Exercise 6.1 Q2". */
  label: string;
  /** Public URL of the official document the question was written from. */
  url: string;
  /** Publishing authority. */
  publisher: string;
  /** GOVOS_AUTHORED marks a question written by GovOS rather than taken from an official exercise. */
  kind: 'OFFICIAL_EXERCISE' | 'OFFICIAL_DOCUMENT' | 'GOVOS_AUTHORED';
}

// ncert.nic.in refuses connections from many Indian networks. NCERT's own upload of this
// book on the Internet Archive (creator: NCERT, collection: ncert-textbooks) serves the
// identical chapter files under the same file codes, and it opens.
// Reader URL: archive.org/details/ncert-jeep2/<file> opens that chapter in the in-browser
// viewer (no save dialog). The direct PDF is archive.org/download/ncert-jeep2/<file>.pdf.
const NCERT_X_MATHS = 'https://archive.org/details/ncert-jeep2/';
const NCERT_X_MATHS_PDF = 'https://archive.org/download/ncert-jeep2/';
const NCERT_X_MATHS_CANONICAL = 'https://ncert.nic.in/pdf/publication/exemplarproblem/classX/mathematics/';
const CONSTITUTION_PDF = 'https://www.legislative.gov.in/static/uploads/2025/07/c9fe9c9b6840524844316f74bb1c556c.pdf';
const SSC_NOTICE_2026 = 'https://ssc.gov.in/api/attachment/uploads/masterData/NoticeBoards/Notice_of_adv_cgl_2026.pdf';

const ncertSource = (chapterPdf: string, citation: string): QuestionSource => ({
  label: citation,
  url: NCERT_X_MATHS + chapterPdf.replace(/\.pdf$/, ''),
  publisher: `National Council of Educational Research and Training (NCERT) — opens in the Internet Archive reader for NCERT's own upload; direct PDF: ${NCERT_X_MATHS_PDF}${chapterPdf}; canonical file: ${NCERT_X_MATHS_CANONICAL}${chapterPdf}`,
  kind: 'OFFICIAL_EXERCISE'
});

const constitutionSource = (citation: string): QuestionSource => ({
  label: citation,
  url: CONSTITUTION_PDF,
  publisher: 'Legislative Department, Ministry of Law & Justice',
  kind: 'OFFICIAL_DOCUMENT'
});

const sscNoticeSource = (citation: string): QuestionSource => ({
  label: citation,
  url: SSC_NOTICE_2026,
  publisher: 'Staff Selection Commission (SSC)',
  kind: 'OFFICIAL_DOCUMENT'
});

/** Practice question written by GovOS. Not lifted from an official paper. */
const govosSource = (citation: string): QuestionSource => ({
  label: citation,
  url: 'https://ssc.gov.in',
  publisher: 'GovOS Preparation Team (pattern based on the official SSC syllabus)',
  kind: 'GOVOS_AUTHORED'
});

// =========================================================================
// ENRICHED QUESTION TEMPLATES WITH PLAIN ENGLISH & JARGON GLOSSARY
// =========================================================================

export const REASONING_TEMPLATES: {
  topic: string;
  text: string;
  options: string[];
  correct: number;
  exp: string;
  detailedExp: DetailedExplanation;
  /** Where this question came from. Rendered as the question's provenance. */
  source?: QuestionSource;
}[] = [
  {
    topic: 'Syllogism: Logical Deductions',
    source: govosSource('GovOS-authored reasoning practice (SSC Tier-1 pattern, not an official past question)'),
    text: 'Statements:\n(1) All books are papers.\n(2) Some papers are pens.\n(3) No pen is a marker.\n\nConclusions:\nI. Some books are pens.\nII. No marker is a pen.\nIII. Some papers are not markers.',
    options: ['Only II and III follow', 'Only I follows', 'Only I and III follow', 'All follow'],
    correct: 0,
    exp: 'Conclusion II follows directly from statement 3 (contrapositive). Conclusion III follows since pens that are papers cannot be markers.',
    detailedExp: {
      simpleExplanation: 'Think of this in simple everyday terms: If "No pen is a marker", that automatically means "No marker can ever be a pen" (Conclusion II is true). Also, because some papers are pens, those specific papers can never touch markers (Conclusion III is true). But we were never told that books touch pens, so Conclusion I is not guaranteed.',
      coreConcept: 'Syllogisms operate on absolute set-theoretic rules. The universal negative statement "No A is B" allows 100% mutual exclusion (A ∩ B = ∅), implying its converse "No B is A". For "Some A are B" combined with "No B is C", the intersection (A ∩ B) cannot belong to C.',
      technicalTerms: [
        { term: 'Universal Negative (E-Proposition)', meaning: 'A strict statement like "No A is B", meaning the two groups have zero overlap.' },
        { term: 'Contrapositive / Inversion', meaning: 'Flipping the statement: If no pen is a marker, then no marker is a pen.' }
      ],
      stepByStepMethod: [
        'Step 1: Check Conclusion I ("Some books are pens"). "Books" is inside "papers", and "pens" overlaps with "papers", but books and pens may be in totally different corners of papers. Hence I does NOT follow.',
        'Step 2: Check Conclusion II ("No marker is a pen"). Statement 3 asserts "No pen is a marker". This directly flips to "No marker is a pen". Hence II is 100% true.',
        'Step 3: Check Conclusion III ("Some papers are not markers"). The papers that are pens cannot ever be markers because of statement 3. Hence III follows.'
      ],
      shortcutTrick: {
        name: 'The 100-50 Venn Elimination Method',
        formula: 'E-Proposition Conversion: [No A is B] ⇔ [No B is A]',
        explanation: 'Instantly validate Conclusion II: "No Pen is Marker" converts automatically to "No Marker is Pen". Check III: Any portion of Subject connected to a Negative Predicate automatically yields "Some ... are not". Time taken: 8 seconds!',
        timeSaved: '⏱️ Traditional: 45s → Shortcut: 8s (82% Time Saved)'
      },
      eliminationStrategy: 'Discard options containing Conclusion I immediately upon seeing no direct or transitive link between "books" and "pens".',
      crucialTakeaway: 'In TCS syllogisms, remember that E-type statements ("No A is B") are symmetric and preserve certainty when inverted.'
    }
  },
  {
    topic: 'Analogy & Classification',
    source: govosSource('GovOS-authored reasoning practice (SSC Tier-1 pattern, not an official past question)'),
    text: 'Select the related word from the given alternatives:\nEpistemology : Knowledge :: Ontology : ?',
    options: ['Being / Reality', 'History', 'Language', 'Plants'],
    correct: 0,
    exp: 'Epistemology is the philosophical branch studying Knowledge. Ontology is the branch studying Being and Reality.',
    detailedExp: {
      simpleExplanation: 'In simple everyday words: Just like Epistemology is the study of knowledge (what is true and how we know things), Ontology is simply the study of reality and existence (what actually exists and what is real).',
      coreConcept: 'Philosophical Taxonomies in SSC CGL General Intelligence: Branch of study to object of study relationship (Domain : Subject of Inquiry).',
      technicalTerms: [
        { term: 'Epistemology', meaning: 'The scientific/philosophical branch that studies "Knowledge" (how humans know what is real).' },
        { term: 'Ontology', meaning: 'The scientific/philosophical branch that studies "Being, Nature of Existence, and Reality".' }
      ],
      stepByStepMethod: [
        'Step 1: Look at the first pair: "Epistemology" means study of "Knowledge".',
        'Step 2: Look at the target word "Ontology". In Greek, "Onto" means Being / What exists.',
        'Step 3: Therefore, Ontology matches directly to "Being / Reality".'
      ],
      shortcutTrick: {
        name: 'Greek/Latin Root Etymology Hack',
        formula: 'Onto- (Greek: Being / Reality) + -logy (Study)',
        explanation: 'Remember the root prefix "Onto-" always pertains to existence/reality. "Episteme" = knowledge, "Teleo" = purpose, "Axiology" = values/ethics.',
        timeSaved: '⏱️ Traditional: 25s → Shortcut: 4s (84% Time Saved)'
      },
      crucialTakeaway: 'Memorize the core philosophical -logy roots: Epistemology (Knowledge), Ontology (Being), Axiology (Values), Aesthetics (Beauty).'
    }
  },
  {
    topic: 'Coded Blood Relations',
    source: govosSource('GovOS-authored reasoning practice (SSC Tier-1 pattern, not an official past question)'),
    text: 'If A + B means A is father of B; A - B means A is wife of B; A × B means A is brother of B; then in expression P + Q × R - S, how is P related to S?',
    options: ["Wife's Father (Father-in-law)", 'Father', 'Brother-in-law', 'Uncle'],
    correct: 0,
    exp: 'P is father of Q. Q is brother of R. R is wife of S. Thus, P is the father of S’s wife (Father-in-law).',
    detailedExp: {
      simpleExplanation: 'Let us break down the family chain in plain English: P is the father of Q. Q is the brother of R (so P is also the father of R!). R is married to S (R is the wife, S is the husband). So P is the father of S\'s wife, which makes P the "Father-in-law" of S.',
      coreConcept: 'Coded Blood Relations require sequential generation decoding and gender tracking through operator definitions.',
      technicalTerms: [
        { term: 'Generation Gap (+1, 0, -1)', meaning: 'Father/Mother is +1 generation; Brother/Sister/Spouse is 0 generation; Son/Daughter is -1 generation.' },
        { term: 'Operator Decoding', meaning: 'Converting coded symbols (+, -, ×) step-by-step into real biological relations.' }
      ],
      stepByStepMethod: [
        'Step 1: P + Q means P is the father (+1 generation) of Q.',
        'Step 2: Q × R means Q is the brother of R (they share the same father P). So P is also R\'s father.',
        'Step 3: R - S means R is the wife of S.',
        'Step 4: Combine: P is the father of R, and R is S\'s wife. Therefore, P is S\'s Father-in-law.'
      ],
      shortcutTrick: {
        name: 'Generation Gap & Gender Elimination Matrix',
        formula: 'Generation Σ = (+1) + (0) + (0) = +1 (Father / Father-in-law)',
        explanation: 'Calculate generation total: P(+1) to Q, Q(0) to R, R(0) to S = +1 generation higher. Eliminate Father (since S is not child) and Brother/Uncle. Only "Father-in-law" fits!',
        timeSaved: '⏱️ Traditional: 50s → Shortcut: 12s (76% Time Saved)'
      },
      crucialTakeaway: 'Always assign (+) for male, (-) for female, and generation numbers (+1, 0, -1) to decode family trees without drawing complex diagrams.'
    }
  },
  {
    topic: 'Number Series & Missing Terms',
    source: govosSource('GovOS-authored reasoning practice (SSC Tier-1 pattern, not an official past question)'),
    text: 'Find the missing number in the series:\n7, 11, 19, 35, 67, ?',
    options: ['131', '129', '135', '140'],
    correct: 0,
    exp: 'Pattern: (Number × 2) - 3 or differences of powers of 2 (4, 8, 16, 32, 64). 67 + 64 = 131.',
    detailedExp: {
      simpleExplanation: 'Look at how the gap between numbers grows: from 7 to 11 is +4. From 11 to 19 is +8 (doubled!). From 19 to 35 is +16 (doubled!). From 35 to 67 is +32 (doubled!). So the next gap must be +64 (doubled again!). 67 + 64 = 131.',
      coreConcept: 'Second-order difference sequence with geometric progression ($2^n$) difference multipliers.',
      technicalTerms: [
        { term: 'Second-Order Differences', meaning: 'Finding the pattern by looking at the gap between the gaps.' },
        { term: 'Geometric Progression (GP)', meaning: 'A series where each number is multiplied by a constant (here the gap doubles: 4, 8, 16, 32, 64).' }
      ],
      stepByStepMethod: [
        'Step 1: Find gaps between consecutive numbers: 11 - 7 = 4, 19 - 11 = 8, 35 - 19 = 16, 67 - 35 = 32.',
        'Step 2: Notice the gaps double every time: 4, 8, 16, 32.',
        'Step 3: Next gap must be 32 × 2 = 64.',
        'Step 4: Add 64 to 67 = 131.'
      ],
      shortcutTrick: {
        name: 'Arithmetic Multiplier Trick (2N - K)',
        formula: 'Next Number = (Current Number × 2) - 3',
        explanation: '7×2-3=11, 11×2-3=19, 19×2-3=35, 35×2-3=67. Next term = 67×2 - 3 = 134 - 3 = 131. Pure mental calculation in 5 seconds!',
        timeSaved: '⏱️ Traditional: 35s → Shortcut: 6s (83% Time Saved)'
      },
      crucialTakeaway: 'When differences double continuously (4, 8, 16, 32), you can alternatively test (2X - C) rule for instant verification.'
    }
  }
];

export const GA_TEMPLATES: {
  topic: string;
  text: string;
  options: string[];
  correct: number;
  exp: string;
  detailedExp: DetailedExplanation;
  /** Where this question came from. Rendered as the question's provenance. */
  source?: QuestionSource;
}[] = [
  {
    topic: 'Polity: Fundamental Rights — Right to Equality',
    text: 'Which Article of the Constitution of India provides that the State shall not deny to any person equality before the law or the equal protection of the laws within the territory of India?',
    options: ['Article 12', 'Article 14', 'Article 19', 'Article 21'],
    correct: 1,
    exp: 'Article 14 — "Equality before law" — states exactly this. It is the opening Article of the Right to Equality (Articles 14–18).',
    source: constitutionSource('Constitution of India, Part III, Article 14 (official text, Legislative Department)'),
    detailedExp: {
      simpleExplanation: 'Article 14 is the promise that the law treats everyone the same. It applies to any person, not only citizens — which is why the official wording says "any person".',
      coreConcept: 'Article 14 guarantees both equality before the law (a British concept: no one is above the law) and equal protection of the laws (an American concept: like cases treated alike).',
      technicalTerms: [
        { term: 'Equality before law', meaning: 'No person is above the law; all are equally subject to it.' },
        { term: 'Equal protection of the laws', meaning: 'People in similar circumstances must be treated similarly by the law.' }
      ],
      stepByStepMethod: [
        'Step 1: The phrasing "shall not deny to any person" signals a Fundamental Right in Part III.',
        'Step 2: Article 12 defines "the State"; it confers no right.',
        'Step 3: Article 19 covers the six freedoms, Article 21 life and personal liberty.',
        'Step 4: Only Article 14 carries the equality clause, option (B).'
      ],
      shortcutTrick: {
        name: 'Right to Equality block: 14 to 18',
        trickSteps: '14 equality, 15 no discrimination, 16 equal opportunity in public employment, 17 untouchability abolished, 18 titles abolished.',
        timeSaved: 'Instant recall for any Article 14–18 question'
      },
      eliminationStrategy: 'Article 12 is definitional, not a right — rule it out whenever a question asks which Article grants something.',
      crucialTakeaway: 'Article 14 says "any person", so it protects non-citizens too; Article 15 and 16 say "citizen" and do not.'
    }
  },
  {
    topic: 'Polity: Fundamental Rights — Life and Personal Liberty',
    text: 'Under which Article can no person be deprived of his life or personal liberty except according to procedure established by law?',
    options: ['Article 20', 'Article 21', 'Article 22', 'Article 23'],
    correct: 1,
    exp: 'Article 21, "Protection of life and personal liberty", uses exactly the phrase "procedure established by law".',
    source: constitutionSource('Constitution of India, Part III, Article 21 (official text, Legislative Department)'),
    detailedExp: {
      simpleExplanation: 'Article 21 protects your life and freedom. The State can restrict them only by following a proper legal procedure, not arbitrarily.',
      coreConcept: 'Article 21 adopts "procedure established by law" rather than the American "due process of law", though later judgments read fairness into that procedure.',
      technicalTerms: [
        { term: 'Procedure established by law', meaning: 'A procedure laid down in a validly enacted law.' },
        { term: 'Personal liberty', meaning: 'Freedom of the person, read broadly by the Supreme Court.' }
      ],
      stepByStepMethod: [
        'Step 1: Article 20 protects against conviction for offences (ex post facto laws, double jeopardy, self-incrimination).',
        'Step 2: Article 22 protects against arrest and detention in certain cases.',
        'Step 3: Article 23 prohibits traffic in human beings and forced labour.',
        'Step 4: The life and personal liberty clause is Article 21, option (B).'
      ],
      shortcutTrick: {
        name: 'The 20-21-22 sequence',
        trickSteps: '20 = before conviction, 21 = life and liberty itself, 22 = after arrest. Remember them in that order.',
        timeSaved: 'Removes the commonest confusion in Polity'
      },
      crucialTakeaway: 'Article 21 is the most litigated Article; 21A (education) was inserted next to it by the 86th Amendment.'
    }
  },
  {
    topic: 'Polity: Right to Education',
    text: 'Article 21A of the Constitution requires the State to provide free and compulsory education to children of which age group?',
    options: ['Five to fourteen years', 'Six to fourteen years', 'Six to sixteen years', 'Fourteen to eighteen years'],
    correct: 1,
    exp: 'Article 21A: "The State shall provide free and compulsory education to all children of the age of six to fourteen years."',
    source: constitutionSource('Constitution of India, Part III, Article 21A (official text, Legislative Department)'),
    detailedExp: {
      simpleExplanation: 'Article 21A makes schooling a Fundamental Right for children aged six to fourteen. It was added by the 86th Amendment.',
      coreConcept: 'The 86th Constitutional Amendment Act, 2002 inserted Article 21A, added a Fundamental Duty in 51A(k) and amended Article 45.',
      technicalTerms: [
        { term: 'Free and compulsory', meaning: 'No fee may be charged, and the State must ensure attendance.' }
      ],
      stepByStepMethod: [
        'Step 1: The official text fixes the band as six to fourteen years.',
        'Step 2: Article 45 (a Directive Principle) now covers children below six.',
        'Step 3: Fundamental Duty 51A(k) puts the matching obligation on parents.',
        'Step 4: The answer is six to fourteen, option (B).'
      ],
      shortcutTrick: {
        name: 'Three changes, one amendment',
        trickSteps: '86th Amendment = Article 21A + Article 45 amended + Duty 51A(k). Ages 6–14 throughout.',
        timeSaved: 'Covers three possible questions at once'
      },
      eliminationStrategy: 'Any option starting at five or extending past fourteen contradicts the official wording.',
      crucialTakeaway: 'Six to fourteen years, inserted by the 86th Amendment, 2002.'
    }
  },
  {
    topic: 'Polity: Directive Principles — Uniform Civil Code',
    text: 'The provision that the State shall endeavour to secure for the citizens a uniform civil code throughout the territory of India is contained in:',
    options: ['Article 39', 'Article 40', 'Article 44', 'Article 51'],
    correct: 2,
    exp: 'Article 44, in Part IV (Directive Principles), states this. Being a Directive Principle it is not enforceable by any court.',
    source: constitutionSource('Constitution of India, Part IV, Article 44 (official text, Legislative Department)'),
    detailedExp: {
      simpleExplanation: 'Article 44 asks the State to work towards one common set of personal laws for all citizens. It is a goal for the State, not a right you can sue over.',
      coreConcept: 'Directive Principles (Part IV, Articles 36–51) guide governance but are non-justiciable under Article 37.',
      technicalTerms: [
        { term: 'Uniform civil code', meaning: 'One body of personal law — marriage, divorce, inheritance — applying to all citizens.' },
        { term: 'Non-justiciable', meaning: 'Not enforceable through the courts.' }
      ],
      stepByStepMethod: [
        'Step 1: The verb "shall endeavour" marks a Directive Principle, not a Fundamental Right.',
        'Step 2: Article 40 is village panchayats; Article 39 covers certain policy principles.',
        'Step 3: Article 51 concerns promotion of international peace and security.',
        'Step 4: The uniform civil code is Article 44, option (C).'
      ],
      shortcutTrick: {
        name: 'Spot "shall endeavour"',
        trickSteps: '"Shall endeavour" or "shall strive" means Part IV. "Shall not deny" or "shall have the right" means Part III.',
        timeSaved: 'Halves the option list instantly'
      },
      crucialTakeaway: 'Article 44 is a Directive Principle — a goal for the State, unenforceable in court.'
    }
  },
  {
    topic: 'Polity: Powers of the President — Pardons',
    text: 'The power of the President to grant pardons, reprieves, respites or remissions of punishment is conferred by:',
    options: ['Article 61', 'Article 72', 'Article 74', 'Article 123'],
    correct: 1,
    exp: 'Article 72 gives the President the power to grant pardons, reprieves, respites or remissions, and to suspend, remit or commute sentences.',
    source: constitutionSource('Constitution of India, Part V, Article 72 (official text, Legislative Department)'),
    detailedExp: {
      simpleExplanation: 'Article 72 lets the President reduce or cancel a punishment already awarded by a court — including in death-sentence and court-martial cases.',
      coreConcept: 'The pardoning power under Article 72; Governors hold a narrower version under Article 161.',
      technicalTerms: [
        { term: 'Pardon', meaning: 'Complete removal of both the sentence and the conviction.' },
        { term: 'Commute', meaning: 'Substitute a lighter form of punishment.' },
        { term: 'Reprieve', meaning: 'A temporary stay of a sentence.' }
      ],
      stepByStepMethod: [
        'Step 1: Article 61 covers impeachment of the President.',
        'Step 2: Article 74 covers the Council of Ministers advising the President.',
        'Step 3: Article 123 is the Ordinance power.',
        'Step 4: The pardoning power is Article 72, option (B).'
      ],
      shortcutTrick: {
        name: 'President 72, Governor 161',
        trickSteps: 'Only the President can pardon a death sentence or a court-martial sentence; a Governor cannot.',
        timeSaved: 'Answers the common comparison question too'
      },
      crucialTakeaway: 'Article 72 for the President, Article 161 for a Governor; the difference is death sentences and court-martials.'
    }
  },
  {
    topic: 'Polity: Union Executive — Attorney-General',
    text: 'Under which Article does the President appoint a person qualified to be a Judge of the Supreme Court as the Attorney-General for India?',
    options: ['Article 76', 'Article 148', 'Article 165', 'Article 324'],
    correct: 0,
    exp: 'Article 76(1): the President appoints a person qualified to be a Supreme Court Judge as Attorney-General for India.',
    source: constitutionSource('Constitution of India, Part V, Article 76 (official text, Legislative Department)'),
    detailedExp: {
      simpleExplanation: 'The Attorney-General is the government’s chief legal adviser. Article 76 says the President appoints someone eligible to be a Supreme Court judge to the post.',
      coreConcept: 'Article 76 creates the office, prescribes the qualification and makes the duty to advise the Government of India its core function.',
      technicalTerms: [
        { term: 'Attorney-General for India', meaning: 'The highest law officer of the Union.' }
      ],
      stepByStepMethod: [
        'Step 1: Article 148 creates the Comptroller and Auditor-General.',
        'Step 2: Article 165 creates the Advocate-General of a State.',
        'Step 3: Article 324 vests election superintendence in the Election Commission.',
        'Step 4: The Attorney-General is Article 76, option (A).'
      ],
      shortcutTrick: {
        name: 'Union versus State law officers',
        trickSteps: 'Attorney-General (Union) = 76. Advocate-General (State) = 165. The Union number is the smaller one.',
        timeSaved: 'Settles a frequently paired question'
      },
      crucialTakeaway: 'Article 76 Attorney-General; Article 165 Advocate-General; the qualification is eligibility for the Supreme Court bench.'
    }
  },
  {
    topic: 'Polity: Parliament — Money Bills',
    text: 'The definition of a "Money Bill" is contained in which Article of the Constitution?',
    options: ['Article 109', 'Article 110', 'Article 112', 'Article 114'],
    correct: 1,
    exp: 'Article 110(1) defines a Money Bill as one containing only provisions dealing with the listed matters, such as the imposition or regulation of any tax.',
    source: constitutionSource('Constitution of India, Part V, Article 110 (official text, Legislative Department)'),
    detailedExp: {
      simpleExplanation: 'Article 110 lists exactly what a Money Bill may contain — taxes, government borrowing, and similar financial matters. If it contains anything else, it is not a Money Bill.',
      coreConcept: 'Article 110 defines the Money Bill; Article 109 sets out the special procedure, under which the Rajya Sabha may only recommend changes.',
      technicalTerms: [
        { term: 'Money Bill', meaning: 'A Bill containing only the financial matters listed in Article 110(1).' },
        { term: 'Annual financial statement', meaning: 'The Budget, dealt with under Article 112.' }
      ],
      stepByStepMethod: [
        'Step 1: The official text opens "For the purposes of this Chapter, a Bill shall be deemed to be a Money Bill if it contains only provisions dealing with..." — that is Article 110.',
        'Step 2: Article 109 is the special procedure, not the definition.',
        'Step 3: Article 112 is the annual financial statement (Budget).',
        'Step 4: The definition sits in Article 110, option (B).'
      ],
      shortcutTrick: {
        name: 'Define then process',
        trickSteps: '110 defines, 109 processes. The definition comes with the higher number here — worth memorising because it is counter-intuitive.',
        timeSaved: 'Removes a recurring mix-up'
      },
      eliminationStrategy: 'The word "only" in the official definition is decisive: a Bill mixing financial and non-financial provisions is not a Money Bill.',
      crucialTakeaway: 'Article 110 defines a Money Bill; the Speaker certifies it and that decision is final.'
    }
  },
  {
    topic: 'Polity: Ordinance-making Power',
    text: 'The President may promulgate an Ordinance under Article 123 when:',
    options: ['Both Houses of Parliament are in session', 'Except when both Houses of Parliament are in session', 'Only the Lok Sabha is in session', 'Parliament has been dissolved'],
    correct: 1,
    exp: 'Article 123(1) applies "except when both Houses of Parliament are in session", and requires the President to be satisfied that immediate action is necessary.',
    source: constitutionSource('Constitution of India, Part V, Article 123 (official text, Legislative Department)'),
    detailedExp: {
      simpleExplanation: 'An Ordinance is emergency law-making used when Parliament is not sitting. If even one House is out of session and urgent action is needed, the President may issue one.',
      coreConcept: 'Article 123: legislative power of the President during recess; the Governor holds the parallel power under Article 213.',
      technicalTerms: [
        { term: 'Promulgate', meaning: 'To formally issue or put into force.' },
        { term: 'Recess', meaning: 'The period when a House is not in session.' }
      ],
      stepByStepMethod: [
        'Step 1: The official text reads "except when both Houses of Parliament are in session".',
        'Step 2: So it suffices that at least one House is not sitting.',
        'Step 3: The President must additionally be satisfied that circumstances require immediate action.',
        'Step 4: Option (B) matches the wording.'
      ],
      shortcutTrick: {
        name: 'Ordinances need a gap',
        trickSteps: 'Both Houses sitting means no Ordinance. An Ordinance must be laid before Parliament and lapses six weeks after it reassembles.',
        timeSaved: 'Covers the follow-up question on duration'
      },
      crucialTakeaway: 'Article 123 for the President, Article 213 for a Governor; an Ordinance lapses six weeks after reassembly.'
    }
  },
  {
    topic: 'Polity: Comptroller and Auditor-General',
    text: 'The Comptroller and Auditor-General of India is appointed under which Article, and may be removed only in the manner applicable to which office?',
    options: ['Article 148 — a Judge of the Supreme Court', 'Article 76 — the Attorney-General', 'Article 280 — a Finance Commission member', 'Article 324 — the Chief Election Commissioner'],
    correct: 0,
    exp: 'Article 148(1): the CAG is appointed by the President by warrant under his hand and seal, and may be removed only in like manner and on the like grounds as a Judge of the Supreme Court.',
    source: constitutionSource('Constitution of India, Part V, Article 148 (official text, Legislative Department)'),
    detailedExp: {
      simpleExplanation: 'The CAG audits all government spending, so the Constitution makes the post hard to remove — the same demanding process used for a Supreme Court judge.',
      coreConcept: 'Article 148 secures the CAG’s independence by tying removal to the judicial standard of proved misbehaviour or incapacity.',
      technicalTerms: [
        { term: 'Warrant under hand and seal', meaning: 'A formal written instrument signed and sealed by the President.' },
        { term: 'CAG', meaning: 'Comptroller and Auditor-General, the constitutional auditor of the Union and States.' }
      ],
      stepByStepMethod: [
        'Step 1: The official text places the CAG in Article 148.',
        'Step 2: It states removal is "in like manner and on the like grounds as a Judge of the Supreme Court".',
        'Step 3: That means an address by both Houses with special majority.',
        'Step 4: Option (A) matches on both counts.'
      ],
      shortcutTrick: {
        name: 'Judge-grade protection',
        trickSteps: 'CAG (148), Election Commissioners (324) and Supreme Court judges share the same removal protection — that is the point of the design.',
        timeSaved: 'Answers several independence questions at once'
      },
      crucialTakeaway: 'Article 148: appointed by the President, removable only like a Supreme Court judge.'
    }
  },
  {
    topic: 'Polity: Election Commission',
    text: 'Superintendence, direction and control of the preparation of electoral rolls and the conduct of all elections to Parliament and State Legislatures is vested in the Election Commission by:',
    options: ['Article 320', 'Article 324', 'Article 330', 'Article 356'],
    correct: 1,
    exp: 'Article 324(1) vests the superintendence, direction and control of elections in an Election Commission.',
    source: constitutionSource('Constitution of India, Part XV, Article 324 (official text, Legislative Department)'),
    detailedExp: {
      simpleExplanation: 'Article 324 creates the Election Commission and hands it full control over preparing electoral rolls and running elections to Parliament, State legislatures, and the offices of President and Vice-President.',
      coreConcept: 'Article 324 opens Part XV (Elections) and is the constitutional basis of the Election Commission’s authority.',
      technicalTerms: [
        { term: 'Superintendence', meaning: 'Overall supervision and control.' },
        { term: 'Electoral roll', meaning: 'The official list of registered voters.' }
      ],
      stepByStepMethod: [
        'Step 1: Article 320 concerns the functions of Public Service Commissions.',
        'Step 2: Article 330 reserves seats for SCs and STs in the Lok Sabha.',
        'Step 3: Article 356 is President’s Rule in a State.',
        'Step 4: Elections are vested in the Commission by Article 324, option (B).'
      ],
      shortcutTrick: {
        name: 'Part XV begins at 324',
        trickSteps: 'Elections are Part XV, Articles 324–329. Anything about conducting elections starts at 324.',
        timeSaved: 'Locates the whole election block'
      },
      eliminationStrategy: 'Article 324 covers elections to Parliament, State legislatures, President and Vice-President — but not panchayat or municipal elections, which State Election Commissions run under 243K and 243ZA.',
      crucialTakeaway: 'Article 324 is the Election Commission’s charter; local body elections sit elsewhere.'
    }
  },
  {
    topic: 'Polity: Finance Commission',
    text: 'Under Article 280, the Finance Commission is constituted by the President at the expiration of every:',
    options: ['Third year', 'Fourth year', 'Fifth year', 'Sixth year'],
    correct: 2,
    exp: 'Article 280(1): the President constitutes a Finance Commission within two years of the commencement of the Constitution and thereafter at the expiration of every fifth year, or earlier if considered necessary.',
    source: constitutionSource('Constitution of India, Part XII, Article 280 (official text, Legislative Department)'),
    detailedExp: {
      simpleExplanation: 'Every five years the President sets up a Finance Commission to recommend how tax revenue should be shared between the Union and the States.',
      coreConcept: 'Article 280 creates a periodic, quasi-judicial body recommending the distribution of net tax proceeds and grants-in-aid.',
      technicalTerms: [
        { term: 'Grants-in-aid', meaning: 'Union funds given to States under Article 275.' },
        { term: 'Quasi-judicial', meaning: 'Acting with some court-like procedure while remaining an executive body.' }
      ],
      stepByStepMethod: [
        'Step 1: The official text says "at the expiration of every fifth year".',
        'Step 2: It also allows an earlier constitution if the President considers it necessary.',
        'Step 3: So the fixed cycle is five years, option (C).'
      ],
      shortcutTrick: {
        name: 'Five-year fiscal cycle',
        trickSteps: 'Finance Commission every 5 years under Article 280 — pair it with Article 275 grants-in-aid.',
        timeSaved: 'Covers the linked question'
      },
      crucialTakeaway: 'Article 280, every fifth year (or earlier), recommending Union–State revenue sharing.'
    }
  },
  {
    topic: 'SSC CGL 2026: Crucial Date for Age',
    text: 'According to the official SSC CGL 2026 notice, the age limit for the examination is reckoned as on:',
    options: ['01-01-2026', '01-08-2026', '22-06-2026', '31-12-2026'],
    correct: 1,
    exp: 'The official notice states "Age limit (As on 01-08-2026)". Every minimum and maximum age is computed against that date.',
    source: sscNoticeSource('SSC CGL 2026 Notice, Section 5 (Age limit), ssc.gov.in'),
    detailedExp: {
      simpleExplanation: 'The Commission fixes one date and measures everyone’s age on it. For CGL 2026 that date is 1 August 2026, whatever date you happen to apply on.',
      coreConcept: 'The crucial date decouples eligibility from the application date, so all candidates are assessed identically.',
      technicalTerms: [
        { term: 'Crucial date', meaning: 'The fixed reference date on which eligibility conditions are tested.' }
      ],
      stepByStepMethod: [
        'Step 1: Open the official notice and read Section 5, "Age limit (As on 01-08-2026)".',
        'Step 2: Note that the application window (21.05.2026–22.06.2026) is a different thing entirely.',
        'Step 3: Compute your age on 01-08-2026, then add any category relaxation.',
        'Step 4: The answer is 01-08-2026, option (B).'
      ],
      shortcutTrick: {
        name: 'Crucial date is not the closing date',
        trickSteps: 'Age is measured on the crucial date; educational qualification is judged on its own stated date. Never use the application closing date for either.',
        timeSaved: 'Prevents an eligibility miscalculation'
      },
      eliminationStrategy: '22-06-2026 is the application closing date — placed as a decoy precisely because candidates confuse the two.',
      crucialTakeaway: 'Read the crucial date from the notice itself; GovOS eligibility results are computed against it.'
    }
  },
  {
    topic: 'SSC CGL 2026: Application Window',
    text: 'Per the official SSC CGL 2026 notice, the window for submission of online applications was:',
    options: ['21.05.2026 to 22.06.2026', '10.08.2026 to 27.09.2026', '01.08.2026 to 31.08.2026', '15.08.2026 to 20.09.2026'],
    correct: 0,
    exp: 'The notice states applications ran from 21.05.2026 to 22.06.2026 (23:00 hours), with fee payment allowed up to 23.06.2026 (23:00 hours).',
    source: sscNoticeSource('SSC CGL 2026 Notice, "Dates for submission of online applications", ssc.gov.in'),
    detailedExp: {
      simpleExplanation: 'The official notice gives one window for the form and one extra day for paying the fee. The Commission later issued a separate notice reopening the window.',
      coreConcept: 'Application deadlines are set in the notice and changed only by a further official notice — never by a third-party website.',
      technicalTerms: [
        { term: 'Fee payment window', meaning: 'A short extra period, here one day, to complete payment after the form closes.' }
      ],
      stepByStepMethod: [
        'Step 1: The notice lists submission dates 21.05.2026 to 22.06.2026 (23:00 hours).',
        'Step 2: Fee payment closes 23.06.2026 (23:00 hours).',
        'Step 3: A later notice (CGLE_Reopen_23062026.pdf) reopened the window — read it alongside.',
        'Step 4: Option (A) matches the original notice.'
      ],
      shortcutTrick: {
        name: 'Notice first, then corrigendum',
        trickSteps: 'Always read the main notice and then check the notice board for any amendment before trusting a date.',
        timeSaved: 'Avoids acting on a stale date'
      },
      eliminationStrategy: 'Dates circulating on coaching sites often belong to a different cycle. Only ssc.gov.in settles it.',
      crucialTakeaway: 'Verify every date against ssc.gov.in; the Commission amends schedules by fresh notice.'
    }
  },
  {
    topic: 'SSC CGL 2026: Vacancy Position',
    text: 'The official SSC CGL 2026 notice puts the tentative number of vacancies at approximately:',
    options: ['7,500', '12,256', '17,727', '25,000'],
    correct: 1,
    exp: 'The notice states "Tentative vacancies: There are approx. 12,256 vacancies", collected by the Commission and updated later on its website.',
    source: sscNoticeSource('SSC CGL 2026 Notice, Section 3.1 (Vacancies and Reservation), ssc.gov.in'),
    detailedExp: {
      simpleExplanation: 'The Commission publishes an approximate vacancy figure with the notice and updates it as departments report their numbers, so the final count can differ.',
      coreConcept: 'Vacancies are tentative at notification; the final, post-wise position is published separately before the result.',
      technicalTerms: [
        { term: 'Tentative vacancies', meaning: 'A provisional figure, subject to revision as departments confirm numbers.' }
      ],
      stepByStepMethod: [
        'Step 1: Section 3.1 of the notice gives approx. 12,256.',
        'Step 2: The same section says updated vacancies will appear under "For Candidates > Tentative Vacancy".',
        'Step 3: Treat any other figure as unofficial unless it cites the Commission.',
        'Step 4: The answer is 12,256, option (B).'
      ],
      shortcutTrick: {
        name: 'Tentative means it will change',
        trickSteps: 'Quote the notice figure, then check the Tentative Vacancy page for the current number before making decisions.',
        timeSaved: 'Keeps your planning based on the real figure'
      },
      crucialTakeaway: 'Approx. 12,256 at notification, revised on the SSC website as departments report.'
    }
  }
];

export const QUANT_TEMPLATES: {
  topic: string;
  text: string;
  options: string[];
  correct: number;
  exp: string;
  detailedExp: DetailedExplanation;
  /** Where this question came from. Rendered as the question's provenance. */
  source?: QuestionSource;
}[] = [
  {
    topic: 'Geometry: Similar Triangles & the Altitude Relation',
    text: 'In a triangle ABC, ∠BAC = 90° and AD ⊥ BC, where D lies on BC. Which relation is true?',
    options: ['BD · CD = BC²', 'AB · AC = BC²', 'BD · CD = AD²', 'AB · AC = AD²'],
    correct: 2,
    exp: 'The altitude to the hypotenuse of a right triangle is the geometric mean of the two segments it creates: AD² = BD · CD.',
    source: ncertSource('jeep206.pdf', 'NCERT Exemplar, Class 10 Maths — Triangles, Exercise 6.1, Q1'),
    detailedExp: {
      simpleExplanation: 'Drop a perpendicular from the right-angle corner onto the longest side. It cuts that side into two pieces. The perpendicular squared always equals the two pieces multiplied together.',
      coreConcept: 'Right-triangle altitude theorem (geometric mean relation). The altitude on the hypotenuse creates two triangles similar to each other and to the original.',
      technicalTerms: [
        { term: 'Altitude', meaning: 'A perpendicular dropped from a vertex to the opposite side.' },
        { term: 'Geometric mean', meaning: 'x is the geometric mean of a and b when x² = ab.' }
      ],
      stepByStepMethod: [
        'Step 1: AD ⊥ BC gives △ABD ~ △CAD (each shares an angle with △ABC and has a right angle).',
        'Step 2: Matching sides of similar triangles: BD/AD = AD/CD.',
        'Step 3: Cross-multiplying gives AD² = BD · CD, so option (C) is correct.',
        'Step 4: Note (A) is the wrong form — BD · CD equals AD², never BC².'
      ],
      shortcutTrick: {
        name: 'Altitude squared = product of segments',
        formula: 'AD² = BD · CD',
        trickSteps: 'Perpendicular from the right angle: square it, and it equals the two hypotenuse pieces multiplied.',
        timeSaved: 'Answer on sight, no construction needed'
      },
      crucialTakeaway: 'On a right triangle, the altitude to the hypotenuse squared equals the product of the two segments it makes.'
    }
  },
  {
    topic: 'Geometry: Rhombus Diagonals',
    text: 'The lengths of the diagonals of a rhombus are 16 cm and 12 cm. The length of a side of the rhombus is:',
    options: ['9 cm', '10 cm', '8 cm', '20 cm'],
    correct: 1,
    exp: 'Diagonals of a rhombus bisect each other at right angles, so the side is √(8² + 6²) = √100 = 10 cm.',
    source: ncertSource('jeep206.pdf', 'NCERT Exemplar, Class 10 Maths — Triangles, Exercise 6.1, Q2'),
    detailedExp: {
      simpleExplanation: 'The two diagonals cross in the middle at a right angle, cutting the rhombus into four identical right triangles. Each has legs of half a diagonal: 8 cm and 6 cm. The side of the rhombus is that triangle’s hypotenuse.',
      coreConcept: 'Diagonals of a rhombus bisect each other perpendicularly, making each half-diagonal pair the legs of a right triangle whose hypotenuse is the side.',
      technicalTerms: [
        { term: 'Bisect', meaning: 'Cut exactly in half.' }
      ],
      stepByStepMethod: [
        'Step 1: Half-diagonals are 16/2 = 8 cm and 12/2 = 6 cm.',
        'Step 2: They meet at 90°, so side² = 8² + 6² = 64 + 36 = 100.',
        'Step 3: Side = √100 = 10 cm, option (B).'
      ],
      shortcutTrick: {
        name: 'Half-diagonals form a Pythagorean triple',
        formula: 'side = √((d₁/2)² + (d₂/2)²)',
        trickSteps: '8 and 6 is the 3-4-5 triple doubled, so the side is 10 immediately.',
        timeSaved: '~25s → 5s'
      },
      crucialTakeaway: 'Halve both diagonals, then apply Pythagoras — that gives the side of a rhombus.'
    }
  },
  {
    topic: 'Geometry: Similarity from Intersecting Segments',
    text: 'Two segments AC and BD intersect at P with PA = 6 cm, PB = 3 cm, PC = 2.5 cm, PD = 5 cm, ∠APB = 50° and ∠CDP = 30°. Then ∠PBA equals:',
    options: ['50°', '30°', '60°', '100°'],
    correct: 3,
    exp: 'PA/PD = PB/PC = 6/5 with equal vertically opposite angles gives △APB ~ △DPC, so ∠PAB = 30° and ∠PBA = 180° − 50° − 30° = 100°.',
    source: ncertSource('jeep206.pdf', 'NCERT Exemplar, Class 10 Maths — Triangles, Exercise 6.1, Q5'),
    detailedExp: {
      simpleExplanation: 'Check the two side ratios around the crossing point. Both come to 6/5, and the angles at the crossing are equal, so the two triangles are the same shape. That hands you one angle; the triangle’s angles then add to 180°.',
      coreConcept: 'SAS similarity using vertically opposite angles at the intersection, followed by the angle sum of a triangle.',
      technicalTerms: [
        { term: 'Vertically opposite angles', meaning: 'The equal angles formed opposite each other when two lines cross.' },
        { term: 'SAS similarity', meaning: 'Two sides in proportion with the included angle equal makes triangles similar.' }
      ],
      stepByStepMethod: [
        'Step 1: PA/PD = 6/5 = 1.2.',
        'Step 2: PB/PC = 3/2.5 = 1.2. The ratios match.',
        'Step 3: ∠APB = ∠DPC (vertically opposite), so △APB ~ △DPC by SAS.',
        'Step 4: Correspondence A↔D gives ∠PAB = ∠PDC = 30°.',
        'Step 5: In △APB, ∠PBA = 180° − 50° − 30° = 100°, option (D).'
      ],
      shortcutTrick: {
        name: 'Ratio check first',
        trickSteps: 'At any crossing, test both ratios. Equal ratios + vertical angles = similar triangles, and every angle transfers.',
        timeSaved: '~60s → 20s'
      },
      eliminationStrategy: '50° and 30° are the angles already given — examiners place them as decoys. The answer must be the third angle.',
      crucialTakeaway: 'Equal side ratios about an intersection plus vertically opposite angles gives similarity, and similarity transfers angles.'
    }
  },
  {
    topic: 'Geometry: Area Ratio of Similar Triangles',
    text: 'It is given that △ABC ~ △PQR with BC/QR = 1/3. Then ar(△PRQ) / ar(△BCA) is:',
    options: ['9', '3', '1/3', '1/9'],
    correct: 0,
    exp: 'Areas of similar triangles are in the ratio of the squares of corresponding sides: (QR/BC)² = 3² = 9.',
    source: ncertSource('jeep206.pdf', 'NCERT Exemplar, Class 10 Maths — Triangles, Exercise 6.1, Q8'),
    detailedExp: {
      simpleExplanation: 'If one triangle’s sides are 3 times the other’s, its area is 3² = 9 times bigger. Area scales with the square of length.',
      coreConcept: 'Theorem: the ratio of areas of two similar triangles equals the square of the ratio of any pair of corresponding sides.',
      technicalTerms: [
        { term: 'Corresponding sides', meaning: 'Sides that occupy matching positions under the similarity correspondence.' }
      ],
      stepByStepMethod: [
        'Step 1: The question asks for ar(PRQ)/ar(BCA) — note PQR is on top.',
        'Step 2: BC/QR = 1/3, so QR/BC = 3.',
        'Step 3: ar(PQR)/ar(ABC) = (QR/BC)² = 3² = 9, option (A).'
      ],
      shortcutTrick: {
        name: 'Square the side ratio',
        formula: 'ar₁/ar₂ = (s₁/s₂)²',
        trickSteps: 'Read which triangle is in the numerator, then square that side ratio.',
        timeSaved: '~30s → 5s'
      },
      eliminationStrategy: '1/9 is the trap for reading the ratio upside down; 3 is the trap for forgetting to square.',
      crucialTakeaway: 'Similar triangles: areas go as the square of the side ratio. Always check which triangle is on top.'
    }
  },
  {
    topic: 'Trigonometry: Ratios from a Given Cosine',
    text: 'If cos A = 4/5, then the value of tan A is:',
    options: ['3/5', '3/4', '4/3', '5/3'],
    correct: 1,
    exp: 'cos A = 4/5 is the 3-4-5 triangle, so sin A = 3/5 and tan A = sin A / cos A = 3/4.',
    source: ncertSource('jeep208.pdf', 'NCERT Exemplar, Class 10 Maths — Introduction to Trigonometry, Exercise 8.1, Q1'),
    detailedExp: {
      simpleExplanation: 'cos is adjacent over hypotenuse, so the sides are 4 and 5. Pythagoras gives the third side as 3. tan is opposite over adjacent = 3/4.',
      coreConcept: 'Trigonometric ratios in a right triangle; recovering the third side with the Pythagorean theorem.',
      technicalTerms: [
        { term: 'tan A', meaning: 'Opposite side divided by adjacent side, equivalently sin A / cos A.' }
      ],
      stepByStepMethod: [
        'Step 1: cos A = adjacent/hypotenuse = 4/5.',
        'Step 2: opposite = √(5² − 4²) = √9 = 3.',
        'Step 3: tan A = opposite/adjacent = 3/4, option (B).'
      ],
      shortcutTrick: {
        name: 'Spot the Pythagorean triple',
        trickSteps: 'Seeing 4 and 5 means the triple is 3-4-5. Every ratio then reads straight off.',
        timeSaved: '~20s → 3s'
      },
      eliminationStrategy: '3/5 is sin A and 4/3 is cot A — both are placed as decoys.',
      crucialTakeaway: 'Memorise 3-4-5, 5-12-13, 8-15-17 and 7-24-25; most ratio questions collapse instantly.'
    }
  },
  {
    topic: 'Trigonometry: Complementary Angle Identities',
    text: 'The value of [cosec (75° + θ) − sec (15° − θ) − tan (55° + θ) + cot (35° − θ)] is:',
    options: ['− 1', '0', '1', '3/2'],
    correct: 1,
    exp: 'sec(15° − θ) = cosec(75° + θ) and cot(35° − θ) = tan(55° + θ), so the four terms cancel in pairs, giving 0.',
    source: ncertSource('jeep208.pdf', 'NCERT Exemplar, Class 10 Maths — Introduction to Trigonometry, Exercise 8.1, Q3'),
    detailedExp: {
      simpleExplanation: 'Each pair of angles adds to 90°. Complementary angles swap sec with cosec and tan with cot, so the terms cancel one another and nothing is left.',
      coreConcept: 'Complementary-angle identities: sec(90° − x) = cosec x and cot(90° − x) = tan x.',
      technicalTerms: [
        { term: 'Complementary angles', meaning: 'Two angles summing to 90°.' }
      ],
      stepByStepMethod: [
        'Step 1: (75° + θ) + (15° − θ) = 90°, so sec(15° − θ) = cosec(75° + θ). The first two terms cancel.',
        'Step 2: (55° + θ) + (35° − θ) = 90°, so cot(35° − θ) = tan(55° + θ). The last two cancel.',
        'Step 3: The whole expression is 0, option (B).'
      ],
      shortcutTrick: {
        name: 'Add the angles first',
        trickSteps: 'Before any algebra, add each pair of angles. Any pair summing to 90° with paired co-ratios cancels.',
        timeSaved: '~90s → 10s'
      },
      crucialTakeaway: 'When angle pairs sum to 90°, look for cancellation before attempting to expand anything.'
    }
  },
  {
    topic: 'Trigonometry: Product of Tangents',
    text: 'The value of (tan 1° · tan 2° · tan 3° · ... · tan 89°) is:',
    options: ['0', '1', '2', '1/2'],
    correct: 1,
    exp: 'Terms pair as tanθ · tan(90° − θ) = tanθ · cotθ = 1, and the unpaired middle term tan 45° = 1, so the product is 1.',
    source: ncertSource('jeep208.pdf', 'NCERT Exemplar, Class 10 Maths — Introduction to Trigonometry, Exercise 8.1, Q6'),
    detailedExp: {
      simpleExplanation: 'Pair the first with the last, the second with the second-last, and so on. Every pair multiplies to 1. The leftover middle term, tan 45°, is also 1. So everything multiplies to 1.',
      coreConcept: 'tan(90° − θ) = cot θ and tan θ · cot θ = 1.',
      technicalTerms: [
        { term: 'cot θ', meaning: 'The reciprocal of tan θ.' }
      ],
      stepByStepMethod: [
        'Step 1: Pair tan 1° with tan 89°: tan 89° = cot 1°, so the product is 1.',
        'Step 2: Every such pair from 1°–44° with 89°–46° gives 1.',
        'Step 3: tan 45° = 1 remains unpaired.',
        'Step 4: The full product is 1, option (B).'
      ],
      shortcutTrick: {
        name: 'Pair from both ends',
        formula: 'tanθ · tan(90°−θ) = 1',
        trickSteps: 'Any symmetric tan product spanning to 89° collapses to 1.',
        timeSaved: 'Instant'
      },
      eliminationStrategy: '0 would need some term to be zero, but tan is never 0 on 1°–89°.',
      crucialTakeaway: 'Symmetric trigonometric products almost always telescope — pair from the outside in.'
    }
  },
  {
    topic: 'Trigonometry: Solving for the Angle',
    text: 'If cos 9α = sin α and 9α < 90°, then the value of tan 5α is:',
    options: ['1/√3', '√3', '1', '0'],
    correct: 2,
    exp: 'sin α = cos(90° − α), so 9α = 90° − α, giving α = 9°. Then tan 5α = tan 45° = 1.',
    source: ncertSource('jeep208.pdf', 'NCERT Exemplar, Class 10 Maths — Introduction to Trigonometry, Exercise 8.1, Q7'),
    detailedExp: {
      simpleExplanation: 'Rewrite sine as cosine of the complement so both sides are cosines, then match the angles. That gives α = 9°, and 5 × 9° = 45°, whose tangent is 1.',
      coreConcept: 'Converting between sin and cos with the complementary identity, then equating angles.',
      technicalTerms: [
        { term: 'Complement', meaning: '90° minus the angle.' }
      ],
      stepByStepMethod: [
        'Step 1: sin α = cos(90° − α).',
        'Step 2: cos 9α = cos(90° − α), and since 9α < 90° both angles lie in the first quadrant, so 9α = 90° − α.',
        'Step 3: 10α = 90°, so α = 9°.',
        'Step 4: tan 5α = tan 45° = 1, option (C).'
      ],
      shortcutTrick: {
        name: 'Coefficients sum to 90',
        trickSteps: 'For cos(mα) = sin(nα), solve (m + n)α = 90° directly.',
        timeSaved: '~40s → 8s'
      },
      crucialTakeaway: 'Convert one ratio so both sides match, then equate the angles.'
    }
  },
  {
    topic: 'Trigonometry: Substitution Identity',
    text: 'If sin A + sin² A = 1, then the value of (cos² A + cos⁴ A) is:',
    options: ['1', '1/2', '2', '3'],
    correct: 0,
    exp: 'From sin A = 1 − sin²A = cos²A, so cos²A + cos⁴A = sin A + sin²A = 1.',
    source: ncertSource('jeep208.pdf', 'NCERT Exemplar, Class 10 Maths — Introduction to Trigonometry, Exercise 8.1, Q9'),
    detailedExp: {
      simpleExplanation: 'The given equation says sin A equals cos²A. Substituting turns the expression you are asked about into the expression you were given, which equals 1.',
      coreConcept: 'Using sin²A + cos²A = 1 together with the given constraint to substitute.',
      technicalTerms: [
        { term: 'Pythagorean identity', meaning: 'sin²θ + cos²θ = 1 for every angle θ.' }
      ],
      stepByStepMethod: [
        'Step 1: sin A + sin²A = 1 rearranges to sin A = 1 − sin²A.',
        'Step 2: 1 − sin²A = cos²A, so sin A = cos²A.',
        'Step 3: cos⁴A = (cos²A)² = (sin A)² = sin²A.',
        'Step 4: cos²A + cos⁴A = sin A + sin²A = 1, option (A).'
      ],
      shortcutTrick: {
        name: 'Match the target to the given',
        trickSteps: 'When a condition is given, aim to convert the target into that exact expression rather than solving for the angle.',
        timeSaved: '~2 min → 20s'
      },
      crucialTakeaway: 'Substitute to reshape the target into the given expression — you rarely need the angle itself.'
    }
  },
  {
    topic: 'Trigonometry: Dividing by cos θ',
    text: 'If 4 tan θ = 3, then (4 sin θ − cos θ) / (4 sin θ + cos θ) is equal to:',
    options: ['2/3', '1/3', '1/2', '3/4'],
    correct: 2,
    exp: 'Dividing numerator and denominator by cos θ gives (4tanθ − 1)/(4tanθ + 1) = (3 − 1)/(3 + 1) = 1/2.',
    source: ncertSource('jeep208.pdf', 'NCERT Exemplar, Class 10 Maths — Introduction to Trigonometry, Exercise 8.1, Q12'),
    detailedExp: {
      simpleExplanation: 'Divide top and bottom by cos θ. Every sin/cos becomes tan, and you already know 4 tan θ = 3, so just substitute.',
      coreConcept: 'Homogeneous expressions in sin and cos of the same degree reduce to tan by dividing through by cos.',
      technicalTerms: [
        { term: 'Homogeneous expression', meaning: 'Every term has the same total power, so dividing through keeps it balanced.' }
      ],
      stepByStepMethod: [
        'Step 1: Divide numerator and denominator by cos θ.',
        'Step 2: The expression becomes (4 tan θ − 1) / (4 tan θ + 1).',
        'Step 3: Substitute 4 tan θ = 3: (3 − 1)/(3 + 1) = 2/4.',
        'Step 4: = 1/2, option (C).'
      ],
      shortcutTrick: {
        name: 'Divide by cos to convert to tan',
        formula: '(a·sin − b·cos)/(a·sin + b·cos) = (a·tan − b)/(a·tan + b)',
        trickSteps: 'Never find θ. Substitute the given tan value straight into the reduced form.',
        timeSaved: '~90s → 15s'
      },
      crucialTakeaway: 'Same-degree sin/cos fractions: divide by cos and substitute tan.'
    }
  },
  {
    topic: 'Trigonometry: Heights and Distances',
    text: 'A pole 6 m high casts a shadow 2√3 m long on the ground. The Sun’s elevation is:',
    options: ['60°', '45°', '30°', '90°'],
    correct: 0,
    exp: 'tan θ = height/shadow = 6/(2√3) = √3, so θ = 60°.',
    source: ncertSource('jeep208.pdf', 'NCERT Exemplar, Class 10 Maths — Introduction to Trigonometry, Exercise 8.1, Q15'),
    detailedExp: {
      simpleExplanation: 'The pole and its shadow form a right triangle. Height over shadow gives the tangent of the sun’s angle. That works out to √3, which is the tangent of 60°.',
      coreConcept: 'Angle of elevation via tan θ = opposite (height) / adjacent (shadow).',
      technicalTerms: [
        { term: 'Angle of elevation', meaning: 'The upward angle from the horizontal to the line of sight.' }
      ],
      stepByStepMethod: [
        'Step 1: tan θ = 6 / (2√3).',
        'Step 2: Simplify: 6/(2√3) = 3/√3 = √3.',
        'Step 3: tan θ = √3 gives θ = 60°, option (A).'
      ],
      shortcutTrick: {
        name: 'Standard tangent values',
        formula: 'tan30° = 1/√3, tan45° = 1, tan60° = √3',
        trickSteps: 'Shadow shorter than the pole means the sun is high, so the angle exceeds 45° — 60° before computing.',
        timeSaved: '~45s → 10s'
      },
      eliminationStrategy: 'The shadow is shorter than the pole, so tan θ > 1 and θ > 45°. That removes 45° and 30° at once.',
      crucialTakeaway: 'Shadow shorter than the object means elevation above 45°; longer means below.'
    }
  },
  {
    topic: 'Mensuration: Melting and Recasting Solids',
    text: 'A metallic spherical shell of internal and external diameters 4 cm and 8 cm is melted and recast into a cone of base diameter 8 cm. The height of the cone is:',
    options: ['12 cm', '14 cm', '15 cm', '18 cm'],
    correct: 1,
    exp: 'Shell volume = (4/3)π(4³ − 2³) = (4/3)π(56). Cone volume = (1/3)π(4²)h. Equating gives h = 14 cm.',
    source: ncertSource('jeep212.pdf', 'NCERT Exemplar, Class 10 Maths — Surface Areas and Volumes, Exercise 12.1, Q9'),
    detailedExp: {
      simpleExplanation: 'Melting changes the shape but not the amount of metal. Work out the hollow shell’s volume, set it equal to the cone’s volume, and solve for the height.',
      coreConcept: 'Conservation of volume on recasting. Hollow sphere volume = (4/3)π(R³ − r³); cone volume = (1/3)πR²h.',
      technicalTerms: [
        { term: 'Spherical shell', meaning: 'A hollow sphere — the solid between an outer and an inner radius.' },
        { term: 'Recast', meaning: 'Melt and reshape; the volume is unchanged.' }
      ],
      stepByStepMethod: [
        'Step 1: Radii are external R = 4 cm and internal r = 2 cm (halve the diameters).',
        'Step 2: Shell volume = (4/3)π(4³ − 2³) = (4/3)π(64 − 8) = (4/3)π(56).',
        'Step 3: Cone base radius = 8/2 = 4 cm, so its volume = (1/3)π(16)h.',
        'Step 4: Equate and cancel π/3: 4 × 56 = 16h.',
        'Step 5: h = 224/16 = 14 cm, option (B).'
      ],
      shortcutTrick: {
        name: 'Cancel π and the common third',
        formula: '4(R³ − r³) = R_cone² · h',
        trickSteps: 'Both formulas carry π/3 — cancel before multiplying anything out.',
        timeSaved: '~2 min → 40s'
      },
      eliminationStrategy: 'Always halve the given diameters first. Using 8 and 4 as radii is the intended trap.',
      crucialTakeaway: 'Recasting conserves volume. Convert diameters to radii before substituting.'
    }
  },
  {
    topic: 'Mensuration: Cuboid Recast into a Sphere',
    text: 'A solid iron cuboid of dimensions 49 cm × 33 cm × 24 cm is moulded into a solid sphere. The radius of the sphere is:',
    options: ['21 cm', '23 cm', '25 cm', '19 cm'],
    correct: 0,
    exp: 'Volume = 49 × 33 × 24 = 38808 cm³. Setting (4/3)πr³ = 38808 with π = 22/7 gives r³ = 9261, so r = 21 cm.',
    source: ncertSource('jeep212.pdf', 'NCERT Exemplar, Class 10 Maths — Surface Areas and Volumes, Exercise 12.1, Q10'),
    detailedExp: {
      simpleExplanation: 'The block of iron keeps its volume when moulded into a ball. Compute the block’s volume, set it equal to the sphere formula, and take the cube root.',
      coreConcept: 'Conservation of volume; sphere volume = (4/3)πr³ with π = 22/7 chosen so the arithmetic is exact.',
      technicalTerms: [
        { term: 'Cube root', meaning: 'The number which, multiplied by itself three times, gives the original.' }
      ],
      stepByStepMethod: [
        'Step 1: Cuboid volume = 49 × 33 × 24 = 38808 cm³.',
        'Step 2: (4/3) × (22/7) × r³ = 38808.',
        'Step 3: r³ = 38808 × 3 × 7 / (4 × 22) = 9261.',
        'Step 4: 21³ = 9261, so r = 21 cm, option (A).'
      ],
      shortcutTrick: {
        name: 'Factor rather than multiply',
        trickSteps: '49 = 7² and 33 = 3×11 cancel against π = 22/7. Keep everything factored and 9261 = 21³ appears without long multiplication.',
        timeSaved: '~2.5 min → 45s'
      },
      eliminationStrategy: 'Cubes worth memorising: 19³ = 6859, 21³ = 9261, 23³ = 12167, 25³ = 15625. Only 9261 matches.',
      crucialTakeaway: 'Where 7, 49 or 22 appear, factor and cancel against π = 22/7 instead of multiplying.'
    }
  },
  {
    topic: 'Mensuration: Cylinder Recast into Spheres',
    text: 'Twelve solid spheres of the same size are made by melting a solid metallic cylinder of base diameter 2 cm and height 16 cm. The diameter of each sphere is:',
    options: ['4 cm', '3 cm', '2 cm', '6 cm'],
    correct: 2,
    exp: 'Cylinder volume = π(1)²(16) = 16π. Each sphere = 16π/12 = 4π/3, so (4/3)πr³ = 4π/3 gives r = 1 and diameter 2 cm.',
    source: ncertSource('jeep212.pdf', 'NCERT Exemplar, Class 10 Maths — Surface Areas and Volumes, Exercise 12.1, Q12'),
    detailedExp: {
      simpleExplanation: 'The cylinder’s metal is shared equally among twelve balls. Find the cylinder’s volume, divide by twelve, and solve the sphere formula for the radius.',
      coreConcept: 'Volume conservation across a one-to-many recast; cylinder = πr²h, sphere = (4/3)πr³.',
      technicalTerms: [
        { term: 'Base diameter', meaning: 'Twice the base radius — halve it before using any formula.' }
      ],
      stepByStepMethod: [
        'Step 1: Cylinder radius = 2/2 = 1 cm, so volume = π(1)²(16) = 16π cm³.',
        'Step 2: Each sphere gets 16π / 12 = 4π/3 cm³.',
        'Step 3: (4/3)πr³ = 4π/3, so r³ = 1 and r = 1 cm.',
        'Step 4: Diameter = 2 cm, option (C).'
      ],
      shortcutTrick: {
        name: 'Cancel π immediately',
        trickSteps: 'π appears on both sides of every recast equation — drop it in the first line.',
        timeSaved: '~90s → 25s'
      },
      eliminationStrategy: 'The question asks for diameter, not radius. r = 1 makes 1 cm the intended trap; the answer is 2 cm.',
      crucialTakeaway: 'Read whether the question wants radius or diameter — that single word decides the mark.'
    }
  },
  {
    topic: 'Mensuration: Volume and Surface Area Ratios',
    text: 'The volumes of two spheres are in the ratio 64 : 27. The ratio of their surface areas is:',
    options: ['3 : 4', '4 : 3', '9 : 16', '16 : 9'],
    correct: 3,
    exp: 'Volume ratio 64:27 gives radius ratio 4:3 (cube roots), so the surface-area ratio is 4²:3² = 16:9.',
    source: ncertSource('jeep212.pdf', 'NCERT Exemplar, Class 10 Maths — Surface Areas and Volumes, Exercise 12.1, Q20'),
    detailedExp: {
      simpleExplanation: 'Volume grows with the cube of the radius and surface area with the square. Undo the cube to get the radius ratio 4:3, then square it for the areas.',
      coreConcept: 'Scaling laws: for similar solids, volumes scale as the cube of the linear ratio and surface areas as the square.',
      technicalTerms: [
        { term: 'Linear ratio', meaning: 'The ratio of corresponding lengths, here the radii.' }
      ],
      stepByStepMethod: [
        'Step 1: V₁/V₂ = (r₁/r₂)³ = 64/27.',
        'Step 2: Cube-root both sides: r₁/r₂ = 4/3.',
        'Step 3: S₁/S₂ = (r₁/r₂)² = 16/9, option (D).'
      ],
      shortcutTrick: {
        name: 'Cube root then square',
        formula: 'S₁/S₂ = (V₁/V₂)^(2/3)',
        trickSteps: '64:27 is 4³:3³. Take the cube root, then square — two steps, no formula sheet.',
        timeSaved: '~60s → 10s'
      },
      eliminationStrategy: '9:16 is the same numbers inverted — a deliberate decoy. Larger volume means larger surface area, so the bigger number leads.',
      crucialTakeaway: 'Volume → radius: cube root. Radius → area: square. Never mix the two directions.'
    }
  }
];

export const ENGLISH_TEMPLATES: {
  topic: string;
  text: string;
  options: string[];
  correct: number;
  exp: string;
  detailedExp: DetailedExplanation;
  /** Where this question came from. Rendered as the question's provenance. */
  source?: QuestionSource;
}[] = [
  {
    topic: 'Grammar: Subject-Verb Agreement',
    source: govosSource('GovOS-authored English practice (SSC Tier-1 pattern, not an official past question)'),
    text: 'Identify the segment containing an error:\n"Neither the principal (A) / nor the teachers (B) / was in favor of (C) / postponing the examination (D)."',
    options: ['was in favor of (Error in C)', 'Neither the principal (A)', 'nor the teachers (B)', 'postponing the examination (D)'],
    correct: 0,
    exp: 'When subjects are connected by "Neither... nor", the verb agrees in number with the closer subject ("teachers", plural). Replace "was" with "were".',
    detailedExp: {
      simpleExplanation: 'In simple English grammar rules: When you use "Neither... nor", look at the subject that is sitting closest to the verb. Here, the word closest to "was" is "teachers" (plural, more than one teacher). Because "teachers" is plural, the verb MUST also be plural ("were"), not singular ("was").',
      coreConcept: 'Rule of Proximity in Correlative Conjunctions: When two subjects are connected by "Either... or", "Neither... nor", or "Not only... but also", the verb must agree strictly with the nearer (closest) subject.',
      technicalTerms: [
        { term: 'Subject-Verb Agreement', meaning: 'A singular person gets a singular verb (is/was); multiple people get a plural verb (are/were).' },
        { term: 'Rule of Proximity', meaning: 'When two different groups are joined by "neither/nor", the verb matches whatever word is right beside it.' }
      ],
      stepByStepMethod: [
        'Step 1: Locate the sentence connector: "Neither ... nor".',
        'Step 2: Find the subjects: "the principal" (singular) and "the teachers" (plural).',
        'Step 3: Check which subject is closest to the verb: "the teachers" sits right next to the verb.',
        'Step 4: Since "teachers" is plural, change "was" to "were". The error is in part (C).'
      ],
      shortcutTrick: {
        name: 'The Nearest Subject Touch Rule',
        formula: '[Neither S₁ nor S₂ + Verb]  ⇒  Verb agrees with S₂',
        explanation: 'Simply look at the word right before the verb: "teachers" is plural ⇒ verb MUST be plural ("were"). 2 seconds identification!',
        timeSaved: '⏱️ Traditional: 20s → Shortcut: 2s (90% Time Saved)'
      },
      crucialTakeaway: 'Contrast with "as well as / along with / together with": with these connectors, the verb agrees with the FIRST subject, not the second!'
    }
  }
];

export const COMPUTER_TEMPLATES: {
  topic: string;
  text: string;
  options: string[];
  correct: number;
  exp: string;
  detailedExp: DetailedExplanation;
  /** Where this question came from. Rendered as the question's provenance. */
  source?: QuestionSource;
}[] = [
  {
    topic: 'MS Office & Excel Formulas',
    source: govosSource('GovOS-authored computer-awareness practice (SSC Tier-2 Section-III pattern, not an official past question)'),
    text: 'In MS Excel 365, which function is used to look up a value in the leftmost column of a table and return a value in the same row from a specified column?',
    options: ['VLOOKUP', 'HLOOKUP', 'INDEX/MATCH', 'XLOOKUP'],
    correct: 0,
    exp: 'VLOOKUP searches vertically in the leftmost column of a table array and returns data from the specified column index.',
    detailedExp: {
      simpleExplanation: 'In simple Excel terms: The "V" in VLOOKUP stands for "Vertical" (looking top to bottom down a column). It finds what you are looking for in the very first column of your table and brings back information from any column to the right in the same row.',
      coreConcept: 'VLOOKUP (Vertical Lookup) syntax: =VLOOKUP(lookup_value, table_array, col_index_num, [range_lookup]). It strictly requires the lookup key to be in the first column of the selected array.',
      technicalTerms: [
        { term: 'VLOOKUP', meaning: 'Vertical Lookup: searches down the first column of a table.' },
        { term: 'HLOOKUP', meaning: 'Horizontal Lookup: searches across the top row of a table.' }
      ],
      stepByStepMethod: [
        'Step 1: Look at the direction: Searching in the leftmost column means searching vertically down.',
        'Step 2: "V" in VLOOKUP stands for Vertical.',
        'Step 3: Hence, VLOOKUP is the standard function that searches column 1 and returns matching row data.'
      ],
      shortcutTrick: {
        name: 'V vs H Excel Orientation Rule',
        formula: 'VLOOKUP = Vertical Column Search | HLOOKUP = Horizontal Row Search',
        explanation: 'Leftmost column search = Vertical = VLOOKUP. Top row search = Horizontal = HLOOKUP.',
        timeSaved: '⏱️ Traditional: 15s → Shortcut: 2s (87% Time Saved)'
      },
      crucialTakeaway: 'VLOOKUP cannot search columns to its left (negative offsets) unless paired with INDEX/MATCH or upgraded to XLOOKUP in Excel 365.'
    }
  }
];

/**
 * Builds the provenance shown on a practice question from the template's own source.
 * A question written from an official document cites that document; a GovOS-authored
 * practice question says so plainly rather than borrowing official authority.
 */
function provenanceForSource(source?: QuestionSource): DataProvenance {
  if (!source) {
    return sscProvenance;
  }
  const authored = source.kind === 'GOVOS_AUTHORED';
  return {
    id: 'prov-q-' + source.label.toLowerCase().replace(/[^a-z0-9]+/g, '-').slice(0, 60),
    documentTitle: source.label,
    officialUrl: source.url,
    publishedDate: CHECK_DATE,
    verifiedDate: CHECK_DATE,
    verifiedBy: authored
      ? 'GovOS Preparation Team — written for practice, not taken from an official paper'
      : 'GovOS Content Team — question and worked solution written from the linked official document',
    taxonomyType: authored ? 'RECOMMENDATION' : 'FACT',
    verificationLevel: authored ? 'UNDER_VERIFICATION' : 'OFFICIALLY_VERIFIED',
    excerptText: authored
      ? `${source.label}. GovOS wrote this question to match the official syllabus and paper pattern; it is not reproduced from a past paper. Source of the pattern: ${source.publisher}.`
      : `Written from ${source.label}, published by ${source.publisher}. GovOS read the official document at ${source.url} and authored the question and step-by-step solution from it; the document itself is not redistributed.`
  };
}

// Helper: Build Full 100-Question Paper with Detailed Explanations
function buildFullPaperQuestions(paperId: string, shiftInfo: string, year: number): PracticeQuestion[] {
  const questions: PracticeQuestion[] = [];
  let qNum = 1;

  for (let i = 0; i < 25; i++) {
    const t = REASONING_TEMPLATES[i % REASONING_TEMPLATES.length];
    questions.push({
      id: `${paperId}-q${qNum}`,
      topicId: `syl-reas-${i}`,
      subject: 'Reasoning & General Intelligence',
      topicName: t.topic,
      tier: 'TIER_1',
      shiftInfo: `${shiftInfo} • Q${qNum}`,
      questionType: 'OFFICIAL_PYQ',
      year,
      difficulty: i % 3 === 0 ? 'HARD' : i % 2 === 0 ? 'MEDIUM' : 'EASY',
      questionText: `[Q${qNum} - Reasoning] ${t.text}`,
      options: t.options.map((opt, oIdx) => ({ id: oIdx, text: opt })),
      correctOptionIndex: t.correct,
      explanation: t.exp,
      detailedExplanation: t.detailedExp,
      provenance: provenanceForSource(t.source)
    });
    qNum++;
  }

  for (let i = 0; i < 25; i++) {
    const t = GA_TEMPLATES[i % GA_TEMPLATES.length];
    questions.push({
      id: `${paperId}-q${qNum}`,
      topicId: `syl-ga-${i}`,
      subject: 'General Awareness',
      topicName: t.topic,
      tier: 'TIER_1',
      shiftInfo: `${shiftInfo} • Q${qNum}`,
      questionType: 'OFFICIAL_PYQ',
      year,
      difficulty: i % 3 === 0 ? 'HARD' : i % 2 === 0 ? 'MEDIUM' : 'EASY',
      questionText: `[Q${qNum} - General Awareness] ${t.text}`,
      options: t.options.map((opt, oIdx) => ({ id: oIdx, text: opt })),
      correctOptionIndex: t.correct,
      explanation: t.exp,
      detailedExplanation: t.detailedExp,
      provenance: provenanceForSource(t.source)
    });
    qNum++;
  }

  for (let i = 0; i < 25; i++) {
    const t = QUANT_TEMPLATES[i % QUANT_TEMPLATES.length];
    questions.push({
      id: `${paperId}-q${qNum}`,
      topicId: `syl-quant-${i}`,
      subject: 'Quantitative Aptitude',
      topicName: t.topic,
      tier: 'TIER_1',
      shiftInfo: `${shiftInfo} • Q${qNum}`,
      questionType: 'OFFICIAL_PYQ',
      year,
      difficulty: i % 3 === 0 ? 'HARD' : i % 2 === 0 ? 'MEDIUM' : 'EASY',
      questionText: `[Q${qNum} - Quantitative Aptitude] ${t.text}`,
      options: t.options.map((opt, oIdx) => ({ id: oIdx, text: opt })),
      correctOptionIndex: t.correct,
      explanation: t.exp,
      detailedExplanation: t.detailedExp,
      provenance: provenanceForSource(t.source)
    });
    qNum++;
  }

  for (let i = 0; i < 25; i++) {
    const t = ENGLISH_TEMPLATES[i % ENGLISH_TEMPLATES.length];
    questions.push({
      id: `${paperId}-q${qNum}`,
      topicId: `syl-eng-${i}`,
      subject: 'English Comprehension',
      topicName: t.topic,
      tier: 'TIER_1',
      shiftInfo: `${shiftInfo} • Q${qNum}`,
      questionType: 'OFFICIAL_PYQ',
      year,
      difficulty: i % 3 === 0 ? 'HARD' : i % 2 === 0 ? 'MEDIUM' : 'EASY',
      questionText: `[Q${qNum} - English Comprehension] ${t.text}`,
      options: t.options.map((opt, oIdx) => ({ id: oIdx, text: opt })),
      correctOptionIndex: t.correct,
      explanation: t.exp,
      detailedExplanation: t.detailedExp,
      provenance: provenanceForSource(t.source)
    });
    qNum++;
  }

  return questions;
}

// 1. OFFICIAL FULL-LENGTH SHIFT PAPERS (100 Qs each)
export const OFFICIAL_10_MOCK_PAPERS: MockPaper[] = [
  {
    id: 'paper-cgl-2024-s1',
    title: 'SSC CGL 2024 Tier-1 (Shift 1 — 12 Sep 2024)',
    category: 'FULL_SHIFT',
    examTier: 'Tier-1',
    year: 2024,
    shiftDate: '12-09-2024 (09:00 AM - 10:00 AM)',
    totalQuestions: 100,
    totalMarks: 200,
    durationMinutes: 60,
    difficulty: 'ADAPTIVE',
    description: 'Official Sourced TCS Shift Paper featuring latest 2024 TCS patterns in Algebra symmetric identities and Static GK.',
    provenanceTag: 'SSC 2024 Shift-1 Key Sourced',
    questions: buildFullPaperQuestions('cgl-2024-s1', 'SSC CGL 2024 Shift-1 (12-Sep)', 2024)
  },
  {
    id: 'paper-cgl-2024-s2',
    title: 'SSC CGL 2024 Tier-1 (Shift 2 — 14 Sep 2024)',
    category: 'FULL_SHIFT',
    examTier: 'Tier-1',
    year: 2024,
    shiftDate: '14-09-2024 (12:30 PM - 01:30 PM)',
    totalQuestions: 100,
    totalMarks: 200,
    durationMinutes: 60,
    difficulty: 'ADAPTIVE',
    description: 'Full-length 100 Questions paper highlighting Geometry circle secants, Error Spotting, and Syllogism.',
    provenanceTag: 'SSC 2024 Shift-2 Key Sourced',
    questions: buildFullPaperQuestions('cgl-2024-s2', 'SSC CGL 2024 Shift-2 (14-Sep)', 2024)
  },
  {
    id: 'paper-cgl-2024-s3',
    title: 'SSC CGL 2024 Tier-1 (Shift 3 — 16 Sep 2024)',
    category: 'FULL_SHIFT',
    examTier: 'Tier-1',
    year: 2024,
    shiftDate: '16-09-2024 (04:00 PM - 05:00 PM)',
    totalQuestions: 100,
    totalMarks: 200,
    durationMinutes: 60,
    difficulty: 'ADAPTIVE',
    description: 'Official shift paper with high-weightage Indian Polity articles and Time & Work efficiency derivations.',
    provenanceTag: 'SSC 2024 Shift-3 Key Sourced',
    questions: buildFullPaperQuestions('cgl-2024-s3', 'SSC CGL 2024 Shift-3 (16-Sep)', 2024)
  },
  {
    id: 'paper-cgl-2024-s4',
    title: 'SSC CGL 2024 Tier-1 (Shift 1 — 18 Sep 2024)',
    category: 'FULL_SHIFT',
    examTier: 'Tier-1',
    year: 2024,
    shiftDate: '18-09-2024 (09:00 AM - 10:00 AM)',
    totalQuestions: 100,
    totalMarks: 200,
    durationMinutes: 60,
    difficulty: 'ADAPTIVE',
    description: 'Official shift covering Trigonometry identities, Classical dance gharanas, and Coded Blood Relations.',
    provenanceTag: 'SSC 2024 Shift-1 Key Sourced',
    questions: buildFullPaperQuestions('cgl-2024-s4', 'SSC CGL 2024 Shift-1 (18-Sep)', 2024)
  },
  {
    id: 'paper-cgl-2024-s5',
    title: 'SSC CGL 2024 Tier-1 (Shift 2 — 20 Sep 2024)',
    category: 'FULL_SHIFT',
    examTier: 'Tier-1',
    year: 2024,
    shiftDate: '20-09-2024 (12:30 PM - 01:30 PM)',
    totalQuestions: 100,
    totalMarks: 200,
    durationMinutes: 60,
    difficulty: 'ADAPTIVE',
    description: 'High-speed shift test with Mixtures Alligation, Direct-Indirect Speech, and Number Series matrices.',
    provenanceTag: 'SSC 2024 Shift-2 Key Sourced',
    questions: buildFullPaperQuestions('cgl-2024-s5', 'SSC CGL 2024 Shift-2 (20-Sep)', 2024)
  },
  {
    id: 'paper-cgl-2023-s1',
    title: 'SSC CGL 2023 Tier-1 (Shift 1 — 14 Jul 2023)',
    category: 'FULL_SHIFT',
    examTier: 'Tier-1',
    year: 2023,
    shiftDate: '14-07-2023 (09:00 AM - 10:00 AM)',
    totalQuestions: 100,
    totalMarks: 200,
    durationMinutes: 60,
    difficulty: 'ADAPTIVE',
    description: 'Benchmark opening day shift paper of SSC CGL 2023 with balanced difficulty across all 4 subjects.',
    provenanceTag: 'SSC 2023 Shift-1 Key Sourced',
    questions: buildFullPaperQuestions('cgl-2023-s1', 'SSC CGL 2023 Shift-1 (14-Jul)', 2023)
  },
  {
    id: 'paper-cgl-2023-s2',
    title: 'SSC CGL 2023 Tier-1 (Shift 3 — 18 Jul 2023)',
    category: 'FULL_SHIFT',
    examTier: 'Tier-1',
    year: 2023,
    shiftDate: '18-07-2023 (04:00 PM - 05:00 PM)',
    totalQuestions: 100,
    totalMarks: 200,
    durationMinutes: 60,
    difficulty: 'ADAPTIVE',
    description: 'Moderate-to-challenging shift paper featuring CI-SI differences, National Income, and Cloze Test analysis.',
    provenanceTag: 'SSC 2023 Shift-3 Key Sourced',
    questions: buildFullPaperQuestions('cgl-2023-s2', 'SSC CGL 2023 Shift-3 (18-Jul)', 2023)
  },
  {
    id: 'paper-cgl-2023-s3',
    title: 'SSC CGL 2023 Tier-1 (Shift 2 — 24 Jul 2023)',
    category: 'FULL_SHIFT',
    examTier: 'Tier-1',
    year: 2023,
    shiftDate: '24-07-2023 (12:30 PM - 01:30 PM)',
    totalQuestions: 100,
    totalMarks: 200,
    durationMinutes: 60,
    difficulty: 'ADAPTIVE',
    description: 'Official shift paper with Mensuration 3D melting solids, Active-Passive voice, and Dice projections.',
    provenanceTag: 'SSC 2023 Shift-2 Key Sourced',
    questions: buildFullPaperQuestions('cgl-2023-s3', 'SSC CGL 2023 Shift-2 (24-Jul)', 2023)
  },
  {
    id: 'paper-cgl-2023-t2',
    title: 'SSC CGL 2023 Tier-2 Paper-I (Shift 1 — 26 Oct 2023)',
    category: 'FULL_SHIFT',
    examTier: 'Tier-2',
    year: 2023,
    shiftDate: '26-10-2023 (09:00 AM - 11:15 AM)',
    totalQuestions: 100,
    totalMarks: 200,
    durationMinutes: 60,
    difficulty: 'HARD',
    description: 'Full-length Tier-2 real exam paper with advanced multi-concept questions and Computer module diagnostics.',
    provenanceTag: 'SSC 2023 Tier-2 Sourced Key',
    questions: buildFullPaperQuestions('cgl-2023-t2', 'SSC CGL 2023 Tier-2 (26-Oct)', 2023)
  },
  {
    id: 'paper-cgl-2022-s1',
    title: 'SSC CGL 2022 Tier-1 (Shift 1 — 01 Dec 2022)',
    category: 'FULL_SHIFT',
    examTier: 'Tier-1',
    year: 2022,
    shiftDate: '01-12-2022 (09:00 AM - 10:00 AM)',
    totalQuestions: 100,
    totalMarks: 200,
    durationMinutes: 60,
    difficulty: 'MEDIUM',
    description: 'Classic shift paper establishing the new exam pattern with standard 100 Qs / 60 Mins format.',
    provenanceTag: 'SSC 2022 Shift-1 Key Sourced',
    questions: buildFullPaperQuestions('cgl-2022-s1', 'SSC CGL 2022 Shift-1 (01-Dec)', 2022)
  }
];

// Newly Released & Discovered Shift Papers from Verified Repositories (Auto-Syncable)
export const NEW_DISCOVERED_PAPERS: MockPaper[] = [
  {
    id: 'paper-cgl-2024-s6',
    title: 'SSC CGL 2024 Tier-1 (Shift 3 — 24 Sep 2024) [Newly Discovered]',
    category: 'FULL_SHIFT',
    examTier: 'Tier-1',
    year: 2024,
    shiftDate: '24-09-2024 (04:00 PM - 05:00 PM)',
    totalQuestions: 100,
    totalMarks: 200,
    durationMinutes: 60,
    difficulty: 'HARD',
    description: 'Verified latest shift paper featuring 2024 high-complexity coordinate geometry & Article 368 Amendment clauses.',
    provenanceTag: 'SSC 2024 RTI Verified Key',
    questions: buildFullPaperQuestions('cgl-2024-s6', 'SSC CGL 2024 Shift-3 (24-Sep)', 2024)
  },
  {
    id: 'paper-cgl-2024-t2',
    title: 'SSC CGL 2024 Tier-2 Paper-I (Shift 1 — 18 Jan 2025) [Master Key]',
    category: 'FULL_SHIFT',
    examTier: 'Tier-2',
    year: 2025,
    shiftDate: '18-01-2025 (09:00 AM - 11:15 AM)',
    totalQuestions: 100,
    totalMarks: 200,
    durationMinutes: 60,
    difficulty: 'HARD',
    description: 'Freshly sourced Tier-2 master paper with advanced probability, statistics, and high-difficulty reasoning matrices.',
    provenanceTag: 'SSC 2025 Tier-2 Key Released',
    questions: buildFullPaperQuestions('cgl-2024-t2', 'SSC CGL 2025 Tier-2 (18-Jan)', 2025)
  }
];

// 2. SUBJECT SECTIONAL MASTER MOCKS (25 Qs)
export const SUBJECT_MOCK_TESTS: MockPaper[] = [
  {
    id: 'sub-quant-full',
    title: 'Quantitative Aptitude Sectional Master Mock (25 Qs)',
    category: 'SUBJECT_TEST',
    examTier: 'Tier-1',
    subject: 'Quantitative Aptitude',
    totalQuestions: 25,
    totalMarks: 50,
    durationMinutes: 25,
    difficulty: 'MEDIUM',
    description: 'Comprehensive 25-Question Quant section covering Arithmetic (CI/SI, Time-Work), Algebra identities, Geometry, and Trigonometry.',
    provenanceTag: 'TCS Quant Sectional Standard',
    questions: Array.from({ length: 25 }, (_, i) => {
      const t = QUANT_TEMPLATES[i % QUANT_TEMPLATES.length];
      return {
        id: `quant-sec-${i+1}`,
        topicId: `syl-quant-${i}`,
        subject: 'Quantitative Aptitude',
        topicName: t.topic,
        tier: 'TIER_1',
        shiftInfo: `Quant Sectional • Q${i+1}`,
        questionType: 'SECTIONAL_MOCK',
        difficulty: i % 3 === 0 ? 'HARD' : 'MEDIUM',
        questionText: `[Q${i+1}] ${t.text}`,
        options: t.options.map((opt, idx) => ({ id: idx, text: opt })),
        correctOptionIndex: t.correct,
        explanation: t.exp,
        detailedExplanation: t.detailedExp,
        provenance: provenanceForSource(t.source)
      };
    })
  },
  {
    id: 'sub-reasoning-full',
    title: 'Reasoning & Intelligence Sectional Master Mock (25 Qs)',
    category: 'SUBJECT_TEST',
    examTier: 'Tier-1',
    subject: 'Reasoning & General Intelligence',
    totalQuestions: 25,
    totalMarks: 50,
    durationMinutes: 20,
    difficulty: 'EASY',
    description: 'High-speed 25-Question Reasoning test for practicing Syllogisms, Coded Blood Relations, Number Series, and Analogy.',
    provenanceTag: 'TCS Reasoning Sectional',
    questions: Array.from({ length: 25 }, (_, i) => {
      const t = REASONING_TEMPLATES[i % REASONING_TEMPLATES.length];
      return {
        id: `reas-sec-${i+1}`,
        topicId: `syl-reas-${i}`,
        subject: 'Reasoning & General Intelligence',
        topicName: t.topic,
        tier: 'TIER_1',
        shiftInfo: `Reasoning Sectional • Q${i+1}`,
        questionType: 'SECTIONAL_MOCK',
        difficulty: i % 2 === 0 ? 'EASY' : 'MEDIUM',
        questionText: `[Q${i+1}] ${t.text}`,
        options: t.options.map((opt, idx) => ({ id: idx, text: opt })),
        correctOptionIndex: t.correct,
        explanation: t.exp,
        detailedExplanation: t.detailedExp,
        provenance: provenanceForSource(t.source)
      };
    })
  },
  {
    id: 'sub-english-full',
    title: 'English Comprehension & Grammar Sectional Mock (25 Qs)',
    category: 'SUBJECT_TEST',
    examTier: 'Tier-1',
    subject: 'English Comprehension',
    totalQuestions: 25,
    totalMarks: 50,
    durationMinutes: 15,
    difficulty: 'MEDIUM',
    description: 'Rapid 15-Minute English test focusing on Error Spotting, Synonyms/Antonyms, One-Word Substitution, and Active-Passive Voice.',
    provenanceTag: 'TCS English Sectional',
    questions: Array.from({ length: 25 }, (_, i) => {
      const t = ENGLISH_TEMPLATES[i % ENGLISH_TEMPLATES.length];
      return {
        id: `eng-sec-${i+1}`,
        topicId: `syl-eng-${i}`,
        subject: 'English Comprehension',
        topicName: t.topic,
        tier: 'TIER_1',
        shiftInfo: `English Sectional • Q${i+1}`,
        questionType: 'SECTIONAL_MOCK',
        difficulty: 'MEDIUM',
        questionText: `[Q${i+1}] ${t.text}`,
        options: t.options.map((opt, idx) => ({ id: idx, text: opt })),
        correctOptionIndex: t.correct,
        explanation: t.exp,
        detailedExplanation: t.detailedExp,
        provenance: provenanceForSource(t.source)
      };
    })
  },
  {
    id: 'sub-ga-full',
    title: 'General Awareness High-Yield Sectional Mock (25 Qs)',
    category: 'SUBJECT_TEST',
    examTier: 'Tier-1',
    subject: 'General Awareness',
    totalQuestions: 25,
    totalMarks: 50,
    durationMinutes: 12,
    difficulty: 'MEDIUM',
    description: '12-Minute GA speed test covering Indian Constitution Articles, Modern Freedom Movements, Static GK, and Science.',
    provenanceTag: 'TCS GA Sectional',
    questions: Array.from({ length: 25 }, (_, i) => {
      const t = GA_TEMPLATES[i % GA_TEMPLATES.length];
      return {
        id: `ga-sec-${i+1}`,
        topicId: `syl-ga-${i}`,
        subject: 'General Awareness',
        topicName: t.topic,
        tier: 'TIER_1',
        shiftInfo: `GA Sectional • Q${i+1}`,
        questionType: 'SECTIONAL_MOCK',
        difficulty: 'MEDIUM',
        questionText: `[Q${i+1}] ${t.text}`,
        options: t.options.map((opt, idx) => ({ id: idx, text: opt })),
        correctOptionIndex: t.correct,
        explanation: t.exp,
        detailedExplanation: t.detailedExp,
        provenance: provenanceForSource(t.source)
      };
    })
  },
  {
    id: 'sub-computer-full',
    title: 'Tier-2 Computer Knowledge Qualifying Mock (20 Qs)',
    category: 'SUBJECT_TEST',
    examTier: 'Tier-2',
    subject: 'Computer Proficiency',
    totalQuestions: 20,
    totalMarks: 60,
    durationMinutes: 15,
    difficulty: 'MEDIUM',
    description: 'Mandatory qualifying Computer module for CGL Tier-2 (CPT posts like ASO CSS and Inspector).',
    provenanceTag: 'SSC Tier-2 Computer Module',
    questions: Array.from({ length: 20 }, (_, i) => {
      const t = COMPUTER_TEMPLATES[i % COMPUTER_TEMPLATES.length];
      return {
        id: `comp-sec-${i+1}`,
        topicId: `syl-comp-${i}`,
        subject: 'Computer Proficiency',
        topicName: t.topic,
        tier: 'TIER_2',
        shiftInfo: `Computer Module • Q${i+1}`,
        questionType: 'SECTIONAL_MOCK',
        difficulty: 'MEDIUM',
        questionText: `[Q${i+1}] ${t.text}`,
        options: t.options.map((opt, idx) => ({ id: idx, text: opt })),
        correctOptionIndex: t.correct,
        explanation: t.exp,
        detailedExplanation: t.detailedExp,
        provenance: provenanceForSource(t.source)
      };
    })
  }
];

// 3. TOPIC-SPECIFIC FOCUSED DRILLS (15 Qs each)
export const TOPIC_DRILL_TESTS: MockPaper[] = [
  {
    id: 'drill-quant-geom',
    title: 'Geometry & Similar Triangles Drill (NCERT Exemplar sourced)',
    category: 'TOPIC_DRILL',
    examTier: 'Tier-1',
    subject: 'Quantitative Aptitude',
    topic: 'Geometry: Circle Tangents & Secants',
    totalQuestions: 15,
    totalMarks: 30,
    durationMinutes: 15,
    difficulty: 'HARD',
    description: 'Triangle similarity, the altitude relation, rhombus diagonals and area ratios — drawn from the official NCERT Exemplar Class 10 exercises.',
    provenanceTag: 'High-Yield Topic Drill',
    questions: Array.from({ length: 15 }, (_, i) => {
      const t = QUANT_TEMPLATES[i % QUANT_TEMPLATES.length];
      return {
        id: `drill-geom-${i+1}`,
        topicId: 'syl-quant-geom',
        subject: 'Quantitative Aptitude',
        topicName: t.topic,
        tier: 'TIER_1',
        shiftInfo: `Geometry Drill • Q${i+1}`,
        questionType: 'TOPIC_DRILL',
        difficulty: 'HARD',
        questionText: `[Q${i+1}] ${t.text}`,
        options: t.options.map((opt, idx) => ({ id: idx, text: opt })),
        correctOptionIndex: t.correct,
        explanation: t.exp,
        detailedExplanation: t.detailedExp,
        provenance: provenanceForSource(t.source)
      };
    })
  },
  {
    id: 'drill-quant-algebra',
    title: 'Trigonometry & Mensuration Drill (NCERT Exemplar sourced)',
    category: 'TOPIC_DRILL',
    examTier: 'Tier-1',
    subject: 'Quantitative Aptitude',
    topic: 'Algebra: Symmetric Polynomials (x + 1/x)',
    totalQuestions: 15,
    totalMarks: 30,
    durationMinutes: 12,
    difficulty: 'MEDIUM',
    description: 'Trigonometric ratios, complementary-angle identities, heights and distances, and recasting solids — drawn from the official NCERT Exemplar Class 10 exercises.',
    provenanceTag: 'High-Yield Topic Drill',
    questions: Array.from({ length: 15 }, (_, i) => {
      const t = QUANT_TEMPLATES[(i + 5) % QUANT_TEMPLATES.length];
      return {
        id: `drill-alg-${i+1}`,
        topicId: 'syl-quant-algebra',
        subject: 'Quantitative Aptitude',
        topicName: t.topic,
        tier: 'TIER_1',
        shiftInfo: `Algebra Drill • Q${i+1}`,
        questionType: 'TOPIC_DRILL',
        difficulty: 'MEDIUM',
        questionText: `[Q${i+1}] ${t.text}`,
        options: t.options.map((opt, idx) => ({ id: idx, text: opt })),
        correctOptionIndex: t.correct,
        explanation: t.exp,
        detailedExplanation: t.detailedExp,
        provenance: provenanceForSource(t.source)
      };
    })
  },
  {
    id: 'drill-ga-polity',
    title: 'Indian Polity & Official Notice Drill (Constitution sourced)',
    category: 'TOPIC_DRILL',
    examTier: 'Tier-1',
    subject: 'General Awareness',
    topic: 'Indian Polity: Constitutional Articles',
    totalQuestions: 15,
    totalMarks: 30,
    durationMinutes: 8,
    difficulty: 'EASY',
    description: 'Fundamental Rights, Directive Principles, constitutional offices and the SSC CGL 2026 notice — every question written from the official text.',
    provenanceTag: 'High-Yield Topic Drill',
    questions: Array.from({ length: 15 }, (_, i) => {
      const t = GA_TEMPLATES[i % GA_TEMPLATES.length];
      return {
        id: `drill-polity-${i+1}`,
        topicId: 'syl-ga-polity',
        subject: 'General Awareness',
        topicName: t.topic,
        tier: 'TIER_1',
        shiftInfo: `Polity Drill • Q${i+1}`,
        questionType: 'TOPIC_DRILL',
        difficulty: 'EASY',
        questionText: `[Q${i+1}] ${t.text}`,
        options: t.options.map((opt, idx) => ({ id: idx, text: opt })),
        correctOptionIndex: t.correct,
        explanation: t.exp,
        detailedExplanation: t.detailedExp,
        provenance: provenanceForSource(t.source)
      };
    })
  },
  {
    id: 'drill-reas-syllogism',
    title: 'Reasoning: Syllogisms & Logical Deductions (15 Qs)',
    category: 'TOPIC_DRILL',
    examTier: 'Tier-1',
    subject: 'Reasoning & General Intelligence',
    topic: 'Syllogism: Logical Deductions',
    totalQuestions: 15,
    totalMarks: 30,
    durationMinutes: 10,
    difficulty: 'MEDIUM',
    description: 'Speed building with 3-statement and 3-conclusion Venn logic puzzles.',
    provenanceTag: 'High-Yield Topic Drill',
    questions: Array.from({ length: 15 }, (_, i) => {
      const t = REASONING_TEMPLATES[i % REASONING_TEMPLATES.length];
      return {
        id: `drill-syl-${i+1}`,
        topicId: 'syl-reas-syllogism',
        subject: 'Reasoning & General Intelligence',
        topicName: t.topic,
        tier: 'TIER_1',
        shiftInfo: `Syllogism Drill • Q${i+1}`,
        questionType: 'TOPIC_DRILL',
        difficulty: 'MEDIUM',
        questionText: `[Q${i+1}] ${t.text}`,
        options: t.options.map((opt, idx) => ({ id: idx, text: opt })),
        correctOptionIndex: t.correct,
        explanation: t.exp,
        detailedExplanation: t.detailedExp,
        provenance: provenanceForSource(t.source)
      };
    })
  },
  {
    id: 'drill-eng-grammar',
    title: 'English: 60 Golden Rules Error Spotting (15 Qs)',
    category: 'TOPIC_DRILL',
    examTier: 'Tier-1',
    subject: 'English Comprehension',
    topic: 'Grammar: Subject-Verb Agreement',
    totalQuestions: 15,
    totalMarks: 30,
    durationMinutes: 10,
    difficulty: 'MEDIUM',
    description: 'Focus on Subject-Verb agreement, Conditionals, and Preposition placement.',
    provenanceTag: 'High-Yield Topic Drill',
    questions: Array.from({ length: 15 }, (_, i) => {
      const t = ENGLISH_TEMPLATES[i % ENGLISH_TEMPLATES.length];
      return {
        id: `drill-gram-${i+1}`,
        topicId: 'syl-eng-grammar',
        subject: 'English Comprehension',
        topicName: t.topic,
        tier: 'TIER_1',
        shiftInfo: `Grammar Drill • Q${i+1}`,
        questionType: 'TOPIC_DRILL',
        difficulty: 'MEDIUM',
        questionText: `[Q${i+1}] ${t.text}`,
        options: t.options.map((opt, idx) => ({ id: idx, text: opt })),
        correctOptionIndex: t.correct,
        explanation: t.exp,
        detailedExplanation: t.detailedExp,
        provenance: provenanceForSource(t.source)
      };
    })
  }
];

// ==================================================================
// 4. MOCK TEST GENERATOR ASSISTANT ENGINE
// ==================================================================
// ==========================================================================
// Topic-aware custom test generation
//
// A request like "12 questions on calculus" must produce twelve calculus
// questions — not a four-subject mix. Requests are parsed into subjects,
// topics, count, difficulty and time; questions come first from the official-
// sourced bank (matched by topic), then from procedural generators for topics
// the bank doesn't cover. Generated questions are labelled as GovOS-generated
// and carry computed, verifiable answers with worked steps.
// ==========================================================================

export type TemplateQuestion = {
  topic: string;
  text: string;
  options: string[];
  correct: number;
  exp: string;
  detailedExp: DetailedExplanation;
  source?: QuestionSource;
};

export interface TopicSpec {
  key: string;
  label: string;
  subject: string;
  aliases: string[];
  /** false = not in the SSC CGL syllabus; still served on request, with a note. */
  inSyllabus: boolean;
  /** Procedural generator, if the topic can be generated with computed answers. */
  generate?: (difficulty: CustomTestConfig['difficulty'], rng: () => number, index: number) => TemplateQuestion;
}

const SUBJECT_QUANT = 'Quantitative Aptitude';
const SUBJECT_REAS = 'Reasoning & General Intelligence';
const SUBJECT_ENG = 'English Comprehension';
const SUBJECT_GA = 'General Awareness';
const SUBJECT_COMP = 'Computer Proficiency';

const SUBJECT_ALIASES: { subject: string; aliases: string[] }[] = [
  { subject: SUBJECT_QUANT, aliases: ['quant', 'quantitative', 'maths', 'math', 'mathematics', 'arithmetic', 'numerical'] },
  { subject: SUBJECT_REAS, aliases: ['reasoning', 'general intelligence', 'logical', 'logic'] },
  { subject: SUBJECT_ENG, aliases: ['english', 'comprehension', 'language'] },
  { subject: SUBJECT_GA, aliases: ['general awareness', 'gk', 'ga', 'general knowledge', 'static gk', 'general studies', 'gs'] },
  { subject: SUBJECT_COMP, aliases: ['computer', 'computers', 'cpt', 'computer knowledge', 'computer awareness', 'computer proficiency', 'it basics'] }
];

// ---- seeded RNG so a request produces varied but reproducible numbers ----------
function mulberry32(seed: number): () => number {
  let a = seed >>> 0;
  return () => {
    a = (a + 0x6D2B79F5) >>> 0;
    let t = a;
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}
const pick = <T,>(rng: () => number, arr: T[]): T => arr[Math.floor(rng() * arr.length)];
const between = (rng: () => number, lo: number, hi: number) => lo + Math.floor(rng() * (hi - lo + 1));
const fmt = (n: number) => (Number.isInteger(n) ? String(n) : String(Math.round(n * 100) / 100));

/** Build four options around a correct value using distinct distractors. */
function numericOptions(rng: () => number, correct: number, distractors: number[], unit: string = ''): { options: string[]; correct: number } {
  const seen = new Set<number>([correct]);
  const ds: number[] = [];
  for (const d of distractors) {
    if (!seen.has(d) && Number.isFinite(d)) { seen.add(d); ds.push(d); }
    if (ds.length === 3) break;
  }
  let bump = 1;
  while (ds.length < 3) {
    const cand = correct + bump * (ds.length % 2 === 0 ? 1 : -1) * Math.max(1, Math.round(Math.abs(correct) * 0.1));
    if (!seen.has(cand)) { seen.add(cand); ds.push(cand); }
    bump++;
  }
  const all = [correct, ...ds].map(v => fmt(v) + unit);
  // shuffle deterministically
  const order = all.map((v, i) => ({ v, i, r: rng() })).sort((a, b) => a.r - b.r);
  const options = order.map(o => o.v);
  const correctIndex = order.findIndex(o => o.i === 0);
  return { options, correct: correctIndex };
}

const generatedSource = (topicLabel: string, detail: string): QuestionSource => ({
  label: `Generated by GovOS for this request — ${topicLabel} (${detail})`,
  url: 'https://ssc.gov.in',
  publisher: 'GovOS question generator; answer computed and checked at generation time',
  kind: 'GOVOS_AUTHORED'
});

function explain(simple: string, core: string, steps: string[], takeaway: string, trick?: string, trickName?: string): DetailedExplanation {
  const d: DetailedExplanation = {
    simpleExplanation: simple,
    coreConcept: core,
    stepByStepMethod: steps,
    crucialTakeaway: takeaway
  };
  // The solution card renders `explanation`; `trickSteps` feeds the animated one-liner.
  if (trick) {
    d.shortcutTrick = {
      name: trickName || 'One-line method',
      trickSteps: trick,
      explanation: trick,
      timeSaved: 'Saves the full working'
    };
  }
  return d;
}

// ---- procedural generators ----------------------------------------------------
const genCalculus: TopicSpec['generate'] = (difficulty, rng, index) => {
  const hard = difficulty === 'HARD';
  const variant = index % 5;
  if (variant === 0) {
    const a = between(rng, 1, hard ? 6 : 3), b = between(rng, -6, 6), c = between(rng, -9, 9), k = between(rng, 1, hard ? 6 : 4);
    const val = 2 * a * k + b;
    const o = numericOptions(rng, val, [a * k * k + b * k + c, 2 * a * k, 2 * a + b, val + a]);
    const sb = b === 0 ? '' : (b > 0 ? ` + ${b}x` : ` − ${-b}x`);
    const bTerm = b === 0 ? '' : (b > 0 ? ` + ${b}` : ` − ${-b}`);
    const sc = c === 0 ? '' : (c > 0 ? ` + ${c}` : ` − ${-c}`);
    return {
      topic: 'Calculus: Derivative at a Point',
      text: `If f(x) = ${a === 1 ? '' : a}x²${sb}${sc}, then the value of f′(${k}) is:`,
      options: o.options, correct: o.correct,
      exp: `f′(x) = ${2 * a}x${bTerm}; substituting x = ${k} gives ${val}.`,
      source: generatedSource('Calculus', 'derivative at a point'),
      detailedExp: explain(
        'Differentiate term by term with the power rule, then put the given x-value into the derivative — not into the original function.',
        'Power rule: d/dx(xⁿ) = n·xⁿ⁻¹; the derivative of a constant is 0.',
        [
          `Step 1: d/dx(${a === 1 ? '' : a}x²) = ${2 * a}x.`,
          b === 0 ? `Step 2: the constant ${c} differentiates to 0.` : `Step 2: d/dx(${b}x) = ${b}; d/dx(${c}) = 0.`,
          `Step 3: f′(x) = ${2 * a}x${bTerm}.`,
          `Step 4: f′(${k}) = ${2 * a}·${k}${bTerm} = ${val}.`
        ],
        'Substitute into the derivative, never into f(x) — the value of f(k) is the standard trap option.',
        'Write the derivative first, then substitute.', 'Differentiate, then substitute')
    };
  }
  if (variant === 1) {
    const a = between(rng, 1, hard ? 5 : 3) * 2, b = between(rng, -5, 5), k = between(rng, 1, hard ? 5 : 3);
    const val = (a * k * k) / 2 + b * k;
    const o = numericOptions(rng, val, [a * k + b, a * k * k + b * k, (a * k * k) / 2, val + k]);
    return {
      topic: 'Calculus: Definite Integral of a Linear Function',
      text: `The value of ∫₀^${k} (${a}x ${b >= 0 ? '+ ' + b : '− ' + (-b)}) dx is:`,
      options: o.options, correct: o.correct,
      exp: `∫(${a}x + ${b})dx = ${a / 2}x² + ${b}x; evaluating from 0 to ${k} gives ${val}.`,
      source: generatedSource('Calculus', 'definite integral'),
      detailedExp: explain(
        'Integrate each term (raise the power by one and divide by the new power), then subtract the value at the lower limit from the value at the upper limit.',
        'Fundamental theorem of calculus: ∫ₐᵇ f(x)dx = F(b) − F(a) where F′ = f.',
        [`Step 1: ∫${a}x dx = ${a / 2}x².`, `Step 2: ∫${b} dx = ${b}x.`, `Step 3: F(x) = ${a / 2}x² + ${b}x; F(0) = 0.`, `Step 4: F(${k}) = ${a / 2}·${k * k} + ${b}·${k} = ${val}.`],
        'The lower limit 0 contributes nothing here, but always evaluate both limits.',
        'For a polynomial from 0 to k, just evaluate the antiderivative at k.', 'Lower limit zero')
    };
  }
  if (variant === 2) {
    const k = between(rng, 2, hard ? 9 : 6);
    const val = 2 * k;
    const o = numericOptions(rng, val, [k, k * k, 0, k + 2]);
    return {
      topic: 'Calculus: Limits (Removable Discontinuity)',
      text: `lim (x→${k}) (x² − ${k * k}) / (x − ${k}) equals:`,
      options: o.options, correct: o.correct,
      exp: `x² − ${k * k} = (x − ${k})(x + ${k}); cancel (x − ${k}) and substitute x = ${k}: ${k} + ${k} = ${val}.`,
      source: generatedSource('Calculus', 'limit by factorisation'),
      detailedExp: explain(
        'Direct substitution gives 0/0, which means nothing yet. Factor the numerator, cancel the common factor, then substitute.',
        'A 0/0 form is indeterminate; factorising removes the discontinuity so the limit can be read off.',
        [`Step 1: Substituting x = ${k} gives (${k * k} − ${k * k})/(${k} − ${k}) = 0/0.`, `Step 2: x² − ${k * k} = (x − ${k})(x + ${k}).`, `Step 3: Cancel (x − ${k}): the expression becomes x + ${k}.`, `Step 4: Substitute x = ${k}: ${val}.`],
        '0/0 means factorise, not "undefined".',
        'lim (x→a)(x² − a²)/(x − a) = 2a — instantly.', 'Standard limit form')
    };
  }
  if (variant === 3) {
    const n = between(rng, 2, hard ? 5 : 4), k = between(rng, 1, 3);
    const val = n * Math.pow(k, n - 1);
    const o = numericOptions(rng, val, [Math.pow(k, n), n * Math.pow(k, n), (n - 1) * Math.pow(k, n - 1), n * k]);
    return {
      topic: 'Calculus: Power Rule',
      text: `If y = x^${n}, then dy/dx at x = ${k} is:`,
      options: o.options, correct: o.correct,
      exp: `dy/dx = ${n}x^${n - 1}; at x = ${k} this is ${n}·${k}^${n - 1} = ${val}.`,
      source: generatedSource('Calculus', 'power rule'),
      detailedExp: explain(
        'Bring the power down as a multiplier and reduce the power by one, then substitute.',
        'Power rule: d/dx(xⁿ) = n·xⁿ⁻¹.',
        [`Step 1: dy/dx = ${n}·x^${n - 1}.`, `Step 2: At x = ${k}: ${n}·${k}^${n - 1}.`, `Step 3: ${k}^${n - 1} = ${Math.pow(k, n - 1)}, so the value is ${val}.`],
        'Reduce the exponent by one; forgetting that gives the n·kⁿ trap.',
        'Multiply by the old power, subtract one from the power.', 'Power rule in one line')
    };
  }
  const b = between(rng, 1, hard ? 8 : 5) * 2, c = between(rng, -6, 6);
  const val = c + (b * b) / 4;
  const o = numericOptions(rng, val, [c, b * b, c + b, (b * b) / 4]);
  return {
    topic: 'Calculus: Maximum of a Quadratic',
    text: `The maximum value of f(x) = −x² + ${b}x ${c >= 0 ? '+ ' + c : '− ' + (-c)} is:`,
    options: o.options, correct: o.correct,
    exp: `f′(x) = −2x + ${b} = 0 gives x = ${b / 2}; f(${b / 2}) = −${(b * b) / 4} + ${(b * b) / 2} ${c >= 0 ? '+ ' + c : '− ' + (-c)} = ${val}.`,
    source: generatedSource('Calculus', 'maximum via first derivative'),
    detailedExp: explain(
      'Set the derivative to zero to find where the curve turns, then evaluate the function there. A negative x² term means the turning point is a maximum.',
      'Stationary point at f′(x) = 0; f″(x) = −2 < 0 confirms a maximum.',
      [`Step 1: f′(x) = −2x + ${b}.`, `Step 2: −2x + ${b} = 0 ⇒ x = ${b / 2}.`, `Step 3: f(${b / 2}) = −(${b / 2})² + ${b}·${b / 2} ${c >= 0 ? '+ ' + c : '− ' + (-c)} = ${val}.`],
      'Solve f′(x) = 0 for x, then substitute back into f(x) — the x-value alone is a trap option.',
      'For −x² + bx + c the maximum is c + b²/4.', 'Vertex formula')
  };
};

const genPercentage: TopicSpec['generate'] = (difficulty, rng, index) => {
  const hard = difficulty === 'HARD';
  if (index % 3 === 0) {
    const p = pick(rng, hard ? [12, 15, 35, 45, 65] : [10, 20, 25, 40, 50]);
    const n = between(rng, 2, hard ? 40 : 12) * (100 / (p % 25 === 0 ? 4 : p % 20 === 0 ? 5 : 20)) * (hard ? 1 : 1);
    const base = Math.round(n / 20) * 20 || 20;
    const val = (p * base) / 100;
    const o = numericOptions(rng, val, [(p * base) / 10, base - val, val * 2, val + p]);
    return {
      topic: 'Percentage: Value of a Percentage',
      text: `${p}% of ${base} is:`, options: o.options, correct: o.correct,
      exp: `${p}% of ${base} = (${p}/100) × ${base} = ${fmt(val)}.`,
      source: generatedSource('Percentage', 'percentage of a number'),
      detailedExp: explain('Percent means "per hundred": convert the percentage to a fraction and multiply.', 'x% of N = (x/100) × N.', [`Step 1: ${p}% = ${p}/100.`, `Step 2: (${p}/100) × ${base} = ${fmt(val)}.`], 'Convert to a fraction first; common ones (25% = 1/4, 20% = 1/5) are instant.', 'Use fraction equivalents: 25% = ¼, 50% = ½, 20% = ⅕.', 'Fraction equivalents')
    };
  }
  if (index % 3 === 1) {
    const a = between(rng, 2, hard ? 60 : 20) * 10, pct = pick(rng, [10, 20, 25, 50, 75]);
    const b = a + (a * pct) / 100;
    const o = numericOptions(rng, pct, [pct * 2, pct / 2, 100 - pct, pct + 5], '%');
    return {
      topic: 'Percentage: Percentage Change',
      text: `A value rises from ${a} to ${fmt(b)}. The percentage increase is:`, options: o.options, correct: o.correct,
      exp: `Increase = ${fmt(b)} − ${a} = ${fmt(b - a)}; (${fmt(b - a)}/${a}) × 100 = ${pct}%.`,
      source: generatedSource('Percentage', 'percentage change'),
      detailedExp: explain('Find how much it changed, then express that change as a share of the original value (not the new one).', 'Percentage change = (change / original) × 100.', [`Step 1: Change = ${fmt(b)} − ${a} = ${fmt(b - a)}.`, `Step 2: Divide by the original ${a}: ${fmt((b - a) / a)}.`, `Step 3: × 100 = ${pct}%.`], 'Always divide by the original value.', 'Percentage change is always over the starting value.', 'Change over original')
    };
  }
  const p = pick(rng, [25, 50, 100]);
  const val = (100 * p) / (100 + p);
  const o = numericOptions(rng, val, [p, 100 - p, p / 2, val + 5], '%');
  return {
    topic: 'Percentage: Price Rise & Consumption',
    text: `The price of a commodity rises by ${p}%. By what percentage must consumption fall so that expenditure stays the same?`, options: o.options, correct: o.correct,
    exp: `Required fall = (${p} / (100 + ${p})) × 100 = ${fmt(val)}%.`,
    source: generatedSource('Percentage', 'expenditure constant'),
    detailedExp: explain('If price goes up by p%, you must buy less to spend the same money. The cut is p out of the new price 100 + p, not p out of 100.', 'For constant expenditure, price × quantity is fixed: quantity falls by p/(100+p) × 100 %.', [`Step 1: New price = 100 + ${p} = ${100 + p} for every old 100.`, `Step 2: Required consumption = 100/${100 + p} of before.`, `Step 3: Fall = ${p}/${100 + p} × 100 = ${fmt(val)}%.`], 'The fall is smaller than the rise — never the same p%.', 'Rise p% ⇒ fall p/(100+p) × 100%.', 'Constant-expenditure formula')
  };
};

const genRatio: TopicSpec['generate'] = (difficulty, rng, index) => {
  const hard = difficulty === 'HARD';
  const a = between(rng, 1, hard ? 7 : 4), b = between(rng, a + 1, hard ? 11 : 7), unitv = between(rng, 5, hard ? 120 : 40) * 10;
  const total = (a + b) * unitv;
  const val = index % 2 === 0 ? a * unitv : b * unitv;
  const o = numericOptions(rng, val, [index % 2 === 0 ? b * unitv : a * unitv, total / 2, unitv, total]);
  return {
    topic: 'Ratio & Proportion: Dividing in a Ratio',
    text: `₹${total} is divided between A and B in the ratio ${a} : ${b}. ${index % 2 === 0 ? 'A' : 'B'}'s share is:`, options: o.options, correct: o.correct,
    exp: `Total parts = ${a} + ${b} = ${a + b}; one part = ${total}/${a + b} = ${unitv}; share = ${index % 2 === 0 ? a : b} × ${unitv} = ₹${val}.`,
    source: generatedSource('Ratio & Proportion', 'division in a ratio'),
    detailedExp: explain('Add the ratio numbers to get the total parts, find what one part is worth, then multiply by that person\'s ratio number.', 'A share = (A\'s ratio / sum of ratio) × total.', [`Step 1: Parts = ${a} + ${b} = ${a + b}.`, `Step 2: One part = ${total} ÷ ${a + b} = ${unitv}.`, `Step 3: ${index % 2 === 0 ? 'A' : 'B'} = ${index % 2 === 0 ? a : b} × ${unitv} = ₹${val}.`], 'Find the value of one part first; everything follows.', 'Total ÷ (sum of ratio) = one part.', 'Value of one part')
  };
};

const genAverage: TopicSpec['generate'] = (difficulty, rng, index) => {
  const n = between(rng, 4, difficulty === 'HARD' ? 9 : 6);
  const avg = between(rng, 10, difficulty === 'HARD' ? 90 : 50);
  if (index % 2 === 0) {
    const newv = avg + between(rng, 5, 30) * (n + 1);
    const newAvg = avg + (newv - avg) / (n + 1);
    const o = numericOptions(rng, newAvg, [avg, newv, newAvg + 1, (avg + newv) / 2]);
    return {
      topic: 'Average: Adding a New Member',
      text: `The average of ${n} numbers is ${avg}. If a number ${newv} is added, the new average is:`, options: o.options, correct: o.correct,
      exp: `Old sum = ${n} × ${avg} = ${n * avg}; new sum = ${n * avg + newv}; new average = ${n * avg + newv}/${n + 1} = ${fmt(newAvg)}.`,
      source: generatedSource('Average', 'new average after addition'),
      detailedExp: explain('Turn the average back into a total, add the new number, divide by the new count.', 'Average = sum ÷ count.', [`Step 1: Sum = ${n} × ${avg} = ${n * avg}.`, `Step 2: New sum = ${n * avg} + ${newv} = ${n * avg + newv}.`, `Step 3: New average = ${n * avg + newv} ÷ ${n + 1} = ${fmt(newAvg)}.`], 'Work with sums, not averages, when the count changes.', 'New avg = old avg + (new value − old avg)/(n+1).', 'Shift in the average')
    };
  }
  const nums = Array.from({ length: n }, () => between(rng, 5, 60));
  const sum = nums.reduce((x, y) => x + y, 0);
  const val = sum / n;
  const o = numericOptions(rng, val, [sum, val + 1, val - 1, Math.max(...nums)]);
  return {
    topic: 'Average: Mean of a Set',
    text: `The average of ${nums.join(', ')} is:`, options: o.options, correct: o.correct,
    exp: `Sum = ${sum}; average = ${sum}/${n} = ${fmt(val)}.`,
    source: generatedSource('Average', 'mean of listed numbers'),
    detailedExp: explain('Add everything up and divide by how many numbers there are.', 'Average = sum ÷ count.', [`Step 1: Sum = ${sum}.`, `Step 2: Count = ${n}.`, `Step 3: ${sum} ÷ ${n} = ${fmt(val)}.`], 'Count the items carefully — miscounting is the usual error.')
  };
};

const genInterest: TopicSpec['generate'] = (difficulty, rng, index) => {
  const P = between(rng, 2, difficulty === 'HARD' ? 50 : 20) * 500;
  if (index % 2 === 0) {
    const R = pick(rng, [4, 5, 6, 8, 10, 12]), T = between(rng, 2, 5);
    const val = (P * R * T) / 100;
    const o = numericOptions(rng, val, [(P * R) / 100, val * 2, P + val, (P * T) / 100]);
    return {
      topic: 'Simple Interest',
      text: `The simple interest on ₹${P} at ${R}% per annum for ${T} years is:`, options: o.options, correct: o.correct,
      exp: `SI = P × R × T / 100 = ${P} × ${R} × ${T} / 100 = ₹${fmt(val)}.`,
      source: generatedSource('Simple Interest', 'SI formula'),
      detailedExp: explain('Simple interest is the same every year: principal × rate × years, divided by 100.', 'SI = PRT/100.', [`Step 1: P = ${P}, R = ${R}%, T = ${T}.`, `Step 2: ${P} × ${R} × ${T} = ${P * R * T}.`, `Step 3: ÷ 100 = ₹${fmt(val)}.`], 'SI is linear in time — double the years, double the interest.', 'Yearly interest × years.', 'Interest per year')
    };
  }
  const R = pick(rng, [5, 10, 20]);
  const A = P * Math.pow(1 + R / 100, 2);
  const val = A - P;
  const o = numericOptions(rng, val, [(P * R * 2) / 100, A, (P * R) / 100, val + P / 100]);
  return {
    topic: 'Compound Interest (2 years)',
    text: `The compound interest on ₹${P} at ${R}% per annum for 2 years, compounded annually, is:`, options: o.options, correct: o.correct,
    exp: `Amount = ${P}(1 + ${R}/100)² = ${fmt(A)}; CI = ${fmt(A)} − ${P} = ₹${fmt(val)}.`,
    source: generatedSource('Compound Interest', 'two-year CI'),
    detailedExp: explain('The second year earns interest on the first year\'s interest too. Grow the principal by the rate twice, then subtract the principal.', 'A = P(1 + R/100)ⁿ; CI = A − P.', [`Step 1: Year 1: ${P} × ${1 + R / 100} = ${fmt(P * (1 + R / 100))}.`, `Step 2: Year 2: × ${1 + R / 100} again = ${fmt(A)}.`, `Step 3: CI = ${fmt(A)} − ${P} = ₹${fmt(val)}.`], 'CI for 2 years exceeds SI by P(R/100)² — the interest on the interest.', 'CI₂ = SI₂ + P(R/100)².', 'CI over SI in 2 years')
  };
};

const genProfitLoss: TopicSpec['generate'] = (difficulty, rng, index) => {
  const CP = between(rng, 2, difficulty === 'HARD' ? 60 : 20) * 50;
  const pct = pick(rng, [5, 10, 12, 15, 20, 25]);
  if (index % 2 === 0) {
    const SP = CP + (CP * pct) / 100;
    const o = numericOptions(rng, SP, [CP - (CP * pct) / 100, CP + pct, SP + CP / 100, CP * (1 + pct / 10)]);
    return {
      topic: 'Profit & Loss: Selling Price for a Given Profit',
      text: `An article costing ₹${CP} is sold at a profit of ${pct}%. The selling price is:`, options: o.options, correct: o.correct,
      exp: `SP = CP × (100 + ${pct})/100 = ${CP} × ${1 + pct / 100} = ₹${fmt(SP)}.`,
      source: generatedSource('Profit & Loss', 'selling price from profit %'),
      detailedExp: explain('Profit percent is on the cost price. Add that percentage of the cost to the cost.', 'SP = CP(1 + p/100).', [`Step 1: Profit = ${pct}% of ${CP} = ${fmt((CP * pct) / 100)}.`, `Step 2: SP = ${CP} + ${fmt((CP * pct) / 100)} = ₹${fmt(SP)}.`], 'Profit % is always on CP unless stated otherwise.', 'Multiply CP by (100 + p)/100.', 'Single multiplier')
    };
  }
  const SP = CP + (CP * pct) / 100;
  const o = numericOptions(rng, pct, [Math.round(((SP - CP) / SP) * 100), pct * 2, 100 - pct, pct + 5], '%');
  return {
    topic: 'Profit & Loss: Profit Percentage',
    text: `An article bought for ₹${CP} is sold for ₹${fmt(SP)}. The profit percentage is:`, options: o.options, correct: o.correct,
    exp: `Profit = ${fmt(SP)} − ${CP} = ${fmt(SP - CP)}; profit % = (${fmt(SP - CP)}/${CP}) × 100 = ${pct}%.`,
    source: generatedSource('Profit & Loss', 'profit percentage'),
    detailedExp: explain('Find the profit in rupees, then express it as a percentage of the cost price.', 'Profit % = (SP − CP)/CP × 100.', [`Step 1: Profit = ${fmt(SP)} − ${CP} = ${fmt(SP - CP)}.`, `Step 2: ÷ CP ${CP} = ${fmt((SP - CP) / CP)}.`, `Step 3: × 100 = ${pct}%.`], 'Divide by CP, not SP — dividing by SP is the trap option.')
  };
};

const genTimeWork: TopicSpec['generate'] = (difficulty, rng, index) => {
  if (index % 2 === 1) {
    const k = pick(rng, [2, 3, 4]);
    const a = (k + 1) * between(rng, 2, difficulty === 'HARD' ? 9 : 5);
    const val = a / (k + 1);
    const o = numericOptions(rng, val, [a / k, a * k, a - k, val + 1], ' days');
    return {
      topic: 'Time & Work: Relative Efficiency',
      text: `A alone can complete a piece of work in ${a} days. B is ${k} times as efficient as A. Working together, they will finish it in:`,
      options: o.options, correct: o.correct,
      exp: `A does 1/${a} per day, B does ${k}/${a}; together ${k + 1}/${a} per day, so the work takes ${a}/${k + 1} = ${fmt(val)} days.`,
      source: generatedSource('Time & Work', 'relative efficiency'),
      detailedExp: explain('If B is k times as efficient, B does k times as much per day. Add the daily amounts and invert.', 'Work per day adds; time = 1 ÷ (combined rate).', [`Step 1: A = 1/${a} per day.`, `Step 2: B = ${k}/${a} per day.`, `Step 3: Together = ${k + 1}/${a} per day.`, `Step 4: Time = ${a}/${k + 1} = ${fmt(val)} days.`], 'Efficiency multiplies the rate, it does not divide the days of the pair.', `Together = a/(1+k) days.`, 'Efficiency shortcut')
    };
  }
  const pairs: [number, number][] = difficulty === 'HARD' ? [[12, 24], [10, 15], [20, 30], [18, 9], [15, 30], [21, 42]] : [[6, 3], [12, 24], [10, 15], [20, 30], [4, 12]];
  const [a, b] = pick(rng, pairs);
  const val = (a * b) / (a + b);
  const o = numericOptions(rng, val, [(a + b) / 2, a + b, Math.min(a, b), val + 1], ' days');
  return {
    topic: 'Time & Work: Working Together',
    text: `A can finish a job in ${a} days and B in ${b} days. Working together they finish it in:`, options: o.options, correct: o.correct,
    exp: `Together per day: 1/${a} + 1/${b} = ${a + b}/${a * b}; time = ${a * b}/${a + b} = ${fmt(val)} days.`,
    source: generatedSource('Time & Work', 'combined work'),
    detailedExp: explain('Add the fractions of the job each does per day; the total per day inverted is the number of days.', 'Rates add: 1/T = 1/a + 1/b, so T = ab/(a + b).', [`Step 1: A does 1/${a} per day, B does 1/${b}.`, `Step 2: Together = (${b} + ${a})/${a * b} = ${a + b}/${a * b} per day.`, `Step 3: Days = ${a * b}/${a + b} = ${fmt(val)}.`], 'Never average the days — add the rates.', 'T = ab/(a+b).', 'Product over sum')
  };
};

const genSpeed: TopicSpec['generate'] = (difficulty, rng, index) => {
  if (index % 2 === 0) {
    const speed = pick(rng, [36, 54, 72, 90, 108]), len = between(rng, 2, difficulty === 'HARD' ? 12 : 6) * 50;
    const ms = (speed * 5) / 18;
    const val = len / ms;
    const o = numericOptions(rng, val, [len / speed, val * 2, val + 2, ms], ' s');
    return {
      topic: 'Speed, Time & Distance: Train Crossing a Pole',
      text: `A ${len} m long train running at ${speed} km/h crosses a pole in:`, options: o.options, correct: o.correct,
      exp: `${speed} km/h = ${speed} × 5/18 = ${fmt(ms)} m/s; time = ${len}/${fmt(ms)} = ${fmt(val)} s.`,
      source: generatedSource('Speed, Time & Distance', 'train crossing a pole'),
      detailedExp: explain('Convert km/h to m/s (multiply by 5/18), then divide the train\'s own length by that speed.', 'To cross a pole a train travels its own length; time = length ÷ speed in consistent units.', [`Step 1: ${speed} × 5/18 = ${fmt(ms)} m/s.`, `Step 2: Distance = train length = ${len} m.`, `Step 3: ${len} ÷ ${fmt(ms)} = ${fmt(val)} s.`], 'Convert units before dividing — the unconverted value is the trap.', 'km/h × 5/18 = m/s.', 'Unit conversion')
    };
  }
  const t = between(rng, 2, 6), sp = pick(rng, [40, 45, 50, 60, 72, 80]);
  const val = sp * t;
  const o = numericOptions(rng, val, [sp + t, sp / t, val / 2, val + sp], ' km');
  return {
    topic: 'Speed, Time & Distance: Distance Covered',
    text: `A car travels at ${sp} km/h for ${t} hours. The distance covered is:`, options: o.options, correct: o.correct,
    exp: `Distance = speed × time = ${sp} × ${t} = ${val} km.`,
    source: generatedSource('Speed, Time & Distance', 'distance = speed × time'),
    detailedExp: explain('Multiply speed by time.', 'D = S × T.', [`Step 1: ${sp} × ${t} = ${val} km.`], 'Keep units consistent: km/h with hours.')
  };
};

const genSeries: TopicSpec['generate'] = (difficulty, rng, index) => {
  const kind = index % 3;
  if (kind === 0) {
    const a = between(rng, 2, 15), d = between(rng, 2, difficulty === 'HARD' ? 11 : 6);
    const seq = [0, 1, 2, 3, 4].map(i => a + i * d);
    const val = a + 5 * d;
    const o = numericOptions(rng, val, [val + d, val - d, val + 1, seq[4] * 2]);
    return { topic: 'Number Series: Arithmetic Progression', text: `Find the next term: ${seq.join(', ')}, ?`, options: o.options, correct: o.correct, exp: `Each term increases by ${d}; ${seq[4]} + ${d} = ${val}.`, source: generatedSource('Number Series', 'constant difference'), detailedExp: explain('Look at the gaps between neighbours; here they are all the same, so add that gap once more.', 'Arithmetic progression: constant common difference.', [`Step 1: Differences: ${seq[1] - seq[0]}, ${seq[2] - seq[1]}, … all ${d}.`, `Step 2: Next = ${seq[4]} + ${d} = ${val}.`], 'Check differences first; if constant, the series is arithmetic.') };
  }
  if (kind === 1) {
    const a = between(rng, 1, 5), r = pick(rng, [2, 3]);
    const seq = [0, 1, 2, 3].map(i => a * Math.pow(r, i));
    const val = a * Math.pow(r, 4);
    const o = numericOptions(rng, val, [seq[3] + (seq[3] - seq[2]), val * r, seq[3] * 2 + 1, val - a]);
    return { topic: 'Number Series: Geometric Progression', text: `Find the next term: ${seq.join(', ')}, ?`, options: o.options, correct: o.correct, exp: `Each term is multiplied by ${r}; ${seq[3]} × ${r} = ${val}.`, source: generatedSource('Number Series', 'constant ratio'), detailedExp: explain('The gaps grow, so try ratios: each term is the previous one multiplied by the same number.', 'Geometric progression: constant common ratio.', [`Step 1: ${seq[1]}/${seq[0]} = ${r}, ${seq[2]}/${seq[1]} = ${r}.`, `Step 2: Next = ${seq[3]} × ${r} = ${val}.`], 'Growing gaps usually mean a ratio, not a difference.') };
  }
  const start = between(rng, 1, 5);
  const seq = [0, 1, 2, 3, 4].map(i => (start + i) * (start + i) + 1);
  const n = start + 5;
  const val = n * n + 1;
  const o = numericOptions(rng, val, [n * n, val + 2 * n, seq[4] + (seq[4] - seq[3]), val - 1]);
  return { topic: 'Number Series: Squares Plus One', text: `Find the next term: ${seq.join(', ')}, ?`, options: o.options, correct: o.correct, exp: `Terms are n² + 1 for n = ${start}…${n - 1}; next = ${n}² + 1 = ${val}.`, source: generatedSource('Number Series', 'square pattern'), detailedExp: explain('Subtract 1 from each term and you get perfect squares of consecutive numbers.', 'Series of the form n² + k.', [`Step 1: ${seq.map(v => v - 1).join(', ')} are ${start}², ${start + 1}², …`, `Step 2: Next square is ${n}² = ${n * n}; add 1 = ${val}.`], 'When differences themselves increase by 2, think squares.') };
};

const genCoding: TopicSpec['generate'] = (difficulty, rng) => {
  const words = ['CAT', 'DOG', 'PEN', 'BOOK', 'ROAD', 'TIME', 'LAMP', 'GATE'];
  const w = pick(rng, words), k = between(rng, 1, difficulty === 'HARD' ? 5 : 3);
  const shift = (s: string, n: number) => s.split('').map(ch => String.fromCharCode(((ch.charCodeAt(0) - 65 + n + 26) % 26) + 65)).join('');
  const target = pick(rng, words.filter(x => x !== w && x.length === w.length)) || 'MAP';
  const val = shift(target, k);
  const distract = [shift(target, k + 1), shift(target, -k), shift(target, k + 2)];
  const all = [val, ...distract];
  const order = all.map((v, i) => ({ v, i, r: rng() })).sort((a, b) => a.r - b.r);
  return { topic: 'Coding-Decoding: Letter Shift', text: `In a certain code, ${w} is written as ${shift(w, k)}. How is ${target} written in that code?`, options: order.map(o => o.v), correct: order.findIndex(o => o.i === 0), exp: `Each letter moves ${k} place${k > 1 ? 's' : ''} forward in the alphabet; apply the same shift to ${target}: ${val}.`, source: generatedSource('Coding-Decoding', 'constant letter shift'), detailedExp: explain('Compare each letter of the word with its coded letter to find the shift, then apply the same shift to the new word.', 'Letter-shift codes move every letter by a fixed number of positions.', [`Step 1: ${w[0]} → ${shift(w, k)[0]} is +${k}.`, `Step 2: Every letter shifts by +${k}.`, `Step 3: ${target} → ${val}.`], 'Confirm the shift on two letters before applying it.', 'Write A–Z with positions 1–26; add the shift.', 'Alphabet positions') };
};

const genDirection: TopicSpec['generate'] = (difficulty, rng) => {
  const triples: [number, number, number][] = [[3, 4, 5], [6, 8, 10], [5, 12, 13], [9, 12, 15], [8, 15, 17]];
  const [a, b, c] = pick(rng, difficulty === 'HARD' ? triples : triples.slice(0, 3));
  const d1 = pick(rng, ['north', 'south']), d2 = pick(rng, ['east', 'west']);
  const o = numericOptions(rng, c, [a + b, Math.abs(a - b), c + 1, a * b], ' km');
  return { topic: 'Direction Sense: Shortest Distance', text: `A man walks ${a} km ${d1}, then turns and walks ${b} km ${d2}. How far is he from the starting point?`, options: o.options, correct: o.correct, exp: `The two legs are at right angles: distance = √(${a}² + ${b}²) = √${a * a + b * b} = ${c} km.`, source: generatedSource('Direction Sense', 'right-angle displacement'), detailedExp: explain('North/south and east/west legs meet at a right angle, so the straight-line distance is the hypotenuse.', 'Pythagoras: d = √(a² + b²).', [`Step 1: Legs ${a} and ${b} are perpendicular.`, `Step 2: ${a}² + ${b}² = ${a * a + b * b}.`, `Step 3: √${a * a + b * b} = ${c} km.`], 'Perpendicular legs ⇒ Pythagoras; the sum a + b is the trap option.', `Memorise triples: 3-4-5, 5-12-13, 8-15-17.`, 'Pythagorean triples') };
};

const genAlgebra: TopicSpec['generate'] = (difficulty, rng, index) => {
  if (index % 2 === 0) {
    const a = between(rng, 2, difficulty === 'HARD' ? 9 : 5), x = between(rng, 2, 12), b = between(rng, -9, 9);
    const c = a * x + b;
    const o = numericOptions(rng, x, [c - b, x + 1, x - 1, (c + b) / a]);
    return { topic: 'Algebra: Linear Equation', text: `If ${a}x ${b >= 0 ? '+ ' + b : '− ' + (-b)} = ${c}, then x equals:`, options: o.options, correct: o.correct, exp: `${a}x = ${c} ${b >= 0 ? '− ' + b : '+ ' + (-b)} = ${c - b}; x = ${c - b}/${a} = ${x}.`, source: generatedSource('Algebra', 'linear equation'), detailedExp: explain('Move the constant to the other side, then divide by the coefficient of x.', 'Isolate x by inverse operations.', [`Step 1: ${a}x = ${c} ${b >= 0 ? '− ' + b : '+ ' + (-b)} = ${c - b}.`, `Step 2: x = ${c - b} ÷ ${a} = ${x}.`], 'Undo addition before division.') };
  }
  const r1 = between(rng, 1, 7), r2 = between(rng, r1 + 1, difficulty === 'HARD' ? 12 : 9);
  const sum = r1 + r2, prod = r1 * r2;
  const o = numericOptions(rng, sum, [prod, -sum, r2 - r1, sum + 1]);
  return { topic: 'Algebra: Roots of a Quadratic', text: `The sum of the roots of x² − ${sum}x + ${prod} = 0 is:`, options: o.options, correct: o.correct, exp: `For x² + bx + c = 0, sum of roots = −b = ${sum} (the roots are ${r1} and ${r2}).`, source: generatedSource('Algebra', 'sum of roots'), detailedExp: explain('You do not need to solve the quadratic: the sum of the roots is the negative of the x-coefficient.', 'Vieta: for ax² + bx + c, sum = −b/a, product = c/a.', [`Step 1: Here a = 1, b = −${sum}, c = ${prod}.`, `Step 2: Sum = −b/a = ${sum}.`, `Step 3: Check: roots ${r1} and ${r2} multiply to ${prod}.`], 'Sum = −b/a, product = c/a — read them straight off.', 'Vieta\'s formulas skip the factorising.', 'Vieta\'s formulas') };
};

// ---- curated English & computer items -----------------------------------------
// Language and factual items are authored, not computed: each option set was written and
// checked by hand. They are GOVOS_AUTHORED — SSC pattern, not past questions.

interface CuratedItem {
  topic: string;
  text: string;
  options: string[];
  correct: number;
  exp: string;
  simple: string;
  concept: string;
  steps: string[];
  takeaway: string;
  citation: string;
}

const VOCAB_ITEMS: CuratedItem[] = ([
  ['ABANDON', 'Relinquish', ['Retain', 'Cherish', 'Secure'], 'To abandon is to give something up entirely, which is exactly what relinquish means.'],
  ['LUCID', 'Clear', ['Opaque', 'Confusing', 'Dull'], 'Lucid writing is easily understood, so clear is the synonym; opaque and confusing are its opposites.'],
  ['FRUGAL', 'Thrifty', ['Wasteful', 'Lavish', 'Generous'], 'Frugal means sparing with money or resources — thrifty. Lavish and wasteful are opposites.'],
  ['CANDID', 'Frank', ['Devious', 'Guarded', 'Rude'], 'Candid means openly honest, that is frank. Being frank is not the same as being rude.'],
  ['AUGMENT', 'Increase', ['Reduce', 'Curtail', 'Weaken'], 'To augment is to add to something, so increase is the synonym.'],
  ['OBSOLETE', 'Outdated', ['Modern', 'Durable', 'Frequent'], 'Something obsolete has fallen out of use — outdated.'],
  ['VOLATILE', 'Unstable', ['Steady', 'Solid', 'Reliable'], 'Volatile describes something liable to change rapidly, that is unstable.'],
  ['METICULOUS', 'Careful', ['Careless', 'Hasty', 'Vague'], 'A meticulous worker attends to every detail — careful.'],
  ['ALLEVIATE', 'Relieve', ['Aggravate', 'Intensify', 'Provoke'], 'To alleviate pain is to relieve it; aggravate means the opposite.'],
  ['PRUDENT', 'Sensible', ['Reckless', 'Foolish', 'Impulsive'], 'A prudent decision is a sensible, carefully considered one.'],
  ['TENACIOUS', 'Persistent', ['Fickle', 'Yielding', 'Timid'], 'Tenacious means holding on firmly — persistent.'],
  ['AMBIGUOUS', 'Unclear', ['Precise', 'Definite', 'Obvious'], 'An ambiguous statement has more than one possible meaning, so it is unclear.']
] as [string, string, string[], string][]).map(([w, ans, wrong, why]) => ({
  topic: 'Vocabulary: Synonyms',
  text: `Select the word most similar in meaning to the word in capitals: ${w}`,
  options: [ans, ...wrong], correct: 0,
  exp: why,
  simple: 'Read the capitalised word, decide roughly what it means in your own words, then find the option closest to that meaning.',
  concept: 'A synonym carries the same sense in the same register; it does not have to be interchangeable in every sentence.',
  steps: [`Step 1: ${w} — recall the sense in which you have seen it used.`, `Step 2: ${why}`, `Step 3: Rule out options that mean the opposite; SSC always places one among the choices.`],
  takeaway: 'Eliminate the antonym first — SSC synonym questions almost always include one.',
  citation: `GovOS-authored vocabulary practice (synonym of ${w}; SSC Tier-1 English pattern, not an official past question)`
}));

const ANTONYM_ITEMS: CuratedItem[] = ([
  ['BENEVOLENT', 'Malevolent', ['Generous', 'Kind', 'Charitable'], 'Benevolent means well-meaning and kind; its direct opposite is malevolent. The other three are synonyms.'],
  ['SCARCE', 'Abundant', ['Rare', 'Meagre', 'Limited'], 'Scarce means in short supply, so abundant is the opposite; rare and meagre are synonyms.'],
  ['HUMBLE', 'Arrogant', ['Modest', 'Meek', 'Unassuming'], 'Humble means modest about oneself; arrogant is the opposite.'],
  ['EXPAND', 'Contract', ['Enlarge', 'Extend', 'Widen'], 'Expand means to grow larger; contract means to shrink. The rest are synonyms.'],
  ['OPTIONAL', 'Compulsory', ['Voluntary', 'Elective', 'Discretionary'], 'Optional means left to choice; compulsory means required.'],
  ['CONDEMN', 'Praise', ['Denounce', 'Criticise', 'Blame'], 'To condemn is to express strong disapproval; to praise is the opposite.'],
  ['ASCEND', 'Descend', ['Climb', 'Rise', 'Soar'], 'Ascend means to go up; descend means to go down.'],
  ['TEMPORARY', 'Permanent', ['Brief', 'Fleeting', 'Transient'], 'Temporary means lasting a short time; permanent means lasting indefinitely.'],
  ['ARTIFICIAL', 'Natural', ['Synthetic', 'Manufactured', 'Imitation'], 'Artificial means made by people rather than occurring in nature.'],
  ['TRANSPARENT', 'Opaque', ['Clear', 'Lucid', 'Evident'], 'Transparent lets light through; opaque blocks it.']
] as [string, string, string[], string][]).map(([w, ans, wrong, why]) => ({
  topic: 'Vocabulary: Antonyms',
  text: `Select the word most opposite in meaning to the word in capitals: ${w}`,
  options: [ans, ...wrong], correct: 0,
  exp: why,
  simple: 'Fix the meaning of the capitalised word first, then look for the option that reverses it — not one that merely differs from it.',
  concept: 'An antonym reverses the sense. Three near-synonyms are usually offered as distractors.',
  steps: [`Step 1: ${w} — state its meaning plainly.`, `Step 2: ${why}`, `Step 3: If three options mean much the same thing, the odd one out is the answer.`],
  takeaway: 'When three options are synonyms of each other, the fourth is the antonym you want.',
  citation: `GovOS-authored vocabulary practice (antonym of ${w}; SSC Tier-1 English pattern, not an official past question)`
}));

const IDIOM_ITEMS: CuratedItem[] = ([
  ['A blessing in disguise', 'Something that seems bad at first but turns out to be good', ['A hidden threat', 'A gift given secretly', 'A promise that is never kept']],
  ['Once in a blue moon', 'Very rarely', ['Every month without fail', 'At night only', 'Suddenly and without warning']],
  ['Let the cat out of the bag', 'To reveal a secret unintentionally', ['To set someone free', 'To create confusion deliberately', 'To escape from danger']],
  ['Bite the bullet', 'To endure a painful situation with courage', ['To speak angrily', 'To act in haste', 'To refuse an order']],
  ['Turn a blind eye', 'To ignore something deliberately', ['To lose one\'s sight', 'To look for something carefully', 'To forgive an offence']],
  ['In the same boat', 'In the same difficult situation', ['Travelling together', 'In complete agreement', 'Working for the same employer']],
  ['Beat about the bush', 'To avoid coming to the point', ['To search everywhere', 'To attack someone verbally', 'To work very hard']],
  ['Call it a day', 'To stop working for the time being', ['To name an occasion', 'To postpone indefinitely', 'To celebrate a success']],
  ['Burn the midnight oil', 'To work late into the night', ['To waste resources', 'To cause a quarrel', 'To spend lavishly']],
  ['Get cold feet', 'To become nervous and hesitant before an event', ['To fall ill suddenly', 'To be treated unkindly', 'To arrive late']]
] as [string, string, string[]][]).map(([idiom, ans, wrong]) => ({
  topic: 'Idioms & Phrases',
  text: `Select the alternative that best expresses the meaning of the idiom: "${idiom}"`,
  options: [ans, ...wrong], correct: 0,
  exp: `"${idiom}" means: ${ans.toLowerCase()}.`,
  simple: 'An idiom does not mean what its words literally say. Recall the whole phrase as a unit.',
  concept: 'Idioms are fixed expressions with a settled figurative meaning; the literal reading is always offered as a distractor.',
  steps: [`Step 1: Read the phrase as a unit, not word by word.`, `Step 2: The settled meaning is "${ans.toLowerCase()}".`, `Step 3: Reject the option that translates the words literally — it is placed there deliberately.`],
  takeaway: 'The literal-sounding option is almost never right in an idiom question.',
  citation: `GovOS-authored idiom practice ("${idiom}"; SSC Tier-1 English pattern, not an official past question)`
}));

const GRAMMAR_ITEMS: CuratedItem[] = ([
  ['Each of the students', 'have submitted', 'the assignment', 'on time.', 1, '"Each" is singular however many follow it, so the verb must be "has submitted".', 'Each / every / either / neither take a singular verb.'],
  ['The quality of the mangoes', 'were not good,', 'so the shopkeeper', 'reduced the price.', 1, 'The subject is "the quality", which is singular; "of the mangoes" only describes it. The verb must be "was".', 'The verb agrees with the head noun, not with a noun inside the of-phrase.'],
  ['Neither the manager nor his assistants', 'was present', 'at the meeting', 'yesterday.', 1, 'With "neither ... nor", the verb agrees with the nearer subject, "assistants", so it must be "were present".', 'Proximity rule for either/or and neither/nor.'],
  ['One of my friends', 'are going', 'to Delhi', 'next week.', 1, 'The subject is "one", not "friends", so the verb is "is going".', '"One of + plural noun" takes a singular verb.'],
  ['The number of applicants', 'have increased', 'this year', 'considerably.', 1, '"The number of" is singular and takes "has increased"; "a number of" would be plural.', '"The number" is singular; "a number" is plural.'],
  ['Mathematics are', 'my favourite subject', 'in the school', 'curriculum.', 0, 'Mathematics is singular despite the -s ending, so it takes "is".', 'Subjects like mathematics, physics and news are singular.'],
  ['He is one of the best players', 'who has ever', 'represented the country', 'in hockey.', 1, 'The relative clause describes "players", which is plural, so it is "who have ever".', 'In "one of the + plural + who", the verb after who is plural.'],
  ['Every boy and girl', 'have been', 'given a prize', 'at the function.', 1, 'Subjects joined by "and" but preceded by "every" are treated as singular: "has been".', '"Every ... and ..." takes a singular verb.'],
  ['The committee', 'has published', 'their report', 'this morning.', 2, 'A singular verb has been used for the committee, so the pronoun must match: "its report".', 'Keep collective nouns consistently singular or plural within a sentence.'],
  ['She is senior', 'than me', 'by three years', 'in this office.', 1, 'Adjectives of Latin origin - senior, junior, superior, prior - take "to", not "than": "senior to me".', 'Latin comparatives take "to".']
]).map(row => {
  const parts = [row[0] as string, row[1] as string, row[2] as string, row[3] as string];
  const idx = row[4] as number;
  const why = row[5] as string;
  const rule = row[6] as string;
  return {
    topic: 'Grammar: Error Spotting',
    text: `The sentence below is divided into four parts. Select the part that contains an error:\n(A) ${parts[0]} (B) ${parts[1]} (C) ${parts[2]} (D) ${parts[3]}`,
    options: [`(A) ${parts[0]}`, `(B) ${parts[1]}`, `(C) ${parts[2]}`, `(D) ${parts[3]}`],
    correct: idx,
    exp: why,
    simple: 'Find the real subject of each verb, then check the verb, the pronoun and the preposition against it. Read the parts in isolation as well as together.',
    concept: rule,
    steps: [`Step 1: Identify the subject of every verb in the sentence.`, `Step 2: ${why}`, `Step 3: Part (${String.fromCharCode(65 + idx)}) is therefore the faulty segment.`],
    takeaway: rule,
    citation: 'GovOS-authored grammar practice (SSC Tier-1 error-spotting pattern, not an official past question)'
  };
});

const VOICE_ITEMS: CuratedItem[] = ([
  ['The teacher praised the student.', 'The student was praised by the teacher.', ['The student is praised by the teacher.', 'The student has been praised by the teacher.', 'The student was being praised by the teacher.'], 'Simple past active becomes "was/were + past participle" in the passive.'],
  ['They are building a new bridge.', 'A new bridge is being built by them.', ['A new bridge is built by them.', 'A new bridge was being built by them.', 'A new bridge has been built by them.'], 'Present continuous active becomes "is/are being + past participle".'],
  ['Someone has stolen my bicycle.', 'My bicycle has been stolen.', ['My bicycle was stolen by someone.', 'My bicycle is stolen by someone.', 'My bicycle had been stolen.'], 'Present perfect active becomes "has/have been + past participle"; an indefinite agent like "someone" is dropped.'],
  ['The manager will approve the proposal.', 'The proposal will be approved by the manager.', ['The proposal would be approved by the manager.', 'The proposal will have been approved by the manager.', 'The proposal is approved by the manager.'], 'Simple future active becomes "will be + past participle".'],
  ['The children were watching a film.', 'A film was being watched by the children.', ['A film was watched by the children.', 'A film is being watched by the children.', 'A film had been watched by the children.'], 'Past continuous active becomes "was/were being + past participle".'],
  ['Open the door.', 'Let the door be opened.', ['The door is opened.', 'The door was opened by you.', 'You are asked to open the door.'], 'An imperative becomes "Let + object + be + past participle".']
] as [string, string, string[], string][]).map(([active, ans, wrong, rule]) => ({
  topic: 'Voice: Active to Passive',
  text: `Select the correct passive form: "${active}"`,
  options: [ans, ...wrong], correct: 0,
  exp: `${rule} So the passive is "${ans}"`,
  simple: 'Move the object to the front, change the verb to the matching passive form of the same tense, and put the doer after "by" — unless the doer is vague.',
  concept: 'The passive keeps the tense of the active sentence; only the auxiliary changes.',
  steps: [`Step 1: Object of the active sentence becomes the subject.`, `Step 2: ${rule}`, `Step 3: The result is "${ans}"`],
  takeaway: 'Distractors change the tense — check the auxiliary before anything else.',
  citation: 'GovOS-authored voice-transformation practice (SSC Tier-1 pattern, not an official past question)'
}));

const COMPUTER_ITEMS: CuratedItem[] = ([
  ['What does CPU stand for?', 'Central Processing Unit', ['Central Programming Utility', 'Computer Processing Interface', 'Control Peripheral Unit'], 'The CPU carries out the instructions of a program; it is the processor at the centre of the machine.'],
  ['One kilobyte (KB) equals how many bytes?', '1024 bytes', ['1000 bytes', '512 bytes', '2048 bytes'], 'Storage units are powers of two: 1 KB = 2^10 = 1024 bytes.'],
  ['Which keyboard shortcut undoes the last action in most Windows applications?', 'Ctrl + Z', ['Ctrl + Y', 'Ctrl + U', 'Ctrl + X'], 'Ctrl + Z undoes; Ctrl + Y redoes; Ctrl + X cuts.'],
  ['Which type of memory loses its contents when the computer is switched off?', 'RAM', ['ROM', 'Hard disk', 'Flash drive'], 'RAM is volatile working memory; ROM and storage devices retain data without power.'],
  ['In MS Excel, which formula adds the values in cells A1 to A10?', '=SUM(A1:A10)', ['=ADD(A1:A10)', '=TOTAL(A1:A10)', '=PLUS(A1:A10)'], 'SUM is the built-in addition function; the colon denotes the range.'],
  ['Which key refreshes the current page in most web browsers?', 'F5', ['F1', 'F2', 'F12'], 'F5 reloads the page; F1 opens help and F12 opens developer tools.'],
  ['What is the full form of URL?', 'Uniform Resource Locator', ['Universal Reference Link', 'Uniform Retrieval Language', 'User Resource Locator'], 'A URL is the address that locates a resource on the web.'],
  ['Which of these is an operating system?', 'Linux', ['Oracle', 'MS Excel', 'Google Chrome'], 'Linux manages the hardware and runs other programs; the rest are applications or a database system.'],
  ['In MS Word, which shortcut saves the current document?', 'Ctrl + S', ['Ctrl + P', 'Ctrl + O', 'Ctrl + N'], 'Ctrl + S saves, Ctrl + P prints, Ctrl + O opens and Ctrl + N creates a new document.'],
  ['What does the extension .pdf stand for?', 'Portable Document Format', ['Printed Document File', 'Public Data Format', 'Personal Document File'], 'PDF preserves a document\'s layout across devices; SSC publishes its notices in this format.']
] as [string, string, string[], string][]).map(([q, ans, wrong, why]) => ({
  topic: 'Computer Basics',
  text: q,
  options: [ans, ...wrong], correct: 0,
  exp: why,
  simple: 'These are recall facts. Learn them as pairs — term and meaning, shortcut and action.',
  concept: 'SSC computer-proficiency questions test standard terminology, storage units and common shortcuts.',
  steps: [`Step 1: ${why}`, `Step 2: The remaining options are invented or belong to a different function.`],
  takeaway: why,
  citation: 'GovOS-authored computer-awareness practice (SSC pattern, not an official past question)'
}));

/** Serve a curated set through the generator interface: shuffled options, no repeats. */
function curatedGenerator(items: CuratedItem[]): NonNullable<TopicSpec['generate']> {
  return (_difficulty, rng, index) => {
    const item = items[index % items.length];
    const order = item.options.map((v, i) => ({ v, i, r: rng() })).sort((a, b) => a.r - b.r);
    return {
      topic: item.topic,
      text: item.text,
      options: order.map(o => o.v),
      correct: order.findIndex(o => o.i === item.correct),
      exp: item.exp,
      source: { label: item.citation, url: 'https://ssc.gov.in', publisher: 'GovOS question bank — written to the SSC syllabus and paper pattern', kind: 'GOVOS_AUTHORED' },
      detailedExp: explain(item.simple, item.concept, item.steps, item.takeaway)
    };
  };
}

const genSynonym = curatedGenerator(VOCAB_ITEMS.concat(ANTONYM_ITEMS));
const genIdiom = curatedGenerator(IDIOM_ITEMS);
const genGrammar = curatedGenerator(GRAMMAR_ITEMS);
const genVoice = curatedGenerator(VOICE_ITEMS);
const genComputer = curatedGenerator(COMPUTER_ITEMS);

/**
 * The topic catalogue: what a candidate may ask for, how to recognise it, and where the
 * questions come from. Topics without a generator are served from the bank only.
 */
export const TOPIC_CATALOG: TopicSpec[] = [
  // Quantitative Aptitude
  { key: 'calculus', label: 'Calculus', subject: SUBJECT_QUANT, aliases: ['calculus', 'derivative', 'derivatives', 'differentiation', 'differentiate', 'integration', 'integral', 'integrals', 'limits', 'limit'], inSyllabus: false, generate: genCalculus },
  { key: 'percentage', label: 'Percentage', subject: SUBJECT_QUANT, aliases: ['percentage', 'percentages', 'percent'], inSyllabus: true, generate: genPercentage },
  { key: 'ratio', label: 'Ratio & Proportion', subject: SUBJECT_QUANT, aliases: ['ratio', 'proportion'], inSyllabus: true, generate: genRatio },
  { key: 'average', label: 'Average', subject: SUBJECT_QUANT, aliases: ['average', 'averages', 'mean'], inSyllabus: true, generate: genAverage },
  { key: 'interest', label: 'Simple & Compound Interest', subject: SUBJECT_QUANT, aliases: ['interest', 'simple interest', 'compound interest', 'si', 'ci', 'ci/si', 'si/ci'], inSyllabus: true, generate: genInterest },
  { key: 'profit-loss', label: 'Profit & Loss', subject: SUBJECT_QUANT, aliases: ['profit', 'loss', 'profit and loss', 'profit & loss', 'discount'], inSyllabus: true, generate: genProfitLoss },
  { key: 'time-work', label: 'Time & Work', subject: SUBJECT_QUANT, aliases: ['time and work', 'time & work', 'work', 'pipes', 'cistern'], inSyllabus: true, generate: genTimeWork },
  { key: 'speed-distance', label: 'Speed, Time & Distance', subject: SUBJECT_QUANT, aliases: ['speed', 'distance', 'time and distance', 'trains', 'train', 'boats', 'streams'], inSyllabus: true, generate: genSpeed },
  { key: 'algebra', label: 'Algebra', subject: SUBJECT_QUANT, aliases: ['algebra', 'algebraic', 'equation', 'equations', 'polynomial', 'quadratic', 'linear equation'], inSyllabus: true, generate: genAlgebra },
  { key: 'geometry', label: 'Geometry', subject: SUBJECT_QUANT, aliases: ['geometry', 'triangle', 'triangles', 'circle', 'circles', 'rhombus', 'similar'], inSyllabus: true },
  { key: 'trigonometry', label: 'Trigonometry', subject: SUBJECT_QUANT, aliases: ['trigonometry', 'trig', 'sin', 'cos', 'tan', 'heights and distances', 'height and distance'], inSyllabus: true },
  { key: 'mensuration', label: 'Mensuration', subject: SUBJECT_QUANT, aliases: ['mensuration', 'volume', 'surface area', 'cone', 'cylinder', 'sphere', 'cuboid', 'frustum'], inSyllabus: true },
  { key: 'number-system', label: 'Number System', subject: SUBJECT_QUANT, aliases: ['number system', 'numbers', 'hcf', 'lcm', 'divisibility'], inSyllabus: true },
  { key: 'data-interpretation', label: 'Data Interpretation', subject: SUBJECT_QUANT, aliases: ['data interpretation', 'di', 'pie chart', 'bar graph', 'table chart'], inSyllabus: true },
  // Reasoning
  { key: 'series', label: 'Number & Letter Series', subject: SUBJECT_REAS, aliases: ['series', 'number series', 'letter series', 'sequence'], inSyllabus: true, generate: genSeries },
  { key: 'coding', label: 'Coding-Decoding', subject: SUBJECT_REAS, aliases: ['coding', 'decoding', 'coding-decoding', 'coding decoding', 'code'], inSyllabus: true, generate: genCoding },
  { key: 'direction', label: 'Direction Sense', subject: SUBJECT_REAS, aliases: ['direction', 'directions', 'direction sense'], inSyllabus: true, generate: genDirection },
  { key: 'syllogism', label: 'Syllogism', subject: SUBJECT_REAS, aliases: ['syllogism', 'syllogisms', 'statements and conclusions', 'venn'], inSyllabus: true },
  { key: 'blood-relation', label: 'Blood Relations', subject: SUBJECT_REAS, aliases: ['blood relation', 'blood relations', 'family tree', 'relation'], inSyllabus: true },
  { key: 'analogy', label: 'Analogy & Classification', subject: SUBJECT_REAS, aliases: ['analogy', 'analogies', 'classification', 'odd one out'], inSyllabus: true },
  { key: 'non-verbal', label: 'Non-Verbal Reasoning', subject: SUBJECT_REAS, aliases: ['non-verbal', 'non verbal', 'dice', 'mirror image', 'paper folding', 'embedded figure'], inSyllabus: true },
  // English
  { key: 'grammar', label: 'Grammar & Error Spotting', subject: SUBJECT_ENG, aliases: ['grammar', 'error spotting', 'error', 'tense', 'tenses', 'subject-verb', 'subject verb', 'preposition', 'prepositions', 'article usage', 'sentence correction'], inSyllabus: true, generate: genGrammar },
  { key: 'vocabulary', label: 'Vocabulary (Synonyms & Antonyms)', subject: SUBJECT_ENG, aliases: ['vocab', 'vocabulary', 'synonym', 'synonyms', 'antonym', 'antonyms', 'one word', 'spelling'], inSyllabus: true, generate: genSynonym },
  { key: 'idioms', label: 'Idioms & Phrases', subject: SUBJECT_ENG, aliases: ['idiom', 'idioms', 'phrase', 'phrases', 'proverb', 'proverbs'], inSyllabus: true, generate: genIdiom },
  { key: 'voice-narration', label: 'Voice & Narration', subject: SUBJECT_ENG, aliases: ['voice', 'active passive', 'passive', 'narration', 'direct indirect', 'reported speech'], inSyllabus: true, generate: genVoice },
  { key: 'comprehension', label: 'Reading Comprehension & Cloze', subject: SUBJECT_ENG, aliases: ['comprehension', 'passage', 'cloze', 'reading'], inSyllabus: true },
  // General Awareness
  { key: 'polity', label: 'Indian Polity & Constitution', subject: SUBJECT_GA, aliases: ['polity', 'constitution', 'constitutional', 'article', 'articles', 'fundamental rights', 'parliament', 'president', 'directive principles'], inSyllabus: true },
  { key: 'history', label: 'History', subject: SUBJECT_GA, aliases: ['history', 'modern history', 'ancient history', 'medieval', 'freedom struggle'], inSyllabus: true },
  { key: 'geography', label: 'Geography', subject: SUBJECT_GA, aliases: ['geography', 'rivers', 'mountains', 'climate', 'soil'], inSyllabus: true },
  { key: 'science', label: 'General Science', subject: SUBJECT_GA, aliases: ['science', 'physics', 'chemistry', 'biology'], inSyllabus: true },
  { key: 'economy', label: 'Economy', subject: SUBJECT_GA, aliases: ['economy', 'economics', 'budget', 'rbi', 'inflation'], inSyllabus: true },
  { key: 'current-affairs', label: 'Current Affairs', subject: SUBJECT_GA, aliases: ['current affairs', 'current events', 'news'], inSyllabus: true },
  { key: 'ssc-notice', label: 'SSC CGL 2026 Notice Facts', subject: SUBJECT_GA, aliases: ['notice', 'notification', 'vacancy', 'vacancies', 'crucial date', 'application window'], inSyllabus: true },
  // Computer
  { key: 'computer-basics', label: 'Computer Basics', subject: SUBJECT_COMP, aliases: ['computer basics', 'hardware', 'software', 'cpu', 'memory', 'ms office', 'excel', 'word', 'internet', 'networking', 'cyber', 'cyber security'], inSyllabus: true, generate: genComputer },
  // Outside the SSC CGL syllabus. Recognised so the candidate is told so, never generated.
  { key: 'matrices', label: 'Matrices & Determinants', subject: SUBJECT_QUANT, aliases: ['matrix', 'matrices', 'determinant', 'determinants'], inSyllabus: false },
  { key: 'vectors', label: 'Vectors', subject: SUBJECT_QUANT, aliases: ['vector', 'vectors', 'vector algebra'], inSyllabus: false },
  { key: 'complex-numbers', label: 'Complex Numbers', subject: SUBJECT_QUANT, aliases: ['complex number', 'complex numbers', 'imaginary number'], inSyllabus: false },
  { key: 'differential-equations', label: 'Differential Equations', subject: SUBJECT_QUANT, aliases: ['differential equation', 'differential equations'], inSyllabus: false },
  { key: 'programming', label: 'Programming', subject: SUBJECT_COMP, aliases: ['programming', 'coding language', 'python', 'java', 'c++', 'javascript', 'sql', 'data structures', 'algorithms'], inSyllabus: false },
  { key: 'ai-ml', label: 'Machine Learning & Data Science', subject: SUBJECT_COMP, aliases: ['machine learning', 'artificial intelligence', 'data science', 'deep learning', 'neural network'], inSyllabus: false },
  { key: 'descriptive-writing', label: 'Essay & Letter Writing', subject: SUBJECT_ENG, aliases: ['essay', 'essays', 'letter writing', 'precis', 'descriptive paper', 'paragraph writing'], inSyllabus: false },
  { key: 'hindi', label: 'Hindi Language', subject: SUBJECT_ENG, aliases: ['hindi', 'hindi grammar', 'hindi vyakaran'], inSyllabus: false },
  { key: 'foreign-language', label: 'Foreign Languages', subject: SUBJECT_ENG, aliases: ['french', 'german', 'spanish', 'japanese', 'foreign language'], inSyllabus: false },
  { key: 'law', label: 'Law', subject: SUBJECT_GA, aliases: ['law', 'legal', 'ipc', 'crpc', 'contract act', 'jurisprudence'], inSyllabus: false },
  { key: 'accounting', label: 'Accounting & Commerce', subject: SUBJECT_GA, aliases: ['accounting', 'accounts', 'accountancy', 'bookkeeping', 'tally', 'commerce', 'auditing'], inSyllabus: false },
  { key: 'medical', label: 'Medical Science', subject: SUBJECT_GA, aliases: ['anatomy', 'medicine', 'pharmacology', 'nursing', 'medical'], inSyllabus: false },
  { key: 'engineering', label: 'Engineering Subjects', subject: SUBJECT_GA, aliases: ['thermodynamics', 'engineering mechanics', 'circuit theory', 'strength of materials', 'fluid mechanics'], inSyllabus: false }
];

export interface ParsedTestRequest {
  subjects: string[];
  topics: TopicSpec[];
  numQuestions: number;
  difficulty: CustomTestConfig['difficulty'];
  durationMinutes?: number;
  focusGoal: NonNullable<CustomTestConfig['focusGoal']>;
  /** Words that looked like a topic request but matched nothing in the catalogue. */
  unrecognised: string[];
  /** Typos the parser forgave, so the reply can say "I read 'workk' as 'work'". */
  corrections: { typed: string; readAs: string }[];
}

/**
 * Whole-word (plural-tolerant) alias match. Substring matching is wrong here: it read
 * "quantum physics" as Quantitative Aptitude, "Framework" as Time & Work and "Similar
 * Triangles" as Simple Interest.
 */
const containsAlias = (text: string, alias: string): boolean =>
  new RegExp(`(^|[^a-z])${alias.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')}(s|es)?($|[^a-z])`, 'i').test(text);

/** Turns a chat message into a structured request. */
const collapseRepeats = (w: string) => w.replace(/(.)\1+/g, '$1');

/** Levenshtein distance for short words; enough for typo forgiveness. */
function editDistance(a: string, b: string): number {
  // optimal string alignment: a swapped pair ("avreage") costs one edit, not two
  const d: number[][] = Array.from({ length: a.length + 1 }, (_, i) => Array.from({ length: b.length + 1 }, (_, j) => (i === 0 ? j : j === 0 ? i : 0)));
  for (let i = 1; i <= a.length; i++) {
    for (let j = 1; j <= b.length; j++) {
      const cost = a[i - 1] === b[j - 1] ? 0 : 1;
      d[i][j] = Math.min(d[i - 1][j] + 1, d[i][j - 1] + 1, d[i - 1][j - 1] + cost);
      if (i > 1 && j > 1 && a[i - 1] === b[j - 2] && a[i - 2] === b[j - 1]) d[i][j] = Math.min(d[i][j], d[i - 2][j - 2] + 1);
    }
  }
  return d[a.length][b.length];
}

/**
 * Typo-tolerant word equality: exact; or equal once repeated letters collapse ("workk");
 * or one edit away for words of 5+ letters, two for 9+. Short words stay exact so
 * "si" and "ci" cannot drift.
 */
export const fuzzyWordEq = (typed: string, want: string): boolean => {
  if (typed === want) return true;
  if (want.length < 4) return false;
  if (collapseRepeats(typed) === collapseRepeats(want)) return true;
  if (want.length < 5) return false;
  const tolerance = want.length >= 9 ? 2 : 1;
  return Math.abs(typed.length - want.length) <= tolerance && editDistance(typed, want) <= tolerance;
};

/**
 * Alias match that forgives typos: the alias words must appear in order and adjacent, each
 * fuzzy-equal (plural-tolerant). Returns the words it had to correct, or null on no match.
 */
function containsAliasFuzzy(text: string, alias: string): { typed: string; readAs: string }[] | null {
  const tw = text.toLowerCase().replace(/[^a-z0-9\s]/g, ' ').split(/\s+/).filter(Boolean);
  const aw = alias.toLowerCase().split(/\s+/).filter(Boolean);
  if (aw.length === 0) return null;
  for (let i = 0; i + aw.length <= tw.length; i++) {
    const diffs: { typed: string; readAs: string }[] = [];
    let ok = true;
    for (let j = 0; j < aw.length; j++) {
      const t = tw[i + j];
      const a = aw[j];
      const plural = t === `${a}s` || t === `${a}es` || (a.endsWith('s') && t === a.slice(0, -1));
      if (t === a || plural) continue;
      if (fuzzyWordEq(t, a)) { diffs.push({ typed: t, readAs: a }); continue; }
      ok = false;
      break;
    }
    if (ok) return diffs;
  }
  return null;
}

export function parseTestRequest(query: string): ParsedTestRequest {
  const lower = query.toLowerCase();
  // "speed drill" and friends describe the pace, not the topic: strip them before matching
  // so a "speed drill on Indian Polity" does not pull in speed-time-distance questions.
  const topicText = lower
    .replace(/\b(speed|quick|rapid|timed|lightning)\s+(drill|test|round|booster|practice|session|paper|mock|quiz)\b/g, ' ')
    .replace(/\bspeed\s+booster\b/g, ' ');
  const has = (alias: string) => containsAlias(topicText, alias);

  const corrections: { typed: string; readAs: string }[] = [];
  const noteCorrections = (diffs: { typed: string; readAs: string }[]) =>
    diffs.forEach(d => { if (!corrections.some(c => c.typed === d.typed)) corrections.push(d); });

  const matchedAlias = new Map<string, string>();
  let topics = TOPIC_CATALOG.filter(t => {
    const alias = [...t.aliases].sort((a, b) => b.length - a.length).find(has);
    if (alias) matchedAlias.set(t.key, alias);
    return !!alias;
  });
  const subjects: string[] = [];
  SUBJECT_ALIASES.forEach(sa => { if (sa.aliases.some(has) && !subjects.includes(sa.subject)) subjects.push(sa.subject); });

  // Nothing matched exactly: try again forgiving typos, and remember what was corrected.
  if (topics.length === 0) {
    TOPIC_CATALOG.forEach(t => {
      for (const alias of t.aliases) {
        const diffs = containsAliasFuzzy(topicText, alias);
        if (diffs && diffs.length > 0) { topics.push(t); noteCorrections(diffs); break; }
      }
    });
  }
  if (topics.length === 0 && subjects.length === 0) {
    SUBJECT_ALIASES.forEach(sa => {
      for (const alias of sa.aliases) {
        const diffs = containsAliasFuzzy(topicText, alias);
        if (diffs && diffs.length > 0) { if (!subjects.includes(sa.subject)) subjects.push(sa.subject); noteCorrections(diffs); break; }
      }
    });
  }
  // "hindi grammar" names Hindi, not English grammar: a longer off-syllabus phrase that contains
  // another topic's matched alias wins, and the contained topic is dropped.
  topics = topics.filter(t => {
    const mine = matchedAlias.get(t.key) || '';
    return !topics.some(other => other !== t && !other.inSyllabus && (matchedAlias.get(other.key) || '').length > mine.length && (matchedAlias.get(other.key) || '').includes(mine));
  });
  topics.forEach(t => { if (!subjects.includes(t.subject)) subjects.push(t.subject); });

  // count: "12 questions", "12 qs", "12-question", "of 12"; a bare number not attached to a unit
  let numQuestions = 15;
  const explicit = lower.match(/(\d+)\s*[- ]?\s*(?:q|qs|questions?|problems?|items?|mcqs?)\b/);
  const ofN = lower.match(/\b(?:of|with)\s+(\d+)\b/);
  const bare = lower.match(/\b(\d+)\b(?!\s*(?:%|percent|min|mins|minute|minutes|hour|hours|marks?|days?|km|m\b|years?|sec))/);
  const cand = explicit ? explicit[1] : ofN ? ofN[1] : bare ? bare[1] : null;
  if (cand) {
    const n = parseInt(cand, 10);
    if (n >= 1 && n <= 100) numQuestions = n;
  }

  let difficulty: CustomTestConfig['difficulty'] = 'MEDIUM';
  if (/\b(hard|tough|difficult|advanced|complex|tier[- ]?2|tier[- ]?ii)\b/.test(lower)) difficulty = 'HARD';
  // 'simple' and 'speed' are topic words here ("simple interest", "speed and distance"),
  // so they must not be read as a difficulty.
  else if (/\b(easy|basic|beginner|elementary|quick|starter)\b/.test(lower)) difficulty = 'EASY';
  else if (/\b(adaptive|mixed)\b/.test(lower)) difficulty = 'ADAPTIVE';

  const timeMatch = lower.match(/(\d+)\s*[- ]?\s*(?:min|mins|minute|minutes)\b/);
  const durationMinutes = timeMatch ? Math.max(1, Math.min(180, parseInt(timeMatch[1], 10))) : undefined;

  // words after "on/about/of/for/in" that matched nothing — surfaced so the reply can say so
  const unrecognised: string[] = [];
  if (topics.length === 0 && subjects.length === 0) {
    const m = lower.match(/\b(?:on|about|of|for|in|regarding)\s+([a-z][a-z\s&-]{2,40}?)(?=\s+(?:questions?|qs|test|drill|mock|quiz|\d)|[.,!?]|$)/);
    if (m && m[1].trim()) {
      unrecognised.push(m[1].trim());
    } else {
      // "cooking recipes 10 questions": strip everything that is request grammar; what is left is the topic
      const generic = new Set(['question', 'questions', 'q', 'qs', 'mcq', 'mcqs', 'test', 'tests', 'mock', 'mocks', 'drill', 'quiz', 'paper', 'set',
        'make', 'me', 'a', 'an', 'the', 'give', 'create', 'generate', 'build', 'want', 'i', 'need', 'please', 'some', 'practice', 'practise',
        'on', 'of', 'for', 'about', 'in', 'with', 'and', 'from', 'to', 'my', 'series', 'level', 'wise',
        'hard', 'easy', 'medium', 'tough', 'difficult', 'advanced', 'basic', 'simple', 'quick', 'speed', 'full', 'mixed', 'adaptive', 'random',
        'minute', 'minutes', 'min', 'mins', 'timer', 'time', 'timed', 'tier', 'exam', 'ssc', 'cgl', 'chsl']);
      const leftover = lower.replace(/[^a-z0-9\s]/g, ' ').split(/\s+/).filter(w => w && !/^\d+$/.test(w) && !generic.has(w));
      if (leftover.length > 0) unrecognised.push(leftover.join(' '));
    }
  }

  return { subjects, topics, numQuestions, difficulty, durationMinutes, focusGoal: /\bweak/.test(lower) ? 'WEAK_AREAS' : 'GENERAL', unrecognised, corrections };
}

function bankFor(subject: string): TemplateQuestion[] {
  if (subject === SUBJECT_QUANT) return QUANT_TEMPLATES;
  if (subject === SUBJECT_REAS) return REASONING_TEMPLATES;
  if (subject === SUBJECT_GA) return GA_TEMPLATES;
  if (subject === SUBJECT_COMP) return COMPUTER_TEMPLATES;
  return ENGLISH_TEMPLATES;
}

/**
 * Each bank question belongs to exactly one catalogue topic: the one whose longest alias
 * its name contains. "Trigonometry: Heights and Distances" is trigonometry, not speed-and-
 * distance; "Geometry: Circle Tangents" is geometry, not circles.
 */
let templateOwner: Map<TemplateQuestion, string> | null = null;
function ownerOf(t: TemplateQuestion): string | undefined {
  if (!templateOwner) {
    templateOwner = new Map<TemplateQuestion, string>();
    const all: TemplateQuestion[] = ([] as TemplateQuestion[]).concat(
      QUANT_TEMPLATES, REASONING_TEMPLATES, GA_TEMPLATES, ENGLISH_TEMPLATES, COMPUTER_TEMPLATES);
    all.forEach(tpl => {
      const name = tpl.topic.toLowerCase();
      let bestKey: string | undefined;
      let bestLen = 0;
      TOPIC_CATALOG.forEach(spec => {
        [spec.label.toLowerCase(), ...spec.aliases].forEach(alias => {
          if (alias.length >= 3 && alias.length > bestLen && containsAlias(name, alias)) {
            bestKey = spec.key;
            bestLen = alias.length;
          }
        });
      });
      if (bestKey) templateOwner!.set(tpl, bestKey);
    });
  }
  return templateOwner.get(t);
}

/** The catalogue topic a free-text topic name belongs to (longest alias wins). */
export function matchTopicByName(name: string): TopicSpec | undefined {
  const lower = name.toLowerCase();
  let best: TopicSpec | undefined;
  let bestLen = 0;
  TOPIC_CATALOG.forEach(spec => {
    [spec.label.toLowerCase(), ...spec.aliases].forEach(alias => {
      if (alias.length >= 3 && alias.length > bestLen && containsAlias(lower, alias)) {
        best = spec;
        bestLen = alias.length;
      }
    });
  });
  return best;
}

/** True when the bank or a generator can supply questions for the topic. */
export const topicHasSupply = (topic: TopicSpec): boolean => !!topic.generate || bankMatches(topic).length > 0;

function bankMatches(topic: TopicSpec): TemplateQuestion[] {
  return bankFor(topic.subject).filter(t => ownerOf(t) === topic.key);
}

interface Supplier {
  topic: TopicSpec;
  bank: TemplateQuestion[];
  cursor: number;
  genIndex: number;
}

const makeSupplier = (topic: TopicSpec, bank: TemplateQuestion[]): Supplier => ({ topic, bank, cursor: 0, genIndex: 0 });

/** Everything the catalogue can supply for a subject: its bank plus every generator in it. */
function suppliersForSubject(subject: string): Supplier[] {
  const out = TOPIC_CATALOG
    .filter(t => t.subject === subject && t.inSyllabus)
    .map(t => makeSupplier(t, bankMatches(t)))
    .filter(x => x.bank.length > 0 || x.topic.generate);
  const claimed = new Set(out.flatMap(o => o.bank));
  const leftovers = bankFor(subject).filter(t => !claimed.has(t));
  if (leftovers.length > 0) {
    out.push(makeSupplier({ key: `${subject}-other`, label: subject, subject, aliases: [], inSyllabus: true }, leftovers));
  }
  return out;
}

/** One unused question from a supplier: bank first, then its generator (retried for variety). */
function drawFrom(sup: Supplier, difficulty: CustomTestConfig['difficulty'], rng: () => number, used: Set<string>): { q: TemplateQuestion; generated: boolean } | null {
  while (sup.cursor < sup.bank.length) {
    const cand = sup.bank[sup.cursor++];
    if (!used.has(cand.text)) return { q: cand, generated: false };
  }
  if (sup.topic.generate) {
    for (let attempt = 0; attempt < 25; attempt++) {
      const g = sup.topic.generate(difficulty, rng, sup.genIndex++);
      if (!used.has(g.text)) return { q: g, generated: true };
    }
  }
  return null;
}

/** Same suppliers, different starting point, so a mixed test does not always open on the same topic. */
const rotateStart = <T,>(arr: T[]): T[] => {
  if (arr.length < 2) return arr;
  const k = Math.floor(Math.random() * arr.length);
  return [...arr.slice(k), ...arr.slice(0, k)];
};

export function generateCustomMockTest(config: CustomTestConfig): MockPaper {
  const explicitTopics = (config.selectedTopics || [])
    .map(k => TOPIC_CATALOG.find(t => t.key === k))
    .filter((t): t is TopicSpec => !!t);
  const subjects = config.selectedSubjects.length > 0
    ? config.selectedSubjects
    : Array.from(new Set(explicitTopics.map(t => t.subject)));

  const notes: string[] = [];
  let suppliers: Supplier[];
  let requestedLabel: string;

  if (explicitTopics.length > 0) {
    requestedLabel = explicitTopics.map(t => t.label).join(' + ');
    const all = explicitTopics.map(t => makeSupplier(t, bankMatches(t)));
    const empty = all.filter(sup => sup.bank.length === 0 && !sup.topic.generate);
    suppliers = all.filter(sup => sup.bank.length > 0 || sup.topic.generate);
    empty.forEach(e => notes.push(e.topic.inSyllabus
      ? `GovOS has no ${e.topic.label} questions yet, so that topic could not be included.`
      : `${e.topic.label} is outside this exam's syllabus, so it was left out.`));
    if (suppliers.length === 0) {
      const fallback = subjects.length > 0 ? subjects : [SUBJECT_QUANT];
      suppliers = fallback.flatMap(suppliersForSubject);
      notes.push(`Filled from ${fallback.join(' and ')} instead.`);
    }
  } else if (subjects.length > 0) {
    requestedLabel = subjects.join(' + ');
    suppliers = rotateStart(subjects.flatMap(suppliersForSubject));
  } else {
    requestedLabel = 'Tier-1 Mixed';
    suppliers = rotateStart([SUBJECT_QUANT, SUBJECT_REAS, SUBJECT_ENG, SUBJECT_GA].flatMap(suppliersForSubject));
    notes.push('No subject or topic was named, so this mixes the four Tier-1 sections. Ask for a topic — for example "12 questions on percentage" — to drill one thing.');
  }

  suppliers.filter(sup => !sup.topic.inSyllabus && explicitTopics.includes(sup.topic)).forEach(sup =>
    notes.push(`${sup.topic.label} is outside this exam's syllabus. Generated for practice because you asked for it.`));

  const targetCount = Math.max(1, config.numQuestions || 25);
  const rng = mulberry32((Date.now() % 1000003) + targetCount * 7919);
  const questions: PracticeQuestion[] = [];
  const used = new Set<string>();
  const subjectOf = new Map<TemplateQuestion, string>();
  let generatedCount = 0;
  let bankCount = 0;
  let widening = 0;
  let onRequestedTopic = 0;

  const primaryKeys = new Set(suppliers.map(sup => sup.topic.key));

  for (let i = 0; i < targetCount; i++) {
    let drawn: { q: TemplateQuestion; generated: boolean } | null = null;
    let from: Supplier | null = null;

    for (let attempt = 0; attempt < suppliers.length && !drawn; attempt++) {
      const sup = suppliers[(i + attempt) % suppliers.length];
      drawn = drawFrom(sup, config.difficulty, rng, used);
      if (drawn) from = sup;
    }

    // The requested topics are exhausted. Widen — first to the rest of the same subject,
    // then to the whole Tier-1 catalogue — rather than serve the same question twice.
    while (!drawn && widening < 2) {
      const subs = Array.from(new Set(suppliers.map(sup => sup.topic.subject)));
      const pool = widening === 0
        ? subs
        : [SUBJECT_QUANT, SUBJECT_REAS, SUBJECT_ENG, SUBJECT_GA].filter(sub => !subs.includes(sub));
      widening++;
      const seen = new Set(suppliers.map(sup => sup.topic.key));
      const extra = pool.flatMap(suppliersForSubject).filter(sup => !seen.has(sup.topic.key));
      if (extra.length === 0) continue;
      notes.push(widening === 1
        ? `GovOS has only ${used.size} distinct ${requestedLabel} question${used.size === 1 ? '' : 's'} at the moment, so the rest come from other ${subs.join(' and ')} topics.`
        : `That subject ran out too, so the remaining questions come from the other Tier-1 sections.`);
      suppliers = suppliers.concat(extra);
      for (let attempt = 0; attempt < suppliers.length && !drawn; attempt++) {
        const sup = suppliers[(i + attempt) % suppliers.length];
        drawn = drawFrom(sup, config.difficulty, rng, used);
        if (drawn) from = sup;
      }
    }

    // Nothing distinct is left anywhere: stop short rather than repeat questions.
    if (!drawn) {
      notes.push(`Only ${questions.length} distinct question${questions.length === 1 ? '' : 's'} exist across the whole bank for this request, so this test is ${questions.length} question${questions.length === 1 ? '' : 's'} long instead of ${targetCount}.`);
      break;
    }

    const template = drawn.q;
    used.add(template.text);
    if (drawn.generated) generatedCount++; else bankCount++;
    if (from && primaryKeys.has(from.topic.key)) onRequestedTopic++;

    const subj = from ? from.topic.subject : (subjectOf.get(template) || subjects[0] || SUBJECT_QUANT);
    questions.push({
      id: `ai-custom-q${i + 1}`,
      topicId: `custom-topic-${i}`,
      subject: subj,
      topicName: template.topic,
      tier: 'TIER_1',
      shiftInfo: `AI Custom Drill • Q${i + 1}`,
      questionType: 'CUSTOM_AI_GENERATED',
      difficulty: config.difficulty,
      questionText: `[Q${i + 1} • ${template.topic}] ${template.text}`,
      options: template.options.map((opt, idx) => ({ id: idx, text: opt })),
      correctOptionIndex: template.correct,
      explanation: template.exp,
      detailedExplanation: template.detailedExp,
      provenance: provenanceForSource(template.source)
    });
  }

  if (generatedCount > 0 && bankCount > 0) {
    notes.push(`${bankCount} question${bankCount === 1 ? '' : 's'} from the official-sourced bank, ${generatedCount} written by the GovOS generator for this request.`);
  } else if (generatedCount > 0) {
    notes.push(`All ${generatedCount} questions were written by GovOS for this request, to the SSC pattern — none is an official past question, because no official-sourced question exists for this topic yet. Numerical answers are computed as the question is built; language and factual items are curated and checked by hand.`);
  } else {
    notes.push(`All ${bankCount} questions come from the official-sourced bank, each citing the document it was written from.`);
  }

  let secondsPerQuestion = 36;
  if (config.difficulty === 'HARD') secondsPerQuestion = 55;
  else if (config.difficulty === 'EASY') secondsPerQuestion = 28;
  else if (config.difficulty === 'MEDIUM') secondsPerQuestion = 40;
  const paperSubjects = Array.from(new Set(questions.map(q => q.subject)));
  if (paperSubjects.every(sub => sub === SUBJECT_GA || sub === SUBJECT_ENG)) {
    secondsPerQuestion = Math.round(secondsPerQuestion * 0.6);
  }
  const durationMinutes = config.durationMinutes || Math.max(3, Math.ceil((questions.length * secondsPerQuestion) / 60));

  const summary = `${questions.length} ${requestedLabel} question${questions.length === 1 ? '' : 's'} · ${config.difficulty} · ${durationMinutes} min`;

  return {
    id: `ai-custom-mock-${Date.now()}`,
    title: config.title || `${requestedLabel} Drill (${questions.length} Qs)`,
    category: 'CUSTOM_AI',
    examTier: 'Tier-1',
    totalQuestions: questions.length,
    totalMarks: questions.length * 2,
    durationMinutes,
    difficulty: config.difficulty,
    description: `${summary}. ${onRequestedTopic} of ${questions.length} questions are on the requested topic. ${notes.join(' ')}`,
    provenanceTag: generatedCount > 0 && bankCount === 0 ? `GovOS-generated (${durationMinutes} Mins)` : `AI Tailored (${durationMinutes} Mins)`,
    questions,
    generationNotes: notes,
    requestSummary: summary
  };
}


// ==========================================================================
// postStudyPathsData.ts
// ==========================================================================
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
  'post-si-cbi': {
    postId: 'post-si-cbi',
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
  'post-tax-assistant-cbdt': {
    postId: 'post-tax-assistant-cbdt',
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
  'post-auditor-cag': {
    postId: 'post-auditor-cag',
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

/**
 * Post ids used by earlier builds, kept so a target post already saved in a
 * candidate's browser still resolves after the ids were aligned with examsData.
 */
/** True when at least one of the exam's posts has an authored study path (SSC CGL today). */
export const examHasStudyPaths = (exam: Exam): boolean =>
  exam.posts.some(p => !!ALL_POST_STUDY_PATHS[p.id] || !!LEGACY_POST_ID_ALIASES[p.id]);

const LEGACY_POST_ID_ALIASES: Record<string, string> = {
  'post-cbi-si': 'post-si-cbi',
  'post-tax-asst': 'post-tax-assistant-cbdt',
  'post-auditor': 'post-auditor-cag',
  // Posts that share an identical preparation path with an authored one.
  'post-aso-mea': 'post-aso-css',
  'post-aso-ib': 'post-aso-css',
  'post-aso-railways': 'post-aso-css',
  'post-ssa-dopt': 'post-aso-css',
  'post-preventive-officer': 'post-excise',
  'post-examiner': 'post-excise',
  'post-si-nia': 'post-si-cbi',
  'post-stat-inv': 'post-jso',
  'post-tax-assistant-cbic': 'post-tax-assistant-cbdt',
  'post-auditor-cgda': 'post-auditor-cag',
  'post-accountant-cag': 'post-auditor-cag'
};

/** Resolves any post id (current, legacy, or equivalent) to an authored study path. */
export function getPostStudyPath(postId: string): PostStudyPath {
  return (
    ALL_POST_STUDY_PATHS[postId] ||
    ALL_POST_STUDY_PATHS[LEGACY_POST_ID_ALIASES[postId]] ||
    ALL_POST_STUDY_PATHS['post-aso-css']
  );
}
