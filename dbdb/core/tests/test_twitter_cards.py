import os
import stat
import tempfile
from io import BytesIO
from unittest.mock import MagicMock, patch

from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse
from PIL import Image

from dbdb.core.models import Organization, SystemVersion
from dbdb.core.utils.twitter_card import create_twitter_card


def _tiny_png():
    buf = BytesIO()
    Image.new('RGBA', (10, 10), (200, 100, 50, 255)).save(buf, 'PNG')
    return buf.getvalue()


class _FakeLogo:
    """PIL-compatible file-like object with a .path attribute for use in tests."""

    def __init__(self, path):
        self.path = path
        self._buf = BytesIO(open(path, 'rb').read())

    def __bool__(self):
        return True

    def read(self, *args):
        return self._buf.read(*args)

    def seek(self, pos, *args):
        return self._buf.seek(pos, *args)

    def tell(self):
        return self._buf.tell()


class TwitterCardCreationTestCase(TestCase):

    fixtures = [
        'adminuser.json',
        'core_features.json',
        'core_attributes.json',
        'core_system.json',
    ]

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()

    def tearDown(self):
        self._tmp.cleanup()

    def _sqlite_sv(self):
        return SystemVersion.objects.get(is_current=True, system__slug='sqlite')

    def test_db_card_created_in_db_subdir(self):
        sv = self._sqlite_sv()
        with self.settings(TWITTER_CARD_ROOT=self._tmp.name):
            card = create_twitter_card(sv)
        expected = os.path.join(self._tmp.name, 'db', 'sqlite.png')
        self.assertEqual(card, expected)
        self.assertTrue(os.path.exists(card))

    def test_org_card_created_in_org_subdir(self):
        logo_path = os.path.join(self._tmp.name, 'odb_logo.png')
        with open(logo_path, 'wb') as f:
            f.write(_tiny_png())

        org = Organization(name='Ol Dirty Bastard', slug='odb')
        org.logo = _FakeLogo(logo_path)

        with self.settings(TWITTER_CARD_ROOT=self._tmp.name):
            card = create_twitter_card(org)
        expected = os.path.join(self._tmp.name, 'org', 'odb.png')
        self.assertEqual(card, expected)
        self.assertTrue(os.path.exists(card))

    def test_card_has_group_write_permission(self):
        sv = self._sqlite_sv()
        with self.settings(TWITTER_CARD_ROOT=self._tmp.name):
            card = create_twitter_card(sv)
        mode = stat.S_IMODE(os.stat(card).st_mode)
        self.assertEqual(mode & 0o664, 0o664,
                         msg=f"Expected mode & 0o664 == 0o664, got {oct(mode)}")

    def test_db_card_no_logo_text_fallback(self):
        sv = self._sqlite_sv()
        self.assertFalse(sv.logo, "Fixture should have no logo for sqlite")
        with self.settings(TWITTER_CARD_ROOT=self._tmp.name):
            card = create_twitter_card(sv)
        self.assertTrue(os.path.exists(card))
        img = Image.open(card)
        self.assertEqual(img.size, (1200, 630))


class CreateTwitterCardsCommandTestCase(TestCase):

    fixtures = [
        'adminuser.json',
        'core_features.json',
        'core_attributes.json',
        'core_system.json',
    ]

    @patch('dbdb.core.management.commands.create_twitter_cards.create_twitter_card')
    def test_type_db_only_processes_systems(self, mock_create):
        call_command('create_twitter_cards', '--type', 'db', '--force')
        self.assertGreater(mock_create.call_count, 0)
        for call_item in mock_create.call_args_list:
            self.assertIsInstance(call_item.args[0], SystemVersion)

    @patch('dbdb.core.management.commands.create_twitter_cards.create_twitter_card')
    def test_type_org_skips_orgs_without_logos(self, mock_create):
        call_command('create_twitter_cards', '--type', 'org', '--force')
        mock_create.assert_not_called()

    @patch('dbdb.core.management.commands.create_twitter_cards.create_twitter_card')
    def test_type_all_processes_systems_and_ignores_logoless_orgs(self, mock_create):
        call_command('create_twitter_cards', '--type', 'all', '--force')
        types = {type(c.args[0]).__name__ for c in mock_create.call_args_list}
        self.assertIn('SystemVersion', types)
        self.assertNotIn('Organization', types)

    @patch('dbdb.core.management.commands.create_twitter_cards.create_twitter_card')
    def test_name_filter_limits_to_matching_system(self, mock_create):
        call_command('create_twitter_cards', 'sqlite', '--type', 'db')
        self.assertEqual(mock_create.call_count, 1)
        sv = mock_create.call_args.args[0]
        self.assertIsInstance(sv, SystemVersion)
        self.assertEqual(sv.system.slug, 'sqlite')


class OrganizationCardSignalTestCase(TestCase):

    def _make_org_mock(self, original_logo, current_logo_name):
        org = MagicMock(spec=Organization)
        org._original_logo = original_logo
        if current_logo_name:
            org.logo.__bool__ = MagicMock(return_value=True)
            org.logo.name = current_logo_name
        else:
            org.logo.__bool__.return_value = False
        return org

    @patch('dbdb.core.utils.twitter_card.create_twitter_card')
    def test_card_regenerated_when_logo_changes(self, mock_create):
        from dbdb.core.signals import _org_regen_card_on_logo_change
        org = self._make_org_mock(original_logo='', current_logo_name='logos/gza.png')
        _org_regen_card_on_logo_change(sender=Organization, instance=org, created=False)
        mock_create.assert_called_once_with(org)

    @patch('dbdb.core.utils.twitter_card.create_twitter_card')
    def test_card_not_regenerated_when_logo_unchanged(self, mock_create):
        from dbdb.core.signals import _org_regen_card_on_logo_change
        org = self._make_org_mock(original_logo='logos/gza.png', current_logo_name='logos/gza.png')
        _org_regen_card_on_logo_change(sender=Organization, instance=org, created=False)
        mock_create.assert_not_called()

    @patch('dbdb.core.utils.twitter_card.create_twitter_card')
    def test_card_not_regenerated_when_no_logo(self, mock_create):
        from dbdb.core.signals import _org_regen_card_on_logo_change
        org = self._make_org_mock(original_logo='', current_logo_name=None)
        _org_regen_card_on_logo_change(sender=Organization, instance=org, created=False)
        mock_create.assert_not_called()


class OrganizationViewMetaTestCase(TestCase):

    fixtures = [
        'adminuser.json',
        'core_features.json',
        'core_attributes.json',
        'core_system.json',
    ]

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.org = Organization.objects.create(name='Raekwon', slug='raekwon')

    def test_twitter_card_type_is_large_image(self):
        response = self.client.get(reverse('organization', args=['raekwon']))
        self.assertContains(response, 'summary_large_image')

    def test_og_image_present_when_card_file_exists(self):
        # Give the org a logo value so get_meta_image() doesn't bail early
        Organization.objects.filter(pk=self.org.pk).update(logo='logos/fake.png')
        with tempfile.TemporaryDirectory() as tmp:
            card_dir = os.path.join(tmp, 'org')
            os.makedirs(card_dir)
            with open(os.path.join(card_dir, 'raekwon.png'), 'wb') as f:
                f.write(_tiny_png())
            with self.settings(TWITTER_CARD_ROOT=tmp, TWITTER_CARD_URL='/media/cards/'):
                response = self.client.get(reverse('organization', args=['raekwon']))
        self.assertContains(response, 'cards/org/raekwon.png')

    def test_og_image_absent_when_no_card_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.settings(TWITTER_CARD_ROOT=tmp, TWITTER_CARD_URL='/media/cards/'):
                response = self.client.get(reverse('organization', args=['raekwon']))
        self.assertNotContains(response, 'cards/org/raekwon.png')
