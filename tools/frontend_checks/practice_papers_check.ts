// Practice papers claim nothing about themselves that their own questions do not bear out. Every full
// paper is the same template-cycled item set with the same difficulty mix, so none may be titled,
// described or levelled as harder or easier than another; papers 9 and 12 once were ("harder mix").
// Their questions, numbering and marking are frozen against the commit before the relabelling.
// Run: npm run check:frontend
import './stub';
import { createHash } from 'crypto';
import * as React from 'react';
import { renderToString } from 'react-dom/server';
import { ExamDetailView } from '../../src/ui';
import {
  mockPaperProblems, NEW_DISCOVERED_PAPERS, OFFICIAL_10_MOCK_PAPERS, SSC_CGL_EXAM, SSC_TIER1_MARKING, SUBJECT_MOCK_TESTS, TOPIC_DRILL_TESTS
} from '../../src/data';
import type { MockPaper } from '../../src/data';

(globalThis as any).fetch = async () => ({ ok: false, status: 503, json: async () => ({}) });

let failures = 0;
const check = (name: string, ok: boolean, detail = '') => {
  if (!ok) failures++;
  if (!ok || process.env.VERBOSE) console.log((ok ? 'PASS ' : 'FAIL ') + name + (detail ? ' :: ' + detail : ''));
};

const FULL: MockPaper[] = [...OFFICIAL_10_MOCK_PAPERS, ...NEW_DISCOVERED_PAPERS];
const ALL: MockPaper[] = [...FULL, ...SUBJECT_MOCK_TESTS, ...TOPIC_DRILL_TESTS];
const CLAIM = /\b(harder|hardest|easier|easiest|tougher|toughest|difficult|advanced level|beginner|challenging|stiffer)\b/i;

// ---------------------------------------------------------------- 1. papers 9 and 12
const nine = FULL.find(p => p.id === 'paper-cgl-2023-t2');
const twelve = FULL.find(p => p.id === 'paper-cgl-2024-t2');
for (const [n, p] of [[9, nine], [12, twelve]] as const) {
  check(`paper ${n}: present`, !!p);
  if (!p) continue;
  check(`paper ${n}: title makes no difficulty claim`, !CLAIM.test(p.title), p.title);
  check(`paper ${n}: description makes no difficulty claim`, !CLAIM.test(p.description), p.description);
  check(`paper ${n}: keeps its number in its title`, new RegExp(`\\bpaper ${n}\\b`).test(p.title), p.title);
  check(`paper ${n}: no paper-level level beyond the other full papers'`, p.difficulty === 'ADAPTIVE', p.difficulty);
}

// ---------------------------------------------------------------- 2. questions, numbering, marking unchanged
// sha256 of {questions, totalQuestions, totalMarks, durationMinutes}, computed from src/data.ts at
// 50dcdfe (main, before the relabelling). A label change may never move one of these.
const FROZEN: Record<string, string> = {
  'paper-cgl-2024-s1': '853f67fd6523d53d', 'paper-cgl-2024-s2': '0032c4b9be22e20b', 'paper-cgl-2024-s3': 'f2ec51ca539a3419',
  'paper-cgl-2024-s4': '9e89e95ad81de59c', 'paper-cgl-2024-s5': 'bc0d37d8146c5a6f', 'paper-cgl-2023-s1': '175aa8832e594e13',
  'paper-cgl-2023-s2': '5d34e2de884231fa', 'paper-cgl-2023-s3': '1ec46bceba0f4edd', 'paper-cgl-2023-t2': '2bbea9d770b33277',
  'paper-cgl-2022-s1': 'd323a5d2a82bdeaf', 'paper-cgl-2024-s6': 'fa28954478e6af39', 'paper-cgl-2024-t2': '285d246e5d7d0fbe',
  'sub-quant-full': 'fecdd1a407a88bca', 'sub-reasoning-full': '4519ca930b472d63', 'sub-english-full': '7f140ada8a23ef09',
  'sub-ga-full': '8d5236559f1893d8', 'sub-computer-full': '30262af212fb05c2', 'drill-quant-geom': '10df8cda6c999b9d',
  'drill-quant-algebra': '449782410e130b52', 'drill-ga-polity': 'aef0dddad7ef3422', 'drill-reas-syllogism': '5b4349e62ea73cf9',
  'drill-eng-grammar': '25d60b2da3516693',
};
const digest = (p: MockPaper) => createHash('sha256')
  .update(JSON.stringify({ q: p.questions, n: p.totalQuestions, m: p.totalMarks, d: p.durationMinutes })).digest('hex').slice(0, 16);
check('frozen: every paper is covered', ALL.every(p => p.id in FROZEN) && Object.keys(FROZEN).length === ALL.length);
for (const p of ALL) check(`${p.id}: questions, numbering and marks unchanged`, digest(p) === FROZEN[p.id], digest(p));
// Marking is now stated on every paper; the full papers state the Tier-I rule they were always scored by.
for (const p of FULL) {
  const m = p.marking;
  check(`${p.id}: states Tier-I marking (+2 / -0.50), 100 questions, 200 marks`, m === SSC_TIER1_MARKING && m.correct === 2 && m.wrong === 0.5
    && p.totalQuestions === 100 && p.questions.length === 100 && p.totalMarks === 200);
  check(`${p.id}: question ids keep their order`, p.questions.every((q, i) => i === 0 || q.id !== p.questions[i - 1].id));
}

// ---------------------------------------------------------------- 3. no paper claims a level its questions do not bear
const mix = (p: MockPaper) => p.questions.reduce<Record<string, number>>((acc, q) => {
  const d = (q as any).difficulty || 'UNSTATED';
  acc[d] = (acc[d] || 0) + 1;
  return acc;
}, {});
const mixes = new Set(FULL.map(p => JSON.stringify(Object.entries(mix(p)).sort())));
check('full papers: one shared difficulty mix', mixes.size === 1, [...mixes].join(' | '));
check('full papers: one shared paper-level label', new Set(FULL.map(p => p.difficulty)).size === 1,
  FULL.map(p => `${p.id}=${p.difficulty}`).join(', '));
for (const p of ALL) {
  check(`${p.id}: title and description make no difficulty claim`, !CLAIM.test(`${p.title} ${p.description}`), p.title);
  if (p.difficulty === 'ADAPTIVE') continue;
  // A stated level must be the level most of its own questions carry.
  const counts = mix(p);
  const top = Math.max(...Object.values(counts));
  check(`${p.id}: "${p.difficulty}" is what most of its questions are`, (counts[p.difficulty] || 0) === top, JSON.stringify(counts));
}
// The same rules, as the data model states them for every paper of every exam.
for (const p of ALL) check(`${p.id}: mockPaperProblems finds nothing`, mockPaperProblems(p).length === 0, mockPaperProblems(p).join('; '));
check('every paper states its own marking, with its clause', ALL.every(p => !!p.marking && !!p.marking.clause));
const ckt = ALL.find(p => p.id === 'sub-computer-full');
check('the Tier-II computer module keeps its own +3 / -1', !!ckt && ckt.marking.correct === 3 && ckt.marking.wrong === 1);

// ---------------------------------------------------------------- 4. what the candidate sees
const text = renderToString(React.createElement(ExamDetailView as any, {
  exam: SSC_CGL_EXAM, initialSection: 9, onOpenProvenanceModal() {}, onOpenReportModal() {}
})).replace(/<[^>]+>/g, ' ').replace(/&amp;/g, '&').replace(/\s+/g, ' ');
// Papers 11 and 12 join the list only when the candidate fetches them (NEW_DISCOVERED_PAPERS), so the
// first render lists papers 1-10; paper 12's own words are checked in the data above.
check('SSC Practice & PYQs: lists paper 9 under its plain title', /Full-length practice paper 9 \(Tier-1 pattern\)/.test(text),
  text.slice(0, 200));
check('SSC Practice & PYQs: no paper is called harder or easier', !/harder mix|easier mix/i.test(text));

console.log(failures === 0 ? 'ALL PRACTICE PAPER CHECKS PASSED' : failures + ' FAILED');
process.exit(failures === 0 ? 0 : 1);
