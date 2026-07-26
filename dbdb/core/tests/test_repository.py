import datetime
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.utils import timezone

from dbdb.core.models import (
    AttributeOption, CitationUrl, RepositoryInfo, RepositorySnapshot,
    System, SystemVersion,
)
from dbdb.core.utils.repositories.base import SnapshotData
from dbdb.core.utils.repository import check_abandoned, check_resurrection
from dbdb.core.utils.versions import clone_system_version, finalize_new_version

User = get_user_model()

INACTIVITY_DAYS = 365


# ==============================================
# CheckAbandonedTestCase
# ==============================================
@override_settings(DBDB_BOT_ACCOUNT='admin')
class CheckAbandonedTestCase(TestCase):
    fixtures = ['adminuser.json', 'core_features.json', 'core_attributes.json', 'core_system.json']

    def setUp(self):
        self.system = System.objects.first()
        self.sv = SystemVersion.objects.get(system=self.system, is_current=True)
        self.abandoned_tag = AttributeOption.objects.get(attribute__slug='tag', slug='abandoned')

    def _make_repo(self, enabled=True):
        citation = CitationUrl.objects.create(url='https://github.com/dbdb-test/testrepo')
        repo_info = RepositoryInfo.objects.create(sourcerepo_url=citation, enabled=enabled)
        self.sv.sourcerepo_url = citation
        self.sv.save(update_fields=['sourcerepo_url'])
        return citation, repo_info

    def _make_snapshot(self, repo_info, **kwargs):
        snapshot = RepositorySnapshot.objects.create(repo=repo_info, **kwargs)
        repo_info.current = snapshot
        repo_info.save(update_fields=['current', 'modified'])
        return snapshot

    def test_raises_when_no_sourcerepo_url(self):
        self.sv.sourcerepo_url = None
        self.sv.save(update_fields=['sourcerepo_url'])
        with self.assertRaises(ValueError):
            check_abandoned(self.system, inactivity_days=INACTIVITY_DAYS)

    def test_raises_when_no_repo_info(self):
        citation = CitationUrl.objects.create(url='https://github.com/dbdb-test/norepo')
        self.sv.sourcerepo_url = citation
        self.sv.save(update_fields=['sourcerepo_url'])
        with self.assertRaises(ValueError):
            check_abandoned(self.system, inactivity_days=INACTIVITY_DAYS)

    def test_returns_false_with_no_snapshots(self):
        self._make_repo()
        self.assertFalse(check_abandoned(self.system, inactivity_days=INACTIVITY_DAYS))

    def test_returns_false_with_one_snapshot(self):
        _, repo_info = self._make_repo()
        old_ts = timezone.now() - datetime.timedelta(days=INACTIVITY_DAYS + 10)
        self._make_snapshot(repo_info, commit_count=100, merged_pr_count=10,
                            last_commit_timestamp=old_ts)
        self.assertFalse(check_abandoned(self.system, inactivity_days=INACTIVITY_DAYS))

    def test_returns_false_when_commit_count_differs(self):
        _, repo_info = self._make_repo()
        old_ts = timezone.now() - datetime.timedelta(days=INACTIVITY_DAYS + 10)
        self._make_snapshot(repo_info, commit_count=100, merged_pr_count=10,
                            last_commit_timestamp=old_ts)
        self._make_snapshot(repo_info, commit_count=101, merged_pr_count=10,
                            last_commit_timestamp=old_ts)
        self.assertFalse(check_abandoned(self.system, inactivity_days=INACTIVITY_DAYS))

    def test_returns_false_when_last_commit_recent(self):
        _, repo_info = self._make_repo()
        old_ts = timezone.now() - datetime.timedelta(days=INACTIVITY_DAYS + 10)
        self._make_snapshot(repo_info, commit_count=100, merged_pr_count=10,
                            last_commit_timestamp=old_ts)
        self._make_snapshot(repo_info, commit_count=100, merged_pr_count=10,
                            last_commit_timestamp=timezone.now() - datetime.timedelta(days=10))
        self.assertFalse(check_abandoned(self.system, inactivity_days=INACTIVITY_DAYS))

    def test_marks_abandoned_when_stale_and_inactive(self):
        _, repo_info = self._make_repo()
        old_ts = timezone.now() - datetime.timedelta(days=INACTIVITY_DAYS + 10)
        self._make_snapshot(repo_info, commit_count=100, merged_pr_count=10,
                            last_commit_timestamp=old_ts)
        self._make_snapshot(repo_info, commit_count=100, merged_pr_count=10,
                            last_commit_timestamp=old_ts)
        self.assertTrue(check_abandoned(self.system, inactivity_days=INACTIVITY_DAYS))

        new_sv = SystemVersion.objects.get(system=self.system, is_current=True)
        self.assertIn(self.abandoned_tag, new_sv.tags.all())
        self.assertIsNotNone(new_sv.end_year)

        repo_info.refresh_from_db()
        self.assertFalse(repo_info.enabled)

    def test_marks_abandoned_immediately_on_archival(self):
        _, repo_info = self._make_repo()
        archival_ts = timezone.now() - datetime.timedelta(days=30)
        self._make_snapshot(repo_info, archival_timestamp=archival_ts,
                            commit_count=100, merged_pr_count=10)
        self.assertTrue(check_abandoned(self.system, inactivity_days=INACTIVITY_DAYS))

        new_sv = SystemVersion.objects.get(system=self.system, is_current=True)
        self.assertIn(self.abandoned_tag, new_sv.tags.all())


# ==============================================
# CheckResurrectionTestCase
# ==============================================
@override_settings(DBDB_BOT_ACCOUNT='admin')
class CheckResurrectionTestCase(TestCase):
    fixtures = ['adminuser.json', 'core_features.json', 'core_attributes.json', 'core_system.json']

    ABANDONED_DAYS_AGO = 60

    def setUp(self):
        self.system = System.objects.first()
        self.sv = SystemVersion.objects.get(system=self.system, is_current=True)
        self.abandoned_tag = AttributeOption.objects.get(attribute__slug='tag', slug='abandoned')

        self.citation = CitationUrl.objects.create(url='https://github.com/dbdb-test/testrepo')
        self.repo_info = RepositoryInfo.objects.create(
            sourcerepo_url=self.citation, enabled=False
        )
        self.sv.sourcerepo_url = self.citation
        self.sv.tags.add(self.abandoned_tag)
        self.sv.save(update_fields=['sourcerepo_url'])

        # Set current_version.created to a known past time so the activity
        # threshold is deterministic (auto_now_add cannot be set at creation time).
        self.abandoned_since = timezone.now() - datetime.timedelta(days=self.ABANDONED_DAYS_AGO)
        SystemVersion.objects.filter(pk=self.sv.pk).update(created=self.abandoned_since)
        self.sv.refresh_from_db()

    def _snap(self, **kwargs):
        return SnapshotData(**kwargs)

    def test_returns_false_when_not_tagged_abandoned(self):
        self.sv.tags.remove(self.abandoned_tag)
        with patch('dbdb.core.utils.repository.fetch_snapshot_data') as mock_fetch:
            mock_fetch.return_value = self._snap()
            self.assertFalse(check_resurrection(self.system))
        self.assertEqual(self.system.versions.filter(approved=False).count(), 0)

    def test_returns_false_when_no_activity(self):
        old_ts = self.abandoned_since - datetime.timedelta(days=10)
        with patch('dbdb.core.utils.repository.fetch_snapshot_data') as mock_fetch:
            mock_fetch.return_value = self._snap(
                last_commit_timestamp=old_ts,
                last_pr_closed_at=old_ts,
                last_issue_closed_at=old_ts,
            )
            self.assertFalse(check_resurrection(self.system))
        self.assertEqual(self.system.versions.filter(approved=False).count(), 0)

    def test_creates_pending_on_new_commit(self):
        recent_ts = self.abandoned_since + datetime.timedelta(days=10)
        with patch('dbdb.core.utils.repository.fetch_snapshot_data') as mock_fetch:
            mock_fetch.return_value = self._snap(last_commit_timestamp=recent_ts, commit_count=101)
            self.assertTrue(check_resurrection(self.system))

        pending = self.system.pending_version()
        self.assertIsNotNone(pending)
        self.assertFalse(pending.approved)
        self.assertIsNone(pending.end_year)
        self.assertNotIn(self.abandoned_tag, pending.tags.all())

    def test_creates_pending_on_closed_pr(self):
        recent_ts = self.abandoned_since + datetime.timedelta(days=5)
        with patch('dbdb.core.utils.repository.fetch_snapshot_data') as mock_fetch:
            mock_fetch.return_value = self._snap(last_pr_closed_at=recent_ts, merged_pr_count=50)
            self.assertTrue(check_resurrection(self.system))
        self.assertIsNotNone(self.system.pending_version())

    def test_creates_pending_on_closed_issue(self):
        recent_ts = self.abandoned_since + datetime.timedelta(days=5)
        with patch('dbdb.core.utils.repository.fetch_snapshot_data') as mock_fetch:
            mock_fetch.return_value = self._snap(last_issue_closed_at=recent_ts, closed_issue_count=1)
            self.assertTrue(check_resurrection(self.system))
        self.assertIsNotNone(self.system.pending_version())

    def test_modifies_existing_pending_version(self):
        admin = User.objects.get(username='admin')
        existing_pending = clone_system_version(
            self.sv, creator=admin, comment="Pre-existing edit", approved=False
        )
        finalize_new_version(existing_pending, old_logo=self.sv.logo)

        recent_ts = self.abandoned_since + datetime.timedelta(days=10)
        with patch('dbdb.core.utils.repository.fetch_snapshot_data') as mock_fetch:
            mock_fetch.return_value = self._snap(last_commit_timestamp=recent_ts, commit_count=200)
            self.assertTrue(check_resurrection(self.system))

        self.assertEqual(self.system.versions.filter(approved=False).count(), 1)

        existing_pending.refresh_from_db()
        self.assertIsNone(existing_pending.end_year)
        self.assertNotIn(self.abandoned_tag, existing_pending.tags.all())
        self.assertIn("dormant", existing_pending.history)

    def test_does_not_reenable_repo_info(self):
        recent_ts = self.abandoned_since + datetime.timedelta(days=10)
        with patch('dbdb.core.utils.repository.fetch_snapshot_data') as mock_fetch:
            mock_fetch.return_value = self._snap(last_commit_timestamp=recent_ts, commit_count=101)
            check_resurrection(self.system)
        self.repo_info.refresh_from_db()
        self.assertFalse(self.repo_info.enabled)

    def test_history_note_appended(self):
        recent_ts = self.abandoned_since + datetime.timedelta(days=10)
        with patch('dbdb.core.utils.repository.fetch_snapshot_data') as mock_fetch:
            mock_fetch.return_value = self._snap(last_commit_timestamp=recent_ts, commit_count=101)
            check_resurrection(self.system)
        pending = self.system.pending_version()
        self.assertIn("dormant", pending.history)
        self.assertIn(str(timezone.now().year), pending.history)

    def test_pending_version_is_not_approved(self):
        recent_ts = self.abandoned_since + datetime.timedelta(days=10)
        with patch('dbdb.core.utils.repository.fetch_snapshot_data') as mock_fetch:
            mock_fetch.return_value = self._snap(last_commit_timestamp=recent_ts, commit_count=101)
            check_resurrection(self.system)
        self.assertFalse(self.system.pending_version().approved)
