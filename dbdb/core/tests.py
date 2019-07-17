# django imports
from django.test import TestCase, Client, override_settings
from django.contrib.auth import get_user
from django.urls import reverse
from django.core import management
# third-party imports
from pyquery import PyQuery as pq
import xapian
import environ
import haystack
from haystack.query import SearchQuerySet
# local imports
from .models import System
from .models import SystemVisit
from .models import Feature
from .views import CounterView

import tempfile
from pprint import pprint

# ==============================================
# HAYSTACK CONFIG
# ==============================================

root = environ.Path(__file__) - 2

HAYSTACK_XAPIAN_FLAGS = (
    xapian.QueryParser.FLAG_PHRASE |
    xapian.QueryParser.FLAG_BOOLEAN |
    xapian.QueryParser.FLAG_LOVEHATE |
    xapian.QueryParser.FLAG_WILDCARD |
    xapian.QueryParser.FLAG_PURE_NOT |
    xapian.QueryParser.FLAG_PARTIAL
)

TEST_INDEX = {
    'default': {
        'ENGINE': 'xapian_backend.XapianEngine',
        'PATH': tempfile.mkdtemp(),
        #'PATH': root.path('data/xapian')(),
        'FLAGS': HAYSTACK_XAPIAN_FLAGS,
    },
}

@override_settings(HAYSTACK_CONNECTIONS=TEST_INDEX)
class BaseTestCase(TestCase):

    def setUp(self):
        haystack.connections.reload('default')
        management.call_command('rebuild_index', interactive=False, verbosity=0)
        super(BaseTestCase, self).setUp()

    def tearDown(self):
        management.call_command('clear_index', interactive=False, verbosity=0)
# CLASS

# ==============================================
# SearchTestCase
# ==============================================
class SearchTestCase(BaseTestCase):

    fixtures = [
        'adminuser.json',
        'testuser.json',
        'core_base.json',
        'core_system.json'
    ]

    #def test_can_access_search_page(self):
        #response = self.client.get(reverse('search'))
        #self.assertRedirects(response, reverse('home'))
        #return
        
    def test_haystack_contents(self):
        """Make sure we are setting up haystack correctly."""
        sqs = SearchQuerySet()
        num_results = len(sqs)
        self.assertEquals(num_results, 1)
        res = sqs[0]
        self.assertEquals(res.name, "SQLite")
        return
    
    def test_search_no_parameters(self):
        query = {'q': 'sql'}
        response = self.client.get(reverse('browse'))
        self.assertContains(response, 'SQLite', html=True)
        return

    def test_search_valid_parameters(self):
        query = {'q': 'sql'}
        response = self.client.get(reverse('browse'), data=query)
        #print(response.content)
        self.assertContains(response, 'Found 1 database for \"sql\"', html=True)
        self.assertContains(response, 'SQLite', html=True)
        # self.assertContains(response, '<p class="card-text">Nice description</p>', html=True)
        return

    def test_search_invalid_parameters(self):
        query = {'q': 'dock'}
        response = self.client.get(reverse('browse'), data=query)
        self.assertContains(response, 'No databases found for \"dock\"', html=True)
        return

    pass

# ==============================================
# AutoCompleteTestCase
# ==============================================
class AutoCompleteTestCase(BaseTestCase):

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
        query = {'q': "XXX"}
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
class SystemViewTestCase(BaseTestCase):

    fixtures = [
        'adminuser.json',
        'testuser.json',
        'core_base.json',
        'core_system.json'
    ]

    def test_counter(self):
        target = "SQLite"
        system = System.objects.get(name=target)
        orig_count = system.view_count
        orig_visits = SystemVisit.objects.filter(system=system).count()
        
        data = {"token": CounterView.build_token('system', pk=system.id)}
        response = self.client.post(reverse('counter'), data)
        result = response.json();
        self.assertTrue("status" in result)
        self.assertEquals(result["status"], "ok")
        
        # Make sure count increased by one
        system = System.objects.get(name=target)
        new_count = system.view_count
        self.assertEquals(new_count, orig_count+1)
        
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
class AdvancedSearchTestCase(BaseTestCase):

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
        # Add eight for country, OS, project type, PL, inspired, derived, compatiable, licenses
        #pprint(filtergroups)
        self.assertEquals(quantity + 2 + 8, len(filtergroups))
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
class CreateDatabaseTestCase(BaseTestCase):

    fixtures = [
        'adminuser.json',
        'testuser.json',
        'core_base.json'
    ]

    def test_cant_access_not_authenticated(self):
        response = self.client.get(reverse('create_database'))
        self.assertEquals(response.status_code, 404)
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
class HomeTestCase(BaseTestCase):

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
        response = self.client.get(reverse('home'))
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
class LoginTestCase(BaseTestCase):

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


