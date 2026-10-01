"""U3: a quoted value ends where the document ends it, never at a character count.

Each reader of a candidate-facing quotation -- qualification, application step, exam-day rule,
FAQ / official clause, physical requirement -- used to slice its value at a fixed length
(90, 150, 300, 400, 500, 600, 700, 900, 6000), and every materialize / evidence step sliced it
again. A sliced value is still a verbatim substring of the document, so no verbatim check could
see what was missing ("District Centres once chos", "Provincial Act or a", "in Telug").

These tests hold four things for every reader:

  * a value longer than the old limit is kept whole;
  * it ends at the unit's semantic boundary (a sentence end, the next clause number, a heading,
    a signature), not at a character;
  * its evidence covers exactly the published value;
  * where the source does not print the unit's end, nothing is completed: the reading is dropped
    or held NEEDS_REVIEW, and the local model, which may only say "whole" or "not whole", can
    withhold but never supply text.

Fixtures are written for an invented authority. Run:
    python -m unittest tools.exam_builder.test_semantic_units
"""
from __future__ import annotations

import json
import unittest

from ..exam_authoring import extract as X
from ..exam_authoring.record import Citation, Field, Status
from ..exam_authoring.sources import Document
from . import build as B
from . import materialize as M
from . import semantic as SM
from . import stages as ST
from . import units as U
from .clauses import procedure_clauses
from tools.claude_cli.schemas import InfraStatus
from tools.claude_cli.testing import FakeClaude

from .test_attribution import URL


def FakeProvider(reply, enabled=True, fail=None):
    """A scripted Claude gateway whose every answer is `reply` (the completeness vetting asks only
    that one question). `fail` simulates the CLI failing; `enabled=False` the integration off."""
    return FakeClaude(reply, enabled=enabled, fail=InfraStatus.CLAUDE_CLI_FAILED if fail else None)

# ------------------------------------------------------------------------------ fixtures

#: 486 characters: longer than every old qualification limit (the 320-character passage window,
#: `.{0,320}`, `[:400]`) and ending in an abbreviation-laden sentence.
LONG_QUALIFICATION = (
    "Must possess a Bachelor's Degree of any recognised University in India established or "
    "incorporated by or under a Central Act, a Provincial Act or a State Act, or of an Institution "
    "recognised by the University Grants Commission (U.G.C.), or any equivalent qualification "
    "recognised as such by the Government vide G.O.Ms.No. 12 dated 01.02.2031, and the degree "
    "must have been obtained on or before the closing date prescribed for the receipt of online "
    "applications under this notification.")

QUALIFICATION_NOTICE = (
    'EXAMPLE COMMISSION NOTIFICATION NO. 04/2031 EXAMPLE OFFICERS EXAMINATION 2031 '
    'PARA-5 EDUCATIONAL QUALIFICATIONS: The qualifications are those prescribed in the service '
    'rules of the department concerned and are reproduced below for the convenience of '
    'applicants who wish to apply for these posts. ' + LONG_QUALIFICATION +
    ' PARA-6 AGE: Candidates must be between 18 and 44 years of age on 01/07/2031.')

#: The same requirement, printed without its end: the sentence runs into the next heading.
UNFINISHED_QUALIFICATION_NOTICE = (
    'EXAMPLE COMMISSION NOTIFICATION NO. 04/2031 PARA-5 EDUCATIONAL QUALIFICATIONS: '
    "Must possess a Bachelor's Degree of any recognised University in India established or "
    'incorporated by or under a Central Act, a Provincial Act or a State Act or of an Institution '
    'recognised by the University Grants Commission or of any other body recognised by the '
    'Government for the purpose of recruitment to the posts notified herein and for other '
    'PARA-6 AGE: Candidates must be between 18 and 44 years of age on 01/07/2031.')

#: 12.1 is 1,000+ characters: longer than the clause reader's old 700. 12.2 is a short clause.
LONG_CLAUSE = (
    'Procedure of selection will be as per the rules in force. ' +
    ' '.join(f'Candidates at rank band {i} will be called for the written examination in the ratio '
             f'fixed for band {i} by the Commission.' for i in range(1, 12)) +
    ' The marks obtained in the qualifying paper are not counted for ranking.')
CLAUSE_NOTICE = (
    'PARA-12 PROCEDURE OF SELECTION: 12.1 ' + LONG_CLAUSE +
    ' 12.2 Candidates are advised to go through the Instructions to Candidates enclosed to this '
    'Notification at Annexure-VI, which form part of it. '
    'PARA-13 DEBARMENT: 13.1 Any candidate found using unfair means will be debarred from all '
    'recruitments of the Commission for five years. Sd/- Place: Example City SECRETARY 23 '
    'ANNEXURE-I Instructions for the use of the online portal.')


def steps_notice(n_steps: int, filler: int) -> str:
    """Numbered application steps; with enough of them, the last one crosses the 9,000-character
    search window the step reader looks in."""
    body = ' '.join(['The candidate must keep a copy of this page for later reference.'] * filler)
    steps = [f'7.{i} Candidates must submit the online application form and upload the required '
             f'documents at step {i}. {body} This completes step {i} of the procedure.'
             for i in range(1, n_steps + 1)]
    return ('PARA-7: HOW TO APPLY\n' + '\n'.join(steps)
            + '\nPARA-8: SCHEME OF EXAMINATION\n8.1 The examination has two stages.')


def pdf(text: str, pages: list[str] | None = None) -> Document:
    return Document(url=URL, kind='PDF', fetched_at='2031-01-01', text='', pages=pages or [text])


def cite(excerpt: str = '') -> Citation:
    return Citation(document_title='Notice', url=URL, page=1, clause='c', excerpt=excerpt,
                    verified_date='2031-01-01')


# ----------------------------------------------------------------------- boundaries

class TestBoundaries(unittest.TestCase):

    def test_an_abbreviation_does_not_end_a_sentence(self):
        text = 'Pay Rs. 200/- under G.O.Ms.No. 12 before 5 p.m. on the last date. Next sentence.'
        self.assertEqual(text[:U.sentence_end(text, 0)], 'Pay Rs. 200/- under G.O.Ms.No. 12 before 5 p.m. on the last date.')

    def test_a_measurement_is_not_a_clause_number(self):
        text = ('For Post Code 02: Must be not less than 165 Cms. in height and 86.3 Cms round the chest; '
                'and must satisfy a medical board. 7.2 Applicants must then apply.')
        end = U.next_structural_boundary(text, 1)
        self.assertEqual(text[end:end + 3], '7.2')

    def test_a_clause_number_after_an_unpunctuated_list_ends_the_clause(self):
        text = 'the centres 16) Khammam 17) Mahabubabad 10.2 Applicants have to choose ten centres.'
        self.assertEqual(text[U.next_structural_boundary(text, 1):][:4], '10.2')
        text = 'other than the cases mentioned above 12.3 In case of candidates getting same marks.'
        self.assertEqual(text[U.next_structural_boundary(text, 1):][:4], '12.3')

    def test_a_cross_reference_is_not_a_heading(self):
        text = ('Candidates must read the instructions enclosed at Annexure-VI and the Gazette No. 35, '
                'Part-IV-B before applying. PARA-9 FEE follows.')
        self.assertEqual(text[U.next_structural_boundary(text, 1, clauses=False):][:6], 'PARA-9')

    def test_the_check_names_where_a_value_was_cut(self):
        # The reason is what a reviewer reads in the NEEDS_REVIEW note, so it must say how the
        # value was cut, not only that it was.
        doc = 'District Centres once chosen shall be final. Requests will not be entertained.'
        self.assertTrue(U.check_value('District Centres once chos', doc).reason.startswith('ends inside a word'))
        self.assertTrue(U.check_value('District Centres once chosen shall', doc).reason.startswith('stops mid-sentence'))
        self.assertTrue(U.check_value('District Centres once chosen shall be final.', doc).complete)

    def test_a_signature_block_ends_the_last_clause(self):
        text = '18.1 The decision of the Commission is final. Sd/- Place: Example City SECRETARY'
        self.assertEqual(text[U.next_structural_boundary(text, 5, clauses=False):][:4], 'Sd/-')


# --------------------------------------------------------------------------- readers

class TestQualificationReader(unittest.TestCase):

    def test_a_long_requirement_is_read_whole_and_its_evidence_is_the_value(self):
        got = SM.extract('qualification', QUALIFICATION_NOTICE, source_url=URL)
        self.assertIsNotNone(got)
        self.assertEqual(got.value['text'], LONG_QUALIFICATION)
        self.assertGreater(len(got.value['text']), 400)          # past every old limit
        self.assertTrue(got.value['text'].endswith('under this notification.'))
        self.assertEqual(got.evidence.span, got.value['text'])   # evidence covers the value
        self.assertTrue(U.check_value(got.value['text'], QUALIFICATION_NOTICE).complete)

    def test_a_requirement_whose_end_is_not_printed_is_not_read(self):
        got = SM.extract('qualification', UNFINISHED_QUALIFICATION_NOTICE, source_url=URL)
        # Nothing ending mid-sentence is offered: no reading, or one whose text is whole.
        if got is not None:
            self.assertFalse(U.check_value(got.value['text'], UNFINISHED_QUALIFICATION_NOTICE).cut,
                             got.value['text'])
            self.assertNotIn('and for other', got.value['text'])

    def test_the_fallback_reader_reads_the_heading_clause_to_its_end(self):
        clause = (LONG_QUALIFICATION + ' Candidates in the final year of the degree may also apply, '
                  'provided they produce the degree certificate at the time of verification of '
                  'certificates, failing which their candidature will be rejected without any further notice.')
        self.assertGreater(len(clause), 700)
        doc = pdf('Minimum Educational Qualification: ' + clause + ' 5.2 Age limits follow.')
        got = X.qualification(doc, 'Notice')
        self.assertEqual(got.value, clause)                      # was cut at 700 via .{80,900}
        self.assertTrue(got.citation.excerpt.endswith(clause))


class TestClauseReader(unittest.TestCase):

    def test_a_clause_longer_than_the_old_limit_is_quoted_whole(self):
        got = {c['number']: c['text'] for c in procedure_clauses(CLAUSE_NOTICE)}
        self.assertGreater(len(LONG_CLAUSE), 700)
        self.assertEqual(got['12.1'], LONG_CLAUSE)
        self.assertFalse(got['12.1'].endswith('…'))

    def test_the_next_clause_ends_a_clause_and_a_cross_reference_does_not(self):
        got = {c['number']: c['text'] for c in procedure_clauses(CLAUSE_NOTICE)}
        self.assertTrue(got['12.2'].endswith('which form part of it.'), got['12.2'])

    def test_the_last_clause_stops_at_the_signature(self):
        got = {c['number']: c['text'] for c in procedure_clauses(CLAUSE_NOTICE)}
        self.assertEqual(got['13.1'], 'Any candidate found using unfair means will be debarred from '
                                      'all recruitments of the Commission for five years.')


class TestStepReader(unittest.TestCase):

    def test_the_step_at_the_search_window_edge_is_read_to_its_end(self):
        text = steps_notice(13, 10)
        self.assertGreater(len(text), ST.REGION_LENGTH)
        got = ST.discover_stages(text)
        self.assertTrue(got)
        for step in got:
            self.assertRegex(step.body.rstrip(), r'This completes step \d+ of the procedure\.$')
            self.assertFalse(U.check_value(step.body, text).cut, step.body[-60:])

    def test_a_step_ends_before_the_next_heading(self):
        text = steps_notice(3, 2)
        got = ST.discover_stages(text)
        self.assertTrue(got)
        self.assertNotIn('SCHEME OF EXAMINATION', got[-1].body)
        self.assertTrue(got[-1].body.rstrip().endswith('This completes step 3 of the procedure.'))

    def test_a_long_step_description_is_not_cut_at_900(self):
        from .application import extract_stages
        from .schema import SourceDocument, SourceKind
        long_body = ' '.join(['The candidate must keep a copy of this page for later reference.'] * 16)
        text = steps_notice(3, 16)
        doc = SourceDocument(id=URL, url=URL, kind=SourceKind.OTHER_OFFICIAL, title='Notice',
                             authority='Example Commission', exam_id='x')
        got = extract_stages(doc, text)
        self.assertTrue(got)
        self.assertTrue(any(long_body in s.description and len(s.description) > 900 for s in got))


class TestFallbackReaders(unittest.TestCase):

    def test_an_exam_day_rule_is_its_own_title(self):
        rule = ('A candidate is not permitted to write part of the paper in English and part of it '
                'in the regional language, and the answer book of such a candidate is not valued.')
        got = X.exam_day_checklist(pdf('INSTRUCTIONS. ' + rule + ' Mobile phones are banned in the hall.'), 'N')
        item = next(i for i in got.value if i['description'] == rule)
        self.assertGreater(len(rule), 90)
        self.assertEqual(item['title'], rule)                    # was s[:90]

    def test_a_long_faq_answer_is_quoted_whole(self):
        answer = ' '.join(f'Part {i} of the answer explains the rule in the words of the Commission.'
                          for i in range(1, 12))
        text = f'Q1. Can I change my centre? {answer} Q2. Can I pay by cash? No, payment is online only.'
        got = X.faqs(pdf(text), 'N')
        self.assertGreater(len(answer), 600)
        self.assertEqual(got.value[0]['answer'], answer)         # was answer[:600]
        self.assertTrue(got.value[0]['excerpt'].endswith(answer))

    def test_an_answer_that_crosses_a_page_break_is_whole(self):
        a1, a2 = 'The fee once paid is not refunded under any', 'circumstances whatsoever.'
        got = X.faqs(pdf('', pages=[f'Q1. Is the fee refunded? {a1}', f'{a2} Q2. Can I pay by cash? No.']), 'N')
        self.assertEqual(got.value[0]['answer'], f'{a1} {a2}')

    def test_the_how_to_apply_section_runs_to_the_next_heading(self):
        section = 'HOW TO APPLY: ' + ' '.join(
            f'{i}. Candidates must complete part {i} of the online form and check it.' for i in range(1, 110))
        got = X.how_to_apply(pdf(section + ' PARA-9 SCHEME OF EXAMINATION: two stages.'), 'N')
        self.assertGreater(len(section), 6000)
        self.assertEqual(got.value, section)                     # was [:6000]
        self.assertEqual(got.citation.excerpt, section)          # was [:400]


class TestPostQualificationRules(unittest.TestCase):

    def test_a_long_qualification_statement_is_kept_whole(self):
        from .eligibility import extract_qualifications
        from .schema import SourceDocument, SourceKind
        doc = SourceDocument(id=URL, url=URL, kind=SourceKind.OTHER_OFFICIAL, title='Notice',
                             authority='Example Commission', exam_id='x')
        rules = extract_qualifications(doc, QUALIFICATION_NOTICE)
        texts = [r.requirement.value for r in rules]
        self.assertIn(LONG_QUALIFICATION, texts)                     # was [:400]


class TestPhysicalRequirement(unittest.TestCase):

    def test_a_long_physical_standard_is_its_whole_sentence(self):
        import re
        from .eligibility import post_code_clauses
        from .schema import Post, SourceDocument, SourceKind
        standard = ('Must be not less than 165 Cms. in height and must be not less than 86.3 Cms. round '
                    'the chest on full inspiration and has a chest expansion of not less than 5 Cms. on '
                    'full inspiration; and the candidate should satisfy a Medical Board of the Government '
                    'as to his physique, fitness and capacity for active outdoor work, and must be certified '
                    'by an Ophthalmic Surgeon of a Government hospital that his vision conforms to the '
                    'requirements specified below, whether for distant or for near vision, without the use of contact glasses.')
        text = ('PHYSICAL REQUIREMENTS:\nFor Post Code Nos. 02 & 09: ' + standard +
                ' Explanation:- A contact glass is a glass shell in contact with the eye.\n'
                'For Post Code No. 07: Must be not less than 160 Cms. in height.\n'
                '6.1 AGE: Candidates must be 18 years old.')
        doc = SourceDocument(id=URL, url=URL, kind=SourceKind.OTHER_OFFICIAL, title='Notice',
                             authority='Example Commission', exam_id='x')
        post = Post(id='p2', name='Deputy Superintendent of Police', code='02')
        post_code_clauses(doc, text, [post], heading=re.compile(r'PHYSICAL REQUIREMENTS:?'))
        self.assertGreater(len(standard), 500)
        # The clause keeps the scope it is printed under; the requirement is its whole first sentence.
        self.assertEqual(post.other_requirements[0].value, 'For Post Code Nos. 02 & 09: ' + standard)   # was [:500]


# ------------------------------------------------------------------------ materialize

def _record(fields: dict) -> 'M.ExamRecord':
    return M.record_from_snapshot({
        'examId': 'exam-example-officers-2031', 'code': 'X', 'title': 'Example Officers Examination 2031',
        'authorityName': 'Example Commission', 'officialDomain': 'https://commission.example.gov.in',
        'sourcesRead': [URL], 'fields': fields})


def _field(value, excerpt='x'):
    return {'status': 'FOUND', 'value': value, 'note': '',
            'citation': {'document_title': 'Notice', 'url': URL, 'page': 3, 'clause': 'c',
                         'excerpt': excerpt, 'verified_date': '2031-01-01'}}


class TestMaterializeKeepsUnitsWhole(unittest.TestCase):

    def test_faq_answer_and_evidence_are_whole(self):
        rec = _record({'faqs': _field([{'question': 'Procedure of selection', 'answer': LONG_CLAUSE,
                                        'officialClause': 'Clause 12.1 of the notice', 'excerpt': LONG_CLAUSE,
                                        'page': 15}])})
        faq = M._faqs(rec)[0]
        self.assertEqual(faq['answer'], LONG_CLAUSE)
        self.assertEqual(faq['provenance']['excerptText'], LONG_CLAUSE)   # was [:600]

    def test_exam_day_title_and_evidence_are_whole(self):
        rule = ('A candidate is not permitted to write part of the paper in one language and part in another '
                'language; ' + ' '.join(f'answers in paper {i} must be written in the medium chosen in the '
                                        f'application,' for i in range(1, 8))
                + ' and an answer book written in more than one medium will not be valued.')
        self.assertGreater(len(rule), 600)
        rec = _record({'examDayChecklist': _field([{'id': 'e1', 'category': 'ITEMS_PROHIBITED', 'title': rule,
                                                    'description': rule, 'excerpt': rule, 'page': 16}])})
        item = M._exam_day(rec)[0]
        self.assertGreater(len(rule), 90)
        self.assertEqual(item['title'], rule)                     # was [:120] (and [:90] upstream)
        self.assertEqual(item['provenance']['excerptText'], rule)

    def test_application_step_lines_are_whole(self):
        long_step = '8.3 Mode of payment: ' + ' '.join(['The fee is paid online only.'] * 40)
        lines = M._how_to_apply_lines([{'title': 'Mode of payment', 'description': long_step}])
        self.assertEqual(lines, [long_step])                      # was [:600]
        self.assertEqual(M._how_to_apply_lines({'text': long_step * 2}), [long_step * 2])   # was [:1200]

    def test_the_qualification_card_is_whole(self):
        rec = _record({'qualification': _field({'text': LONG_QUALIFICATION, 'levels': ['bachelor', 'degree']},
                                               excerpt=LONG_QUALIFICATION)})
        card = next(c for c in M._eligibility_highlights(rec) if c['title'] == 'Educational qualification')
        self.assertEqual(card['body'], LONG_QUALIFICATION)       # was [:400]

    def test_evidence_excerpt_is_the_whole_span(self):
        from .compat import to_legacy_provenance
        from .evidence import Evidence
        from .schema import Fact, SourceEvidence
        span = LONG_CLAUSE
        ev = SourceEvidence.from_evidence(Evidence(span=span, source_url=URL, document_title='Notice', page=15))
        prov = to_legacy_provenance(Fact.verified(span, ev), prov_id='p')
        self.assertEqual(prov['excerptText'], span)              # was [:600]

    def test_the_simulator_quotes_whole_clauses_and_whole_post_names(self):
        from .runtime_simulator import _words
        self.assertEqual(_words({'excerptText': LONG_CLAUSE}), LONG_CLAUSE)          # was [:300]
        from . import runtime_simulator as RS
        name = ('District Backward Classes Welfare Officer including Assistant Director (District '
                'Backward Classes Development Officer) (Backward Classes Welfare Service)')
        import inspect
        self.assertGreater(len(name), 90)
        self.assertNotIn("p['postName'][:", inspect.getsource(RS))


# ------------------------------------------------------------- the builder's vetting

def _loaded(text: str) -> dict:
    return {URL: pdf(text)}


def _rec():
    from ..exam_authoring.record import ExamRecord
    return ExamRecord(exam_id='exam-example-officers-2031', code='X', title='Example Officers Examination 2031',
                      authority_name='Example Commission', official_domain='https://commission.example.gov.in')


class TestCompletenessVetting(unittest.TestCase):

    def vet(self, field: Field, text: str, gateway=None):
        return B._vet_completeness(field.name, field, _loaded(text), _rec(),
                                   gateway=gateway or FakeProvider({}, enabled=False))

    def test_whole_units_pass_untouched(self):
        f = Field.found('faqs', [{'question': 'Q', 'answer': LONG_CLAUSE}], cite(LONG_CLAUSE))
        got = self.vet(f, CLAUSE_NOTICE)
        self.assertIs(got, f)

    def test_a_cut_unit_is_held_and_nothing_is_added(self):
        cut = LONG_CLAUSE[:700].rsplit(' ', 1)[0] + ' …'
        value = [{'question': 'Q', 'answer': cut}]
        got = self.vet(Field.found('faqs', value, cite(cut)), CLAUSE_NOTICE)
        self.assertEqual(got.status, Status.NEEDS_REVIEW)
        self.assertEqual(got.value, value)                        # held as read, never completed
        self.assertIn('not whole', got.note)

    def test_a_unit_cut_mid_word_is_held(self):
        cut = LONG_QUALIFICATION[:145]
        got = self.vet(Field.found('qualification', {'text': cut, 'levels': ['degree']}, cite(cut)),
                       QUALIFICATION_NOTICE)
        self.assertEqual(got.status, Status.NEEDS_REVIEW)

    def test_a_step_that_ran_past_a_heading_is_held(self):
        text = steps_notice(2, 1)
        overrun = text[text.index('7.2'):]
        got = self.vet(Field.found('howToApply', [{'title': 't', 'description': overrun}], cite(overrun)), text)
        self.assertEqual(got.status, Status.NEEDS_REVIEW)

    def complete_reply(self, **over):
        out = {'complete': True, 'continues_after': False, 'starts_mid_unit': False,
               'confidence': 'high', 'reason': ''}
        out.update(over)
        return out

    def only_completeness(self, reply):
        """A provider whose every answer is `reply` (the vetting asks only the completeness question)."""
        return FakeProvider(reply)

    def test_the_model_confirming_keeps_the_field(self):
        f = Field.found('faqs', [{'question': 'Q', 'answer': LONG_CLAUSE}], cite(LONG_CLAUSE))
        p = self.only_completeness(self.complete_reply())
        got = self.vet(f, CLAUSE_NOTICE, p)
        self.assertIs(got, f)
        self.assertEqual(p.calls, 1)

    def test_the_model_saying_incomplete_holds(self):
        f = Field.found('faqs', [{'question': 'Q', 'answer': LONG_CLAUSE}], cite(LONG_CLAUSE))
        got = self.vet(f, CLAUSE_NOTICE, self.only_completeness(self.complete_reply(complete=False)))
        self.assertEqual(got.status, Status.NEEDS_REVIEW)

    def test_the_model_seeing_a_continuation_holds(self):
        f = Field.found('faqs', [{'question': 'Q', 'answer': LONG_CLAUSE}], cite(LONG_CLAUSE))
        got = self.vet(f, CLAUSE_NOTICE, self.only_completeness(self.complete_reply(continues_after=True)))
        self.assertEqual(got.status, Status.NEEDS_REVIEW)

    def test_low_confidence_holds(self):
        f = Field.found('faqs', [{'question': 'Q', 'answer': LONG_CLAUSE}], cite(LONG_CLAUSE))
        got = self.vet(f, CLAUSE_NOTICE, self.only_completeness(self.complete_reply(confidence='low')))
        self.assertEqual(got.status, Status.NEEDS_REVIEW)

    def test_an_unreachable_model_holds(self):
        f = Field.found('faqs', [{'question': 'Q', 'answer': LONG_CLAUSE}], cite(LONG_CLAUSE))
        got = self.vet(f, CLAUSE_NOTICE, FakeProvider({}, fail='down'))
        self.assertEqual(got.status, Status.NEEDS_REVIEW)
        self.assertIn('could not check completeness', got.note)

    def test_the_model_cannot_supply_text(self):
        # A reply carrying extra words (a "completed" quotation) is not the agreed object: held,
        # and the value is the reader's, unchanged.
        reply = dict(self.complete_reply(), completed_text=LONG_CLAUSE + ' And more.')
        f = Field.found('faqs', [{'question': 'Q', 'answer': LONG_CLAUSE}], cite(LONG_CLAUSE))
        got = self.vet(f, CLAUSE_NOTICE, self.only_completeness(reply))
        self.assertEqual(got.status, Status.NEEDS_REVIEW)
        self.assertEqual(got.value[0]['answer'], LONG_CLAUSE)

    def test_the_model_is_not_asked_about_a_cut_unit(self):
        cut = LONG_QUALIFICATION[:145]
        p = self.only_completeness(self.complete_reply())
        got = self.vet(Field.found('qualification', {'text': cut}, cite(cut)), QUALIFICATION_NOTICE, p)
        self.assertEqual(got.status, Status.NEEDS_REVIEW)
        self.assertEqual(p.calls, 0)                               # it cannot rescue a cut unit

    def test_the_vetting_runs_after_every_reader(self):
        import inspect
        self.assertIn('_vet_completeness(cf.name, got, loaded, rec)',
                      inspect.getsource(B._dispatch_domain_extraction))


# ------------------------------------------------------------ completing a stored value

class TestCompletionFromSource(unittest.TestCase):

    def test_a_cut_value_is_extended_to_its_unit_verbatim(self):
        got = U.complete_from_source(LONG_QUALIFICATION[:145], QUALIFICATION_NOTICE, 'sentence')
        self.assertEqual((got.kind, got.text), ('extended', LONG_QUALIFICATION))
        self.assertIn(got.text, QUALIFICATION_NOTICE)

    def test_an_ellipsis_cut_clause_is_extended(self):
        cut = LONG_CLAUSE[:700].rsplit(' ', 1)[0] + ' …'
        got = U.complete_from_source(cut, CLAUSE_NOTICE, 'clause')
        self.assertEqual((got.kind, got.text), ('extended', LONG_CLAUSE))

    def test_a_value_that_ran_past_a_heading_is_ended_there(self):
        text = steps_notice(2, 1)
        start = text.index('7.2')
        overrun = text[start:]
        got = U.complete_from_source(overrun, text, 'clause')
        self.assertEqual(got.kind, 'ended')
        self.assertTrue(got.text.endswith('This completes step 2 of the procedure.'))

    def test_a_whole_value_is_unchanged(self):
        got = U.complete_from_source(LONG_QUALIFICATION, QUALIFICATION_NOTICE, 'sentence')
        self.assertEqual((got.kind, got.text), ('unchanged', LONG_QUALIFICATION))

    def test_wording_that_is_not_a_quotation_is_left_alone(self):
        got = U.complete_from_source('Electronic gadgets are banned (phones and others)', CLAUSE_NOTICE, 'sentence')
        self.assertEqual(got.kind, 'unchecked')

    def test_an_unfinished_source_is_not_completed(self):
        cut = "Must possess a Bachelor's Degree of any recognised University in India"
        got = U.complete_from_source(cut, UNFINISHED_QUALIFICATION_NOTICE, 'sentence')
        self.assertEqual(got.kind, 'unresolved')
        self.assertIsNone(got.text)


# ------------------------------------------------------------- unrelated records unchanged

class TestUnrelatedValuesUnchanged(unittest.TestCase):

    def test_whole_short_values_are_untouched_by_every_path(self):
        rule = 'Mobile phones are banned in the examination hall.'
        text = 'INSTRUCTIONS. ' + rule + ' Candidates must carry the hall ticket.'
        self.assertTrue(U.check_value(rule, text).complete)
        self.assertEqual(U.complete_from_source(rule, text, 'sentence').kind, 'unchanged')
        f = Field.found('examDayChecklist', [{'title': rule, 'description': rule}], cite(rule))
        self.assertIs(B._vet_completeness('examDayChecklist', f, _loaded(text), _rec(),
                                          gateway=FakeProvider({}, enabled=False)), f)

    def test_fields_that_quote_no_unit_are_not_vetted(self):
        f = Field.found('vacancies', {'count': '120'}, cite('There are 120 vacancies.'))
        self.assertIs(B._vet_completeness('vacancies', f, _loaded('There are 120 vacancies.'), _rec()), f)
        self.assertEqual(U.units_of('vacancies', {'count': '120'}), [])


# ------------------------------------------------------------------ syllabus units (F3)

#: 284 characters: longer than the old 160-character title cut. It is printed over two pages,
#: so the page's number ("29") stands between two of its lines.
LONG_ENTRY = ('Early Indian Civilizations of the river valleys; Emergence of Religious Movements in the '
              'sixth century BC - Jainism and Buddhism; Indo- Greek Art and Architecture – Mauryan, '
              'Satavahana and Gupta periods; Growth of Socialist and Communist Movements; Independence '
              'and Partition of India')
#: A note longer than the old 600-character cut.
LONG_NOTE = ' '.join(f'Resource {i} of the region, its distribution and its conservation are studied.'
                     for i in range(1, 11))


def _wrap(text: str, width: int = 80) -> list[str]:
    out, line = [], ''
    for word in text.split():
        if len(line) + len(word) + 1 > width:
            out.append(line)
            line = word
        else:
            line = (line + ' ' + word).strip()
    return out + [line]


def syllabus_notice(footer: str = '29') -> str:
    entry = _wrap('1. ' + LONG_ENTRY)
    note = _wrap('3. Natural Resources: ' + LONG_NOTE)
    return '\n'.join([
        'ANNEXURE-II', 'SCHEME AND SYLLABUS', 'SYLLABUS',
        'PAPER-II: HISTORY, CULTURE AND GEOGRAPHY OF THE STATE AND OF THE COUNTRY AS A WHOLE',
        'I. History and Culture of India', *entry[:2], footer, *entry[2:],
        '2. Satavahanas and their contribution to the culture of the Deccan.',
        'II. Geography of India', '1. Physical features of India.', '2. Rivers of India.', *note,
    ])


def read_syllabus(text: str):
    from . import syllabus as SY
    from .schema import SourceDocument, SourceKind
    doc = SourceDocument(id=URL, url=URL, kind=SourceKind.OTHER_OFFICIAL, title='Notice',
                         authority='Example Commission', exam_id='exam-example-officers-2031')
    return SY.extract_syllabus(doc, text, exam_id='exam-example-officers-2031', cycle='2031')


def _all(nodes):
    for n in nodes:
        yield n
        yield from _all(n.children)


def _tree(syl):
    from .compat import syllabus_tree
    return syllabus_tree(syl, exam_id='exam-example-officers-2031')


class TestSyllabusUnits(unittest.TestCase):

    def entry(self, syl, start):
        return next(n for n in _all(syl.roots) if n.title.startswith(start))

    def test_an_entry_longer_than_160_is_kept_whole(self):
        node = self.entry(read_syllabus(syllabus_notice()), 'Early Indian Civilizations')
        self.assertGreater(len(LONG_ENTRY), 160)
        self.assertEqual(node.title, LONG_ENTRY)                         # was title[:160]
        self.assertTrue(node.title.endswith('Independence and Partition of India'))

    def test_a_page_number_inside_an_entry_is_not_part_of_it_but_the_evidence_quotes_it(self):
        node = self.entry(read_syllabus(syllabus_notice()), 'Early Indian Civilizations')
        self.assertNotIn(' 29 ', f' {node.title} ')
        self.assertEqual(node.status.value, 'VERIFIED')
        self.assertIn(' 29 ', f' {node.evidence[0].span} ')              # verbatim, footer and all
        self.assertTrue(U._within(node.title, node.evidence[0].span))  # and it covers the value

    def test_a_note_longer_than_600_is_kept_whole(self):
        node = self.entry(read_syllabus(syllabus_notice()), 'Natural Resources')
        self.assertGreater(len(LONG_NOTE), 600)
        self.assertEqual(node.note, LONG_NOTE)                           # was note[:600]
        self.assertTrue(U._within(node.note, node.evidence[0].span))

    def test_no_entry_ends_inside_a_word(self):
        text = syllabus_notice()
        for node in _all(read_syllabus(text).roots):
            if node.status.value == 'VERIFIED':
                self.assertFalse(U.check_value(node.evidence[0].span, text).reason.startswith('ends inside a word'),
                                 node.title)

    def test_the_published_tree_carries_whole_values_and_covering_evidence(self):
        text = syllabus_notice()
        tree = _tree(read_syllabus(text))
        self.assertEqual(U.syllabus_problems(tree, text), [])
        flat = M.flat_syllabus_from_tree(tree)
        subs = [s for t in flat for s in t['subtopics']] + [t['topicName'] for t in flat]
        self.assertIn(LONG_ENTRY, subs)                                  # was [:220] / [:160]

    def test_a_long_heading_is_its_own_subject_label(self):
        heading = 'PAPER-II: HISTORY, CULTURE AND GEOGRAPHY OF THE STATE AND OF THE COUNTRY AS A WHOLE'
        self.assertEqual(M._subject_label(heading), heading)             # was [:58] + '…'

    def test_an_entry_whose_whole_text_is_not_printed_is_held_not_completed(self):
        # A page footer of words ("Page 29 of 40", which the reader recognises and leaves out of the
        # entry) sits inside it: the entry as read is not printed verbatim and is not only a page
        # number apart, so it is held for review with its first line -- never published as covered
        # evidence, and never completed.
        text = syllabus_notice(footer='Page 29 of 40')
        node = self.entry(read_syllabus(text), 'Early Indian Civilizations')
        self.assertEqual(node.status.value, 'NEEDS_REVIEW')
        self.assertNotIn('Page 29', node.title)
        self.assertFalse(U._within(node.title, node.evidence[0].span))

    def test_a_cut_syllabus_is_found_and_held(self):
        text = syllabus_notice()
        tree = _tree(read_syllabus(text))
        cut = json.loads(json.dumps(tree))
        for node in U._syllabus_nodes(cut):
            if node['title'].startswith('Early Indian'):
                node['title'] = node['title'][:160]                      # the old cut
                node['provenance']['excerptText'] = node['provenance']['excerptText'][:88]
        problems = U.syllabus_problems(cut, text)
        self.assertTrue(problems)
        got = B._vet_completeness('syllabus', Field.found('syllabus', cut, cite('SYLLABUS')),
                                  _loaded(text), _rec(), gateway=FakeProvider({}, enabled=False))
        self.assertEqual(got.status, Status.NEEDS_REVIEW)
        self.assertEqual(got.value, cut)                                 # held as read, not completed

    def test_a_whole_syllabus_passes_untouched(self):
        text = syllabus_notice()
        f = Field.found('syllabus', _tree(read_syllabus(text)), cite('SYLLABUS'))
        self.assertIs(B._vet_completeness('syllabus', f, _loaded(text), _rec(),
                                          gateway=FakeProvider({}, enabled=False)), f)

    def test_the_model_only_withholds_a_syllabus(self):
        text = syllabus_notice()
        tree = _tree(read_syllabus(text))
        f = Field.found('syllabus', tree, cite('SYLLABUS'))
        no = FakeProvider({'complete': False, 'continues_after': True, 'starts_mid_unit': False,
                           'confidence': 'high', 'reason': 'x'})
        held = B._vet_completeness('syllabus', f, _loaded(text), _rec(), gateway=no)
        self.assertEqual(held.status, Status.NEEDS_REVIEW)
        self.assertEqual(held.value, tree)                               # no text supplied
        down = B._vet_completeness('syllabus', f, _loaded(text), _rec(), gateway=FakeProvider({}, fail='down'))
        self.assertEqual(down.status, Status.NEEDS_REVIEW)

    def test_an_entry_over_a_page_is_placed_where_it_begins(self):
        from types import SimpleNamespace
        text = syllabus_notice()
        head, rest = text.split('I. History and Culture of India\n')
        entry_start, page_three = rest.split('\n29\n')
        syl = read_syllabus(text)
        # Page 1 is the heading block, page 2 is where the entry begins, page 3 holds its tail.
        B._place_tree_pages(syl.roots, SimpleNamespace(pages=[head + 'I. History and Culture of India',
                                                              entry_start, '29\n' + page_three]))
        node = self.entry(syl, 'Early Indian Civilizations')
        self.assertEqual(node.evidence[0].page, 2)                       # not left at page 1

    def test_a_long_wrapped_heading_is_kept_whole(self):
        heading = ('Social, Cultural and Economic History of the Region from the earliest settlements to the '
                   'present day, with special reference to its movements, institutions and people')
        lines = _wrap('III. ' + heading, 70)
        text = syllabus_notice() + '\n' + '\n'.join(lines + ['1. Early settlements of the region.',
                                                            '2. The modern period.'])
        syl = read_syllabus(text)
        self.assertGreater(len(heading), 160)
        self.assertTrue(any(n.title == heading for n in _all(syl.roots)),
                        [n.title[:60] for n in _all(syl.roots) if n.title.startswith('Social')])

    def test_the_clause_reader_keeps_a_long_clause_and_its_whole_evidence(self):
        topic = ('Number Systems and their properties, including divisibility, the highest common factor and '
                 'the least common multiple, fractions and decimals, and the relationships between numbers '
                 'of every kind printed in the school curriculum up to the tenth class')
        body = ' '.join(f'Computation of item {i} of the arithmetic section, with worked problems.' for i in range(1, 16))
        text = '\n'.join(['NOTICE OF EXAMINATION 2031', '13.10 Indicative Syllabus (Tier-I):',
                          '13.10.1 Quantitative Aptitude:', f'13.10.1.1 {topic}: {body}',
                          '13.10.1.2 Percentages: Percentage and its applications.'])
        node = next(n for n in _all(read_syllabus(text).roots) if n.title.startswith('Number Systems'))
        self.assertGreater(len(node.title), 160)
        self.assertTrue(node.title.startswith(topic))                    # was title[:160]
        self.assertTrue((node.title + ' ' + (node.note or '')).rstrip().endswith('with worked problems'))
        self.assertGreater(len(node.evidence[0].span), 900)             # was span[:900]
        self.assertEqual(node.status.value, 'VERIFIED')

    def test_the_bullet_reader_keeps_a_long_bullet_whole(self):
        bullet = ('Indian Polity and Governance including the Constitution, the Political System, Panchayati Raj, '
                  'Public Policy and Rights Issues, the working of the Parliament and of the State Legislatures, '
                  'and the role of the constitutional bodies in the Republic')
        text = '\n'.join(['SECTION III: SYLLABI FOR THE EXAMINATION', 'Part A—Preliminary Examination',
                          'Paper I - (200 marks) Duration: Two hours',
                          '• Current events of national and international importance.', f'• {bullet}',
                          '• Economic and Social Development.', 'SECTION IV: CENTRES'])
        node = next(n for n in _all(read_syllabus(text).roots) if n.title.startswith('Indian Polity'))
        self.assertGreater(len(bullet), 160)
        self.assertEqual(node.title, bullet)                             # was title[:160]

    def test_a_long_branch_topic_is_its_whole_name(self):
        name = ('Paper-IV Economy and Development: the Indian economy, its growth, planning, the public sector, '
                'agriculture, industry and services, with the development of the State since its formation and '
                'the problems and prospects of each of its regions')
        tree = [{'id': 'r', 'title': 'SYLLABUS', 'children': [{'id': 's', 'title': 'Main Examination', 'children': [
            {'id': 't', 'title': name, 'children': [{'id': 'l1', 'title': 'Growth'}, {'id': 'l2', 'title': 'Planning'}]}]}]}]
        self.assertGreater(len(name), 220)
        self.assertIn(name, [t['topicName'] for t in M.flat_syllabus_from_tree(tree)])   # was [:220]


if __name__ == '__main__':
    unittest.main()
