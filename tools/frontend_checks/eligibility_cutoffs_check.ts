// Eligibility and cut-offs apply only what the record declares for this exam, post and category.
//  * The engine required a Bachelor's degree of every post and carried SSC's JSO / Statistical Investigator
//    rules as `post.id === …` branches. It now reads the post's own `ruleGroup`, else the exam's
//    `globalRuleGroup`; a post with no rule, or one no profile can answer, is NOT DETERMINED.
//  * Results compared a candidate with the year's first cut-off row whenever their category had no row
//    (a "General" candidate on an exam that prints "UR" got SSC's SC cut-off). A row is used now only
//    where it is the category's own; otherwise the section says the cut-off is not available.
// Run: npm run check:frontend
import './stub';
import * as React from 'react';
import { renderToString } from 'react-dom/server';
import { EligibilityCalculator, ExamDetailView, startingResultCategory, verdictCutoffRows } from '../../src/ui';
import {
  categoryCodesOf, evaluateEligibility, evaluatePostEligibility, evaluateQualification, matchCutoffRow, postVerdictState,
  qualificationLevelOf, qualificationQuestionsFor
} from '../../src/services';
import * as services from '../../src/services';
import { ALL_EXAMS, IBPS_PO_EXAM, SSC_CGL_EXAM, UPSC_CSE_EXAM } from '../../src/data';
import type { CutoffEntry, Exam, MultiTierResultEntry, UserProfile } from '../../src/types';
import { futureExam, futureExamWithQualifications } from './future_exam_fixture';

(globalThis as any).fetch = async () => ({ ok: false, status: 503, json: async () => ({}) });

let failures = 0;
const check = (name: string, ok: boolean, detail = '') => {
  if (!ok) failures++;
  if (!ok || process.env.VERBOSE) console.log((ok ? 'PASS ' : 'FAIL ') + name + (detail ? ' :: ' + detail : ''));
};
const flat = (html: string) => html.replace(/<!--.*?-->/g, '').replace(/<[^>]+>/g, ' ').replace(/&amp;/g, '&')
  .replace(/&#x27;/g, "'").replace(/&quot;/g, '"').replace(/\s+/g, ' ');

// ======================================================================= 1. cut-off rows by category
const prov = SSC_CGL_EXAM.cutoffsHistory[0].provenance;
const row = (category: string, tier1Cutoff: number): CutoffEntry => ({ year: 2030, category, tier1Cutoff, provenance: prov });
const UR_SC = [row('UR', 150), row('SC', 120)];
const pick = (rows: CutoffEntry[], cat: string) => { const m = matchCutoffRow(rows, cat); return m.status === 'MATCHED' ? m.row.tier1Cutoff : m.status; };

check('the audit\'s bug: ST with only UR and SC rows -> no cut-off, not 150', pick(UR_SC, 'ST') === 'NO_ROW_FOR_CATEGORY', String(pick(UR_SC, 'ST')));
check('SC -> 120', pick(UR_SC, 'SC') === 120);
check('UR -> 150', pick(UR_SC, 'UR') === 150);
check('the profile\'s GENERAL is the record\'s UR (one category in the existing wording table)', pick(UR_SC, 'GENERAL') === 150);
check('"General (UR)" names the same category', pick([row('General (UR)', 150), row('SC', 120)], 'UR') === 150 && pick([row('General (UR)', 150)], 'GENERAL') === 150);
check('an unknown category is not mapped to UR', pick(UR_SC, 'Freedom Fighter') === 'NO_ROW_FOR_CATEGORY');
check('no category chosen -> asked for, not assumed', pick(UR_SC, '') === 'NO_CATEGORY');
check('no rows -> no cut-off', pick([], 'UR') === 'NO_CUTOFFS');
check('a generic PwBD is not given a PwBD sub-category\'s cut-off', pick([row('PwBD-OH', 100), row('PwBD-HH', 68)], 'PwBD') === 'NO_ROW_FOR_CATEGORY');
check('the exact sub-category is matched exactly', pick([row('PwBD-OH', 100), row('PwBD-HH', 68)], 'PwBD-HH') === 68);
check('substring is not a match: ST does not take an "SC, STE…" style label', pick([row('SCOUTS', 90)], 'SC') === 'NO_ROW_FOR_CATEGORY');
check('a combined row declared for SC/ST serves ST where it is the only one', pick([row('SC/ST', 110), row('UR', 150)], 'ST') === 110);
check('a category\'s own row outranks a combined one', pick([row('SC/ST', 110), row('SC', 120)], 'SC') === 120);
check('two rows that could both be it -> ambiguous, neither used', pick([row('SC/ST', 110), row('SC (Ex-S)', 95), row('Scheduled Castes', 120)], 'SC') === 'AMBIGUOUS');
check('no alias is invented: Backward Classes is not OBC', pick([row('Backward Classes', 66)], 'OBC') === 'NO_ROW_FOR_CATEGORY');
check('category codes come from the existing table only', [...categoryCodesOf('General (UR)')].join() === 'GENERAL' && categoryCodesOf('PwBD-OH').size === 0);

// Real records.
const ssc25 = verdictCutoffRows(SSC_CGL_EXAM, 2025);
check('SSC: only stage cut-off rows are offered to the verdict (no JSO/sectional rows)', ssc25.length === 10 && ssc25.every(r => r.tier1Cutoff != null), String(ssc25.length));
check('SSC: GENERAL reads the UR row (136.40215), not the first row (SC 115.02843)', pick(ssc25, 'GENERAL') === 136.40215, String(pick(ssc25, 'GENERAL')));
check('UPSC: General reads its own row', pick(verdictCutoffRows(UPSC_CSE_EXAM, 2025), 'GENERAL') === 92.66);
check('IBPS: only General (UR) is recorded; SC gets no cut-off', pick(verdictCutoffRows(IBPS_PO_EXAM, 2024), 'GENERAL') === 54.25 && pick(verdictCutoffRows(IBPS_PO_EXAM, 2024), 'SC') === 'NO_ROW_FOR_CATEGORY');
check('the starting category is the candidate\'s, never the first row\'s', startingResultCategory(SSC_CGL_EXAM, 2025, null, null) === ''
  && startingResultCategory(SSC_CGL_EXAM, 2025, null, 'GENERAL') === 'UR' && startingResultCategory(SSC_CGL_EXAM, 2025, { category: 'OBC' }, 'GENERAL') === 'OBC');

// ======================================================================= 2. eligibility from the record
const base: UserProfile = { dateOfBirth: '2005-03-10', degree: "Bachelor's degree", branch: 'History', percentage: 70, category: 'GENERAL',
  gender: 'Female', domicileState: '', nationality: 'Indian', physicalFitnessDeclared: true, colorBlind: false, mathsIn12thWith60Percent: false, statisticsInDegree: false };
const FUTURE = futureExamWithQualifications();
const postOf = (exam: Exam, id: string) => exam.posts.find(p => p.id === id)!;
const verdict = (exam: Exam, id: string, over: Partial<UserProfile> = {}) =>
  evaluatePostEligibility(postOf(exam, id), { ...base, ...over }, exam.crucialEligibilityDate, exam);

// A -- a Bachelor's post
check('A: Bachelor\'s post, Bachelor\'s candidate -> eligible', postVerdictState(verdict(FUTURE, 'post-zssc-revenue-inspector')) === 'ELIGIBLE');
check('A: Bachelor\'s post, Class 12 candidate -> not eligible', postVerdictState(verdict(FUTURE, 'post-zssc-revenue-inspector', { degree: 'Class 12 (Intermediate)' })) === 'NOT_ELIGIBLE');
check('A: the reason names the requirement and the notice clause', /requires a Bachelor's degree \(Para 5\)/.test(verdict(FUTURE, 'post-zssc-revenue-inspector', { degree: '12th Pass' }).reason));
// B -- a Class 12 post
check('B: Class 12 post, Class 12 candidate -> eligible (no global Bachelor\'s assumption)', postVerdictState(verdict(FUTURE, 'post-zssc-record-assistant', { degree: '12th Pass' })) === 'ELIGIBLE');
check('B: Class 12 post, Bachelor\'s candidate -> meets the minimum level', postVerdictState(verdict(FUTURE, 'post-zssc-record-assistant')) === 'ELIGIBLE');
check('B: Class 12 post, below Class 12 -> not eligible', postVerdictState(verdict(FUTURE, 'post-zssc-record-assistant', { degree: 'Below Class 12' })) === 'NOT_ELIGIBLE');
// C -- a specific qualification
check('C: subject post, Statistics graduate -> eligible', postVerdictState(verdict(FUTURE, 'post-zssc-agri-statistician', { branch: 'Statistics' })) === 'ELIGIBLE');
check('C: subject post, History graduate -> not eligible (not every Bachelor\'s qualifies)', postVerdictState(verdict(FUTURE, 'post-zssc-agri-statistician')) === 'NOT_ELIGIBLE');
check('C: subject post, subject not given -> not determined', postVerdictState(verdict(FUTURE, 'post-zssc-agri-statistician', { branch: '' })) === 'NOT_DETERMINED');
// D -- no qualification stated
const missing = verdict(FUTURE, 'post-zssc-process-server');
check('D: no qualification in the record -> not determined, neither eligible nor not', postVerdictState(missing) === 'NOT_DETERMINED' && missing.qualStatus === 'UNKNOWN'
  && /states no educational qualification for Process Server/.test(missing.reason), missing.reason);
check('D: the same for a Class 12 candidate (never rejected on an assumed degree)', postVerdictState(verdict(FUTURE, 'post-zssc-process-server', { degree: '12th Pass' })) === 'NOT_DETERMINED');
check('an unreadable qualification is not determined, not a fail', verdict(FUTURE, 'post-zssc-revenue-inspector', { degree: 'Diploma in Something' }).qualStatus === 'UNKNOWN');
check('a final-year candidate with no declared permission -> not determined', verdict(FUTURE, 'post-zssc-revenue-inspector', { degree: 'Final Year' }).qualStatus === 'UNKNOWN');
check('a final-year candidate still meets a Class 12 post', verdict(FUTURE, 'post-zssc-record-assistant', { degree: 'Final Year' }).qualStatus === 'OK');
const futureDiag = evaluateEligibility(FUTURE, { ...base, degree: '12th Pass' });
check('the exam verdict counts undetermined posts as such, not as failures', futureDiag.status === 'CONDITIONAL' && futureDiag.totalEligiblePosts === 1
  && /1 post\(s\) were not evaluated/.test(futureDiag.plainEnglishExplanation), futureDiag.plainEnglishExplanation);
check('the plain future exam (no qualification rule at all) is never "eligible" on a guessed degree',
  evaluateEligibility(futureExam(), base).postVerdicts.every(v => v.qualStatus === 'UNKNOWN'));

// SSC regression, from the rules now held in its record
const SSC = SSC_CGL_EXAM;
check('SSC: an ordinary post accepts any Bachelor\'s, citing Para 8.4', verdict(SSC, 'post-aso-css').qualStatus === 'OK' && /Para 8\.4/.test(verdict(SSC, 'post-aso-css').reason));
check('SSC: a Class 12 candidate is not eligible for an ordinary post', verdict(SSC, 'post-aso-css', { degree: '12th Pass' }).qualStatus === 'DISQUALIFIED');
check('SSC: final-year candidates may apply (Para 8.5), with its condition', verdict(SSC, 'post-aso-css', { degree: 'Final Year' }).qualStatus === 'OK'
  && /Para 8\.5.*01\.08\.2026/.test(verdict(SSC, 'post-aso-css', { degree: 'Final Year' }).reason));
check('SSC JSO: 60% in Class 12 Mathematics qualifies', verdict(SSC, 'post-jso', { mathsIn12thWith60Percent: true }).qualStatus === 'OK');
check('SSC JSO: Statistics in the degree qualifies', verdict(SSC, 'post-jso', { statisticsInDegree: true }).qualStatus === 'OK');
check('SSC JSO: neither -> not eligible', verdict(SSC, 'post-jso').qualStatus === 'DISQUALIFIED');
check('SSC JSO: Mathematics question unanswered and no Statistics -> not determined', verdict(SSC, 'post-jso', { mathsIn12thWith60Percent: undefined }).qualStatus === 'UNKNOWN');
check('SSC Statistical Investigator: Economics degree qualifies', verdict(SSC, 'post-stat-inv', { branch: 'Economics' }).qualStatus === 'OK');
check('SSC Statistical Investigator: Maths written "Maths" still matches Mathematics', verdict(SSC, 'post-stat-inv', { branch: 'Maths' }).qualStatus === 'OK');
check('SSC Statistical Investigator: History degree -> not eligible', verdict(SSC, 'post-stat-inv').qualStatus === 'DISQUALIFIED');
check('SSC AAO (State): the state-language condition is stated and not guessed', verdict(SSC, 'post-aao-state').qualStatus === 'UNKNOWN'
  && /Regional\/official language of the State at matriculation level/.test(verdict(SSC, 'post-aao-state').reason));
check('SSC: age is unchanged -- underage still fails', verdict(SSC, 'post-aso-css', { dateOfBirth: '2010-01-01' }).ageStatus === 'UNDERAGE');
check('SSC: OBC relaxation still applies where the record publishes it', verdict(SSC, 'post-aso-css', { dateOfBirth: '1993-09-01', category: 'OBC' }).ageStatus === 'OK'
  && verdict(SSC, 'post-aso-css', { dateOfBirth: '1993-09-01', category: 'GENERAL' }).ageStatus === 'EXCEEDED');
check('UPSC: final-year has no quoted permission in its record -> not determined, not assumed', verdict(UPSC_CSE_EXAM, UPSC_CSE_EXAM.posts[0].id, { degree: 'Final Year', dateOfBirth: '2003-01-01' }).qualStatus === 'UNKNOWN');
check('qualification levels are read deterministically', [["Bachelor's degree", 'GRADUATION'], ['12th Pass', 'CLASS_12'], ['Class 12 (Intermediate)', 'CLASS_12'], ['B.Tech', 'GRADUATION'],
  ["Master's Degree", 'POST_GRADUATION'], ['Final Year', 'GRADUATION_APPEARING'], ['Below Class 12', 'BELOW_CLASS_12'], ['Diploma in Something', null]]
  .every(([t, l]) => qualificationLevelOf(t) === l));
check('questions are asked only where a rule reads them', qualificationQuestionsFor(SSC).mathsIn12th && qualificationQuestionsFor(SSC).degreeSubject
  && !qualificationQuestionsFor(IBPS_PO_EXAM).mathsIn12th && !qualificationQuestionsFor(IBPS_PO_EXAM).degreeSubject
  && qualificationQuestionsFor(FUTURE).degreeSubject && !qualificationQuestionsFor(FUTURE).mathsIn12th);

// No exam or post is named in the rules.
{
  const src = [services.evaluateQualification, services.evaluatePostEligibility, services.matchCutoffRow, services.categoryCodesOf,
    services.qualificationQuestionsFor, services.postVerdictState].map(String).join('\n');
  const named = [...ALL_EXAMS, FUTURE].flatMap(e => [e.id, ...e.posts.map(p => p.id)]).filter(id => src.includes(`'${id}'`) || src.includes(`"${id}"`));
  check('the eligibility and cut-off rules name no exam or post id', named.length === 0 && !/post-jso|post-stat-inv|includes\('ssc|includes\('cgl/i.test(src), named.join());
}

// ======================================================================= 3. what the candidate sees
// Eligibility: the calculator on the future exam (its default profile is a B.Tech graduate).
{
  const html = renderToString(React.createElement(EligibilityCalculator as any, { exam: FUTURE, onSelectExam() {}, onOpenProvenanceModal() {} }));
  const states = Object.fromEntries((html.match(/data-post-state="[^"]*"[^>]*>[\s\S]*?<h4[^>]*>([^<]*)</g) || [])
    .map(m => [m.replace(/[\s\S]*<h4[^>]*>/, '').replace(/<$/, '').trim(), (m.match(/data-post-state="([^"]*)"/) || [])[1]]));
  const text = flat(html);
  check('UI: the Class 12 post is not rejected for a graduate', states['Record Assistant'] === 'ELIGIBLE', JSON.stringify(states));
  check('UI: the subject post shows NOT ELIGIBLE for a B.Tech in Computer Science', states['Agricultural Statistician'] === 'NOT_ELIGIBLE');
  check('UI: the post with no stated qualification shows NOT DETERMINED', states['Process Server'] === 'NOT_DETERMINED' && /NOT DETERMINED/.test(text) && /states no educational qualification for Process Server/.test(text));
  check('UI: the Bachelor\'s requirement is shown with its clause', /requires a Bachelor's degree \(Para 5\)/.test(text));
  check('UI: the qualification list no longer calls 12th pass ineligible', !/12th Pass Only \(Ineligible\)/.test(text) && />12th Pass</.test(html));
  check('UI: a "Not determined" filter appears beside Eligible / Ineligible', /Not determined \(1\)/.test(text) && /Ineligible \(1\)/.test(text), (text.match(/Eligible \(\d+\)|Ineligible \(\d+\)|Not determined \(\d+\)/g) || []).join());
  check('UI: the Mathematics question is not asked where no rule reads it', !/60% or more in Mathematics/.test(text) && /Statistics<\/strong> as a subject/.test(html));
}
// Results: the exact bug, through the real section.
const withRows = (rows: CutoffEntry[]): Exam => ({ ...futureExam(), cutoffsHistory: rows });
const section16 = (exam: Exam, entry?: Partial<MultiTierResultEntry>) => {
  localStorage.removeItem(`govos_result_entry_${exam.id}`);
  localStorage.removeItem('govos_candidate_profile');
  if (entry) localStorage.setItem(`govos_result_entry_${exam.id}`, JSON.stringify({ source: 'TYPED', examId: exam.id, ...entry }));
  const html = renderToString(React.createElement(ExamDetailView as any, { exam, initialSection: 16, onOpenProvenanceModal() {}, onOpenReportModal() {} }));
  localStorage.removeItem(`govos_result_entry_${exam.id}`);
  const text = flat(html);
  return { html, text, state: (html.match(/data-cutoff-state="([^"]*)"/) || [])[1], benchmark: (text.match(/Cutoffs Benchmark \([^)]*\) [^|]*/) || [''])[0] };
};
{
  const exam = withRows([{ ...row('UR', 150), year: 2030 }, { ...row('SC', 120), year: 2030 }]);
  const st = section16(exam, { category: 'ST', examYear: 2030, marks: 130, tier1Marks: 130 });
  check('UI: ST candidate -> "Cut-off not available for your selected category"', st.state === 'NO_ROW_FOR_CATEGORY' && /Cut-off not available for your selected category/.test(st.text), st.state);
  // The verdict badges are upper case ("ABOVE 2030'S PHASE A CUT-OFF", "BELOW THE PHASE A CUT-OFF"); "below" also
  // occurs in ordinary prose ("the self-assessment below"), so the badge words are matched as written.
  const VERDICT = /ABOVE \d{4}'S|ABOVE BOTH|BELOW THE|Above the [^.]* cut-off|Below \d{4}'s/;
  check('UI: ST candidate -> no verdict against 150 or 120', !VERDICT.test(st.text) && !st.benchmark, (st.text.match(VERDICT) || [''])[0]);
  check('UI: the notice says which categories are recorded and that none is borrowed', /lists UR, SC\. GovOS does not use another category's figure/.test(st.text));
  const sc = section16(exam, { category: 'SC', examYear: 2030, marks: 130, tier1Marks: 130 });
  check('UI: SC candidate -> compared with 120', !sc.state && /Cutoffs Benchmark \(2030 · SC\)/.test(sc.text) && /: 120\b/.test(sc.benchmark) && /ABOVE 2030'S/.test(sc.text), sc.benchmark);
  const ur = section16(exam, { category: 'UR', examYear: 2030, marks: 130, tier1Marks: 130 });
  check('UI: UR candidate -> compared with 150', /: 150\b/.test(ur.benchmark) && /BELOW THE/.test(ur.text), ur.benchmark);
  const none = section16(exam);
  check('UI: no category chosen -> asked for, no verdict, no benchmark', none.state === 'NO_CATEGORY' && !none.benchmark && /<option value="" selected="">Choose your category<\/option>/.test(none.html), none.state);
  const ssc = section16(SSC_CGL_EXAM, { category: 'GENERAL', examYear: 2025, marks: 140, tier1Marks: 140 });
  check('UI: SSC with the profile\'s GENERAL -> its UR cut-off 136.40215, not SC\'s 115.02843', /136\.40215/.test(ssc.benchmark) && !/115\.02843/.test(ssc.benchmark), ssc.benchmark);
}

console.log(failures ? `FAIL eligibility & cut-offs: ${failures} failing` : 'PASS eligibility & cut-offs: only what the record declares for the exam, post and category');
process.exitCode = failures ? 1 : 0;
