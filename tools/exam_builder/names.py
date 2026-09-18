"""What an authority is called, and how well we actually know it.

A hostname is a fine way to *find* a candidate and a poor way to *identify* one.
`portal-psc.ap.gov.in` became "Portal PSC", which is not the name of any body; it then
travelled onward as though it were the commission's own name, and the ambiguity layer read
"psc" out of it as a word that told one commission apart from another. It tells nothing
apart. It is the part of the address that both of them share.

So a name now arrives with its provenance attached, and the three cases are kept apart:

    CANONICAL_NAME_VERIFIED   the authority prints this about itself, and the span is
                              quoted from its own page
    CANONICAL_NAME_INFERRED   a usable label, but assembled by us -- read off third-party
                              pages, or built from the address
    NAME_UNRESOLVED           we have no name, and will not invent one

Only a VERIFIED name is identity evidence. An INFERRED one may be displayed, and may not be
used to decide that two bodies are the same, or that they are different, or which of them
the caller meant. That restraint is the whole point: an inferred name is a guess, and a
guess must not be allowed to settle a question about who conducts an examination.

Nothing here is tuned to any authority, and no score is computed -- this module reports
where a name came from, it does not rank anything.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum

from .evidence import Evidence, EvidenceStatus, normalise_ws

#: Page chrome that names a page rather than a body: "SSC Notice Board" is a notice board.
_NOT_AN_AUTHORITY = re.compile(
    r'notice|board of study|result|admit|syllabus|download|portal|home|'
    r'welcome|sitemap|login|main page|click|read more', re.I)

#: Indian bodies come in two shapes and both must be matched: suffix-form ("Staff Selection
#: Commission") and prefix-form ("Institute of Banking Personnel Selection").
_PREFIX_FORM = re.compile(
    r'\b((?:Institute|Board|Bank|Council|Corporation|Commission|Department|Ministry|Authority)'
    r'\s+of\s+(?:[A-Z][\w&-]*\s*){1,6})')

_SUFFIX_FORM = re.compile(
    # No '.' in the word class: with one, a match ran straight through a sentence boundary
    # and produced "...Commission. Union Public Service Commission".
    r'\b((?:[A-Z][\w&-]*\s+){1,7}'
    r'(?:Commission|Corporation|Authority|Institute|Council|Bank|Ministry|Department|Board)'
    # "Life Insurance Corporation of India" is one name, not "Life Insurance Corporation"
    # plus "Corporation of India"; the tail has to be part of the match.
    r'(?:\s+of\s+(?:[A-Z][\w&-]*\s*){1,4})?)')


class NameStatus(str, Enum):
    CANONICAL_NAME_VERIFIED = 'CANONICAL_NAME_VERIFIED'
    CANONICAL_NAME_INFERRED = 'CANONICAL_NAME_INFERRED'
    NAME_UNRESOLVED = 'NAME_UNRESOLVED'


@dataclass
class AuthorityName:
    value: str
    status: NameStatus
    #: The page the name was read from. Empty when it was built from the address.
    source_url: str = ''
    #: A verbatim span from that page, present only for a VERIFIED name.
    evidence: Evidence | None = None
    reason: str = ''

    @property
    def is_identity_evidence(self) -> bool:
        """May this name be used to decide who an authority is?

        Only when the authority itself printed it. Everything else is a label we made.
        """
        return self.status is NameStatus.CANONICAL_NAME_VERIFIED

    def __str__(self) -> str:
        return self.value


# ------------------------------------------------------------------ harvesting
#: Words that sit in front of a body's name without being part of it. A page heading reads
#: "Chairman, The Zeta Commission"; the body is called "Zeta Commission". Live, this left an
#: authority named "Chairman The Arunachal Pradesh Public Service Commission".
_LEADING_NOISE = re.compile(
    r"^(?:the|office|chairman|chairperson|secretary|president|director|member|"
    r"hon'?ble|shri|smt|dr|prof|welcome|to|of)\b[\s,.:-]*", re.I)


def _strip_leading_noise(name: str) -> str:
    """Peel titles and articles off the front, while a name remains underneath."""
    prev = None
    while prev != name:
        prev = name
        stripped = _LEADING_NOISE.sub('', name).strip()
        # Never strip down to something that is no longer a name.
        if len(stripped.split()) >= 2:
            name = stripped
    return name


def _harvest(hits) -> list[str]:
    """Every string in these pages that reads like the name of a body."""
    found: list[str] = []
    for h in hits:
        blob = f'{getattr(h, "title", "")}. {getattr(h, "content", "")}'
        for m in _PREFIX_FORM.finditer(blob):
            cand = _strip_leading_noise(' '.join(m.group(1).split()).rstrip('.,;'))
            if not _NOT_AN_AUTHORITY.search(cand) and 3 <= len(cand.split()) <= 8:
                found.append(cand)
        for m in _SUFFIX_FORM.finditer(blob):
            cand = _strip_leading_noise(' '.join(m.group(1).split()))
            if _NOT_AN_AUTHORITY.search(cand):
                continue
            if 2 <= len(cand.split()) <= 8:
                found.append(cand)
    return found


def _acronym_of(name: str) -> str:
    return ''.join(w[0] for w in re.findall(r'\b[A-Za-z]+\b', name)
                   if w.lower() not in ('of', 'and', 'the', 'for')).lower()


def _matches_address(name: str, host: str) -> bool:
    """Does this name acronymise to the address the body publishes on?

    An authority's domain is nearly always its own initials, and the address is the one
    part of a site the body chose for itself. It corroborates a name without being one.
    """
    root = (host or '').split('.')[0].lower()
    return bool(root) and _acronym_of(name) == root


def _pick(names: list[str], host: str) -> str:
    """The institution among the candidates."""
    by_count: dict[str, int] = {}
    for c in names:
        by_count[c] = by_count.get(c, 0) + 1

    # A name the address corroborates is the body's own, and is settled here -- before the
    # fragment rule below, which would otherwise discard it. Live, "Institute of Banking
    # Personnel Selection" was dropped as a fragment of a stray "Assessment The Institute of
    # Banking Personnel Selection", leaving a navigation menu item to win.
    endorsed = [c for c in by_count if _matches_address(c, host)]
    if endorsed:
        return sorted(endorsed, key=lambda c: (-by_count[c], len(c)))[0]

    # A candidate wholly contained in another is a fragment of it, not a rival name:
    # "Corporation of India" inside "Life Insurance Corporation of India".
    full = [c for c in by_count if not any(c != other and c in other for other in by_count)]
    if full:
        by_count = {c: by_count[c] for c in full}

    # Without the address signal the winner was "Department of Personnel" for two different
    # commissions, because notices cite the rule-making ministry far more often than the
    # body conducting the exam.
    def rank(item: tuple[str, int]) -> tuple:
        name, count = item
        return (-count, len(name))

    return sorted(by_count.items(), key=rank)[0][0]


def _label_from_host(host: str) -> str:
    root = (host or '').split('.')[0]
    if not root or len(root) < 2 or root.isdigit():
        return ''
    return root.upper() if len(root) <= 6 else root.replace('-', ' ').title()


def _is_own_page(hit, host: str) -> bool:
    hit_host = (getattr(hit, 'host', '') or '').lower().replace('www.', '')
    return bool(host) and hit_host == host.lower().replace('www.', '')


# ------------------------------------------------------------------ the resolver
def resolve_name(host: str, hits, *, fetch=None) -> AuthorityName:
    """Name this authority, and say how the name was arrived at.

    Preference order, and it is a preference about *provenance* rather than about quality:

        1. a name printed on the authority's own pages          -> VERIFIED
        2. a name printed on somebody else's pages              -> INFERRED
        3. a label built from the address                       -> INFERRED
        4. nothing                                              -> NAME_UNRESOLVED

    Steps 2 and 3 share a status deliberately. Both are us describing the body rather than
    the body describing itself, and the distinction that matters downstream is exactly
    that one.
    """
    own = [h for h in (hits or []) if _is_own_page(h, host)]

    # 1. The authority's own pages.
    names = _harvest(own)
    if names:
        chosen = _pick(names, host)
        page = next((h for h in own
                     if chosen in f'{getattr(h, "title", "")}. {getattr(h, "content", "")}'),
                    own[0])
        text = normalise_ws(f'{getattr(page, "title", "")}. {getattr(page, "content", "")}')
        ev = Evidence(span=chosen, source_url=getattr(page, 'url', ''),
                      document_title=getattr(page, 'title', '') or host,
                      reading=f'{host} calls itself {chosen}')
        ev.verify(text)
        if ev.status is EvidenceStatus.VERIFIED:
            return AuthorityName(
                value=chosen, status=NameStatus.CANONICAL_NAME_VERIFIED,
                source_url=getattr(page, 'url', ''), evidence=ev,
                reason='read from a page on the authority’s own domain')

    # 2. The authority's own site, fetched, when the caller supplied a way to.
    if fetch is not None and host:
        page = fetch(f'https://{host}')
        text = normalise_ws(getattr(page, 'text', '') or '') if page is not None else ''
        if text:
            class _Page:                      # harvesting wants title/content
                title = ''
                content = text
                url = f'https://{host}'
            names = _harvest([_Page()])
            # A home page is mostly navigation, and chrome has the shape of a name. Here,
            # unlike a search snippet about the exam, the address must agree -- otherwise
            # this is a guess, and it goes on to be labelled as one.
            names = [x for x in names if _matches_address(x, host)]
            if names:
                chosen = _pick(names, host)
                ev = Evidence(span=chosen, source_url=f'https://{host}',
                              document_title=f'{host} (home)',
                              reading=f'{host} calls itself {chosen}')
                ev.verify(text)
                if ev.status is EvidenceStatus.VERIFIED:
                    return AuthorityName(
                        value=chosen, status=NameStatus.CANONICAL_NAME_VERIFIED,
                        source_url=f'https://{host}', evidence=ev,
                        reason='read from the authority’s own home page')

    # 3. Somebody else's pages. Useful, and not the body speaking.
    others = [h for h in (hits or []) if not _is_own_page(h, host)]
    names = _harvest(others)
    if names:
        chosen = _pick(names, host)
        page = next((h for h in others
                     if chosen in f'{getattr(h, "title", "")}. {getattr(h, "content", "")}'),
                    others[0])
        return AuthorityName(
            value=chosen, status=NameStatus.CANONICAL_NAME_INFERRED,
            source_url=getattr(page, 'url', ''),
            reason='read from a page the authority does not control, so it is what others '
                   'call this body rather than what it calls itself')

    # 4. The address. A label, never an identity.
    label = _label_from_host(host)
    if label:
        return AuthorityName(
            value=label, status=NameStatus.CANONICAL_NAME_INFERRED,
            reason=f'assembled from the address "{host}" because no page named this body; '
                   f'it is a placeholder for display and carries no evidence about who '
                   f'this authority is')

    return AuthorityName(value='', status=NameStatus.NAME_UNRESOLVED,
                         reason='no page named this body and its address yielded nothing')
