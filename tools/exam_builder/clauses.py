"""A notice's own procedure clauses, quoted, for the FAQs & Official Clauses section.

A notice answers most of a candidate's procedural questions itself -- how objections to the key
are made, whether a stage's marks are published, how recounting works, what debars a candidate --
in numbered clauses under numbered headings ("PARA-15 MEMORANDUM OF MARKS" / "15.1 The marks
secured ..."). This reads those clauses and returns each one verbatim under the heading the
notice printed. Nothing is paraphrased and no question is composed: the heading is the label,
the clause is the answer, and its number is the citation.

Only procedure headings are read. Eligibility, age, fee and the scheme already have their own
sections read from the same notice; repeating them here would say the same thing twice.
"""
from __future__ import annotations

import re

from .units import next_structural_boundary

#: A numbered heading: "PARA-15 MEMORANDUM OF MARKS:-", "PARA 17: SPECIAL INSTRUCTIONS", "SECTION-11:".
_HEADING = re.compile(r'\b(?:PARA|SECTION|CHAPTER)\s*[-–]?\s*(\d{1,2})\s*[:.]?\s*[-–:]?\s*', re.I)
#: The heading's title: a run of capitals ending where the clause text begins.
_TITLE = re.compile(r"([A-Z][A-Z0-9 ,’'&/().-]{3,260}?)\s*(?=[:\-–]+\s|\s\d{1,2}\.\d{1,2}\s|\s[A-Z][a-z]|$)")
#: What a procedure heading is about -- the questions candidates ask once they have applied.
_PROCEDURE = re.compile(
    r'objection|\bkeys?\b|marks|memorandum|recount|debar|malpractice|instruction|decision|'
    r'cent(?:re|er)s?|procedure\s+of\s+selection|selection\s+procedure|normali[sz]', re.I)
_FOOTER = re.compile(r'\bPage\s+\d+\s+of\s+\d+\b|^\s*\d{1,3}\s+', re.I)


def procedure_clauses(text: str, *, page_of=None) -> list[dict]:
    """[{heading, number, text, page}] for every numbered clause under a procedure heading."""
    flat = ' '.join((text or '').split())
    heads = []
    for m in _HEADING.finditer(flat):
        title = _TITLE.match(flat, m.end())
        if not title:
            continue
        heads.append((m.start(), m.end(), int(m.group(1)), title.group(1).strip(' ,.-')))
    # A heading number repeats in a table of contents or a cross-reference ("see PARA-15"); the
    # one followed by its own first clause is the heading.
    out, seen = [], set()
    for i, (start, end, number, title) in enumerate(heads):
        stop = heads[i + 1][0] if i + 1 < len(heads) else len(flat)
        region = flat[end:stop]
        if not _PROCEDURE.search(title) or number in seen:
            continue
        marks = list(re.finditer(rf'(?<![\d.]){number}\.(\d{{1,2}})\s+(?=[A-Z(a-z])', region))
        if not marks:
            continue
        seen.add(number)
        label = re.sub(r'\s+', ' ', title).strip().capitalize()
        for j, mk in enumerate(marks):
            # A clause is one unit: it ends where the next clause of its heading begins. The
            # last clause of a heading ends at the next heading of any kind, or at an annexure,
            # appendix or other part of the document -- never at a character count, which cut
            # long clauses mid-sentence ("Provided that, in case …").
            if j + 1 < len(marks):
                body_end = marks[j + 1].start()
            else:
                body_end = next_structural_boundary(region, mk.end(), clauses=False)
            body = region[mk.end():body_end].strip()
            body = _FOOTER.sub(' ', body).strip()
            if len(body) < 25:
                continue
            clause = f'{number}.{mk.group(1)}'
            out.append({'heading': label, 'number': clause, 'text': body,
                        'page': page_of(body[:120]) if page_of else 1})
    return out
