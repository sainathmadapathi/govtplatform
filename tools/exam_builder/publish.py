"""Staged publishing, and the proof that building one exam changed no other.

Building "IBPS PO 2027" must leave SSC CGL and UPSC CSE byte-for-byte as they were. Saying
so is easy; proving it is the point of this module, and the proof is mechanical:

    1. hash every exam in the register *before* the build
    2. write the new exam into a staging copy, never into the live file
    3. hash every exam again
    4. every id other than the one being built must have an identical hash
    5. only then is the staged copy allowed to replace the live one

A build that changes another exam's bytes is a failed build. It is not repaired, not
reported as a warning, and not published — because a silent edit to a neighbouring exam is
exactly the failure the whole architecture exists to prevent, and it is the kind that no
one notices until a candidate is misinformed.

Nothing here parses TypeScript. It slices `data.ts` on the register's own declaration
boundaries, which is enough to hash each exam independently and is far harder to get subtly
wrong than a parser would be.
"""
from __future__ import annotations

import hashlib
import io
import os
import re
import shutil
import time
from dataclasses import dataclass, field

DATA_TS = os.path.join('src', 'data.ts')
STAGING_DIR = os.path.join('.exam_staging')

#: `export const SSC_CGL_EXAM: Exam = {` ... the register's own shape.
_EXAM_DECL = re.compile(r'^export const (\w+):\s*Exam\s*=\s*\{', re.M)
#: The id line inside a record, which is the exam's real identity.
_ID_LINE = re.compile(r"^\s*id:\s*'([^']+)'", re.M)


class IsolationViolation(RuntimeError):
    """Another exam's bytes changed. The build is void."""


@dataclass
class ExamSlice:
    const_name: str
    exam_id: str
    start: int
    end: int
    text: str

    @property
    def digest(self) -> str:
        return hashlib.sha256(self.text.encode('utf-8')).hexdigest()[:16]


#: A record ends at a `};` alone on a line, which is how this register is formatted. A "}"
#: inside a string is never at column 0 followed by a semicolon, so this cannot split a
#: record early the way a brace-counter would.
_RECORD_END = re.compile(r'^\};[ \t]*$', re.M)


def slice_exams(source: str) -> list[ExamSlice]:
    """Every `export const X: Exam = {...}` block, by its own id.

    A record ends at its own closing `};`, **not** at the next declaration. Ending it at
    the next declaration made the last exam's slice absorb everything after it — including
    `ALL_EXAMS` — so merely appending a new exam changed the previous one's hash and the
    isolation proof reported a violation that had not happened.
    """
    decls = list(_EXAM_DECL.finditer(source))
    out: list[ExamSlice] = []
    for i, m in enumerate(decls):
        start = m.start()
        hard_limit = decls[i + 1].start() if i + 1 < len(decls) else len(source)
        closing = _RECORD_END.search(source, m.end(), hard_limit)
        end = closing.end() if closing else hard_limit
        body = source[start:end]
        id_match = _ID_LINE.search(body)
        out.append(ExamSlice(
            const_name=m.group(1),
            exam_id=id_match.group(1) if id_match else f'(no id: {m.group(1)})',
            start=start, end=end, text=body))
    return out


def fingerprint(source: str) -> dict[str, str]:
    """exam id -> digest, for every exam in the register."""
    return {s.exam_id: s.digest for s in slice_exams(source)}


@dataclass
class PublishReport:
    exam_id: str
    staged_path: str
    before: dict[str, str] = field(default_factory=dict)
    after: dict[str, str] = field(default_factory=dict)
    added: list[str] = field(default_factory=list)
    replaced: list[str] = field(default_factory=list)
    untouched: list[str] = field(default_factory=list)
    published: bool = False

    def summary(self) -> str:
        lines = [f'exam:      {self.exam_id}',
                 f'staged to: {self.staged_path}',
                 f'added:     {self.added or "-"}',
                 f'replaced:  {self.replaced or "-"}',
                 f'untouched: {len(self.untouched)} other exam(s), all hashes identical',
                 f'published: {self.published}']
        return '\n'.join(lines)


def assert_only_this_exam_changed(before: dict[str, str], after: dict[str, str],
                                  exam_id: str) -> tuple[list[str], list[str], list[str]]:
    """The proof. Raises rather than returning a warning."""
    added = [e for e in after if e not in before]
    removed = [e for e in before if e not in after]
    changed = [e for e in before if e in after and before[e] != after[e]]

    if removed:
        raise IsolationViolation(
            f'building {exam_id} removed {len(removed)} exam(s) from the register: {removed}')

    foreign_changed = [e for e in changed if e != exam_id]
    if foreign_changed:
        raise IsolationViolation(
            f'building {exam_id} changed {len(foreign_changed)} other exam(s): '
            f'{foreign_changed}. The staged file is discarded; the live register is untouched.')

    foreign_added = [e for e in added if e != exam_id]
    if foreign_added:
        raise IsolationViolation(
            f'building {exam_id} added exams nobody asked for: {foreign_added}')

    untouched = [e for e in before if e in after and before[e] == after[e]]
    return added, [e for e in changed if e == exam_id], untouched


def stage(exam_id: str, record_ts: str, *, data_ts: str = DATA_TS,
          staging_dir: str = STAGING_DIR) -> PublishReport:
    """Write the new record into a staging copy and prove nothing else moved.

    `record_ts` is the rendered `export const ..._EXAM: Exam = {...};` block.
    """
    live = io.open(data_ts, encoding='utf-8').read()
    before = fingerprint(live)

    existing = next((s for s in slice_exams(live) if s.exam_id == exam_id), None)
    if existing is not None:
        staged_source = live[:existing.start] + record_ts.rstrip() + '\n\n' + live[existing.end:]
    else:
        # Appended, not spliced into the middle: inserting between two records is where a
        # stray brace would silently corrupt the neighbour above or below.
        staged_source = live.rstrip() + '\n\n' + record_ts.rstrip() + '\n'

    os.makedirs(staging_dir, exist_ok=True)
    staged_path = os.path.join(staging_dir, f'{exam_id}-{time.strftime("%Y%m%d-%H%M%S")}.ts')
    io.open(staged_path, 'w', encoding='utf-8', newline='').write(staged_source)

    after = fingerprint(staged_source)
    added, replaced, untouched = assert_only_this_exam_changed(before, after, exam_id)

    return PublishReport(exam_id=exam_id, staged_path=staged_path, before=before,
                         after=after, added=added, replaced=replaced, untouched=untouched)


def publish(report: PublishReport, *, data_ts: str = DATA_TS,
            typecheck: bool = True) -> PublishReport:
    """Replace the live register with the staged copy — only after the proof and a typecheck.

    The typecheck is not optional by default. A staged file that does not compile would take
    the whole app down, and the register is the one file every screen reads.
    """
    staged_source = io.open(report.staged_path, encoding='utf-8').read()

    # Re-run the proof against the live file as it is *now*, not as it was when staged:
    # something else may have written to the register in between.
    live_now = io.open(data_ts, encoding='utf-8').read()
    assert_only_this_exam_changed(fingerprint(live_now), fingerprint(staged_source),
                                  report.exam_id)

    if typecheck:
        backup = report.staged_path + '.live-backup'
        shutil.copyfile(data_ts, backup)
        io.open(data_ts, 'w', encoding='utf-8', newline='').write(staged_source)
        import subprocess
        proc = subprocess.run(['npx', 'tsc', '--noEmit'], capture_output=True, text=True,
                              shell=os.name == 'nt')
        if proc.returncode != 0:
            shutil.copyfile(backup, data_ts)
            raise IsolationViolation(
                'the staged register does not typecheck; the live file has been restored.\n'
                + (proc.stdout or proc.stderr)[:1500])
    else:
        io.open(data_ts, 'w', encoding='utf-8', newline='').write(staged_source)

    report.published = True
    return report
