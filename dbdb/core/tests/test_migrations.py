import importlib

from django.apps import apps
from django.test import TestCase

from dbdb.core.models import Organization, SystemVersion

fix_uk = importlib.import_module('dbdb.core.migrations.0100_fix_uk_country_code')


class FixUkCountryCodeMigrationTestCase(TestCase):

    fixtures = ['adminuser.json', 'core_features.json', 'core_attributes.json', 'core_system.json']

    def _countries(self, model, **filters) -> str:
        return model.objects.filter(**filters).values_list('countries', flat=True).get()

    def test_replaces_uk_with_gb(self):
        SystemVersion.objects.filter(system__slug='sqlite', is_current=True).update(countries='UK,US')
        SystemVersion.objects.filter(system__slug='xxx', is_current=True).update(countries='GB,UK')
        Organization.objects.create(name='Wu-Tang Financial', slug='wu-tang-financial', countries='UK')

        fix_uk.fix_country_codes(apps, None)

        self.assertEqual(self._countries(SystemVersion, system__slug='sqlite', is_current=True), 'GB,US')
        # Already had GB, so the duplicate is dropped
        self.assertEqual(self._countries(SystemVersion, system__slug='xxx', is_current=True), 'GB')
        self.assertEqual(self._countries(Organization, slug='wu-tang-financial'), 'GB')
