// The generated study plan (section 07) is built from each exam's own record and nothing else. Every register exam
// gets a plan (none is left empty); the days split into learning, a second pass and full papers; the learning hours
// scheduled add up to what the candidate has; ticked topics drop out; a paper choice keeps the plan inside that
// paper; a left-out subject gets no time; a thin syllabus is planned from the pattern's sections; a qualifying part
// does not buy time with its marks; and the planner names no exam, authority or id.
// Run: npm run check:frontend
import './stub';
import { generateStudyPlan, studyPlanDefaultDays, studyPlanUnits, studyPlanTracks, PLAN_DAY_PRESETS } from '../../src/ui';
import { ALL_EXAMS } from '../../src/data';
import type { Exam } from '../../src/types';
import { futureExam } from './future_exam_fixture';

let failures = 0;
const check = (name: string, ok: boolean, detail = '') => {
  if (!ok) failures++;
  if (!ok || process.env.VERBOSE) console.log((ok ? 'PASS ' : 'FAIL ') + name + (detail ? ' :: ' + detail : ''));
};

const learnScheduled = (p: ReturnType<typeof generateStudyPlan>) =>
  p.weeks.filter(w => w.phase === 'LEARN').reduce((a, w) => a + w.items.reduce((b, i) => b + i.hours, 0), 0);

for (const exam of [...ALL_EXAMS, futureExam()]) {
  const ownTopics = new Set(exam.syllabus.map(t => t.id));
  for (const days of PLAN_DAY_PRESETS) {
    const p = generateStudyPlan(exam, { days, hoursPerDay: 4 });
    check(`${exam.id} ${days}d: a plan with subjects and weeks`, p.subjects.length > 0 && p.weeks.length > 0, `${p.subjects.length} subjects, ${p.weeks.length} weeks`);
    check(`${exam.id} ${days}d: the phases add up to the days`, p.learnDays + p.reviseDays + p.practiceDays === days && p.learnDays > 0 && p.reviseDays > 0 && p.practiceDays > 0,
      `${p.learnDays}/${p.reviseDays}/${p.practiceDays}`);
    const sched = learnScheduled(p);
    check(`${exam.id} ${days}d: the learning hours scheduled are the hours the candidate has`, Math.abs(sched - p.learnDays * 4) <= Math.max(4, p.learnDays * 4 * 0.06), `${sched} of ${p.learnDays * 4}`);
    const shares = p.subjects.filter(s => s.included).reduce((a, s) => a + s.share, 0);
    check(`${exam.id} ${days}d: the subject shares add to the whole`, Math.abs(shares - 1) < 0.001, String(shares));
    const foreign = p.subjects.flatMap(s => s.units).filter(u => u.topicId && !ownTopics.has(u.topicId));
    check(`${exam.id} ${days}d: every topic in the plan is this exam's own`, foreign.length === 0, foreign.map(u => u.topicId).join());
    check(`${exam.id} ${days}d: the plan states its basis`, p.basis.length >= 2 && p.basis.every(b => !/undefined|NaN/.test(b)), p.basis.join(' | '));
    const names = ALL_EXAMS.filter(e => e.id !== exam.id).map(e => e.authorityName.split(' (')[0]);
    const text = JSON.stringify(p.basis) + JSON.stringify(p.weeks.map(w => w.items.map(i => i.unit.subtopics)));
    check(`${exam.id} ${days}d: no other authority is named`, !names.some(n => text.includes(n) && !exam.authorityName.includes(n)), '');
  }
}

// Ticked topics drop out, and their hours go to what is left.
const jee = ALL_EXAMS.find(e => e.id === 'exam-jee-main-2026')!;
const physics = jee.syllabus.filter(t => t.subject === 'Paper 1 · Physics');
const done = Object.fromEntries(physics.slice(0, 5).map(t => [t.id, true]));
const before = generateStudyPlan(jee, { days: 90, hoursPerDay: 4 });
const after = generateStudyPlan(jee, { days: 90, hoursPerDay: 4, done });
const learnUnits = (p: typeof after) => new Set(p.weeks.filter(w => w.phase === 'LEARN').flatMap(w => w.items.map(i => i.unit.topicId)).filter(Boolean));
check('JEE: ticked topics are not scheduled again', physics.slice(0, 5).every(t => !learnUnits(after).has(t.id)) && after.unitsDone === 5 && after.unitsLeft === before.unitsLeft - 5,
  `${after.unitsDone} done, ${after.unitsLeft} left`);
check('JEE: what is left gets more time per topic', after.hoursPerUnit > before.hoursPerUnit, `${before.hoursPerUnit} -> ${after.hoursPerUnit}`);

// A paper choice keeps the plan inside that paper.
check('JEE: its alternative papers are the plan\'s choices', studyPlanTracks(jee).join('|') === 'Paper 1|Paper 2A|Paper 2B', studyPlanTracks(jee).join('|'));
const arch = generateStudyPlan(jee, { days: 90, hoursPerDay: 4, track: 'Paper 2A' });
check('JEE Paper 2A: only Paper 2A\'s subjects', arch.track === 'Paper 2A' && arch.subjects.every(s => s.name.startsWith('Paper 2A')), arch.subjects.map(s => s.name).join());
check('JEE Paper 1: equal time to the three equally marked subjects', before.subjects.every(s => Math.abs(s.share - 1 / 3) < 0.01), before.subjects.map(s => s.share.toFixed(3)).join());

// A subject left out gets no time.
const noChem = generateStudyPlan(jee, { days: 90, hoursPerDay: 4, excludedSubjects: ['Paper 1 · Chemistry'] });
check('JEE: a left-out subject gets no hours and no week', noChem.subjects.find(s => s.name === 'Paper 1 · Chemistry')!.hours === 0
  && !noChem.weeks.some(w => w.items.some(i => i.subject === 'Paper 1 · Chemistry')), '');

// A thin syllabus is planned from the pattern's own sections.
for (const id of ['exam-ibps-po-2026', 'exam-appsc-group2-2026']) {
  const exam = ALL_EXAMS.find(e => e.id === id)!;
  const u = studyPlanUnits(exam, null);
  const sections = exam.stages.filter(st => st.tier !== 'INTERVIEW').flatMap(st => st.sections).filter(s => s.marks > 0).length;
  check(`${id}: a thin syllabus is planned from the pattern's sections`, /lists only \d+ topic/.test(u.basis[0] || '') && u.subjects.length >= Math.min(2, sections)
    && u.subjects.reduce((a, s) => a + s.units.length, 0) > exam.syllabus.length, `${u.subjects.length} subjects, ${u.subjects.reduce((a, s) => a + s.units.length, 0)} units`);
  check(`${id}: every syllabus topic is in the plan`, exam.syllabus.every(t => u.subjects.some(s => s.units.some(x => x.topicId === t.id))), '');
}
// A syllabus read whole from the notice is planned from its topics, weighed on the stage that names most subjects.
const g1 = ALL_EXAMS.find(e => e.id === 'exam-appsc-group1-2026')!;
const g1Plan = generateStudyPlan(g1, { days: 120, hoursPerDay: 6 });
const g1Share = (name: string) => g1Plan.subjects.find(s => s.name === name);
check('APPSC Group-I: planned from its own topics, not the thin path', !/lists only/.test(g1Plan.basis[0]) && g1Plan.subjects.reduce((a, s) => a + s.units.length, 0) === g1.syllabus.length, g1Plan.basis[0]);
check('APPSC Group-I: the qualifying Telugu and English papers get the average share, not their 150 marks',
  ['Telugu (Qualifying)', 'English (Qualifying)'].every(n => g1Share(n)?.marks === undefined) && /qualifying parts/.test(g1Plan.basis[0]), g1Plan.basis[0]);
check('APPSC Group-I: two subjects printed in one 150-mark paper share it', g1Share('History & Culture')?.marks === 75 && g1Share('Geography')?.marks === 75,
  `${g1Share('History & Culture')?.marks} / ${g1Share('Geography')?.marks}`);
const thin: Exam = { ...futureExam(), id: 'exam-zssc-thin-2031', syllabus: futureExam().syllabus.slice(0, 2) };
const thinPlan = generateStudyPlan(thin, { days: 60, hoursPerDay: 3 });
check('a synthetic thin syllabus is planned from its own sections', /lists only 2 topics/.test(thinPlan.basis[0]) && thinPlan.subjects.length > 0, thinPlan.basis[0]);

// A qualifying part does not buy time with its marks.
const upsc = ALL_EXAMS.find(e => e.id === 'exam-upsc-cse-2026')!;
const upscPlan = generateStudyPlan(upsc, { days: 180, hoursPerDay: 6 });
const lang = upscPlan.subjects.find(s => /Qualifying/.test(s.name));
check('UPSC: the qualifying language papers get the average share, not their 300 marks', !!lang && lang.marks === undefined && /qualifying part/.test(upscPlan.basis[0]), upscPlan.basis[0]);

// The default length: days to the next firm examination date, else 90.
const now = new Date('2031-01-01T00:00:00');
const fx = futureExam();
const withDate: Exam = { ...fx, dates: [{ ...fx.dates[0], type: 'EXAM_TIER1', dateTimeStr: '2031-03-02 09:00:00', isTentative: false, displayWhen: undefined, status: 'AVAILABLE' }] };
const d = studyPlanDefaultDays(withDate, now);
check('default length is the days left to a firm examination date', d.days === 61 && !!d.reason, JSON.stringify(d));
check('no firm date ahead: 90 days', studyPlanDefaultDays(jee, now).days === 90 && studyPlanDefaultDays(jee, now).reason === null, '');
const tentative: Exam = { ...withDate, dates: [{ ...withDate.dates[0], isTentative: true }] };
check('a tentative date is never counted down to', studyPlanDefaultDays(tentative, now).reason === null, '');

// The planner holds no exam of its own.
{
  const src = String(generateStudyPlan) + String(studyPlanUnits) + String(studyPlanDefaultDays) + String(studyPlanTracks);
  const named = [...ALL_EXAMS, futureExam()].flatMap(e => [e.id, e.code, e.authorityName.split(' (')[0]]).filter(w => w && src.includes(w));
  check('the planner names no exam, code or authority', named.length === 0 && !/['"]exam-/.test(src), named.join());
}

if (failures) { console.log(`\n${failures} study-plan check(s) failed`); process.exit(1); }
console.log('study plan: all checks passed');
