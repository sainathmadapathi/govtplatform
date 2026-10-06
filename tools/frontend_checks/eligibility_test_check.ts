// An eligibility test (a TET) fills no post. The assistant's age, vacancy, pay, physical, post and eligibility answers
// were written for recruitments and, for an exam with no posts, printed "Age limits run from Infinity to -Infinity",
// "all 0 posts" and "the vacancy figure is announced separately ... and is not final in the register yet". Every
// exam without a fee card was told "women, SC, ST, PwBD and ex-servicemen candidates are exempted under the
// notice", and every admit-card answer said to carry "an original photo ID" -- one authority's rules stated as
// any notice's. This holds the real TG TET record and a synthetic eligibility test (the future-exam fixture with
// its posts removed) to the record-only answers, and every register exam to the fee and admit-card rules.
// An admission test (JEE (Main)) is held to the same, plus the answers it needed: a release rule instead of an
// admit-card date, a cut-off that says what kind it is and that it is this cycle's, no invented pass mark, the
// exam's own FAQ for a question it answers whole, and a declared result named as declared.
// Run: npm run check:frontend
import './stub';
import { answerCandidateQuery, faqAnswerFor, noPostsReply } from '../../src/ui';
import { buildChatContext, conversationService } from '../../src/services';
import { ALL_EXAMS } from '../../src/data';
import type { Exam } from '../../src/types';
import { futureExam } from './future_exam_fixture';

(globalThis as any).fetch = async () => ({ ok: false, status: 503, json: async () => ({}) });

let failures = 0;
const check = (name: string, ok: boolean, detail = '') => {
  if (!ok) failures++;
  if (!ok || process.env.VERBOSE) console.log((ok ? 'PASS ' : 'FAIL ') + name + (detail ? ' :: ' + detail : ''));
};
const ask = (exam: Exam, q: string) => {
  conversationService.clearAll?.();
  return answerCandidateQuery(q, buildChatContext(exam, 'ASSISTANT'));
};
const BROKEN = /Infinity|NaN|undefined|\b0 posts\b|all 0\b|not final in the register yet|crucial date, \./;

const tet = ALL_EXAMS.find(e => e.id === 'exam-tgtet-inservice-2026-ii')!;
check('register: TG TET 2026-II is held, as an eligibility test with no posts', !!tet && tet.examNature === 'ELIGIBILITY_TEST' && tet.posts.length === 0);

const base = futureExam();
const synthetic: Exam = {
  ...base, id: 'exam-zssc-eligibility-test-2031', examNature: 'ELIGIBILITY_TEST', posts: [], vacanciesTotal: undefined,
  eligibilityHighlights: [{ title: 'Who may appear', body: 'Only serving officers of the Zenith State may appear (Para 3).', provenance: base.stages[0].provenance }]
};

const POST_SHAPED: [string, RegExp][] = [
  ['how many vacancies', /eligibility test, not a recruitment|no vacancies/],
  ['what is the salary', /eligibility test, not a recruitment|no pay scale/],
  ['what is the age limit', /eligibility test, not a recruitment|no age limit/],
  ['age limit for OBC', /eligibility test, not a recruitment|no age limit/],
  ['physical test', /eligibility test, not a recruitment|no physical standard/],
  ['what posts are there', /eligibility test, not a recruitment|no posts/],
  ['am i eligible', /eligibility test, not a recruitment|post-by-post eligibility check/],
];
for (const exam of [tet, synthetic]) {
  for (const [q, want] of POST_SHAPED) {
    const r = ask(exam, q);
    check(`${exam.id}: "${q}" answers from the record, not a recruitment template`, want.test(r.text) && !BROKEN.test(r.text), r.text.slice(0, 160));
    check(`${exam.id}: "${q}" cites the record's own rule`, !!r.citation, String(r.sourceKind));
  }
}
check('noPostsReply: a recruitment with no posts on record says the record holds none yet, not that it is a test',
  /holds no posts for .* yet/.test(noPostsReply({ ...base, posts: [] }, 'vacancy').text));

// Fee and admit card: only what each exam's own record says.
for (const exam of ALL_EXAMS) {
  const fee = ask(exam, 'what is the fee').text;
  const ownExemptions = JSON.stringify([exam.applicationGuide?.fee, exam.eligibilityHighlights]);
  check(`${exam.id}: the fee answer states no exemption its record does not hold`,
    !/ex-servicemen/i.test(fee) || /ex-servicemen/i.test(ownExemptions), fee.slice(0, 160));
  const admit = ask(exam, 'when is the admit card').text;
  const ownAdmit = JSON.stringify([exam.admitCardEvents, exam.admitCardDetails, exam.examDayChecklist]);
  check(`${exam.id}: the admit-card answer asks for no photo ID its record does not mention`,
    !/photo ID/i.test(admit) || /photo ?ID|identity/i.test(ownAdmit), admit.slice(0, 160));
}
const tetFee = ask(tet, 'what is the fee');
check('TG TET: the fee is the notice\'s own four amounts', /Rs\. 750\/-[\s\S]*Rs\.1000\/-[\s\S]*Rs\.700\/-[\s\S]*Rs\.950\/-/.test(tetFee.text) && !!tetFee.citation, tetFee.text.slice(0, 200));

// The exam's own FAQs answer what no intent covers.
const dsc = ask(tet, 'can i use this pass for DSC recruitment');
check('TG TET: a question its FAQs answer is answered from them, cited', /cannot be used for appearing in any direct recruitment/.test(dsc.text) && !!dsc.citation, dsc.text.slice(0, 160));
check('faqAnswerFor: an unrelated question is not forced onto a FAQ', faqAnswerFor('what is the weather in paris tomorrow', tet) === null);
const pass = ask(tet, 'what are the pass marks');
check('TG TET: pass marks come from its own rule, and no cut-off is invented', /60% and above/.test(pass.text) && /no cut-off/.test(pass.text), pass.text.slice(0, 160));

// An admission test (JEE (Main)) fills no post either, and says so in its own words.
const jee = ALL_EXAMS.find(e => e.id === 'exam-jee-main-2026')!;
check('register: JEE (Main) 2026 is held, as an admission test with no posts', !!jee && jee.examNature === 'ADMISSION_TEST' && jee.posts.length === 0);
const admission: Exam = { ...synthetic, id: 'exam-zssc-admission-test-2031', examNature: 'ADMISSION_TEST' };
for (const exam of [jee, admission]) {
  for (const [q] of POST_SHAPED) {
    const r = ask(exam, q);
    check(`${exam.id}: "${q}" says it is an admission test, from the record`, /an admission test, not a recruitment/.test(r.text) && !BROKEN.test(r.text) && !/eligibility test/.test(r.text), r.text.slice(0, 160));
  }
}
// No admit-card date, but a release rule: the rule is the answer, not every date on record.
const jeeAdmit = ask(jee, 'when is the admit card');
check('JEE: the admit-card answer is NTA\'s release rule', /03-04 days before the date of the Examination/.test(jeeAdmit.text) && !/Key dates on record/.test(jeeAdmit.text) && !!jeeAdmit.citation, jeeAdmit.text.slice(0, 200));
// A cut-off names what kind it is, and one of the record's own cycle is not "does not exist yet".
const jeeCut = ask(jee, 'what are the cutoffs');
check('JEE: each cut-off says it is a percentile for JEE (Advanced) eligibility', /93\.4123549 \(NTA score \(percentile\) to become eligible for JEE \(Advanced\)/.test(jeeCut.text), jeeCut.text.slice(0, 200));
check('JEE: this cycle\'s cut-off is not called one that does not exist yet', /published for this cycle/.test(jeeCut.text) && !/does not exist yet/.test(jeeCut.text) && !/vacancies/.test(jeeCut.text), jeeCut.text.slice(-260));
const ssc = ALL_EXAMS.find(e => e.id === 'exam-ssc-cgl-2026')!;
const sscCut = ask(ssc, 'what are the cutoffs');
check('SSC: an earlier year\'s cut-off is still the latest published, not this cycle\'s', !/published for this cycle/.test(sscCut.text), sscCut.text.slice(-200));
const jeePass = ask(jee, 'what is the pass mark');
check('JEE: no pass mark is invented; the cut-offs are not passed off as one', /holds no pass mark/.test(jeePass.text), jeePass.text.slice(0, 160));
// A question one of the exam's own FAQs answers whole is answered by it, cited.
for (const [q, want] of [['who can take jee advanced', /top 2,50,000/], ['can i change my exam centre', /cannot be changed/], ['can i use a calculator', /calculators in any form is not permitted/],
  ['what is percentile', /percentage of candidates in your shift/], ['how many sessions', /^Two: Session 1/]] as [string, RegExp][]) {
  const r = ask(jee, q);
  check(`JEE: "${q}" is answered from its own FAQ`, want.test(r.text) && r.sourceKind === 'OFFICIAL' && !!r.citation, r.text.slice(0, 160));
}
// After a declared result, the next step is not "watch for the result".
const jeeNext = ask(jee, 'what should i do next');
check('JEE: next step names the declared result', /result and NTA scores declared/.test(jeeNext.text) && !/Watch for the answer key/.test(jeeNext.text), jeeNext.text.slice(0, 200));

if (failures) { console.log(`\n${failures} eligibility-test check(s) failed`); process.exit(1); }
console.log('eligibility test: all checks passed');
