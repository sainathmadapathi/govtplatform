"""A domain is official because it says so about itself, not because it ends in .gov.in.

IBPS, LIC and SBI conduct some of the largest recruitment examinations in the country and
none of them uses a government domain. A resolver that treats the suffix as the test cannot
reach them; one that treats search ranking as the test cannot either, because a search for
those exams returns coaching articles and nothing else.

So the test here is the one the resolver actually applies: the site is fetched and asked to
identify itself. The important cases are the *rejections* — a coaching site that talks about
the same exam all day long must not pass, or the check would be decoration.

Run: python -m tools.exam_builder.test_officiality
"""
from __future__ import annotations

from types import SimpleNamespace

from .officiality import best_official_domain, candidate_domains, verify_domain
from .resolve import exam_aliases

_FAILURES: list[str] = []


def check(label: str, got, want) -> None:
    if got != want:
        _FAILURES.append(f'{label}\n     got  {got!r}\n     want {want!r}')


def hit(host: str, title: str, content: str):
    return SimpleNamespace(host=host, title=title, content=content, url=f'https://{host}/x')


# A realistic shape of results: every one is a coaching site, and the authority's own domain
# appears only inside their text. This is what the live search actually returned.
COACHING_HITS = [
    hit('testbook.com', 'IBPS PO 2026 Notification Out',
        'The Institute of Banking Personnel Selection has released the IBPS PO notification. '
        'Candidates can apply online at ibps.in before the last date.'),
    hit('guidely.in', 'IBPS PO Apply Online',
        'Visit the official website ibps.in to register for the Probationary Officer post.'),
    hit('mahendras.org', 'IBPS PO Exam Pattern',
        'Download the notification PDF from ibps.in and check youtube.com for our videos.'),
]

AUTHORITY_HOME = """
Institute of Banking Personnel Selection. Recruitment of Probationary Officers /
Management Trainees. IBPS PO CRP XVI. Common Recruitment Process. Apply Online.
Candidates may download the admit card from this website.
"""

COACHING_HOME = """
Testbook — India's best online coaching for IBPS PO, SSC CGL and Railways. Live classes,
mock tests and study material. Join our IBPS PO batch today and crack the examination.
"""

PARKED_HOME = 'This domain is for sale. Buy this premium domain name today.'


def fake_fetch(pages: dict[str, str]):
    def fetch(url: str):
        for host, body in pages.items():
            if host in url:
                return SimpleNamespace(text=body, url=url)
        return None
    return fetch


IBPS_ALIASES = exam_aliases('IBPS PO 2026', 'Institute of Banking Personnel Selection')


# ------------------------------------------------------------------------------ tests
def test_the_authority_is_recovered_from_result_text() -> None:
    doms = candidate_domains(COACHING_HITS)
    check('the domain the articles point at is found', 'ibps.in' in doms, True)
    check('and it is the most-mentioned one', doms[0], 'ibps.in')
    check('the hosting coaching sites are not proposed as the authority',
          [d for d in doms if d in ('testbook.com', 'guidely.in', 'mahendras.org')], [])
    check('and neither is a social platform', 'youtube.com' in doms, False)


def test_a_non_government_authority_is_accepted_on_its_own_content() -> None:
    v = verify_domain('ibps.in', exam_aliases=IBPS_ALIASES,
                      authority_hint='Institute of Banking Personnel Selection',
                      fetch=fake_fetch({'ibps.in': AUTHORITY_HOME}))
    check('a .in authority is accepted', v.is_official, True)
    check('with the confidence stated', v.confidence >= 0.7, True)
    check('and a verbatim span to show for it',
          bool(v.evidence and v.evidence[0].span), True)


def test_a_coaching_site_about_the_same_exam_is_rejected() -> None:
    """The deliberately incorrect domain. It names the exam constantly — and must still fail."""
    v = verify_domain('testbook.com', exam_aliases=IBPS_ALIASES,
                      authority_hint='Institute of Banking Personnel Selection',
                      fetch=fake_fetch({'testbook.com': COACHING_HOME}))
    check('a coaching site is not the authority', v.is_official, False)
    check('and the refusal is explained',
          any('conducting authority' in r for r in v.reasons), True)


def test_an_unreachable_domain_is_not_declared_unofficial() -> None:
    v = verify_domain('ibps.in', exam_aliases=IBPS_ALIASES,
                      fetch=fake_fetch({}))
    check('an unfetchable site is not accepted', v.is_official, False)
    check('but the reason names our outage, not their status',
          any('infrastructure outcome' in r for r in v.reasons), True)


def test_shortlisting_walks_past_the_failures_to_the_authority() -> None:
    # The parked domain is mentioned more often than the real one, so it is shortlisted
    # first. Being named a lot is what gets a domain looked at; it is never what gets it
    # believed.
    noise = [hit('blogspot-mirror.in', 'IBPS PO', 'parkeddomain.in parkeddomain.in')
             for _ in range(3)]
    hits = noise + COACHING_HITS
    best, tried = best_official_domain(
        hits, exam_aliases=IBPS_ALIASES,
        authority_hint='Institute of Banking Personnel Selection',
        fetch=fake_fetch({'parkeddomain.in': PARKED_HOME, 'ibps.in': AUTHORITY_HOME}))
    check('the authority is reached', best.domain if best else None, 'ibps.in')
    check('and the domains it walked past are reported',
          any(t.domain == 'parkeddomain.in' and not t.is_official for t in tried), True)


def test_resolution_is_deterministic_over_result_order() -> None:
    """Re-ranking the same results must not change which domain is chosen."""
    fetch = fake_fetch({'ibps.in': AUTHORITY_HOME, 'testbook.com': COACHING_HOME})
    forward, _ = best_official_domain(COACHING_HITS, exam_aliases=IBPS_ALIASES,
                                      authority_hint='Institute of Banking Personnel Selection',
                                      fetch=fetch)
    reverse, _ = best_official_domain(list(reversed(COACHING_HITS)),
                                      exam_aliases=IBPS_ALIASES,
                                      authority_hint='Institute of Banking Personnel Selection',
                                      fetch=fetch)
    check('search ranking does not decide the authority',
          forward.domain if forward else None, reverse.domain if reverse else None)


def test_nothing_here_is_keyed_to_a_particular_authority() -> None:
    """The same code, an unrelated authority, no edit: an insurer instead of a bank."""
    lic_hits = [
        hit('careerpower.in', 'LIC AAO 2027 Notification',
            'LIC AAO recruitment 2027. Apply online at licindia.in for Assistant '
            'Administrative Officer.'),
        hit('adda247.com', 'LIC AAO Apply Online',
            'The official website is licindia.in. Download the notification PDF.'),
    ]
    lic_home = """
    Life Insurance Corporation of India. Careers. Recruitment of Assistant Administrative
    Officer (AAO). Notification and Apply Online. Candidate login.
    """
    best, _ = best_official_domain(
        lic_hits, exam_aliases=exam_aliases('LIC AAO 2027', 'Life Insurance Corporation of India'),
        authority_hint='Life Insurance Corporation of India',
        fetch=fake_fetch({'licindia.in': lic_home}))
    check('a second non-government authority resolves with no new code',
          best.domain if best else None, 'licindia.in')


def main() -> int:
    test_the_authority_is_recovered_from_result_text()
    test_a_non_government_authority_is_accepted_on_its_own_content()
    test_a_coaching_site_about_the_same_exam_is_rejected()
    test_an_unreachable_domain_is_not_declared_unofficial()
    test_shortlisting_walks_past_the_failures_to_the_authority()
    test_resolution_is_deterministic_over_result_order()
    test_nothing_here_is_keyed_to_a_particular_authority()
    if _FAILURES:
        print(f'{len(_FAILURES)} FAILURE(S):')
        for f in _FAILURES:
            print('  -', f)
        return 1
    print('officiality: a site is believed because it identifies itself')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
