// A new exam is added by adding its validated data; the existing engine handles it. This runs an exam
// GovOS does not hold (future_exam_fixture.ts: an invented authority, its own stage labels, subjects,
// marking and dates) through the unchanged assistant, section-state resolver, exam page and practice
// rules, and checks that every answer comes from its own record, no other exam's evidence or words
// reach it, and that none of this needed a line of src/ to name it.
// Run: npm run check:frontend
import './stub';
import { readFileSync } from 'fs';
import { join } from 'path';
import * as React from 'react';
import { renderToString } from 'react-dom/server';
import { answerCandidateQuery, ExamDetailView, resolveSectionState, skillTestInRecord } from '../../src/ui';
import { buildChatContext, conversationService } from '../../src/services';
import { ALL_EXAMS, mockPaperProblems, SSC_TIER1_MARKING } from '../../src/data';
import type { MockPaper } from '../../src/data';
import type { DiscoveredSourceItem, DiscoveredSources, Exam, PracticeQuestion } from '../../src/types';
import { FUTURE_AUTHORITY, FUTURE_ID, FUTURE_TITLE, futureExam, futureMachineExam } from './future_exam_fixture';

(globalThis as any).fetch = async () => ({ ok: false, status: 503, json: async () => ({}) });

let failures = 0;
const check = (name: string, ok: boolean, detail = '') => {
  if (!ok) failures++;
  if (!ok || process.env.VERBOSE) console.log((ok ? 'PASS ' : 'FAIL ') + name + (detail ? ' :: ' + detail : ''));
};
const flat = (html: string) => html.replace(/<!--.*?-->/g, '').replace(/<[^>]+>/g, ' ').replace(/&amp;/g, '&')
  .replace(/&#x27;/g, "'").replace(/&quot;/g, '"').replace(/\s+/g, ' ');

// Everything that identifies another exam: titles, authorities, codes, and the vocabulary only one
// authority uses. None of it may appear in what GovOS tells this exam's candidate.
const OTHER_EXAM_WORDS: RegExp[] = [
  ...ALL_EXAMS.flatMap(e => [e.title, e.authorityName.split(' (')[0]]).map(s => new RegExp(s.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'), 'i')),
  /\bSSC\b/, /\bUPSC\b/, /\bIBPS\b/, /\bAPPSC\b/, /\bTGPSC\b/, /\bCGL\b/, /\bCSAT\b/, /\bDEST\b/, /\bCKT\b/, /Data Entry Speed Test/i,
  /\bTier-?(?:I|II|1|2)\b/i, /Online CBT \+ Typing Test/i,
];
const leaks = (text: string) => OTHER_EXAM_WORDS.filter(re => re.test(text)).map(re => {
  const m = text.match(new RegExp(`.{0,50}${re.source}.{0,30}`, re.flags.replace('g', '')));
  return m ? m[0] : String(re);
});

const exam = futureExam();
check('fixture: not one of the register\'s exams', !ALL_EXAMS.some(e => e.id === FUTURE_ID || e.title === FUTURE_TITLE));

// ---------------------------------------------------------------- 1. assistant answers from its own record
conversationService.clear('ASSISTANT');
const ask = (e: Exam, q: string) => {
  const r = answerCandidateQuery(q, buildChatContext(e, 'ASSISTANT'));
  return r.text;
};
const answers: Record<string, { q: string; must: (string | RegExp)[] }> = {
  typing: { q: 'where is the typing practice tool', must: ['Paper III: Typing Test (qualifying)', 'Phase B: Written Examination', 'Qualifying at 25 words a minute (Para 7.4)'] },
  negative: { q: 'is there negative marking', must: ['one-third of the marks of a question deducted', 'no deduction for a wrong answer'] },
  pattern: { q: 'what is the exam pattern', must: ['Phase A: Screening Test', 'Phase B: Written Examination'] },
  syllabus: { q: 'what is the syllabus', must: [/3 topics/, 'General Studies: 2 topics', /Applied Statistics: 1 topic$/m] },
  lastDate: { q: 'what is the last date to apply', must: [/2031-02-19|19(?:th)? Feb(?:ruary)? 2031|19-02-2031/] },
  vacancies: { q: 'how many vacancies are there', must: ['612'] },
};
for (const [name, { q, must }] of Object.entries(answers)) {
  const t = ask(exam, q);
  for (const m of must) check(`assistant ${name}: states its own "${m}"`, typeof m === 'string' ? t.includes(m) : m.test(t), t.slice(0, 300));
  check(`assistant ${name}: no other exam's words`, leaks(t).length === 0, leaks(t).join(' | '));
}
// The typing answer follows wherever the record states the test, and only there.
const viaMode = ask(futureExam('MODE'), 'where is the typing practice tool');
check('assistant typing (mode only): quotes the stage and its mode', viaMode.includes('"Computer-based test with a keyboard typing test"')
  && viaMode.includes('Phase B: Written Examination') && !/record has no typing/.test(viaMode), viaMode);
check('assistant typing (mode only): invents no speed, duration or marks', !/\d+\s*(?:words|wpm|minutes?|marks?)\b/i.test(viaMode.split('\n\n')[1] || ''), viaMode);
const none = ask(futureExam('NONE'), 'where is the typing practice tool');
check('assistant typing (none): says its record has none', /record has no typing or data-entry test/.test(none), none);
check('skill-test reader: section, then mode, then none', skillTestInRecord(futureExam('SECTION'))?.where === 'SECTION'
  && skillTestInRecord(futureExam('MODE'))?.where === 'MODE' && skillTestInRecord(futureExam('NONE')) === null);
// Switching from a real exam to this one carries nothing over.
const ssc = ALL_EXAMS[0];
conversationService.append('ASSISTANT', { role: 'assistant', text: ask(ssc, 'where is the typing practice tool'), examId: ssc.id });
conversationService.clear('ASSISTANT');
const afterSwitch = ask(exam, 'and the typing test?');
check('assistant: after a switch from another exam, only this exam\'s answer', afterSwitch.includes(FUTURE_AUTHORITY.split(' (')[0])
  && leaks(afterSwitch).length === 0, afterSwitch.slice(0, 200));
conversationService.clear('ASSISTANT');

// ---------------------------------------------------------------- 2. section banners from its own evidence
const NF = 'SOURCE_NOT_FOUND_AFTER_SEARCH';
const machine = futureMachineExam();
const item = (over: Partial<DiscoveredSourceItem>): DiscoveredSourceItem => ({
  title: 'Item', url: 'https://zssc.example.gov.in/doc.pdf', context: '', role: 'QUESTION_PAPER', section: 'PRACTICE',
  sourceLabel: 'Official source', sourceClass: 'PRIMARY_OFFICIAL', status: 'FETCHED', obtainable: true, foundOn: '',
  foundOnTitle: '', relation: 'THIS_EXAM', identity: {}, duplicateOf: '', ...over
});
const walk = (examId: string, states: Record<string, string>, items: DiscoveredSourceItem[]): DiscoveredSources => ({
  examId, state: 'DISCOVERED', portals: items.filter(i => /PORTAL/.test(i.role)),
  repositories: [{ title: 'Listing', url: 'https://zssc.example.gov.in/list', role: 'NOTIFICATION', section: 'OFFICIAL_LINKS',
    sourceLabel: 'Official source', items: items.filter(i => !/PORTAL/.test(i.role)), itemCount: items.length, listedWithoutLink: [],
    itemsForThisExam: items.length, status: 'FETCHED', note: '' }],
  searchStates: Object.fromEntries(Object.entries(states).map(([k, v]) => [k, { state: v, reason: '' }])) as any
});
const ROLES = ['QUESTION_PAPER', 'ANSWER_KEY', 'CUTOFF', 'RESULT', 'ADMIT_CARD', 'SYLLABUS', 'CORRIGENDUM', 'NOTIFICATION', 'APPLICATION_PORTAL'] as const;
const everything = (relation: string) => ROLES.map(role => item({ role, relation, url: `https://zssc.example.gov.in/${role.toLowerCase()}` }));
const allFound = Object.fromEntries(ROLES.map(r => [r, 'FOUND_VERIFIED']));
const nums = Object.values(machine.sectionStates!).map(s => s.sectionNum);
const states = (d: DiscoveredSources | null, e: Exam = machine) => Object.fromEntries(nums.map(n => [n, resolveSectionState(e, n, d)]));

// Another exam's walk, carrying an item of every role "for this exam": none of it may reach this exam.
const foreign = states(walk('exam-some-other-board-2031', allFound, everything('THIS_EXAM')));
check('banners: another exam\'s evidence satisfies no section', Object.values(foreign).every(s => s === NF), JSON.stringify(foreign));
// Its own walk, every item naming another exam or cycle: found nowhere, and not "not found" either.
const otherRel = states(walk(FUTURE_ID, allFound, [...everything('OTHER_EXAM'), ...everything('THIS_EXAM_OTHER_CYCLE')]));
check('banners: other exams\' and cycles\' items prove nothing', !Object.values(otherRel).includes('FOUND_AFTER_BUILD'), JSON.stringify(otherRel));
// Its own walk, its own items: each section found by its own evidence role, and only those.
const own = states(walk(FUTURE_ID, allFound, everything('THIS_EXAM')));
const EXPECT_FOUND = [4, 6, 9, 10, 12, 13, 14, 16, 30];
check('banners: sections with their own evidence are found', EXPECT_FOUND.every(n => own[n] === 'FOUND_AFTER_BUILD'), JSON.stringify(own));
check('banners: sections with no evidence role keep the build state (1, 2, 3, 5, 15)', [1, 2, 3, 5, 15].every(n => own[n] === NF), JSON.stringify(own));
// A section the platform has no default for works from the role the record declares.
const keysOnlyIncomplete = states(walk(FUTURE_ID, { ANSWER_KEY: 'SEARCH_INCOMPLETE' }, []));
check('banners: a record-declared section (30, answer keys) reads its declared role', keysOnlyIncomplete[30] === 'SEARCH_INCOMPLETE'
  && keysOnlyIncomplete[9] === NF, JSON.stringify(keysOnlyIncomplete));
const declaredPyqs = futureMachineExam({ pyqs: { state: NF, nature: 'OFFICIAL_FACT', studentStatusSummary: '', sectionNum: 9, isApplicable: true,
  evidenceRoles: ['QUESTION_PAPER', 'ANSWER_KEY'] } });
const keyFound = walk(FUTURE_ID, { ANSWER_KEY: 'FOUND_VERIFIED' }, [item({ role: 'ANSWER_KEY' })]);
check('banners: a record may widen a section\'s evidence (pyqs + answer keys)', resolveSectionState(declaredPyqs, 9, keyFound) === 'FOUND_AFTER_BUILD',
  String(resolveSectionState(declaredPyqs, 9, keyFound)));
check('banners: without that declaration an answer key is a sibling and proves nothing', resolveSectionState(machine, 9, keyFound) === NF,
  String(resolveSectionState(machine, 9, keyFound)));
check('banners: no walk keeps every build state', Object.values(states(null)).every(s => s === NF));

// ---------------------------------------------------------------- 3. the exam page renders its own record
const page = (e: Exam, n: number) => flat(renderToString(React.createElement(ExamDetailView as any, {
  exam: e, initialSection: n, onOpenProvenanceModal() {}, onOpenReportModal() {}
})));
const PAGE_SECTIONS: Record<number, (string | RegExp)[]> = {
  1: [FUTURE_AUTHORITY, 'Phase A → Phase B'],
  2: ['Last date for online applications'],
  3: [/AGE MAX\s*(?:<=|&lt;=)\s*37/],
  5: ['Phase A: Screening Test', 'Phase B: Written Examination', 'one-third of the marks of a question deducted'],
  6: ['History of Zenith State', 'Sampling methods'],
  9: ['Phase A: Screening Test', 'practice is not available yet'],
  15: [],
};
for (const [n, must] of Object.entries(PAGE_SECTIONS)) {
  const text = page(exam, Number(n));
  // The page chrome lists every exam's name in the header and finder; read the section's own body.
  const body = text.slice(Math.max(0, text.indexOf('Ask about this exam')));
  if (n === '1') check('page 1: carries its own title', text.includes(FUTURE_TITLE));
  for (const m of must) check(`page ${n}: shows its own "${m}"`, typeof m === 'string' ? body.includes(m) : m.test(body), body.slice(0, 200));
  check(`page ${n}: no other exam's words`, leaks(body).length === 0, leaks(body).slice(0, 4).join(' | '));
  check(`page ${n}: no other exam's practice papers`, !/Full-length practice paper/.test(body));
}
check('page 9 (machine): the build state reaches the banner', /Not found\s*\./.test(page(machine, 9)));

// ---------------------------------------------------------------- 4. practice metadata, at any scale
// 100 papers in this exam's own marking (+1, one-third off), each stating its own level.
const question = (p: number, i: number, difficulty: 'EASY' | 'MEDIUM' | 'HARD'): PracticeQuestion => ({
  id: `zssc-p${p}-q${i}`, topicId: 'syl-zssc-history', subject: 'General Studies', topicName: 'History of Zenith State', tier: 'PHASE_A',
  shiftInfo: 'GovOS practice question', questionType: 'SECTIONAL_MOCK', questionText: `Question ${i}`, difficulty,
  options: [{ id: 0, text: 'a' }, { id: 1, text: 'b' }, { id: 2, text: 'c' }, { id: 3, text: 'd' }], correctOptionIndex: i % 4,
  explanation: 'Worked from the record.', provenance: exam.dates[0].provenance
} as PracticeQuestion);
const ZSSC_MARKING = { correct: 1, wrong: 1 / 3, clause: 'Phase A: one mark a question; one-third off for a wrong answer (Para 6.3)' };
const LEVELS = ['EASY', 'MEDIUM', 'HARD'] as const;
const papers: MockPaper[] = Array.from({ length: 100 }, (_, p) => {
  const level = LEVELS[p % 3];
  const questions = Array.from({ length: 50 }, (_, i) => question(p, i, i < 30 ? level : LEVELS[(p + 1) % 3]));
  return { id: `zssc-paper-${p + 1}`, title: `Screening practice paper ${p + 1}`, category: 'FULL_SHIFT', examTier: 'Phase A',
    totalQuestions: 50, totalMarks: 50, durationMinutes: 60, difficulty: p % 10 === 0 ? 'ADAPTIVE' : level,
    description: 'GovOS practice paper written to the ZSSC Screening Test pattern.', provenanceTag: 'GovOS practice paper',
    marking: ZSSC_MARKING, questions } as MockPaper;
});
const found = papers.map(p => mockPaperProblems(p)).filter(x => x.length);
check('practice: 100 papers in its own marking pass the same rules', found.length === 0, found.slice(0, 3).join(' / '));
check('practice: scored by its own marking, never SSC\'s', papers.every(p => p.marking !== SSC_TIER1_MARKING && p.marking.wrong === 1 / 3));
const bad = (over: Partial<MockPaper>) => mockPaperProblems({ ...papers[1], ...over });
check('practice: a relative claim is caught', bad({ title: 'Screening practice paper 2 (harder mix)' }).some(s => /claims/.test(s)));
check('practice: a level its questions do not bear is caught', bad({ difficulty: 'HARD' }).some(s => /labelled HARD/.test(s)));
check('practice: totals that do not follow from the marking are caught', bad({ totalMarks: 100 }).some(s => /totalMarks/.test(s)));
check('practice: a paper without its marking is caught', bad({ marking: undefined as any }).some(s => /marking/.test(s)));

// ---------------------------------------------------------------- 5. no exam-specific code was needed
// The functions this rests on name no exam: no exam id, no exam constant, no authority, in their code.
const read = (f: string) => readFileSync(join(process.cwd(), 'src', f), 'utf8').replace(/\r\n/g, '\n');
const ui = read('ui.tsx');
const dataSrc = read('data.ts');
const body = (src: string, start: string) => {
  const i = src.indexOf(start);
  if (i < 0) return '';
  const j = src.indexOf('\n};', i);
  const k = src.indexOf('\n}\n', i);
  const end = [j, k].filter(x => x > i).sort((a, b) => a - b)[0] ?? src.length;
  return src.slice(i, end).replace(/\/\*[\s\S]*?\*\//g, '').replace(/\/\/[^\n]*/g, '');   // code, not comments
};
const GENERIC = [
  ['skillTestInRecord', body(ui, 'export const skillTestInRecord')], ['SKILL_TEST_WORDS', body(ui, 'export const SKILL_TEST_WORDS')],
  ['typingAnswerFor', body(ui, 'const typingAnswerFor')], ['SECTION_EVIDENCE_ROLES', body(ui, 'export const SECTION_EVIDENCE_ROLES')],
  ['provesSection', body(ui, 'const provesSection')], ['resolveSectionState', body(ui, 'export const resolveSectionState')],
  ['SectionStateNote', body(ui, 'const SectionStateNote')], ['mockPaperProblems', body(dataSrc, 'export function mockPaperProblems')],
] as const;
const EXAM_SPECIFIC = /'exam-[a-z0-9-]+'|\b(?:SSC_CGL|UPSC_CSE|IBPS_PO|APPSC_GROUP[12]|TGPSC)\w*|PRACTICE_BANK_EXAM_ID|\b(?:SSC|UPSC|IBPS|APPSC|TGPSC|DEST|CKT)\b/;
for (const [name, code] of GENERIC) {
  check(`generic: ${name} found`, code.length > 0);
  check(`generic: ${name} names no exam`, !EXAM_SPECIFIC.test(code), (code.match(EXAM_SPECIFIC) || [''])[0]);
}
check('generic: nothing in src/ names the new exam', !/zssc|zenith/i.test(ui + dataSrc + read('services.ts')));

console.log(failures === 0 ? 'ALL FUTURE EXAM CHECKS PASSED' : failures + ' FAILED');
process.exit(failures === 0 ? 0 : 1);
