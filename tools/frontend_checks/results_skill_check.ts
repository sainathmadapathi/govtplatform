// Results & Next Steps renders each exam's own record: skill tests come from `ExamStage.skillTest`
// and nothing else, their standards are the ones the notice prints, nothing missing is filled in, and
// no exam's result vocabulary reaches another. Runs the real section (section 16 of ExamDetailView)
// for every register exam and three synthetic future exams, plus the pure interpretation functions.
// Run: npm run check:frontend
import './stub';
import { readFileSync } from 'fs';
import { join } from 'path';
import * as React from 'react';
import { renderToString } from 'react-dom/server';
import {
  evaluateSkillTest, ExamDetailView, meritMaxOf, meritSectionsOf, skillScoreOf, skillStandardFor, skillTestsOf
} from '../../src/ui';
import { storageService } from '../../src/services';
import { ALL_EXAMS, APPSC_GROUP1_EXAM, APPSC_GROUP2_EXAM, IBPS_PO_EXAM, SSC_CGL_EXAM, UPSC_CSE_EXAM } from '../../src/data';
import type { Exam, MultiTierResultEntry } from '../../src/types';
import { futureExamWithSkill } from './future_exam_fixture';

(globalThis as any).fetch = async () => ({ ok: false, status: 503, json: async () => ({}) });

let failures = 0;
const check = (name: string, ok: boolean, detail = '') => {
  if (!ok) failures++;
  if (!ok || process.env.VERBOSE) console.log((ok ? 'PASS ' : 'FAIL ') + name + (detail ? ' :: ' + detail : ''));
};
const flat = (html: string) => html.replace(/<!--.*?-->/g, '').replace(/<[^>]+>/g, ' ').replace(/&amp;/g, '&')
  .replace(/&#x27;/g, "'").replace(/&quot;/g, '"').replace(/&lt;/g, '<').replace(/&gt;/g, '>').replace(/\s+/g, ' ');

/** Section 16 as the candidate sees it, with `entry` saved for this exam (or nothing). */
const results = (exam: Exam, entry?: Partial<MultiTierResultEntry>) => {
  localStorage.removeItem(`govos_result_entry_${exam.id}`);
  if (entry) localStorage.setItem(`govos_result_entry_${exam.id}`, JSON.stringify({ source: 'TYPED', examId: exam.id, ...entry }));
  const html = renderToString(React.createElement(ExamDetailView as any, { exam, initialSection: 16, onOpenProvenanceModal() {}, onOpenReportModal() {} }));
  localStorage.removeItem(`govos_result_entry_${exam.id}`);
  const text = flat(html);
  return { html, text: text.slice(Math.max(0, text.indexOf('Ask about this exam'))), cards: (html.match(/data-skill-test="([^"]*)"/g) || []).map(m => m.slice(17, -1)) };
};
const cutoffRow = (exam: Exam) => [...exam.cutoffsHistory].filter(r => r.tier1Cutoff != null).sort((a, b) => b.year - a.year)[0];
/** An entry that clears this exam's latest stage-one cut-off, in its own category, so the stage grid renders. */
const clearing = (exam: Exam, extra: Partial<MultiTierResultEntry> = {}): Partial<MultiTierResultEntry> => {
  const row = cutoffRow(exam);
  return { marks: (row?.tier1Cutoff ?? 50) + 5, tier1Marks: (row?.tier1Cutoff ?? 50) + 5, category: row?.category ?? 'UR', examYear: row?.year, ...extra };
};

const SSC_TERMS = [/\bCKT\b/, /\bDEST\b/, /Data Entry Speed Test/i, /Computer Knowledge Test/i, /\bTier-?(?:I|II|1|2)\b/, /\b390\b/, /Ministry allocation/i,
  /SSC CHSL/, /RRB NTPC/, /Section-III/, /Section-IV/, /2000 key depressions/];
const IBPS_TERMS = [/\bIBPS\b/, /Online CBT \+ Typing Test/i, /Probationary Officer/i];
const found = (text: string, terms: RegExp[]) => terms.filter(re => re.test(text)).map(re => (text.match(new RegExp(`.{0,40}${re.source}.{0,30}`, re.flags)) || [String(re)])[0]);

// ---------------------------------------------------------------- 1. SSC keeps what its record supports
const sscTests = skillTestsOf(SSC_CGL_EXAM);
check('SSC: its record states one skill test, on Tier-II Paper-I', sscTests.length === 1 && sscTests[0].stage.id === 'stage-tier2-p1', JSON.stringify(sscTests.map(t => t.stage.id)));
const ckt = sscTests[0]?.test.metrics?.find(m => m.key === 'computerKnowledgeMarks')!;
const dest = sscTests[0]?.test.metrics?.find(m => m.key === 'destMistakesPercent')!;
// Para 16.1 / 16.2, as printed: CKT 30 / 25 / 20 % of 60; DEST at most 20 / 25 / 30 % errors.
check('SSC: CKT standard by category, computed from the printed %', [['UR', 18], ['OBC', 15], ['EWS', 15], ['SC', 12], ['ST', 12]]
  .every(([c, v]) => skillStandardFor(ckt, c as string)?.value === v && skillStandardFor(ckt, c as string)?.computed === true));
check('SSC: DEST standard by category, as printed', [['UR', 20], ['OBC', 25], ['EWS', 25], ['SC', 30]].every(([c, v]) => skillStandardFor(dest, c as string)?.value === v));
check('SSC: no category chosen, no standard claimed', skillStandardFor(ckt, '') === null);
check('SSC: CKT and DEST standards cite Para 16.1 and 16.2', /Para 16\.1/.test(ckt.standard!.asPrinted) && /Para 16\.2/.test(dest.standard!.asPrinted)
  && ckt.standard!.provenance?.clauseNumber?.startsWith('Para 16.1') === true && dest.standard!.provenance?.clauseNumber?.startsWith('Para 16.2') === true);
const judge = (entry: Partial<MultiTierResultEntry>, cat: string) => evaluateSkillTest(sscTests[0].stage, sscTests[0].test, entry as MultiTierResultEntry, cat).allPassed;
check('SSC: UR, CKT 20 and DEST 10% -> standards met', judge({ skillScores: { computerKnowledgeMarks: 20, destMistakesPercent: 10 } }, 'UR') === true);
check('SSC: UR, CKT 16 -> below (18 needed)', judge({ skillScores: { computerKnowledgeMarks: 16, destMistakesPercent: 10 } }, 'UR') === false);
check('SSC: OBC, CKT 16 -> met (15 needed)', judge({ skillScores: { computerKnowledgeMarks: 16, destMistakesPercent: 24 } }, 'OBC') === true);
check('SSC: UR, DEST 22% -> below (20% allowed)', judge({ skillScores: { computerKnowledgeMarks: 40, destMistakesPercent: 22 } }, 'UR') === false);
check('SSC: one figure missing -> not judged', judge({ skillScores: { computerKnowledgeMarks: 40 } }, 'UR') === null);
check('SSC: an entry stored before skillScores still reads', skillScoreOf({ computerKnowledgeMarks: 21 } as MultiTierResultEntry, 'computerKnowledgeMarks') === 21
  && judge({ computerKnowledgeMarks: 20, destMistakesPercent: 10 }, 'UR') === true);
check('SSC: Tier-II Paper-I merit is 390 of 450, from its record', meritMaxOf(SSC_CGL_EXAM.stages[1]) === 390 && SSC_CGL_EXAM.stages[1].totalMarks === 450);
check('SSC: merit sections exclude the skill sections', JSON.stringify(meritSectionsOf(SSC_CGL_EXAM.stages[1]).map(s => s.split(':')[0])) === '["Section-I","Section-II"]');

const ssc = results(SSC_CGL_EXAM, clearing(SSC_CGL_EXAM, { category: 'UR', marks: 199, tier1Marks: 199, skillScores: { computerKnowledgeMarks: 20, destMistakesPercent: 10 } }));
check('SSC page: one skill card, under its record\'s name', ssc.cards.length === 1 && /Computer Knowledge Test/.test(ssc.cards[0]), JSON.stringify(ssc.cards));
check('SSC page: CKT and DEST with figures and printed standards', /CKT, Section-III\): 20 marks \/ 60/.test(ssc.text) && /DEST, Section-IV\): 10% errors/.test(ssc.text)
  && /At least 18 marks \/ 60 for UR \(computed from the printed percentage\)/.test(ssc.text) && /At most 20% errors for UR/.test(ssc.text), ssc.text.slice(ssc.text.indexOf('Stage 3'), ssc.text.indexOf('Stage 3') + 500));
check('SSC page: standards met', /STANDARDS MET/.test(ssc.text));
check('SSC page: Tier-II merit shown out of 390', /\/ 390/.test(ssc.text));
check('SSC page: the skill tab carries its record\'s name', /Section-III Qualifying standards from the notice/.test(ssc.text), (ssc.text.match(/.{0,60}Qualifying standards.{0,20}/) || [''])[0]);
check('SSC page: no IBPS words', found(ssc.text, IBPS_TERMS).length === 0, found(ssc.text, IBPS_TERMS).join(' | '));
const sscBelow = results(SSC_CGL_EXAM, clearing(SSC_CGL_EXAM, { category: 'UR', marks: 199, tier1Marks: 199, skillScores: { computerKnowledgeMarks: 11, destMistakesPercent: 10 } }));
check('SSC page: below a standard is said so', /BELOW A STANDARD/.test(sscBelow.text));
const sscNone = results(SSC_CGL_EXAM, clearing(SSC_CGL_EXAM, { category: 'UR', marks: 199, tier1Marks: 199 }));
check('SSC page: no figures -> "not entered", never a pass', /CKT, Section-III\): not entered/.test(sscNone.text) && !/STANDARDS MET/.test(sscNone.text) && /QUALIFYING/.test(sscNone.text));
check('SSC page: next step names its own merit sections and skill test', /prepare for Tier-II \(Section-I: [^)]*Reasoning and General Intelligence; Section-II: [^)]*General Awareness\)/.test(sscNone.text)
  && /plus the qualifying Section-III \(Computer Knowledge Test\) and Section-IV \(Data Entry Speed Test\)/.test(sscNone.text),
  (sscNone.text.match(/Next: prepare[^.]{0,260}/) || [''])[0]);

// ---------------------------------------------------------------- 2. other register exams inherit nothing
for (const exam of [IBPS_PO_EXAM, APPSC_GROUP1_EXAM, APPSC_GROUP2_EXAM, UPSC_CSE_EXAM]) {
  check(`${exam.id}: its record states no skill test`, skillTestsOf(exam).length === 0);
  // As if a scorecard reading had reported SSC-named fields for this exam: they must not surface.
  const r = results(exam, clearing(exam, { computerKnowledgeMarks: 40, destMistakesPercent: 5 } as Partial<MultiTierResultEntry>));
  check(`${exam.id} page: no skill card`, r.cards.length === 0, JSON.stringify(r.cards));
  const leak = found(r.text, SSC_TERMS);
  check(`${exam.id} page: no SSC result terms`, leak.length === 0, leak.join(' | '));
  if (exam.id !== IBPS_PO_EXAM.id) check(`${exam.id} page: no IBPS result terms`, found(r.text, IBPS_TERMS.slice(1)).length === 0);
}
check('UPSC keeps its own engine', /UPSC CIVIL SERVICES 3-STAGE/.test(results(UPSC_CSE_EXAM).text));

// ---------------------------------------------------------------- 3. synthetic future exams
const A = futureExamWithSkill('A'), B = futureExamWithSkill('B'), C = futureExamWithSkill('C');
const a = results(A, clearing(A, { skillScores: { practicalAssessmentMarks: 30 } }));
check('Future A: one card, its own Practical Assessment', JSON.stringify(a.cards) === '["Practical Assessment"]', JSON.stringify(a.cards));
check('Future A: its duration, requirement and printed standard', /Duration: 45 minutes/.test(a.text) && /Prepare one land-record extract/.test(a.text)
  && /At least 20 marks \/ 50 for General \(computed from the printed percentage\)/.test(a.text) && /Para 8\.4/.test(a.text), a.text.slice(a.text.indexOf('Practical Assessment'), a.text.indexOf('Practical Assessment') + 400));
check('Future A: 30 of 50 meets the General standard', /STANDARDS MET/.test(a.text));
check('Future A: "all other categories" applies to Backward Classes', skillStandardFor(skillTestsOf(A)[0].test.metrics![0], 'Backward Classes')?.value === 17.5);
check('Future A: only its own terminology', found(a.text, [...SSC_TERMS, ...IBPS_TERMS]).length === 0, found(a.text, [...SSC_TERMS, ...IBPS_TERMS]).join(' | '));
const b = results(B, clearing(B));
check('Future B: no skill card, though a section is named "Typing Test"', b.cards.length === 0 && B.stages[1].sections.some(s => /Typing Test/.test(s.sectionName)));
check('Future B: no skill tab', !/Qualifying standards from the notice|What the notice states/.test(b.text));
check('Future B: the grid still renders its own stages', /Stage 1: Phase A/.test(b.text) && /Stage 2: Phase B/.test(b.text) && /Stage 3: Post Allocation/.test(b.text));
const c = results(C, clearing(C));
check('Future C: one card, under the name the notice gives', JSON.stringify(c.cards) === '["Proficiency Check"]');
check('Future C: says what the record does not state', /does not state whether it is qualifying, its duration or what it involves, how it is scored/.test(c.text),
  c.text.slice(c.text.indexOf('Proficiency Check'), c.text.indexOf('Proficiency Check') + 300));
const cCard = c.text.slice(c.text.indexOf('Stage 3: Proficiency Check'), c.text.indexOf('Stage 4'));
check('Future C: invents no standard, duration, score or status', !/At least|At most|minutes|%|STANDARDS MET|BELOW|QUALIFYING\b/.test(cCard) && /NOT STATED/.test(cCard), cCard);
check('Future C: the next step does not call its unstated test qualifying', /plus the Proficiency Check/.test(c.text) && !/qualifying Proficiency Check/.test(c.text),
  (c.text.match(/Next: prepare[^.]{0,200}/) || [''])[0]);
for (const [n, r] of [['A', a], ['B', b], ['C', c]] as const) check(`Future ${n}: no SSC or IBPS terms anywhere in the section`, found(r.text, [...SSC_TERMS, ...IBPS_TERMS]).length === 0);
// A future exam whose code says UPSC is not the CSE: it gets the stage engine, not CSE's.
const upscLike: Exam = { ...B, id: 'exam-upsc-combined-defence-2031', code: 'UPSC_CDS_2031', title: 'Combined Defence Services Examination 2031' };
const ul = results(upscLike, clearing(upscLike));
check('future UPSC-coded exam: not handed the CSE engine', !/3-STAGE|CSAT|1750|Prelims GS-1/.test(ul.text) && /Stage 1: Phase A/.test(ul.text));

// ---------------------------------------------------------------- 4. switching exams keeps nothing
storageService.setResultEntry({ examId: SSC_CGL_EXAM.id, marks: 150, tier1Marks: 150, category: 'UR', source: 'TYPED', skillScores: { computerKnowledgeMarks: 55 } } as MultiTierResultEntry, SSC_CGL_EXAM.id);
const ibpsAfter = flat(renderToString(React.createElement(ExamDetailView as any, { exam: IBPS_PO_EXAM, initialSection: 16, onOpenProvenanceModal() {}, onOpenReportModal() {} })));
check('switch: IBPS reads no SSC entry', storageService.getResultEntry(IBPS_PO_EXAM.id) === null && !/\b150\b/.test(ibpsAfter.slice(ibpsAfter.indexOf('Ask about this exam'))) && !/\b55\b.*marks \/ 60/.test(ibpsAfter));
// Future A with marks of its own but no skill figure: SSC's stored 55 must not become its figure.
const aAfter = results(A, clearing(A));
check('switch: Future A reads no SSC entry or skill figure', !/\b55\b/.test(aAfter.text) && /Practical Assessment: not entered/.test(aAfter.text)
  && !/STANDARDS MET/.test(aAfter.text), aAfter.text.slice(aAfter.text.indexOf('Stage 3'), aAfter.text.indexOf('Stage 3') + 300));
storageService.setResultEntry(null, SSC_CGL_EXAM.id);

// ---------------------------------------------------------------- 5. the generic engine names no exam
const ui = readFileSync(join(process.cwd(), 'src', 'ui.tsx'), 'utf8').replace(/\r\n/g, '\n');
const code = (start: string, end: string) => {
  const i = ui.indexOf(start), j = ui.indexOf(end, i);
  return i < 0 || j < 0 ? '' : ui.slice(i, j).replace(/\/\*[\s\S]*?\*\//g, '').replace(/\/\/[^\n]*/g, '').replace(/\{\/\*[\s\S]*?\*\/\}/g, '');
};
const interpretation = code('export const skillTestsOf', 'const RESULT_SCHEMES');
const card = code('const SkillTestCard', '// ResultNextStepsSection.tsx');
const section = code('export const ResultNextStepsSection', '\n};\n');
check('scan: the interpretation and the card were found', interpretation.length > 1500 && card.length > 1000 && section.length > 20000);
const EXAM_NAMES = /'exam-[a-z0-9-]+'|\b(?:SSC_CGL|UPSC_CSE|IBPS_PO|APPSC_GROUP[12])_EXAM\b|\b(?:SSC|UPSC|IBPS|APPSC|TGPSC|CKT|DEST)\b|Tier-?(?:I|II|1|2)\b/;
for (const [name, src] of [['interpretation (skillTestsOf … meritMaxOf)', interpretation], ['SkillTestCard', card]] as const) {
  check(`scan: ${name} names no exam, authority or SSC term`, !EXAM_NAMES.test(src), (src.match(EXAM_NAMES) || [''])[0]);
}
// The section keeps the CSE's own engine (registered by id in RESULT_SCHEMES); nothing SSC-shaped is left in it.
const SSC_SHAPED = /\bisSSC\b|\bCKT\b|\bDEST\b|\bSSC\b|SSC_CGL|cktCutoff|destMaxAllowed|candidateCKT|candidateDEST|\b390\b|Ministry allocation|CHSL|RRB NTPC|skill\|typing\|dest|Tier-?2 Paper|Tier-2 Total/;
check('scan: Results & Next Steps holds no SSC-specific logic, threshold or wording', !SSC_SHAPED.test(section), (section.match(SSC_SHAPED) || [''])[0]);
check('scan: no exam is detected by a code, id or title substring', !/exam\.(?:code|id|title)[^;\n]{0,40}\.(?:includes|toLowerCase)/.test(section));

console.log(failures === 0 ? 'ALL RESULTS SKILL-TEST CHECKS PASSED' : failures + ' FAILED');
process.exit(failures === 0 ? 0 : 1);
