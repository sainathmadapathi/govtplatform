// Headless checks of the Claude-facing frontend contract: the deterministic assistant still places what
// it can and no longer offers a live web search; the services fail soft (ok:false / fallback) when the
// server is offline or Claude is unavailable; 503 CLAUDE_UNAVAILABLE and 403 ADMIN_REQUIRED are explained.
// Run: npm run check:frontend
import './stub';
import { answerCandidateQuery } from '../../src/ui';
import { buildChatContext, claudeService, adminHeaders, adminToken, researchService } from '../../src/services';
import { SSC_CGL_EXAM, UPSC_CSE_EXAM } from '../../src/data';

let failures = 0;
const check = (name: string, ok: boolean, detail = '') => {
  if (!ok) failures++;
  console.log((ok ? 'PASS ' : 'FAIL ') + name + (detail ? ' :: ' + detail : ''));
};

const ask = (q: string, exam = SSC_CGL_EXAM) => answerCandidateQuery(q, buildChatContext(exam, 'ASSISTANT'));

// Deterministic answers still place the questions the register can answer.
const dates = ask('what is the last date to apply');
check('last-date question answered from the register', dates.verified === true && /2026|June|July|apply/i.test(dates.text), dates.text.slice(0, 90));
const where = ask('where do I check my eligibility');
check('navigation question answered with an action', !!where.action, JSON.stringify(where.action));

// An unplaced question is UNVERIFIED, and no longer offers a live web search.
const odd = ask('does the commission allow a scribe for candidates with low vision');
check('unplaced question is UNVERIFIED', odd.sourceKind === 'UNVERIFIED', odd.sourceKind || '');
check('fallback no longer offers a live web search', !/search official government domains live/i.test(odd.text), odd.text.slice(-120));
check('fallback names no other exam', !/SSC/.test(ask('qwerty zxcv', UPSC_CSE_EXAM).text), ask('qwerty zxcv', UPSC_CSE_EXAM).text.slice(0, 80));

// The Claude service degrades to ok:false instead of throwing when the server is unreachable.
(globalThis as any).fetch = async () => { throw new Error('offline'); };
(async () => {
  check('health() is null when offline', (await claudeService.health()) === null);
  const t = await claudeService.ask('exam-ssc-cgl-2026', 'q');
  check('ask() is ok:false + fallback when offline', t.ok === false && (t as any).fallback === true);
  const w = await claudeService.waitForJob('x', { timeoutMs: 50, intervalMs: 10 });
  check('waitForJob() times out into a fallback', w.ok === false && (w as any).fallback === true);
  const s = await researchService.startSearch('x');
  check('startSearch() is ok:false offline', s.ok === false);

  // admin token lives in sessionStorage only and shapes the headers.
  adminToken.set('tok');
  check('adminHeaders carries the token', adminHeaders()['X-GovOS-Admin-Token'] === 'tok');
  adminToken.set('');
  check('adminHeaders empty without a token', Object.keys(adminHeaders()).length === 0);

  // a 503 CLAUDE_UNAVAILABLE becomes a claudeUnavailable outcome with the setup hint.
  (globalThis as any).fetch = async () => ({ ok: false, status: 503, json: async () => ({ error: 'CLAUDE_UNAVAILABLE', status: 'CLAUDE_DISABLED', message: 'disabled', setup: 'do x' }) });
  const u = await researchService.startSearch('x');
  check('503 maps to claudeUnavailable', u.ok === false && (u as any).claudeUnavailable === true && (u as any).setup === 'do x');
  // a 403 admin refusal is explained, not generic.
  (globalThis as any).fetch = async () => ({ ok: false, status: 403, json: async () => ({ error: 'ADMIN_REQUIRED', message: 'admin token required', hint: 'send the header' }) });
  const f = await researchService.startSearch('x');
  check('403 explains the admin guard', f.ok === false && /admin token required/.test((f as any).error));

  console.log(failures === 0 ? 'ALL FRONTEND CHECKS PASSED' : failures + ' FAILED');
  process.exit(failures === 0 ? 0 : 1);
})();
