// Headless checks that the Resource Library lists learning material only, and that nothing an exam
// holds is lost when it moves out: resourceRoleOf (src/ui.tsx) must agree with the Python classifier
// on every case in tools/exam_builder/resource_role_cases.json, and every non-learning card must have
// another section to appear in. Run: npm run check:frontend
import './stub';
import cases from '../exam_builder/resource_role_cases.json';
import { isLearningResource, namedResourceAnswer, RESOURCE_SECTION, resourcePlacementOf, resourceRoleOf,
  SECTION_OF_PLACEMENT } from '../../src/ui';
import { ALL_EXAMS, SSC_CGL_EXAM, UPSC_CSE_EXAM } from '../../src/data';
import type { ResourceItem } from '../../src/types';

let failures = 0;
const check = (name: string, ok: boolean, detail = '') => {
  if (!ok) failures++;
  if (!ok || process.env.VERBOSE) console.log((ok ? 'PASS ' : 'FAIL ') + name + (detail ? ' :: ' + detail : ''));
};

// 1. One table, two classifiers.
const table = (cases as any).cases as Array<{ source: string; item: any; role: string }>;
const learning = new Set<string>((cases as any).learningRoles);
let agreed = 0;
for (const c of table) {
  const got = resourceRoleOf(c.item);
  check(`role of "${c.item.title}" (${c.source})`, got === c.role, `TS ${got}, table ${c.role}`);
  if (got === c.role) agreed++;
}
console.log(`PASS resourceRoleOf agrees with the Python classifier on ${agreed}/${table.length} cases`);
check('the table has cases', table.length >= 50, String(table.length));

// 2. Every registered exam: Resources holds learning roles only, and nothing is lost.
const NON_LEARNING_FORBIDDEN = ['NOTIFICATION', 'CORRIGENDUM', 'APPLICATION_PORTAL', 'OTR_PORTAL', 'QUESTION_PAPER',
  'ANSWER_KEY', 'ADMIT_CARD', 'RESULT', 'CUTOFF', 'EXAM_DAY_INSTRUCTIONS'];
for (const exam of ALL_EXAMS) {
  const all: ResourceItem[] = exam.resources || [];
  const listed = all.filter(isLearningResource);
  const wrong = listed.filter(r => NON_LEARNING_FORBIDDEN.includes(resourceRoleOf(r)) || !learning.has(resourceRoleOf(r)));
  check(`${exam.id}: the Resource Library holds learning material only`, wrong.length === 0, wrong.map(r => r.title).join('; '));
  const placed = all.filter(r => !isLearningResource(r));
  const homeless = placed.filter(r => resourcePlacementOf(r) === 'RESOURCES' || resourcePlacementOf(r) === 'NONE');
  check(`${exam.id}: every other card has a section to appear in`, homeless.length === 0, homeless.map(r => r.title).join('; '));
  console.log(`PASS ${exam.id}: ${listed.length} learning, ${placed.length} shown elsewhere, of ${all.length}`);
}

// 3. The rules the spec names, on the real register.
const byTitle = (exam: typeof SSC_CGL_EXAM, re: RegExp) => (exam.resources || []).find(r => re.test(r.title));
const sscNotice = byTitle(SSC_CGL_EXAM, /Official Notice \(Complete/);
check('SSC: the notice PDF is not study material', !!sscNotice && !isLearningResource(sscNotice) && resourcePlacementOf(sscNotice) === 'OFFICIAL_LINKS');
const sscReopen = byTitle(SSC_CGL_EXAM, /Reopening/);
check('SSC: the reopening notice is a corrigendum, not study material', !!sscReopen && resourceRoleOf(sscReopen) === 'CORRIGENDUM');
const constitution = byTitle(SSC_CGL_EXAM, /Constitution of India/);
check('SSC: the Constitution text is study material although it is a PDF under an official subject', !!constitution && isLearningResource(constitution));
const upscPapers = (UPSC_CSE_EXAM.resources || []).filter(r => r.subject === 'Previous Year Papers');
check('UPSC: every previous-year paper goes to Practice & PYQs', upscPapers.length > 0 && upscPapers.every(r => resourcePlacementOf(r) === 'PRACTICE'));
const upscPortal = byTitle(UPSC_CSE_EXAM, /Online Application Portal/);
check('UPSC: the application portal goes to Application & Documents', !!upscPortal && resourcePlacementOf(upscPortal) === 'APPLICATION');
const channels = (SSC_CGL_EXAM.resources || []).filter(r => r.resourceFormat === 'YOUTUBE_CHANNEL');
check('SSC: coaching channels stay in Resources as lessons', channels.length > 0 && channels.every(r => resourceRoleOf(r) === 'LECTURE_VIDEO'));
// Classification is by content role, never by file extension.
const pdfPaper = { title: 'General Studies — question paper 2025', type: 'OFFICIAL_PDF', resourceFormat: 'DIRECT_PDF', subject: 'History & Culture' } as ResourceItem;
check('a PDF named a question paper is not study material', resourceRoleOf(pdfPaper) === 'QUESTION_PAPER');
const thirdPartyPapers = { title: 'Previous question papers (77) — a coaching site', type: 'THIRD_PARTY', resourceFormat: 'EXTERNAL_PAGE', subject: 'Previous Year Papers' } as ResourceItem;
check('a third-party paper list goes to Practice, never Resources', resourcePlacementOf(thirdPartyPapers) === 'PRACTICE');
const news = { title: 'Admit card released — download now', type: 'VIDEO_LECTURE', resourceFormat: 'YOUTUBE_COURSE', subject: 'Current Affairs & Governance' } as ResourceItem;
check('a news video is a lead, shown nowhere as a resource', resourcePlacementOf(news) === 'NONE');

// 4. One placement model. The frontend's role -> section is the table the Python model is held to.
const sectionTable = (cases as any).sectionForRole as Record<string, string | null>;
check('RESOURCE_SECTION covers exactly the roles of the shared table',
  Object.keys(RESOURCE_SECTION).sort().join() === Object.keys(sectionTable).sort().join());
for (const role of Object.keys(sectionTable)) {
  const got = (RESOURCE_SECTION as Record<string, string | null>)[role] ?? null;
  check(`placement of ${role}`, got === sectionTable[role], `TS ${got}, table ${sectionTable[role]}`);
}

// 5. The assistant hands an entry over in the section that shows it. Only learning material is "in Resources".
let routed = 0;
const sectionsSeen = new Set<string>();
for (const exam of [SSC_CGL_EXAM, UPSC_CSE_EXAM]) {
  for (const r of exam.resources || []) {
    const placement = resourcePlacementOf(r);
    if (placement === 'NONE') continue;
    const got = namedResourceAnswer(r.title, 1, exam);
    // Ranking may prefer another entry for the same words; routing is checked on the entry handed over.
    if (!got || got.reply.resourceLink?.url !== r.url) continue;
    const where = SECTION_OF_PLACEMENT[placement];
    const text = got.reply.text;
    const ok = got.reply.action?.section === where.num && (placement === 'RESOURCES'
      ? /card in Resources/.test(text)
      : text.includes(`I found it under **${where.label}**`) && !/card in Resources|Also in the library/.test(text));
    check(`${exam.id}: "${r.title}" is answered under ${where.label} (section ${where.num})`, ok,
      `action ${got.reply.action?.section}; ${text.slice(0, 160)}`);
    routed++;
    sectionsSeen.add(placement);
  }
}
check('the assistant was checked on entries of several sections', sectionsSeen.size >= 4, [...sectionsSeen].join());
console.log(`PASS namedResourceAnswer routed ${routed} named entries to ${sectionsSeen.size} sections (${[...sectionsSeen].join(', ')})`);
const named = (title: string, exam: typeof SSC_CGL_EXAM) => {
  const r = byTitle(exam, new RegExp(title.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')));
  return r ? namedResourceAnswer(r.title, 1, exam) : null;
};
const upscPaper = upscPapers[0];
const paperAnswer = upscPaper ? namedResourceAnswer(upscPaper.title, 1, UPSC_CSE_EXAM) : null;
check('UPSC: a named previous-year paper is "under Practice & PYQs", never "the card in Resources"',
  !!paperAnswer && paperAnswer.reply.text.includes('I found it under **Practice & PYQs**') && paperAnswer.reply.action?.section === 9
    && !/card in Resources/.test(paperAnswer.reply.text), paperAnswer?.reply.text.slice(0, 160));
const portalAnswer = upscPortal ? named(upscPortal.title, UPSC_CSE_EXAM) : null;
check('UPSC: the named application portal opens Application & Documents',
  !!portalAnswer && portalAnswer.reply.action?.section === 4 && /under \*\*Application & Documents\*\*/.test(portalAnswer.reply.text));
const reopenAnswer = sscReopen ? named(sscReopen.title, SSC_CGL_EXAM) : null;
check('SSC: the named reopening notice opens the Corrigenda Log',
  !!reopenAnswer && reopenAnswer.reply.action?.section === 13 && /under \*\*Corrigenda Log\*\*/.test(reopenAnswer.reply.text));
const constitutionAnswer = constitution ? named(constitution.title, SSC_CGL_EXAM) : null;
check('SSC: named study material is still answered from the Resource Library',
  !!constitutionAnswer && constitutionAnswer.reply.action?.section === 8 && /card in Resources/.test(constitutionAnswer.reply.text));

console.log(failures === 0 ? 'ALL RESOURCE ROLE CHECKS PASSED' : failures + ' FAILED');
process.exit(failures === 0 ? 0 : 1);
