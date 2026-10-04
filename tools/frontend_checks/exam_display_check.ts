// What a candidate sees is the selected exam's own record: the results engine, the typing, syllabus and
// practice answers, the section banner against the latest walk, and the reads the exam page shares.
// Run: npm run check:frontend
import './stub';
import * as React from 'react';
import { renderToString } from 'react-dom/server';
import { answerCandidateQuery, ExamDetailView, resolveSectionState, SECTION_EVIDENCE_ROLES } from '../../src/ui';
import { buildChatContext, conversationService, sharedRead } from '../../src/services';
import { ALL_EXAMS, APPSC_GROUP1_EXAM, APPSC_GROUP2_EXAM, IBPS_PO_EXAM, SSC_CGL_EXAM, UPSC_CSE_EXAM } from '../../src/data';
import type { DiscoveredSourceItem, DiscoveredSources, Exam } from '../../src/types';

(globalThis as any).fetch = async () => ({ ok: false, status: 503, json: async () => ({}) });

let failures = 0;
const check = (name: string, ok: boolean, detail = '') => {
  if (!ok) failures++;
  if (!ok || process.env.VERBOSE) console.log((ok ? 'PASS ' : 'FAIL ') + name + (detail ? ' :: ' + detail : ''));
};
const ask = (exam: Exam, q: string) => answerCandidateQuery(q, buildChatContext(exam, 'ASSISTANT')).text;
const NOT_SSC = ALL_EXAMS.filter(e => e.id !== SSC_CGL_EXAM.id);
const SSC_WORDS = [/\bTier-?(?:1|2|I|II)\b/i, /\bCKT\b/, /\bDEST\b/, /Data Entry Speed Test/i, /\b298\b/, /Ministry allocation/i, /SSC CHSL/];

// ---------------------------------------------------------------- results engine B
const sectionText = (exam: Exam, section: number) =>
  renderToString(React.createElement(ExamDetailView as any, { exam, initialSection: section, onOpenProvenanceModal() {}, onOpenReportModal() {} }))
    .replace(/<[^>]+>/g, ' ').replace(/&amp;/g, '&').replace(/\s+/g, ' ');
for (const exam of ALL_EXAMS.filter(e => e.id !== UPSC_CSE_EXAM.id)) {
  const row = [...exam.cutoffsHistory].filter(r => r.tier1Cutoff != null).sort((a, b) => b.year - a.year)[0];
  if (!row) continue;
  for (const delta of [5, -5]) {
    const marks = (row.tier1Cutoff as number) + delta;
    localStorage.setItem(`govos_result_entry_${exam.id}`, JSON.stringify({ marks, tier1Marks: marks, category: row.category, source: 'MANUAL', examId: exam.id }));
    const text = sectionText(exam, 16);
    const tag = `${exam.id} results (${delta > 0 ? 'above' : 'below'} the cut-off)`;
    check(`${tag}: a verdict is shown`, /(ABOVE|BELOW) .*CUT-OFF/.test(text), text.slice(0, 200));
    if (exam.id === SSC_CGL_EXAM.id) {
      check(`${tag}: SSC keeps its own CKT/DEST card`, /CKT/.test(text) && /DEST/.test(text));
    } else {
      for (const re of SSC_WORDS) check(`${tag}: no SSC wording ${re}`, !re.test(text), (text.match(new RegExp(`.{0,80}${re.source}.{0,40}`, re.flags)) || [''])[0]);
    }
    check(`${tag}: no allocation claimed that was never entered`, !/None \(No Post Allocated\)/.test(text));
    localStorage.removeItem(`govos_result_entry_${exam.id}`);
  }
}

// ---------------------------------------------------------------- assistant answers
for (const exam of ALL_EXAMS) {
  const typing = ask(exam, 'where is the typing practice tool');
  check(`${exam.id} typing: no misplaced SSC section`, !/Section III Module 2/.test(typing), typing.slice(0, 160));
  check(`${exam.id} typing: no link promised in words`, !/link below/i.test(typing));
  // What the answer must say is read from the exam's own record, never from a list of exams.
  const typingIn = (t?: string) => /typing|data entry|\bDEST\b|skill test|key depressions/i.test(t || '');
  const recordedSection = exam.stages.some(st => (st.sections || []).some(sec => typingIn(sec.sectionName) || (sec.modules || []).some(typingIn)));
  const recordedMode = exam.stages.find(st => typingIn(st.mode));
  if (recordedSection) {
    check(`${exam.id} typing: names the section its record gives`, /typing test is .*Data Entry Speed Test/.test(typing), typing.slice(0, 220));
  } else if (recordedMode) {
    check(`${exam.id} typing: quotes the stage and mode its record gives`, typing.includes(recordedMode.stageName)
      && typing.includes(`"${recordedMode.mode}"`), typing.slice(0, 260));
    check(`${exam.id} typing: does not say the record has none`, !/has no typing or data-entry test/.test(typing));
    check(`${exam.id} typing: invents no duration, marks or speed`, !/\b\d+\s*(?:minutes?|marks?|wpm|key depressions)\b/i.test(typing.split('typing practice tool')[1] || typing), typing);
  } else {
    check(`${exam.id} typing: says it has no typing test`, /has no typing or data-entry test/.test(typing), typing.slice(0, 220));
  }
  if (exam.id !== SSC_CGL_EXAM.id) {
    for (const re of [/Data Entry Speed Test/i, /\bDEST\b/, /Tier-?(?:2|II)\b/i, /\bCKT\b/, /Section-IV/]) check(`${exam.id} typing: no SSC term ${re}`, !re.test(typing));
  }
  if (exam.id !== IBPS_PO_EXAM.id) {
    for (const re of [/Online CBT \+ Typing Test/i, /\bIBPS\b/]) check(`${exam.id} typing: no IBPS term ${re}`, !re.test(typing));
  }
  const where = ask(exam, 'where is the syllabus');
  check(`${exam.id} syllabus: no SSC section name`, !/Study Plan & Syllabus/.test(where), where.slice(0, 160));
  const weighted = exam.syllabus.some(t => t.weightagePercentage > 0);
  check(`${exam.id} syllabus: weight only where recorded`, /weight/i.test(where) === weighted, where.slice(0, 200));
}
const empty: Exam = { ...IBPS_PO_EXAM, id: 'exam-unknown-board-2031', title: 'Unknown Board Examination 2031', syllabus: [], answerKeys: [], officialPapers: [] };
check('empty syllabus: says none is on record', /no syllabus topics on record/.test(ask(empty, 'where is the syllabus')));
check('empty syllabus: no "0 topics:"', !/0 topics:/.test(ask(empty, 'what is the syllabus')));

const sscPractice = ask(SSC_CGL_EXAM, 'is there any practice for this exam');
check('SSC practice: answer-key notices are not counted as answer keys', !/\b\d+ answer keys\b/.test(sscPractice), sscPractice.slice(0, 300));
check('SSC practice: says the notices are of earlier cycles and login-served',
  /answer-key notices from the 2024 and 2025 cycles/.test(sscPractice) && /login/.test(sscPractice), sscPractice);
const upscPractice = ask(UPSC_CSE_EXAM, 'is there any practice for this exam');
check('UPSC practice: OCR-read items are said to be under verification', /still being checked against the original paper/.test(upscPractice), upscPractice);
for (const exam of NOT_SSC) {
  const t = ask(exam, 'is there any practice for this exam');
  check(`${exam.id} practice: no "another exam's papers"`, !/another exam's papers/.test(t), t.slice(0, 200));
}

// ---------------------------------------------------------------- typing answer across an exam switch
// AIAssistant clears its thread when exam.id changes (conversationService.clear); the next exam's
// answer must then be that exam's alone.
conversationService.clear('ASSISTANT');
const sscTyping = ask(SSC_CGL_EXAM, 'where is the typing practice tool');
conversationService.append('ASSISTANT', { role: 'user', text: 'where is the typing practice tool', examId: SSC_CGL_EXAM.id });
conversationService.append('ASSISTANT', { role: 'assistant', text: sscTyping, examId: SSC_CGL_EXAM.id });
for (const next of [IBPS_PO_EXAM, APPSC_GROUP1_EXAM, APPSC_GROUP2_EXAM, UPSC_CSE_EXAM]) {
  conversationService.clear('ASSISTANT');                         // what the component does on the switch
  const t = ask(next, 'and the typing test?');
  check(`switch SSC -> ${next.id}: no SSC typing answer carried over`, !/Data Entry Speed Test|\bDEST\b|Section-IV/.test(t), t.slice(0, 200));
  check(`switch SSC -> ${next.id}: answers for ${next.id}`, t.includes(next.title) || t.includes(next.authorityName), t.slice(0, 200));
}
conversationService.clear('ASSISTANT');

// ---------------------------------------------------------------- section banner vs the latest walk
// A section says "Found" only on an item of its own evidence role, the authority's own, tied to this
// exam in this cycle and openable; anything else the walk did not rule out is "Search incomplete".
const NF = 'SOURCE_NOT_FOUND_AFTER_SEARCH';
const machine = (id: string, states: Record<string, [number, string]>): Exam => ({
  ...IBPS_PO_EXAM, id, origin: 'MACHINE_ACQUIRED',
  sectionStates: Object.fromEntries(Object.entries(states).map(([k, [num, state]]) =>
    [k, { state, nature: 'OFFICIAL_FACT', studentStatusSummary: '', sectionNum: num, isApplicable: true }]))
} as Exam);
const X = machine('exam-x-2026', { pyqs: [9, NF], cutoffs: [10, NF], results: [16, NF], 'admit-card': [14, NF], application: [4, NF],
  syllabus: [6, NF], corrigenda: [13, NF], overview: [1, NF], dates: [2, NF], pattern: [5, NF], 'exam-day': [15, NF] });
const item = (over: Partial<DiscoveredSourceItem>): DiscoveredSourceItem => ({
  title: 'Item', url: 'https://psc.example.gov.in/doc.pdf', context: '', role: 'QUESTION_PAPER', section: 'PRACTICE',
  sourceLabel: 'Official source', sourceClass: 'PRIMARY_OFFICIAL', status: 'FETCHED', obtainable: true, foundOn: '',
  foundOnTitle: '', relation: 'THIS_EXAM', identity: {}, duplicateOf: '', ...over
});
const walk = (states: Record<string, string>, items: DiscoveredSourceItem[] = [], portals: DiscoveredSourceItem[] = [], examId = X.id): DiscoveredSources => ({
  examId, state: 'DISCOVERED', portals,
  repositories: items.length ? [{ title: 'Listing', url: 'https://psc.example.gov.in/list', role: items[0].role, section: items[0].section,
    sourceLabel: 'Official source', items, itemCount: items.length, listedWithoutLink: [], itemsForThisExam: items.length, status: 'FETCHED', note: '' }] : [],
  searchStates: Object.fromEntries(Object.entries(states).map(([k, v]) => [k, { state: v, reason: '' }])) as any
});
const at = (num: number, d: DiscoveredSources | null, exam: Exam = X) => resolveSectionState(exam, num, d);

// 1. a section-specific verified finding
check('banner 1: this exam\'s own question paper -> Found', at(9, walk({ QUESTION_PAPER: 'FOUND_VERIFIED' }, [item({})])) === 'FOUND_AFTER_BUILD');
check('banner 1: this exam\'s own cut-off list -> Found', at(10, walk({ CUTOFF: 'FOUND_VERIFIED' }, [item({ role: 'CUTOFF', section: 'CUTOFFS' })])) === 'FOUND_AFTER_BUILD');
check('banner 1: this exam\'s own application portal -> Found', at(4, walk({ APPLICATION_PORTAL: 'FOUND_VERIFIED' }, [],
  [item({ role: 'APPLICATION_PORTAL', section: 'APPLICATION', url: 'https://apply.example.gov.in/x' })])) === 'FOUND_AFTER_BUILD');
// 1b. names this exam but not its cycle, or a role only Claude read: listed, never proof
check('banner 1b: a paper naming this exam but no cycle does not make the section "Found"',
  at(9, walk({ QUESTION_PAPER: 'FOUND_AMBIGUOUS' }, [item({ relation: 'THIS_EXAM_CYCLE_UNSTATED' })])) !== 'FOUND_AFTER_BUILD');
check('banner 1b: a role only Claude proposed does not make the section "Found"',
  at(9, walk({ QUESTION_PAPER: 'FOUND_AMBIGUOUS' }, [item({ roleFrom: 'CLAUDE' })])) !== 'FOUND_AFTER_BUILD');
check('banner 1b: the same item read by GovOS\'s rules still is',
  at(9, walk({ QUESTION_PAPER: 'FOUND_VERIFIED' }, [item({ roleFrom: 'RULES' })])) === 'FOUND_AFTER_BUILD');
// 2. a sibling role only
const keyOnly = walk({ QUESTION_PAPER: 'SEARCH_INCOMPLETE', ANSWER_KEY: 'FOUND_VERIFIED' }, [item({ role: 'ANSWER_KEY' })]);
check('banner 2: an answer key alone does not make Practice & PYQs "Found"', at(9, keyOnly) === 'SEARCH_INCOMPLETE', String(at(9, keyOnly)));
check('banner 2: a notification alone does not make Cutoffs "Found"', at(10, walk({ CUTOFF: 'SEARCH_INCOMPLETE', NOTIFICATION: 'FOUND_VERIFIED' },
  [item({ role: 'NOTIFICATION', section: 'OFFICIAL_LINKS' })])) === 'SEARCH_INCOMPLETE');
check('banner 2: a sibling role found with the section\'s own search complete keeps "Not found"',
  at(9, walk({ QUESTION_PAPER: 'NOT_FOUND_AFTER_DISCOVERY', ANSWER_KEY: 'FOUND_VERIFIED' }, [item({ role: 'ANSWER_KEY' })])) === NF);
// 3. an authority-wide portal only
const otrOnly = walk({ APPLICATION_PORTAL: 'FOUND_VERIFIED', OTR_PORTAL: 'FOUND_VERIFIED' }, [],
  [item({ role: 'OTR_PORTAL', section: 'APPLICATION', relation: 'NOT_THIS_EXAM', url: 'https://otr.example.gov.in' }),
   item({ role: 'APPLICATION_PORTAL', section: 'APPLICATION', relation: 'NOT_THIS_EXAM', url: 'https://apply.example.gov.in' })]);
check('banner 3: an authority-wide portal alone -> Search incomplete', at(4, otrOnly) === 'SEARCH_INCOMPLETE', String(at(4, otrOnly)));
check('banner 3: a portal satisfies no other section', [9, 10, 16, 14, 6, 13].every(n => at(n, otrOnly) === NF));
// 4. an unrelated or unlinked item only
check('banner 4: another exam\'s paper -> Search incomplete', at(9, walk({ QUESTION_PAPER: 'FOUND_VERIFIED' }, [item({ relation: 'OTHER_EXAM' })])) === 'SEARCH_INCOMPLETE');
check('banner 4: another cycle\'s paper -> Search incomplete', at(9, walk({ QUESTION_PAPER: 'FOUND_VERIFIED' }, [item({ relation: 'THIS_EXAM_OTHER_CYCLE' })])) === 'SEARCH_INCOMPLETE');
check('banner 4: a third-party copy -> Search incomplete', at(9, walk({ QUESTION_PAPER: 'FOUND_VERIFIED' }, [item({ sourceClass: 'SECONDARY' })])) === 'SEARCH_INCOMPLETE');
check('banner 4: listed without a working link -> Search incomplete', at(9, walk({ QUESTION_PAPER: 'FOUND_UNREADABLE' }, [item({ obtainable: false })])) === 'SEARCH_INCOMPLETE');
check('banner 4: unlinked, nothing listed -> Search incomplete', at(9, walk({ QUESTION_PAPER: 'FOUND_UNREADABLE' })) === 'SEARCH_INCOMPLETE');
check('banner 4: listed but tied to no exam, shown below -> Not confirmed', at(14, walk({ ADMIT_CARD: 'FOUND_AMBIGUOUS' },
  [item({ role: 'ADMIT_CARD', section: 'ADMIT_CARD', relation: 'UNIDENTIFIABLE' })])) === 'LISTED_NOT_CONFIRMED');
check('banner 4: ambiguous with nothing shown -> Search incomplete', at(14, walk({ ADMIT_CARD: 'FOUND_AMBIGUOUS' })) === 'SEARCH_INCOMPLETE');
// 5. the section's own search incomplete
check('banner 5: search incomplete -> Search incomplete', at(9, walk({ QUESTION_PAPER: 'SEARCH_INCOMPLETE' })) === 'SEARCH_INCOMPLETE');
check('banner 5: never searched -> Search incomplete', at(10, walk({ CUTOFF: 'NOT_SEARCHED' })) === 'SEARCH_INCOMPLETE');
check('banner 5: a complete walk keeps "Not found"', at(9, walk({ QUESTION_PAPER: 'NOT_FOUND_AFTER_DISCOVERY' })) === NF);
check('banner 5: another section\'s incomplete search does not leak in', at(10, walk({ QUESTION_PAPER: 'SEARCH_INCOMPLETE' })) === NF);
// 6 and 7. the build's findings about documents are never rewritten
const incompleteEverywhere = walk(Object.fromEntries(Object.values(SECTION_EVIDENCE_ROLES).flat().map(r => [r, 'SEARCH_INCOMPLETE'])));
for (const [state, label] of [['NOT_YET_PUBLISHED', 'Not published'], ['EXTRACTION_FAILED', 'Not extracted'], ['SOURCE_UNREADABLE', 'Unreadable'],
  ['NEEDS_REVIEW', 'Under review'], ['INFRASTRUCTURE_FAILURE', 'Check incomplete']] as const) {
  const e = machine('exam-x-2026', { pyqs: [9, state] });
  check(`banner 6/7: ${state} stays ${label}, whatever the walk`, at(9, incompleteEverywhere, e) === state
    && at(9, walk({ QUESTION_PAPER: 'FOUND_VERIFIED' }, [item({})]), e) === state);
}
check('banner: no walk keeps the build state', at(9, null) === NF && at(9, { examId: X.id, state: 'NOT_DISCOVERED' }) === NF);
check('banner: a section the exam has no state for has none', at(12, incompleteEverywhere) === null);
// Sections 1, 2, 5 and 15 have no evidence role: a walk can neither prove nor disprove them.
for (const n of [1, 2, 5, 15]) {
  check(`banner: section ${n} keeps its build state`, at(n, incompleteEverywhere) === NF
    && at(n, walk({ NOTIFICATION: 'FOUND_VERIFIED', CALENDAR: 'FOUND_VERIFIED' }, [item({ role: 'NOTIFICATION', section: 'OFFICIAL_LINKS' })])) === NF);
}
// 9. another exam's walk
const otherExams = walk({ QUESTION_PAPER: 'FOUND_VERIFIED' }, [item({})], [], 'exam-other-2026');
check('banner 9: another exam\'s walk is ignored (the frame before a switched exam\'s read lands)', at(9, otherExams) === NF);
check('banner 9: another exam\'s incomplete walk is ignored', at(9, walk({ QUESTION_PAPER: 'SEARCH_INCOMPLETE' }, [], [], 'exam-other-2026')) === NF);

// 8. TGPSC Group-I 02/2024 as the live walk run-21b7287b1eaa (2026-10-02) projected it, and its record's
// section states: only Practice & PYQs and Cutoffs were "not found" at build time.
const TG = 'exam-websitenew-tgpsc-group-i-2024';
const tgpsc = machine(TG, { overview: [1, 'VERIFIED_AVAILABLE'], dates: [2, 'VERIFIED_AVAILABLE'], eligibility: [3, 'VERIFIED_AVAILABLE'],
  application: [4, 'VERIFIED_AVAILABLE'], pattern: [5, 'VERIFIED_AVAILABLE'], syllabus: [6, 'VERIFIED_AVAILABLE'], roadmap: [7, 'SUPPORTED_AND_PROJECTED'],
  resources: [8, 'VERIFIED_AVAILABLE'], pyqs: [9, NF], 'mock-tests': [17, 'NOT_YET_GENERATED'], 'admit-card': [14, 'VERIFIED_AVAILABLE'],
  'exam-day': [15, 'VERIFIED_AVAILABLE'], results: [16, 'VERIFIED_AVAILABLE'], faqs: [11, 'VERIFIED_AVAILABLE'], corrigenda: [13, 'VERIFIED_AVAILABLE'],
  'official-links': [12, 'VERIFIED_AVAILABLE'], cutoffs: [10, NF] });
const tgWalk: DiscoveredSources = {
  ...walk({ ADMIT_CARD: 'NOT_SEARCHED', ANSWER_KEY: 'SEARCH_INCOMPLETE', APPLICATION_PORTAL: 'FOUND_VERIFIED', CORRIGENDUM: 'FOUND_VERIFIED',
    CUTOFF: 'SEARCH_INCOMPLETE', NOTIFICATION: 'FOUND_VERIFIED', OTR_PORTAL: 'FOUND_VERIFIED', QUESTION_PAPER: 'SEARCH_INCOMPLETE',
    RESULT: 'FOUND_AMBIGUOUS', SYLLABUS: 'FOUND_VERIFIED' }, [
    item({ role: 'SYLLABUS', section: 'SYLLABUS', title: 'Group-I Services' }),
    item({ role: 'NOTIFICATION', section: 'OFFICIAL_LINKS', title: '02/2024 - GROUP-I SERVICES' }),
    item({ role: 'NOTIFICATION', section: 'OFFICIAL_LINKS', title: '04/2022 - Group - I Services', relation: 'THIS_EXAM_OTHER_CYCLE' }),
  ], [
    item({ role: 'OTR_PORTAL', section: 'APPLICATION', relation: 'NOT_THIS_EXAM', title: 'One Time Registration', url: 'https://www.tgpsc.gov.in/otr' }),
    item({ role: 'OFFICIAL_PORTAL', section: 'OFFICIAL_LINKS', relation: 'NOT_THIS_EXAM', title: 'Know Your TGPSC ID', url: 'https://www.tgpsc.gov.in/id' }),
  ], TG)
};
const tgStates = Object.fromEntries(Object.values(tgpsc.sectionStates!).map(s => [s.sectionNum, at(s.sectionNum, tgWalk, tgpsc)]));
check('banner 8: TGPSC Practice & PYQs -> Search incomplete', tgStates[9] === 'SEARCH_INCOMPLETE', String(tgStates[9]));
check('banner 8: TGPSC Cutoffs -> Search incomplete', tgStates[10] === 'SEARCH_INCOMPLETE', String(tgStates[10]));
check('banner 8: TGPSC verified sections stay verified (no banner)', [1, 2, 3, 4, 5, 6, 8, 11, 12, 13, 14, 15, 16].every(n => tgStates[n] === 'VERIFIED_AVAILABLE'),
  JSON.stringify(tgStates));
check('banner 8: TGPSC guidance sections unchanged', tgStates[7] === 'SUPPORTED_AND_PROJECTED' && tgStates[17] === 'NOT_YET_GENERATED');
check('banner 8: nothing on TGPSC reads "Found"', !Object.values(tgStates).includes('FOUND_AFTER_BUILD'));
// What the page renders: the banner above section 09 and 10 reads "Search incomplete", never "Not found".
const banner = (exam: Exam, num: number) => sectionText(exam, num).match(/(Search incomplete|Not found|Found on the official site|Not confirmed)\s*\./)?.[1] || '';
check('banner 8: TGPSC section 09 renders a banner (no walk read yet: build state)', banner(tgpsc, 9) === 'Not found', banner(tgpsc, 9));

// ---------------------------------------------------------------- one shared read per exam page
(async () => {
  const reads = sharedRead<number>(60_000);
  let loads = 0;
  const load = (v: number | null) => () => new Promise<number | null>(r => { loads++; setTimeout(() => r(v), 5); });
  const [a, b] = await Promise.all([reads.get('k', load(1)), reads.get('k', load(2))]);
  check('shared read: two panels share one request', loads === 1 && a === 1 && b === 1, `${loads} ${a} ${b}`);
  check('shared read: a kept result is reused', (await reads.get('k', load(3))) === 1 && loads === 1);
  check('shared read: fresh reads again', (await reads.get('k', load(4), true)) === 4 && loads === 2);
  await reads.get('miss', load(null));
  check('shared read: a failed read is not kept', (await reads.get('miss', load(5))) === 5 && loads === 4);
  const short = sharedRead<number>(1);
  await short.get('t', load(6));
  await new Promise(r => setTimeout(r, 10));
  check('shared read: an expired result is read again', (await short.get('t', load(7))) === 7);

  console.log(failures === 0 ? 'ALL EXAM DISPLAY CHECKS PASSED' : failures + ' FAILED');
  process.exit(failures === 0 ? 0 : 1);
})();
