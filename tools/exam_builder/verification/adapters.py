"""Turn a published record row into a verification `Claim`.

This is the join between the completed data engine and the verification layer: it takes a
projected result declaration (the dict `compat.result_declarations` emits) plus the exam's own
identity, and produces the exact claim/evidence/source triple the verifier checks. It is
universal -- it reads only generic row fields and never branches on an authority or exam type,
so the same adapter serves every exam's results.

It does not itself verify or publish anything; it only shapes the input.
"""
from __future__ import annotations

from .schemas import Claim


def claim_from_result(row: dict, *, official_name: str, authority: str,
                      source_text: str = '') -> Claim:
    """A `Claim` for one result declaration.

    - `value` is the declared date, else the scheduled date -- exactly what the record states.
    - `evidence_span` is the declaration's own provenance excerpt (the verbatim span the
      reader captured), never a Tavily snippet.
    - identity/cycle come from the exam record, so the deterministic gate can reject a source
      that belongs to another exam or cycle before the model is ever consulted.
    """
    prov = row.get('provenance') or {}
    value = row.get('declaredAt') or row.get('expectedAt') or ''
    field = 'result:' + str(row.get('kind', 'RESULT')).lower()
    return Claim(
        exam_id=row.get('examId', ''),
        field=field,
        value=str(value),
        cycle=str(row.get('cycle', '')),
        evidence_span=prov.get('excerptText') or row.get('label', ''),
        source_url=prov.get('officialUrl') or row.get('documentUrl') or row.get('portalUrl') or '',
        source_title=prov.get('documentTitle') or row.get('label', ''),
        authority=authority,
        official_name=official_name,
        source_text=source_text,
        # A scheduled result carries a date but no declared value; a declared one always has a
        # value. Both are checkable, so a value is required only when the row states one.
        requires_value=bool(value),
    )
