# stdlib imports
from pprint import pprint
import tempfile
# django imports
from django.contrib.auth import get_user
from django.core import management
from django.test import Client
from django.test import TestCase
from django.test import override_settings
from django.urls import reverse
# third-party imports
from haystack.query import SearchQuerySet
from pyquery import PyQuery as pq
import environ
# local imports
from .models import Feature
from .models import System
from .models import SystemVisit
from .views import CounterView


root = environ.Path(__file__) - 2

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
        'core_base.json',
        'core_system.json'
    ]

    def test_haystack_contents(self):
        """Make sure we are setting up haystack correctly."""
        sqs = SearchQuerySet()
        num_results = len(sqs)
        self.assertEquals(num_results, 2)

        expected = ["SQLite", "XXX"]
        for i in range(num_results):
            res = sqs[i]
            self.assertTrue(res.name in expected)
        return

    def test_search_no_parameters(self):
        query = {'q': 'sql'}
        response = self.client.get(reverse('browse'))
        self.assertContains(response, 'SQLite', html=True)
        return

    def test_search_valid_parameters(self):
        query = {'q': 'sql'}
        response = self.client.get(reverse('browse'), data=query)

        self.assertContains(response, 'Found 1 database', html=False)
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
        'core_base.json',
        'core_system.json'
    ]

    def test_autocom_valid_parameters(self):
        target = "SQLite"
        for i in range(1, len(target)):
            query = {'q': target[:i+1]}
            #pprint(query)
            response = self.client.get(reverse('search_autocomplete'), data=query)
            #pprint(response.json())
            self.assertContains(response, 'SQLite', html=False)
        return

    def test_autocom_invalid_parameters(self):
        query = {'q': "YYY"}
        response = self.client.get(reverse('search_autocomplete'), data=query)
        #pprint(response.json())
        self.assertEquals(len(response.json()), 0)
        return

    def test_autocom_no_parameters(self):
        response = self.client.get(reverse('search_autocomplete'))
        self.assertEquals(len(response.json()), 0)
        return
    pass

# ==============================================
# SystemViewTestCase
# ==============================================
class SystemViewTestCase(TestCase):

    fixtures = [
        'adminuser.json',
        'testuser.json',
        'core_base.json',
        'core_system.json'
    ]

    def test_counter(self):
        target = "SQLite"

        system = System.objects.get(name=target)
        orig_visits = SystemVisit.objects.filter(system=system).count()

        data = {"token": CounterView.build_token('system', pk=system.id)}
        response = self.client.post(reverse('counter'), data)
        result = response.json();
        self.assertTrue("status" in result)
        self.assertEquals(result["status"], "ok")

        # Check that we got added a SystemVisit
        new_visits = SystemVisit.objects.filter(system=system).count()
        self.assertEquals(new_visits, orig_visits+1)

        return

    def test_bot_block(self):
        target = "SQLite"
        system = System.objects.get(name=target)
        orig_count = system.view_count

        c = Client(HTTP_USER_AGENT='(KHTML, like Gecko; compatible; Googlebot/2.1)')

        data = {"token": CounterView.build_token('system', pk=system.id)}
        response = c.post(reverse('counter'), data)
        result = response.json();
        self.assertTrue("status" in result)
        self.assertEquals(result["status"], "bot")

        # Make sure count is the same
        system = System.objects.get(name=target)
        new_count = system.view_count
        self.assertEquals(new_count, orig_count)
        return


    pass

# ==============================================
# AdvancedSearchTestCase
# ==============================================
class AdvancedSearchTestCase(TestCase):

    fixtures = [
        'adminuser.json',
        'testuser.json',
        'core_base.json',
        'core_system.json'
    ]

    def test_can_access_browse(self):
        response = self.client.get(reverse('browse'))
        self.assertEquals(response.status_code, 200)
        return

    def test_inputs_quantity(self):
        quantity = Feature.objects.count()
        response = self.client.get(reverse('browse'))
        d = pq(response.content)
        filtergroups = d('div.filter-group')
        # Add two for the year filtergroups
        # Add nine for country, OS, project type, PL, inspired, derived, embedded compatiable, licenses
        #pprint(filtergroups)
        self.assertEquals(quantity + 2 + 9, len(filtergroups))
        return

    def test_search_with_insuficient_data(self):
        data = {
            'feature1': ['option1'],
        }
        response = self.client.get(reverse('browse'), data=data)
        #pprint(response.content)
        self.assertContains(response, 'No databases found')
        return

    def test_search_with_suficient_data(self):
        data = {
            'feature1': ['option3'],
        }
        response = self.client.get(reverse('browse'), data=data)
        self.assertContains(response, 'SQLite', html=True)
        return

    def test_search_with_extra_data(self):
        data = {
            'feature1': ['option2', 'option3'],
        }
        response = self.client.get(reverse('browse'), data=data)
        self.assertContains(response, 'SQLite', html=True)
        return

    def test_search_with_combined_fields(self):
        data = {
            'feature1': ['option3'],
            'feature2': ['option-high'],
        }
        response = self.client.get(reverse('browse'), data=data)
        self.assertContains(response, '<h5>SQLite</h5>', html=True)

        data = {
            'feature1': ['option3'],
            'feature2': ['option-low']
        }
        response = self.client.get(reverse('browse'), data=data)
        self.assertContains(response, '<h5>SQLite</h5>', html=True)

        data = {
            'feature1': ['option3'],
            'feature2': ['option-high', 'option-low']
        }
        response = self.client.get(reverse('browse'), data=data)
        self.assertContains(response, 'SQLite', html=True)

        data = {
            'feature1': ['option1'],
            'feature2': ['option-low']
        }
        response = self.client.get(reverse('browse'), data=data)
        self.assertContains(response, 'No databases found')
        return

    pass

# ==============================================
# CreateDatabaseTestCase
# ==============================================
class CreateDatabaseTestCase(TestCase):

    fixtures = [
        'adminuser.json',
        'testuser.json',
        'core_base.json'
    ]

    def test_cant_access_not_authenticated(self):
        response = self.client.get(reverse('create_database'))
        self.assertEquals(response.status_code, 302)
        return

    def test_cant_access_not_superuser(self):
        self.client.login(username='testuser', password='testpassword')
        response = self.client.get(reverse('create_database'))
        self.assertEquals(response.status_code, 404)
        self.client.logout()
        return

    def test_can_access_as_superuser(self):
        self.client.login(username='admin', password='testpassword')
        response = self.client.get(reverse('create_database'))
        self.assertEquals(response.status_code, 200)
        self.client.logout()
        return

    def test_can_create_database(self):
        self.client.login(username='admin', password='testpassword')
        data = {
            'name': 'TestDB',
            'url': 'http://example.com',
            'developer': 'Developer X',
            'tech_docs': 'http://example.com',
            'project_types': [1],
            'start_year': 2010,
            'end_year': 2020,
            'start_year_citations': '',
            'end_year_citations': '',
            'description': 'Simple test database',
            'description_citations': '',
            'history': 'The history of test db.',
            'history_citations': '',
            'logo': '',
            'licenses': [1],
            'oses': [1, 2],

            'action': 'save',
            'comment': '',
        }
        response = self.client.post(reverse('create_database'), data=data)
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
        self.assertEquals(response.status_code, 200)
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
        # Load stats insead of home so that we don't get a cached
        # result. Yes we try to override settings of the cache
        # up aove to disable it but it doesn't work
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
        self.assertEquals(response.status_code, 200)
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
        self.assertEquals(response.status_code, 200)
        self.assertContains(
            response,
            'Please enter a correct username and password. Note that both fields may be case-sensitive.'
        )
        return
    pass


