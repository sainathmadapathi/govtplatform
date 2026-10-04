// Results & Next Steps: every pathway tab of every exam but the UPSC CSE shows content built from that
// exam's own record. The five tabs (the stage-two plan, after both stages, the stage-two gap, the stage-one
// comeback, the skill test) opened onto nothing for SSC CGL, IBPS PO, both APPSC exams and any machine-read
// exam: their panels were deleted with the CSE engine (b473776). Checks the pure builder for every exam and
// pathway, the real section 16 for the pathway its own verdict selects, and that no exam's words or
// evidence reach another.
// Run: npm run check:frontend
import './stub';
import * as React from 'react';
import { renderToString } from 'react-dom/server';
import { ExamDetailView, resultPathway, ResultPathwayPanel, resultPathwayOf } from '../../src/ui';
import type { ResultPathwayId } from '../../src/ui';
import { ALL_EXAMS, APPSC_GROUP1_EXAM, IBPS_PO_EXAM, SSC_CGL_EXAM, UPSC_CSE_EXAM } from '../../src/data';
import type { DataProvenance, Exam, MultiTierResultEntry } from '../../src/types';
import { futureExam, futureExamWithSkill } from './future_exam_fixture';

(globalThis as any).fetch = async () => ({ ok: false, status: 503, json: async () => ({}) });

let failures = 0;
const check = (name: string, ok: boolean, detail = '') => {
  if (!ok) failures++;
  if (!ok || process.env.VERBOSE) console.log((ok ? 'PASS ' : 'FAIL ') + name + (detail ? ' :: ' + detail : ''));
};
const flat = (html: string) => html.replace(/<!--.*?-->/g, '').replace(/<[^>]+>/g, ' ').replace(/&amp;/g, '&')
  .replace(/&#x27;/g, "'").replace(/&quot;/g, '"').replace(/&lt;/g, '<').replace(/&gt;/g, '>').replace(/\s+/g, ' ');

const PATHWAYS: ResultPathwayId[] = ['TIER2_PREP', 'BOTH_PASSED_SELECTION', 'TIER2_MISSED_RECOVERY', 'TIER1_FAILED_RECOVERY', 'SKILL_TEST'];
const FUTURE_C = futureExamWithSkill('C');
const EXAMS: Exam[] = [...ALL_EXAMS.filter(e => e.id !== UPSC_CSE_EXAM.id), futureExam(), FUTURE_C];

/** Every provenance object reachable from a record: the only evidence its pathways may cite. */
const provenancesOf = (root: unknown) => {
  const out = new Set<unknown>(); const seen = new Set<unknown>();
  const walk = (v: unknown) => {
    if (!v || typeof v !== 'object' || seen.has(v)) return; seen.add(v);
    if (Array.isArray(v)) { v.forEach(walk); return; }
    const o = v as Record<string, unknown>;
    if (typeof o.documentTitle === 'string' && ('verificationLevel' in o)) out.add(o);
    Object.values(o).forEach(walk);
  };
  walk(root);
  return out;
};

// What only one exam says. None of it may appear in another exam's pathway.
const OWN_WORDS: Record<string, RegExp[]> = {
  [SSC_CGL_EXAM.id]: [/\bCKT\b/, /\bDEST\b/, /Data Entry Speed/i, /Computer Knowledge/i, /\bTier-?(?:I|II|1|2)\b/, /\b390\b/, /Ministry allocation/i, /Staff Selection/i],
  [UPSC_CSE_EXAM.id]: [/\bCSAT\b/, /Civil Services/i, /Union Public Service/i, /\b1750\b/, /Personality Test/i],
  [IBPS_PO_EXAM.id]: [/\bIBPS\b/, /Probationary Officer/i, /Banking Personnel/i],
};
// SSC's deleted panels, which must not come back for anyone: figures no record holds.
const INVENTED = [/298\+/, /2,?000 key depressions/i, /NACIN/, /Dholpur/i, /Annexure-VI format within 3 years/i];

const standing = (score: number | null, cutoff: number | null) => ({ score, cutoff, margin: score !== null && cutoff !== null ? score - cutoff : null });

// ---------------------------------------------------------------- 1. every pathway of every exam has content
for (const exam of EXAMS) {
  const own = provenancesOf(exam);
  const leaks = Object.entries(OWN_WORDS).filter(([id]) => id !== exam.id).flatMap(([, rx]) => rx);
  for (const id of PATHWAYS) {
    const p = resultPathway(exam, id, { category: 'UR', year: 2025, stageOne: standing(null, null), stageTwo: standing(null, null), now: new Date('2026-10-04') });
    const html = renderToString(React.createElement(ResultPathwayPanel, { pathway: p, onNavigateSection() {}, onNavigatePractice() {}, onSelectPathway() {}, onOpenProvenanceModal() {} }));
    const text = flat(html);
    check(`${exam.id} / ${id}: renders a panel with a title and a summary`, html.includes(`data-result-pathway="${id}"`) && p.title.length > 0 && p.summary.length > 20, p.title);
    check(`${exam.id} / ${id}: every block shows content or says what the record lacks`,
      p.blocks.length > 0 && p.blocks.every(b => b.items.length > 0 || b.missing.trim().length > 10), p.blocks.filter(b => !b.items.length && !b.missing).map(b => b.key).join());
    check(`${exam.id} / ${id}: nothing undefined or empty is printed`, !/\bundefined\b|\bnull\b|NaN/.test(text) && p.blocks.every(b => b.items.every(i => i.title.trim())));
    const cited = p.blocks.flatMap(b => b.items).map(i => i.provenance).filter(Boolean) as DataProvenance[];
    check(`${exam.id} / ${id}: every citation is this exam's own evidence`, cited.every(c => own.has(c)), `${cited.filter(c => !own.has(c)).length} foreign`);
    const found = [...leaks, ...INVENTED].filter(rx => rx.test(text)).map(rx => (text.match(new RegExp(`.{0,40}${rx.source}.{0,30}`, rx.flags)) || [String(rx)])[0]);
    check(`${exam.id} / ${id}: no other exam's words or invented figures`, found.length === 0, found.join(' | '));
  }
}

// ---------------------------------------------------------------- 2. the content is the record's
{
  const ssc = resultPathway(SSC_CGL_EXAM, 'TIER2_PREP', { category: 'UR', stageOne: standing(null, null), stageTwo: standing(null, null) });
  const how = ssc.blocks.find(b => b.key.startsWith('how-'))!;
  check('SSC: the stage-two plan states the merit marks its record prints (390 of 450)', how.items.some(i => /390 counted for the merit, of 450/.test(i.body || '')));
  check('SSC: the stage-two plan offers its skill test, from the record', ssc.blocks.some(b => b.key === 'skill' && b.items.length > 0 && b.action?.pathway === 'SKILL_TEST'));
  const ibps = resultPathway(IBPS_PO_EXAM, 'TIER2_PREP', { category: 'UR', stageOne: standing(null, null), stageTwo: standing(null, null) });
  check('IBPS: no skill-test block, because its record states none', !ibps.blocks.some(b => b.key === 'skill'));
  check('IBPS: its stage-two penalty is quoted from its own record', ibps.blocks.some(b => b.items.some(i => i.body === IBPS_PO_EXAM.stages[1].negativeMarking)));
  const appsc = resultPathway(APPSC_GROUP1_EXAM, 'BOTH_PASSED_SELECTION', { category: 'UR', stageOne: standing(null, null), stageTwo: standing(null, null) });
  const certs = appsc.blocks.find(b => b.key === 'certificates')!;
  check('APPSC Group-I: holds no certificate rules, and says so rather than borrowing another exam\'s', certs.items.length === 0 && /no certificate-validity rules/.test(certs.missing));
  const sscFinal = resultPathway(SSC_CGL_EXAM, 'BOTH_PASSED_SELECTION', { category: 'UR', stageOne: standing(null, null), stageTwo: standing(null, null) });
  const phys = sscFinal.blocks.find(b => b.key === 'physical')!;
  check('SSC: physical standards are the notice\'s own, per post', phys.items.length > 0 && phys.items.every(i => SSC_CGL_EXAM.posts.some(p => p.physicalNote === i.body)));
  const skill = resultPathway(FUTURE_C, 'SKILL_TEST', { category: 'UR', stageOne: standing(null, null), stageTwo: standing(null, null) });
  const cTest = FUTURE_C.stages.find(st => st.skillTest)!.skillTest!;
  check('future exam C: its skill test is named from its own record', skill.title === cTest.name && skill.blocks[0].items.length === 1, skill.title);
  const gap = resultPathway(futureExam(), 'TIER2_MISSED_RECOVERY', { category: 'UR', year: 2029, stageOne: standing(80, 60), stageTwo: standing(150, 170) });
  check('the gap is stated from the candidate\'s figures and the recorded cut-off', /150 is 20 below 2029's UR cut-off of 170/.test(gap.summary), gap.summary);
  check('status aliases map onto their tabs', resultPathwayOf('QUALIFIED_TIER2') === 'TIER2_PREP' && resultPathwayOf('DOC_VERIFICATION') === 'BOTH_PASSED_SELECTION'
    && resultPathwayOf('NOT_QUALIFIED') === 'TIER1_FAILED_RECOVERY' && resultPathwayOf('UPSC_MAINS_PREP') === null);
}

// ---------------------------------------------------------------- 3. the real section shows the pathways
// Section 16 renders the selected pathway's panel. The switch to the verdict's tab runs in an effect, which a
// server render does not run, so here the verdict is read from the tab it marks ACTIVE; the live check
// clicks through the switch itself.
const section16 = (exam: Exam, entry?: Partial<MultiTierResultEntry>) => {
  localStorage.removeItem(`govos_result_entry_${exam.id}`);
  if (entry) localStorage.setItem(`govos_result_entry_${exam.id}`, JSON.stringify({ source: 'TYPED', examId: exam.id, ...entry }));
  const html = renderToString(React.createElement(ExamDetailView as any, { exam, initialSection: 16, onOpenProvenanceModal() {}, onOpenReportModal() {} }));
  localStorage.removeItem(`govos_result_entry_${exam.id}`);
  const text = flat(html);
  // Most specific first: "Comeback Plan ACTIVE" also ends in "Plan ACTIVE".
  const active = (['Comeback Plan', 'Final Allocation & DV', 'Gap', 'Plan'] as const).find(w => text.includes(`${w} ACTIVE`));
  return { html, pathway: (html.match(/data-result-pathway="([^"]*)"/) || [])[1], blocks: (html.match(/data-pathway-block="/g) || []).length, active };
};
const rowOf = (exam: Exam) => [...exam.cutoffsHistory].filter(r => r.tier1Cutoff != null).sort((a, b) => b.year - a.year)[0];
for (const exam of EXAMS) {
  const row = rowOf(exam);
  const opened = section16(exam);
  check(`${exam.id}: section 16 opens on a pathway panel with content`, opened.pathway === 'TIER2_PREP' && opened.blocks > 0, `${opened.pathway} / ${opened.blocks} blocks`);
  if (!row) continue;
  const base = { category: row.category, examYear: row.year };
  const cases: [string, Partial<MultiTierResultEntry>, string][] = [
    ['above the stage-one cut-off -> the stage-two plan', { marks: row.tier1Cutoff! + 5, tier1Marks: row.tier1Cutoff! + 5 }, 'Plan'],
    ['below the stage-one cut-off -> the comeback plan', { marks: row.tier1Cutoff! - 5, tier1Marks: row.tier1Cutoff! - 5 }, 'Comeback Plan'],
    ...(row.tier2Cutoff != null ? [
      ['above both cut-offs -> after both stages', { marks: row.tier1Cutoff! + 5, tier1Marks: row.tier1Cutoff! + 5, tier2Marks: row.tier2Cutoff + 5 }, 'Final Allocation & DV'],
      ['below the stage-two cut-off -> the gap plan', { marks: row.tier1Cutoff! + 5, tier1Marks: row.tier1Cutoff! + 5, tier2Marks: row.tier2Cutoff - 5 }, 'Gap'],
    ] as [string, Partial<MultiTierResultEntry>, string][] : []),
  ];
  for (const [name, entry, tab] of cases) {
    const r = section16(exam, { ...base, ...entry });
    check(`${exam.id}: ${name}`, r.active === tab && !!r.pathway && r.blocks > 0, `active=${r.active} panel=${r.pathway}`);
  }
}
check('UPSC CSE keeps its own engine: no pathway panel from this builder', section16(UPSC_CSE_EXAM).pathway === undefined);

// ---------------------------------------------------------------- 4. generic: no exam is named in the rule
{
  const src = String(resultPathway) + String(ResultPathwayPanel) + String(resultPathwayOf);
  const named = [...ALL_EXAMS, futureExam()].flatMap(e => [e.id, e.code, e.authorityName.split(' (')[0]]).filter(w => w && src.includes(w));
  check('the pathway builder names no exam, code or authority', named.length === 0 && !/['"]exam-/.test(src), named.join());
}

console.log(failures ? `FAIL results pathways: ${failures} failing` : 'PASS results pathways: every non-UPSC tab shows its own exam\'s record');
process.exitCode = failures ? 1 : 0;
