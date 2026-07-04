"""
Tests for SystemEditView.

Covers slug-change behaviour: when a superuser submits a new slug,
a SystemRedirect should be created for the old slug so that existing
links continue to resolve.

Also covers approval-timestamp behaviour: when a superuser approves a
pending SystemVersion, the 'created' field should be updated to the
current time when 'Current Timestamp' is chosen, or preserved when
'Original' is chosen.
"""
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from dbdb.core.models import System, SystemRedirect, SystemVersion
from dbdb.core.utils.versions import clone_system_version


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


class ApprovalTimestampTestCase(TestCase):
    """
    Verify that SystemVersion.created is correctly updated when a superuser
    approves a pending version via SystemEditView.

    Bug: the view only handled admin_timestamp='original' (reset to pending's
    created time). The 'now' branch was missing, so created was never updated
    to the approval time — it silently kept the pending version's creation
    timestamp.
    """

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

        current = SystemVersion.objects.get(system=self.system, is_current=True)
        self.pending = clone_system_version(
            current,
            creator=self.superuser,
            comment='test pending version',
            approved=False,
        )
        # Backdate created by 1 day so we can reliably distinguish
        # "left unchanged" from "updated to now" without sub-ms precision.
        past_time = timezone.now() - timedelta(days=1)
        SystemVersion.objects.filter(pk=self.pending.pk).update(created=past_time)
        self.pending.refresh_from_db()

    def _approve_post(self, admin_timestamp):
        data = {
            'name':           self.system.name,
            'slug':           self.system.slug,
            'comment':        '',
            'admin_approved': 'approved',
            'admin_timestamp': admin_timestamp,
        }
        data.update(_formset_management('acquisitions'))
        data.update(_formset_management('developer_orgs'))
        data.update(_formset_management('coding_agents'))
        return self.client.post(
            reverse('system_edit', args=[self.system.slug]),
            data=data,
        )

    def test_current_timestamp_updates_created(self):
        before = timezone.now()
        response = self._approve_post('now')
        self.assertEqual(response.status_code, 302,
            "Expected redirect after approval — form may be invalid if this fails")

        approved = SystemVersion.objects.get(pk=self.pending.pk)
        # Bug: without the fix, approved.created == self.pending.created (yesterday)
        self.assertGreater(approved.created, self.pending.created,
            "approved version's 'created' should be updated to the approval time, "
            "not left as the pending version's original creation time")
        self.assertGreaterEqual(approved.created, before,
            "approved version's 'created' should be >= the time just before the POST")

    def test_original_timestamp_preserves_created(self):
        response = self._approve_post('original')
        self.assertEqual(response.status_code, 302,
            "Expected redirect after approval — form may be invalid if this fails")

        approved = SystemVersion.objects.get(pk=self.pending.pk)
        self.assertEqual(approved.created, self.pending.created,
            "When admin_timestamp='original', created should be preserved as the "
            "pending version's original creation time")
