// Bundles each headless check for node with esbuild (already shipped inside Vite) and runs it.
import { build } from 'esbuild';
import { spawnSync } from 'node:child_process';
import { mkdirSync, rmSync, writeFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const here = dirname(fileURLToPath(import.meta.url));
const root = join(here, '..', '..');
const outDir = join(root, 'exam_data');
mkdirSync(outDir, { recursive: true });
const CHECKS = ['claude_services_check.ts', 'resource_roles_check.ts', 'assistant_practice_check.ts', 'assistant_application_check.ts', 'exam_display_check.ts', 'sync_payload_check.ts', 'practice_papers_check.ts', 'future_exam_check.ts', 'results_skill_check.ts', 'ask_verification_check.ts', 'assistant_action_exam_check.ts', 'syllabus_tree_keys_check.ts', 'results_pathways_check.ts', 'eligibility_cutoffs_check.ts', 'exam_isolation_check.ts', 'evidence_boundary_check.ts', 'persistence_check.ts'];
let status = 0;

// The future-exam fixture is "validated data" only if it types against the same Exam model every real
// exam uses: esbuild does not typecheck, so tsc does, over src/ and the fixture together.
const fixtureConfig = join(outDir, '.future_exam.tsconfig.json');
writeFileSync(fixtureConfig, JSON.stringify({ extends: '../tsconfig.json', include: ['../src', '../tools/frontend_checks/future_exam_fixture.ts'] }));
try {
  const tsc = spawnSync(process.execPath, [join(root, 'node_modules', 'typescript', 'bin', 'tsc'), '--noEmit', '-p', fixtureConfig], { stdio: 'inherit' });
  if ((tsc.status ?? 1) !== 0) {
    console.log('FAIL future-exam fixture does not type against the Exam model');
    status = tsc.status ?? 1;
  } else {
    console.log('PASS future-exam fixture types against the Exam model');
  }
} finally {
  rmSync(fixtureConfig, { force: true });
}

for (const check of CHECKS) {
  const out = join(outDir, `.${check.replace(/\.ts$/, '')}.cjs`);
  try {
    await build({
      entryPoints: [join(here, check)], bundle: true, platform: 'node', format: 'cjs',
      jsx: 'automatic', loader: { '.png': 'dataurl' }, outfile: out, logLevel: 'error'
    });
    const run = spawnSync(process.execPath, [out], { stdio: 'inherit' });
    if ((run.status ?? 1) !== 0) status = run.status ?? 1;
  } finally {
    rmSync(out, { force: true });
  }
}
process.exitCode = status;
