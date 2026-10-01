// Bundles claude_services_check.ts for node with esbuild (already shipped inside Vite) and runs it.
import { build } from 'esbuild';
import { spawnSync } from 'node:child_process';
import { mkdirSync, rmSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const here = dirname(fileURLToPath(import.meta.url));
const outDir = join(here, '..', '..', 'exam_data');
const out = join(outDir, '.claude_services_check.cjs');
mkdirSync(outDir, { recursive: true });
try {
  await build({
    entryPoints: [join(here, 'claude_services_check.ts')], bundle: true, platform: 'node', format: 'cjs',
    jsx: 'automatic', loader: { '.png': 'dataurl' }, outfile: out, logLevel: 'error'
  });
  const run = spawnSync(process.execPath, [out], { stdio: 'inherit' });
  process.exitCode = run.status ?? 1;
} finally {
  rmSync(out, { force: true });
}
