# stdlib imports
import datetime
# django imports
import environ
import jwt
from django.conf import settings
from django.contrib.auth import get_user
from django.test import Client, RequestFactory, TestCase, override_settings
from django.urls import reverse

# local imports
from dbdb.core.models import Attribute, Feature, System, SystemSearchText, SystemVersion, SystemVisit
from dbdb.core.utils.searchtext import generate_searchtext
from dbdb.core.views import CounterView
from dbdb.core.views.auth import CreateUserView, SetupUserView, SignupRequestView
from dbdb.core.views.browse import _is_doi_query

root = environ.Path(__file__) - 4

@override_settings(CACHES={
    'default': {
        'BACKEND': 'django.core.cache.backends.dummy.DummyCache'
    }
})

# ==============================================
# SearchTestCase
# ==============================================
class SearchTestCase(TestCase):

    fixtures = [
        'adminuser.json',
        'testuser.json',
        'core_features.json',
        'core_attributes.json',
        'core_system.json'
    ]

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        for ver in SystemVersion.objects.filter(is_current=True):
            sst, _ = SystemSearchText.objects.update_or_create(system=ver.system)
            sst.name = ver.system.name
            sst.search_text = generate_searchtext(ver)
            sst.save()

    def test_search_no_parameters(self):
        response = self.client.get(reverse('browse'))
        self.assertContains(response, 'SQLite', html=True)
        return

    def test_search_valid_parameters(self):
        query = {'q': 'sql'}
        response = self.client.get(reverse('browse'), data=query)

        self.assertContains(response, '1 System Found', html=False)
        self.assertContains(response, 'SQLite', html=False)
        return

    def test_search_invalid_parameters(self):
        query = {'q': 'dock'}
        response = self.client.get(reverse('browse'), data=query)

        self.assertContains(response, 'No databases found', html=False)
        return

    def test_search_doi_url_does_not_crash(self):
        # A DOI URL as the search term contains ":" which is a tsquery operator
        # and previously caused a ProgrammingError (syntax error in tsquery).
        response = self.client.get(reverse('browse'), data={'q': 'https://doi.org/10.1145/3786704'})
        self.assertEqual(response.status_code, 200)

    pass

# ==============================================
# AutoCompleteTestCase
# ==============================================
class AutoCompleteTestCase(TestCase):

    fixtures = [
        'adminuser.json',
        'testuser.json',
        'core_features.json',
        'core_attributes.json',
        'core_system.json'
    ]

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        for ver in SystemVersion.objects.filter(is_current=True):
            sst, _ = SystemSearchText.objects.update_or_create(system=ver.system)
            sst.name = ver.system.name
            sst.search_text = generate_searchtext(ver)
            sst.save()

    def test_autocom_valid_parameters(self):
        target = "SQLite"
        for i in range(1, len(target)):
            query = {'q': target[:i+1]}
            response = self.client.get(reverse('system_autocomplete'), data=query)
            self.assertContains(response, 'SQLite', html=False)
        return

    def test_autocom_invalid_parameters(self):
        query = {'q': "YYY"}
        response = self.client.get(reverse('system_autocomplete'), data=query)
        self.assertEqual(len(response.json()), 0)
        return

    def test_autocom_no_parameters(self):
        response = self.client.get(reverse('system_autocomplete'))
        self.assertEqual(len(response.json()), 0)
        return
    pass

# ==============================================
# SystemViewTestCase
# ==============================================
class SystemViewTestCase(TestCase):

    fixtures = [
        'adminuser.json',
        'testuser.json',
        'core_features.json',
        'core_attributes.json',
        'core_system.json'
    ]

    def test_counter(self):
        target = "SQLite"

        system = System.objects.get(name=target)
        orig_visits = SystemVisit.objects.filter(system=system).count()

        data = {"token": CounterView.build_token('system', pk=system.id)}
        response = self.client.post(reverse('system_counter'), data)
        result = response.json()
        self.assertTrue("status" in result)
        self.assertEqual(result["status"], "ok")

        new_visits = SystemVisit.objects.filter(system=system).count()
        self.assertEqual(new_visits, orig_visits+1)

        return

    def test_bot_block(self):
        target = "SQLite"
        system = System.objects.get(name=target)
        orig_count = system.view_count

        c = Client(HTTP_USER_AGENT='(KHTML, like Gecko; compatible; Googlebot/2.1)')

        data = {"token": CounterView.build_token('system', pk=system.id)}
        response = c.post(reverse('system_counter'), data)
        result = response.json()
        self.assertTrue("status" in result)
        self.assertEqual(result["status"], "bot")

        system = System.objects.get(name=target)
        new_count = system.view_count
        self.assertEqual(new_count, orig_count)
        return

    def test_counter_missing_token(self):
        response = self.client.post(reverse('system_counter'), {})
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()['status'], 'missing token')

    def test_counter_invalid_token(self):
        response = self.client.post(reverse('system_counter'), {'token': 'notavalidjwttoken'})
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()['status'], 'invalid token')

    def test_counter_expired_token(self):
        system = System.objects.get(name='SQLite')
        expired_token = jwt.encode(
            {
                'iss': 'counter:system',
                'pk': system.id,
                'nbf': datetime.datetime.utcnow() - datetime.timedelta(seconds=30),
                'exp': datetime.datetime.utcnow() - datetime.timedelta(seconds=10),
            },
            settings.SECRET_KEY,
            algorithm='HS256',
        )
        response = self.client.post(reverse('system_counter'), {'token': expired_token})
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()['status'], 'expired counter')

    def test_counter_wrong_issuer(self):
        system = System.objects.get(name='SQLite')
        token = CounterView.build_token('bogus', pk=system.id)
        response = self.client.post(reverse('system_counter'), {'token': token})
        self.assertEqual(response.status_code, 400)
        self.assertIn('unrecognized', response.json()['status'])

    pass

# ==============================================
# AdvancedSearchTestCase
# ==============================================
class AdvancedSearchTestCase(TestCase):

    fixtures = [
        'adminuser.json',
        'testuser.json',
        'core_features.json',
        'core_attributes.json',
        'core_system.json'
    ]

    def test_can_access_browse(self):
        response = self.client.get(reverse('browse'))
        self.assertEqual(response.status_code, 200)
        return

    def test_inputs_quantity(self):
        feature_count = Feature.objects.count()
        attr_count = Attribute.objects.filter(sv_field__gt='').count()
        # 9 hardcoded groups: country, compatible, embedded, derived, inspired, hosted, developer, acquired-by, supported
        hardcoded_count = 9
        expected = feature_count + attr_count + hardcoded_count

        response = self.client.get(reverse('browse'))
        self.assertEqual(expected, len(response.context['filtergroups']))
        return

    def test_search_with_insuficient_data(self):
        # SQLite is row-store; columnar storage → no match
        data = {'storage-model': ['decomposition-storage-model-columnar']}
        response = self.client.get(reverse('browse'), data=data)
        self.assertContains(response, 'No databases found')
        return

    def test_search_with_suficient_data(self):
        # SQLite uses N-ary (row) storage
        data = {'storage-model': ['n-ary-storage-model-rowrecord']}
        response = self.client.get(reverse('browse'), data=data)
        self.assertContains(response, 'SQLite', html=True)
        return

    def test_search_with_extra_data(self):
        # OR mode: SQLite matches n-ary even when columnar also listed
        data = {'storage-model': ['n-ary-storage-model-rowrecord', 'decomposition-storage-model-columnar']}
        response = self.client.get(reverse('browse'), data=data)
        self.assertContains(response, 'SQLite', html=True)
        return

    def test_search_with_combined_fields(self):
        # SQLite: storage-model=n-ary, joins includes hash-join and nested-loop-join
        data = {'storage-model': ['n-ary-storage-model-rowrecord'], 'joins': ['hash-join']}
        response = self.client.get(reverse('browse'), data=data)
        self.assertContains(response, 'SQLite', html=False)

        data = {'storage-model': ['n-ary-storage-model-rowrecord'], 'joins': ['nested-loop-join']}
        response = self.client.get(reverse('browse'), data=data)
        self.assertContains(response, 'SQLite', html=False)

        data = {'storage-model': ['n-ary-storage-model-rowrecord'], 'joins': ['hash-join', 'nested-loop-join']}
        response = self.client.get(reverse('browse'), data=data)
        self.assertContains(response, 'SQLite', html=False)

        # SQLite is row-store and doesn't do broadcast joins → no match in OR mode
        data = {'storage-model': ['decomposition-storage-model-columnar'], 'joins': ['broadcast-join']}
        response = self.client.get(reverse('browse'), data=data)
        self.assertContains(response, 'No databases found')
        return

    # --- Existence queries (=*) ---

    def test_existence_feature_returns_results(self):
        # SQLite has storage-model set, so =* should match it
        response = self.client.get(reverse('browse'), data={'storage-model': '*'})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'SQLite')

    def test_existence_feature_title(self):
        response = self.client.get(reverse('browse'), data={'storage-model': '*'})
        self.assertContains(response, 'with Storage Model')

    def test_existence_feature_combined_with_normal_filter(self):
        # storage-model=* AND joins=hash-join: SQLite matches both
        response = self.client.get(reverse('browse'), data={
            'storage-model': '*', 'joins': 'hash-join',
        })
        self.assertContains(response, 'SQLite')

    def test_existence_attribute_returns_results(self):
        # SQLite has license=public-domain, so license=* should match it
        response = self.client.get(reverse('browse'), data={'license': '*'})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'SQLite')

    def test_existence_attribute_title(self):
        response = self.client.get(reverse('browse'), data={'license': '*'})
        self.assertContains(response, 'with License')

    def test_existence_attribute_programming_language(self):
        # SQLite written in C
        response = self.client.get(reverse('browse'), data={'programming-language': '*'})
        self.assertContains(response, 'SQLite')

    def test_existence_url_field_returns_results(self):
        from dbdb.core.models import CitationUrl, SystemVersion
        sv = SystemVersion.objects.get(system__name='SQLite', is_current=True)
        url, _ = CitationUrl.objects.get_or_create(url='https://en.wikipedia.org/wiki/SQLite')
        sv.wikipedia_url = url
        sv.save()
        response = self.client.get(reverse('browse'), data={'wikipedia_url': '*'})
        self.assertContains(response, 'SQLite')

    def test_existence_url_field_title(self):
        from dbdb.core.models import CitationUrl, SystemVersion
        sv = SystemVersion.objects.get(system__name='SQLite', is_current=True)
        url, _ = CitationUrl.objects.get_or_create(url='https://en.wikipedia.org/wiki/SQLite')
        sv.wikipedia_url = url
        sv.save()
        response = self.client.get(reverse('browse'), data={'wikipedia_url': '*'})
        self.assertContains(response, 'with Wikipedia URL')

    def test_existence_url_field_no_match_when_empty(self):
        # SQLite has no wikipedia_url in fixture — existence filter returns no results
        response = self.client.get(reverse('browse'), data={'wikipedia_url': '*'})
        self.assertContains(response, 'No databases found')

    def test_existence_stacked_filters(self):
        # Both storage-model=* and license=* must match — SQLite has both
        response = self.client.get(reverse('browse'), data={
            'storage-model': '*', 'license': '*',
        })
        self.assertContains(response, 'SQLite')

    def test_supported_filter_returns_results(self):
        from dbdb.core.models import AttributeOption, SystemVersion
        sv = SystemVersion.objects.get(system__name='SQLite', is_current=True)
        c_opt = AttributeOption.objects.get(slug='c', attribute__slug='programming-language')
        sv.supported_languages.add(c_opt)
        response = self.client.get(reverse('browse'), data={'supported': 'c'})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'SQLite')

    def test_supported_filter_existence(self):
        from dbdb.core.models import AttributeOption, SystemVersion
        sv = SystemVersion.objects.get(system__name='SQLite', is_current=True)
        c_opt = AttributeOption.objects.get(slug='c', attribute__slug='programming-language')
        sv.supported_languages.add(c_opt)
        response = self.client.get(reverse('browse'), data={'supported': '*'})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'SQLite')

    def test_supported_filter_no_match(self):
        # SQLite has no supported_languages by default
        response = self.client.get(reverse('browse'), data={'supported': '*'})
        self.assertContains(response, 'No databases found')

    pass

# ==============================================
# NegationFilterTestCase
# ==============================================
class NegationFilterTestCase(TestCase):
    """Tests for negation (!) filter prefix on FeatureOptions and AttributeOptions."""

    fixtures = [
        'adminuser.json',
        'testuser.json',
        'core_features.json',
        'core_attributes.json',
        'core_system.json',
    ]

    # --- Feature negation ---

    def test_feature_negation_excludes_matching_system(self):
        # Before fix: causes "Invalid Search" (! slug unknown). After fix: SQLite excluded.
        data = {'storage-model': '!n-ary-storage-model-rowrecord'}
        response = self.client.get(reverse('browse'), data=data)
        self.assertNotContains(response, 'SQLite')

    def test_feature_negation_does_not_exclude_non_matching(self):
        # Before fix: causes "Invalid Search". After fix: SQLite present (not columnar).
        data = {'storage-model': '!decomposition-storage-model-columnar'}
        response = self.client.get(reverse('browse'), data=data)
        self.assertContains(response, 'SQLite')

    # --- Attribute negation ---

    def test_attribute_negation_excludes_matching_system(self):
        # SQLite has license=public-domain; negating it excludes SQLite.
        # Before fix: Q(licenses__slug__in=['!public-domain']) matches nothing → no results (wrong).
        # After fix: sqs.exclude(...) correctly removes SQLite → no results (correct).
        data = {'license': '!public-domain'}
        response = self.client.get(reverse('browse'), data=data)
        self.assertNotContains(response, 'SQLite')

    def test_attribute_negation_does_not_exclude_non_matching(self):
        # SQLite has public-domain, not MIT. Negating MIT should keep SQLite.
        # Before fix: Q(licenses__slug__in=['!mit']) matches nothing → "No databases found" (WRONG).
        # After fix: exclude(licenses__slug__in=['mit']) leaves SQLite → SQLite shown.
        data = {'license': '!mit'}
        response = self.client.get(reverse('browse'), data=data)
        self.assertContains(response, 'SQLite')

    # --- Combined ---

    def test_positive_and_negation_feature_coexist(self):
        # Positive matches SQLite (row-store), negation doesn't affect it (not columnar).
        data = {'storage-model': ['n-ary-storage-model-rowrecord',
                                  '!decomposition-storage-model-columnar']}
        response = self.client.get(reverse('browse'), data=data)
        self.assertContains(response, 'SQLite')

    def test_negation_overrides_positive_for_same_value(self):
        # Positive would include SQLite, but negating the same value excludes it.
        data = {'storage-model': ['n-ary-storage-model-rowrecord',
                                  '!n-ary-storage-model-rowrecord']}
        response = self.client.get(reverse('browse'), data=data)
        self.assertNotContains(response, 'SQLite')

    pass

# ==============================================
# BrowseColumnTestCase
# ==============================================
class BrowseColumnTestCase(TestCase):
    """Verify that each column type is correctly populated in browse results."""

    fixtures = [
        'adminuser.json',
        'testuser.json',
        'core_features.json',
        'core_attributes.json',
        'core_system.json',
    ]

    def _sqlite(self, response):
        return next(r for r in response.context['results'] if r['name'] == 'SQLite')

    def _col_value(self, response, result, col_id):
        idx = response.context['active_col_ids'].index(col_id)
        return result['col_values'][idx]

    # --- supported-languages column ---

    def test_supported_languages_column_via_filter(self):
        """?supported=python auto-shows the column and populates it with Python."""
        from dbdb.core.models import AttributeOption, SystemVersion
        sv = SystemVersion.objects.get(system__name='SQLite', is_current=True)
        python = AttributeOption.objects.get(slug='python', attribute__slug='programming-language')
        sv.supported_languages.add(python)

        response = self.client.get(reverse('browse'), data={'supported': 'python'})
        self.assertEqual(response.status_code, 200)
        sqlite = self._sqlite(response)
        self.assertIn('supported-languages', response.context['active_col_ids'])
        cv = self._col_value(response, sqlite, 'supported-languages')
        self.assertEqual(cv['type'], 'attr_opts')
        names = [d['name'] for d in cv['data']]
        self.assertIn('Python', names)

    def test_supported_languages_column_via_cols_param(self):
        """?cols=... with supported-languages shows all supported languages without a filter constraint."""
        from dbdb.core.models import AttributeOption, SystemVersion
        sv = SystemVersion.objects.get(system__name='SQLite', is_current=True)
        python = AttributeOption.objects.get(slug='python', attribute__slug='programming-language')
        java = AttributeOption.objects.get(slug='java', attribute__slug='programming-language')
        sv.supported_languages.add(python, java)

        response = self.client.get(reverse('browse'), data={'cols': 'data-model,start-year,supported-languages,tags'})
        self.assertEqual(response.status_code, 200)
        sqlite = self._sqlite(response)
        cv = self._col_value(response, sqlite, 'supported-languages')
        self.assertEqual(cv['type'], 'attr_opts')
        names = [d['name'] for d in cv['data']]
        self.assertIn('Python', names)
        self.assertIn('Java', names)

    def test_supported_languages_empty_shows_dash(self):
        """When a system has no supported_languages, the column renders a dash."""
        response = self.client.get(reverse('browse'), data={'cols': 'data-model,start-year,supported-languages,tags'})
        self.assertEqual(response.status_code, 200)
        sqlite = self._sqlite(response)
        cv = self._col_value(response, sqlite, 'supported-languages')
        self.assertEqual(cv['type'], 'attr_opts')
        self.assertEqual(cv['data'], [])

    # --- attribute column ---

    def test_attribute_programming_language_column_populated(self):
        """The programming-language attribute column shows the system's written_in language."""
        response = self.client.get(reverse('browse'), data={'cols': 'data-model,start-year,programming-language,tags'})
        self.assertEqual(response.status_code, 200)
        sqlite = self._sqlite(response)
        cv = self._col_value(response, sqlite, 'programming-language')
        self.assertEqual(cv['type'], 'attr_opts')
        names = [d['name'] for d in cv['data']]
        self.assertIn('C', names)

    def test_attribute_license_column_populated(self):
        """The license attribute column shows the system's license."""
        response = self.client.get(reverse('browse'), data={'cols': 'data-model,start-year,license,tags'})
        self.assertEqual(response.status_code, 200)
        sqlite = self._sqlite(response)
        cv = self._col_value(response, sqlite, 'license')
        self.assertEqual(cv['type'], 'attr_opts')
        names = [d['name'] for d in cv['data']]
        self.assertIn('Public Domain', names)

    # --- feature column ---

    def test_feature_storage_model_column_populated(self):
        """The storage-model feature column shows the system's storage model."""
        response = self.client.get(reverse('browse'), data={'cols': 'data-model,start-year,storage-model,tags'})
        self.assertEqual(response.status_code, 200)
        sqlite = self._sqlite(response)
        cv = self._col_value(response, sqlite, 'storage-model')
        self.assertEqual(cv['type'], 'feature_opts')
        values = [d['value'] for d in cv['data']]
        self.assertIn('N-ary Storage Model (Row/Record)', values)

    # --- builtin columns ---

    def test_start_year_column_populated(self):
        """The start-year builtin column shows the system's start year."""
        response = self.client.get(reverse('browse'))
        self.assertEqual(response.status_code, 200)
        sqlite = self._sqlite(response)
        cv = self._col_value(response, sqlite, 'start-year')
        self.assertEqual(cv['type'], 'year')
        self.assertEqual(cv['data'], 2001)

    def test_tags_column_empty_shows_no_dash(self):
        """Tags column with no tags produces an empty data list (no crash)."""
        response = self.client.get(reverse('browse'))
        self.assertEqual(response.status_code, 200)
        sqlite = self._sqlite(response)
        cv = self._col_value(response, sqlite, 'tags')
        self.assertEqual(cv['type'], 'tags')
        self.assertIsInstance(cv['data'], list)

# ==============================================
# WildcardNameSearchTestCase
# ==============================================
class WildcardNameSearchTestCase(TestCase):

    fixtures = [
        'adminuser.json',
        'testuser.json',
        'core_features.json',
        'core_attributes.json',
        'core_system.json',
    ]

    def test_wildcard_both_ends_matches(self):
        response = self.client.get(reverse('browse'), data={'name': '%qlite%'})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'SQLite')

    def test_wildcard_suffix_only_matches(self):
        # "S%" — starts with "S", case-insensitive → matches SQLite
        response = self.client.get(reverse('browse'), data={'name': 's%'})
        self.assertContains(response, 'SQLite')

    def test_wildcard_prefix_only_matches(self):
        # "%ite" — ends with "ite" → matches SQLite
        response = self.client.get(reverse('browse'), data={'name': '%ite'})
        self.assertContains(response, 'SQLite')

    def test_wildcard_multiple_wildcards(self):
        # "%S%ite%" — contains "S" then "ite" → matches SQLite
        response = self.client.get(reverse('browse'), data={'name': '%S%ite%'})
        self.assertContains(response, 'SQLite')

    def test_wildcard_no_match(self):
        response = self.client.get(reverse('browse'), data={'name': '%XXXX_no_such_system%'})
        self.assertContains(response, 'No databases found')

    def test_wildcard_combined_with_feature_filter(self):
        # name matches SQLite AND storage-model is n-ary (which SQLite is) → SQLite in results
        response = self.client.get(reverse('browse'), data={
            'name': '%qlite%',
            'storage-model': ['n-ary-storage-model-rowrecord'],
        })
        self.assertContains(response, 'SQLite')

    def test_wildcard_name_excludes_non_matching(self):
        # name doesn't match even though feature filter would pass
        response = self.client.get(reverse('browse'), data={
            'name': '%XXXX_no_such_system%',
            'storage-model': ['n-ary-storage-model-rowrecord'],
        })
        self.assertContains(response, 'No databases found')

    def test_wildcard_regex_special_chars_are_safe(self):
        # "+" and "." are regex metacharacters — must be escaped, not crash
        response = self.client.get(reverse('browse'), data={'name': '%s.l+ite%'})
        self.assertEqual(response.status_code, 200)

    def test_wildcard_appears_in_title(self):
        response = self.client.get(reverse('browse'), data={'name': '%qlite%'})
        self.assertIn('named "%qlite%"', response.context['title'].lower())

    pass


# ==============================================
# FieldNameMapTestCase
# ==============================================
class FieldNameMapTestCase(TestCase):

    def test_all_exists_params_have_field_name_entry(self):
        from dbdb.core.views.browse import _EXISTS_FILTER_MAP, _FIELD_NAME_MAP
        for param in _EXISTS_FILTER_MAP:
            self.assertIn(param, _FIELD_NAME_MAP,
                msg=f"_FIELD_NAME_MAP missing entry for '{param}'")

    def test_field_name_map_noun_label_not_empty(self):
        from dbdb.core.views.browse import _FIELD_NAME_MAP
        for param, (verb, noun) in _FIELD_NAME_MAP.items():
            self.assertTrue(noun, msg=f"_FIELD_NAME_MAP['{param}'] has empty noun_label")

    pass

# ==============================================
# CreateSystemTestCase
# ==============================================
class CreateSystemTestCase(TestCase):

    fixtures = [
        'adminuser.json',
        'testuser.json',
        'core_features.json',
        'core_attributes.json',
    ]

    def test_cant_access_not_authenticated(self):
        response = self.client.get(reverse('create_system'))
        self.assertEqual(response.status_code, 302)
        return

    def test_cant_access_not_superuser(self):
        self.client.login(username='testuser', password='testpassword')
        response = self.client.get(reverse('create_system'))
        self.assertEqual(response.status_code, 404)
        self.client.logout()
        return

    def test_can_access_as_superuser(self):
        self.client.login(username='admin', password='testpassword')
        response = self.client.get(reverse('create_system'))
        self.assertEqual(response.status_code, 200)
        self.client.logout()
        return

    def test_can_create_system(self):
        self.client.login(username='admin', password='testpassword')
        data = {
            'name': 'TestDB',
            'slug': 'testdb',
            'project_types': [33],
            'start_year': 2010,
            'end_year': 2020,
            'start_year_citations': '',
            'end_year_citations': '',
            'description': 'Simple test database',
            'description_citations': '',
            'history': 'The history of test db.',
            'history_citations': '',
            'licenses': [53],
            'oses': [76, 84],
            'action': 'save',
            'comment': '',
            'acquisitions-TOTAL_FORMS': 0,
            'acquisitions-INITIAL_FORMS': 0,
            'acquisitions-MIN_NUM_FORMS': 0,
            'acquisitions-MAX_NUM_FORMS': 1000,
            'developer_orgs-TOTAL_FORMS': 0,
            'developer_orgs-INITIAL_FORMS': 0,
            'developer_orgs-MIN_NUM_FORMS': 0,
            'developer_orgs-MAX_NUM_FORMS': 1000,
            'coding_agents-TOTAL_FORMS': 0,
            'coding_agents-INITIAL_FORMS': 0,
            'coding_agents-MIN_NUM_FORMS': 0,
            'coding_agents-MAX_NUM_FORMS': 1000,
        }
        response = self.client.post(reverse('create_system'), data=data)
        self.assertRedirects(response, reverse('system', kwargs={'slug': 'testdb'}))
        return
    pass

# ==============================================
# HomeTestCase
# ==============================================
class HomeTestCase(TestCase):

    fixtures = [
        'adminuser.json',
        'testuser.json',
    ]

    def test_can_access_home(self):
        response = self.client.get(reverse('home'))
        self.assertEqual(response.status_code, 200)
        return

    def test_buttons_hiden_when_not_authenticated(self):
        response = self.client.get(reverse('home'))
        self.assertNotContains(
            response,
            '<a class="nav-link btn btn-outline-secondary" href="/create-db/">Create Database</a>',
        )
        return

    def test_buttons_hiden_when_not_superuser(self):
        self.client.login(username='testuser', password='testpassword')
        response = self.client.get(reverse('home'))
        self.assertNotContains(
            response,
            '<a class="nav-link btn btn-outline-secondary" href="/create-db/">Create Database</a>',
        )
        self.client.logout()
        return

    def test_buttons_shows_when_superuser(self):
        self.client.login(username='admin', password='testpassword')
        response = self.client.get(reverse('stats'))
        self.assertContains(
            response,
            'href="/create"',
        )
        self.client.logout()
        return
    pass

# ==============================================
# LoginTestCase
# ==============================================
class LoginTestCase(TestCase):

    fixtures = ['testuser.json']

    def test_login_page_available(self):
        response = self.client.get(reverse('login'))
        self.assertEqual(response.status_code, 200)
        return

    def test_can_login_with_right_data(self):
        data = {
            'username': 'testuser',
            'password': 'testpassword'
        }
        response = self.client.post(reverse('login'), data=data)
        self.assertRedirects(response, '/')
        user = get_user(self.client)
        self.assertTrue(user.is_authenticated)
        return

    def test_cant_login_with_wrong_data(self):
        data = {
            'username': 'testauser',
            'password': 'testpassword'
        }
        response = self.client.post(reverse('login'), data=data)
        self.assertEqual(response.status_code, 200)
        self.assertContains(
            response,
            'Please enter a correct username and password. Note that both fields may be case-sensitive.'
        )
        return
    pass


# ==============================================
# MetaTagsTestCase
# ==============================================
class MetaTagsTestCase(TestCase):

    fixtures = [
        'adminuser.json',
        'testuser.json',
        'core_features.json',
        'core_attributes.json',
        'core_system.json'
    ]

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        for ver in SystemVersion.objects.filter(is_current=True):
            sst, _ = SystemSearchText.objects.update_or_create(system=ver.system)
            sst.name = ver.system.name
            sst.search_text = generate_searchtext(ver)
            sst.save()

    # --- System page ---

    def test_system_og_title_contains_system_name(self):
        response = self.client.get(reverse('system', kwargs={'slug': 'sqlite'}))
        self.assertContains(response, 'property="og:title"')
        self.assertContains(response, f'SQLite{settings.DBDB_TITLE_SEPARATOR}{settings.DBDB_SITE_NAME}')

    def test_system_card_is_large_image(self):
        response = self.client.get(reverse('system', kwargs={'slug': 'sqlite'}))
        self.assertContains(response, 'name="twitter:card"')
        self.assertContains(response, 'summary_large_image')

    def test_system_og_description_present(self):
        response = self.client.get(reverse('system', kwargs={'slug': 'sqlite'}))
        self.assertContains(response, 'property="og:description"')

    def test_system_og_type_is_article(self):
        response = self.client.get(reverse('system', kwargs={'slug': 'sqlite'}))
        self.assertContains(response, 'property="og:type"')
        self.assertContains(response, 'article')

    # --- Home page ---

    def test_home_og_title(self):
        response = self.client.get(reverse('home'))
        self.assertContains(response, 'property="og:title"')
        self.assertContains(response, 'Database of Databases')

    def test_home_og_description(self):
        response = self.client.get(reverse('home'))
        self.assertContains(response, 'property="og:description"')
        self.assertContains(response, 'encyclopedia of database systems')

    def test_home_card_is_summary(self):
        response = self.client.get(reverse('home'))
        self.assertContains(response, 'name="twitter:card"')
        self.assertContains(response, 'summary')

    # --- Browse page ---

    def test_browse_og_title_no_filter(self):
        response = self.client.get(reverse('browse'))
        self.assertContains(response, 'property="og:title"')
        self.assertContains(response, f'Browse{settings.DBDB_TITLE_SEPARATOR}{settings.DBDB_SITE_NAME}')

    def test_browse_og_title_with_keyword(self):
        response = self.client.get(reverse('browse'), data={'q': 'sql'})
        self.assertContains(response, 'property="og:title"')
        self.assertContains(response, 'Database of Databases')

    def test_browse_og_description_with_filter(self):
        response = self.client.get(
            reverse('browse'),
            data={'storage-model': ['n-ary-storage-model-rowrecord']},
        )
        self.assertContains(response, 'property="og:description"')
        self.assertContains(response, 'Database systems matching')

    def test_browse_og_image_is_dynamic_when_query_set(self):
        response = self.client.get(reverse('browse'), data={'q': 'sqlite'})
        self.assertContains(response, 'og:image')
        self.assertContains(response, 'api/og-image')
        self.assertContains(response, 'q=sqlite')

    def test_browse_og_image_is_static_when_no_query(self):
        response = self.client.get(reverse('browse'))
        self.assertContains(response, 'og:image')
        self.assertNotContains(response, 'api/og-image')

    pass


class OGImageTestCase(TestCase):

    def test_og_image_returns_png(self):
        response = self.client.get(reverse('og_image_search'), {'q': 'sqlite', 'n': 3})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'image/png')

    def test_og_image_empty_query(self):
        response = self.client.get(reverse('og_image_search'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'image/png')

    def test_og_image_zero_results(self):
        response = self.client.get(reverse('og_image_search'), {'q': 'sqlite', 'n': 0})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'image/png')

    def test_og_image_long_query_does_not_crash(self):
        response = self.client.get(reverse('og_image_search'), {'q': 'a' * 200, 'n': 0})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'image/png')


class OGImageSavedSearchTestCase(TestCase):

    @classmethod
    def setUpTestData(cls):
        from dbdb.core.models import SavedSearch
        cls.ss_with_icon = SavedSearch.objects.create(
            name='Relational Systems',
            description='All relational database systems',
            icon='fas fa-database',
            search_params='data-model=relational',
        )
        cls.ss_no_icon = SavedSearch.objects.create(
            name='Ghost Dog Systems',
            description='No icon on this one',
            icon='',
            search_params='data-model=relational',
        )
        cls.ss_bad_icon = SavedSearch.objects.create(
            name='Ol Dirty Systems',
            description='Unknown icon class',
            icon='fas fa-nonexistent-icon-xyzzy',
            search_params='data-model=relational',
        )

    def test_returns_png_with_icon_and_count(self):
        response = self.client.get(
            reverse('og_image_ss', kwargs={'pk': self.ss_with_icon.pk}),
            {'n': 42},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'image/png')

    def test_returns_png_with_no_icon(self):
        response = self.client.get(
            reverse('og_image_ss', kwargs={'pk': self.ss_no_icon.pk}),
            {'n': 7},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'image/png')

    def test_returns_png_with_unknown_icon(self):
        response = self.client.get(
            reverse('og_image_ss', kwargs={'pk': self.ss_bad_icon.pk}),
            {'n': 0},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'image/png')

    def test_returns_png_without_count(self):
        response = self.client.get(
            reverse('og_image_ss', kwargs={'pk': self.ss_with_icon.pk}),
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'image/png')

    def test_returns_404_for_missing_pk(self):
        response = self.client.get(reverse('og_image_ss', kwargs={'pk': 99999}))
        self.assertEqual(response.status_code, 404)


class BrowseSavedSearchMetaTestCase(TestCase):

    fixtures = [
        'adminuser.json',
        'testuser.json',
        'core_features.json',
        'core_attributes.json',
        'core_system.json',
    ]

    @classmethod
    def setUpTestData(cls):
        from dbdb.core.models import SavedSearch
        from dbdb.core.templatetags.savedsearch_tags import ss_token
        super().setUpTestData()
        cls.ss = SavedSearch.objects.create(
            name='Method Man Systems',
            icon='fas fa-database',
            search_params='data-model=relational',
        )
        cls.ss_token = ss_token(cls.ss.pk)

    def test_browse_with_ss_token_uses_og_image_ss(self):
        response = self.client.get(reverse('browse'), {'ss': self.ss_token})
        self.assertContains(response, 'og:image')
        self.assertContains(response, f'api/og-image/ss/{self.ss.pk}')


# ==============================================
# IsDoiQueryTestCase
# ==============================================
class IsDoiQueryTestCase(TestCase):

    DOI_QUERIES = [
        'doi:10.1007/978-3-031-75016-8_12',
        'DOI10.1007/s11356-023-28793-2',
        'doi.org/10.1177/00218286211070275',
        'doi:10.1123/ijspp.2022-0018',
        'doi:10.1016/j.yjpso.2023.100105',
        'doi.org/10.1016/j.encep.2025.02.002',
        'doi:10.1109/icaice68195.2025.11382395',
    ]

    def test_doi_queries_detected(self):
        for q in self.DOI_QUERIES:
            with self.subTest(q=q):
                self.assertTrue(_is_doi_query(q), msg=f"Expected DOI match for: {q!r}")

    def test_non_doi_queries_not_detected(self):
        for q in ['postgresql', 'sqlite relational', '10.5 release notes', 'doi information']:
            with self.subTest(q=q):
                self.assertFalse(_is_doi_query(q), msg=f"Unexpected DOI match for: {q!r}")


# ==============================================
# JwtAuthTestCase
# ==============================================
class JwtAuthTestCase(TestCase):

    def setUp(self):
        self.factory = RequestFactory()
        self.create_view = CreateUserView()

    def _decode(self, token=None):
        """Call decode_token on a fake GET request, optionally with a token param."""
        url = '/'
        if token is not None:
            url = f'/?token={token}'
        request = self.factory.get(url)
        return self.create_view.decode_token(request)

    def test_decode_token_missing(self):
        self.assertIsNone(self._decode())

    def test_decode_token_valid(self):
        email = 'rza@wutang.com'
        token = SetupUserView().build_token(email, [])
        result = self._decode(token)
        self.assertIsNotNone(result)
        self.assertEqual(result['sub'], email)

    def test_decode_token_expired(self):
        expired = jwt.encode(
            {
                'iss': 'setup_user',
                'sub': 'ghostface@wutang.com',
                'nbf': datetime.datetime.utcnow() - datetime.timedelta(seconds=30),
                'exp': datetime.datetime.utcnow() - datetime.timedelta(seconds=10),
            },
            settings.SECRET_KEY,
            algorithm='HS256',
        )
        self.assertIs(self._decode(expired), False)

    def test_decode_token_invalid(self):
        self.assertIsNone(self._decode('notavalidtoken'))

    def test_setup_build_token_is_string(self):
        token = SetupUserView().build_token('methodman@wutang.com', [])
        self.assertIsInstance(token, str)

    def test_signup_build_token_is_string(self):
        token = SignupRequestView()._build_token('raekwon@wutang.com', [])
        self.assertIsInstance(token, str)

    def test_setup_token_roundtrip(self):
        email = 'odb@wutang.com'
        system_ids = [42]
        token = SetupUserView().build_token(email, system_ids)
        result = self._decode(token)
        self.assertIsNotNone(result)
        self.assertEqual(result['sub'], email)
        self.assertEqual(result['systems'], system_ids)


# ==============================================
# SetupUserViewTestCase
# ==============================================
class SetupUserViewTestCase(TestCase):

    fixtures = [
        'adminuser.json',
        'testuser.json',
        'core_features.json',
        'core_attributes.json',
        'core_system.json',
    ]

    def setUp(self):
        self.url = reverse('setup_user')
        self.client.login(username='admin', password='testpassword')
        self.system = System.objects.first()

    def test_superuser_can_access_page(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Generate URL')

    def test_non_superuser_cannot_access(self):
        self.client.logout()
        self.client.login(username='testuser', password='testpassword')
        response = self.client.get(self.url)
        self.assertNotEqual(response.status_code, 200)

    def test_form_uses_get_not_post(self):
        # Before fix: form had method="POST" so clicking Generate URL would
        # hit the view's missing post() handler and return 405.
        response = self.client.get(self.url)
        self.assertContains(response, 'method="GET" id="setup"',
                            msg_prefix='Setup form must use GET so the button works without JS')

    def test_generate_url_returns_json(self):
        response = self.client.get(self.url, {
            'action': 'url',
            'email': 'inspectah@wutang.com',
            'systems': [self.system.id],
        })
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn('url', data)
        self.assertNotIn('error', data)

    def test_generate_url_existing_email_returns_error(self):
        # admin@dbdb.io already exists in the adminuser fixture
        response = self.client.get(self.url, {
            'action': 'url',
            'email': 'admin@dbdb.io',
            'systems': [self.system.id],
        })
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn('error', data)
