from django.test import TestCase
from django.urls import reverse
from django.contrib.auth.models import User

from dbdb.core.models import System, SystemVersion


class FormerNamesModelTestCase(TestCase):
    """ArrayField stores and retrieves former_names correctly."""
    fixtures = ['adminuser.json', 'core_features.json', 'core_attributes.json', 'core_system.json']

    def _sqlite_version(self):
        return SystemVersion.objects.get(system__name='SQLite', is_current=True)

    def test_default_is_empty_list(self):
        sv = self._sqlite_version()
        self.assertEqual(sv.former_names, [])

    def test_stores_and_retrieves_array(self):
        sv = self._sqlite_version()
        sv.former_names = ['RZA DB', 'GZA DB']
        sv.save(update_fields=['former_names'])
        sv.refresh_from_db()
        self.assertEqual(sv.former_names, ['RZA DB', 'GZA DB'])


class FormerNamesViewTestCase(TestCase):
    """System side-panel renders former_names correctly."""
    fixtures = ['adminuser.json', 'core_features.json', 'core_attributes.json', 'core_system.json']

    def setUp(self):
        self.system = System.objects.get(name='SQLite')
        self.sv = SystemVersion.objects.get(system=self.system, is_current=True)
        self.url = self.system.get_absolute_url()

    def test_no_former_names_section_when_empty(self):
        response = self.client.get(self.url)
        self.assertNotContains(response, 'Former Name')

    def test_singular_label_for_one_name(self):
        self.sv.former_names = ['ODB Systems']
        self.sv.save(update_fields=['former_names'])
        response = self.client.get(self.url)
        self.assertContains(response, 'Former Name')
        self.assertNotContains(response, 'Former Names')
        self.assertContains(response, 'ODB Systems')

    def test_plural_label_for_multiple_names(self):
        self.sv.former_names = ['ODB Systems', 'RZA DB']
        self.sv.save(update_fields=['former_names'])
        response = self.client.get(self.url)
        self.assertContains(response, 'Former Names')
        self.assertContains(response, 'ODB Systems, RZA DB')


class FormerNamesEditFormTestCase(TestCase):
    """Edit form saves former_names from newline-delimited textarea input."""
    fixtures = ['adminuser.json', 'core_features.json', 'core_attributes.json', 'core_system.json']

    def setUp(self):
        self.user = User.objects.get(username='admin')
        self.client.force_login(self.user)
        self.system = System.objects.get(name='SQLite')
        self.sv = SystemVersion.objects.get(system=self.system, is_current=True)
        self.url = reverse('system_edit', args=[self.system.slug])

    def _base_post_data(self):
        """Minimal valid POST data for the system edit form."""
        return {
            'name': self.system.name,
            'slug': self.system.slug,
            'description': self.sv.description or '',
            'history': '',
            'start_year': self.sv.start_year or '',
            'end_year': '',
            'twitter_handle': '',
            'project_types': [33],
            'licenses': [61],
            'oses': [76],
            'written_in': [89],
            'countries': [],
            'tags': [],
            'description_citations': '',
            'history_citations': '',
            'start_year_citations': '',
            'end_year_citations': '',
            'action': 'save',
            'comment': '',
            'developer_orgs-TOTAL_FORMS': '0',
            'developer_orgs-INITIAL_FORMS': '0',
            'developer_orgs-MIN_NUM_FORMS': '0',
            'developer_orgs-MAX_NUM_FORMS': '1000',
            'acquisitions-TOTAL_FORMS': '0',
            'acquisitions-INITIAL_FORMS': '0',
            'acquisitions-MIN_NUM_FORMS': '0',
            'acquisitions-MAX_NUM_FORMS': '1000',
            'coding_agents-TOTAL_FORMS': '0',
            'coding_agents-INITIAL_FORMS': '0',
            'coding_agents-MIN_NUM_FORMS': '0',
            'coding_agents-MAX_NUM_FORMS': '1000',
        }

    def _current_sv(self):
        return SystemVersion.objects.get(system=self.system, is_current=True)

    def test_saves_former_names_from_newline_input(self):
        data = self._base_post_data()
        data['former_names'] = 'GZA Data\nMethodMan DB'
        response = self.client.post(self.url, data)
        self.assertRedirects(response, self.system.get_absolute_url(), fetch_redirect_response=False)
        self.assertEqual(self._current_sv().former_names, ['GZA Data', 'MethodMan DB'])

    def test_empty_former_names_saves_empty_array(self):
        data = self._base_post_data()
        data['former_names'] = ''
        self.client.post(self.url, data)
        self.assertEqual(self._current_sv().former_names, [])


class FormerNamesMigrationLogicTestCase(TestCase):
    """Unit tests for the comma-split logic used in the data migration."""

    def _split(self, value):
        return [n.strip() for n in value.split(',') if n.strip()]

    def test_single_name(self):
        self.assertEqual(self._split('RZA DB'), ['RZA DB'])

    def test_two_names(self):
        self.assertEqual(self._split('RZA DB, GZA Systems'), ['RZA DB', 'GZA Systems'])

    def test_empty_string(self):
        self.assertEqual(self._split(''), [])

    def test_strips_whitespace(self):
        self.assertEqual(self._split('  RZA DB ,  GZA Systems  '), ['RZA DB', 'GZA Systems'])

    def test_trailing_comma(self):
        self.assertEqual(self._split('RZA DB,'), ['RZA DB'])
