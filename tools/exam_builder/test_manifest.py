"""A manifest must freeze discovery — and freeze nothing else.

Two claims are under test, and the second matters more than the first:

    * replaying a manifest gives the same source set however search ranks that day
    * replaying a manifest still runs every correctness check

The second is what stops a manifest becoming a way to smuggle a stale or foreign document
past the gates that exist to catch exactly that. A snapshot that could vouch for a document
would be worse than no snapshot.

Run: python -m tools.exam_builder.test_manifest
"""
from __future__ import annotations

import os
import tempfile

from ..exam_authoring.record import Status
from ..exam_authoring.sources import Document
from . import build as B
from . import discover as D
from .discover import DiscoveredDoc, DocKind, Relevance, SourceSet
from .gate import BuildState
from .identity import IdentityVerdict
from .manifest import (SourceManifest, from_source_set, latest_for, load, save,
                       to_source_set)

_FAILURES: list[str] = []


def check(label: str, got, want) -> None:
    if got != want:
        _FAILURES.append(f'{label}\n     got  {got!r}\n     want {want!r}')


TARGET_NOTICE = """
Staff Selection Commission. Notice of Examination.
Combined Graduate Level Examination, 2026.
FEE: Candidates are required to pay a fee of Rs. 100/-. Women candidates and candidates
belonging to Scheduled Caste and Scheduled Tribe are exempted from payment of fee.
"""

SIBLING_NOTICE = """
Staff Selection Commission. Notice of Examination.
Combined Higher Secondary Level Examination, 2026.
FEE: Candidates are required to pay a fee of Rs. 777/- for this recruitment.
"""


def _source_set(urls: list[str]) -> SourceSet:
    out = SourceSet(exam_id='exam-ssc-ssc-cgl-2026', authority_domain='https://ssc.gov.in')
    for u in urls:
        out.docs.append(DiscoveredDoc(url=u, kind=DocKind.NOTIFICATION, title='Notice',
                                      relevance=Relevance.DIRECT, matched=['cgl']))
    return out


def _loader(mapping: dict[str, str]):
    def load_doc(doc):
        return Document(url=doc.url, kind='PDF', fetched_at='2026-09-17',
                        pages=[mapping.get(doc.url, '')])
    return load_doc


def _build_with(manifest: SourceManifest, mapping: dict[str, str]):
    saved = (B._load, D._search_for_missing_kinds)
    B._load = _loader(mapping)
    D._search_for_missing_kinds = lambda *a, **k: None
    try:
        return B.build(replay=manifest)
    finally:
        B._load, D._search_for_missing_kinds = saved


# ------------------------------------------------------------------------------ tests
def test_fresh_discovery_can_vary_but_replay_cannot() -> None:
    """Two different discovery outcomes; one manifest; one stable input set."""
    run_a = _source_set(['https://ssc.gov.in/a.pdf', 'https://ssc.gov.in/b.pdf'])
    run_b = _source_set(['https://ssc.gov.in/b.pdf', 'https://ssc.gov.in/c.pdf'])
    check('fresh discovery genuinely differs between runs',
          from_source_set(run_a, query='q', authority_name='SSC').digest()
          != from_source_set(run_b, query='q', authority_name='SSC').digest(), True)

    m = from_source_set(run_a, query='SSC CGL 2026', authority_name='Staff Selection Commission')
    replay_1, replay_2 = to_source_set(m), to_source_set(m)
    check('replay is identical to itself',
          [d.url for d in replay_1.docs], [d.url for d in replay_2.docs])
    check('and identical to what was captured', sorted(d.url for d in replay_1.docs),
          sorted(run_a.docs[i].url for i in range(len(run_a.docs))))


def test_manifest_round_trips_on_disk_and_is_never_overwritten() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        m = from_source_set(_source_set(['https://ssc.gov.in/a.pdf']),
                            query='SSC CGL 2026', authority_name='Staff Selection Commission')
        p1 = save(m, directory=tmp)
        p2 = save(m, directory=tmp)
        check('a second capture is a new version, not an overwrite', p1 != p2, True)
        check('both versions survive', all(os.path.exists(p) for p in (p1, p2)), True)
        check('latest_for finds the newest', latest_for(m.exam_id, directory=tmp), p2)
        check('a manifest round-trips', load(p1).urls, m.urls)


def test_replay_still_runs_content_identity() -> None:
    """A foreign document written into a manifest must still be rejected on replay."""
    m = from_source_set(_source_set(['https://ssc.gov.in/chsl.pdf']),
                        query='SSC CGL 2026', authority_name='Staff Selection Commission')
    result = _build_with(m, {'https://ssc.gov.in/chsl.pdf': SIBLING_NOTICE})

    verdicts = {u: c.verdict for u, c in result.identity.items()}
    check('the manifest did not vouch for the document',
          verdicts.get('https://ssc.gov.in/chsl.pdf'), IdentityVerdict.MISMATCH)

    fee = result.record.fields.get('fee')
    check('and its fee never reached the record',
          bool(fee and fee.usable and '777' in (fee.value or {}).get('amounts', [])), False)


def test_replay_still_extracts_from_a_valid_source() -> None:
    m = from_source_set(_source_set(['https://ssc.gov.in/cgl.pdf']),
                        query='SSC CGL 2026', authority_name='Staff Selection Commission')
    result = _build_with(m, {'https://ssc.gov.in/cgl.pdf': TARGET_NOTICE})
    fee = result.record.fields.get('fee')
    check('the exam’s own fee is read on replay',
          bool(fee and fee.usable and '100' in fee.value['amounts']), True)
    check('and it carries a citation', bool(fee and fee.citation and fee.citation.url), True)


def test_replay_does_not_bypass_the_publication_gate() -> None:
    from .gate import GateDecision, evaluate
    m = from_source_set(_source_set(['https://ssc.gov.in/cgl.pdf']),
                        query='SSC CGL 2026', authority_name='Staff Selection Commission')
    result = _build_with(m, {'https://ssc.gov.in/cgl.pdf': TARGET_NOTICE})
    report = evaluate(result.record, build_state=result.build_state,
                      identity_by_source={u: c.verdict for u, c in result.identity.items()})
    check('a replayed build is still judged by the gate',
          report.decision, GateDecision.BLOCK)
    check('and the blockers are real fields, not the manifest',
          any(b.field not in ('(build)',) for b in report.blockers), True)


def test_unfetchable_source_is_infrastructure_not_absence() -> None:
    """A source named in a manifest that will not load must never read as "not published"."""
    from ..exam_authoring.sources import FetchError

    m = from_source_set(_source_set(['https://ssc.gov.in/gone.pdf']),
                        query='SSC CGL 2026', authority_name='Staff Selection Commission')

    def exploding(doc):
        raise FetchError('host unreachable')

    saved = (B._load, D._search_for_missing_kinds)
    B._load = exploding
    D._search_for_missing_kinds = lambda *a, **k: None
    try:
        result = B.build(replay=m)
    finally:
        B._load, D._search_for_missing_kinds = saved

    check('the build is paused, not completed',
          result.build_state, BuildState.PAUSED_INFRASTRUCTURE)
    fee = result.record.fields.get('fee')
    check('and an unread field is ours, not the authority’s silence',
          fee.status if fee else None, Status.NOT_EXTRACTED)


def test_changed_source_is_surfaced() -> None:
    """If a document has been revised since capture, say so — and re-read it."""
    ss = _source_set(['https://ssc.gov.in/cgl.pdf'])
    m = from_source_set(ss, query='SSC CGL 2026', authority_name='Staff Selection Commission',
                        hashes={'https://ssc.gov.in/cgl.pdf': 'a-stale-hash-000000'})
    result = _build_with(m, {'https://ssc.gov.in/cgl.pdf': TARGET_NOTICE})
    check('a source that changed since capture is reported',
          result.changed_sources, ['https://ssc.gov.in/cgl.pdf'])


def main() -> int:
    test_fresh_discovery_can_vary_but_replay_cannot()
    test_manifest_round_trips_on_disk_and_is_never_overwritten()
    test_replay_still_runs_content_identity()
    test_replay_still_extracts_from_a_valid_source()
    test_replay_does_not_bypass_the_publication_gate()
    test_unfetchable_source_is_infrastructure_not_absence()
    test_changed_source_is_surfaced()
    if _FAILURES:
        print(f'{len(_FAILURES)} FAILURE(S):')
        for f in _FAILURES:
            print('  -', f)
        return 1
    print('manifest: discovery is frozen, correctness is not')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
