"""
Tests for the enrich_system management command's attribute-loading logic.

Attribute.sv_field stores the SystemVersion M2M field name (e.g. 'licenses'),
NOT the Attribute slug (e.g. 'license').  The query in enrich_system.handle()
must filter by sv_field__in=<sv-field-names> — the keys of M2M_ATTR_SLUGS —
not by the dict values, which are Attribute slugs used later for option lookups.
"""
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings

from dbdb.core.management.commands.enrich_system import (
    M2M_ATTR_SLUGS,
    Command as EnrichSystemCommand,
    _extract_twitter_handle,
)
from dbdb.core.management.commands.enrich_organization import (
    Command as EnrichOrgCommand,
    _validate_crunchbase_url,
    _validate_linkedin_url,
)
from dbdb.core.models import Attribute, AttributeOption, CitationUrl, CitationUrlContent, Organization, System, SystemVersion
from dbdb.core.utils.enrichment.base import BaseEnricher
from dbdb.core.utils.versions import clone_system_version

User = get_user_model()

_FIXTURES = [
    'adminuser.json',
    'core_features.json',
    'core_attributes.json',
    'core_system.json',
]

_ORG_FIXTURES = _FIXTURES + ['core_organizations.json']


def _options(**overrides):
    opts = {
        'dry_run': False,
        'recrawl_after': 7,
        'skip_spamcheck': True,
        'enricher': 'mock',
        'model': None,
        'skip_field': [],
        'fields': None,
        'per_feature': False,
        'include_urls': False,
        'mode': 'extract-urls',
    }
    opts.update(overrides)
    return opts


class MockEnricher(BaseEnricher):
    """LLM backend that returns a fixed dict without making any API calls."""

    def __init__(self, response: dict):
        self._response = response

    def call_llm(self, user_prompt, tool_schema, model_override=None, dry_run=False):
        return dict(self._response)


def _load_attributes_for_missing_fields(missing_fields: list[str]) -> list[Attribute]:
    """Mirror the production query from enrich_system.handle()."""
    missing_sv_fields = [f for f in missing_fields if f in M2M_ATTR_SLUGS]
    return list(
        Attribute.objects
        .filter(sv_field__in=missing_sv_fields)
        .order_by('sv_field')
    )


class EnrichSystemAttributeLoadingTestCase(TestCase):

    fixtures = ['core_features.json', 'core_attributes.json']

    def test_loads_only_the_requested_m2m_attributes(self):
        attrs = _load_attributes_for_missing_fields(['licenses', 'oses'])
        sv_fields = [a.sv_field for a in attrs]
        self.assertIn('licenses', sv_fields)
        self.assertIn('oses', sv_fields)
        self.assertNotIn('project_types', sv_fields)
        self.assertNotIn('written_in', sv_fields)

    def test_loads_all_m2m_attributes_when_all_fields_missing(self):
        attrs = _load_attributes_for_missing_fields(list(M2M_ATTR_SLUGS.keys()))
        returned_sv_fields = {a.sv_field for a in attrs}
        for sv_field in M2M_ATTR_SLUGS:
            if Attribute.objects.filter(sv_field=sv_field).exists():
                self.assertIn(
                    sv_field, returned_sv_fields,
                    f"Attribute with sv_field='{sv_field}' should be loaded when that field is missing",
                )

    def test_loads_no_attributes_when_no_m2m_fields_missing(self):
        attrs = _load_attributes_for_missing_fields(['description', 'history', 'start_year'])
        self.assertEqual(attrs, [])

    def test_sv_field_stores_field_names_not_attribute_slugs(self):
        """
        Regression guard: Attribute.sv_field stores SV field names ('licenses'),
        not Attribute slugs ('license').  Filtering by M2M_ATTR_SLUGS.values()
        is therefore wrong and returns far fewer results than filtering by keys.
        """
        correct = Attribute.objects.filter(sv_field__in=list(M2M_ATTR_SLUGS.keys()))
        regressed = Attribute.objects.filter(sv_field__in=list(M2M_ATTR_SLUGS.values()))
        self.assertGreater(
            correct.count(), regressed.count(),
            "sv_field__in=keys must match more Attributes than sv_field__in=values; "
            "if equal, the fixture data or M2M_ATTR_SLUGS may have changed",
        )


# ---------------------------------------------------------------------------
# _extract_twitter_handle unit tests
# ---------------------------------------------------------------------------

class ExtractTwitterHandleTestCase(TestCase):

    def test_full_twitter_url(self):
        self.assertEqual(_extract_twitter_handle('https://twitter.com/sqlite'), '@sqlite')

    def test_full_x_url(self):
        self.assertEqual(_extract_twitter_handle('https://x.com/sqlite'), '@sqlite')

    def test_bare_handle_with_at(self):
        self.assertEqual(_extract_twitter_handle('@sqlite'), '@sqlite')

    def test_bare_handle_without_at(self):
        self.assertEqual(_extract_twitter_handle('sqlite'), '@sqlite')

    def test_invalid_returns_none(self):
        self.assertIsNone(_extract_twitter_handle('https://example.com/nottwitter'))

    def test_empty_returns_none(self):
        self.assertIsNone(_extract_twitter_handle(''))


# ---------------------------------------------------------------------------
# _validate_linkedin_url unit tests
# ---------------------------------------------------------------------------

class ValidateLinkedInUrlTestCase(TestCase):

    def test_company_url_accepted(self):
        result = _validate_linkedin_url('https://www.linkedin.com/company/wu-tang-financial')
        self.assertEqual(result, 'https://www.linkedin.com/company/wu-tang-financial')

    def test_in_url_accepted(self):
        result = _validate_linkedin_url('https://linkedin.com/in/rza')
        self.assertEqual(result, 'https://www.linkedin.com/in/rza')

    def test_school_url_accepted(self):
        result = _validate_linkedin_url('https://www.linkedin.com/school/shaolin-school')
        self.assertEqual(result, 'https://www.linkedin.com/school/shaolin-school')

    def test_non_linkedin_returns_none(self):
        self.assertIsNone(_validate_linkedin_url('https://example.com/company/foo'))

    def test_empty_returns_none(self):
        self.assertIsNone(_validate_linkedin_url(''))


# ---------------------------------------------------------------------------
# _validate_crunchbase_url unit tests
# ---------------------------------------------------------------------------

class ValidateCrunchbaseUrlTestCase(TestCase):

    def test_organization_url_accepted(self):
        result = _validate_crunchbase_url('https://www.crunchbase.com/organization/ol-dirty-bastard-corp')
        self.assertEqual(result, 'https://www.crunchbase.com/organization/ol-dirty-bastard-corp')

    def test_person_url_accepted(self):
        result = _validate_crunchbase_url('https://crunchbase.com/person/rza')
        self.assertEqual(result, 'https://www.crunchbase.com/person/rza')

    def test_trailing_slash_stripped(self):
        result = _validate_crunchbase_url('https://www.crunchbase.com/organization/wu-tang/')
        self.assertEqual(result, 'https://www.crunchbase.com/organization/wu-tang')

    def test_non_crunchbase_returns_none(self):
        self.assertIsNone(_validate_crunchbase_url('https://example.com/organization/foo'))

    def test_empty_returns_none(self):
        self.assertIsNone(_validate_crunchbase_url(''))


# ---------------------------------------------------------------------------
# HomepageUrlSystemExtractionTestCase
# ---------------------------------------------------------------------------

_HOMEPAGE_HTML = (
    '<html><head></head><body>'
    '<a href="https://sqlite.org/docs">Docs</a>'
    '<a href="https://twitter.com/sqlite">Twitter</a>'
    '</body></html>'
)

_NO_OP_CRAWL = patch(
    'dbdb.core.management.commands.enrich_system.crawl_citation_url',
    return_value='',
)


@override_settings(DBDB_BOT_ACCOUNT='admin')
class HomepageUrlSystemExtractionTestCase(TestCase):

    fixtures = _FIXTURES

    def setUp(self):
        self.system = System.objects.get(slug='sqlite')
        self.current = SystemVersion.objects.get(system=self.system, is_current=True)
        self.admin_user = User.objects.get(username='admin')

        # Create a homepage CitationUrl and pre-populate its HTML content
        self.homepage = CitationUrl.objects.create(
            url='https://sqlite.org/',
            status=CitationUrl.Status.VALID,
        )
        CitationUrlContent.objects.create(citation=self.homepage, raw=_HOMEPAGE_HTML)

        # Wire the current version to the homepage
        self.current.system_url = self.homepage
        self.current.save(update_fields=['system_url'])

        self.cmd = EnrichSystemCommand()

    def _call(self, enricher, **opt_overrides):
        opts = _options(**opt_overrides)
        with _NO_OP_CRAWL:
            self.cmd._extract_urls_one(self.system, self.current, opts, enricher=enricher)

    def test_extracts_docs_url_creates_pending_version(self):
        # Pre-create the docs CitationUrl so the code reuses it (bypasses HTTP)
        docs_citation = CitationUrl.objects.create(
            url='https://sqlite.org/docs',
            status=CitationUrl.Status.VALID,
        )
        enricher = MockEnricher({'docs_url': 'https://sqlite.org/docs'})
        self._call(enricher)

        pending = self.system.pending_version()
        self.assertIsNotNone(pending, "A pending SystemVersion should have been created")
        self.assertEqual(pending.docs_url_id, docs_citation.pk)

    def test_extracts_twitter_handle_from_url(self):
        enricher = MockEnricher({'twitter_url': 'https://twitter.com/sqlite'})
        self._call(enricher)

        pending = self.system.pending_version()
        self.assertIsNotNone(pending)
        self.assertEqual(pending.twitter_handle, '@sqlite')

    def test_skips_when_all_fields_already_set(self):
        docs_citation = CitationUrl.objects.create(
            url='https://sqlite.org/docs',
            status=CitationUrl.Status.VALID,
        )
        blog_citation = CitationUrl.objects.create(
            url='https://sqlite.org/blog',
            status=CitationUrl.Status.VALID,
        )
        self.current.docs_url = docs_citation
        self.current.blog_url = blog_citation
        self.current.twitter_handle = '@sqlite'
        self.current.save(update_fields=['docs_url', 'blog_url', 'twitter_handle'])

        enricher = MockEnricher({'docs_url': 'https://sqlite.org/docs', 'twitter_url': 'https://twitter.com/sqlite'})
        self._call(enricher)

        self.assertIsNone(self.system.pending_version())

    def test_skips_when_no_system_url(self):
        self.current.system_url = None
        self.current.save(update_fields=['system_url'])

        enricher = MockEnricher({'twitter_url': 'https://twitter.com/sqlite'})
        self._call(enricher)

        self.assertIsNone(self.system.pending_version())

    def test_dry_run_does_not_create_pending_version(self):
        enricher = MockEnricher({'twitter_url': 'https://twitter.com/sqlite'})
        self._call(enricher, dry_run=True)

        self.assertIsNone(self.system.pending_version())

    def test_both_modes_share_single_pending_version(self):
        # Simulate what _enrich_one() would create: a pending SystemVersion
        pending = clone_system_version(
            self.current,
            approved=False,
            creator=self.admin_user,
            comment='enrich_one result',
        )

        # Now _extract_urls_one() should reuse the existing pending, not create a second
        enricher = MockEnricher({'twitter_url': 'https://twitter.com/sqlite'})
        self._call(enricher)

        all_pending = SystemVersion.objects.filter(system=self.system, approved=False)
        self.assertEqual(all_pending.count(), 1, "Only one pending SystemVersion should exist")
        pending.refresh_from_db()
        self.assertEqual(pending.twitter_handle, '@sqlite')

    def test_extracts_blog_url_creates_pending_version(self):
        blog_citation = CitationUrl.objects.create(
            url='https://sqlite.org/blog',
            status=CitationUrl.Status.VALID,
        )
        enricher = MockEnricher({'blog_url': 'https://sqlite.org/blog'})
        self._call(enricher)

        pending = self.system.pending_version()
        self.assertIsNotNone(pending, "A pending SystemVersion should have been created")
        self.assertEqual(pending.blog_url_id, blog_citation.pk)

    def test_invalid_docs_url_not_saved(self):
        # Patch process_citation_url to simulate an unreachable URL
        dead_result = {'status': CitationUrl.Status.DEAD}
        with patch(
            'dbdb.core.management.commands.enrich_system.process_citation_url',
            side_effect=lambda citation, **kw: (citation, dead_result),
        ):
            enricher = MockEnricher({'docs_url': 'https://this-url-fails.invalid/'})
            self._call(enricher)

        self.assertIsNone(self.system.pending_version())

    def test_dead_existing_docs_url_not_assigned(self):
        CitationUrl.objects.create(
            url='https://sqlite.org/docs',
            status=CitationUrl.Status.DEAD,
        )
        enricher = MockEnricher({'docs_url': 'https://sqlite.org/docs'})
        self._call(enricher)

        self.assertIsNone(self.system.pending_version())

    def test_dead_existing_blog_url_not_assigned(self):
        CitationUrl.objects.create(
            url='https://sqlite.org/blog',
            status=CitationUrl.Status.DEAD,
        )
        enricher = MockEnricher({'blog_url': 'https://sqlite.org/blog'})
        self._call(enricher)

        self.assertIsNone(self.system.pending_version())

    def test_relative_docs_url_resolved_against_homepage(self):
        docs_citation = CitationUrl.objects.create(
            url='https://sqlite.org/docs',
            status=CitationUrl.Status.VALID,
        )
        enricher = MockEnricher({'docs_url': '/docs'})
        self._call(enricher)

        pending = self.system.pending_version()
        self.assertIsNotNone(pending)
        self.assertEqual(pending.docs_url_id, docs_citation.pk)


# ---------------------------------------------------------------------------
# HomepageUrlOrgExtractionTestCase
# ---------------------------------------------------------------------------

_ORG_HOMEPAGE_HTML = (
    '<html><body>'
    '<a href="https://www.linkedin.com/company/wu-tang-financial">LinkedIn</a>'
    '</body></html>'
)

_NO_OP_ORG_CRAWL = patch(
    'dbdb.core.management.commands.enrich_organization.crawl_citation_url',
    return_value='',
)


@override_settings(DBDB_BOT_ACCOUNT='admin')
class HomepageUrlOrgExtractionTestCase(TestCase):

    fixtures = _ORG_FIXTURES

    def setUp(self):
        self.org = Organization.objects.get(slug='wu-tang-financial')

        self.homepage = CitationUrl.objects.create(
            url='https://wu-tang-financial.example/',
            status=CitationUrl.Status.VALID,
        )
        CitationUrlContent.objects.create(citation=self.homepage, raw=_ORG_HOMEPAGE_HTML)

        self.org.url = self.homepage
        self.org.linkedin_url = None
        self.org.save(update_fields=['url', 'linkedin_url'])

        self.cmd = EnrichOrgCommand()

    def _call(self, enricher, **opt_overrides):
        opts = _options(**opt_overrides)
        with _NO_OP_ORG_CRAWL:
            self.cmd._extract_urls_one(self.org, opts, enricher=enricher)

    def test_extracts_valid_linkedin_url(self):
        linkedin_url = 'https://www.linkedin.com/company/wu-tang-financial'
        CitationUrl.objects.create(url=linkedin_url, status=CitationUrl.Status.VALID)

        enricher = MockEnricher({'linkedin_url': linkedin_url})
        self._call(enricher)

        self.org.refresh_from_db()
        self.assertIsNotNone(self.org.linkedin_url_id)
        self.assertEqual(self.org.linkedin_url.url, linkedin_url)

    def test_rejects_invalid_linkedin_url(self):
        enricher = MockEnricher({'linkedin_url': 'https://example.com/notlinkedin'})
        self._call(enricher)

        self.org.refresh_from_db()
        self.assertIsNone(self.org.linkedin_url_id)

    def test_extracts_crunchbase_url(self):
        crunchbase_url = 'https://www.crunchbase.com/organization/wu-tang-financial'
        enricher = MockEnricher({'crunchbase_url': crunchbase_url})
        self._call(enricher)

        self.org.refresh_from_db()
        self.assertIsNotNone(self.org.crunchbase_url_id)
        self.assertEqual(self.org.crunchbase_url.url, crunchbase_url)

    def test_rejects_invalid_crunchbase_url(self):
        enricher = MockEnricher({'crunchbase_url': 'https://example.com/org/foo'})
        self._call(enricher)

        self.org.refresh_from_db()
        self.assertIsNone(self.org.crunchbase_url_id)

    def test_skips_when_both_urls_already_set(self):
        linkedin = CitationUrl.objects.create(
            url='https://www.linkedin.com/company/wu-tang-financial',
            status=CitationUrl.Status.VALID,
        )
        crunchbase = CitationUrl.objects.create(
            url='https://www.crunchbase.com/organization/wu-tang-financial',
            status=CitationUrl.Status.IGNORE,
        )
        self.org.linkedin_url = linkedin
        self.org.crunchbase_url = crunchbase
        self.org.save(update_fields=['linkedin_url', 'crunchbase_url'])

        did_work = False
        opts = _options()
        with _NO_OP_ORG_CRAWL:
            did_work = self.cmd._extract_urls_one(self.org, opts, enricher=MockEnricher({}))

        self.assertFalse(did_work, "_extract_urls_one should return False when all fields are set")

    def test_skips_when_linkedin_already_set(self):
        existing = CitationUrl.objects.create(
            url='https://www.linkedin.com/company/existing',
            status=CitationUrl.Status.VALID,
        )
        self.org.linkedin_url = existing
        self.org.save(update_fields=['linkedin_url'])

        enricher = MockEnricher({'linkedin_url': 'https://www.linkedin.com/company/wu-tang-financial'})
        self._call(enricher)

        self.org.refresh_from_db()
        self.assertEqual(self.org.linkedin_url_id, existing.pk, "linkedin_url should not be overwritten")

    def test_skips_when_no_org_url(self):
        self.org.url = None
        self.org.save(update_fields=['url'])

        enricher = MockEnricher({'linkedin_url': 'https://www.linkedin.com/company/wu-tang-financial'})
        self._call(enricher)

        self.org.refresh_from_db()
        self.assertIsNone(self.org.linkedin_url_id)

    def test_dry_run_does_not_save(self):
        enricher = MockEnricher({'linkedin_url': 'https://www.linkedin.com/company/wu-tang-financial'})
        self._call(enricher, dry_run=True)

        self.org.refresh_from_db()
        self.assertIsNone(self.org.linkedin_url_id)

    def test_relative_url_rejected_by_validator(self):
        # Relative paths can't resolve to a valid linkedin/crunchbase URL, so
        # they are logged as invalid and the field is left unset.
        enricher = MockEnricher({'linkedin_url': '/company/wu-tang-financial'})
        self._call(enricher)

        self.org.refresh_from_db()
        self.assertIsNone(self.org.linkedin_url_id)


# ---------------------------------------------------------------------------
# clone_system_version M2M field copy
# ---------------------------------------------------------------------------

@override_settings(DBDB_BOT_ACCOUNT='admin')
class CloneSystemVersionM2MTestCase(TestCase):
    """
    Regression: copy.copy() shares _prefetched_objects_cache with the source
    object, so M2M fields that were prefetch_related before cloning end up
    empty on the new SystemVersion (the stale cache makes Django believe the
    through-table rows already exist).  tags is unaffected because
    enrich_system.py does not prefetch it.
    """

    fixtures = _FIXTURES

    def setUp(self):
        self.system = System.objects.get(slug='sqlite')
        self.version = SystemVersion.objects.get(system=self.system, is_current=True)
        self.admin_user = User.objects.get(username='admin')

        def _opt(attr_slug, slug, name):
            attr = Attribute.objects.get(slug=attr_slug)
            opt, _ = AttributeOption.objects.get_or_create(
                attribute=attr, slug=slug, defaults={'name': name}
            )
            return opt

        self.opt_project_type = _opt('project-type', 'commercial', 'Commercial')
        self.opt_license      = _opt('license', 'apache-2', 'Apache 2')
        self.opt_os           = _opt('os', 'linux', 'Linux')
        self.opt_written_in   = _opt('programming-language', 'c', 'C')
        self.opt_tag          = _opt('tag', 'relational', 'Relational')

        self.version.project_types.add(self.opt_project_type)
        self.version.licenses.add(self.opt_license)
        self.version.oses.add(self.opt_os)
        self.version.written_in.add(self.opt_written_in)
        self.version.tags.add(self.opt_tag)

    def _assert_m2m(self, clone):
        """Assert that all options added in setUp are present on the clone."""
        self.assertIn(self.opt_project_type, list(clone.project_types.all()))
        self.assertIn(self.opt_license,      list(clone.licenses.all()))
        self.assertIn(self.opt_os,           list(clone.oses.all()))
        self.assertIn(self.opt_written_in,   list(clone.written_in.all()))
        self.assertIn(self.opt_tag,          list(clone.tags.all()))

    def test_m2m_fields_copied_when_source_is_prefetched(self):
        """All M2M fields survive cloning even when the source was loaded with
        prefetch_related, which is how enrich_system.py always loads versions."""
        prefetched = SystemVersion.objects.prefetch_related(
            'project_types', 'licenses', 'oses', 'written_in',
            'features', 'features__options',
        ).get(pk=self.version.pk)

        clone = clone_system_version(prefetched, creator=self.admin_user, comment='test')

        self._assert_m2m(clone)

    def test_m2m_fields_copied_without_prefetch(self):
        """Baseline: M2M fields are copied correctly when source is not prefetched."""
        clone = clone_system_version(self.version, creator=self.admin_user, comment='test')

        self._assert_m2m(clone)
