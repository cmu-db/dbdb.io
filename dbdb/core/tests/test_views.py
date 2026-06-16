# stdlib imports
# django imports
import environ
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
        response = self.client.post(reverse('counter'), data)
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
        response = c.post(reverse('counter'), data)
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
