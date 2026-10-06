// Ask GovOS AI may say "verified" only when the fact's own evidence proves it. Checks the page's rule
// against the server's case table (tools/claude_cli/fact_verification_cases.json), then the rendered state:
// the answer badge, each cited fact's chip, the Evidence button, and the Evidence panel it opens.
// Run: npm run check:frontend
import './stub';
import { readFileSync } from 'fs';
import { join } from 'path';
import * as React from 'react';
import { renderToString } from 'react-dom/server';
import {
  answerVerification, ClaudeAnswerBadge, ClaudeAnswerFacts, claudeAnswerBadgeText, EvidenceButton, EvidencePanel,
  factVerification, withClaim
} from '../../src/ui';
import { SSC_CGL_EXAM } from '../../src/data';
import type { ClaudeAnswerCitation, ClaudeAnswerResult, DataProvenance } from '../../src/types';

let failures = 0;
const check = (name: string, ok: boolean, detail = '') => {
  if (!ok) failures++;
  if (!ok || process.env.VERBOSE) console.log((ok ? 'PASS ' : 'FAIL ') + name + (detail ? ' :: ' + detail : ''));
};
const flat = (html: string) => html.replace(/<!--.*?-->/g, '').replace(/<[^>]+>/g, ' ').replace(/&amp;/g, '&')
  .replace(/&#x27;/g, "'").replace(/&quot;/g, '"').replace(/\s+/g, ' ');
const panelSays = (p: DataProvenance) => flat(renderToString(React.createElement(EvidencePanel, { provenance: p, onClose() {} })));
const OFFICIAL = /Officially verified/;

// ---------------------------------------------------------------- 1. one rule, one table, both sides
type Case = { name: string; provenance: DataProvenance | null; claim: string[]; expect: string };
const table: { cases: Case[] } = JSON.parse(readFileSync(join(__dirname, '..', 'tools', 'claude_cli', 'fact_verification_cases.json'), 'utf8'));
for (const c of table.cases) {
  const got = factVerification(c.provenance, c.claim);
  check(`rule parity: ${c.name}`, got === c.expect, `page ${got}, server ${c.expect}`);
  // What the Evidence button opens is withClaim(provenance, claim); the panel says "Officially verified"
  // for exactly the VERIFIED cases.
  if (c.provenance) {
    const opened = withClaim(c.provenance, c.claim)!;
    const says = OFFICIAL.test(panelSays(opened));
    check(`panel: ${c.name}`, says === (c.expect === 'VERIFIED'), `panel verified=${says}, state ${c.expect}`);
  }
}
check('the table covers every state', new Set(table.cases.map(c => c.expect)).size === 5);

// ---------------------------------------------------------------- 2. rendered answers (Cases A-F)
// Facts as the server sends them, built from SSC CGL's own record so real provenance is exercised.
const lastDate = SSC_CGL_EXAM.dates.find(d => d.type === 'APPLICATION_CLOSE' && d.status !== 'SUPERSEDED')!;
const lastClaim = [lastDate.displayWhen || '', lastDate.dateTimeStr.split(' ')[0]].filter(Boolean);
check('fixture: SSC\'s operative last date is itself verified against its own words',
  factVerification(lastDate.provenance, lastClaim) === 'VERIFIED', JSON.stringify(lastClaim));

const cite = (id: string, label: string, text: string, provenance: DataProvenance | undefined, claim: string[], verification?: string): ClaudeAnswerCitation =>
  ({ id, section: 'Dates', label, text, provenance, claim, verification: verification as any });
const verifiedCite = cite('F6', 'Last date to apply', lastDate.dateTimeStr, lastDate.provenance, lastClaim, 'VERIFIED');
const noSource = cite('F2', 'Cycle', '2026', undefined, ['2026'], 'UNVERIFIED');
const pending = cite('F9', 'Last date to apply', lastDate.dateTimeStr,
  { ...lastDate.provenance, verificationLevel: 'UNDER_VERIFICATION' }, lastClaim, 'UNDER_VERIFICATION');
const mismatched = cite('F7', 'Last date to apply', '2026-10-15', lastDate.provenance, ['2026-10-15'], 'UNSUPPORTED');

const answer = (citations: ClaudeAnswerCitation[], verification?: string): ClaudeAnswerResult => ({
  answer: 'text', basis: 'VERIFIED_DATA', verification: verification as any, uncertainty: 'NONE', navigateTo: 'DATES', followUp: '',
  citations, label: 'CLAUDE_ASSISTED', engine: 'claude-cli', examId: SSC_CGL_EXAM.id, factsSupplied: 20, factsTruncated: false
});

/** The badge and facts as the chat renders them, plus what each Evidence button opens when clicked. */
const render = (a: ClaudeAnswerResult) => {
  const opened: DataProvenance[] = [];
  const onOpen = (p: DataProvenance) => opened.push(p);
  const badge = renderToString(React.createElement(ClaudeAnswerBadge, { answer: a }));
  const facts = renderToString(React.createElement(ClaudeAnswerFacts, { answer: a, onOpenProvenanceModal: onOpen }));
  // Click every Evidence button the facts render: the same props ClaudeAnswerFacts passes, through the real component.
  for (const c of a.citations) {
    if (!c.provenance) continue;
    const el = (EvidenceButton as any)({ provenance: c.provenance, onOpen, claim: c.claim && c.claim.length ? c.claim : c.text });
    el?.props.onClick();
  }
  return {
    badge: flat(badge), badgeState: (badge.match(/data-answer-verification="([^"]*)"/) || [])[1],
    chips: (facts.match(/data-fact-verification="([^"]*)"/g) || []).map(m => m.slice(24, -1)),
    facts: flat(facts), buttons: (facts.match(/data-evidence-type="([^"]*)"/g) || []).map(m => m.slice(20, -1)),
    panels: opened.map(p => OFFICIAL.test(panelSays(p)))
  };
};
const GLOBAL = 'FROM GOVOS VERIFIED DATA';

{ // A: a fact with no provenance
  const r = render(answer([noSource], 'NOT_VERIFIED'));
  check('A: no provenance -> no global verified badge', !r.badge.includes(GLOBAL) && r.badgeState === 'NOT_VERIFIED', r.badge);
  check('A: its chip says not verified, and there is no Evidence button', r.chips.join() === 'UNVERIFIED' && r.buttons.length === 0
    && /No official source on record — not verified/.test(r.facts));
}
{ // B: under verification
  const r = render(answer([pending], 'NOT_VERIFIED'));
  check('B: UNDER_VERIFICATION is preserved, not upgraded', r.chips.join() === 'UNDER_VERIFICATION' && !r.badge.includes(GLOBAL), r.chips.join());
  check('B: its Evidence panel does not say "Officially verified"', r.panels.length === 1 && !r.panels[0]);
}
{ // C: a verified fact
  const r = render(answer([verifiedCite], 'VERIFIED'));
  check('C: verified fact -> verified badge', r.badge.includes(GLOBAL) && r.badgeState === 'VERIFIED', r.badge);
  check('C: its chip and its Evidence panel both say verified', r.chips.join() === 'VERIFIED' && r.panels.join() === 'true'
    && /Officially verified/.test(r.facts) && r.buttons.length === 1 && r.buttons[0] !== 'UNSUPPORTED', `${r.chips} ${r.panels} ${r.buttons}`);
}
{ // D: a mixed answer
  const r = render(answer([verifiedCite, noSource, pending], 'PARTLY_VERIFIED'));
  check('D: mixed -> partly verified, never the global badge', r.badgeState === 'PARTLY_VERIFIED' && !r.badge.includes(GLOBAL)
    && /PARTLY VERIFIED/.test(r.badge), r.badge);
  check('D: each fact keeps its own state', r.chips.join() === 'VERIFIED,UNVERIFIED,UNDER_VERIFICATION', r.chips.join());
  check('D: only the verified fact\'s panel says verified', r.panels.join() === 'true,false', r.panels.join());
  check('D: the footer says only the marked facts are verified', /Only the facts marked "Officially verified" are verified/.test(r.facts));
}
{ // E: evidence exists but does not state the claim
  const r = render(answer([mismatched], 'NOT_VERIFIED'));
  check('E: claim mismatch -> not verified', r.chips.join() === 'UNSUPPORTED' && !r.badge.includes(GLOBAL), r.chips.join());
  check('E: the Evidence button says not verified and its panel names the value', r.buttons.join() === 'UNSUPPORTED'
    && /Evidence · not verified/.test(r.facts) && r.panels.join() === 'false');
}
{ // F: the page never takes the server's (or anyone's) word over the evidence
  const forged = render(answer([{ ...mismatched, verification: 'VERIFIED' }, { ...noSource, verification: 'VERIFIED' }], 'VERIFIED'));
  check('F: a result claiming VERIFIED for unproven facts is not shown verified', !forged.badge.includes(GLOBAL)
    && forged.chips.join() === 'UNSUPPORTED,UNVERIFIED', `${forged.badge} | ${forged.chips.join()}`);
  const demoted = render(answer([{ ...verifiedCite, verification: 'UNDER_VERIFICATION' }], 'NOT_VERIFIED'));
  check('F: the page never upgrades a fact the server did not verify', demoted.chips.join() === 'UNDER_VERIFICATION' && !demoted.badge.includes(GLOBAL));
  const legacy = render(answer([{ ...verifiedCite, verification: undefined }], undefined));
  check('F: an older result with no verification state is not verified', !legacy.badge.includes(GLOBAL) && legacy.chips.join() === 'UNVERIFIED');
  check('F: citing nothing verifies nothing', answerVerification(answer([], 'VERIFIED')) === 'NOT_VERIFIED');
}

// ---------------------------------------------------------------- 3. the invariant, over every combination
const pool = [verifiedCite, noSource, pending, mismatched];
for (let mask = 1; mask < 16; mask++) {
  const cs = pool.filter((_, i) => mask & (1 << i));
  for (const server of ['VERIFIED', 'PARTLY_VERIFIED', 'NOT_VERIFIED', undefined]) {
    const a = answer(cs, server);
    const shown = claudeAnswerBadgeText(a).includes(GLOBAL);
    const proven = cs.every(c => factVerification(withClaim(c.provenance, c.claim), c.claim) === 'VERIFIED');
    check(`invariant: badge verified <=> every fact proven (${mask}/${server})`, shown === (proven && server === 'VERIFIED'));
  }
}
for (const basis of ['NOT_IN_RECORD', 'NEEDS_CLARIFICATION'] as const) {
  check(`${basis} is never badged verified`, !claudeAnswerBadgeText({ ...answer([verifiedCite], 'VERIFIED'), basis }).includes(GLOBAL));
}

console.log(failures ? `FAIL ask verification: ${failures} failing` : 'PASS ask verification: rule parity, badge, fact chips, Evidence button and panel');
process.exitCode = failures ? 1 : 0;
