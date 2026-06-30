# stdlib imports
# django imports
import environ
from django.conf import settings
from django.contrib.auth import get_user
from django.test import Client, TestCase, override_settings
from django.urls import reverse

# local imports
from dbdb.core.models import Attribute, Feature, System, SystemSearchText, SystemVersion, SystemVisit
from dbdb.core.utils.searchtext import generate_searchtext
from dbdb.core.views import CounterView

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
        # 8 hardcoded groups: country, compatible, embedded, derived, inspired, hosted, developer, acquired-by
        hardcoded_count = 8
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

    def test_system_twitter_card_is_large_image(self):
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

    def test_home_twitter_card_is_summary(self):
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
