"""
Tests for:
  1. swap_versions() utility in utils/versions.py
  2. The pending-before-live guard in the systemversion_pre_save signal
"""
from django.contrib.auth import get_user_model
from django.test import TestCase

from dbdb.core.models import AttributeOption, System, SystemVersion
from dbdb.core.utils.versions import clone_system_version, swap_versions

User = get_user_model()

_FIXTURES = [
    'adminuser.json',
    'core_features.json',
    'core_attributes.json',
    'core_system.json',
]


def _make_broken_state(system):
    """
    Return (pending_sv, live_sv) where pending has a LOWER ver than live —
    the bug scenario.

    Strategy:
    1. Clone the current live as a pending version (guard doesn't fire; approved=False).
       This gets ver N+1 (higher).
    2. Use .update() to swap their approved/is_current flags so that:
       - The original (lower ver) becomes pending (approved=False, is_current=False)
       - The clone (higher ver) becomes live (approved=True, is_current=True)
    This bypasses the pre_save signal to manufacture the broken state.
    """
    creator  = User.objects.filter(is_superuser=True).first()
    live_orig = SystemVersion.objects.get(system=system, is_current=True)

    # Create a pending clone — gets the higher ver
    new_sv = clone_system_version(
        live_orig,
        creator=creator,
        comment='bot-generated pending',
        approved=False,
    )

    # Flip via update() to get the broken state (bypasses signal / guard).
    # Order matters: promote new_sv to approved=True FIRST (clears the unique
    # pending constraint), THEN demote live_orig to approved=False.
    SystemVersion.objects.filter(pk=new_sv.pk).update(approved=True, is_current=True)
    SystemVersion.objects.filter(pk=live_orig.pk).update(approved=False, is_current=False)
    System.objects.filter(pk=system.pk).update(ver=new_sv.ver)

    live_orig.refresh_from_db()
    new_sv.refresh_from_db()
    # live_orig: lower ver, approved=False → this is the "pending"
    # new_sv:    higher ver, approved=True  → this is the "live"
    return live_orig, new_sv


class SwapVersionsCoreTestCase(TestCase):

    fixtures = _FIXTURES

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.system = System.objects.get(slug='sqlite')
        cls.pending, cls.live = _make_broken_state(cls.system)

    def _fresh(self, sv):
        return SystemVersion.objects.get(pk=sv.pk)

    def test_ver_numbers_are_swapped(self):
        pending_ver = self.pending.ver
        live_ver    = self.live.ver
        swap_versions(self.system, pending_ver, live_ver)
        self.assertEqual(self._fresh(self.pending).ver, live_ver)
        self.assertEqual(self._fresh(self.live).ver, pending_ver)

    def test_system_ver_updated_to_live_new_ver(self):
        pending_ver = self.pending.ver
        live_ver    = self.live.ver
        swap_versions(self.system, pending_ver, live_ver)
        self.system.refresh_from_db()
        self.assertEqual(self.system.ver, pending_ver)

    def test_pending_description_gets_live_content_appended(self):
        SystemVersion.objects.filter(pk=self.live.pk).update(description='Bot added this.')
        SystemVersion.objects.filter(pk=self.pending.pk).update(description='Human wrote this.')
        swap_versions(self.system, self.pending.ver, self.live.ver)
        merged = self._fresh(self.pending).description
        self.assertIn('Human wrote this.', merged)
        self.assertIn('Bot added this.', merged)

    def test_pending_description_not_duplicated(self):
        shared = 'Shared content.'
        SystemVersion.objects.filter(pk=self.live.pk).update(description=shared)
        SystemVersion.objects.filter(pk=self.pending.pk).update(description=shared)
        swap_versions(self.system, self.pending.ver, self.live.ver)
        merged = self._fresh(self.pending).description
        self.assertEqual(merged.count(shared), 1)

    def test_pending_m2m_gains_live_options(self):
        license_option = (
            AttributeOption.objects
            .filter(attribute__slug='license')
            .exclude(pk__in=self.pending.licenses.values_list('pk', flat=True))
            .first()
        )
        if license_option is None:
            self.skipTest('No extra license option available in fixture')
        self.live.licenses.add(license_option)
        swap_versions(self.system, self.pending.ver, self.live.ver)
        self.assertIn(license_option, self._fresh(self.pending).licenses.all())

    def test_pending_m2m_unchanged_for_overlapping_options(self):
        existing = list(self.pending.licenses.all())
        if not existing:
            self.skipTest('No license options on pending version in fixture')
        # Add the same option to live too
        self.live.licenses.add(existing[0])
        swap_versions(self.system, self.pending.ver, self.live.ver)
        count = self._fresh(self.pending).licenses.filter(pk=existing[0].pk).count()
        self.assertEqual(count, 1)


class SwapVersionsValidationTestCase(TestCase):

    fixtures = _FIXTURES

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.system = System.objects.get(slug='sqlite')
        cls.pending, cls.live = _make_broken_state(cls.system)

    def test_raises_if_ver1_not_lower_than_ver2(self):
        with self.assertRaises(ValueError):
            swap_versions(self.system, self.live.ver, self.pending.ver)

    def test_raises_if_ver1_equal_to_ver2(self):
        with self.assertRaises(ValueError):
            swap_versions(self.system, self.pending.ver, self.pending.ver)

    def test_raises_if_ver1_is_not_pending(self):
        with self.assertRaises(ValueError):
            swap_versions(self.system, self.live.ver, self.live.ver + 1)

    def test_raises_if_ver2_is_pending(self):
        with self.assertRaises(ValueError):
            swap_versions(self.system, self.pending.ver - 1, self.pending.ver)

    def test_dry_run_makes_no_changes(self):
        pending_ver = self.pending.ver
        live_ver    = self.live.ver
        swap_versions(self.system, pending_ver, live_ver, dry_run=True)
        self.assertEqual(SystemVersion.objects.get(pk=self.pending.pk).ver, pending_ver)
        self.assertEqual(SystemVersion.objects.get(pk=self.live.pk).ver, live_ver)


class CheckFlagTestCase(TestCase):

    fixtures = _FIXTURES

    def _call_check(self):
        from io import StringIO
        from django.core.management import call_command
        out = StringIO()
        call_command('swap_versions', '--check', stdout=out)
        return out.getvalue()

    def test_check_reports_out_of_order_system(self):
        system = System.objects.get(slug='sqlite')
        _make_broken_state(system)
        output = self._call_check()
        self.assertIn('sqlite', output)

    def test_check_reports_nothing_when_no_problems(self):
        output = self._call_check()
        self.assertIn('No out-of-order', output)

    def test_check_output_includes_swap_command_hint(self):
        system = System.objects.get(slug='sqlite')
        pending, live = _make_broken_state(system)
        output = self._call_check()
        self.assertIn(f'swap_versions {system.slug} {pending.ver} {live.ver}', output)


class PendingGuardTestCase(TestCase):

    fixtures = _FIXTURES

    def setUp(self):
        self.system  = System.objects.get(slug='sqlite')
        self.creator = User.objects.filter(is_superuser=True).first()
        self.current = SystemVersion.objects.get(system=self.system, is_current=True)

    def test_creating_approved_version_without_pending_succeeds(self):
        # No pending exists — creating an approved version should work fine
        new_v = clone_system_version(
            self.current, creator=self.creator, comment='live ok', approved=True,
        )
        self.assertTrue(new_v.approved)

    def test_creating_approved_version_when_pending_exists_raises(self):
        # First create a pending version
        clone_system_version(
            self.current, creator=self.creator, comment='pending', approved=False,
        )
        # Now trying to create another approved version must raise
        with self.assertRaises(ValueError, msg='Should raise when pending exists'):
            clone_system_version(
                self.current, creator=self.creator, comment='live bad', approved=True,
            )

    def test_approving_existing_pending_does_not_raise(self):
        pending = clone_system_version(
            self.current, creator=self.creator, comment='pending', approved=False,
        )
        # Approve the existing pending row in-place — must NOT raise
        pending.approved   = True
        pending.is_current = True
        SystemVersion.objects.filter(system=self.system).exclude(pk=pending.pk).update(is_current=False)
        pending.save()  # update on existing row (id is not None) — guard must not fire
        pending.refresh_from_db()
        self.assertTrue(pending.approved)
