from datetime import datetime, timezone as dt_timezone
from unittest.mock import MagicMock, patch

from django.core.management import CommandError, call_command
from django.test import TestCase

from dbdb.core.models import CitationUrl, CitationUrlContent, SystemVersion
from dbdb.core.tests.test_citation_pdf import NSDI_PDF

_FIXTURES = [
    'adminuser.json',
    'core_features.json',
    'core_attributes.json',
    'core_system.json',
]

_PROCESS = 'dbdb.core.management.commands.process_citations.process_citation_url'
_REQUESTS_GET = 'dbdb.core.utils.citations.requests.get'

_CHECKED = datetime(2025, 6, 1, tzinfo=dt_timezone.utc)


def _pdf_response():
    resp = MagicMock()
    resp.status_code = 200
    resp.encoding = None
    resp.headers = {'Content-Type': 'application/pdf', 'Content-Length': str(len(NSDI_PDF))}
    resp.iter_content.return_value = [NSDI_PDF]
    resp.__enter__.return_value = resp
    return resp


def _redirect_response(location):
    resp = MagicMock()
    resp.status_code = 301
    resp.headers = {'Location': location}
    resp.__enter__.return_value = resp
    return resp


class ProcessCitationsTestBase(TestCase):
    """
    Runs process_citations with process_citation_url() replaced by a fake that
    records which URLs were processed, so no network requests are made.
    """

    fixtures = _FIXTURES

    def setUp(self):
        self.rza = CitationUrl.objects.create(url='https://rza.example.com/')
        self.gza = CitationUrl.objects.create(url='https://gza.example.com/', last_checked=_CHECKED, last_statuscode=404)
        self.odb = CitationUrl.objects.create(url='https://odb.example.com/', last_checked=_CHECKED, last_statuscode=200)
        self.rae = CitationUrl.objects.create(url='https://raekwon.example.com/')
        self.ftp = CitationUrl.objects.create(url='ftp://ghostface.example.com/')
        self.processed = []
        self.fake = None

    def _fake_process(self, c, **kwargs):
        self.processed.append(c.url)
        if self.fake:
            return self.fake(c, **kwargs)
        return c, {}

    def _run(self, *args):
        self.processed = []
        with patch(_PROCESS, side_effect=self._fake_process) as mock_process:
            call_command('process_citations', '--sleep', '0', *args)
        self.mock_process = mock_process
        return self.processed


class ProcessCitationsFilterTestCase(ProcessCitationsTestBase):

    def test_no_args_processes_all_http_urls_in_order(self):
        self.assertEqual(self._run(), [self.rza.url, self.gza.url, self.odb.url, self.rae.url])

    def test_positional_id(self):
        self.assertEqual(self._run(str(self.gza.id)), [self.gza.url])

    def test_positional_keyword(self):
        self.assertEqual(self._run('raekwon'), [self.rae.url])

    def test_positional_id_and_keyword_are_ored(self):
        self.assertEqual(self._run(str(self.gza.id), 'raekwon'), [self.gza.url, self.rae.url])

    def test_only_new(self):
        self.assertEqual(self._run('--only-new'), [self.rza.url, self.rae.url])

    def test_last_checked(self):
        self.assertEqual(self._run('--last-checked', '2026-01-01T00:00:00+00:00'), [self.gza.url, self.odb.url])

    def test_statuscode(self):
        self.assertEqual(self._run('--statuscode', '404'), [self.gza.url])

    def test_ignore_repeated(self):
        self.assertEqual(self._run('--ignore', 'gza', '--ignore', 'odb'), [self.rza.url, self.rae.url])

    def test_limit_processes_exactly_n(self):
        self.assertEqual(self._run('--limit', '3'), [self.rza.url, self.gza.url, self.odb.url])
        self.assertEqual(self._run('--limit', '1'), [self.rza.url])


class ProcessCitationsLoopTestCase(ProcessCitationsTestBase):

    def test_saves_processed_citation(self):
        def fake(c, **kwargs):
            c.last_title = 'Enter the Wu-Tang'
            return c, {}
        self.fake = fake
        self._run(str(self.rza.id))
        self.rza.refresh_from_db()
        self.assertEqual(self.rza.last_title, 'Enter the Wu-Tang')

    def test_error_propagates_without_skip_errors(self):
        def fake(c, **kwargs):
            raise RuntimeError('Protect Ya Neck')
        self.fake = fake
        with self.assertRaises(RuntimeError):
            self._run()
        self.assertEqual(self.processed, [self.rza.url])

    def test_skip_errors_continues(self):
        def fake(c, **kwargs):
            if c.id == self.gza.id:
                raise RuntimeError('Protect Ya Neck')
            return c, {}
        self.fake = fake
        self.assertEqual(self._run('--skip-errors'), [self.rza.url, self.gza.url, self.odb.url, self.rae.url])

    def test_merged_citation_is_not_saved(self):
        def fake(c, **kwargs):
            c.last_title = 'Should not be saved'
            return self.odb, None
        self.fake = fake
        self._run(str(self.rza.id))
        self.rza.refresh_from_db()
        self.assertIsNone(self.rza.last_title)

    def test_dry_run_is_passed_through(self):
        self._run(str(self.rza.id), '--dry-run')
        self.assertTrue(self.mock_process.call_args.kwargs['dry_run'])
        self._run(str(self.rza.id))
        self.assertFalse(self.mock_process.call_args.kwargs['dry_run'])


class ProcessCitationsOverrideTestCase(ProcessCitationsTestBase):

    def test_set_status(self):
        self.assertEqual(self._run('--set-status', 'dead', 'gza', 'odb'), [])
        statuses = dict(CitationUrl.objects.values_list('id', 'status'))
        self.assertEqual(statuses[self.gza.id], CitationUrl.Status.DEAD)
        self.assertEqual(statuses[self.odb.id], CitationUrl.Status.DEAD)
        self.assertEqual(statuses[self.rza.id], CitationUrl.Status.UNKNOWN)

    def test_set_title(self):
        self._run('--set-title', 'Liquid Swords', 'gza')
        self.gza.refresh_from_db()
        self.assertEqual(self.gza.last_title, 'Liquid Swords')

    def test_set_status_dry_run(self):
        self._run('--set-status', 'dead', '--set-title', 'Liquid Swords', '--dry-run', 'gza')
        self.gza.refresh_from_db()
        self.assertEqual(self.gza.status, CitationUrl.Status.UNKNOWN)
        self.assertIsNone(self.gza.last_title)

    def test_replace(self):
        self.assertEqual(self._run('--replace-from', 'raekwon', '--replace-to', 'chef'), [])
        self.rae.refresh_from_db()
        self.assertEqual(self.rae.url, 'https://chef.example.com/')

    def test_replace_merges_into_existing(self):
        self._run('--replace-from', 'raekwon', '--replace-to', 'rza')
        self.assertFalse(CitationUrl.objects.filter(id=self.rae.id).exists())
        self.assertTrue(CitationUrl.objects.filter(id=self.rza.id).exists())

    def test_replace_dry_run(self):
        self._run('--replace-from', 'raekwon', '--replace-to', 'chef', '--dry-run')
        self.rae.refresh_from_db()
        self.assertEqual(self.rae.url, 'https://raekwon.example.com/')

    def test_replace_requires_both_flags(self):
        with self.assertRaises(CommandError):
            self._run('--replace-from', 'raekwon')
        with self.assertRaises(CommandError):
            self._run('--replace-to', 'chef')


class ProcessCitationsOnlyTestCase(ProcessCitationsTestBase):

    def setUp(self):
        super().setUp()
        self.sv = SystemVersion.objects.get(system__slug='sqlite', is_current=True)
        self.sv.system_url = self.rza
        self.sv.docs_url = self.gza
        self.sv.save()
        self.sv.description_citations.add(self.rza, self.odb)

        # Referenced only by a non-current version
        self.old_sv = SystemVersion.objects.exclude(pk=self.sv.pk).first()
        SystemVersion.objects.filter(pk=self.old_sv.pk).update(system_url=self.rae, is_current=False)

    def test_only_fk_field(self):
        self.assertEqual(self._run('--only', 'system_url'), [self.rza.url])

    def test_only_repeated_dedupes(self):
        processed = self._run('--only', 'system_url', '--only', 'description_citations')
        self.assertEqual(processed, [self.rza.url, self.odb.url])

    def test_only_with_ignore(self):
        self.assertEqual(self._run('--only', 'system_url', '--only', 'docs_url', '--ignore', 'gza'), [self.rza.url])

    def test_only_with_only_new(self):
        self.assertEqual(self._run('--only', 'docs_url', '--only-new'), [])

    def test_only_with_limit(self):
        self.assertEqual(self._run('--only', 'system_url', '--only', 'docs_url', '--limit', '1'), [self.rza.url])

    def test_only_with_set_status(self):
        self._run('--only', 'docs_url', '--set-status', 'dead')
        statuses = dict(CitationUrl.objects.values_list('id', 'status'))
        self.assertEqual(statuses[self.gza.id], CitationUrl.Status.DEAD)
        self.assertEqual(statuses[self.rza.id], CitationUrl.Status.UNKNOWN)

    def test_only_excludes_non_current_versions(self):
        self.assertNotIn(self.rae.url, self._run('--only', 'system_url'))

    def test_only_invalid_field(self):
        with self.assertRaises(CommandError):
            self._run('--only', 'bogus')


class ProcessCitationsRealFetchTestCase(TestCase):
    """
    Runs the real process_citation_url() with requests.get mocked, to check
    what actually gets written to the database.
    """

    fixtures = _FIXTURES

    def setUp(self):
        self.paper = CitationUrl.objects.create(
            url='https://method.example.com/paper.pdf',
            status=CitationUrl.Status.DEAD,
            last_title='Tical',
            last_checked=_CHECKED,
        )

    def test_dry_run_writes_nothing(self):
        with patch(_REQUESTS_GET, side_effect=lambda *a, **kw: _pdf_response()):
            call_command('process_citations', '--sleep', '0', '--skip-spamcheck', '--dry-run', str(self.paper.id))
        self.paper.refresh_from_db()
        self.assertEqual(self.paper.status, CitationUrl.Status.DEAD)
        self.assertEqual(self.paper.last_title, 'Tical')
        self.assertEqual(self.paper.last_checked, _CHECKED)
        self.assertFalse(CitationUrlContent.objects.filter(citation=self.paper).exists())

    def test_without_dry_run_writes(self):
        with patch(_REQUESTS_GET, side_effect=lambda *a, **kw: _pdf_response()):
            call_command('process_citations', '--sleep', '0', '--skip-spamcheck', str(self.paper.id))
        self.paper.refresh_from_db()
        self.assertEqual(self.paper.status, CitationUrl.Status.VALID)
        self.assertGreater(self.paper.last_checked, _CHECKED)
        self.assertTrue(CitationUrlContent.objects.filter(citation=self.paper).exists())

    def test_normalize_dry_run_does_not_merge(self):
        dup = CitationUrl.objects.create(url='https://method.example.com/paper.pdf?utm_source=wutang')
        with patch(_REQUESTS_GET, side_effect=lambda *a, **kw: _pdf_response()) as mock_get:
            call_command('process_citations', '--sleep', '0', '--skip-spamcheck', '--normalize', '--dry-run', str(dup.id))
        mock_get.assert_not_called()
        dup.refresh_from_db()
        self.assertEqual(dup.url, 'https://method.example.com/paper.pdf?utm_source=wutang')

    def test_redirect_merge_does_not_reinsert_deleted_citation(self):
        old = CitationUrl.objects.create(url='https://method.example.com/old/paper.pdf')
        sv = SystemVersion.objects.get(system__slug='sqlite', is_current=True)
        sv.system_url = old
        sv.save()

        def fake_get(url, *args, **kwargs):
            if url == old.url:
                return _redirect_response(self.paper.url)
            return _pdf_response()

        with patch(_REQUESTS_GET, side_effect=fake_get):
            call_command('process_citations', '--sleep', '0', '--skip-spamcheck', str(old.id))
        self.assertFalse(CitationUrl.objects.filter(id=old.id).exists())
        sv.refresh_from_db()
        self.assertEqual(sv.system_url_id, self.paper.id)

    def _redirecting_get(self, from_url, to_url):
        def fake_get(url, *args, **kwargs):
            if url == from_url:
                return _redirect_response(to_url)
            return _pdf_response()
        return fake_get

    def test_redirect_rewrites_url_by_default(self):
        old = CitationUrl.objects.create(url='https://method.example.com/old/paper.pdf')
        new_url = 'https://method.example.com/new/paper.pdf'
        with patch(_REQUESTS_GET, side_effect=self._redirecting_get(old.url, new_url)):
            call_command('process_citations', '--sleep', '0', '--skip-spamcheck', str(old.id))
        old.refresh_from_db()
        self.assertEqual(old.url, new_url)

    def test_skip_redirect_keeps_url(self):
        old = CitationUrl.objects.create(url='https://method.example.com/old/paper.pdf')
        new_url = 'https://method.example.com/new/paper.pdf'
        with patch(_REQUESTS_GET, side_effect=self._redirecting_get(old.url, new_url)):
            call_command('process_citations', '--sleep', '0', '--skip-spamcheck', '--skip-redirect', str(old.id))
        old.refresh_from_db()
        self.assertEqual(old.url, 'https://method.example.com/old/paper.pdf')
        self.assertEqual(old.status, CitationUrl.Status.VALID)
        self.assertIsNotNone(old.last_checked)
        self.assertTrue(CitationUrlContent.objects.filter(citation=old).exists())

    def test_skip_redirect_does_not_merge_into_existing(self):
        old = CitationUrl.objects.create(url='https://method.example.com/old/paper.pdf')
        sv = SystemVersion.objects.get(system__slug='sqlite', is_current=True)
        sv.system_url = old
        sv.save()
        with patch(_REQUESTS_GET, side_effect=self._redirecting_get(old.url, self.paper.url)):
            call_command('process_citations', '--sleep', '0', '--skip-spamcheck',
                         '--only', 'system_url', '--skip-redirect')
        old.refresh_from_db()
        self.assertEqual(old.url, 'https://method.example.com/old/paper.pdf')
        sv.refresh_from_db()
        self.assertEqual(sv.system_url_id, old.id)

    def _redirecting_get(self, from_url, to_url):
        def fake_get(url, *args, **kwargs):
            if url == from_url:
                return _redirect_response(to_url)
            return _pdf_response()
        return fake_get

    def test_redirect_rewrites_url_by_default(self):
        old = CitationUrl.objects.create(url='https://method.example.com/old/paper.pdf')
        new_url = 'https://method.example.com/new/paper.pdf'
        with patch(_REQUESTS_GET, side_effect=self._redirecting_get(old.url, new_url)):
            call_command('process_citations', '--sleep', '0', '--skip-spamcheck', str(old.id))
        old.refresh_from_db()
        self.assertEqual(old.url, new_url)

    def test_skip_redirects_keeps_url(self):
        old = CitationUrl.objects.create(url='https://method.example.com/old/paper.pdf')
        new_url = 'https://method.example.com/new/paper.pdf'
        with patch(_REQUESTS_GET, side_effect=self._redirecting_get(old.url, new_url)):
            call_command('process_citations', '--sleep', '0', '--skip-spamcheck', '--skip-redirects', str(old.id))
        old.refresh_from_db()
        self.assertEqual(old.url, 'https://method.example.com/old/paper.pdf')
        self.assertEqual(old.status, CitationUrl.Status.VALID)
        self.assertIsNotNone(old.last_checked)
        self.assertTrue(CitationUrlContent.objects.filter(citation=old).exists())

    def test_skip_redirects_does_not_merge_into_existing(self):
        old = CitationUrl.objects.create(url='https://method.example.com/old/paper.pdf')
        sv = SystemVersion.objects.get(system__slug='sqlite', is_current=True)
        sv.system_url = old
        sv.save()
        with patch(_REQUESTS_GET, side_effect=self._redirecting_get(old.url, self.paper.url)):
            call_command('process_citations', '--sleep', '0', '--skip-spamcheck',
                         '--only', 'system_url', '--skip-redirects')
        old.refresh_from_db()
        self.assertEqual(old.url, 'https://method.example.com/old/paper.pdf')
        sv.refresh_from_db()
        self.assertEqual(sv.system_url_id, old.id)
