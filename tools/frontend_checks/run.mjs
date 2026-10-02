// Bundles each headless check for node with esbuild (already shipped inside Vite) and runs it.
import { build } from 'esbuild';
import { spawnSync } from 'node:child_process';
import { mkdirSync, rmSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const here = dirname(fileURLToPath(import.meta.url));
const outDir = join(here, '..', '..', 'exam_data');
mkdirSync(outDir, { recursive: true });
const CHECKS = ['claude_services_check.ts', 'resource_roles_check.ts', 'assistant_practice_check.ts'];
let status = 0;
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
