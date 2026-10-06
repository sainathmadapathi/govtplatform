// Mock-attempt sync: each attempt's paper and answers travel once, and sync-all goes in size-bounded
// requests that never approach the server's 16 MB limit, with every attempt in exactly one of them.
// The real storageService runs against a stubbed fetch; every request it sends is inspected.
// Run: npm run check:frontend
import './stub';
import { OFFICIAL_10_MOCK_PAPERS } from '../../src/data';
import {
  attemptSyncPayload, planAttemptSyncBatches, storageService, SYNC_BATCH_BUDGET_BYTES, SYNC_REQUEST_LIMIT_BYTES
} from '../../src/services';
import type { MockAttemptRecord } from '../../src/services';

let failures = 0;
const check = (name: string, ok: boolean, detail = '') => {
  if (!ok) failures++;
  if (!ok || process.env.VERBOSE) console.log((ok ? 'PASS ' : 'FAIL ') + name + (detail ? ' :: ' + detail : ''));
};
const bytes = (s: string) => new TextEncoder().encode(s).length;
const count = (hay: string, needle: string) => hay.split(needle).length - 1;

// The largest real paper GovOS stores, as an attempt carries it.
const paper = [...OFFICIAL_10_MOCK_PAPERS].sort((a, b) => JSON.stringify(b).length - JSON.stringify(a).length)[0];
const marker = `"${paper.questions[0].id}"`;                     // appears once per copy of the paper
const answers = Object.fromEntries(paper.questions.map((_, i) => [i, i % 4]));
const attempt = (i: number, over: Partial<MockAttemptRecord> = {}): MockAttemptRecord => ({
  id: `att-${i}`, exam_id: 'exam-ssc-cgl-2026', subject: 'Full Mock', score: 120, total_marks: 200,
  correct_count: 70, incorrect_count: 20, unattempted_count: 10, time_taken_seconds: 3600,
  userAnswers: answers, paperData: paper, ...over
});
const oldShape = (a: MockAttemptRecord) => ({ ...a, details: { userAnswers: a.userAnswers, paperData: a.paperData } });

// ---------------------------------------------------------------- 1. one attempt, once
const one = JSON.stringify(attemptSyncPayload(attempt(1)));
check('payload: the paper appears exactly once', count(one, marker) === 1, String(count(one, marker)));
check('payload: one "paperData" and one "userAnswers"', count(one, '"paperData"') === 1 && count(one, '"userAnswers"') === 1);
const parsed = JSON.parse(one);
check('payload: answers and paper sit under details, where both endpoints read them',
  parsed.details?.paperData?.id === paper.id && Object.keys(parsed.details?.userAnswers || {}).length === paper.questions.length
  && !('paperData' in parsed) && !('userAnswers' in parsed));
const loadedBack = attempt(2, { details: { userAnswers: answers, paperData: paper, note: 'kept' } });
const lb = JSON.stringify(attemptSyncPayload(loadedBack));
check('payload: an attempt loaded back from the server (it carries details too) is sent once, its other details kept',
  count(lb, marker) === 1 && JSON.parse(lb).details.note === 'kept', String(count(lb, marker)));
const before = bytes(JSON.stringify(oldShape(attempt(1)))), after = bytes(one);
check('payload: half the size it was', after < before * 0.55, `${before} -> ${after} bytes`);
console.log(`one attempt: ${(before / 1024).toFixed(0)} KB before, ${(after / 1024).toFixed(0)} KB after`);

// ---------------------------------------------------------------- stubbed network
type Sent = { url: string; body: string };
let sent: Sent[] = [];
let answer: (n: number) => { ok: boolean; status: number } | 'throw' = () => ({ ok: true, status: 200 });
(globalThis as any).fetch = async (url: string, init?: any) => {
  const n = sent.length;
  sent.push({ url, body: String(init?.body ?? '') });
  const a = answer(n);
  if (a === 'throw') throw new Error('network down');
  return { ok: a.ok, status: a.status, json: async () => ({}) };
};
const setAttempts = (list: MockAttemptRecord[]) => localStorage.setItem('govos_mock_attempts', JSON.stringify(list));
const syncAll = async () => { sent = []; return storageService.syncAllToSQLite(); };

(async () => {
  // ------------------------------------------------------------ 2. single-attempt route
  setAttempts([]);
  sent = [];
  storageService.saveMockAttempt(attempt(7));
  await new Promise(r => setTimeout(r, 0));
  const single = sent.find(s => s.url === '/api/sqlite/mock-attempts');
  check('single attempt: sent once', sent.filter(s => s.url === '/api/sqlite/mock-attempts').length === 1);
  check('single attempt: paper once, answers once', !!single && count(single.body, marker) === 1
    && count(single.body, '"userAnswers"') === 1, single ? String(count(single.body, marker)) : 'nothing sent');

  // ------------------------------------------------------------ 3. a long history: 50 full papers
  const history = Array.from({ length: 50 }, (_, i) => attempt(i));
  setAttempts(history);
  const oldBody = bytes(JSON.stringify({ mock_attempts: history.map(oldShape) }));
  const res = await syncAll();
  const bodies = sent.map(s => s.body);
  const sizes = bodies.map(bytes);
  const ids = bodies.flatMap(b => (JSON.parse(b).mock_attempts || []).map((a: any) => a.id));
  console.log(`50 attempts: one ${(oldBody / 1048576).toFixed(1)} MB request before; now ${bodies.length} requests of `
    + `${sizes.map(n => (n / 1048576).toFixed(2)).join(', ')} MB`);
  check('history: spread across several requests', bodies.length > 1, String(bodies.length));
  check('history: every request within the batch budget and far under the server limit',
    sizes.every(n => n <= SYNC_BATCH_BUDGET_BYTES + 64 * 1024 && n < SYNC_REQUEST_LIMIT_BYTES), sizes.join(','));
  check('history: every attempt in exactly one request', ids.length === 50 && new Set(ids).size === 50
    && history.every(a => ids.includes(a.id)), `${ids.length} sent, ${new Set(ids).size} distinct`);
  check('history: no paper sent twice', bodies.reduce((n, b) => n + count(b, marker), 0) === 50);
  check('history: no answers sent twice', bodies.reduce((n, b) => n + count(b, '"userAnswers"'), 0) === 50);
  check('history: the profile goes once, with the first request', 'profile' in JSON.parse(bodies[0])
    && bodies.slice(1).every(b => !('profile' in JSON.parse(b)) && JSON.parse(b).user_id));
  check('history: success, all 50 counted', res.success && res.syncedAttempts === 50 && res.requests === bodies.length
    && (res.failedAttemptIds || []).length === 0, JSON.stringify({ ...res, message: undefined }));

  // ------------------------------------------------------------ 4. a failed request is reported, not retried
  const plan = planAttemptSyncBatches(history);
  answer = n => (n === 1 ? { ok: false, status: 500 } : { ok: true, status: 200 });
  const failed = await syncAll();
  const secondIds = plan.batches[1].map(a => String(a.id));
  check('failure: reported', !failed.success && /returned error/.test(failed.message), failed.message);
  check('failure: names exactly the attempts of the failed request', JSON.stringify(failed.failedAttemptIds) === JSON.stringify(secondIds));
  check('failure: no request repeated -- the successful ones are not resent', sent.length === plan.batches.length
    && new Set(sent.map(s => s.body)).size === sent.length, `${sent.length} requests for ${plan.batches.length} batches`);
  check('failure: the rest still synced', failed.syncedAttempts === 50 - secondIds.length);
  answer = () => 'throw';
  const offline = await syncAll();
  check('offline: reported as offline, every attempt listed', !offline.success && /offline/.test(offline.message)
    && (offline.failedAttemptIds || []).length === 50, offline.message);
  answer = () => ({ ok: true, status: 200 });

  // ------------------------------------------------------------ 5. idempotent and deterministic
  await syncAll();
  const first = sent.map(s => s.body);
  await syncAll();
  check('re-run: the same requests, in the same order (the server upserts by attempt id)',
    JSON.stringify(first) === JSON.stringify(sent.map(s => s.body)));

  // ------------------------------------------------------------ 6. empty history
  setAttempts([]);
  const empty = await syncAll();
  const body = sent[0] ? JSON.parse(sent[0].body) : {};
  check('empty: one request, still carrying the profile, with no attempts', sent.length === 1 && 'profile' in body
    && Array.isArray(body.mock_attempts) && body.mock_attempts.length === 0 && empty.success);

  // ------------------------------------------------------------ 7. near and over the limit
  const big = attempt(99);
  const size = bytes(JSON.stringify(attemptSyncPayload(big)));
  const near = planAttemptSyncBatches([attempt(1), big, attempt(2)], size - 1, size + 1024);
  check('near the limit: an attempt larger than the budget travels alone', near.batches.length === 3
    && near.batches.every(b => b.length === 1) && near.oversized.length === 0);
  const over = planAttemptSyncBatches([attempt(1), big, attempt(2)], size * 4, size - 1);
  check('over the limit: reported as oversized, never sent and never dropped silently',
    JSON.stringify(over.oversized) === JSON.stringify(['att-1', 'att-99', 'att-2']) && over.batches.length === 0);
  // Through the real sync: an attempt over the server's 16 MB limit is never sent (it would be a 413
  // that took its whole request down) and is reported by id; the others still go.
  const huge = attempt(500, { paperData: { ...paper, padding: 'x'.repeat(SYNC_REQUEST_LIMIT_BYTES + 1024) } });
  setAttempts([attempt(1), huge, attempt(2)]);
  const withHuge = await syncAll();
  check('over the limit: syncAll never sends it, names it, and still syncs the rest', !withHuge.success
    && JSON.stringify(withHuge.failedAttemptIds) === JSON.stringify(['att-500']) && withHuge.syncedAttempts === 2
    && sent.every(s => bytes(s.body) < SYNC_REQUEST_LIMIT_BYTES && !s.body.includes('att-500'))
    && /larger than the server accepts/.test(withHuge.message), withHuge.message);

  console.log(failures === 0 ? 'ALL SYNC PAYLOAD CHECKS PASSED' : failures + ' FAILED');
  process.exit(failures === 0 ? 0 : 1);
})();
