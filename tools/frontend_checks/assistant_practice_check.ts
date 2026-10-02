// The assistant's Practice & PYQs answer is the selected exam's own, read from its record. It used to give
// every exam SSC's answer -- "the full previous-year shift papers on a real CBT clock with SSC Tier-1 marking
// (+2 correct, −0.5 wrong)" -- and called GovOS-authored papers shift papers even for SSC.
// Run: npm run check:frontend
import './stub';
import { answerCandidateQuery } from '../../src/ui';
import { buildChatContext } from '../../src/services';
import { IBPS_PO_EXAM, SSC_CGL_EXAM, UPSC_CSE_EXAM } from '../../src/data';
import type { Exam } from '../../src/types';

let failures = 0;
const check = (name: string, ok: boolean, detail = '') => {
  if (!ok) failures++;
  if (!ok || process.env.VERBOSE) console.log((ok ? 'PASS ' : 'FAIL ') + name + (detail ? ' :: ' + detail : ''));
};

//: Both ways a candidate reaches the answer: a "where is it" question and a plain question about practice.
const QUESTIONS = ['where can I find previous question papers', 'is there any practice for this exam'];
const answers = (exam: Exam) => QUESTIONS.map(q => answerCandidateQuery(q, buildChatContext(exam, 'ASSISTANT')));

//: SSC's own wording, which no other exam may be given -- and which no exam may be given about shift papers.
const SSC_ONLY = [/SSC Tier-1/i, /\+2 correct/i, /−0\.5|-0\.5/, /SSC shift papers/i, /Staff Selection Commission/i, /\bSSC\b/];
const NEVER = [/previous-year shift papers/i, /full shift papers/i, /full previous-year/i];

/** A TGPSC-shaped record as the registry serves it: the authority's notices, no papers or keys GovOS has
 *  verified, and no practice engine registered for its id. Only the fields the answer reads are its own. */
const tgpsc: Exam = {
  ...IBPS_PO_EXAM,
  id: 'exam-websitenew-tgpsc-group-i-2024', title: 'TGPSC Group-I Services', code: 'TGPSC',
  authorityName: 'Telangana Public Service Commission', officialDomain: 'https://websitenew.tgpsc.gov.in/',
  resources: [{ ...(IBPS_PO_EXAM.resources || [])[0], id: 'tg-notice', title: 'TGPSC Group-I Services — Examination Notice (official PDF)',
    url: 'https://websitenew.tgpsc.gov.in/notice.pdf', subject: 'Official Gazette' } as any],
  officialPapers: [], answerKeys: []
};
/** An exam GovOS knows nothing practice-related about: no papers, no keys, no stages, no engine. */
const unknown: Exam = {
  ...IBPS_PO_EXAM, id: 'exam-unknown-board-2031', title: 'Unknown Board Examination 2031', code: 'UBE',
  authorityName: 'Unknown Board', officialDomain: 'https://board.example.gov.in/', resources: [], stages: [],
  officialPapers: [], answerKeys: []
};

// A. SSC: its own record supports GovOS-authored practice papers on the Tier-I pattern, scored the way
//    its notice prints; never "previous-year shift papers".
const tier1 = SSC_CGL_EXAM.stages.find(s => s.tier === 'TIER_1')!;
for (const a of answers(SSC_CGL_EXAM)) {
  check('SSC: points at Practice & PYQs', a.action?.section === 9, JSON.stringify(a.action));
  check('SSC: GovOS-authored papers, said to be not SSC\'s shift papers',
    /GovOS-authored, not Staff Selection Commission's own shift papers/.test(a.text), a.text.slice(0, 200));
  check('SSC: marking is the notice\'s own words', a.text.includes(tier1.negativeMarking), tier1.negativeMarking);
  check('SSC: the paper-building chat is still offered', /\*\*Mock Tests\*\* has the chat/.test(a.text));
  for (const re of NEVER) check(`SSC: never says ${re}`, !re.test(a.text), a.text.slice(0, 160));
}

// B-E. Every other exam: its own state, nothing of SSC's.
const others: Array<[string, Exam, (t: string) => boolean, string]> = [
  ['TGPSC', tgpsc, t => /no verified previous-year papers or answer keys for TGPSC Group-I Services/.test(t)
    && /its practice section is not built yet/.test(t), 'no verified papers; practice not built'],
  ['UPSC', UPSC_CSE_EXAM, t => /from Union Public Service Commission itself/.test(t) && /not scored/.test(t)
    && /GovOS has not written practice questions for UPSC/.test(t), 'UPSC\'s own papers; essay items unscored'],
  ['IBPS', IBPS_PO_EXAM, t => /no verified previous-year papers or answer keys for IBPS/.test(t)
    && /GovOS has not written practice questions for IBPS/.test(t), 'no verified papers; none written'],
  ['unknown exam', unknown, t => /no verified previous-year papers or answer keys for Unknown Board Examination 2031/.test(t)
    && /practice section is not built yet/.test(t) && !/Exam Pattern/.test(t), 'honest unavailable state'],
];
for (const [name, exam, own, what] of others) {
  for (const a of answers(exam)) {
    check(`${name}: ${what}`, own(a.text), a.text.slice(0, 260));
    check(`${name}: points at Practice & PYQs`, a.action?.section === 9, JSON.stringify(a.action));
    for (const re of [...SSC_ONLY, ...NEVER]) check(`${name}: no SSC wording ${re}`, !re.test(a.text), a.text.slice(0, 200));
    check(`${name}: does not offer SSC's paper-building chat`, !/\*\*Mock Tests\*\* has the chat/.test(a.text));
  }
}
// UPSC's figures are its record's, counted here the same way: the papers it published and its own items.
const upsc = answers(UPSC_CSE_EXAM)[0].text;
const upscPapers = (UPSC_CSE_EXAM.resources || []).filter(r => r.subject === 'Previous Year Papers' && r.type === 'OFFICIAL_PDF').length;
check('UPSC: counts at least its published PDFs', new RegExp(`has (${upscPapers}|[1-9]\\d*) paper`).test(upsc), upsc.slice(0, 200));

console.log(failures === 0 ? 'ALL ASSISTANT PRACTICE CHECKS PASSED' : failures + ' FAILED');
process.exit(failures === 0 ? 0 : 1);
