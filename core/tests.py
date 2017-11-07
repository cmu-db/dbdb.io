from django.test import TestCase
from django.contrib.auth import get_user


class LoginTestCase(TestCase):

    fixtures = ['testuser.json']

    def test_login_page_available(self):
        response = self.client.get('/login/')
        self.assertEquals(response.status_code, 200)

    def test_can_login_with_right_data(self):
        data = {
            'username': 'testuser',
            'password': 'testpassword'
        }
        response = self.client.post('/login/', data=data)
        self.assertRedirects(response, '/')
        user = get_user(self.client)
        self.assertTrue(user.is_authenticated())

    def test_cant_login_with_wrong_data(self):
        data = {
            'username': 'testauser',
            'password': 'testpassword'
        }
        response = self.client.post('/login/', data=data)
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
        response = self.client.get('/')
        self.assertEquals(response.status_code, 200)

    def test_buttons_hiden_when_not_authenticated(self):
        response = self.client.get('/')
        self.assertNotContains(
            response,
            '<a class="nav-link btn btn-outline-secondary" href="/create-db/">Create Database</a>',
        )

    def test_buttons_hiden_when_not_superuser(self):
        self.client.login(username='testuser', password='testpassword')
        response = self.client.get('/')
        self.assertNotContains(
            response,
            '<a class="nav-link btn btn-outline-secondary" href="/create-db/">Create Database</a>',
        )
        self.client.logout()

    def test_buttons_shows_when_superuser(self):
        self.client.login(username='admin', password='testpassword')
        response = self.client.get('/')
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
        response = self.client.get('/create-db/')
        self.assertRedirects(response, '/login/?next=/create-db/')

    def test_cant_access_not_superuser(self):
        self.client.login(username='testuser', password='testpassword')
        response = self.client.get('/create-db/')
        self.assertEquals(response.status_code, 404)
        self.client.logout()

    def test_can_access_as_superuser(self):
        self.client.login(username='admin', password='testpassword')
        response = self.client.get('/create-db/')
        self.assertEquals(response.status_code, 200)
        self.client.logout()

    def test_can_create_database(self):
        self.client.login(username='admin', password='testpassword')
        data = {
            'name': 'MySQL',
            'description': 'Oracles simple database',
            'website': 'http://oracle.com',
            'tech_docs': 'http://oracle.com',
            'developer': 'A Nice Guy',
            'start_year': 2010,
            'end_year': 2020,
            'project_type': [1],
            'logo': '',
            'written_in': [1],
            'supported_languages': [1, 2],
            'oses': [1, 2],
            'licenses': [1],
            'derived_from': [],
            'publications': [1],
            'Feature One': [2],
            'Feature Two': ['high', 'low']
        }
        response = self.client.post('/create-db/', data=data)
        self.assertRedirects(response, '/system/1/')
