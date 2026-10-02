// The assistant's "how do I apply" answer is the selected exam's own, read from its application guide. It used
// to tell every exam's candidates "the form itself is filled on SSC's own portal at ssc.gov.in", and to promise
// certificate rules and rejection pitfalls whether or not the exam's guide had them.
// Run: npm run check:frontend
import './stub';
import { answerCandidateQuery } from '../../src/ui';
import { buildChatContext } from '../../src/services';
import { ALL_EXAMS, IBPS_PO_EXAM, SSC_CGL_EXAM } from '../../src/data';
import type { Exam } from '../../src/types';

let failures = 0;
const check = (name: string, ok: boolean, detail = '') => {
  if (!ok) failures++;
  if (!ok || process.env.VERBOSE) console.log((ok ? 'PASS ' : 'FAIL ') + name + (detail ? ' :: ' + detail : ''));
};

// A "how do I" question takes the platform map's answer; a plain question about registering takes the fact
// answer. Each is checked to land where it is meant to, so neither path can go untested.
const QUESTIONS: [string, 'PLATFORM' | 'FACT'][] = [['how do I apply', 'PLATFORM'], ['tell me about the otr registration', 'FACT']];
const ask = (exam: Exam, q: string) => answerCandidateQuery(q, buildChatContext(exam, 'ASSISTANT'));
const SSC_ONLY = [/ssc\.gov\.in/i, /\bSSC\b/, /Staff Selection Commission/i];

const spec = (rules: string[] = []) => ({ documentType: '', dimensions: '', fileFormat: '', fileSize: '', rules, sampleDescription: '' });
/** A TGPSC-shaped guide as the registry serves it: its own OTR portal, one registration step, upload rules,
 *  six listed documents and a fee; no certificate rules and no rejection pitfalls on record. */
const tgpsc: Exam = {
  ...IBPS_PO_EXAM, id: 'exam-websitenew-tgpsc-group-i-2024', title: 'TGPSC Group-I Services', code: 'TGPSC',
  authorityName: 'Telangana Public Service Commission', officialDomain: 'https://websitenew.tgpsc.gov.in/',
  applicationGuide: {
    officialPortal: 'https://otr.tgpsc.gov.in', otrSteps: [{ step: 1, title: 'One Time Registration' } as any],
    photoRules: spec(['Upload a recent photograph']), signatureRules: spec(['Upload a signature']),
    certificateRules: [], rejectionPitfalls: [],
    requiredDocuments: Array.from({ length: 6 }, (_, i) => ({ id: `d${i}`, name: `Document ${i + 1}`, required: true, specifications: [] })),
    fee: { amounts: ['Rs. 200'], rules: [], acceptedModes: [], exemptions: [] }
  }
};
/** An exam whose guide records nothing: no portal, no steps, no rules. */
const unknown: Exam = {
  ...IBPS_PO_EXAM, id: 'exam-unknown-board-2031', title: 'Unknown Board Examination 2031', code: 'UBE',
  authorityName: 'Unknown Board', officialDomain: 'https://board.example.gov.in/',
  applicationGuide: { officialPortal: '', otrSteps: [], photoRules: spec(), signatureRules: spec(), certificateRules: [], rejectionPitfalls: [] }
};

const exams: Exam[] = [...ALL_EXAMS, tgpsc, unknown];
for (const exam of exams) {
  const g = exam.applicationGuide;
  for (const [q, path] of QUESTIONS) {
    const a = ask(exam, q);
    const t = a.text;
    const tag = `${exam.id} / "${q}"`;
    check(`${tag}: answered by the ${path === 'PLATFORM' ? 'platform map' : 'fact answer'}`, (a.sourceKind === 'PLATFORM') === (path === 'PLATFORM'), String(a.sourceKind));
    check(`${tag}: points at Application & Documents`, a.action?.section === 4, JSON.stringify(a.action));
    if (g.officialPortal) check(`${tag}: names its own portal`, t.includes(g.officialPortal), t.slice(0, 160));
    else check(`${tag}: says no portal is on record`, /has not recorded where applications/.test(t), t.slice(0, 160));
    if (exam.id !== SSC_CGL_EXAM.id) for (const re of SSC_ONLY) check(`${tag}: no SSC wording ${re}`, !re.test(t), t.slice(0, 200));
    // Nothing the guide does not hold.
    check(`${tag}: registration steps only where recorded`, /registration step/.test(t) === (g.otrSteps.length > 0), t.slice(0, 200));
    check(`${tag}: certificate rules only where recorded`, /certificates must be valid/.test(t) === ((g.certificateRules || []).length > 0));
    check(`${tag}: rejection mistakes only where recorded`, /applications rejected/.test(t) === ((g.rejectionPitfalls || []).length > 0));
    check(`${tag}: fee only where recorded`, /fee as the notice prints it/.test(t) === !!g.fee);
    check(`${tag}: listed documents only where recorded`, /documents the notice lists/.test(t) === ((g.requiredDocuments || []).length > 0));
  }
}
// SSC keeps its own portal, and its own counts.
const ssc = ask(SSC_CGL_EXAM, 'how do I apply').text;
check('SSC: its own portal and its guide\'s counts', ssc.includes(SSC_CGL_EXAM.applicationGuide.officialPortal)
  && ssc.includes(`${SSC_CGL_EXAM.applicationGuide.otrSteps.length} registration steps`)
  && ssc.includes(`${SSC_CGL_EXAM.applicationGuide.rejectionPitfalls.length} mistakes`), ssc.slice(0, 220));

console.log(failures === 0 ? 'ALL ASSISTANT APPLICATION CHECKS PASSED' : failures + ' FAILED');
process.exit(failures === 0 ? 0 : 1);
