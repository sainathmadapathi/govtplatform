"""Trusted-secondary ingestion: the reviewed-source registry, reading a reviewed source for one exam,
the claims it yields, the cross-check against the official record -- and the rule above all of them:
no secondary source can make an official fact publishable without official evidence.

Everything runs over `secondary_fixture_site` (an invented portal) and the shipped registry file. No
test reaches the network, and Claude is a ForbiddenClaude throughout: this layer never calls it.
"""
from __future__ import annotations

import io
import json
import os
import shutil
import tempfile
import unittest
from unittest import mock

from tools.claude_cli import testing  # noqa: F401  (marks the process as under test)
from tools.claude_cli.exam_fixtures import NoNetwork
from tools.claude_cli.testing import ForbiddenClaude, use_gateway

from . import secondary_ingestion as SI
from .authority_discovery import discover_authority, project_for_exam
from .authority_fixture_site import AUTHORITY, ROOT, FakeSite
from .claims import Resolution, SourceClaim, reconcile
from .discover import DocKind
from .evidence import EvidenceStatus
from .schema import (AdmitCardNotice, AnswerEntry, AnswerKey, AnswerStatus, ExamIdentity, Fact, OfficialQuestion,
                     PaperIdentity, ResultDeclaration, SourceEvidence, SourceStatus, Status, UniversalExam)
from .secondary_fixture_site import (DOMAIN, EXAM, INJECTION, KEY_PAGE, OFFICIAL_NOTICE, PAPERS, PROFILE, RESULTS,
                                     SecondarySite)
from .source_graph import SourceClass
from .source_trust import DEFAULT_PROFILE_PATH, TrustRegistry, classify_source

TGPSC = 'Telangana Public Service Commission'


class Guarded(unittest.TestCase):
    """No network, and a Claude that fails the test if anything asks it."""

    def setUp(self):
        self.net = NoNetwork().__enter__()
        gw = use_gateway(ForbiddenClaude('trusted-secondary ingestion must never call Claude'))
        gw.__enter__()
        self.addCleanup(gw.__exit__, None, None, None)
        self.addCleanup(self._no_network)
        self.tmp = tempfile.mkdtemp(prefix='govos-secondary-')
        self.addCleanup(shutil.rmtree, self.tmp, True)

    def _no_network(self):
        self.net.__exit__(None, None, None)
        self.assertEqual(self.net.attempts, [], 'the test reached for the network')

    def registry_file(self, *profiles) -> str:
        path = os.path.join(self.tmp, 'profiles.json')
        with io.open(path, 'w', encoding='utf-8') as fh:
            json.dump({'profiles': list(profiles)}, fh)
        return path

    def source(self, profile=None):
        sources, problems = SI.load_reviewed_sources(self.registry_file(profile or PROFILE))
        self.assertEqual(problems, [])
        return sources[DOMAIN]

    def ingest(self, *, site=None, exam=None, **kw):
        site = site or SecondarySite()
        return SI.ingest_secondary(self.source(), exam or EXAM, fetch=site, **kw), site


# ============================================================ the registry
class RegistryTests(Guarded):
    def test_the_shipped_registry_reads_manabadi_as_trusted_secondary_for_tgpsc_only(self):
        sources, problems = SI.load_reviewed_sources()
        self.assertEqual(problems, [])
        manabadi = sources['manabadi.co.in']
        self.assertEqual((manabadi.profile.source_class, manabadi.profile.review_status), ('TRUSTED_SECONDARY', 'REVIEWED'))
        self.assertTrue(manabadi.profile.reviewed_by and manabadi.profile.last_reviewed and manabadi.profile.notes)
        self.assertTrue(all('manabadi.co.in' in e.url for e in manabadi.entry_points))
        self.assertEqual(TrustRegistry.load().rejected, [])
        reg = TrustRegistry.load()
        for role in (DocKind.QUESTION_PAPER, DocKind.NOTIFICATION, DocKind.RESULT):
            cls, _ = classify_source('https://www.manabadi.co.in/x.asp', estates=['tgpsc.gov.in'], role=role,
                                     registry=reg, authority=TGPSC)
            self.assertIs(cls, SourceClass.TRUSTED_SECONDARY, role)
        cls, why = classify_source('https://www.manabadi.co.in/x.asp', estates=['tgpsc.gov.in'], role=DocKind.STUDY_MATERIAL,
                                   registry=reg, authority=TGPSC)
        self.assertIs(cls, SourceClass.SECONDARY, 'a role the review does not name')
        cls, _ = classify_source('https://www.manabadi.co.in/x.asp', estates=['ssc.gov.in'], role=DocKind.NOTIFICATION,
                                 registry=reg, authority='Staff Selection Commission')
        self.assertIs(cls, SourceClass.SECONDARY, 'an authority the review does not cover')

    def test_a_review_that_is_wrong_anywhere_is_refused_whole(self):
        bad = [
            dict(PROFILE, domain='pending.example.in', review_status='PENDING'),
            dict(PROFILE, domain='official.example.in', source_class='PRIMARY_OFFICIAL'),
            dict(PROFILE, domain='offsite.example.in'),          # its listings are on studyportal, not on itself
            dict(PROFILE, domain=DOMAIN, ingestion={'entryPoints': [{'url': PAPERS, 'lists': 'NOT_A_ROLE'}]}),
            dict(PROFILE, domain='quiet.example.in', ingestion=None),
        ]
        sources, problems = SI.load_reviewed_sources(self.registry_file(*bad))
        self.assertEqual(sources, {}, 'nothing in that file may be read')
        text = json.dumps(problems)
        self.assertIn('only a REVIEWED source is read', text)
        self.assertIn('officiality comes from the authority', text)
        self.assertIn('is not on offsite.example.in', text)
        self.assertIn('unknown role', text)
        self.assertNotIn('quiet.example.in', text, 'a profile with no ingestion block is classified, not read: no problem')

    def test_a_missing_registry_reads_nothing(self):
        sources, problems = SI.load_reviewed_sources(os.path.join(self.tmp, 'absent.json'))
        self.assertEqual(sources, {})
        self.assertTrue(problems)


# ============================================================ reading the source
class IngestionTests(Guarded):
    def setUp(self):
        super().setUp()
        self.out, self.site = self.ingest()
        self.res = {r['title']: r for r in self.out.resources}

    def test_only_this_exams_items_are_kept_each_with_its_provenance(self):
        self.assertEqual(set(self.res), {
            'EPSC Group 1 Notification 2026 Out', 'EPSC Group 1 Results 2026 OUT',
            'EPSC Group 1 2026 Answer Key English & Telugu key', 'EPSC Group 1 2026 Mains Hall Ticket',
            'EPSC Group 1 Notification 2022', 'EPSC Group 1 2022 Master Question Paper and Answer Key',
            'EPSC Group-1 2022 Master Paper and Key'})
        notice = self.res['EPSC Group 1 Notification 2026 Out']
        self.assertEqual(notice['foundOn'], [SI.normalize_url(PROFILE['ingestion']['entryPoints'][0]['url'])])
        self.assertEqual(notice['anchors'], ['EPSC Group 1 Notification 2026 Out'])
        self.assertTrue(notice['fetched'] and notice['contentHash'] and notice['retrievedAt'])
        self.assertEqual(notice['sourceDomain'], DOMAIN)
        self.assertEqual(notice['review']['reviewedBy'], 'test reviewer')
        listing = self.out.listings[0]
        self.assertTrue(listing['ok'] and listing['contentHash'])
        self.assertEqual(listing['otherItems'], 2, 'the Group-2 notice and the "Gr-1" grade post')

    def test_a_listed_paper_keeps_the_title_and_facts_of_its_block_and_its_file_address(self):
        paper = self.res['EPSC Group-1 2022 Master Paper and Key']
        self.assertEqual((paper['role'], paper['relation'], paper['cycle']), ('QUESTION_PAPER', 'THIS_EXAM_OTHER_CYCLE', '2022'))
        self.assertEqual(paper['fields']['QP.Type/Year'], 'Previous Year/2022')
        self.assertTrue(paper['embeddedFile'].endswith('g1-2022-master.pd'), 'kept as printed, even truncated')
        self.assertFalse(paper['fetched'], 'another cycle is recorded, not read')

    def test_every_resource_is_secondary_and_trusted_only_for_the_roles_the_review_names(self):
        classes = {r['title']: r['sourceClass'] for r in self.out.resources}
        self.assertNotIn('PRIMARY_OFFICIAL', classes.values())
        self.assertEqual(classes['EPSC Group 1 2026 Mains Hall Ticket'], 'SECONDARY', 'ADMIT_CARD is not a reviewed role')
        self.assertEqual(classes['EPSC Group 1 Notification 2026 Out'], 'TRUSTED_SECONDARY')
        self.assertEqual(self.res['EPSC Group 1 Notification 2026 Out']['sourceLabel'], 'Trusted secondary source')

    def test_even_a_classifier_that_said_official_could_not_make_a_secondary_page_official(self):
        with mock.patch.object(SI, 'classify_source', lambda *a, **k: (SourceClass.PRIMARY_OFFICIAL, 'forced')):
            out, _ = self.ingest()
        self.assertEqual({r['sourceClass'] for r in out.resources}, {'SECONDARY'})
        self.assertNotIn('PRIMARY_OFFICIAL', {c['sourceClass'] for c in out.claims})

    def test_links_to_the_authority_are_leads_never_official_and_other_sites_are_ignored(self):
        urls = {p['url'] for p in self.out.pointers}
        self.assertEqual(urls, {ROOT, OFFICIAL_NOTICE})
        self.assertTrue(all('never official because a secondary source links to it' in p['note'] for p in self.out.pointers))
        self.assertFalse([r for r in self.out.resources if 'elsewhere.example.com' in r['url']])
        self.assertNotIn(OFFICIAL_NOTICE, self.site.calls, 'a pointer is not followed from here')

    def test_what_could_not_be_read_is_said_so(self):
        why = ' '.join(u['why'] for u in self.out.unexplored)
        self.assertIn('items 1-2 of 9', why, 'a paged listing says how much was on its first page')
        self.assertIn('redirected off studyportal.example.in', why)
        self.assertIn('could not be read', self.res['EPSC Group 1 2026 Mains Hall Ticket']['note'])

    def test_the_page_budget_holds(self):
        out, site = self.ingest(max_item_pages=1)
        item_pages = [u for u in site.calls if u not in {e['url'] for e in PROFILE['ingestion']['entryPoints']}]
        self.assertEqual(len(item_pages), 1)
        self.assertIn('page budget (1) was used', ' '.join(u['why'] for u in out.unexplored))

    def test_an_authority_the_review_does_not_cover_is_refused(self):
        other = dict(EXAM, authorityName='Some Other Commission', officialDomain='https://www.other.gov.in')
        with self.assertRaises(SI.IngestionRefused):
            self.ingest(exam=other)

    def test_the_authoritys_own_site_is_never_read_as_a_secondary_source(self):
        own = dict(PROFILE, domain='epsc.gov.in', authority_coverage=['epsc.gov.in'],
                   ingestion={'entryPoints': [{'url': 'https://www.epsc.gov.in/notifications.jsp', 'lists': 'NOTIFICATION',
                                               'authority': AUTHORITY, 'estates': ['epsc.gov.in']}]})
        sources, _ = SI.load_reviewed_sources(self.registry_file(own))
        with self.assertRaises(SI.IngestionRefused):
            SI.ingest_secondary(sources['epsc.gov.in'], EXAM, fetch=FakeSite())


# ============================================================ claims
class ClaimTests(Guarded):
    def setUp(self):
        super().setUp()
        self.out, _ = self.ingest()
        self.claims = self.out.claims

    def by_field(self, name):
        return [c for c in self.claims if c['field'] == name]

    def test_table_rows_become_claims_with_the_exact_words_checked_against_the_page(self):
        self.assertEqual({c['value'] for c in self.by_field('application_close')}, {'2026-01-30'})
        (close,) = self.by_field('application_close')
        self.assertEqual((close['quotation'], close['quotationStatus'], close['origin']),
                         ('Online Application Last Date 30/01/2026', 'VERIFIED', 'table'))
        self.assertEqual({c['value'] for c in self.by_field('edit_window_start')}, {'2026-02-05'})
        self.assertEqual({c['value'] for c in self.by_field('exam_stage_1_months')}, {'2026-05/2026-06'})
        self.assertEqual({c['value'] for c in self.by_field('exam_stage_2_end')}, {'2026-10-16'},
                         'an "Exam Date" row is placed by the table\'s own "Exam Name" row')
        self.assertTrue(all(c['quotationStatus'] == 'VERIFIED' for c in self.claims))

    def test_a_sibling_exams_table_and_a_group_number_are_not_read_as_this_exams_counts(self):
        self.assertEqual({c['value'] for c in self.by_field('vacancies_total')}, {'120'},
                         'not 783 (the Group-2 table), not 1 ("Group 1 posts")')

    def test_text_addressed_to_an_ai_changes_nothing(self):
        self.assertFalse([c for c in self.claims if 'ignore previous' in c['quotation'].lower()])
        self.assertNotIn('PRIMARY_OFFICIAL', {c['sourceClass'] for c in self.claims})
        self.assertIn(INJECTION.split('.')[0], SI.visible_text(SecondarySite().pages[SI.normalize_url(
            'https://www.studyportal.example.in/articles/epsc-group-1-notification.asp')]))

    def test_a_listing_line_is_the_sources_statement_that_a_document_exists(self):
        (key,) = self.by_field('listed:ANSWER_KEY')
        self.assertEqual((key['quotation'], key['sourceUrl']), ('EPSC Group 1 2026 Answer Key English & Telugu key',
                                                               SI.normalize_url(RESULTS)))
        self.assertIn(SI.normalize_url(KEY_PAGE), [r['url'] for r in self.out.resources])

    def test_a_claim_whose_cycle_is_another_or_unstated_is_never_compared(self):
        other = SI.SecondaryIngestion(source=DOMAIN, review={}, exam_id='e', exam_title='t', authority='a', cycle='2026')
        page = ('<html><head><title>EPSC Group 1 Notification</title></head><body><table>'
                '<tr><td>EPSC Group 1 Vacancy 2022</td></tr><tr><td>TOTAL</td><td>99</td></tr></table></body></html>')
        res = {'url': 'https://www.studyportal.example.in/a', 'title': 'x', 'relation': 'THIS_EXAM_CYCLE_UNSTATED',
               'cycle': '', 'sourceClass': 'TRUSTED_SECONDARY'}
        SI._claims_from_page(other, res, page, words=['group i'], siblings=['group ii'], cycle='2026', estates=[],
                             source=None)
        (claim,) = other.claims
        self.assertEqual((claim['value'], claim['cycle'], claim['compared']), ('99', '2022', False))


# ============================================================ the cross-check
class CrossCheckTests(Guarded):
    def setUp(self):
        super().setUp()
        walk = discover_authority([ROOT], authority_name=AUTHORITY, fetch=FakeSite(), registry=TrustRegistry())
        listing = project_for_exam(walk, exam_id=EXAM['id'], title=EXAM['title'], authority_name=AUTHORITY,
                                   authority_domain=ROOT, cycle='2026', sibling_words=['group-ii'])
        self.out, _ = self.ingest(official_listing=listing)
        self.r = {r['field']: r for r in self.out.resolutions}

    def test_agreeing_values_corroborate_and_the_official_value_governs(self):
        for name in ('vacancies_total', 'notification_date', 'application_open', 'edit_window_start', 'edit_window_end',
                     'exam_stage_1_months', 'exam_stage_2_start', 'exam_stage_2_end', 'listed:RESULT'):
            with self.subTest(field=name):
                self.assertEqual(self.r[name]['state'], 'OFFICIAL_CORROBORATED')
                self.assertTrue(self.r[name]['publishable'])
                self.assertTrue(all(g['sourceClass'] == 'PRIMARY_OFFICIAL' for g in self.r[name]['governing']))
                self.assertTrue(all(c['sourceClass'] == 'TRUSTED_SECONDARY' for c in self.r[name]['corroborations']))

    def test_a_source_repeating_a_date_the_authority_later_changed_is_recorded_and_told_so(self):
        close = self.r['application_close']
        self.assertEqual((close['state'], close['value']), ('OFFICIAL_CONTESTED', '2026-02-02'))
        self.assertEqual([c['value'] for c in close['conflicts']], ['2026-01-30'])
        self.assertIn('what the authority first printed', ' '.join(close['notes']))

    def test_a_value_the_record_does_not_hold_is_contested_never_adopted(self):
        result = self.r['result_release']
        self.assertEqual((result['state'], result['value']), ('OFFICIAL_CONTESTED', '2026-12-20'))
        self.assertIn('may describe a different event', ' '.join(result['notes']))

    def test_what_only_the_source_says_stays_its_claim_and_names_what_the_walk_found(self):
        key = self.r['listed:ANSWER_KEY']
        self.assertEqual((key['state'], key['value'], key['publishable']), ('SECONDARY_ONLY', None, False))
        notes = ' '.join(key['notes'])
        self.assertIn("GovOS's walk of the authority's site", notes)
        self.assertIn('never shown as the authority', notes)


# ============================================================ the rule
class NoSecondaryOfficialFactTests(Guarded):
    """A secondary source -- trusted or not, agreeing or not, any number of them -- can not make a value
    publishable as the authority's without official verbatim evidence."""

    def evidence(self, source_class):
        return SourceEvidence(source_id='s', url='https://www.studyportal.example.in/a', span='Vacancy 120',
                              span_status=EvidenceStatus.VERIFIED, source_class=source_class)

    def test_every_publication_rule_in_the_contract_refuses_secondary_only_evidence(self):
        paper = PaperIdentity(exam_id='exam-epsc-group-i-2026', cycle='2026', stage='Preliminary')
        builders = {
            'Fact': lambda ev: Fact.verified('120', ev),
            'AnswerEntry': lambda ev: AnswerEntry(question_number='1', paper=paper, accepted=['b'],
                                                  status=AnswerStatus.PUBLISHED, evidence=ev),
            'OfficialQuestion': lambda ev: OfficialQuestion(paper=paper, number='1', text='Which article ...?',
                                                            source_status=SourceStatus.OFFICIAL_VERIFIED, evidence=ev),
            'AnswerKey': lambda ev: AnswerKey(paper=paper, evidence=ev),
            'AdmitCardNotice': lambda ev: AdmitCardNotice(id='a', cycle='2026', status=Status.VERIFIED, evidence=ev),
            'ResultDeclaration': lambda ev: ResultDeclaration(id='r', cycle='2026', status=Status.VERIFIED, evidence=ev),
        }
        for name, build in builders.items():
            with self.subTest(contract=name):
                self.assertTrue(build([self.evidence('')]).is_publishable, 'official evidence publishes (control)')
                self.assertTrue(build([self.evidence('PRIMARY_OFFICIAL')]).is_publishable)
                for cls in ('TRUSTED_SECONDARY', 'SECONDARY', 'DISCOVERY_ONLY', 'UNVERIFIED'):
                    self.assertFalse(build([self.evidence(cls)]).is_publishable, cls)
                    self.assertFalse(build([self.evidence(cls)] * 5).is_publishable, f'five {cls} sources')

    def test_the_contracts_own_audit_flags_a_value_held_only_by_secondary_evidence(self):
        exam = UniversalExam(identity=ExamIdentity(exam_id='exam-epsc-group-i-2026'))
        exam.identity.official_name = Fact.verified('Group-I Services', self.evidence('TRUSTED_SECONDARY'))
        self.assertEqual(exam.unsourced_facts(), ['identity.official_name'])
        exam.identity.official_name = Fact.verified('Group-I Services', [self.evidence('TRUSTED_SECONDARY'),
                                                                         self.evidence('PRIMARY_OFFICIAL')])
        self.assertEqual(exam.unsourced_facts(), [], 'secondary evidence beside official evidence is corroboration')

    def test_reconciling_any_number_of_agreeing_secondary_sources_yields_no_value(self):
        claims = []
        for i, cls in enumerate([SourceClass.TRUSTED_SECONDARY] * 4 + [SourceClass.SECONDARY] * 4):
            c = SourceClaim('vacancies_total', '120', f'https://s{i}.example.in/x', cls, quotation='Vacancy 120')
            c.check_quotation('Vacancy 120')
            claims.append(c)
        r = reconcile('vacancies_total', claims)
        self.assertIs(r.state, Resolution.SECONDARY_ONLY)
        self.assertIsNone(r.value)
        fact = r.as_fact()
        self.assertEqual((fact.status, fact.value, fact.is_publishable), (Status.NEEDS_REVIEW, None, False))

    def test_every_fact_an_ingestion_yields_is_publishable_only_where_an_official_statement_governs(self):
        out, _ = self.ingest()
        self.assertTrue(out.resolutions)
        for row in out.resolutions:
            with self.subTest(field=row['field']):
                officially_governed = bool(row['governing']) and all(
                    g['sourceClass'] == 'PRIMARY_OFFICIAL' for g in row['governing'])
                self.assertEqual(row['publishable'], officially_governed)
                if not officially_governed:
                    self.assertIsNone(row['value'])
        for claim in out.claims:
            self.assertIn(claim['sourceClass'], ('TRUSTED_SECONDARY', 'SECONDARY'))
            ev = SourceClaim(claim['field'], claim['value'], claim['sourceUrl'], SourceClass(claim['sourceClass']),
                             quotation=claim['quotation'], quotation_status=EvidenceStatus(claim['quotationStatus'])
                             ).as_evidence()
            self.assertFalse(Fact.verified(claim['value'], ev).is_publishable, claim['field'])

    def test_with_no_official_record_nothing_the_source_says_is_publishable(self):
        bare = {k: v for k, v in EXAM.items() if k not in ('dates', 'vacanciesTotal', 'factEvidence', 'resultDeclarations')}
        out, _ = self.ingest(exam=bare)
        self.assertTrue(out.resolutions)
        self.assertEqual({r['state'] for r in out.resolutions}, {'SECONDARY_ONLY'})
        self.assertFalse([r for r in out.resolutions if r['publishable'] or r['value'] is not None])

    def test_the_layer_writes_nothing_and_offers_no_way_to_publish(self):
        source = self.source()                       # the test's own registry file is written here, before
        before = {n: os.path.getmtime(os.path.join(self.tmp, n)) for n in os.listdir(self.tmp)}
        SI.ingest_secondary(source, EXAM, fetch=SecondarySite())
        self.assertEqual({n: os.path.getmtime(os.path.join(self.tmp, n)) for n in os.listdir(self.tmp)}, before)
        public = {n for n in dir(SI) if not n.startswith('_')}
        self.assertFalse({n for n in public if any(w in n.lower() for w in ('publish', 'register', 'materialize', 'save'))})


if __name__ == '__main__':
    unittest.main()
