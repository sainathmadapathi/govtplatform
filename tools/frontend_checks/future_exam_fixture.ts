// A future exam GovOS does not hold: an invented authority, an invented examination, its own vocabulary
// ("Screening Test", "Written Examination", "Phase"), its own marking and dates. It is typed against the
// same `Exam` model every real exam uses, and nothing in src/ names it -- which is the point: adding an
// exam must mean adding its validated data, not editing the engine.
import type { DataProvenance, Exam } from '../../src/types';

export const FUTURE_ID = 'exam-zssc-combined-officers-2031';
export const FUTURE_AUTHORITY = 'Zenith State Service Commission (ZSSC)';
export const FUTURE_TITLE = 'ZSSC Combined Officers Examination 2031';
const HOST = 'https://zssc.example.gov.in';

const notice: DataProvenance = {
  id: 'prov-zssc-notice',
  documentTitle: 'ZSSC Notification No. 07/2031 — Combined Officers Examination',
  officialUrl: `${HOST}/notifications/07-2031.pdf`,
  pageNumber: 4,
  clauseNumber: 'Para 6',
  publishedDate: '2031-01-12',
  verifiedDate: '2031-01-14',
  verifiedBy: 'Synthetic fixture',
  taxonomyType: 'FACT',
  verificationLevel: 'OFFICIALLY_VERIFIED',
  excerptText: 'The examination shall consist of a Screening Test and a Written Examination.',
};

const docSpec = (documentType: string) => ({
  documentType, dimensions: 'As printed in the notice', fileFormat: 'JPG', fileSize: '20-50 KB',
  rules: [`${documentType} as Para 9 of the notice prints it.`], sampleDescription: documentType,
});

/** The stage that carries the typing test, in each of the three places a record can state one. */
export type TypingShape = 'SECTION' | 'MODE' | 'NONE';

export const futureExam = (typing: TypingShape = 'SECTION'): Exam => ({
  id: FUTURE_ID,
  code: 'ZSSC_CO_2031',
  title: FUTURE_TITLE,
  authorityName: FUTURE_AUTHORITY,
  officialDomain: HOST,
  crucialEligibilityDate: '2031-07-01',
  isGoldenJourney: false,
  isDemoData: false,
  overviewDescription: 'Recruitment of Assistant Revenue Officers and Block Statistical Officers in the Zenith State services.',
  vacanciesTotal: '612',
  posts: [
    { id: 'post-zssc-aro', postName: 'Assistant Revenue Officer', department: 'Zenith Revenue Department', payLevel: 'Zenith Pay Band 9',
      payScale: 'Zenith Pay Band 9', classification: 'Group B (Non-Gazetted)', minAge: 21, maxAge: 37,
      natureOfWork: 'Land revenue records and assessment.', provenance: notice },
    { id: 'post-zssc-bso', postName: 'Block Statistical Officer', department: 'Zenith Directorate of Economics', payLevel: 'Zenith Pay Band 8',
      payScale: 'Zenith Pay Band 8', classification: 'Group B (Non-Gazetted)', minAge: 21, maxAge: 35,
      natureOfWork: 'Block-level statistical surveys.', provenance: notice },
  ],
  dates: [
    { id: 'date-zssc-notif', type: 'NOTIFICATION', label: 'Notification No. 07/2031 published', dateTimeStr: '2031-01-12 10:00:00',
      timezone: 'Asia/Kolkata (IST)', isTentative: false, status: 'AVAILABLE', provenance: notice },
    { id: 'date-zssc-open', type: 'APPLICATION_OPEN', label: 'Online applications open', dateTimeStr: '2031-01-20 10:00:00',
      timezone: 'Asia/Kolkata (IST)', isTentative: false, status: 'AVAILABLE', provenance: notice },
    { id: 'date-zssc-close', type: 'APPLICATION_CLOSE', label: 'Last date for online applications', dateTimeStr: '2031-02-19 17:00:00',
      timezone: 'Asia/Kolkata (IST)', isTentative: false, status: 'AVAILABLE', provenance: notice },
    { id: 'date-zssc-screening', type: 'EXAM_TIER1', label: 'Screening Test', dateTimeStr: '2031-04-27 10:00:00',
      timezone: 'Asia/Kolkata (IST)', isTentative: true, status: 'AVAILABLE', provenance: notice },
  ],
  globalRuleGroup: { id: 'rg-zssc', operator: 'AND', rules: [
    { id: 'rule-zssc-age-min', ruleType: 'AGE_MIN', operator: '>=', ruleValue: 21, category: 'GENERAL', provenance: notice },
    { id: 'rule-zssc-age-max', ruleType: 'AGE_MAX', operator: '<=', ruleValue: 37, category: 'GENERAL', provenance: notice },
  ] },
  stages: [
    { id: 'stage-zssc-screening', stageNumber: 1, stageName: 'Phase A: Screening Test', tier: 'PHASE_A', durationMinutes: 120,
      totalQuestions: 120, totalMarks: 120, negativeMarking: 'one-third of the marks of a question deducted for each wrong answer (Para 6.3)',
      mode: 'Pen and paper (OMR)', qualifyingNature: 'Qualifying only; its marks are not counted for the merit (Para 6.4)',
      sections: [
        { sectionName: 'General Studies of Zenith State', modules: ['History of Zenith', 'Zenith Economy'], questions: 60, marks: 60, durationMinutes: 60, negativeMarking: '-1/3' },
        { sectionName: 'Mental Ability', modules: ['Analytical reasoning'], questions: 60, marks: 60, durationMinutes: 60, negativeMarking: '-1/3' },
      ], provenance: notice },
    { id: 'stage-zssc-written', stageNumber: 2, stageName: 'Phase B: Written Examination', tier: 'PHASE_B', durationMinutes: 180,
      totalQuestions: 150, totalMarks: 300, negativeMarking: 'no deduction for a wrong answer (Para 7.2)',
      mode: typing === 'MODE' ? 'Computer-based test with a keyboard typing test' : 'Computer-based test',
      qualifyingNature: 'Counted for the merit list (Para 7.5)',
      sections: [
        { sectionName: 'Paper I: Zenith Administration', modules: ['State acts', 'Revenue procedure'], questions: 75, marks: 150, durationMinutes: 90, negativeMarking: 'none' },
        { sectionName: 'Paper II: Applied Statistics', modules: ['Sampling', 'Index numbers'], questions: 75, marks: 150, durationMinutes: 90, negativeMarking: 'none' },
        ...(typing === 'SECTION'
          ? [{ sectionName: 'Paper III: Typing Test (qualifying)', modules: ['25 words a minute in English'], questions: 0, marks: 0, durationMinutes: 10,
              negativeMarking: 'Qualifying at 25 words a minute (Para 7.4)' }]
          : []),
      ], provenance: notice },
  ],
  syllabus: [
    { id: 'syl-zssc-history', subject: 'General Studies', tier: 'PHASE_A', topicName: 'History of Zenith State', weightagePercentage: 0,
      avgQuestions: 0, isHighYield: false, officialProvenance: notice },
    { id: 'syl-zssc-economy', subject: 'General Studies', tier: 'PHASE_A', topicName: 'Zenith Economy', weightagePercentage: 0,
      avgQuestions: 0, isHighYield: false, officialProvenance: notice },
    { id: 'syl-zssc-sampling', subject: 'Applied Statistics', tier: 'PHASE_B', topicName: 'Sampling methods', weightagePercentage: 0,
      avgQuestions: 0, isHighYield: false, officialProvenance: notice },
  ],
  practiceQuestions: [],
  corrigendums: [],
  cutoffsHistory: [
    { year: 2029, category: 'General', tier1Cutoff: 72, tier2Cutoff: 168, provenance: notice },
    { year: 2029, category: 'Backward Classes', tier1Cutoff: 66, tier2Cutoff: 159, provenance: notice },
  ],
  resources: [],
  faqs: [],
  applicationGuide: {
    officialPortal: `${HOST}/apply`,
    otrSteps: [],
    photoRules: docSpec('Photograph'),
    signatureRules: docSpec('Signature'),
    certificateRules: [],
    rejectionPitfalls: [],
  },
  roadmapTracks: [],
});

/** The same exam as a machine build would leave it: every section "not found" at build time, plus one
 *  section this platform has no default for, whose evidence the record itself declares. */
export const futureMachineExam = (extra: Exam['sectionStates'] = {}): Exam => {
  const nf = (sectionNum: number) => ({ state: 'SOURCE_NOT_FOUND_AFTER_SEARCH', nature: 'OFFICIAL_FACT', studentStatusSummary: '', sectionNum, isApplicable: true });
  return {
    ...futureExam(),
    origin: 'MACHINE_ACQUIRED',
    sectionStates: {
      overview: nf(1), dates: nf(2), eligibility: nf(3), application: nf(4), pattern: nf(5), syllabus: nf(6), pyqs: nf(9),
      cutoffs: nf(10), 'admit-card': nf(14), 'exam-day': nf(15), results: nf(16), corrigenda: nf(13), 'official-links': nf(12),
      'provisional-keys': { ...nf(30), evidenceRoles: ['ANSWER_KEY'] },
      ...extra,
    },
  };
};

/**
 * Three skill-test shapes for the Results engine, each its own record:
 *   A -- a third phase whose skill test is unlike any held exam's: an on-site Practical Assessment,
 *        qualifying, 45 minutes, scored out of 50 against a printed percentage by category;
 *   B -- no skill test at all (the base exam: its "Typing Test" section name alone makes none);
 *   C -- a skill test the notice names and says nothing else about.
 */
export type SkillShape = 'A' | 'B' | 'C';
export const PRACTICAL_PROVENANCE: DataProvenance = { ...notice, id: 'prov-zssc-practical', clauseNumber: 'Para 8', pageNumber: 6,
  excerptText: 'Phase C: a Practical Assessment of 45 minutes at the district office, qualifying in nature.' };

export const futureExamWithSkill = (shape: SkillShape): Exam => {
  const base = futureExam();
  if (shape === 'B') return base;
  if (shape === 'C') {
    return { ...base, stages: [base.stages[0], { ...base.stages[1], skillTest: { name: 'Proficiency Check' } }] };
  }
  return {
    ...base,
    stages: [...base.stages, {
      id: 'stage-zssc-practical', stageNumber: 3, stageName: 'Phase C: Practical Assessment', tier: 'PHASE_C', durationMinutes: 45,
      totalQuestions: 0, totalMarks: 50, negativeMarking: 'not applicable', mode: 'On-site, at the district office',
      qualifyingNature: 'Qualifying; not counted for the merit (Para 8.3)', sections: [], provenance: PRACTICAL_PROVENANCE,
      skillTest: {
        name: 'Practical Assessment', description: 'Field-record handling at the district office (Para 8.1).', qualifying: true, durationMinutes: 45,
        requirements: ['Prepare one land-record extract from a given survey file (Para 8.2)'],
        metrics: [{ key: 'practicalAssessmentMarks', label: 'Practical Assessment', unit: 'marks', outOf: 50, direction: 'AT_LEAST',
          standard: { byCategory: [{ categories: ['GENERAL'], value: 40 }], otherwise: 35, percentOfOutOf: true,
            asPrinted: 'Minimum: General 40%, all other categories 35% (Para 8.4)', provenance: PRACTICAL_PROVENANCE } }],
        provenance: PRACTICAL_PROVENANCE,
      },
    }],
  };
};

/** The educational qualifications a notice prints, at three levels and one subject rule, and one post the
 *  notice states none for. Exercises the eligibility engine with no line of src/ naming this exam. */
export const QUALIFICATION_PROVENANCE: DataProvenance = { ...notice, id: 'prov-zssc-qualification', clauseNumber: 'Para 5', pageNumber: 3,
  excerptText: 'Para 5: Record Assistant — Higher Secondary (Class 12). Revenue Inspector — a Bachelor Degree. Agricultural Statistician — a Bachelor Degree in Agriculture or Statistics.' };

export const futureExamWithQualifications = (): Exam => {
  const base = futureExam();
  const rule = (id: string, ruleType: 'DEGREE_REQUIRED' | 'BRANCH_SPECIALIZATION', ruleValue: string[]) =>
    ({ id, ruleType, operator: '=' as const, ruleValue, category: 'GENERAL' as const, provenance: QUALIFICATION_PROVENANCE });
  const post = (id: string, postName: string) => ({ id, postName, department: 'Zenith Revenue Department', payLevel: 'Zenith Pay Band 6',
    payScale: 'Zenith Pay Band 6', classification: 'Group C', minAge: 21, maxAge: 37, provenance: QUALIFICATION_PROVENANCE });
  return {
    ...base,
    posts: [
      { ...post('post-zssc-record-assistant', 'Record Assistant'),
        ruleGroup: { id: 'rg-zssc-ra', operator: 'AND', rules: [rule('rule-zssc-ra-12', 'DEGREE_REQUIRED', ['Higher Secondary (Class 12)'])] } },
      { ...post('post-zssc-revenue-inspector', 'Revenue Inspector'),
        ruleGroup: { id: 'rg-zssc-ri', operator: 'AND', rules: [rule('rule-zssc-ri-deg', 'DEGREE_REQUIRED', ['Bachelor Degree'])] } },
      { ...post('post-zssc-agri-statistician', 'Agricultural Statistician'),
        ruleGroup: { id: 'rg-zssc-as', operator: 'AND', rules: [
          rule('rule-zssc-as-deg', 'DEGREE_REQUIRED', ['Bachelor Degree']),
          rule('rule-zssc-as-subject', 'BRANCH_SPECIALIZATION', ['Agriculture', 'Statistics']),
        ] } },
      // The notice states no qualification for this post: the engine must say so, not assume one.
      post('post-zssc-process-server', 'Process Server'),
    ],
  };
};
