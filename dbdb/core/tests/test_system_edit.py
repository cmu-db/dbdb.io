"""
Tests for SystemEditView.

Covers slug-change behaviour: when a superuser submits a new slug,
a SystemRedirect should be created for the old slug so that existing
links continue to resolve.
"""
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from dbdb.core.models import System, SystemRedirect


def _formset_management(prefix, total=0, initial=0):
    return {
        f'{prefix}-TOTAL_FORMS':   str(total),
        f'{prefix}-INITIAL_FORMS': str(initial),
        f'{prefix}-MIN_NUM_FORMS': '0',
        f'{prefix}-MAX_NUM_FORMS': '1000',
    }


class SystemEditSlugRedirectTestCase(TestCase):

    fixtures = [
        'adminuser.json',
        'core_features.json',
        'core_attributes.json',
        'core_system.json',
    ]

    def setUp(self):
        User = get_user_model()
        self.superuser = User.objects.get(username='admin')
        self.client.force_login(self.superuser)
        self.system = System.objects.get(slug='sqlite')

    def _post_data(self, new_slug):
        data = {
            'name':    self.system.name,
            'slug':    new_slug,
            'comment': '',
        }
        data.update(_formset_management('acquisitions'))
        data.update(_formset_management('developer_orgs'))
        data.update(_formset_management('coding_agents'))
        return data

    def test_slug_change_creates_system_redirect(self):
        old_slug = self.system.slug
        new_slug = 'sqlite-renamed'

        response = self.client.post(
            reverse('system_edit', args=[old_slug]),
            data=self._post_data(new_slug),
        )

        # Confirm the form submission succeeded (redirect to the new system page)
        self.assertEqual(response.status_code, 302,
            "Expected a redirect after successful form submission — "
            "form may be invalid if this fails")

        # The old slug should now have a SystemRedirect pointing at the system
        self.assertTrue(
            SystemRedirect.objects.filter(slug=old_slug).exists(),
            f"SystemRedirect for old slug '{old_slug}' was not created after slug change",
        )
