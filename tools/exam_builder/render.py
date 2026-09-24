"""Preservation-safe use of the existing universal renderer.

The universal renderer already exists and is reused verbatim: `exam_authoring.emit.render_exam`
turns a build record into a complete, valid, status-aware `Exam` block — only sourced values,
`NEEDS_REVIEW` emitted as `UNDER_VERIFICATION`, unauthored sections as honest empty arrays, a
`DataProvenance` on every value, and no exam-specific branch. This module does **not**
re-implement it. It adds the one decision the renderer cannot make on its own: whether it is
*safe* to publish the rendered block over the live register.

A full preservation-merge is not safely achievable against the production representation
(see PRODUCTION_RENDERER_AUDIT.md): authored `data.ts` records reference shared `const`
provenance and carry inline comments, and `publish.stage` replaces an exam's whole slice — so
re-emitting a partial machine build over an authored record would (a) erase authored arrays a
partial build never extracted and (b) drop comments and inline the shared consts. Neither is
acceptable. So the rule is asymmetric and preservation-first:

    NEW exam (no block in the register)   -> safe to append the rendered block
    EXISTING exam in the register         -> refuse; overwriting could erase authored data

"A missing section is not an empty section": a partial build never overwrites an existing
record. Merging new verified fields into an existing authored record is a separate, bounded P1
(it needs a fidelity-preserving structured store, not a TS re-emit), documented in the audit
and deliberately not forced here.
"""
from __future__ import annotations

import io

from . import publish as P
from ..exam_authoring.emit import render_exam   # the universal renderer, reused as-is

__all__ = ['render_exam', 'target_in_register', 'NEW', 'EXISTS']

NEW = 'NEW'
EXISTS = 'EXISTS'


def target_in_register(exam_id: str, data_ts: str = P.DATA_TS) -> bool:
    """True when an exam with this id already holds a block in the register.

    Reuses `publish.slice_exams`/`fingerprint` (a textual slice on the register's own
    declaration boundaries — no TypeScript is parsed), so there is one definition of "an exam
    is in the register" across the engine.
    """
    try:
        source = io.open(data_ts, encoding='utf-8').read()
    except OSError:
        return False
    return exam_id in P.fingerprint(source)
