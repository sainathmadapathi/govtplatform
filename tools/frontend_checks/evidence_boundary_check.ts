// Nothing a candidate reads may be stronger than the evidence GovOS holds for that exam and cycle.
//  * An alert for an exam GovOS does not hold opened the register's first exam (SSC CGL); it opens nothing now.
//  * An empty tracked list came back as ['exam-ssc-cgl-2026'], so every candidate "tracked" SSC CGL.
//  * A verifier's addition on any *.gov.in host was OFFICIAL and OFFICIALLY_VERIFIED, quoting GovOS's own sentence
//    and dated as "published" the day it was added; a syllabus revision with any URL was OFFICIALLY_VERIFIED.
//  * The exam badge said "Officially verified" where no fact was contradicted, even with none verified.
//  * The syllabus watch showed "Reading…" forever when the server was down, and could say "nothing published
//    since" about a board it never read.
//  * Results fell back to a 2025 benchmark cycle an exam with no cut-offs never had.
// Run: npm run check:frontend
import './stub';
import * as React from 'react';
import { readFileSync } from 'node:fs';
import { renderToString } from 'react-dom/server';
import {
  additionToResource, ExamVerifiedBadge, notificationDestination, syllabusWatchMessage, syllabusWatchState
} from '../../src/ui';
import { applySyllabusRevisions, storageService } from '../../src/services';
import { ALL_EXAMS, IBPS_PO_EXAM, SSC_CGL_EXAM, UPSC_CSE_EXAM } from '../../src/data';
import type { Exam, ResourceAddition, SyllabusRevision, SyllabusWatch } from '../../src/types';
import { futureExam, FUTURE_ID } from './future_exam_fixture';

(globalThis as any).fetch = async () => ({ ok: false, status: 503, json: async () => ({}) });

let failures = 0;
const check = (name: string, ok: boolean, detail = '') => {
  if (!ok) failures++;
  if (!ok || process.env.VERBOSE) console.log((ok ? 'PASS ' : 'FAIL ') + name + (detail ? ' :: ' + detail : ''));
};
const flat = (html: string) => html.replace(/<!--.*?-->/g, '').replace(/<[^>]+>/g, ' ').replace(/&amp;/g, '&')
  .replace(/&#x27;/g, "'").replace(/&quot;/g, '"').replace(/\s+/g, ' ');

const future = futureExam();
const APPSC = ALL_EXAMS.find(e => e.id.includes('appsc'))!;
const universe: Exam[] = [...ALL_EXAMS, future];

// ======================================================================= 1. notifications open their own exam
for (const exam of [SSC_CGL_EXAM, UPSC_CSE_EXAM, IBPS_PO_EXAM, APPSC, future]) {
  const d = notificationDestination({ examId: exam.id, actionType: 'ADMIT_CARD' }, universe);
  check(`notification: ${exam.id} opens ${exam.id} at Admit Card`, d?.exam.id === exam.id && d.section === 14, JSON.stringify(d && { id: d.exam.id, s: d.section }));
}
const deep = notificationDestination({ examId: UPSC_CSE_EXAM.id, actionType: 'EXAM_DETAIL', actionPayload: { section: 16 } }, universe);
check('notification: an explicit section is kept', deep?.exam.id === UPSC_CSE_EXAM.id && deep.section === 16);
check('notification: an exam GovOS does not hold opens nothing (not SSC CGL)', notificationDestination({ examId: 'exam-removed-2029', actionType: 'RESULT' }, universe) === null);
check('notification: an alert naming no exam opens nothing', notificationDestination({ examId: '', actionType: 'RESULT' }, universe) === null);
check('notification: the future exam is unknown until it is in the universe', notificationDestination({ examId: FUTURE_ID, actionType: 'RESULT' }, ALL_EXAMS) === null);
const mainSrc = readFileSync('src/main.tsx', 'utf8');
check('main.tsx: no alert or exam lookup falls back to the first exam', !/\|\|\s*ALL_EXAMS\[0\]/.test(mainSrc));
check('main.tsx: the unresolved alert is said, not swallowed', /data-exam-notice="unresolved"/.test(mainSrc) && /notificationDestination\(notif, examUniverse\)/.test(mainSrc));
// Text from the server (resource titles, feeds, verifier additions, Claude) reaches the chats; it must render as
// React text. The navigator's bubble once used dangerouslySetInnerHTML, so a fetched page's title ran as script.
for (const file of ['src/ui.tsx', 'src/main.tsx']) {
  const src = readFileSync(file, 'utf8');
  check(`${file}: no raw HTML rendering (dangerouslySetInnerHTML / innerHTML)`, !/dangerouslySetInnerHTML|\.innerHTML\s*=|insertAdjacentHTML|outerHTML\s*=/.test(src));
}

// ======================================================================= 2. an empty tracked list stays empty
localStorage.removeItem('govos_tracked_exams');
check('tracked: nothing stored -> nothing tracked (not SSC CGL)', JSON.stringify(storageService.getTrackedExams()) === '[]', JSON.stringify(storageService.getTrackedExams()));
localStorage.setItem('govos_tracked_exams', '[]');
check('tracked: an emptied list stays empty', storageService.getTrackedExams().length === 0);
localStorage.setItem('govos_tracked_exams', JSON.stringify([UPSC_CSE_EXAM.id]));
check('tracked: a stored list is returned as stored', JSON.stringify(storageService.getTrackedExams()) === JSON.stringify([UPSC_CSE_EXAM.id]));
localStorage.setItem('govos_tracked_exams', '{not json');
const warn = console.warn; console.warn = () => {};
check('tracked: an unreadable list is nothing tracked, not SSC CGL', storageService.getTrackedExams().length === 0);
console.warn = warn;
localStorage.removeItem('govos_tracked_exams');

// ======================================================================= 2b. an alert says only what is true now
const realNow = Date.now;
const alertsAt = (iso: string, exam: Exam) => {
  Date.now = () => Date.parse(iso);
  localStorage.removeItem('govos_candidate_notifications');
  localStorage.setItem('govos_tracked_exams', JSON.stringify([exam.id]));
  try { return storageService.generatePersonalizedNotificationsForTrackedExams([exam]); } finally { Date.now = realNow; }
};
const close = (exam: Exam) => exam.dates.find(d => d.type === 'APPLICATION_CLOSE' && d.status !== 'SUPERSEDED' && !d.displayWhen)!;
const upscClose = Date.parse(close(UPSC_CSE_EXAM).dateTimeStr.replace(' ', 'T'));
const iso = (ms: number) => new Date(ms).toISOString();
const ids = (list: { id: string }[]) => list.map(n => n.id.replace(/^notif-[^-]+(?:-[^-]+)*?-(?=deadline|app-open|exam|result|anskey|admit|correction)/, ''));
const after = alertsAt('2026-10-04T10:00:00Z', UPSC_CSE_EXAM);
check('alerts: a window that closed in February raises no countdown in October', !after.some(n => /deadline/.test(n.id)), ids(after).join());
check('alerts: nothing claims "24 Hours Left" after the close', !after.some(n => /24 Hours Left/.test(n.title)));
const dayBefore = alertsAt(iso(upscClose - 12 * 36e5), UPSC_CSE_EXAM);
check('alerts: 12 hours before the close, the 1-day reminder is due', dayBefore.some(n => n.id.endsWith('deadline-1d')), ids(dayBefore).join());
check('alerts: ...and the 7-day one is no longer shown', !dayBefore.some(n => n.id.endsWith('deadline-7d')));
const weekBefore = alertsAt(iso(upscClose - 6 * 864e5), UPSC_CSE_EXAM);
check('alerts: 6 days before, only the 7-day reminder', weekBefore.filter(n => /deadline/.test(n.id)).map(n => n.id.split('-').pop()).join() === '7d',
  ids(weekBefore).join());
const longBefore = alertsAt('2025-06-01T00:00:00Z', UPSC_CSE_EXAM);
check('alerts: before anything is due, no deadline, release or result alert', !longBefore.some(n => /deadline|result|anskey|admit|app-open/.test(n.id)), ids(longBefore).join());
const closeAlert = alertsAt(iso(upscClose - 12 * 36e5), UPSC_CSE_EXAM).find(n => n.id.endsWith('deadline-1d'))!;
check('alerts: "sent" is written in the record\'s own wall-clock', closeAlert.createdAt === (() => {
  const t = new Date(upscClose - 864e5); const p2 = (x: number) => String(x).padStart(2, '0');
  return `${t.getFullYear()}-${p2(t.getMonth() + 1)}-${p2(t.getDate())} ${p2(t.getHours())}:${p2(t.getMinutes())}:${p2(t.getSeconds())}`;
})() && closeAlert.createdAt.slice(11, 16) === close(UPSC_CSE_EXAM).dateTimeStr.slice(11, 16), closeAlert.createdAt);
check('alerts: no two alerts share an id', [after, dayBefore, weekBefore, longBefore].every(l => new Set(l.map(n => n.id)).size === l.length));
check('alerts: no alert is "sent" in the future', [after, dayBefore, weekBefore].every(list => list.every(n => Date.parse(n.createdAt.replace(' ', 'T')) <= Date.parse('2026-10-04T10:00:00Z'))));
const futureAlerts = alertsAt('2026-10-04T10:00:00Z', future);
check('alerts: the future exam raises no "released" or "declared" alert years ahead', !futureAlerts.some(n => /result|anskey|admit|deadline/.test(n.id)), ids(futureAlerts).join());
for (const exam of [UPSC_CSE_EXAM, IBPS_PO_EXAM, APPSC, future]) {
  const all = [...alertsAt('2026-10-04T10:00:00Z', exam), ...exam.dates.flatMap(d => alertsAt(iso(Date.parse(d.dateTimeStr.replace(' ', 'T')) + 36e5), exam))];
  const words = all.map(n => `${n.title} ${n.message}`).join(' ');
  check(`alerts: ${exam.id} carries no SSC wording (Tier 1 city slip, CBT, cut-off marks)`,
    !/City Intimation|Computer Based Test|cut-off marks|SSC/.test(words), words.slice(0, 200));
}
localStorage.removeItem('govos_candidate_notifications');
localStorage.removeItem('govos_tracked_exams');

// ======================================================================= 3. verifier additions: ownership, not a domain
const addition = (over: Partial<ResourceAddition>): ResourceAddition => ({
  id: 'add-1', title: 'A page', url: 'https://upsc.gov.in/x', subject: 'General Studies', resourceFormat: 'EXTERNAL_PAGE',
  author: 'UPSC', description: 'd', addedAt: '2026-10-04T10:00:00Z', addedFrom: 'trust-panel', examId: UPSC_CSE_EXAM.id, ...over
});
const own = additionToResource(addition({ sourceKind: 'OFFICIAL' }));
check('addition: the authority\'s own link is never "officially verified" by being added', own.provenance.verificationLevel === 'UNDER_VERIFICATION');
check('addition: no quotation is invented for it', !own.provenance.excerptText);
check('addition: the day it was added is not a publication date', own.provenance.publishedDate === '');
const gov = additionToResource(addition({ url: 'https://pib.gov.in/x', sourceKind: 'GOVERNMENT_SITE' }));
check('addition: another government site is not this authority\'s source', gov.type === 'THIRD_PARTY' && /NOT THIS AUTHORITY'S OWN/.test(gov.officialTag || ''), gov.officialTag);
check('addition: ...and is not verified', gov.provenance.verificationLevel !== 'OFFICIALLY_VERIFIED');
const unknownKind = additionToResource(addition({ sourceKind: undefined }));
check('addition: a kind the server did not state is third-party', unknownKind.type === 'THIRD_PARTY');
const third = additionToResource(addition({ url: 'https://coaching.example.com/x', sourceKind: 'THIRD_PARTY' }));
check('addition: a third party says so', third.type === 'THIRD_PARTY' && /NOT OFFICIAL/.test(third.officialTag || ''));

// ======================================================================= 4. syllabus revisions are a verifier's act
const topic = UPSC_CSE_EXAM.syllabus[0];
const revision = (over: Partial<SyllabusRevision>): SyllabusRevision => ({
  id: 'rev-1', examId: UPSC_CSE_EXAM.id, kind: 'AMEND', topicId: topic.id, topic: { name: 'Renamed topic' },
  note: 'Read from the corrigendum', noticeTitle: 'Corrigendum', noticeUrl: 'https://upsc.gov.in/corrigendum.pdf',
  noticeDate: '2026-10-01', appliedAt: '2026-10-04T10:00:00Z', appliedBy: 'verifier', ...over
});
const revised = (r: SyllabusRevision) => applySyllabusRevisions(UPSC_CSE_EXAM, [r]).syllabus.find(t => t.id === topic.id)!;
const withUrl = revised(revision({}));
check('revision: a notice URL alone does not make it officially verified', withUrl.officialProvenance.verificationLevel === 'UNDER_VERIFICATION',
  withUrl.officialProvenance.verificationLevel);
check('revision: the verifier\'s note is not presented as the notice\'s words', withUrl.officialProvenance.excerptText !== 'Read from the corrigendum');
check('revision: its date is the notice\'s', withUrl.officialProvenance.publishedDate === '2026-10-01');
const noteOnly = revised(revision({ noticeUrl: null, noticeTitle: null, noticeDate: null }));
check('revision: a note alone cites no document and borrows no homepage', noteOnly.officialProvenance.officialUrl === ''
  && /no notice cited/i.test(noteOnly.officialProvenance.documentTitle), noteOnly.officialProvenance.officialUrl);
check('revision: a note alone has no publication date', noteOnly.officialProvenance.publishedDate === '');

// ======================================================================= 5. the exam badge counts what is verified
const badge = (exam: Pick<Exam, 'dates' | 'posts'>) => renderToString(React.createElement(ExamVerifiedBadge, { exam }));
for (const exam of [SSC_CGL_EXAM, UPSC_CSE_EXAM, IBPS_PO_EXAM, APPSC, future]) {
  const html = badge(exam);
  const full = /OFFICIALLY VERIFIED/.test(flat(html)) && !/data-verified-facts|data-unsupported-claims/.test(html);
  const partial = html.match(/data-verified-facts="(\d+)\/(\d+)"/);
  check(`badge: ${exam.id} claims only what its facts carry`, full ? !partial : true, flat(html).trim());
  if (partial) check(`badge: ${exam.id} counts ${partial[1]} of ${partial[2]}, never all`, Number(partial[1]) < Number(partial[2]));
}
const prov = SSC_CGL_EXAM.dates[0].provenance;
const unsourcedDates: Pick<Exam, 'dates' | 'posts'> = {
  posts: [],
  dates: [{ ...SSC_CGL_EXAM.dates[0], provenance: { ...prov, verificationLevel: 'UNDER_VERIFICATION' } }]
};
check('badge: a date under verification is not "officially verified"', !/>\s*OFFICIALLY VERIFIED/.test(badge(unsourcedDates)) && /0\/1/.test(badge(unsourcedDates)), flat(badge(unsourcedDates)));
check('badge: an exam with no dates or posts gets no badge (0 of 0 is not verified)', badge({ dates: [], posts: [] }) === '');

// ======================================================================= 6. a failed read is not silence
const board = (over: Partial<SyllabusWatch>): SyllabusWatch => ({ items: [], fetchedAt: '2026-10-04T09:00:00Z', stale: false, error: null, source: 'https://ssc.gov.in', ...over });
check('watch: still reading', syllabusWatchState(undefined) === 'LOADING');
check('watch: server unreachable is not "reading" and not "nothing published"', syllabusWatchState(null) === 'UNREACHABLE'
  && /could not reach/.test(syllabusWatchMessage(null)) && !/nothing published/i.test(syllabusWatchMessage(null)));
check('watch: a board never read cannot say nothing was published', syllabusWatchState(board({ fetchedAt: null, error: 'timed out' })) === 'NOT_READ'
  && /cannot say/.test(syllabusWatchMessage(board({ fetchedAt: null, error: 'timed out' }))));
check('watch: a board read with nothing new', syllabusWatchState(board({})) === 'NOTHING_NEW');
check('watch: no board wired is said', syllabusWatchState(board({ source: null, note: 'No board.' })) === 'NO_BOARD');
check('watch: notices found', syllabusWatchState(board({ items: [{} as any] })) === 'NOTICES');

// ======================================================================= 7. no default exam, year or category in generic logic
const uiSrc = readFileSync('src/ui.tsx', 'utf8');
check('ui: no cut-off year is made up (|| 2025)', !/\|\|\s*2025\b/.test(uiSrc));
check('ui: no exam lookup falls back to the first or Nth exam', !/\)\s*\|\|\s*ALL_EXAMS\[\d\]\s*\)/.test(uiSrc) && !/ev\.examId\)\s*\|\|\s*ALL_EXAMS/.test(uiSrc));
check('ui: a link check is not called a verification of the content', !/Link verified/.test(uiSrc));
check('ui: the verdict says GovOS holds no cut-off rather than "not published yet"', !/cut-?off[^`'"\n]{0,60}not (?:been )?published yet/i.test(uiSrc));

if (failures) { console.log(`\n${failures} evidence-boundary check(s) failed`); process.exit(1); }
console.log('evidence boundary: all checks passed');
