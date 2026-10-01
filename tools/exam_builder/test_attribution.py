"""Identity MATCH is not fact attribution.

A document can belong to the right recruitment while the sentence, clause or table cell a
reader took a value from does not state that fact: a row's serial number is not a vacancy
count, an age-relaxation clause is not the qualification, a category column is not a post,
marks shared by two papers are not one paper's marks, and an exemption in one list item does
not extend to the next item. Each fixture below reproduces one such failure found on a real
notice (a central bank's HTML advertisement, and list items joined across a state commission's
notice), written for an invented authority: the failures are shapes, not one authority's.

Every test drives the builder's real dispatch, so it exercises whatever reader produced the
value and whatever vetting follows it.

Run: python -m unittest tools.exam_builder.test_attribution
"""
from __future__ import annotations

import json
import unittest

from tools.claude_cli.schemas import InfraStatus, Operation
from tools.claude_cli.testing import ByOperation, FakeClaude, use_gateway

from ..exam_authoring.record import ExamRecord, Status
from ..exam_authoring.sources import Document
from . import build as B
from .contract import CONTRACT
from .discover import DiscoveredDoc, DocKind, Relevance, SourceSet
from .identity import ExamIdentity, IdentityCheck, IdentityVerdict
from .resolve import Authority, ResolvedExam

DOMAIN = 'https://commission.example.gov.in'
URL = DOMAIN + '/notice.pdf'
TARGET = ExamIdentity(exam_id='exam-example-officers-2031', query='Example Officers Examination 2031',
                      official_name='Example Officers Examination 2031', year='2031',
                      authority_name='Example Commission', authority_domain=DOMAIN)


def read(field: str, text: str, *, html: str = '', gateway=None):
    """One contract field, read from one identity-matched notification."""
    kind = 'HTML' if html else 'PDF'
    doc = Document(url=URL, kind=kind, fetched_at='2031-01-01',
                   text=text if kind == 'HTML' else '', pages=[] if kind == 'HTML' else [text])
    if html:
        doc.html = html
    sources = SourceSet(exam_id=TARGET.exam_id, authority_domain=DOMAIN,
                        docs=[DiscoveredDoc(url=URL, kind=DocKind.NOTIFICATION, title='Notice',
                                            relevance=Relevance.DIRECT)])
    rec = ExamRecord(exam_id=TARGET.exam_id, code='X', title='Example Officers Examination 2031',
                     authority_name='Example Commission', official_domain=DOMAIN)
    resolved = ResolvedExam(query=TARGET.query, official_name=TARGET.official_name, year='2031',
                            authority=Authority(name='Example Commission', domain=DOMAIN, confidence=1.0))
    identity = {URL: IdentityCheck(IdentityVerdict.MATCH)}
    cf = next(c for c in CONTRACT if c.name == field)
    # The real CLI is never reached: with no gateway given, a disabled one is installed.
    with use_gateway(gateway or FakeClaude(enabled=False)):
        return B._dispatch_domain_extraction(cf, sources, {URL: doc}, rec, resolved, identity, TARGET)


def published(got) -> bool:
    return got is not None and got.status is Status.FOUND


# ------------------------------------------------------------------------------ fixtures
#: A vacancy table flattened to text: header words, a second header row of category labels,
#: then row 1 -- whose serial number is the first number after "Vacancies".
FLATTENED_VACANCY_TABLE = (
    'The Commission invites applications for the posts mentioned below. Post Number of '
    'Vacancies GEN/UR EWS OBC SC ST Total PwBD Category A B C D 1 Officers in Grade II - '
    'Economics Stream 16 4 9 7 4 40 - - 1 1 2 Officers in Grade II - Statistics Stream 4 1 1 '
    '3 1 10 - - - - Total 20 5 10 10 5 50 1 - 1 1 Abbreviations: GEN/UR - General / Unreserved.')

#: The same table as the HTML the authority serves: a two-row header, a serial column the
#: header does not name, entities left in the cells, and a footnote row.
VACANCY_TABLE_HTML = (
    '<table><tr><td>Post</td><td>Number of Vacancies</td></tr>'
    '<tr><td>GEN/UR</td><td>EWS</td><td>OBC</td><td>SC</td><td>ST</td><td>Total</td></tr>'
    '<tr><td>1</td><td>Officers in Grade II &ndash; Economics Stream</td><td>16</td><td>4</td>'
    '<td>9</td><td>7</td><td>4</td><td>40</td></tr>'
    '<tr><td>2</td><td>Officers in Grade II &ndash; Statistics Stream</td><td>4</td><td>1</td>'
    '<td>1</td><td>3</td><td>1</td><td>10</td></tr>'
    '<tr><td>&nbsp;</td><td></td></tr>'
    '<tr><td>Abbreviations: GEN/UR &ndash; General / Unreserved; EWS &ndash; Economically '
    'Weaker Section</td></tr></table>')

AGE_RELAXATION_ONLY = (
    'Age Limit: A candidate must have attained the age of 21 years and must not have attained '
    'the age of 30 years. x) For recruitment to the Statistics Stream, candidates having '
    "Master's Degree with Research/Teaching experience at a recognised University will be "
    'eligible for relaxation in upper age to the extent of the years of such experience subject '
    'to a maximum of three years.')

#: An exemption in item a), a certificate rule for other groups in item b).
EXEMPTION_THEN_CERTIFICATE = (
    'Application Fee: GEN/OBC/EWS Application fee including Intimation Charges Rs. 850/- . '
    'SC/ST/PwBD Intimation Charges only Rs. 100/- . a) Fee once paid will not be refunded. '
    'SC/ST/PwBD candidates are exempt from payment of Application Fee but will have to pay '
    'specified Intimation Charges. b) Candidates seeking reservation as SC/ST/OBC, shall have to '
    'produce a certificate in the prescribed proforma from the designated authority.')

#: List items joined across unrelated instructions; the exemption sits far from the group.
JOINED_LIST_ITEMS = (
    'Examination Fee: Each applicant must pay Rs. 200/- towards the examination fee. '
    'This stipulation is to avoid any sort of human interface in evaluation of the Scripts. '
    'b) Tampering of OMR answer sheet by using whitener leads to invalidation. c) No request '
    'for reconsideration will be entertained. 10) A) The following certificates must be '
    'submitted: i) Hall Ticket ii) Ex-Servicemen discharge book iii) certificate of the '
    'candidates who are exempted from payment of the fee under the rules.')

SHARED_PAPER_MARKS = (
    'Scheme of Phase-II Examination. Paper-II Descriptive Type (on Economics) 90 Minutes 50 '
    'Total 120 Minutes 100 Grand Total 300 @For both Paper-I and Paper-III, there will be 30 '
    'questions and 50 marks for Objective questions (some questions carrying 2 marks each).')

INCIDENTAL_VACANCY_NUMBER = (
    'Preference of posts. As the vacancies are related to 22 offices, the preferences are to be '
    'given for all offices. For instance, in the above case vacancies are available in only 9 '
    'offices.')

CONFLICTING_TOTALS = (
    'There are 120 vacancies in the notification. The number of vacancies is 135, including '
    'backlog vacancies.')

# The phrasings real notices use for correct facts; none may stop publishing.
CORRECT_VACANCIES = 'Vacancies: There are approx. 12,256 vacancies. The vacancies are tentative.'
CORRECT_QUALIFICATION = ('Educational Qualification: Candidates must possess a Bachelor\'s Degree '
                         'from a recognised University or equivalent.')
CORRECT_EXEMPTION = ('10.1 Fee payable: Rs. 100/- (Rupees One Hundred only). 10.2 Women '
                     'candidates and candidates belonging to Scheduled Castes (SC), Scheduled Tribes '
                     '(ST), Persons with Benchmark Disabilities (PwBD) and Ex-servicemen (ESM) are '
                     'exempted from payment of fee.')
CORRECT_EXEMPTION_LIST = ('8.2 Examination Fee: Each applicant has to pay Rs. 120/- towards the '
                          'Examination Fee. However, the following category of candidates are '
                          'exempted from payment of Examination fee: a) BC, SC & ST candidates b) '
                          'Unemployed candidates.')


# ============================================================ the five failures, generically
class TestTheFiveFailures(unittest.TestCase):

    def test_a_row_serial_is_not_a_vacancy_count(self):
        got = read('vacancies', FLATTENED_VACANCY_TABLE)
        self.assertFalse(published(got) and got.value == 1, (got.status, got.value, got.note))

    def test_an_age_relaxation_clause_is_not_the_qualification(self):
        got = read('qualification', AGE_RELAXATION_ONLY)
        text = json.dumps(got.value) if got and got.value else ''
        self.assertFalse(published(got) and 'relaxation' in text, (got.status, text[:120]))

    def test_an_exemption_does_not_reach_the_next_list_item(self):
        for field in ('fee', 'feeExemptions'):
            got = read(field, EXEMPTION_THEN_CERTIFICATE)
            text = json.dumps(got.value).lower() if got and got.value else ''
            leaked = 'obc' in text and ('"isexempt": true' in text.replace(' ', ' ')
                                        or 'exemptions' in text)
            if field == 'feeExemptions':
                leaked = any('obc' in str(x.get('category', '')).lower() for x in (got.value or []))
            else:
                leaked = any('obc' in str(r.get('scope', '')).lower() and r.get('isExempt')
                             for r in (got.value or {}).get('rules', []))
            self.assertFalse(published(got) and leaked, (field, got.status, text[:200]))

    def test_a_category_label_or_table_residue_is_not_a_post(self):
        got = read('posts', FLATTENED_VACANCY_TABLE, html=VACANCY_TABLE_HTML)
        names = [str(p.get('postName', '')) for p in (got.value or [])] if got else []
        bad = [n for n in names if n in ('GEN/UR', 'EWS') or '&' in n and ';' in n
               or n.lower().startswith('abbreviation')]
        self.assertFalse(published(got) and bad, (got.status, names))

    def test_marks_shared_by_two_papers_are_not_one_papers_marks(self):
        got = read('examPattern', SHARED_PAPER_MARKS)
        papers = (got.value or {}).get('papers', []) if got and isinstance(got.value, dict) else []
        bad = [p for p in papers if str(p.get('name', '')).lower().startswith('and ')
               or 'there will be' in str(p.get('name', ''))]
        self.assertFalse(published(got) and bad, (got.status, papers))


# ========================================================================= the wider class
class TestScopeAndRole(unittest.TestCase):

    def test_a_number_bound_to_another_noun_is_not_a_vacancy_count(self):
        got = read('vacancies', INCIDENTAL_VACANCY_NUMBER)
        self.assertFalse(published(got) and got.value in (22, 9), (got.status, got.value))

    def test_a_category_count_in_a_total_row_is_not_the_total(self):
        # "Total 20 5 10 10 5 50": the first figure after "Total" is a category column's total.
        from .attribution import check_vacancies
        for n in (20, 1):
            v = check_vacancies(n, FLATTENED_VACANCY_TABLE, FLATTENED_VACANCY_TABLE)
            self.assertFalse(v.ok, (n, v))

    def test_a_lone_number_bound_to_another_noun_is_not_a_vacancy_count(self):
        # With only one such figure there is no conflict to hold it back.
        got = read('vacancies', 'Preference of offices. As the vacancies are related to 22 offices, '
                                'the preferences are to be given for all offices.')
        self.assertFalse(published(got) and got.value == 22, (got.status, got.value))

    def test_one_stream_count_is_not_the_recruitments_total(self):
        # A document with several streams: a stream's row is a component, never the total.
        got = read('vacancies', FLATTENED_VACANCY_TABLE)
        self.assertFalse(published(got) and got.value in (40, 10, 16), (got.status, got.value))

    def test_joined_list_items_do_not_carry_an_exemption_across(self):
        got = read('feeExemptions', JOINED_LIST_ITEMS)
        cats = [str(x.get('category', '')).lower() for x in (got.value or [])] if got else []
        self.assertFalse(published(got) and any('servicemen' in c for c in cats), (got.status, cats))

    def test_conflicting_evidence_is_not_resolved_by_picking(self):
        got = read('vacancies', CONFLICTING_TOTALS)
        self.assertFalse(published(got), (got.status, got.value))

    def test_a_table_cell_is_not_read_from_the_wrong_column(self):
        # The header names "Post" over the serial column; the post names are one column right.
        got = read('posts', FLATTENED_VACANCY_TABLE, html=VACANCY_TABLE_HTML)
        names = [str(p.get('postName', '')) for p in (got.value or [])] if got else []
        self.assertFalse(published(got) and any(n.strip() in ('1', '2', '&nbsp;', '') for n in names),
                         names)


class TestCorrectFactsStillPublish(unittest.TestCase):

    def test_vacancies(self):
        got = read('vacancies', CORRECT_VACANCIES)
        self.assertTrue(published(got), (got.status, got.note))

    def test_qualification(self):
        got = read('qualification', CORRECT_QUALIFICATION)
        self.assertTrue(published(got), (got.status, got.note))

    def test_exemption_in_one_clause(self):
        got = read('feeExemptions', CORRECT_EXEMPTION)
        self.assertTrue(published(got), (got.status, got.note))
        cats = {str(x.get('category', '')).lower() for x in got.value}
        self.assertTrue(any('women' in c for c in cats) and any('servicemen' in c or 'esm' in c for c in cats), cats)

    def test_a_free_text_group_is_not_a_reservation_category(self):
        # Only reservation categories are collected sentence-wide and can leak; a group recorded
        # in words is the exempting sentence's own subject and is left to the reader.
        from .attribution import check_exemptions
        v = [{'category': 'Applied under the cancelled notification: no fee again', 'isExempt': True}]
        r = check_exemptions('feeExemptions', v, 'Candidates who applied earlier need not pay again.')
        self.assertEqual(r.out_of_scope, [])

    def test_exemption_introduced_by_a_lead_in(self):
        got = read('feeExemptions', CORRECT_EXEMPTION_LIST)
        self.assertTrue(published(got), (got.status, got.note))


# ======================================================== each rule, where it alone decides
class TestEachRuleAlone(unittest.TestCase):
    """One fixture per rule, built so no other rule would catch it: removing any one rule
    must turn exactly its own test red."""

    def vac(self, span, n):
        from .attribution import check_vacancies
        return check_vacancies(n, span, span).ok

    def test_count_labels_between_noun_and_figure(self):
        self.assertFalse(self.vac('Number of vacancies GEN UR 40.', 40))
        self.assertTrue(self.vac('Number of vacancies: 40.', 40))

    def test_count_another_figure_between(self):
        self.assertFalse(self.vac('Total: 12 - 40.', 40))
        self.assertTrue(self.vac('Total: 40.', 40))

    def test_count_zero_padded_figure(self):
        self.assertTrue(self.vac('There are 05 vacancies.', 5))

    def test_count_a_component_is_not_the_total(self):
        # "including 06 vacancies for NCC": a share of the total, stated as such.
        self.assertFalse(self.vac('90 posts [including 06 vacancies for NCC Certificate holders]', 6))
        self.assertFalse(self.vac('of which 12 vacancies are reserved for Ex-Servicemen', 12))
        self.assertTrue(self.vac('90 posts [including 06 vacancies for NCC Certificate holders]', 90))

    def test_count_figure_opening_another_noun(self):
        self.assertFalse(self.vac('Number of vacancies: 22 offices.', 22))
        self.assertTrue(self.vac('Number of vacancies: 22.', 22))

    def test_qualification_an_age_requirement_is_not_an_education_requirement(self):
        from .attribution import check_qualification
        text = ('Candidates must have attained the age of 21 years on the date of the degree '
                'examination result, and the upper age is relaxed by 3 years.')
        self.assertFalse(check_qualification({'text': text}, text, text).ok)
        good = 'Candidates must possess a degree; the upper age is relaxed by 3 years for some.'
        self.assertTrue(check_qualification({'text': good}, good, good).ok)

    def test_posts_category_label(self):
        from .attribution import check_posts
        self.assertFalse(check_posts([{'postName': 'GEN/UR'}, {'postName': 'Assistant Officer'}]).ok)

    def test_posts_markup_residue(self):
        from .attribution import check_posts
        self.assertFalse(check_posts([{'postName': 'Assistant&nbsp;Officer'}]).ok)

    def test_posts_serial_number(self):
        from .attribution import check_posts
        self.assertFalse(check_posts([{'postName': '12'}, {'postName': 'Assistant Officer'}]).ok)
        self.assertTrue(check_posts([{'postName': 'Assistant Officer'},
                                     {'postName': 'Deputy Collector (Executive Branch)'}]).ok)

    def test_posts_a_long_designation_is_still_a_designation(self):
        # Real designations from a state commission's notice: long, verbless, correct.
        from .attribution import check_posts
        self.assertTrue(check_posts([
            {'postName': 'District Backward Classes Welfare Officer including Assistant Director '
                         '(District Backward Classes Development Officer) (Backward Classes Welfare Service)'},
            {'postName': 'Assistant Treasury Officer / Assistant Accounts Officer / Assistant Lecturer '
                         'in the Training College and School (Treasuries and Accounts Service)'}]).ok)

    def test_posts_a_sentence(self):
        from .attribution import check_posts
        self.assertFalse(check_posts([{'postName': 'The candidates selected will be posted anywhere '
                                                   'in the country as required'}]).ok)

    def test_pattern_prose_fragment_as_a_name(self):
        from .attribution import check_pattern
        v = {'papers': [{'label': 'Paper-I', 'name': 'there will be 30 questions', 'marks': 50}]}
        self.assertFalse(check_pattern(v, 'Paper-I there will be 30 questions 50 marks').ok)
        ok = {'papers': [{'label': 'Paper-I', 'name': 'General Awareness', 'marks': 100}]}
        self.assertTrue(check_pattern(ok, 'Paper-I General Awareness 100 marks').ok)


# ================================================================ Claude's part
#: The completeness check asks a different question; these tests are about attribution, so it is
#: answered "whole" and never decides one of them.
WHOLE = {'complete': True, 'continues_after': False, 'starts_mid_unit': False, 'confidence': 'high', 'reason': ''}


def FakeProvider(reply, enabled=True, fail=None):
    """A scripted Claude gateway that answers the attribution and date-role questions with `reply` (a
    dict, or a raw string for a malformed reply) and the completeness question with "whole"."""
    return FakeClaude(ByOperation({Operation.CLASSIFY_ATTRIBUTION: reply, Operation.CLASSIFY_DATE: reply,
                                   Operation.CHECK_COMPLETENESS: WHOLE}),
                      enabled=enabled, fail=InfraStatus.CLAUDE_CLI_FAILED if fail else None)


class TestModelOnlyWithholds(unittest.TestCase):

    SPAN = "Candidates must possess a Bachelor's Degree from a recognised University or equivalent."

    def reply(self, **over):
        out = {'role': 'qualification_requirement', 'supports_value': True, 'scope': 'all posts',
               'evidence_span': self.SPAN, 'confidence': 'high', 'conflicts': []}
        out.update(over)
        return out

    def test_a_supported_fact_stays_published(self):
        got = read('qualification', CORRECT_QUALIFICATION, gateway=FakeProvider(self.reply()))
        self.assertTrue(published(got), got.note)

    def test_an_unsupported_claim_is_withheld(self):
        got = read('qualification', CORRECT_QUALIFICATION,
                   gateway=FakeProvider(self.reply(supports_value=False)))
        self.assertFalse(published(got))

    def test_evidence_not_in_the_source_is_withheld(self):
        got = read('qualification', CORRECT_QUALIFICATION,
                   gateway=FakeProvider(self.reply(evidence_span='Candidates must hold a PhD.')))
        self.assertFalse(published(got))

    def test_evidence_from_the_wrong_scope_is_withheld(self):
        got = read('qualification', CORRECT_QUALIFICATION,
                   gateway=FakeProvider(self.reply(role='age_relaxation')))
        self.assertFalse(published(got))

    def test_an_ambiguous_scope_is_withheld(self):
        got = read('qualification', CORRECT_QUALIFICATION,
                   gateway=FakeProvider(self.reply(conflicts=['applies only to one stream'])))
        self.assertFalse(published(got))

    def test_an_unreachable_model_withholds(self):
        got = read('qualification', CORRECT_QUALIFICATION, gateway=FakeProvider({}, fail='down'))
        self.assertFalse(published(got))
        self.assertIn('could not check', got.note)          # withheld for this reason, not another

    def test_the_model_cannot_rescue_a_fact_the_checks_refused(self):
        p = FakeProvider(self.reply(role='total_vacancies', evidence_span='Vacancies GEN/UR'))
        got = read('vacancies', FLATTENED_VACANCY_TABLE, gateway=p)
        self.assertFalse(published(got) and got.value == 1)
        self.assertEqual(p.calls, 0)

    def test_the_model_cannot_create_a_fact(self):
        p = FakeProvider(self.reply(evidence_span='x'))
        got = read('qualification', 'The Commission will announce the schedule later.', gateway=p)
        self.assertFalse(published(got))
        self.assertEqual(p.calls, 0)


if __name__ == '__main__':
    unittest.main()
