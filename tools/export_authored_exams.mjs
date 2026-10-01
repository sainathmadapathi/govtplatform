// Writes exam_data/authored_exams.json: the authored exam register (ALL_EXAMS in src/data.ts) as
// plain JSON, for the server's Ask AI context builder. The register has one source of truth,
// src/data.ts; this is a read-only projection of it, regenerated on every `npm run build` and
// never committed (exam_data/ is gitignored). Without it Ask AI cannot build a fact sheet for an
// authored exam and the candidate gets the deterministic assistant instead.
import { build } from 'esbuild';
import { mkdirSync, rmSync, writeFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';

const root = join(dirname(fileURLToPath(import.meta.url)), '..');
const outDir = join(root, 'exam_data');
const bundle = join(outDir, '.authored_exams.bundle.mjs');

mkdirSync(outDir, { recursive: true });
try {
  await build({
    entryPoints: [join(root, 'src', 'data.ts')],
    bundle: true, platform: 'node', format: 'esm', outfile: bundle, logLevel: 'error',
    loader: { '.png': 'dataurl' },
  });
  const mod = await import(pathToFileURL(bundle).href);
  const exams = mod.ALL_EXAMS;
  if (!Array.isArray(exams) || exams.length === 0) throw new Error('ALL_EXAMS is empty');
  writeFileSync(join(outDir, 'authored_exams.json'), JSON.stringify(exams));
  console.log(`exam_data/authored_exams.json: ${exams.length} exams`);
} finally {
  rmSync(bundle, { force: true });
}
