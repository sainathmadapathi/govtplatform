// Every node of a published syllabus tree gets a React key no sibling shares. UPSC CSE's tree was projected
// before the builder made ids unique, and repeats ids among siblings (eighteen `…-section-a` under its Main
// Examination); keyed by id, React warned on every render and could attach one node's open/closed state to
// another. The check records the key each SyllabusNodeCard element is actually created with while the real
// Syllabus section renders, for every register exam and an invented future one, and holds syllabusNodeKeys
// to its rule on edge cases.
// Run: npm run check:frontend
import './stub';
import * as React from 'react';
import { renderToString } from 'react-dom/server';
import { ExamDetailView, PublishedSyllabusPanel, syllabusNodeKeys } from '../../src/ui';
import { ALL_EXAMS, UPSC_CSE_EXAM } from '../../src/data';
import type { Exam, ExamSyllabusNode } from '../../src/types';
import { futureExam } from './future_exam_fixture';

(globalThis as any).fetch = async () => ({ ok: false, status: 503, json: async () => ({}) });

let failures = 0;
const check = (name: string, ok: boolean, detail = '') => {
  if (!ok) failures++;
  if (!ok || process.env.VERBOSE) console.log((ok ? 'PASS ' : 'FAIL ') + name + (detail ? ' :: ' + detail : ''));
};

// ---------------------------------------------------------------- 1. the rule
const n = (id: string): ExamSyllabusNode => ({ id, title: id, levelLabel: 'Topic' } as ExamSyllabusNode);
const keys = (...ids: string[]) => syllabusNodeKeys(ids.map(n));
check('unique ids are their own keys', keys('a', 'b', 'c').join() === 'a,b,c');
check('a repeat is qualified, the first keeps its id', keys('a', 'a', 'b', 'a').join() === 'a,a~2,b,a~3');
check('a repeat never borrows a sibling\'s real id', new Set(keys('a', 'a', 'a~2')).size === 3 && keys('a', 'a', 'a~2')[2] === 'a~2', keys('a', 'a', 'a~2').join());
check('an empty id still gets a unique key', new Set(keys('', '')).size === 2);
check('nothing in, nothing out', syllabusNodeKeys([]).length === 0);

// ---------------------------------------------------------------- 2. what the Syllabus section renders
type Made = { key: string | null | undefined; node: ExamSyllabusNode };
const made: Made[] = [];
// The module object itself: the bundle's import of it reads `jsx` from here on every call.
declare const require: (id: string) => any;
const runtime = require('react/jsx-runtime');
for (const fn of ['jsx', 'jsxs']) {
  const real = runtime[fn];
  runtime[fn] = (type: any, props: any, key?: any) => {
    if (typeof type === 'function' && /^SyllabusNodeCard\d*$/.test(type.name || '')) made.push({ key, node: props.node });
    return real(type, props, key);
  };
}

/** The published tree as section 06's Official Syllabus view mounts it -- the panel itself, because an exam
 *  with post-wise study paths (SSC) opens the section on another view. */
const renderSyllabus = (exam: Exam) => {
  made.length = 0;
  renderToString(React.createElement(PublishedSyllabusPanel, { exam, onOpenProvenanceModal() {} }));
  return [...made];
};
/** Section 06 as a candidate opens it from the exam page (UPSC opens on its Official Syllabus view). */
const renderSection = (exam: Exam) => {
  made.length = 0;
  renderToString(React.createElement(ExamDetailView as any, { exam, initialSection: 6, onOpenProvenanceModal() {}, onOpenReportModal() {} }));
  return [...made];
};

const exams: Exam[] = [...ALL_EXAMS, futureExam()];
for (const exam of exams) {
  const tree = exam.syllabusTree || [];
  // Every node's siblings, by object identity, straight from the record.
  const siblingsOf = new Map<ExamSyllabusNode, ExamSyllabusNode[]>();
  let repeated = 0;
  const walk = (nodes: ExamSyllabusNode[]) => {
    const ids = nodes.map(x => x.id);
    repeated += ids.length - new Set(ids).size;
    nodes.forEach(x => { siblingsOf.set(x, nodes); walk(x.children || []); });
  };
  walk(tree);
  const rendered = renderSyllabus(exam);
  if (tree.length === 0) {
    check(`${exam.id}: no tree, no nodes rendered`, rendered.length === 0);
    continue;
  }
  if (rendered.length === 0) {
    check(`${exam.id}: the published tree renders`, false, 'no SyllabusNodeCard was created');
    continue;
  }
  const groups = new Map<ExamSyllabusNode[], string[]>();
  for (const m of rendered) {
    const group = siblingsOf.get(m.node);
    if (!group) { check(`${exam.id}: every rendered node is a node of this exam's tree`, false, String(m.node?.id)); continue; }
    groups.set(group, [...(groups.get(group) || []), String(m.key)]);
  }
  const clashes = [...groups.values()].filter(ks => new Set(ks).size !== ks.length);
  check(`${exam.id}: ${rendered.length} rendered nodes, no two siblings share a key (record repeats ${repeated} sibling ids)`,
    clashes.length === 0, clashes.slice(0, 2).map(ks => ks.join(',').slice(0, 160)).join(' | '));
  check(`${exam.id}: every key is the node's id, or its id qualified as a repeat`,
    rendered.every(m => m.key === m.node.id || String(m.key).startsWith(`${m.node.id || 'node'}~`)));
  check(`${exam.id}: a node whose id is unique among its siblings keeps it as its key`,
    rendered.every(m => siblingsOf.get(m.node)!.filter(s => s.id === m.node.id).length > 1 || m.key === m.node.id));
}

// The case the warning came from: it must still be in the record, or this check proves nothing.
{
  const viaPage = renderSection(UPSC_CSE_EXAM);
  const viaPanel = renderSyllabus(UPSC_CSE_EXAM);
  check('UPSC: the Syllabus section on the exam page renders the same keyed nodes as the panel',
    viaPage.length > 0 && viaPage.map(m => m.key).join() === viaPanel.map(m => m.key).join(), `${viaPage.length} vs ${viaPanel.length}`);
  const main = (UPSC_CSE_EXAM.syllabusTree || [])[0]?.children?.find(c => /Main Examination/.test(c.title));
  const ids = (main?.children || []).map(c => c.id);
  check('UPSC: the Main Examination still repeats sibling ids in the record (this check covers that case)', ids.length - new Set(ids).size > 0,
    `${ids.length} children, ${new Set(ids).size} distinct`);
}

console.log(failures ? `FAIL syllabus tree keys: ${failures} failing` : 'PASS syllabus tree keys: every rendered node has a key no sibling shares');
process.exitCode = failures ? 1 : 0;
