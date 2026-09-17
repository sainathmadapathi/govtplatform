"""Exam name (+ year) -> the authority that conducts it and its official domain.

Nobody tells this module who runs an exam. It searches official domains for the exam's own
name and lets the results vote: the host that carries the most official pages mentioning
that exam, weighted by how well each page's title matches, is the authority. That is why it
works for an exam nobody has written a connector for.

It resolves an *authority*, not a fact about the exam. Everything factual still comes from
reading that authority's documents, and nothing here is allowed to reach `data.ts`.
"""
from __future__ import annotations

import re
from collections import defaultdict
from dataclasses import dataclass, field
from urllib.parse import urlparse

from .search import Hit, SearchUnavailable, search

#: Words that appear in every exam's name and therefore identify nothing.
_GENERIC = {
    'exam', 'exams', 'examination', 'examinations', 'recruitment', 'services', 'service',
    'the', 'of', 'for', 'and', 'in', 'to', 'india', 'indian', 'government', 'govt',
    'post', 'posts', 'officer', 'officers', 'grade', 'level', 'paper', 'online',
    'notification', 'apply', 'application', 'result', 'admit', 'card', 'syllabus',
    # Short words that occur inside longer ones. "non" (from "Non-Technical") matches
    # inside "announcement", which would attach an unrelated notice to the exam.
    'non', 'pre', 'sub', 'all', 'new', 'old', 'per', 'via', 'and', 'any',
}

#: Page-title words that name a *page*, not a body. "SSC Notice Board" is a notice board.
_NOT_AN_AUTHORITY = re.compile(
    r'notice|board of study|result|admit|syllabus|download|portal|home|'
    # Navigation menus concatenate into things that end in "...The Commission" and look
    # like a name. They are a page's chrome, not the body.
    r'about us|historical|perspective|constitutional provision|sitemap|contact',
    re.I)

#: Hosts that mirror government content but are not the authority. Being on this list is
#: not a judgement about them; they simply cannot be cited as the source of a rule.
_AGGREGATORS = {
    'india.gov.in',        # the National Portal links to everyone
    'data.gov.in',
    'pib.gov.in',          # press releases about many authorities
    'egazette.gov.in',
    'archive.org',
}


@dataclass
class Authority:
    name: str
    domain: str
    confidence: float
    #: For a non-government domain, the official page that vouched for it. Empty for a
    #: .gov.in/.nic.in host, which needs no vouching.
    corroborated_by: str = ''
    #: What the decision was made from, so a wrong guess is visible rather than mysterious.
    evidence: list[str] = field(default_factory=list)
    rivals: list[tuple[str, float]] = field(default_factory=list)


@dataclass
class ResolvedExam:
    query: str
    official_name: str
    year: str
    authority: Authority
    #: Official pages that mentioned this exam, for the discovery step to start from.
    seed_urls: list[str] = field(default_factory=list)


def distinctive_words(name: str) -> list[str]:
    return [w for w in re.split(r'[^a-z0-9]+', name.lower())
            if len(w) > 2 and w not in _GENERIC and not w.isdigit()]


def _year_in(text: str) -> str:
    m = re.search(r'\b(20\d{2})\b', text or '')
    return m.group(1) if m else ''


def _authority_name_from(host: str, hits: list[Hit]) -> str:
    """Prefer a name the authority prints about itself over one built from its domain.

    Every candidate is collected and the longest plausible one wins, because the first
    match was "SSC Notice Board" -- a page's name, not the body's. Anything whose words
    describe a page rather than an institution is discarded outright.
    """
    names: list[str] = []
    # Indian bodies come in two shapes and both must be matched: suffix-form ("Staff
    # Selection Commission") and prefix-form ("Institute of Banking Personnel Selection",
    # "Board of Secondary Education"). Matching only the first left IBPS unnamed.
    prefix_rx = re.compile(
        r'\b((?:Institute|Board|Bank|Council|Corporation|Commission|Department|Ministry|Authority)'
        r'\s+of\s+(?:[A-Z][\w&-]*\s*){1,6})')
    for h in hits:
        for m in prefix_rx.finditer(f'{h.title}. {h.content}'):
            cand = ' '.join(m.group(1).split()).rstrip('.,;')
            if not _NOT_AN_AUTHORITY.search(cand) and 3 <= len(cand.split()) <= 8:
                names.append(cand)
        for m in re.finditer(
                # No '.' in the word class: with one, a match ran straight through a
                # sentence boundary and produced "…Commission. Union Public Service Commission".
                r'\b((?:[A-Z][\w&-]*\s+){1,7}'
                r'(?:Commission|Corporation|Authority|Institute|Council|Bank|Ministry|Department|Board)'
                # "Life Insurance Corporation of India" is one name, not "Life Insurance
                # Corporation" plus "Corporation of India"; the tail has to be part of the match.
                r'(?:\s+of\s+(?:[A-Z][\w&-]*\s*){1,4})?)',
                f'{h.title}. {h.content}'):
            cand = ' '.join(m.group(1).split())
            if _NOT_AN_AUTHORITY.search(cand):
                continue
            if 2 <= len(cand.split()) <= 8:
                names.append(cand)
    if names:
        # The most frequently repeated name, then the longest, is the institution.
        by_count: dict[str, int] = {}
        for c in names:
            by_count[c] = by_count.get(c, 0) + 1
        # A candidate wholly contained in another is a fragment of it, not a rival name:
        # "Corporation of India" inside "Life Insurance Corporation of India". Drop the
        # fragments first, then prefer the most frequent and — among those — the shortest,
        # which is what keeps a concatenated navigation menu from winning.
        full = [c for c in by_count
                if not any(c != other and c in other for other in by_count)]
        if full:
            by_count = {c: by_count[c] for c in full}
        return sorted(by_count.items(), key=lambda kv: (-kv[1], len(kv[0])))[0][0]
    root = host.split('.')[0]
    return root.upper() if len(root) <= 6 else root.replace('-', ' ').title()


def _corroborated_hosts(exam_query: str, official_hosts: set[str]) -> dict[str, str]:
    """Non-government hosts that an official page names, mapped to the page that names them.

    IBPS, LIC and SBI conduct exams the requirement lists, and none of them publishes on a
    .gov.in domain. Excluding them would make the engine unable to do what was asked;
    accepting them on their own authority would let any site claim to be a recruiter. The
    middle is corroboration -- an official page has to point at them.
    """
    try:
        wide = search(f'{exam_query} official notification apply', max_results=20,
                      official_only=False)
    except SearchUnavailable:
        return {}
    candidates = {h.host for h in wide
                  if h.trust != 'OFFICIAL' and h.host and h.host not in _AGGREGATORS}
    if not candidates:
        return {}
    corroborated: dict[str, str] = {}
    try:
        official_pages = search(f'{exam_query} official website', max_results=20,
                                official_only=True)
    except SearchUnavailable:
        return {}
    for page in official_pages:
        blob = f'{page.title} {page.content}'.lower()
        for host in candidates:
            if host in blob:
                corroborated.setdefault(host, page.url)
    return corroborated


def resolve(exam_query: str, *, year: str = '', min_confidence: float = 0.34) -> ResolvedExam:
    """Find the conducting authority for an exam, from official sources only.

    Raises `SearchUnavailable` if there is no way to search, and `LookupError` if the
    official web does not point clearly enough at one authority. Both are refusals, not
    fallbacks: naming the wrong authority would attach one body's rules to another's exam,
    which is the failure the whole isolation rule exists to prevent.
    """
    year = year or _year_in(exam_query)
    words = distinctive_words(exam_query)
    if not words:
        raise LookupError(f'"{exam_query}" has no distinctive words to search on.')

    queries = [
        f'{exam_query} official notification',
        f'{exam_query} official website apply online',
    ]
    hits: list[Hit] = []
    for q in queries:
        try:
            hits.extend(search(q, max_results=20, official_only=True))
        except SearchUnavailable:
            raise

    corroboration: dict[str, str] = {}
    if not hits:
        # The authority may simply not use a government domain (IBPS, LIC, SBI). Accept one
        # only if an official page vouches for it.
        corroboration = _corroborated_hosts(exam_query, set())
        if corroboration:
            try:
                wide = search(f'{exam_query} official notification apply', max_results=20,
                              official_only=False)
            except SearchUnavailable:
                wide = []
            hits = [h for h in wide if h.host in corroboration]
    if not hits:
        raise LookupError(
            f'No official page mentions "{exam_query}", and no government page vouches for a '
            f'non-government site that does. Either the name is wrong, or this exam is not '
            f'published online by its authority — GovOS will not source it from a coaching '
            f'site or an aggregator.')

    # Vote: a host scores by how many of the exam's distinctive words its pages carry.
    scores: dict[str, float] = defaultdict(float)
    per_host: dict[str, list[Hit]] = defaultdict(list)
    for h in hits:
        host = h.host
        if host in _AGGREGATORS:
            continue
        hay = f'{h.title} {h.content}'.lower()
        covered = sum(1 for w in words if w in hay)
        if not covered:
            continue
        # A host whose own name echoes the exam ("upsc" in upsc.gov.in) is a strong signal.
        host_bonus = 0.5 * sum(1 for w in words if w in host)
        scores[host] += covered / len(words) + host_bonus
        per_host[host].append(h)

    if not scores:
        # Official pages exist but none is about this exam — the authority likely publishes
        # on its own non-government domain (IBPS, LIC, SBI). Try corroboration before giving
        # up, rather than refusing an exam the requirement explicitly names.
        corroboration = _corroborated_hosts(exam_query, set())
        if corroboration:
            try:
                wide = search(f'{exam_query} official notification apply', max_results=20,
                              official_only=False)
            except SearchUnavailable:
                wide = []
            for h in (x for x in wide if x.host in corroboration):
                hay = f'{h.title} {h.content}'.lower()
                covered = sum(1 for w in words if w in hay)
                if covered:
                    scores[h.host] += covered / len(words) + 0.5 * sum(1 for w in words if w in h.host)
                    per_host[h.host].append(h)
    if not scores:
        raise LookupError(f'Official pages were found for "{exam_query}" but none of them '
                          f'carry its distinctive words, and no government page vouches for a '
                          f'non-government site that does; cannot name an authority.')

    ranked = sorted(scores.items(), key=lambda kv: -kv[1])
    top_host, top_score = ranked[0]
    total = sum(scores.values()) or 1.0
    confidence = top_score / total

    if confidence < min_confidence and len(ranked) > 1:
        raise LookupError(
            f'"{exam_query}" does not point clearly at one authority — '
            f'{", ".join(f"{h} ({s:.2f})" for h, s in ranked[:4])}. '
            f'Name the exam more precisely (include the authority or the year) rather than '
            f'letting the builder pick.')

    top_hits = per_host[top_host]
    # The best title carries the most of the exam's own words (and its year), not the most
    # characters — the longest was a URL fragment, which slugged into
    # "exam-ssc-https-ssc-gov-website-2026".
    def title_score(t: str) -> tuple:
        low = t.lower()
        return (-sum(1 for w in words if w in low),
                0 if (year and year in t) else 1,
                len(t))

    titles = [re.sub(r'\s*[|]\s*[^|]*$', '', h.title).strip()
              for h in top_hits if h.title and not h.title.lower().startswith('http')]
    titles = [t for t in titles if len(t) > 5]
    official_name = min(titles, key=title_score) if titles else exam_query

    authority = Authority(
        name=_authority_name_from(top_host, top_hits),
        domain=f'https://{top_host}',
        confidence=round(confidence, 3),
        corroborated_by=corroboration.get(top_host, ''),
        evidence=[h.url for h in top_hits[:5]],
        rivals=[(h, round(s / total, 3)) for h, s in ranked[1:4]],
    )
    return ResolvedExam(
        query=exam_query,
        official_name=official_name or exam_query,
        year=year or _year_in(official_name),
        authority=authority,
        seed_urls=[h.url for h in top_hits],
    )


def stable_exam_id(resolved: ResolvedExam) -> str:
    """An id derived from the exam's own name, not from a hand-kept table."""
    host_root = urlparse(resolved.authority.domain).hostname or ''
    org = host_root.replace('www.', '').split('.')[0]
    # The query is what the user actually named; the scraped title is a fallback only,
    # because a title can be a navigation crumb or a URL.
    words = distinctive_words(resolved.query) or distinctive_words(resolved.official_name)
    slug = '-'.join(dict.fromkeys(words))[:60].strip('-')
    year = resolved.year or ''
    return f"exam-{org}-{slug}" + (f'-{year}' if year else '')
