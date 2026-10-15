import csv
import os
import tempfile
from io import StringIO

from django.core.management import call_command
from django.test import TestCase

from dbdb.core.models import Feature, System, SystemFeature, SystemVersion


class ImportSystemsTestCase(TestCase):

    fixtures = ['adminuser.json', 'core_features.json', 'core_attributes.json']

    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmpdir.cleanup)

    def _write_csv(self, rows: list[list[str]]) -> str:
        path = os.path.join(self.tmpdir.name, 'systems.csv')
        with open(path, 'w', newline='') as fh:
            csv.writer(fh).writerows(rows)
        return path

    def _run(self, rows, *args) -> tuple[str, str]:
        out, err = StringIO(), StringIO()
        call_command('import_systems', self._write_csv(rows), '--creator', 'admin', *args,
                     stdout=out, stderr=err)
        return out.getvalue(), err.getvalue()

    def _features(self, slug: str) -> dict[str, set[str]]:
        sv = SystemVersion.objects.get(system__slug=slug, is_current=True)
        return {
            sf.feature.slug: {o.slug for o in sf.options.all()}
            for sf in SystemFeature.objects.filter(version=sv)
        }

    def test_feature_columns_create_system_features(self):
        _, err = self._run([
            ['name', 'query-interface', 'storage-model'],
            ['WuTangDB', 'SQL, graphql', 'Hybrid'],
        ])
        self.assertEqual(err, '')
        self.assertEqual(self._features('wutangdb'), {
            'query-interface': {'sql', 'graphql'},
            'storage-model': {'hybrid'},
        })

    def test_feature_column_empty_value_creates_nothing(self):
        self._run([
            ['name', 'query-interface'],
            ['ShaolinDB', ''],
        ])
        self.assertEqual(self._features('shaolindb'), {})

    def test_feature_unmatched_option_is_reported(self):
        _, err = self._run([
            ['name', 'query-interface'],
            ['MethodDB', 'SQL, Protect Ya Neck'],
        ])
        self.assertIn("no FeatureOption match for 'Protect Ya Neck'", err)
        self.assertEqual(self._features('methoddb'), {'query-interface': {'sql'}})

    def test_single_valued_feature_keeps_first_option(self):
        Feature.objects.filter(slug='storage-model').update(multivalued=False)
        _, err = self._run([
            ['name', 'storage-model'],
            ['RaekwonDB', 'Hybrid, Custom'],
        ])
        self.assertIn("'storage-model' is not multivalued", err)
        self.assertEqual(self._features('raekwondb'), {'storage-model': {'hybrid'}})

    def test_feature_column_is_not_unknown(self):
        _, err = self._run([
            ['name', 'query-interface', 'bogus-column'],
            ['GhostfaceDB', 'SQL', 'x'],
        ])
        self.assertNotIn("'query-interface'", err)
        self.assertIn("Unknown header field 'bogus-column'", err)

    def test_dry_run_creates_nothing(self):
        out, _ = self._run([
            ['name', 'query-interface'],
            ['InspectahDB', 'SQL'],
        ], '--dry-run')
        self.assertFalse(System.objects.filter(slug='inspectahdb').exists())
        self.assertIn('SQL', out)

    def test_table_column_order(self):
        out, _ = self._run([
            ['name', 'description', 'query-interface'],
            ['MaskedDB', 'Liquid Swords', 'SQL'],
        ], '--dry-run')
        header = next(line for line in out.splitlines() if line.startswith('| Status'))
        columns = [c.strip() for c in header.strip('|').split('|')]
        self.assertEqual(columns, ['Status', 'Name', 'Logo', 'Slug', 'description', 'query-interface'])
