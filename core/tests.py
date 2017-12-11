from django.test import TestCase
from django.contrib.auth import get_user
from django.urls import reverse

from .models import Feature

from pyquery import PyQuery as pq


class LoginTestCase(TestCase):

    fixtures = ['testuser.json']

    def test_login_page_available(self):
        response = self.client.get(reverse('login'))
        self.assertEquals(response.status_code, 200)

    def test_can_login_with_right_data(self):
        data = {
            'username': 'testuser',
            'password': 'testpassword'
        }
        response = self.client.post(reverse('login'), data=data)
        self.assertRedirects(response, '/')
        user = get_user(self.client)
        self.assertTrue(user.is_authenticated())

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


class HomeTestCase(TestCase):
    fixtures = [
        'adminuser.json',
        'testuser.json',
    ]

    def test_can_access_home(self):
        response = self.client.get(reverse('home'))
        self.assertEquals(response.status_code, 200)

    def test_buttons_hiden_when_not_authenticated(self):
        response = self.client.get(reverse('home'))
        self.assertNotContains(
            response,
            '<a class="nav-link btn btn-outline-secondary" href="/create-db/">Create Database</a>',
        )

    def test_buttons_hiden_when_not_superuser(self):
        self.client.login(username='testuser', password='testpassword')
        response = self.client.get(reverse('home'))
        self.assertNotContains(
            response,
            '<a class="nav-link btn btn-outline-secondary" href="/create-db/">Create Database</a>',
        )
        self.client.logout()

    def test_buttons_shows_when_superuser(self):
        self.client.login(username='admin', password='testpassword')
        response = self.client.get(reverse('home'))
        self.assertContains(
            response,
            '<a class="nav-link btn btn-outline-secondary" href="/create-db/">Create Database</a>',
        )
        self.client.logout()


class CreateDatabaseTestCase(TestCase):
    fixtures = [
        'adminuser.json',
        'testuser.json',
        'core_base.json'
    ]

    def test_cant_access_not_authenticated(self):
        response = self.client.get(reverse('create_database'))
        self.assertRedirects(response, '/login/?next=/create-db/')

    def test_cant_access_not_superuser(self):
        self.client.login(username='testuser', password='testpassword')
        response = self.client.get(reverse('create_database'))
        self.assertEquals(response.status_code, 404)
        self.client.logout()

    def test_can_access_as_superuser(self):
        self.client.login(username='admin', password='testpassword')
        response = self.client.get(reverse('create_database'))
        self.assertEquals(response.status_code, 200)
        self.client.logout()

    def test_can_create_database(self):
        self.client.login(username='admin', password='testpassword')
        data = {
            'name': 'MySQL',
            'description': 'Oracles simple database',
            'description_citation': [],
            'history': 'The history of oracle MySQL',
            'history_citation': [],
            'website': 'http://oracle.com',
            'tech_docs': 'http://oracle.com',
            'developer': 'A Nice Guy',
            'start_year': 2010,
            'start_year_citation': [],
            'end_year': 2020,
            'end_year_citation': [],
            'project_type': [1],
            'logo': '',
            'written_in': [1],
            'supported_languages': [1, 2],
            'oses': [1, 2],
            'licenses': [1],
            'derived_from': '',
            'publications': [1],
            'Feature One': [2],
            'Feature One_description': "",
            'Feature One_citations': [],
            'Feature Two': ['high', 'low'],
            'Feature Two_description': "",
            'Feature Two_citations': [],
        }
        response = self.client.post(reverse('create_database'), data=data)
        self.assertRedirects(response, reverse('system', kwargs={'slug': 'mysql'}))


class SearchTestCase(TestCase):
    fixtures = [
        'adminuser.json',
        'testuser.json',
        'core_base.json',
        'core_system.json'
    ]

    def test_can_access_search_page(self):
        response = self.client.get(reverse('search'))
        self.assertRedirects(response, reverse('home'))

    def test_search_valid_parameter(self):
        query = {'q': 'sql'}
        response = self.client.get(reverse('search'), data=query)
        self.assertContains(response, '<h3>Results for "sql"</h3>', html=True)
        self.assertContains(response, '<h5>SQLite</h5>', html=True)
        self.assertContains(response, '<p class="card-text">Nice description</p>', html=True)

    def test_search_invalid_parameters(self):
        query = {'q': 'dock'}
        response = self.client.get(reverse('search'), data=query)
        self.assertContains(response, '<h3>No results found for "dock"</h3>', html=True)


class AdvancedSearchTestCase(TestCase):
    fixtures = [
        'adminuser.json',
        'testuser.json',
        'core_base.json',
        'core_system.json'
    ]

    def test_can_access_advanced_search(self):
        response = self.client.get(reverse('advanced_search'))
        self.assertEquals(response.status_code, 200)

    def test_inputs_quantity(self):
        quantity = Feature.objects.count()
        response = self.client.get(reverse('advanced_search'))
        d = pq(response.content)
        selects = d('select')
        self.assertEquals(quantity, len(selects))

    def test_search_with_insuficient_data(self):
        data = {
            'Feature One': ['1'],
        }
        response = self.client.post(reverse('advanced_search'), data=data)
        self.assertContains(response, 'No results found')

    def test_search_with_suficient_data(self):
        data = {
            'Feature One': [3],
        }
        response = self.client.post(reverse('advanced_search'), data=data)
        self.assertContains(response, '<a href="/db/sqlite/">SQLite</a>', html=True)

    def test_search_with_extra_data(self):
        data = {
            'Feature One': [2, 3],
        }
        response = self.client.post(reverse('advanced_search'), data=data)
        self.assertContains(response, '<a href="/db/sqlite/">SQLite</a>', html=True)

    def test_search_with_combined_fields(self):
        data = {
            'Feature One': [3],
            'Feature Two': ['high']
        }
        response = self.client.post(reverse('advanced_search'), data=data)
        self.assertContains(response, '<a href="/db/sqlite/">SQLite</a>', html=True)

        data = {
            'Feature One': [3],
            'Feature Two': ['low']
        }
        response = self.client.post(reverse('advanced_search'), data=data)
        self.assertContains(response, '<a href="/db/sqlite/">SQLite</a>', html=True)

        data = {
            'Feature One': [3],
            'Feature Two': ['low', 'high']
        }
        response = self.client.post(reverse('advanced_search'), data=data)
        self.assertContains(response, '<a href="/db/sqlite/">SQLite</a>', html=True)

        data = {
            'Feature One': [2],
            'Feature Two': ['low']
        }
        response = self.client.post(reverse('advanced_search'), data=data)
        self.assertContains(response, 'No results found')
