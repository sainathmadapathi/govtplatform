"""Evidence on every published fact of a runtime exam.

A candidate who sees "Vacancies 563" can ask where it came from. The answer is the fact's
provenance -- document, page, clause, the exact words -- and this module makes sure every
provenance a runtime exam carries can answer that question consistently:

  * every provenance gets an `evidenceId` computed from what it cites (URL, page, clause,
    excerpt), so the same evidence keeps the same identity from the canonical record through
    the runtime to the page, and two facts citing different words never share one;
  * every provenance names the authority that published the document;
  * every provenance says what kind of evidence it is:
      DIRECT      the value appears in the cited words;
      RECONCILED  a later official statement replaced an earlier one; both are linked
                  (`supersedes` on the governing statement, `supersededBy` on the replaced);
      DERIVED     GovOS computed the value from cited figures; `derivation` names the method
                  and the evidence of every input;
  * a provenance that cites no URL, or neither a page nor any words, is never presented as
    OFFICIALLY_VERIFIED.

Nothing here reads an exam's name or an authority's; it works on the runtime shape alone.
"""
from __future__ import annotations

import hashlib
import json
import re
from typing import Any, Optional

#: The keys under which a runtime object carries its evidence.
PROVENANCE_KEYS = ('provenance', 'officialProvenance')
#: Maps of fact name -> evidence.
EVIDENCE_MAPS = ('factEvidence', 'derivedEvidence')
#: Links between evidence records; never followed when computing an identity.
_LINKS = ('supersedes', 'supersededBy', 'derivation')

EVIDENCE_TYPES = ('DIRECT', 'RECONCILED', 'DERIVED')


def is_provenance(x: Any) -> bool:
    return isinstance(x, dict) and 'documentTitle' in x and 'officialUrl' in x


def _ws(text: Any) -> str:
    return ' '.join(str(text or '').split())


def evidence_id(p: dict) -> str:
    """The identity of what a provenance cites. Same words on the same page of the same
    document, same id; anything else, a different one."""
    basis = [str(p.get('officialUrl') or ''), str(p.get('pageNumber') or ''),
             _ws(p.get('clauseNumber')), _ws(p.get('excerptText'))]
    return 'ev-' + hashlib.sha1(json.dumps(basis, ensure_ascii=False).encode('utf-8')).hexdigest()[:16]


def has_evidence(p: dict) -> bool:
    """A source a candidate can open, and a place in it: a page or the words themselves."""
    return (str(p.get('officialUrl') or '').startswith('http')
            and bool(_ws(p.get('excerptText')) or p.get('pageNumber')))


def summary(p: dict) -> dict:
    """A provenance without its links: what one evidence record says on its own."""
    return {k: v for k, v in p.items() if k not in _LINKS}


def stamp(p: dict, authority: str) -> dict:
    """Identity, authority, type and an honest verification level, on one provenance and on
    every provenance it links to."""
    for linked in (p.get('supersedes') or []):
        if is_provenance(linked):
            stamp(linked, authority)
    if is_provenance(p.get('supersededBy')):
        stamp(p['supersededBy'], authority)
    for inp in ((p.get('derivation') or {}).get('inputs') or []):
        if is_provenance(inp):
            stamp(inp, authority)
    if authority and not p.get('authorityName'):
        p['authorityName'] = authority
    if p.get('evidenceType') not in EVIDENCE_TYPES:
        p['evidenceType'] = ('DERIVED' if p.get('derivation')
                             else 'RECONCILED' if (p.get('supersedes') or p.get('supersededBy'))
                             else 'DIRECT')
    if p.get('verificationLevel') == 'OFFICIALLY_VERIFIED' and not has_evidence(p):
        p['verificationLevel'] = 'UNDER_VERIFICATION'
    p['evidenceId'] = evidence_id(p)
    return p


def stamp_exam(exam: dict) -> None:
    """Stamp every provenance anywhere in a runtime exam."""
    authority = str(exam.get('authorityName') or '')

    def walk(x: Any) -> None:
        if isinstance(x, dict):
            for key in PROVENANCE_KEYS:
                if is_provenance(x.get(key)):
                    stamp(x[key], authority)
            for key in EVIDENCE_MAPS:
                if isinstance(x.get(key), dict):
                    for p in x[key].values():
                        if is_provenance(p):
                            stamp(p, authority)
            for key, value in x.items():
                if key not in PROVENANCE_KEYS and key not in EVIDENCE_MAPS:
                    walk(value)
        elif isinstance(x, list):
            for value in x:
                walk(value)

    walk(exam)


# ------------------------------------------------------------------------ reconciliation
def link_revisions(rows: list[dict], superseded_by: dict[str, str]) -> None:
    """Link each replaced row's evidence to the row that replaced it, both ways.

    `superseded_by` maps a row id to the id of the row that governs in its place (as the
    reconciliation recorded it). Provenance dicts are copied before they are changed: a
    fallback provenance can be shared by several rows."""
    by_id = {str(r.get('id')): r for r in rows if isinstance(r, dict)}
    for old_id, new_id in superseded_by.items():
        old, new = by_id.get(old_id), by_id.get(new_id)
        if not (old and new and is_provenance(old.get('provenance')) and is_provenance(new.get('provenance'))):
            continue
        old_p, new_p = dict(old['provenance']), dict(new['provenance'])
        old_p['supersededBy'] = summary(new_p)
        old_p['evidenceType'] = 'RECONCILED'
        new_p['supersedes'] = list(new_p.get('supersedes') or []) + [summary(old_p)]
        new_p['evidenceType'] = 'RECONCILED'
        old['provenance'], new['provenance'] = old_p, new_p
        old['supersededBy'] = new_id


# ------------------------------------------------------------------------ derivation
#: How GovOS computes each derived pattern figure, in words, and where its inputs are.
_DERIVATIONS = {
    'marksPerQuestion': ('the marks this part prints, divided by the number of questions it prints',
                         'self'),
    'negativeMarkPerWrong': ('the penalty stated for this part, as a number of marks', 'self'),
    'questions': ('the sum of the question counts printed for the parts below it', 'children'),
    'marks': ('the sum of the marks printed for the parts below it', 'children'),
    'durationMinutes': ('the printed duration, converted to minutes', 'self'),
    'negativeMarking': ('the negative-marking rule stated for the stage this part belongs to, '
                        'which applies to each of its parts', 'ancestor'),
}


def derive_pattern_evidence(tree: list[dict]) -> None:
    """For every figure a pattern node marks as derived, evidence naming its inputs.

    The figure keeps its node's own provenance for what was printed; `derivedEvidence[key]`
    is a DERIVED record whose inputs are the evidence it was computed from -- the node's own
    row, its parts, or the stage whose rule it carries."""
    def visit(node: dict, ancestors: list[dict]) -> None:
        own = node.get('provenance')
        derived = [k for k in (node.get('derived') or []) if k in node]
        out: dict = {}
        for key in derived:
            method, where = _DERIVATIONS.get(key, ('computed by GovOS from the figures this part prints', 'self'))
            if where == 'children':
                inputs = [summary(c['provenance']) for c in (node.get('children') or [])
                          if is_provenance(c.get('provenance')) and key in c and key not in (c.get('derived') or [])]
            elif where == 'ancestor':
                source = next((a for a in reversed(ancestors) if a.get('negativeMarking')
                               and 'negativeMarking' not in (a.get('derived') or [])), None)
                inputs = [summary(source['provenance'])] if source and is_provenance(source.get('provenance')) else []
            else:
                inputs = [summary(own)] if is_provenance(own) else []
            if not inputs:
                continue                     # a derivation that cannot name its inputs is not offered
            base = summary(inputs[0])
            out[key] = dict(base, id=f"{base.get('id', 'prov')}-derived-{key}", evidenceType='DERIVED',
                            derivation={'method': method, 'inputs': _unique(inputs)})
        if out:
            node['derivedEvidence'] = out
        for child in node.get('children') or []:
            if isinstance(child, dict):
                visit(child, ancestors + [node])

    for root in tree or []:
        if isinstance(root, dict):
            visit(root, [])


def _unique(provs: list[dict]) -> list[dict]:
    seen, out = set(), []
    for p in provs:
        key = evidence_id(p)
        if key not in seen:
            seen.add(key)
            out.append(p)
    return out


# ------------------------------------------------------------------------ checks
def evidence_problems(exam: dict) -> list[str]:
    """Every way a runtime exam's evidence fails the contract; empty when it holds."""
    problems: list[str] = []

    def check(p: dict, where: str) -> None:
        if not p.get('evidenceId') or p.get('evidenceId') != evidence_id(p):
            problems.append(f'{where}: evidence identity missing or not computed from what it cites')
        if p.get('evidenceType') not in EVIDENCE_TYPES:
            problems.append(f'{where}: no evidence type')
        if p.get('verificationLevel') == 'OFFICIALLY_VERIFIED' and not has_evidence(p):
            problems.append(f'{where}: presented as officially verified without a source and a place in it')
        if p.get('evidenceType') == 'DERIVED' and not ((p.get('derivation') or {}).get('inputs')):
            problems.append(f'{where}: derived without naming its inputs')
        if p.get('evidenceType') == 'RECONCILED' and not (p.get('supersedes') or p.get('supersededBy')):
            problems.append(f'{where}: reconciled without the statement it reconciles')

    def walk(x: Any, where: str) -> None:
        if isinstance(x, dict):
            for key in PROVENANCE_KEYS:
                if is_provenance(x.get(key)):
                    check(x[key], f'{where}.{key}')
            for key in EVIDENCE_MAPS:
                for name, p in (x.get(key) or {}).items() if isinstance(x.get(key), dict) else ():
                    if is_provenance(p):
                        check(p, f'{where}.{key}.{name}')
            for key, value in x.items():
                if key not in PROVENANCE_KEYS and key not in EVIDENCE_MAPS:
                    walk(value, f'{where}.{key}')
        elif isinstance(x, list):
            for i, value in enumerate(x):
                walk(value, f'{where}[{i}]')

    walk(exam, 'exam')
    return problems


def strip_evidence_metadata(x: Any) -> Any:
    """The runtime with this module's additions removed: what the facts were before evidence
    was attached. Used to prove that attaching evidence changed no fact."""
    added = {'evidenceId', 'evidenceType', 'authorityName', 'supersedes', 'supersededBy', 'derivation'}
    if isinstance(x, dict):
        out = {}
        for k, v in x.items():
            if k in ('factEvidence', 'derivedEvidence'):
                continue
            if k in PROVENANCE_KEYS and is_provenance(v):
                v = {kk: vv for kk, vv in v.items() if kk not in added}
            elif k == 'supersededBy' and isinstance(v, str):
                continue
            out[k] = strip_evidence_metadata(v)
        return out
    if isinstance(x, list):
        return [strip_evidence_metadata(v) for v in x]
    return x


def fact_provenance(value_present: bool, prov: Optional[dict]) -> Optional[dict]:
    """Evidence for a scalar fact: only where the fact is published and its source is cited."""
    return dict(prov) if value_present and is_provenance(prov) else None
