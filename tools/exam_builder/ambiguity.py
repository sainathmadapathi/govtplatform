"""When two real authorities both answer to the name, say so instead of voting.

Live, "APPSC Group I 2026" produced Arunachal Pradesh Public Service Commission at 0.60 and
Andhra Pradesh Public Service Commission at 0.40, and the resolver took the 0.60. Both are
real commissions, both run a Group I examination, and the acronym is genuinely shared. The
0.20 that separated them was a property of that afternoon's search results, not evidence
about which commission the candidate meant — and a candidate sent to the wrong state's
notification is worse off than one told the name was ambiguous.

So the margin never decides. Three questions decide, in order:

    1. Are these actually two bodies, or one body and its own regional arm or portal?
    2. Is each of them plausibly present in the evidence at all?
    3. Does the name the caller supplied distinguish between the ones that remain?

Only the third can pick a winner. If two distinct bodies are both plausible and the supplied
name carries nothing that tells them apart, the answer is AMBIGUOUS_AUTHORITY — which is a
result, with every candidate and its evidence preserved for audit, and never a failure.

Nothing here names an authority, an exam, a state or a domain. The distinctions are drawn
from the names the authorities print about themselves.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum

#: Words that appear in the name of almost every public body and so distinguish none of
#: them. "Public Service Commission" is what two rival commissions have in common, not what
#: separates them. Structural only -- no authority, exam, place or domain is named.
_SHARED_BODY_WORDS = frozenset({
    'public', 'service', 'services', 'commission', 'commissions', 'board', 'boards',
    'authority', 'authorities', 'department', 'departments', 'ministry', 'bureau',
    'institute', 'institution', 'corporation', 'council', 'committee', 'office',
    'government', 'govt', 'state', 'central', 'national', 'india', 'indian', 'union',
    'recruitment', 'selection', 'examination', 'examinations', 'exam', 'exams',
    'staff', 'personnel', 'official', 'website', 'portal', 'home', 'the', 'and', 'of',
    'for', 'chairman', 'secretary', 'member', 'members',
})

#: A body carrying less than this share of the evidence is a stray mention, not a rival
#: claim. This is a floor for *presence*, never a margin for *preference*: it can drop a
#: candidate nothing points at, and it can never break a tie between two that are present.
PLAUSIBLE_SHARE = 0.25


class Decision(str, Enum):
    RESOLVED = 'RESOLVED'
    AMBIGUOUS_AUTHORITY = 'AMBIGUOUS_AUTHORITY'
    INFRASTRUCTURE_FAILURE = 'INFRASTRUCTURE_FAILURE'
    UNRESOLVED = 'UNRESOLVED'


@dataclass
class AuthorityCandidate:
    """One body the evidence points at, kept whole so a decision can be audited."""

    domain: str
    name: str
    score: float
    evidence: list[str] = field(default_factory=list)
    #: Domains merged into this one as the same body (a regional arm, an apply portal).
    absorbed: list[str] = field(default_factory=list)
    #: Name words this body has and its rivals do not. Empty when nothing sets it apart.
    distinguishing: list[str] = field(default_factory=list)

    @property
    def share(self) -> float:
        return self._share

    _share: float = 0.0


@dataclass
class AuthorityVerdict:
    decision: Decision
    #: Set only for RESOLVED.
    chosen: AuthorityCandidate | None = None
    #: Every candidate considered, winners and losers alike, always populated.
    candidates: list[AuthorityCandidate] = field(default_factory=list)
    reason: str = ''
    #: For INFRASTRUCTURE_FAILURE, what actually failed. Never a claim about an authority.
    infrastructure_note: str = ''
    #: For RESOLVED, the full `ResolvedExam`. Untyped to keep this module free of any
    #: dependency on the resolver, which imports it.
    resolved: object | None = None

    @property
    def is_ambiguous(self) -> bool:
        return self.decision is Decision.AMBIGUOUS_AUTHORITY

    def summary(self) -> str:
        lines = [f'decision: {self.decision.value}', f'reason:   {self.reason}']
        for c in self.candidates:
            mark = ' <- chosen' if (self.chosen and c.domain == self.chosen.domain) else ''
            lines.append(f'  {c.domain:30} {c.score:.2f} (share {c.share:.2f})  '
                         f'{c.name[:46]}{mark}')
            if c.distinguishing:
                lines.append(f'      told apart by: {", ".join(c.distinguishing)}')
            if c.absorbed:
                lines.append(f'      same body as:  {", ".join(c.absorbed)}')
        return '\n'.join(lines)


# ---------------------------------------------------------------- naming
def name_tokens(name: str) -> set[str]:
    """The words of a body's name that could distinguish it from another body."""
    return {w for w in re.split(r'[^a-z]+', (name or '').lower())
            if len(w) > 2 and w not in _SHARED_BODY_WORDS}


def _label(domain: str) -> str:
    host = re.sub(r'^https?://', '', domain or '').split('/')[0]
    return host.replace('www.', '').split('.')[0].lower()


def same_body(a: AuthorityCandidate, b: AuthorityCandidate) -> bool:
    """Is this one authority twice, rather than two authorities?

    An authority's regional office and its apply portal are not rivals to it. Two tells,
    both structural:

      * one printed name says everything the other says and adds detail -- "Staff Selection
        Commission" against "Staff Selection Commission Southern Region". A subset is a
        part of the same body; two names that each carry something the other lacks are two
        bodies.
      * one address is the other's with something appended -- ssc / sscsr, upsc /
        upsconline. A body's own sites grow out of its own short form.
    """
    ta, tb = name_tokens(a.name), name_tokens(b.name)
    smaller = min(ta, tb, key=len) if (ta and tb) else set()
    # Two or more shared words, not one. Many bodies reduce to a single distinctive word
    # once the words every body shares are removed, and a one-word subset would then merge
    # an authority into any site that happens to print that word — a coaching page called
    # "Crack Zeta Clerk" would absorb the Zeta board itself.
    if len(smaller) >= 2 and (ta <= tb or tb <= ta):
        return True

    la, lb = _label(a.domain), _label(b.domain)
    if la and lb and len(min(la, lb, key=len)) >= 3:
        short, long_ = (la, lb) if len(la) <= len(lb) else (lb, la)
        if long_.startswith(short):
            return True
    return False


def _merge(candidates: list[AuthorityCandidate]) -> list[AuthorityCandidate]:
    """Collapse each body's own sites onto the strongest of them."""
    bodies: list[AuthorityCandidate] = []
    for c in sorted(candidates, key=lambda x: -x.score):
        for b in bodies:
            if same_body(b, c):
                b.score += c.score
                b.absorbed.append(c.domain)
                b.evidence.extend(e for e in c.evidence if e not in b.evidence)
                break
        else:
            bodies.append(c)
    return bodies


def _set_distinguishing(bodies: list[AuthorityCandidate]) -> None:
    """What each body's name has that none of the others does."""
    for b in bodies:
        mine = name_tokens(b.name)
        others: set[str] = set()
        for other in bodies:
            if other is not b:
                others |= name_tokens(other.name)
        b.distinguishing = sorted(mine - others)


# ---------------------------------------------------------------- the decision
def decide(exam_query: str, candidates: list[AuthorityCandidate]) -> AuthorityVerdict:
    """Resolve, or report that the name does not choose between real alternatives."""
    if not candidates:
        return AuthorityVerdict(Decision.UNRESOLVED, candidates=[],
                                reason='no candidate authority was found at all')

    bodies = _merge(candidates)
    total = sum(max(0.0, b.score) for b in bodies) or 1.0
    for b in bodies:
        b._share = max(0.0, b.score) / total
    bodies.sort(key=lambda b: -b.score)

    plausible = [b for b in bodies if b.share >= PLAUSIBLE_SHARE]
    if not plausible:                                  # everything is a stray mention
        plausible = bodies[:1]

    _set_distinguishing(plausible)

    if len(plausible) == 1:
        winner = plausible[0]
        return AuthorityVerdict(
            Decision.RESOLVED, chosen=winner, candidates=bodies,
            reason=(f'one body is plausibly the authority; '
                    f'{len(bodies) - 1} other candidate(s) were either the same body under '
                    f'another address or too faintly present to be a rival claim'))

    # Two or more real bodies. The margin between them is not evidence about which one the
    # caller meant, so it is not consulted. Only the name they supplied can choose.
    asked = name_tokens(exam_query)
    named = [b for b in plausible if asked & set(b.distinguishing)]

    if len(named) == 1:
        winner = named[0]
        told_apart = sorted(asked & set(winner.distinguishing))
        return AuthorityVerdict(
            Decision.RESOLVED, chosen=winner, candidates=bodies,
            reason=(f'{len(plausible)} bodies share this name, and the exam as supplied '
                    f'names {", ".join(told_apart)}, which only this one carries'))

    shared = ', '.join(b.name or b.domain for b in plausible)
    return AuthorityVerdict(
        Decision.AMBIGUOUS_AUTHORITY, chosen=None, candidates=bodies,
        reason=(f'{len(plausible)} distinct authorities are plausible for '
                f'"{exam_query}" — {shared}. They are told apart by '
                f'{"; ".join("/".join(b.distinguishing) or "(nothing)" for b in plausible)}, '
                f'and the exam as supplied carries none of it. '
                f'The scores differ, but a score gap is a fact about today’s search results '
                f'rather than about which authority was meant, so it is not used to choose. '
                f'Name the authority in the exam and this resolves.'))
