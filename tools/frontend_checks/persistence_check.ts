// Candidate data and application state are never silently lost, overwritten, downgraded or shown from a
// failed read. Each case is a defect reproduced before it was fixed:
//  * a corrupt or refused localStorage write lost the practice attempt (and the local sync was skipped);
//    a second save of one sitting added a duplicate; the server's rows replaced local ones field-for-field;
//  * the server's tracked-exam list (a new server's seeded SSC CGL, or one that missed an offline toggle)
//    replaced the browser's; server-side default preferences replaced the candidate's own;
//  * regenerated alerts kept "sent" times stamped by an earlier generator outside their own window;
//  * a slower, older registry load overwrote a newer one, and a failed load handed back [];
//  * a new candidate was shown two study modules as completed; a corrupt tick store dropped ticks silently;
//  * two sync clicks sent everything twice; a 413 from the scorecard reader read as "server unreachable".
// Run: npm run check:frontend
import './stub';
import { readFileSync } from 'node:fs';
import {
  applySyllabusRevisions, examRegistryService, readStoredJson, storageService
} from '../../src/services';
import { ALL_EXAMS, SSC_CGL_EXAM, UPSC_CSE_EXAM } from '../../src/data';
import type { CandidateNotification, Exam, MockAttemptRecord } from '../../src/types';

let failures = 0;
const check = (name: string, ok: boolean, detail = '') => {
  if (!ok) failures++;
  if (!ok || process.env.VERBOSE) console.log((ok ? 'PASS ' : 'FAIL ') + name + (detail ? ' :: ' + detail : ''));
};
const ls = (globalThis as any).localStorage;
const realSetItem = ls.setItem;
const refuse = (keyPart: string) => { ls.setItem = (k: string, v: string) => { if (k.includes(keyPart)) throw new Error('QuotaExceededError'); realSetItem(k, v); }; };
const allow = () => { ls.setItem = realSetItem; };
const calls: { url: string; body?: any; method?: string }[] = [];
let respond: (url: string, init?: any) => Promise<any> = async () => { throw new Error('offline'); };
(globalThis as any).fetch = (url: string, init?: any) => {
  calls.push({ url, method: init?.method, body: init?.body ? JSON.parse(init.body) : undefined });
  return respond(url, init);
};
const json = (body: any, status = 200) => Promise.resolve({ ok: status < 400, status, json: async () => body });
const quiet = <T,>(fn: () => T): T => { const w = console.warn; console.warn = () => {}; try { return fn(); } finally { console.warn = w; } };
const quietAsync = async <T,>(fn: () => Promise<T>): Promise<T> => { const w = console.warn; console.warn = () => {}; try { return await fn(); } finally { console.warn = w; } };

const att = (over: Partial<MockAttemptRecord> = {}): MockAttemptRecord => ({
  id: 'attempt-1', exam_id: SSC_CGL_EXAM.id, subject: 'Full Mock', score: 150, total_marks: 200, correct_count: 80,
  incorrect_count: 10, unattempted_count: 10, time_taken_seconds: 3000, attempted_at: '04/10/2026',
  userAnswers: { q1: 2 } as any, paperData: { id: 'p1' } as any, ...over
} as MockAttemptRecord);

(async () => {
  // ===================================================================== 1. practice attempts
  ls.clear();
  check('modules: a new candidate has completed nothing', JSON.stringify(storageService.getCompletedModules()) === '{}');

  calls.length = 0;
  let r = storageService.saveMockAttempt(att());
  r = storageService.saveMockAttempt(att({ score: 151 }));
  const kept = storageService.getMockAttempts();
  check('attempts: a second save of one sitting replaces, never duplicates', kept.length === 1 && kept[0].score === 151 && r.local);

  refuse('mock_attempts');
  calls.length = 0;
  const refused = quiet(() => storageService.saveMockAttempt(att({ id: 'attempt-2' })));
  allow();
  check('attempts: a refused local write says so', refused.local === false);
  check('attempts: ...the previous history is intact', storageService.getMockAttempts().map(a => a.id).join() === 'attempt-1');
  check('attempts: ...and the server copy is still sent', calls.some(c => c.url === '/api/sqlite/mock-attempts' && c.body?.id === 'attempt-2'));

  ls.setItem('govos_mock_attempts', '{broken');
  ls.setItem('govos_target_post_id', 'post-x');
  check('attempts: a corrupt store reads as empty', quiet(() => storageService.getMockAttempts()).length === 0);
  check('attempts: ...its text is kept aside, not lost', ls.getItem('govos_mock_attempts__corrupt') === '{broken');
  check('attempts: ...and unrelated keys are untouched', storageService.getTargetPost() === 'post-x');
  ls.setItem('govos_mock_attempts', JSON.stringify({ not: 'a list' }));
  check('attempts: a store of the wrong shape is not iterated as one', quiet(() => storageService.getMockAttempts(SSC_CGL_EXAM.id)).length === 0);

  ls.clear();
  storageService.saveMockAttempt(att({ localOnlyNote: 'mine' } as any));
  respond = (url) => url.startsWith('/api/sqlite/mock-attempts')
    ? json({ attempts: [{ id: 'attempt-1', exam_id: SSC_CGL_EXAM.id, score: 150, details: null }] }) : json({});
  const merged = (await storageService.loadMockAttemptsFromSQLite(SSC_CGL_EXAM.id))[0] as any;
  check('attempts: the server row is laid over the local one, keeping what only the browser holds',
    merged.localOnlyNote === 'mine' && merged.paperData?.id === 'p1' && merged.userAnswers?.q1 === 2, JSON.stringify(merged));

  // ===================================================================== 2. tracked exams
  ls.clear(); calls.length = 0;
  ls.setItem('govos_tracked_exams', '[]');
  respond = (url) => url === '/api/sqlite/tracked-exams' ? json({ tracked_exam_ids: [SSC_CGL_EXAM.id] }) : json({});
  let tracked = await storageService.loadTrackedExamsFromSQLite();
  check('tracked: the browser\'s empty list is not replaced by the server\'s', tracked.length === 0, tracked.join());
  check('tracked: ...the server is told instead', calls.some(c => c.body?.exam_id === SSC_CGL_EXAM.id && c.body?.is_tracked === false));
  ls.setItem('govos_tracked_exams', JSON.stringify([UPSC_CSE_EXAM.id]));
  calls.length = 0;
  tracked = await storageService.loadTrackedExamsFromSQLite();
  check('tracked: an exam tracked while offline survives the next start', tracked.join() === UPSC_CSE_EXAM.id);
  check('tracked: ...and is sent to the server', calls.some(c => c.body?.exam_id === UPSC_CSE_EXAM.id && c.body?.is_tracked === true));
  ls.clear();
  respond = (url) => url === '/api/sqlite/tracked-exams' ? json({ tracked_exam_ids: [UPSC_CSE_EXAM.id] }) : json({});
  check('tracked: a browser that never held a list adopts the server\'s', (await storageService.loadTrackedExamsFromSQLite()).join() === UPSC_CSE_EXAM.id);
  respond = async () => { throw new Error('offline'); };
  check('tracked: offline keeps the browser\'s list', (await storageService.loadTrackedExamsFromSQLite()).join() === UPSC_CSE_EXAM.id);

  // ===================================================================== 3. notification preferences
  ls.clear();
  const mine = { ...storageService.getNotificationPreferences(), eventSubscriptions: { ...storageService.getNotificationPreferences().eventSubscriptions, results: false } };
  ls.setItem('govos_notification_preferences', JSON.stringify(mine));
  respond = () => json({ user_id: 'u', channels: { inApp: true }, eventSubscriptions: { results: true } });
  check('prefs: the candidate\'s own preferences stand against the server\'s', (await storageService.loadNotificationPreferencesFromSQLite()).eventSubscriptions.results === false);
  ls.clear();
  respond = () => json({ user_id: 'u', stored: false });
  const none = await storageService.loadNotificationPreferencesFromSQLite();
  check('prefs: "nothing stored" is not adopted as a choice', none.eventSubscriptions.results === true && ls.getItem('govos_notification_preferences') === null);
  respond = () => json({ user_id: 'u', channels: { inApp: true }, eventSubscriptions: { results: false } });
  check('prefs: stored server preferences fill an empty browser', (await storageService.loadNotificationPreferencesFromSQLite()).eventSubscriptions.results === false);

  // ===================================================================== 4. notifications, on a controlled clock
  const realNow = Date.now;
  const at = (iso: string) => { Date.now = () => Date.parse(iso); };
  const close = UPSC_CSE_EXAM.dates.find(d => d.type === 'APPLICATION_CLOSE' && d.status !== 'SUPERSEDED' && !d.displayWhen)!;
  const closeMs = Date.parse(close.dateTimeStr.replace(' ', 'T'));
  const regen = (exams: Exam[] = [UPSC_CSE_EXAM]) => storageService.generatePersonalizedNotificationsForTrackedExams(exams);
  ls.clear();
  ls.setItem('govos_tracked_exams', JSON.stringify([UPSC_CSE_EXAM.id, SSC_CGL_EXAM.id]));
  respond = () => json({});
  // a stored alert from the earlier generator: a September "sent" time for a February deadline, and read
  const staleId = `notif-${UPSC_CSE_EXAM.id}-deadline-1d`;
  ls.setItem('govos_candidate_notifications', JSON.stringify([
    { id: staleId, examId: UPSC_CSE_EXAM.id, title: 'old', createdAt: '2026-09-26 10:00:00', isRead: true },
    { id: `notif-${UPSC_CSE_EXAM.id}-obsolete`, examId: UPSC_CSE_EXAM.id, title: 'gone', createdAt: '2026-01-01 00:00:00', isRead: false }
  ]));
  at(new Date(closeMs - 6 * 36e5).toISOString());
  const first = regen([UPSC_CSE_EXAM, SSC_CGL_EXAM]);
  const oneDay = first.find(n => n.id === staleId)!;
  check('alerts: a "sent" time outside the alert\'s own window is replaced', !!oneDay && oneDay.createdAt !== '2026-09-26 10:00:00', oneDay?.createdAt);
  check('alerts: ...its read state is kept', oneDay?.isRead === true);
  check('alerts: an alert no longer generated is not resurrected', !first.some(n => n.id.endsWith('-obsolete')));
  at(new Date(closeMs - 3 * 36e5).toISOString());
  const second = regen([UPSC_CSE_EXAM, SSC_CGL_EXAM]);
  check('alerts: a still-valid "sent" time survives regeneration', second.find(n => n.id === staleId)?.createdAt === oneDay.createdAt);
  check('alerts: regeneration adds no duplicates', new Set(second.map(n => n.id)).size === second.length && second.length === first.length,
    `${first.length} -> ${second.length}`);
  check('alerts: one exam\'s alerts never carry another\'s id', second.every(n => n.id.startsWith(`notif-${n.examId}-`)));
  const result = UPSC_CSE_EXAM.dates.find(d => d.type === 'RESULT' && !d.isTentative && !d.displayWhen);
  if (result) {
    const rMs = Date.parse(result.dateTimeStr.replace(' ', 'T'));
    at(new Date(rMs - 864e5).toISOString());
    check('alerts: a result due tomorrow is not "declared" today', !regen().some(n => n.id.endsWith('-result')));
    at(new Date(rMs + 864e5).toISOString());
    check('alerts: ...and is, once its date has passed', regen().some(n => n.id.endsWith('-result')));
  }
  Date.now = realNow;

  // ===================================================================== 5. registry loads
  const pending: Record<string, (v: any) => void> = {};
  respond = (url) => new Promise(res => { pending[`load${Object.keys(pending).length}`] = (body: any) => res({ ok: true, status: 200, json: async () => body }); });
  const exam = (id: string) => ({ ...ALL_EXAMS[0], id } as Exam);
  const a = examRegistryService.loadWithStatus();
  const b = examRegistryService.loadWithStatus();
  pending.load1({ exams: [exam('exam-new-b')] });
  const bDone = await b;
  pending.load0({ exams: [exam('exam-old-a')] });
  const aDone = await a;
  check('registry: the newer load stands when an older one finishes after it',
    bDone.status === 'FRESH' && aDone.status === 'SUPERSEDED' && examRegistryService.loaded().map(e => e.id).join() === 'exam-new-b',
    `${aDone.status}/${bDone.status}/${examRegistryService.loaded().map(e => e.id)}`);
  respond = async () => { throw new Error('aborted'); };
  const failed = await examRegistryService.loadWithStatus();
  check('registry: a failed or cancelled load keeps the last good list', failed.status === 'FAILED' && failed.exams.map(e => e.id).join() === 'exam-new-b');
  respond = () => json({ error: 'maintenance' });
  check('registry: a reply without a list is a failure, not an empty registry', (await examRegistryService.loadWithStatus()).exams.length === 1);
  respond = () => json({ exams: [exam('exam-new-c')] });
  check('registry: the next good load recovers', (await examRegistryService.loadWithStatus()).exams.map(e => e.id).join() === 'exam-new-c');

  // ===================================================================== 6. results, ticks, sync, scorecard
  ls.clear();
  const entry = { examId: SSC_CGL_EXAM.id, examType: 'GENERIC', marks: 120, category: 'UR', source: 'TYPED' } as any;
  check('results: a saved entry reports success', storageService.setResultEntry(entry, SSC_CGL_EXAM.id) === true);
  refuse('result_entry');
  const refusedEntry = quiet(() => storageService.setResultEntry({ ...entry, marks: 1 }, SSC_CGL_EXAM.id));
  allow();
  check('results: a refused save reports failure and keeps the previous entry',
    refusedEntry === false && storageService.getResultEntry(SSC_CGL_EXAM.id)?.marks === 120);

  ls.setItem('govos_completed_syllabus_topics', 'not json');
  respond = () => json({});
  const ticked = quiet(() => storageService.toggleCompletedTopic(SSC_CGL_EXAM.id, 't1'));
  check('ticks: a corrupt store no longer swallows the tick', ticked.t1 === true && storageService.getCompletedTopics(SSC_CGL_EXAM.id).t1 === true);
  check('ticks: ...the unreadable text was kept aside', ls.getItem('govos_completed_syllabus_topics__corrupt') === 'not json');
  check('readStoredJson: a missing key is the fallback, nothing written', readStoredJson('govos_absent', Array.isArray, ['x']).join() === 'x' && ls.getItem('govos_absent__corrupt') === null);

  calls.length = 0;
  let release!: () => void;
  respond = (url) => url === '/api/sqlite/sync-all' ? new Promise(res => { release = () => res({ ok: true, status: 200, json: async () => ({}) }); }) : json({});
  const s1 = storageService.syncAllToSQLite();
  const s2 = storageService.syncAllToSQLite();
  await new Promise(res => setTimeout(res, 0));
  release();
  const [r1, r2] = await Promise.all([s1, s2]);
  check('sync: two clicks while one sync runs send it once', calls.filter(c => c.url === '/api/sqlite/sync-all').length === 1 && r1 === r2);
  respond = () => Promise.resolve({ ok: false, status: 500, json: async () => ({}) });
  const failedSync = await storageService.syncAllToSQLite();
  check('sync: a server error is not reported as offline', !failedSync.success && /reachable but returned error/.test(failedSync.message), failedSync.message);

  respond = () => Promise.resolve({ ok: false, status: 413, json: async () => { throw new SyntaxError('not json'); } });
  const big = await storageService.parseResultDocument({ name: 'x.pdf', arrayBuffer: async () => new ArrayBuffer(4) } as any, SSC_CGL_EXAM.id);
  check('scorecard: a 413 is "too large", not "server unreachable"', big.ok === false && big.reason === 'FILE_TOO_LARGE', String(big.reason));

  // The syllabus revisions the page applies are a merge over the seed, never a replacement by nothing.
  check('revisions: no revisions leaves the seed as it is', applySyllabusRevisions(SSC_CGL_EXAM, []) === SSC_CGL_EXAM);

  const mainSrc = readFileSync('src/main.tsx', 'utf8');
  check('report: a second click while a report is on its way does not file it twice',
    mainSrc.includes('if (!reportModalData || reportSendingRef.current) return;'));

  if (failures) { console.log(`\n${failures} persistence check(s) failed`); process.exit(1); }
  console.log('persistence: all checks passed');
})();
