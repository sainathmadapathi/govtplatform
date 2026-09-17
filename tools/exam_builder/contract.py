"""The Universal Information Contract — what every exam is asked for, and who can answer.

The *structure* here is universal; the *contents* are always the exam's own. Every exam is
asked the same questions, and each question declares which kinds of document could answer
it, in preference order.

That ordering is the point. A field is not tied to a document kind, because authorities
package their information differently: SSC publishes no standalone syllabus for CGL — it is
an annexure inside the notice — while UPSC gives some exams a separate syllabus PDF. A
contract that demanded a SYLLABUS document would report "not published" for SSC, which is
false. So `syllabus` accepts a SYLLABUS document *or* the NOTIFICATION, and the extractor
reads whichever is present.

Nothing here knows an authority's name. Adding an exam adds no entry to this file.
"""
from __future__ import annotations

from dataclasses import dataclass, field as dc_field

from .discover import DocKind


@dataclass(frozen=True)
class ContractField:
    """One thing GovOS wants to know, and where it could come from."""

    name: str
    group: str
    #: Document kinds that may supply it, best first.
    sources: tuple[DocKind, ...]
    #: The extractor in tools.exam_authoring.extract that reads it, by function name.
    extractor: str = ''
    #: Why it matters — printed in the report so a gap is legible, not just a missing row.
    purpose: str = ''
    #: A field GovOS can render an honest empty state for is not a build failure.
    required: bool = False


#: The tree from the specification, flattened. Group names are the sections a candidate
#: sees, so a gap in the report maps directly to a screen that will show its empty state.
CONTRACT: tuple[ContractField, ...] = (
    # -- Identity ---------------------------------------------------------------------
    ContractField('officialName', 'Identity', (DocKind.EXAM_PAGE, DocKind.NOTIFICATION),
                  purpose='The name the authority itself prints.', required=True),
    ContractField('authority', 'Identity', (DocKind.EXAM_PAGE, DocKind.NOTIFICATION),
                  purpose='Who conducts it.', required=True),

    # -- Application ------------------------------------------------------------------
    ContractField('applicationPortal', 'Application', (DocKind.NOTIFICATION, DocKind.APPLICATION_PORTAL),
                  extractor='application_portal',
                  purpose='Where a candidate actually applies.', required=True),
    ContractField('howToApply', 'Application', (DocKind.NOTIFICATION, DocKind.APPLICATION_PORTAL),
                  extractor='how_to_apply',
                  purpose='The process, in the authority’s own words — the mock form is built from this.'),
    ContractField('fee', 'Application', (DocKind.NOTIFICATION,), extractor='fee',
                  purpose='Amount, exemptions and the modes that are accepted.'),

    # -- Posts and eligibility --------------------------------------------------------
    ContractField('posts', 'Posts', (DocKind.NOTIFICATION,), extractor='services_list',
                  purpose='The services or posts this exam recruits to.'),
    ContractField('vacancies', 'Posts', (DocKind.NOTIFICATION,), extractor='vacancies',
                  purpose='How many, where the authority states a number.'),
    ContractField('ageLimits', 'Eligibility', (DocKind.NOTIFICATION,), extractor='age_limits',
                  purpose='The age band and the date it is reckoned on.'),
    ContractField('qualification', 'Eligibility', (DocKind.NOTIFICATION,), extractor='qualification',
                  purpose='The minimum educational qualification.'),
    ContractField('attempts', 'Eligibility', (DocKind.NOTIFICATION,), extractor='attempts',
                  purpose='Any cap on attempts, and relaxations.'),

    # -- Dates ------------------------------------------------------------------------
    ContractField('dates', 'Dates', (DocKind.EXAM_PAGE, DocKind.NOTIFICATION),
                  extractor='dates_from_rows',
                  purpose='Every milestone the authority has announced.', required=True),
    ContractField('corrigenda', 'Timeline', (DocKind.CORRIGENDUM,),
                  purpose='Anything the authority changed after publishing.'),

    # -- Pattern and syllabus ---------------------------------------------------------
    ContractField('examPattern', 'Exam Pattern', (DocKind.EXAM_PATTERN, DocKind.NOTIFICATION),
                  extractor='scheme_tables',
                  purpose='Papers, marks and duration.'),
    ContractField('syllabus', 'Syllabus', (DocKind.SYLLABUS, DocKind.NOTIFICATION),
                  purpose='The topics, from the authority’s own scheme.'),

    # -- Practice material ------------------------------------------------------------
    ContractField('officialPapers', 'PYQs', (DocKind.QUESTION_PAPER,),
                  purpose='Past papers the authority itself published.'),
    ContractField('answerKeys', 'Answer Keys', (DocKind.ANSWER_KEY,),
                  purpose='Official keys. Without one a paper cannot be scored without inventing answers.'),

    # -- Downstream -------------------------------------------------------------------
    ContractField('admitCard', 'Admit Card', (DocKind.ADMIT_CARD, DocKind.NOTIFICATION),
                  extractor='admit_card',
                  purpose='When and where the call letter appears.'),
    ContractField('results', 'Results', (DocKind.RESULT,),
                  purpose='What the authority has declared so far.'),
    ContractField('cutoffs', 'Results', (DocKind.CUTOFF,),
                  purpose='The bar, by category and year, where published.'),

    # -- Provenance -------------------------------------------------------------------
    ContractField('officialSources', 'Official Sources', (),
                  purpose='Every document this record was read from.', required=True),
)

GROUPS: tuple[str, ...] = tuple(dict.fromkeys(f.group for f in CONTRACT))


def fields_for(kind: DocKind) -> list[ContractField]:
    """Every contract field a document of this kind could help answer."""
    return [f for f in CONTRACT if kind in f.sources]


def suppliers(field_name: str) -> tuple[DocKind, ...]:
    for f in CONTRACT:
        if f.name == field_name:
            return f.sources
    return ()


@dataclass
class Coverage:
    """How much of the contract one exam could actually be given."""

    supplied: dict[str, str] = dc_field(default_factory=dict)      # field -> status
    missing_sources: dict[str, list[str]] = dc_field(default_factory=dict)

    def by_group(self) -> dict[str, list[tuple[str, str]]]:
        out: dict[str, list[tuple[str, str]]] = {g: [] for g in GROUPS}
        for f in CONTRACT:
            out[f.group].append((f.name, self.supplied.get(f.name, 'NO_SOURCE')))
        return out


def coverage_from(available_kinds: set[DocKind]) -> Coverage:
    """Which contract fields *could* be answered by the documents discovered.

    This is deliberately computed before any extraction runs. It separates "the authority
    published nothing that could answer this" from "we read the document and failed", which
    are the two claims the whole pipeline is built to keep apart.
    """
    cov = Coverage()
    for f in CONTRACT:
        if not f.sources:
            cov.supplied[f.name] = 'INTRINSIC'
            continue
        usable = [k for k in f.sources if k in available_kinds]
        if usable:
            cov.supplied[f.name] = f'CAN_ANSWER_FROM:{usable[0].value}'
        else:
            cov.supplied[f.name] = 'NO_SOURCE'
            cov.missing_sources[f.name] = [k.value for k in f.sources]
    return cov
