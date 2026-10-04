// An assistant action opens the exam its answer was about -- never whichever exam is open when it is
// clicked. The audit's bug: an answer given for SSC CGL while UPSC was open ("how do I apply for ssc
// cgl") carried { tab, section } only, and the button opened UPSC's section. Each action's exam is followed
// here through generation -> serialization -> the rendered button -> its click -> the destination the app
// navigates to (assistantDestination, the function main.tsx's navigate() calls), for every register exam
// and an invented future exam.
// Run: npm run check:frontend
import './stub';
import * as React from 'react';
import { renderToString } from 'react-dom/server';
import {
  actionForExam, answerCandidateQuery, AssistantActionButton, assistantDestination, claudeAnswerAction, EXAM_BOUND_TABS
} from '../../src/ui';
import type { AssistantAction, GovOSTab } from '../../src/ui';
import { buildChatContext, conversationService } from '../../src/services';
import { ALL_EXAMS, IBPS_PO_EXAM, SSC_CGL_EXAM, UPSC_CSE_EXAM } from '../../src/data';
import type { Exam } from '../../src/types';
import { FUTURE_ID, futureExam } from './future_exam_fixture';

(globalThis as any).fetch = async () => ({ ok: false, status: 503, json: async () => ({}) });

let failures = 0;
const check = (name: string, ok: boolean, detail = '') => {
  if (!ok) failures++;
  if (!ok || process.env.VERBOSE) console.log((ok ? 'PASS ' : 'FAIL ') + name + (detail ? ' :: ' + detail : ''));
};

const FUTURE = futureExam();
const UNIVERSE: Exam[] = [...ALL_EXAMS, FUTURE];

/** Ask the assistant with `open` as the exam on screen, as AIAssistant does (a fresh thread). */
const ask = (open: Exam, question: string) => {
  conversationService.clear('ASSISTANT');
  return answerCandidateQuery(question, buildChatContext(open, 'ASSISTANT'));
};

/**
 * What a candidate gets by clicking the action: the rendered button (its HTML and its element), its click,
 * and the destination navigate() computes from what the click hands it, with `open` on screen.
 */
const click = (action: AssistantAction, open: Exam, universe = UNIVERSE) => {
  const html = renderToString(React.createElement(AssistantActionButton, { action, onNavigate() {} }));
  let handed: { tab: GovOSTab; section?: number; examId?: string } | null = null;
  const el = (AssistantActionButton as any)({ action, onNavigate: (tab: GovOSTab, section?: number, examId?: string) => { handed = { tab, section, examId }; } });
  el.props.onClick();
  const dest = handed ? assistantDestination(handed, open, universe) : null;
  return { html, renderedExam: (html.match(/data-action-exam="([^"]*)"/) || [])[1], handed: handed as typeof handed, dest };
};

// ---------------------------------------------------------------- 1. every generated action names its exam
const PHRASINGS = ['how do I apply', 'where are the resources', 'what is the last date to apply', 'what is the syllabus',
  'where do I check my eligibility', 'is there negative marking', 'what is the exam pattern', 'where is the admit card',
  'what are the cutoffs', 'where are the faqs', 'compare exams', 'where is the trust panel', 'what can you do'];
for (const exam of UNIVERSE) {
  let bound = 0, unbound = 0;
  for (const q of PHRASINGS) {
    const reply = ask(exam, q);
    if (!reply.action) continue;
    const answeredFor = reply.switchedExamId || exam.id;
    if (EXAM_BOUND_TABS.has(reply.action.tab)) {
      bound++;
      check(`${exam.id}: "${q}" -> its action names the exam it answered for`, reply.action.examId === answeredFor,
        `${JSON.stringify(reply.action)} answered for ${answeredFor}`);
    } else {
      unbound++;
      check(`${exam.id}: "${q}" -> an action into ${reply.action.tab} names no exam`, reply.action.examId === undefined, JSON.stringify(reply.action));
    }
  }
  check(`${exam.id}: phrasings produced exam-bound actions to test`, bound >= 8, `${bound} bound, ${unbound} unbound`);
}

// ---------------------------------------------------------------- 2. the audit's bug, and its reverse
const crossCases: { name: string; open: Exam; question: string; expect: Exam; section: number }[] = [
  { name: 'A: UPSC open, SSC application answer', open: UPSC_CSE_EXAM, question: 'how do I apply for ssc cgl', expect: SSC_CGL_EXAM, section: 4 },
  { name: 'B: SSC open, UPSC application answer', open: SSC_CGL_EXAM, question: 'how do I apply for upsc', expect: UPSC_CSE_EXAM, section: 4 },
  { name: 'SSC open, IBPS syllabus answer', open: SSC_CGL_EXAM, question: 'what is the syllabus for ibps po', expect: IBPS_PO_EXAM, section: 6 },
  { name: 'IBPS open, UPSC dates answer', open: IBPS_PO_EXAM, question: 'what is the last date to apply for upsc', expect: UPSC_CSE_EXAM, section: 2 },
];
for (const c of crossCases) {
  const reply = ask(c.open, c.question);
  check(`${c.name}: the answer is about ${c.expect.id}`, reply.switchedExamId === c.expect.id, String(reply.switchedExamId));
  const action = reply.action!;
  check(`${c.name}: generated action names ${c.expect.id}`, !!action && action.examId === c.expect.id && action.tab === 'EXAM_DETAIL' && action.section === c.section,
    JSON.stringify(action));
  const serialized: AssistantAction = JSON.parse(JSON.stringify(reply)).action;
  check(`${c.name}: the exam survives serialization`, JSON.stringify(serialized) === JSON.stringify(action));
  const r = click(serialized, c.open);
  check(`${c.name}: the rendered button carries the exam`, r.renderedExam === c.expect.id, r.html.slice(0, 160));
  check(`${c.name}: the click hands the navigator the exam`, r.handed?.examId === c.expect.id && r.handed?.tab === 'EXAM_DETAIL' && r.handed?.section === c.section);
  check(`${c.name}: destination is ${c.expect.id}, EXAM_DETAIL, section ${c.section} -- not ${c.open.id}`,
    r.dest?.exam.id === c.expect.id && r.dest?.tab === 'EXAM_DETAIL' && r.dest?.section === c.section, JSON.stringify({ exam: r.dest?.exam.id, tab: r.dest?.tab, section: r.dest?.section }));
}

// ---------------------------------------------------------------- 3. Test C: several actions, clicked in turn
{
  const actions = [
    { open: UPSC_CSE_EXAM, q: 'how do I apply for ssc cgl', expect: SSC_CGL_EXAM.id },
    { open: SSC_CGL_EXAM, q: 'what is the syllabus for upsc', expect: UPSC_CSE_EXAM.id },
    { open: UPSC_CSE_EXAM, q: 'ibps po exam pattern', expect: IBPS_PO_EXAM.id },
    { open: IBPS_PO_EXAM, q: 'where are the resources', expect: IBPS_PO_EXAM.id },
    { open: FUTURE, q: 'what is the last date to apply', expect: FUTURE_ID },
  ].map(a => ({ ...a, action: ask(a.open, a.q).action! }));
  // Click them one after another, each time with the exam the previous click opened on screen.
  let onScreen: Exam = SSC_CGL_EXAM;
  const landed: string[] = [];
  for (const a of actions) {
    const d = click(a.action, onScreen).dest;
    landed.push(d ? d.exam.id : 'nowhere');
    if (d) onScreen = d.exam;
  }
  check('C: each of several actions opens its own exam, whatever was opened before', landed.join() === actions.map(a => a.expect).join(), landed.join());
}

// ---------------------------------------------------------------- 4. Test D: actions that show no exam keep working
{
  const compare = ask(UPSC_CSE_EXAM, 'compare exams').action!;
  const d = click(compare, UPSC_CSE_EXAM).dest;
  check('D: Compare carries no exam and leaves the open exam as it is', compare.tab === 'COMPARE' && compare.examId === undefined
    && d?.tab === 'COMPARE' && d?.exam.id === UPSC_CSE_EXAM.id, JSON.stringify(compare));
  const legacy: AssistantAction = { label: 'Open Resources', tab: 'EXAM_DETAIL', section: 8 };
  const l = click(legacy, UPSC_CSE_EXAM).dest;
  check('D: an action with no exam context keeps its old behaviour (the open exam)', l?.exam.id === UPSC_CSE_EXAM.id && l?.section === 8);
  const sameExam = ask(SSC_CGL_EXAM, 'where are the resources').action!;
  check('D: an action for the open exam stays on it', click(sameExam, SSC_CGL_EXAM).dest?.exam === SSC_CGL_EXAM);
}

// ---------------------------------------------------------------- 5. the Claude path, and an exam GovOS does not hold
{
  const a = claudeAnswerAction('APPLICATION', SSC_CGL_EXAM.id)!;
  const d = click(a, UPSC_CSE_EXAM).dest;
  check('Claude answer for SSC, UPSC open: its button opens SSC section 4', a.examId === SSC_CGL_EXAM.id && d?.exam.id === SSC_CGL_EXAM.id && d?.section === 4);
  check('Claude answer naming no section has no button', claudeAnswerAction('NONE', SSC_CGL_EXAM.id) === undefined);
  const fut = click(ask(FUTURE, 'how do I apply').action!, SSC_CGL_EXAM);
  check('future exam: its action opens it from another exam', fut.dest?.exam.id === FUTURE_ID, String(fut.dest?.exam.id));
  const unknown = click(ask(FUTURE, 'how do I apply').action!, SSC_CGL_EXAM, ALL_EXAMS).dest;
  check('an action for an exam not in the register goes nowhere -- never to the open exam', unknown === null);
  check('actionForExam leaves an action into a view with no exam alone', actionForExam({ label: 'x', tab: 'ADMIN' }, SSC_CGL_EXAM.id)?.examId === undefined);
}

// ---------------------------------------------------------------- 6. generic: no exam is named in the rule
for (const fn of [actionForExam, assistantDestination, claudeAnswerAction, AssistantActionButton]) {
  const src = String(fn);
  const named = UNIVERSE.flatMap(e => [e.id, e.code, e.authorityName]).filter(w => w && src.includes(w));
  check(`${(fn as any).name || 'fn'} names no exam, code or authority`, named.length === 0 && !/['"]exam-/.test(src), named.join());
}

console.log(failures ? `FAIL assistant action exam: ${failures} failing` : 'PASS assistant action exam: every action opens the exam its answer was about');
process.exitCode = failures ? 1 : 0;
