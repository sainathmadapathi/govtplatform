"""A name is only identity evidence when the authority is the one who printed it.

The defect: `portal-psc.ap.gov.in` became "Portal PSC", which is the name of no body, and
the ambiguity layer then read "psc" out of it as a word telling one commission apart from
another. It is the part of the address they share. A hostname is a fine way to *find* a
candidate and no way at all to *identify* one.

Every fixture is invented. The behaviour under test is structural, so naming a real
authority in an assertion would prove nothing about any other.

Run: python -m tools.exam_builder.test_names
"""
from __future__ import annotations

from types import SimpleNamespace

from .ambiguity import AuthorityCandidate, Decision, decide, identity_tokens
from .names import NameStatus, resolve_name

_FAILURES: list[str] = []


def check(label: str, got, want) -> None:
    if got != want:
        _FAILURES.append(f'{label}\n     got  {got!r}\n     want {want!r}')


def hit(host: str, title: str, content: str):
    return SimpleNamespace(host=host, title=title, content=content,
                           url=f'https://{host}/page')


# ------------------------------------------------------ the authority's own page
def test_the_authoritys_own_page_gives_a_verified_name() -> None:
    hits = [
        hit('zppsc.gov.in', 'Zephyr Pradesh Public Service Commission',
            'The Zephyr Pradesh Public Service Commission invites applications for Group I.'),
        hit('zppsc.gov.in', 'Notifications | Zephyr Pradesh Public Service Commission',
            'Zephyr Pradesh Public Service Commission notification for Group I 2026.'),
    ]
    n = resolve_name('zppsc.gov.in', hits)
    check('a name on the body’s own domain is VERIFIED',
          n.status, NameStatus.CANONICAL_NAME_VERIFIED)
    check('and it is the body’s name, not the page’s',
          n.value, 'Zephyr Pradesh Public Service Commission')
    check('it cites the page it was read from', n.source_url.startswith('https://zppsc'), True)
    check('and carries a verbatim span', bool(n.evidence and n.evidence.span), True)
    check('so it may be reasoned from', n.is_identity_evidence, True)


def test_a_fetched_home_page_also_verifies() -> None:
    def fetch(url):
        return SimpleNamespace(
            text='Zeta Recruitment Board. Recruitment of clerks. Apply online.',
            url=url)

    n = resolve_name('zrb.gov.in', [], fetch=fetch)
    check('the body’s own site, fetched, is VERIFIED',
          n.status, NameStatus.CANONICAL_NAME_VERIFIED)
    check('with the name it prints', n.value, 'Zeta Recruitment Board')


# ------------------------------------------------------------ domain-only inference
def test_a_name_the_address_corroborates_survives_the_fragment_rule() -> None:
    """Found live, after fetching home pages made names stable.

    The body's own name was harvested and then discarded as a "fragment", because a noisy
    longer string happened to contain it — leaving a navigation menu item to win and be
    labelled VERIFIED. The acronym of the address is the strongest corroboration available
    and must outrank the fragment rule, not lose to it.
    """
    def fetch(url):
        return SimpleNamespace(url=url, text=(
            'Management & Faculty Members Governing Board About The Founders. '
            'Assessment The Zeta Board of Recruitment Services. '
            'Zeta Board of Recruitment Services. Apply online for recruitment.'))

    n = resolve_name('zbrs.gov.in', [], fetch=fetch)
    check('the name whose acronym is the address wins',
          n.value, 'Zeta Board of Recruitment Services')
    check('and a navigation menu item does not',
          'Faculty' in n.value, False)


def test_a_fetched_page_with_no_corroborating_name_stays_inferred() -> None:
    """A whole home page is mostly chrome, and chrome has the shape of a name.

    With nothing agreeing with the address, whatever was scraped is a guess, and must be
    labelled as one rather than badged VERIFIED.
    """
    def fetch(url):
        return SimpleNamespace(url=url, text=(
            'Management & Faculty Members Governing Board. Quick Links Council. '
            'Recruitment notices and candidate corner.'))

    n = resolve_name('zbrs.gov.in', [], fetch=fetch)
    check('an uncorroborated scrape is not VERIFIED',
          n.status, NameStatus.CANONICAL_NAME_INFERRED)
    check('and it is not reasoned from', n.is_identity_evidence, False)


def test_a_hostname_only_name_is_inferred_never_verified() -> None:
    """The exact shape of the live defect."""
    n = resolve_name('portal-psc.zp.gov.in', [])
    check('a name built from the address is INFERRED',
          n.status, NameStatus.CANONICAL_NAME_INFERRED)
    check('it is still shown', n.value, 'Portal Psc')
    check('it cites no page, because no page said it', n.source_url, '')
    check('it carries no evidence span', n.evidence, None)
    check('and it may not be reasoned from', n.is_identity_evidence, False)
    check('the reason says plainly what it is',
          'placeholder' in n.reason, True)


def test_a_name_from_someone_elses_page_is_inferred() -> None:
    """What others call a body is not the body's account of itself."""
    hits = [hit('examnews.example', 'Group I notification out',
                'The Zephyr Pradesh Public Service Commission has released the notice.')]
    n = resolve_name('zppsc.gov.in', hits)
    check('a third party’s wording is INFERRED',
          n.status, NameStatus.CANONICAL_NAME_INFERRED)
    check('the name is still recovered', n.value, 'Zephyr Pradesh Public Service Commission')
    check('but it is not identity evidence', n.is_identity_evidence, False)


def test_nothing_at_all_is_name_unresolved() -> None:
    n = resolve_name('', [])
    check('no name and no address is NAME_UNRESOLVED',
          n.status, NameStatus.NAME_UNRESOLVED)
    check('and nothing is invented', n.value, '')


# -------------------------------------------- an inferred name cannot decide identity
def test_an_inferred_name_contributes_no_identity_tokens() -> None:
    inferred = AuthorityCandidate(domain='portal-psc.zp.gov.in', name='Portal Psc',
                                  score=1.0, name_is_evidence=False)
    verified = AuthorityCandidate(domain='zppsc.gov.in',
                                  name='Zephyr Pradesh Public Service Commission',
                                  score=1.0, name_is_evidence=True)
    check('a guessed name yields nothing to reason from', identity_tokens(inferred), set())
    check('a printed name yields its distinctive words',
          identity_tokens(verified), {'zephyr', 'pradesh'})


def test_a_shared_acronym_in_an_inferred_name_cannot_resolve_ambiguity() -> None:
    """The regression. "PSC" in a hostname must not pick a commission.

    Before, the inferred name "Portal Psc" contributed "psc" as a distinguishing word, so a
    query mentioning PSC would resolve to it — on a word both commissions share, read out
    of an address.
    """
    v = decide('ZPSC PSC Group I 2026', [
        AuthorityCandidate(domain='zpsc.gov.in',
                           name='Zeta Pradesh Public Service Commission',
                           score=0.6, name_is_evidence=True),
        AuthorityCandidate(domain='portal-psc.zp.gov.in', name='Portal Psc',
                           score=0.4, name_is_evidence=False),
    ])
    check('a shared acronym from an address does not decide',
          v.decision, Decision.AMBIGUOUS_AUTHORITY)
    check('and the guessed name offers nothing to be told apart by',
          [c.distinguishing for c in v.candidates if c.domain.startswith('portal')],
          [[]])


def test_two_legitimate_authorities_are_still_ambiguous() -> None:
    v = decide('ZPSC Group I 2026', [
        AuthorityCandidate(domain='zpsc.gov.in',
                           name='Zeta Pradesh Public Service Commission',
                           score=0.6, name_is_evidence=True),
        AuthorityCandidate(domain='zppsc.gov.in',
                           name='Zephyr Pradesh Public Service Commission',
                           score=0.4, name_is_evidence=True),
    ])
    check('two verified names, nothing to choose between them',
          v.decision, Decision.AMBIGUOUS_AUTHORITY)


def test_an_explicit_authority_name_resolves_the_ambiguity() -> None:
    v = decide('Zephyr Pradesh Public Service Commission Group I 2026', [
        AuthorityCandidate(domain='zpsc.gov.in',
                           name='Zeta Pradesh Public Service Commission',
                           score=0.6, name_is_evidence=True),
        AuthorityCandidate(domain='zppsc.gov.in',
                           name='Zephyr Pradesh Public Service Commission',
                           score=0.4, name_is_evidence=True),
    ])
    check('naming the authority resolves it', v.decision, Decision.RESOLVED)
    check('to the one named, not the one ahead on score',
          v.chosen.domain, 'zppsc.gov.in')


def test_an_inferred_name_cannot_merge_two_bodies_either() -> None:
    """Identity works in both directions: a guess must not join bodies, nor split them."""
    v = decide('Zeta Board Clerk 2026', [
        AuthorityCandidate(domain='zrb.gov.in', name='Zeta Recruitment Board',
                           score=0.6, name_is_evidence=True),
        AuthorityCandidate(domain='otherbody.gov.in', name='Otherbody',
                           score=0.4, name_is_evidence=False),
    ])
    check('an unrelated body with a guessed name is not merged in',
          len([c for c in v.candidates if c.absorbed]), 0)


def main() -> int:
    test_the_authoritys_own_page_gives_a_verified_name()
    test_a_fetched_home_page_also_verifies()
    test_a_name_the_address_corroborates_survives_the_fragment_rule()
    test_a_fetched_page_with_no_corroborating_name_stays_inferred()
    test_a_hostname_only_name_is_inferred_never_verified()
    test_a_name_from_someone_elses_page_is_inferred()
    test_nothing_at_all_is_name_unresolved()
    test_an_inferred_name_contributes_no_identity_tokens()
    test_a_shared_acronym_in_an_inferred_name_cannot_resolve_ambiguity()
    test_two_legitimate_authorities_are_still_ambiguous()
    test_an_explicit_authority_name_resolves_the_ambiguity()
    test_an_inferred_name_cannot_merge_two_bodies_either()
    if _FAILURES:
        print(f'{len(_FAILURES)} FAILURE(S):')
        for f in _FAILURES:
            print('  -', f)
        return 1
    print('names: only what an authority prints about itself is identity evidence')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
