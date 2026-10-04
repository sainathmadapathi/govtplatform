// Exam-scoped state stays with its exam. Switching exam with the page open (a notification, the registry
// restoring the saved exam) kept the same component instances, so exam A's open section, Application tab,
// planner track and goals, library filters and visible chat stayed on screen for exam B; the Exam-Day
// checklist wrote A's ticks under B's key; and a scorecard read started on A was applied to B when it came
// back. What can be checked without a browser is checked here: the storage keys, the stale-result guard,
// each section rendered for B with A's state stored, and the chats' history scoping. The transitions
// themselves (A -> B -> A on one mounted page) are exercised in the real browser; see the report.
// Run: npm run check:frontend
import './stub';
import * as React from 'react';
import { renderToString } from 'react-dom/server';
import { ApplicationGuide, ExamDetailView, examChecklistKey, isCurrentScorecardRequest, readExamChecklist, ResourceLibrary } from '../../src/ui';
import { buildChatContext, conversationService, storageService } from '../../src/services';
import * as ui from '../../src/ui';
import { ALL_EXAMS, SSC_CGL_EXAM, UPSC_CSE_EXAM } from '../../src/data';
import type { Exam, ExamDayChecklistItem } from '../../src/types';
import { futureExam } from './future_exam_fixture';

(globalThis as any).fetch = async () => ({ ok: false, status: 503, json: async () => ({}) });

let failures = 0;
const check = (name: string, ok: boolean, detail = '') => {
  if (!ok) failures++;
  if (!ok || process.env.VERBOSE) console.log((ok ? 'PASS ' : 'FAIL ') + name + (detail ? ' :: ' + detail : ''));
};

// Two exams that carry Exam-Day checklists, from the synthetic future exam (no register exam authors one).
const prov = futureExam().stages[0].provenance;
const items = (prefix: string): ExamDayChecklistItem[] => [1, 2, 3].map(n => ({
  id: `${prefix}-item-${n}`, category: 'DOCUMENTS', title: `${prefix} instruction ${n}`, description: `Instruction ${n} as printed.`, isMandatory: true, provenance: prov,
}));
const EXAM_A: Exam = { ...futureExam(), examDayChecklist: items('a') };
const EXAM_B: Exam = { ...futureExam(), id: 'exam-zssc-second-2031', title: 'ZSSC Second Examination 2031', examDayChecklist: items('b') };

const page = (exam: Exam, section: number) =>
  renderToString(React.createElement(ExamDetailView as any, { exam, initialSection: section, onOpenProvenanceModal() {}, onOpenReportModal() {} }));
/** The checklist's own count line: "N of M confirmed". */
const ticked = (html: string) => Number((html.replace(/<!--.*?-->/g, '').replace(/<[^>]+>/g, ' ').match(/(\d+) of \d+ confirmed/) || [])[1] ?? -1);

// ---------------------------------------------------------------- C. Exam-Day checklist
localStorage.clear();
check('C: each exam has its own checklist key', examChecklistKey(EXAM_A.id) !== examChecklistKey(EXAM_B.id) && examChecklistKey(EXAM_A.id).endsWith(EXAM_A.id));
localStorage.setItem(examChecklistKey(EXAM_A.id), JSON.stringify({ 'a-item-1': true }));
check('C: A\'s tick is read only from A\'s key', readExamChecklist(examChecklistKey(EXAM_A.id))['a-item-1'] === true
  && Object.keys(readExamChecklist(examChecklistKey(EXAM_B.id))).length === 0);
const aPage = page(EXAM_A, 15), bPage = page(EXAM_B, 15);
check('C: A\'s page shows its one tick', ticked(aPage) === 1, String(ticked(aPage)));
check('C: B\'s page shows none of A\'s ticks', ticked(bPage) === 0 && !/a instruction/.test(bPage) && /b instruction 1/.test(bPage), String(ticked(bPage)));
check('C: rendering B wrote nothing to B\'s key and left A\'s alone',
  localStorage.getItem(examChecklistKey(EXAM_B.id)) === null && JSON.parse(localStorage.getItem(examChecklistKey(EXAM_A.id))!)['a-item-1'] === true);

// ---------------------------------------------------------------- E. stale scorecard results
check('E: the latest read for the exam on screen is applied', isCurrentScorecardRequest(1, 1, 'A', 'A'));
check('E: a read started on A is not applied to B', !isCurrentScorecardRequest(1, 1, 'A', 'B'));
check('E: A -> B -> A: the switch invalidated the read, so it cannot overwrite A\'s newer state', !isCurrentScorecardRequest(1, 2, 'A', 'A'));
check('E: an older upload on the same exam yields to the newer one', !isCurrentScorecardRequest(1, 2, 'A', 'A') && isCurrentScorecardRequest(2, 2, 'A', 'A'));
check('E: result entries are stored per exam', (() => {
  storageService.setResultEntry({ examId: SSC_CGL_EXAM.id, examType: 'GENERIC', marks: 140, category: 'UR', source: 'TYPED' } as any, SSC_CGL_EXAM.id);
  return storageService.getResultEntry(SSC_CGL_EXAM.id)?.marks === 140 && storageService.getResultEntry(UPSC_CSE_EXAM.id) === null;
})());

// ---------------------------------------------------------------- D. planner and library
localStorage.clear();
const sscGoal = Object.keys({ x: 1 }).map(() => 'goal-a-1')[0];
storageService.toggleRoadmapGoal(EXAM_A.id, sscGoal);
check('D: roadmap goals are stored per exam', storageService.getRoadmapGoals(EXAM_A.id)[sscGoal] === true && !storageService.getRoadmapGoals(EXAM_B.id)[sscGoal]);
storageService.toggleCompletedTopic(SSC_CGL_EXAM.id, 'syl-quant-arithmetic');
check('D: syllabus ticks are stored per exam', storageService.getCompletedTopics(SSC_CGL_EXAM.id)['syl-quant-arithmetic'] !== undefined
  && Object.keys(storageService.getCompletedTopics(UPSC_CSE_EXAM.id)).length === 0);
{
  // Bookmarks are one list of resource ids; each library counts only its own resources among them.
  storageService.toggleResourceBookmark(SSC_CGL_EXAM.resources[0].id);
  const html = renderToString(React.createElement(ResourceLibrary as any, { exam: UPSC_CSE_EXAM, onOpenResource() {}, onOpenProvenanceModal() {} }));
  const saved = (html.replace(/<[^>]+>/g, ' ').match(/Saved\s*\((\d+)\)/) || [])[1];
  check('D: an SSC bookmark is not counted in UPSC\'s library', saved === undefined || saved === '0', String(saved));
}

// ---------------------------------------------------------------- B. Application guide
// No Application tab is persisted anywhere: each exam opens on its own default, and the component resets to
// it on a switch. The transition (Documents on A, then B) is exercised in the browser.
check('B: the Application guide stores nothing of its own', !/localStorage|storageService/.test(String(ApplicationGuide)));

// ---------------------------------------------------------------- H. chats
localStorage.clear();
conversationService.append('RESOURCES', { role: 'user', text: 'constitution pdf', examId: SSC_CGL_EXAM.id });
conversationService.append('RESOURCES', { role: 'assistant', text: 'Here is the Constitution.', subject: 'Polity', examId: SSC_CGL_EXAM.id });
conversationService.append('PRACTICE', { role: 'assistant', text: '12 calculus questions', topics: ['calculus'], examId: SSC_CGL_EXAM.id });
check('H: UPSC\'s resources chat does not see SSC\'s thread', buildChatContext(UPSC_CSE_EXAM, 'RESOURCES').history.length === 0
  && buildChatContext(SSC_CGL_EXAM, 'RESOURCES').history.length === 2);
check('H: the practice chat\'s "make it harder" cannot reach another exam\'s topics', buildChatContext(futureExam(), 'PRACTICE').history.length === 0
  && buildChatContext(SSC_CGL_EXAM, 'PRACTICE').history.length === 1);
conversationService.append('ASSISTANT', { role: 'assistant', text: 'UPSC answer', examId: UPSC_CSE_EXAM.id });
check('H: Ask AI keeps its whole thread (a switch inside it is deliberate; the thread is cleared on an exam change)',
  buildChatContext(SSC_CGL_EXAM, 'ASSISTANT').history.length === 1);
{
  const greet = (exam: Exam) => renderToString(React.createElement((ui as any).AIAssistant, { exam, onOpenProvenanceModal() {} })).replace(/<[^>]+>/g, ' ');
  check('H: Ask AI greets with the exam in hand, not SSC CGL', /register for UPSC Civil Services Examination \(CSE\) 2026/.test(greet(UPSC_CSE_EXAM))
    && !/register for SSC CGL 2026/.test(greet(UPSC_CSE_EXAM)) && /register for ZSSC Combined Officers Examination 2031/.test(greet(futureExam())));
}

// ---------------------------------------------------------------- A. the page for each exam starts on its own state
localStorage.clear();
{
  const activeOf = (html: string) => (html.match(/class="side-link active"[^>]*>[\s\S]*?<\/button>/) || [''])[0].replace(/<[^>]+>/g, ' ').replace(/\s+/g, ' ').trim();
  check('A: the exam page opens on the section asked for', /Application/.test(activeOf(page(UPSC_CSE_EXAM, 4))) && /Overview/.test(activeOf(page(SSC_CGL_EXAM, 1))),
    `${activeOf(page(UPSC_CSE_EXAM, 4))} / ${activeOf(page(SSC_CGL_EXAM, 1))}`);
}

// ---------------------------------------------------------------- generic: no exam named in the guards
{
  // Code only: a comment may quote a candidate's words ("and for upsc?").
  const src = [isCurrentScorecardRequest, examChecklistKey, readExamChecklist, buildChatContext].map(String).join('\n')
    .replace(/\/\*[\s\S]*?\*\//g, '').replace(/\/\/[^\n]*/g, '');
  const named = [...ALL_EXAMS, futureExam()].map(e => e.id).filter(id => src.includes(id));
  check('the isolation guards name no exam', named.length === 0 && !/ssc|upsc|ibps|appsc/i.test(src), named.join());
}

console.log(failures ? `FAIL exam isolation: ${failures} failing` : 'PASS exam isolation: exam-scoped state stays with its exam');
process.exitCode = failures ? 1 : 0;
