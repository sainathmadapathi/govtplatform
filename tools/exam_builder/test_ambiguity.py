"""Two real authorities answering to one name is a result, not a failure.

The live case that forced this: "APPSC Group I 2026" scored Arunachal Pradesh Public Service
Commission at 0.60 and Andhra Pradesh Public Service Commission at 0.40, and the resolver
took the 0.60. Both commissions exist, both run a Group I examination, and the 0.20 between
them was a property of that afternoon's search results.

Every fixture here is invented. No real authority is named in the assertions, because the
behaviour under test is structural — if it only worked for the two commissions that exposed
it, it would be the hard-coding this engine exists to avoid.

Run: python -m tools.exam_builder.test_ambiguity
"""
from __future__ import annotations

from .ambiguity import (PLAUSIBLE_SHARE, AuthorityCandidate, Decision, decide, name_tokens,
                        same_body)

_FAILURES: list[str] = []


def check(label: str, got, want) -> None:
    if got != want:
        _FAILURES.append(f'{label}\n     got  {got!r}\n     want {want!r}')


def cand(domain: str, name: str, score: float, **kw) -> AuthorityCandidate:
    return AuthorityCandidate(domain=domain, name=name, score=score,
                              evidence=[f'https://{domain}/notice'], **kw)


# ------------------------------------------------------------------- A. one authority
def test_a_single_clear_authority_resolves() -> None:
    v = decide('Zeta Recruitment Board Clerk 2026', [
        cand('zrb.gov.in', 'Zeta Recruitment Board', 0.9),
    ])
    check('A: one body resolves', v.decision, Decision.RESOLVED)
    check('A: and it is the one found', v.chosen.domain, 'zrb.gov.in')
    check('A: the candidate list is still populated', len(v.candidates), 1)


def test_a_body_and_its_own_regional_site_are_one_authority() -> None:
    """A branch office is not a rival, and must not create a false ambiguity."""
    v = decide('Zeta Board Clerk 2026', [
        cand('zrb.gov.in', 'Zeta Recruitment Board', 0.6),
        cand('zrbsouth.gov.in', 'Zeta Recruitment Board Southern Region', 0.4),
    ])
    check('A: a regional arm is absorbed, not treated as a rival',
          v.decision, Decision.RESOLVED)
    check('A: onto the parent body', v.chosen.domain, 'zrb.gov.in')
    check('A: and the absorption is recorded for audit',
          v.chosen.absorbed, ['zrbsouth.gov.in'])


def test_a_body_and_its_apply_portal_are_one_authority() -> None:
    v = decide('Zeta Board Clerk 2026', [
        cand('zrb.gov.in', 'Zeta Recruitment Board', 0.7),
        cand('zrbonline.gov.in', 'Online Application Portal', 0.3),
    ])
    check('A: an apply portal grown from the same address is the same body',
          v.decision, Decision.RESOLVED)
    check('A: absorbed onto the parent', v.chosen.absorbed, ['zrbonline.gov.in'])


# ------------------------------------------------------- B. two authorities, one acronym
def test_two_real_authorities_sharing_an_acronym_are_ambiguous() -> None:
    v = decide('ZPSC Group I 2026', [
        cand('zpsc.gov.in', 'Zeta Pradesh Public Service Commission', 0.60),
        cand('portal-psc.zp.gov.in', 'Zephyr Pradesh Public Service Commission', 0.40),
    ])
    check('B: two real bodies, no distinguishing name -> ambiguous',
          v.decision, Decision.AMBIGUOUS_AUTHORITY)
    check('B: nothing is chosen', v.chosen, None)
    check('B: both candidates are preserved', len(v.candidates), 2)
    check('B: and the evidence of each survives',
          all(c.evidence for c in v.candidates), True)
    check('B: the reason says what would have told them apart',
          'zeta' in v.reason.lower() and 'zephyr' in v.reason.lower(), True)


def test_a_large_score_gap_still_does_not_decide() -> None:
    """Requirement 4, taken at its word: the margin is never the tiebreaker.

    0.75 against 0.25 is a wide gap, and it is still a fact about search ranking rather
    than about which commission the candidate meant.
    """
    v = decide('ZPSC Group I 2026', [
        cand('zpsc.gov.in', 'Zeta Pradesh Public Service Commission', 0.75),
        cand('zppsc.gov.in', 'Zephyr Pradesh Public Service Commission', 0.25),
    ])
    check('B: a wide margin between two real bodies is still ambiguous',
          v.decision, Decision.AMBIGUOUS_AUTHORITY)


def test_shared_body_words_alone_never_distinguish() -> None:
    """"Public Service Commission" is what they have in common, not what separates them."""
    check('"commission" is not a distinguishing word',
          name_tokens('Public Service Commission'), set())
    check('but the place-name in front of it is',
          name_tokens('Zeta Pradesh Public Service Commission'), {'zeta', 'pradesh'})


# ------------------------------------------------- 5. the name may resolve the ambiguity
def test_a_name_that_distinguishes_resolves() -> None:
    v = decide('Zephyr Pradesh Public Service Commission Group I 2026', [
        cand('zpsc.gov.in', 'Zeta Pradesh Public Service Commission', 0.60),
        cand('zppsc.gov.in', 'Zephyr Pradesh Public Service Commission', 0.40),
    ])
    check('the supplied name carries one body’s own word -> resolved',
          v.decision, Decision.RESOLVED)
    check('and it resolves to that body, not to the higher score',
          v.chosen.domain, 'zppsc.gov.in')
    check('the reason names what decided it', 'zephyr' in v.reason.lower(), True)


def test_a_name_naming_both_stays_ambiguous() -> None:
    v = decide('Zeta Zephyr joint Group I 2026', [
        cand('zpsc.gov.in', 'Zeta Pradesh Public Service Commission', 0.60),
        cand('zppsc.gov.in', 'Zephyr Pradesh Public Service Commission', 0.40),
    ])
    check('a name matching both distinguishes neither',
          v.decision, Decision.AMBIGUOUS_AUTHORITY)


# ------------------------------------------ C. an authority beside unrelated noise
def test_a_faint_unrelated_site_does_not_create_ambiguity() -> None:
    """A stray mention is not a rival claim, so the presence floor may drop it.

    This is a floor for presence, never a margin for preference: it removes a candidate
    almost nothing points at, and never chooses between two that are both present.
    """
    v = decide('Zeta Board Clerk 2026', [
        cand('zrb.gov.in', 'Zeta Recruitment Board', 0.90),
        cand('examnews.example', 'Latest Govt Jobs and Coaching Updates', 0.06),
        cand('crackit.example', 'Crack Zeta Clerk — Best Online Coaching', 0.04),
    ])
    check('C: one authority plus noise resolves', v.decision, Decision.RESOLVED)
    check('C: to the authority', v.chosen.domain, 'zrb.gov.in')
    check('C: and the noise is still listed for audit', len(v.candidates), 3)


def test_the_floor_cannot_break_a_tie_between_two_present_bodies() -> None:
    check('the floor sits below an even split', PLAUSIBLE_SHARE < 0.5, True)
    v = decide('ZPSC Group I 2026', [
        cand('zpsc.gov.in', 'Zeta Pradesh Public Service Commission', 0.51),
        cand('zppsc.gov.in', 'Zephyr Pradesh Public Service Commission', 0.49),
    ])
    check('two present bodies survive the floor and stay ambiguous',
          v.decision, Decision.AMBIGUOUS_AUTHORITY)


# ------------------------------------------------------------------ housekeeping
def test_no_candidates_is_unresolved_not_ambiguous() -> None:
    v = decide('Zeta Board Clerk 2026', [])
    check('nothing found is UNRESOLVED', v.decision, Decision.UNRESOLVED)
    check('and is never dressed up as ambiguity', v.is_ambiguous, False)


def test_same_body_needs_a_real_overlap() -> None:
    a = cand('zrb.gov.in', 'Zeta Recruitment Board', 1.0)
    b = cand('zppsc.gov.in', 'Zephyr Pradesh Public Service Commission', 1.0)
    check('two unrelated bodies are not merged', same_body(a, b), False)
    check('a body is the same as itself', same_body(a, a), True)


def test_the_verdict_can_be_audited() -> None:
    v = decide('ZPSC Group I 2026', [
        cand('zpsc.gov.in', 'Zeta Pradesh Public Service Commission', 0.60),
        cand('zppsc.gov.in', 'Zephyr Pradesh Public Service Commission', 0.40),
    ])
    text = v.summary()
    check('the summary shows the decision', 'AMBIGUOUS_AUTHORITY' in text, True)
    check('and every candidate with its score',
          all(c.domain in text for c in v.candidates), True)


# --------------------------------------- D/E. through the real resolver, no network
def _fake_hits(rows):
    from types import SimpleNamespace
    return [SimpleNamespace(title=t, url=u, content=c, trust='OFFICIAL',
                            host=u.split('/')[2].replace('www.', ''))
            for t, u, c in rows]


def _with_search(fn):
    """Run the real resolver with search replaced. Nothing else is stubbed."""
    from . import resolve as R
    saved = R.search
    R.search = fn
    try:
        return R.resolve_authority('ZPSC Group I 2026')
    finally:
        R.search = saved


def test_e_a_search_outage_is_infrastructure_not_a_verdict() -> None:
    """E. The one outcome that must never be confused with the other three."""
    from .search import SearchUnavailable

    def down(*a, **k):
        raise SearchUnavailable('search failed: getaddrinfo failed')

    v = _with_search(down)
    check('E: an outage is INFRASTRUCTURE_FAILURE',
          v.decision, Decision.INFRASTRUCTURE_FAILURE)
    check('E: it is not ambiguity', v.is_ambiguous, False)
    check('E: it is not UNRESOLVED', v.decision is Decision.UNRESOLVED, False)
    check('E: and it says what failed, not what an authority publishes',
          'getaddrinfo' in v.infrastructure_note, True)


def test_b_end_to_end_two_commissions_reach_ambiguous() -> None:
    """B, through the resolver rather than the decision function alone."""
    rows = [
        ('Zeta Pradesh Public Service Commission',
         'https://zpsc.gov.in/group-i', 'ZPSC Group I 2026 notification. Group I services.'),
        ('Zeta Pradesh Public Service Commission | Notifications',
         'https://zpsc.gov.in/notices', 'Group I examination 2026 apply online.'),
        ('Zephyr Pradesh Public Service Commission',
         'https://zppsc.gov.in/group-i', 'ZPSC Group I 2026 notification. Group I posts.'),
        ('Zephyr Pradesh Public Service Commission | Recruitment',
         'https://zppsc.gov.in/notices', 'Group I examination 2026 apply online.'),
    ]
    v = _with_search(lambda *a, **k: _fake_hits(rows))
    check('B: the resolver reports ambiguity rather than returning a winner',
          v.decision, Decision.AMBIGUOUS_AUTHORITY)
    check('B: both commissions are preserved', len(v.candidates), 2)


def test_d_an_unrelated_authority_never_becomes_the_answer() -> None:
    """D. A real government body that is not this exam's must not be resolved to.

    Here the only pages carrying the exam's words belong to one commission; another
    genuine authority is present in the results but is about something else.
    """
    rows = [
        ('Zeta Pradesh Public Service Commission',
         'https://zpsc.gov.in/group-i', 'ZPSC Group I 2026 notification. Group I services.'),
        ('Zeta Pradesh Public Service Commission | Notices',
         'https://zpsc.gov.in/notices', 'ZPSC Group I 2026 apply online.'),
        ('Department of Roads and Highways',
         'https://roads.gov.in/tenders', 'Tender notice for highway maintenance contracts.'),
    ]
    v = _with_search(lambda *a, **k: _fake_hits(rows))
    check('D: an unrelated authority does not create ambiguity',
          v.decision, Decision.RESOLVED)
    check('D: and is not the one resolved to',
          'roads' in (v.chosen.domain if v.chosen else ''), False)


def main() -> int:
    test_a_single_clear_authority_resolves()
    test_a_body_and_its_own_regional_site_are_one_authority()
    test_a_body_and_its_apply_portal_are_one_authority()
    test_two_real_authorities_sharing_an_acronym_are_ambiguous()
    test_a_large_score_gap_still_does_not_decide()
    test_shared_body_words_alone_never_distinguish()
    test_a_name_that_distinguishes_resolves()
    test_a_name_naming_both_stays_ambiguous()
    test_a_faint_unrelated_site_does_not_create_ambiguity()
    test_the_floor_cannot_break_a_tie_between_two_present_bodies()
    test_no_candidates_is_unresolved_not_ambiguous()
    test_same_body_needs_a_real_overlap()
    test_the_verdict_can_be_audited()
    test_e_a_search_outage_is_infrastructure_not_a_verdict()
    test_b_end_to_end_two_commissions_reach_ambiguous()
    test_d_an_unrelated_authority_never_becomes_the_answer()
    if _FAILURES:
        print(f'{len(_FAILURES)} FAILURE(S):')
        for f in _FAILURES:
            print('  -', f)
        return 1
    print('ambiguity: two real authorities are reported, never voted on')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
