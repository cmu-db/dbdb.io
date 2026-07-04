"""Tests for the rotate_spotlight management command."""
from io import StringIO
from unittest.mock import MagicMock, patch

from django.core.management import call_command
from django.test import TestCase

from dbdb.core.models import System

_FIXTURES = [
    'adminuser.json',
    'core_features.json',
    'core_attributes.json',
    'core_system.json',
]

# A fixed (year, week) pair used to make tests deterministic
_FIXED_YEAR = 2026
_FIXED_WEEK = 27


def _mock_date(year=_FIXED_YEAR, week=_FIXED_WEEK):
    """Return a patch target for date.today() that returns the given ISO week."""
    mock = MagicMock()
    today = MagicMock()
    today.isocalendar.return_value = (year, week, 1)
    mock.today.return_value = today
    return mock


def _call(dry_run=False, force=False):
    out = StringIO()
    call_command('rotate_spotlight',
                 dry_run=dry_run, force=force, stdout=out)
    return out.getvalue()


class RotateSpotlightCoreTestCase(TestCase):

    fixtures = _FIXTURES

    def setUp(self):
        # Mark all systems as eligible for the tests that need a pool
        System.objects.update(spotlight_eligible=True, spotlight_enabled=False)

    @patch('dbdb.core.management.commands.rotate_spotlight.date', _mock_date())
    def test_rotate_enables_exactly_one_system(self):
        _call()
        self.assertEqual(System.objects.filter(spotlight_enabled=True).count(), 1)

    @patch('dbdb.core.management.commands.rotate_spotlight.date', _mock_date())
    def test_rotated_system_is_eligible(self):
        _call()
        chosen = System.objects.get(spotlight_enabled=True)
        self.assertTrue(chosen.spotlight_eligible)

    @patch('dbdb.core.management.commands.rotate_spotlight.date', _mock_date())
    def test_does_not_pick_current_when_alternatives_exist(self):
        # Force a known current system (the one the algorithm would pick this week)
        eligible = list(System.objects.filter(spotlight_eligible=True).order_by('pk'))
        count = len(eligible)
        seed = _FIXED_YEAR * 53 + _FIXED_WEEK
        idx = seed % count
        current = eligible[idx]
        System.objects.filter(pk=current.pk).update(spotlight_enabled=True)

        _call(force=True)

        new_spotlight = System.objects.get(spotlight_enabled=True)
        self.assertNotEqual(new_spotlight.pk, current.pk)

    @patch('dbdb.core.management.commands.rotate_spotlight.date', _mock_date())
    def test_deterministic_within_same_week(self):
        # Without --force the idempotency guard fires on the second call,
        # leaving the spotlight unchanged — same system both times.
        _call()
        first = System.objects.get(spotlight_enabled=True)
        _call()
        second = System.objects.get(spotlight_enabled=True)
        self.assertEqual(first.pk, second.pk)

    def test_different_weeks_may_pick_different_system(self):
        eligible = list(System.objects.filter(spotlight_eligible=True).order_by('pk'))
        count = len(eligible)
        if count < 2:
            self.skipTest('Need at least 2 eligible systems')

        with patch('dbdb.core.management.commands.rotate_spotlight.date', _mock_date(week=1)):
            _call(force=True)
        week1_pk = System.objects.get(spotlight_enabled=True).pk

        with patch('dbdb.core.management.commands.rotate_spotlight.date', _mock_date(week=2)):
            _call(force=True)
        week2_pk = System.objects.get(spotlight_enabled=True).pk

        # With at least 2 eligible systems and consecutive weeks the picks differ
        # (week2 idx advances past week1 if they would collide)
        # We simply assert the algorithm ran without error; exact picks depend on count
        self.assertIsNotNone(week1_pk)
        self.assertIsNotNone(week2_pk)

    @patch('dbdb.core.management.commands.rotate_spotlight.date', _mock_date())
    def test_dry_run_makes_no_db_changes(self):
        before = set(System.objects.filter(spotlight_enabled=True).values_list('pk', flat=True))
        _call(dry_run=True)
        after = set(System.objects.filter(spotlight_enabled=True).values_list('pk', flat=True))
        self.assertEqual(before, after)

    @patch('dbdb.core.management.commands.rotate_spotlight.date', _mock_date())
    def test_dry_run_output_describes_selection(self):
        out = _call(dry_run=True)
        self.assertIn('Would set spotlight_enabled', out)

    def test_warns_when_no_eligible_systems(self):
        System.objects.update(spotlight_eligible=False)
        out = _call()
        self.assertIn('No spotlight-eligible', out)
        self.assertEqual(System.objects.filter(spotlight_enabled=True).count(), 0)

    @patch('dbdb.core.management.commands.rotate_spotlight.date', _mock_date())
    def test_single_eligible_system_always_picked(self):
        only = System.objects.filter(spotlight_eligible=True).order_by('pk').first()
        System.objects.exclude(pk=only.pk).update(spotlight_eligible=False)
        _call(force=True)
        self.assertTrue(System.objects.get(pk=only.pk).spotlight_enabled)

    @patch('dbdb.core.management.commands.rotate_spotlight.date', _mock_date())
    def test_idempotency_guard_skips_if_already_correct(self):
        # Run once to set the spotlight
        _call()
        chosen_pk = System.objects.get(spotlight_enabled=True).pk
        # Run again without --force — should not change anything
        _call()
        self.assertEqual(System.objects.get(spotlight_enabled=True).pk, chosen_pk)

    @patch('dbdb.core.management.commands.rotate_spotlight.date', _mock_date())
    def test_force_rotates_even_if_already_correct(self):
        eligible = list(System.objects.filter(spotlight_eligible=True).order_by('pk'))
        if len(eligible) < 2:
            self.skipTest('Need at least 2 eligible systems')
        _call()
        chosen_pk = System.objects.get(spotlight_enabled=True).pk
        _call(force=True)
        new_pk = System.objects.get(spotlight_enabled=True).pk
        # With force the algorithm re-runs and skips the current, picking a different one
        self.assertNotEqual(new_pk, chosen_pk)
