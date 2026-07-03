from django.test import TestCase
from django.urls import reverse

from dbdb.core.models import Organization, SystemVersion


_FIXTURES = [
    'adminuser.json',
    'core_features.json',
    'core_attributes.json',
    'core_system.json',
    'core_organizations.json',
]


def _link_fixture_orgs_to_sv():
    """Link all three fixture orgs to the SQLite SystemVersion so they pass the list filter."""
    sv = SystemVersion.objects.get(system__slug='sqlite', is_current=True)
    for slug in ('wu-tang-financial', 'shaolin-systems', 'staten-island-capital'):
        sv.developer_orgs.add(Organization.objects.get(slug=slug))


class OrganizationListViewTestCase(TestCase):

    fixtures = _FIXTURES

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        _link_fixture_orgs_to_sv()

    def test_list_returns_200(self):
        response = self.client.get('/org/')
        self.assertEqual(response.status_code, 200)

    def test_list_returns_200_no_slash(self):
        response = self.client.get('/org')
        self.assertEqual(response.status_code, 200)

    def test_list_shows_all_fixture_orgs(self):
        response = self.client.get(reverse('organization_list'))
        self.assertContains(response, 'Wu-Tang Financial')
        self.assertContains(response, 'Shaolin Systems')
        self.assertContains(response, 'Staten Island Capital')

    def test_list_no_suggest_by_default(self):
        response = self.client.get(reverse('organization_list'))
        self.assertNotContains(response, 'Did you mean')


class OrganizationDidYouMeanTestCase(TestCase):

    fixtures = _FIXTURES

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        _link_fixture_orgs_to_sv()

    def test_missing_slug_redirects_to_list(self):
        response = self.client.get('/org/nope/')
        self.assertEqual(response.status_code, 302)
        self.assertIn('/org', response['Location'])

    def test_matching_slug_adds_suggest_param(self):
        # prefix 'wu' should match 'wu-tang-financial'
        response = self.client.get('/org/wu-inc/')
        self.assertEqual(response.status_code, 302)
        self.assertIn('suggest=wu-tang-financial', response['Location'])

    def test_suggest_shows_did_you_mean(self):
        response = self.client.get('/org/wu-inc/', follow=True)
        self.assertContains(response, 'Did you mean')

    def test_suggest_links_to_correct_org(self):
        response = self.client.get('/org/wu-inc/', follow=True)
        self.assertContains(response, reverse('organization', args=['wu-tang-financial']))

    def test_no_suggestion_when_no_close_match(self):
        response = self.client.get('/org/zzzzz/')
        self.assertEqual(response.status_code, 302)
        self.assertNotIn('suggest=', response['Location'])

    def test_valid_slug_still_renders(self):
        response = self.client.get('/org/wu-tang-financial/')
        self.assertEqual(response.status_code, 200)
