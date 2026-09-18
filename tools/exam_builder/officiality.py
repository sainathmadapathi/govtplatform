"""Establishing that a domain is an authority's own — by reading it, not by trusting a ranking.

Search is how candidates are *found*; it is never why they are believed. For IBPS and LIC a
search for the exam plus "official notification" returns nothing but coaching sites, and the
authorities' own domains — ibps.in, licindia.in — do not appear in the results at all. A
resolver that waits for an official-looking domain to be ranked will never resolve them.

But those coaching pages do something useful: they tell candidates where to apply. So the
domains are recoverable from the *text* of the results even when they are absent from the
results themselves. Recovering a name is not the same as believing it, so every candidate is
then fetched and asked to identify itself, and only a site whose own pages name the
authority and the exam is accepted.

    search           -> candidate domains (from result text, not from ranking)
    fetch the site   -> does it name this authority and this exam?
    corroboration    -> does an independent page point at it?
    -> OFFICIAL

Nothing here names a domain, an authority or an exam. A hard-coded `if 'ibps.in'` would
solve today's two failures and none of the hundreds behind them.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field as dc_field
from urllib.parse import urlparse

from .evidence import Evidence, EvidenceStatus, normalise_ws
from .sources_compat import safe_load_html

#: A bare domain written in running text: "apply online at ibps.in", "visit licindia.in".
_BARE_DOMAIN = re.compile(
    r'\b((?:[a-z0-9][a-z0-9-]{1,62}\.)+(?:in|org|com|net|co\.in|gov\.in|nic\.in))\b', re.I)

#: Hosts that appear in every recruitment article and identify no authority.
_NEVER_AN_AUTHORITY = frozenset({
    'youtube.com', 'facebook.com', 'twitter.com', 'x.com', 'instagram.com',
    'telegram.me', 't.me', 'whatsapp.com', 'linkedin.com', 'google.com',
    'wikipedia.org', 'blogspot.com', 'wordpress.com', 'amazon.in', 'play.google.com',
    'apple.com', 'adobe.com', 'gmail.com', 'archive.org',
})

#: How a third party writes *about* a recruitment process it does not run. An authority
#: invites applications; a coaching business sells preparation for them.
#:
#: The cues have to be the ones only a *seller* uses, which is narrower than it first looks.
#: An earlier, broader set rejected both real authorities it was written to admit: IBPS
#: publishes its own candidate "Mock Test" and, being an institute, lists "Faculty Members";
#: LIC runs an "Agent Mock Test Portal" and a "Join Our Team" careers page. Practising and
#: recruiting are things an authority genuinely does. Selling a course is not.
#:
#: Nothing here names an exam, an authority or a company -- this is posture, not identity.
_THIRD_PARTY_POSTURE = (
    re.compile(r'\bcoaching\b', re.I),
    re.compile(r'\btest\s*series\b', re.I),
    re.compile(r'\bstudy\s*material\b', re.I),
    re.compile(r'\b(live|online|recorded)\s*(classes|lectures?)\b', re.I),
    re.compile(r'\b(our|new)\s+batch\w*\b', re.I),
    re.compile(r'\benroll\w*\s+(now|today)\b', re.I),
    re.compile(r'\bcrack\s+(the\s+)?\w+\b', re.I),
    re.compile(r'\b(tips|tricks)\s+(and|&)\s+(tricks|tips)\b', re.I),
    re.compile(r'\b(best|top)\s+(online\s+)?(coaching|institute|app|platform)\b', re.I),
    re.compile(r'\bfree\s+(pdf|download|mock)\b', re.I),
)

#: Words a recruiting body's own site says about itself.
_SELF_DESCRIPTION = re.compile(
    r'\b(recruitment|examination|notification|advertisement|career|vacanc\w*|'
    r'apply\s*online|candidate|admit\s*card|corporation|commission|institute|board|'
    r'ministry|department|authority|bank)\b', re.I)


@dataclass
class OfficialityCheck:
    domain: str
    is_official: bool
    confidence: float = 0.0
    evidence: list[Evidence] = dc_field(default_factory=list)
    reasons: list[str] = dc_field(default_factory=list)


def candidate_domains(hits, *, exclude_hosts: set[str] | None = None) -> list[str]:
    """Domains a set of search results *mentions*, most-mentioned first.

    The domain an article tells its readers to apply on is a far better signal than the
    domain the article is hosted on, and it survives the case where no official page is
    ranked at all.
    """
    exclude = {h.lower() for h in (exclude_hosts or set())} | _NEVER_AN_AUTHORITY
    counts: dict[str, int] = {}
    for h in hits:
        blob = f'{h.title} {h.content}'
        host_of_hit = (getattr(h, 'host', '') or '').lower()
        for m in _BARE_DOMAIN.finditer(blob):
            dom = m.group(1).lower().strip('.')
            if dom in exclude or dom == host_of_hit:
                continue
            if dom.count('.') > 3 or len(dom) < 5:
                continue
            counts[dom] = counts.get(dom, 0) + 1
    return [d for d, _ in sorted(counts.items(), key=lambda kv: -kv[1])]


def _name_tokens(authority_hint: str) -> set[str]:
    return {w for w in re.split(r'[^a-z]+', (authority_hint or '').lower()) if len(w) > 2}


def _says(text: str, phrase: str) -> bool:
    """Whole words only. "bps" lives inside "ibps", and is also how a news site writes
    basis points. Either match would be an accident, not an identification.
    """
    if not phrase:
        return False
    pattern = r'\b' + r'[\s\-]*'.join(re.escape(w) for w in phrase.split()) + r'\b'
    return re.search(pattern, text, re.I) is not None


def _full_name_of(authority_hint: str) -> str:
    """The authority's printed name, when the caller gave one rather than a bare query.

    Two or more substantial words is a name ("Institute of Banking Personnel
    Selection"); one word is an acronym or a search string, and identifies nobody by
    itself.
    """
    words = [w for w in re.split(r'[^A-Za-z]+', authority_hint or '') if len(w) > 2]
    return ' '.join(words) if len(words) >= 2 else ''


def verify_domain(domain: str, *, exam_aliases: list[str], authority_hint: str = '',
                  fetch=safe_load_html) -> OfficialityCheck:
    """Ask the site itself whether it is the authority.

    A site is accepted when its own pages describe recruitment or examinations *and* name
    this exam or this authority. Being mentioned by a coaching article is what got it into
    the shortlist; it is not what gets it accepted.
    """
    url = domain if domain.startswith('http') else f'https://{domain}'
    page = fetch(url)
    if page is None:
        return OfficialityCheck(domain, False, reasons=[
            f'{domain} could not be fetched, so it could not identify itself; this is an '
            f'infrastructure outcome, not a judgement that the site is unofficial'])

    text = normalise_ws(getattr(page, 'text', '') or '')
    if not text:
        return OfficialityCheck(domain, False,
                                reasons=[f'{domain} returned no readable text'])

    low = text.lower()
    reasons: list[str] = []
    evidence: list[Evidence] = []
    score = 0.0

    if _SELF_DESCRIPTION.search(low):
        score += 0.4
        reasons.append('the site describes recruitment or examinations')

    # Word boundaries, not substrings: "bps" lives inside "ibps" and is also how a news
    # site writes basis points.
    alias_hits = [a for a in exam_aliases if _says(low, a)]
    if alias_hits:
        score += 0.4
        reasons.append(f'the site names this exam ({", ".join(alias_hits[:3])})')
        m = re.search(r'[^.]{0,110}' + re.escape(alias_hits[0]) + r'[^.]{0,110}', low)
        if m:
            ev = Evidence(span=normalise_ws(text[m.start():m.end()]), source_url=url,
                          document_title=f'{domain} (home)',
                          reading=f'{domain} names {alias_hits[0]}')
            ev.verify(text)
            if ev.status is EvidenceStatus.VERIFIED:
                evidence.append(ev)

    hint_tokens = _name_tokens(authority_hint)
    if hint_tokens and len(hint_tokens & set(re.split(r'[^a-z]+', low))) >= 2:
        score += 0.3
        reasons.append('the site names the authority the search pointed at')

    # The domain's own label echoing the exam's short form. A site does not get to choose
    # what a reporter calls it, but it does choose its own address, so this is the one
    # signal a third party cannot borrow by writing about the exam.
    root = domain.split('.')[0].lower()
    label_echo = any(a == root or (len(a) >= 3 and a in root) for a in exam_aliases)
    if label_echo:
        score += 0.2
        reasons.append(f'the domain label "{root}" echoes this exam’s name')

    full_name = _full_name_of(authority_hint)
    names_itself = bool(full_name) and _says(low, full_name)
    if names_itself:
        score += 0.3
        reasons.append(f'the site prints the authority’s full name ("{full_name}")')

    # A third party writing about the exam matches every positive signal above, because
    # describing the exam is its product. Each distinct posture cue is evidence that this
    # page is *about* the process rather than issued by whoever runs it.
    # Two cues, not one: a single stray phrase on a large site is noise, and a seller's
    # posture is never expressed only once.
    posture = [pat.pattern for pat in _THIRD_PARTY_POSTURE if pat.search(text)]
    if len(posture) >= 2:
        penalty = min(0.6, 0.3 * len(posture))
        score -= penalty
        reasons.append(
            f'the page sells preparation rather than conducting the process '
            f'({len(posture)} such cue(s)), so it reads as a third party writing about '
            f'this exam, not as the body that runs it')

    # Scoring alone is not enough, because a news report and a rival authority can both
    # accumulate score by sharing ordinary words with the authority's name. One of the two
    # signals that a third party cannot produce must be present: the authority's full
    # printed name, or an address that is the authority's own short form.
    identifies_itself = names_itself or label_echo
    is_official = score >= 0.7 and bool(alias_hits) and identifies_itself
    if not is_official:
        if not identifies_itself:
            reasons.append('the site neither prints the authority’s full name nor uses its '
                           'short form as its address, so sharing words with the exam’s '
                           'name is all it does — that is what a report about the exam '
                           'looks like, not the body that runs it')
        else:
            reasons.append('not enough of the site’s own content identifies it as the '
                           'conducting authority')
    return OfficialityCheck(domain=domain, is_official=is_official,
                            confidence=round(min(1.0, score), 3),
                            evidence=evidence, reasons=reasons)


def best_official_domain(hits, *, exam_aliases: list[str], authority_hint: str = '',
                         limit: int = 6, fetch=safe_load_html
                         ) -> tuple[OfficialityCheck | None, list[OfficialityCheck]]:
    """The best self-identifying domain among those the results mention."""
    tried: list[OfficialityCheck] = []
    for dom in candidate_domains(hits)[:limit]:
        check = verify_domain(dom, exam_aliases=exam_aliases,
                              authority_hint=authority_hint, fetch=fetch)
        tried.append(check)
        if check.is_official:
            return check, tried
    return None, tried
