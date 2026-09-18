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


class AmbiguousAuthority(RuntimeError):
    """Two or more real authorities answer to this exam's name.

    Carries the full `AuthorityVerdict` -- every candidate, its evidence and what would
    have told them apart -- so a caller can report the ambiguity or ask, rather than
    receiving a winner picked by a score gap. Deliberately not a LookupError: this is a
    finding, not a failure to find.
    """

    def __init__(self, verdict):
        super().__init__(verdict.reason)
        self.verdict = verdict


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

def id_words(name: str) -> list[str]:
    """The tokens that distinguish one exam from another, for naming it.

    Looser than `distinctive_words` in exactly one way: length is not a filter. "PO" and
    "SO" are what separate two IBPS exams, "I" from "II" separates two APPSC ones and "D"
    from "C" separates two RRB ones; dropping them merges records that must never be
    merged. Filler words are excluded by name, as they already were.

    This is safe here and not safe in matching, because an id is *constructed* from a name
    the caller supplied, whereas an alias is *searched for* inside a document, where a
    one-letter token would match everywhere.
    """
    return [w for w in re.split(r'[^a-z0-9]+', name.lower())
            if w and w not in _GENERIC and not w.isdigit()]


def exam_aliases(query: str, official_name: str = '') -> list[str]:
    """Every token that legitimately names this exam, expansion and acronym alike.

    Authorities mix the two freely: the page is titled "Combined Graduate Level
    Examination" and the link beside it says "CGL 2026 Notice". Matching only the words of
    the official name rejected the exam's own documents, and matching only the acronym
    misses the page that spells it out. Both go in the set.

    Acronyms are built from the name the authority prints, never from a table of exams — a
    hand-kept table is the thing this engine exists to avoid.
    """
    words = list(dict.fromkeys(distinctive_words(query) + distinctive_words(official_name)))
    aliases = set(words)

    for source in (official_name, query):
        tokens = distinctive_words(source)
        # "Combined Graduate Level" -> "cgl". Built over runs of 2+ words, and over the run
        # with the leading authority code dropped, since "SSC CGL" acronymises to both.
        for start in (0, 1):
            run = tokens[start:]
            if len(run) >= 2:
                acronym = ''.join(w[0] for w in run)
                if 2 <= len(acronym) <= 6:
                    aliases.add(acronym)
        # An acronym the user typed directly ("CGL", "NTPC", "AAO").
        for raw in re.findall(r'\b[A-Z]{2,6}\b', source or ''):
            aliases.add(raw.lower())

    # Two letters is too little to identify anything; it would match inside other words.
    return sorted(a for a in aliases if len(a) >= 3)


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

        # The decisive signal: an authority's domain is nearly always its own acronym.
        # ssc.gov.in -> "Staff Selection Commission", upsc.gov.in -> "Union Public Service
        # Commission". Without this the winner was "Department of Personnel" for both,
        # because the notices cite DoPT as the rule-making ministry far more often than
        # they name the commission that is actually conducting the exam.
        root = host.split('.')[0].lower()

        def acronym_of(name: str) -> str:
            return ''.join(w[0] for w in re.findall(r'\b[A-Za-z]+\b', name)
                           if w.lower() not in ('of', 'and', 'the', 'for')).lower()

        def rank(item: tuple[str, int]) -> tuple:
            name, count = item
            return (0 if acronym_of(name) == root else 1, -count, len(name))

        return sorted(by_count.items(), key=rank)[0][0]
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
    forced_host = ''
    if not hits:
        # No government page is about this exam. That is routine: IBPS, LIC and SBI do not
        # use government domains, and a search for their exams returns coaching articles
        # whose *text* names the real site even though the site itself is never ranked.
        try:
            wide = search(f'{exam_query} official notification apply online',
                          max_results=20, official_only=False)
        except SearchUnavailable:
            raise
        if wide:
            # An official page that names the site is the strongest corroboration; failing
            # that, the site is made to identify itself before being believed.
            corroboration = _corroborated_hosts(exam_query, set())
            vouched = [h for h in wide if h.host in corroboration]
            if vouched:
                hits = vouched
            else:
                from .officiality import best_official_domain
                best, _tried = best_official_domain(
                    wide, exam_aliases=exam_aliases(exam_query, ''),
                    authority_hint=exam_query)
                if best is not None:
                    forced_host = best.domain.replace('www.', '')
                    corroboration[forced_host] = (
                        best.evidence[0].source_url if best.evidence
                        else f'https://{best.domain}')
                    hits = [h for h in wide if h.host == forced_host] or wide
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
        # Nothing on a government domain is about this exam. The authority may simply not
        # use one -- IBPS, LIC and SBI do not -- and for those a search returns coaching
        # articles only, with the real domain absent from the results but named inside
        # them. Recover it from the text, then make the site identify itself.
        from .officiality import best_official_domain
        try:
            wide = search(f'{exam_query} official notification apply online',
                          max_results=20, official_only=False)
        except SearchUnavailable:
            wide = []
        if wide:
            best, tried = best_official_domain(
                wide, exam_aliases=exam_aliases(exam_query, ''),
                authority_hint=exam_query)
            if best is not None:
                host = best.domain.replace('www.', '')
                per_host[host] = [h for h in wide if h.host == host] or wide[:1]
                scores[host] = 1.0
                corroboration[host] = (best.evidence[0].source_url if best.evidence
                                       else f'https://{best.domain}')
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

    from .ambiguity import AuthorityCandidate, Decision, decide

    if forced_host:
        # The vote is over pages *about* the exam, and here those pages are coaching
        # articles. The authority was established by reading its own site, so it is not put
        # to a popularity contest against the articles that pointed at it.
        scores = defaultdict(float, {forced_host: 1.0})
        per_host.setdefault(forced_host, [])
    ranked = sorted(scores.items(), key=lambda kv: -kv[1])

    # Hand the ranking to the ambiguity layer rather than taking its first row. A body's
    # own regional sites are merged onto it there, so a rival is a rival and not a branch
    # office, and two genuine rivals are never separated by their scores.
    verdict = decide(exam_query, [
        AuthorityCandidate(
            domain=host,
            name=_authority_name_from(host, per_host[host]),
            score=score,
            evidence=[h.url for h in per_host[host][:4]])
        for host, score in ranked])

    if verdict.decision is Decision.AMBIGUOUS_AUTHORITY:
        raise AmbiguousAuthority(verdict)

    top_host = verdict.chosen.domain
    confidence = verdict.chosen.share

    if confidence < min_confidence and len(verdict.candidates) > 1:
        raise LookupError(
            f'"{exam_query}" does not point clearly at one authority — '
            f'{", ".join(f"{c.domain} ({c.score:.2f})" for c in verdict.candidates[:4])}. '
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

    aliases = exam_aliases(exam_query, '')

    def looks_like_a_name(t: str) -> bool:
        # A title is a name, not a sentence. The first live run picked
        # "i.e. https://ssc.gov.in on 21-05-2026) (Website of the ..." because it merely
        # scored least badly among fragments.
        if not t or len(t) < 8 or len(t) > 120:
            return False
        if not t[0].isupper():
            return False
        if re.search(r'https?://|www\.|@', t):
            return False
        if re.match(r'^(i\.e|e\.g|note|click|read|download)\b', t, re.I):
            return False
        # Site chrome, not an exam: "Home", "Welcome to ...", "Official Website".
        if re.match(r'^(home|welcome|index|official website|sitemap|login|main page)\b', t, re.I):
            return False
        # A title must name this exam. Aliases, not the query's raw words: the query says
        # "CGL" while the authority's own title spells out "Combined Graduate Level", and
        # checking only the query's words rejected the very title we want.
        if not any(a in t.lower() for a in aliases):
            return False
        return bool(re.search(r'[A-Za-z]{3}', t))

    # Separators vary (|, ｜, –, —, ·, ::) and so does which side carries the name, so every
    # segment is considered rather than assuming the first. "Home | Staff Selection
    # Commission" survived a strip that only knew the ASCII bar.
    def segments(title: str) -> list[str]:
        parts = re.split(r'\s*[|｜–—·]+\s*|\s+::\s+', title)
        return [p.strip() for p in parts if p.strip()]

    titles = [seg for h in top_hits if h.title for seg in segments(h.title)]
    titles = [t for t in titles if looks_like_a_name(t)]
    # The query is the fallback: the user named the exam, and a bad scrape must not
    # overwrite that with a fragment.
    official_name = min(titles, key=title_score) if titles else exam_query

    authority = Authority(
        name=_authority_name_from(top_host, top_hits),
        domain=f'https://{top_host}',
        confidence=round(confidence, 3),
        corroborated_by=corroboration.get(top_host, ''),
        evidence=[h.url for h in top_hits[:5]],
        # Rivals come from the merged bodies, not the raw host ranking: a body's own
        # regional site is not a rival to it, and listing it as one invites the reader to
        # worry about a disagreement that does not exist.
        rivals=[(c.domain, round(c.share, 3))
                for c in verdict.candidates if c.domain != top_host][:3],
    )
    return ResolvedExam(
        query=exam_query,
        official_name=official_name or exam_query,
        year=year or _year_in(official_name),
        authority=authority,
        seed_urls=[h.url for h in top_hits],
    )


def resolve_authority(exam_query: str, *, year: str = '', **kw):
    """Resolve, returning the outcome rather than raising it.

    Four outcomes, and the point of the function is that they stay four:

        RESOLVED                one authority, with the exam attached
        AMBIGUOUS_AUTHORITY     several real authorities; the name does not choose
        INFRASTRUCTURE_FAILURE  we could not look; says nothing about any authority
        UNRESOLVED              we looked, and nothing published by an authority matched

    Collapsing the middle two into the last would be the same mistake the field states
    already guard against: reporting our own outage, or our own uncertainty, as a fact
    about the world.
    """
    from .ambiguity import AuthorityVerdict, Decision

    try:
        resolved = resolve(exam_query, year=year, **kw)
    except AmbiguousAuthority as exc:
        return exc.verdict
    except SearchUnavailable as exc:
        return AuthorityVerdict(
            Decision.INFRASTRUCTURE_FAILURE, chosen=None, candidates=[],
            reason='could not search, so no authority was assessed either way',
            infrastructure_note=str(exc))
    except LookupError as exc:
        return AuthorityVerdict(Decision.UNRESOLVED, chosen=None, candidates=[],
                                reason=str(exc))

    from .ambiguity import AuthorityCandidate
    chosen = AuthorityCandidate(
        domain=resolved.authority.domain,
        name=resolved.authority.name,
        score=resolved.authority.confidence,
        evidence=list(resolved.authority.evidence))
    chosen._share = resolved.authority.confidence
    verdict = AuthorityVerdict(Decision.RESOLVED, chosen=chosen, candidates=[chosen],
                               reason='one authority')
    verdict.resolved = resolved
    return verdict


def stable_exam_id(resolved: ResolvedExam) -> str:
    """An id derived from the exam's own name, not from a hand-kept table."""
    host_root = urlparse(resolved.authority.domain).hostname or ''
    org = host_root.replace('www.', '').split('.')[0]
    # The query is what the user actually named; the scraped title is a fallback only,
    # because a title can be a navigation crumb or a URL.
    # id_words, not distinctive_words: "IBPS PO" and "IBPS SO" are one id under the
    # latter, and they are two exams.
    words = id_words(resolved.query) or id_words(resolved.official_name)
    slug = '-'.join(dict.fromkeys(words))[:60].strip('-')
    year = resolved.year or ''
    return f"exam-{org}-{slug}" + (f'-{year}' if year else '')
