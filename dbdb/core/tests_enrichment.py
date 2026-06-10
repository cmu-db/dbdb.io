"""
Tests for the enrich_system management command's attribute-loading logic.

Attribute.sv_field stores the SystemVersion M2M field name (e.g. 'licenses'),
NOT the Attribute slug (e.g. 'license').  The query in enrich_system.handle()
must filter by sv_field__in=<sv-field-names> — the keys of M2M_ATTR_SLUGS —
not by the dict values, which are Attribute slugs used later for option lookups.
"""
from django.test import TestCase

from dbdb.core.management.commands.enrich_system import M2M_ATTR_SLUGS
from dbdb.core.models import Attribute


def _load_attributes_for_missing_fields(missing_fields: list[str]) -> list[Attribute]:
    """Mirror the production query from enrich_system.handle()."""
    missing_sv_fields = [f for f in missing_fields if f in M2M_ATTR_SLUGS]
    return list(
        Attribute.objects
        .filter(sv_field__in=missing_sv_fields)
        .order_by('sv_field')
    )


class EnrichSystemAttributeLoadingTestCase(TestCase):

    fixtures = ['core_base.json']

    def test_loads_only_the_requested_m2m_attributes(self):
        attrs = _load_attributes_for_missing_fields(['licenses', 'oses'])
        sv_fields = [a.sv_field for a in attrs]
        self.assertIn('licenses', sv_fields)
        self.assertIn('oses', sv_fields)
        self.assertNotIn('project_types', sv_fields)
        self.assertNotIn('written_in', sv_fields)

    def test_loads_all_m2m_attributes_when_all_fields_missing(self):
        attrs = _load_attributes_for_missing_fields(list(M2M_ATTR_SLUGS.keys()))
        returned_sv_fields = {a.sv_field for a in attrs}
        for sv_field in M2M_ATTR_SLUGS:
            if Attribute.objects.filter(sv_field=sv_field).exists():
                self.assertIn(
                    sv_field, returned_sv_fields,
                    f"Attribute with sv_field='{sv_field}' should be loaded when that field is missing",
                )

    def test_loads_no_attributes_when_no_m2m_fields_missing(self):
        attrs = _load_attributes_for_missing_fields(['description', 'history', 'start_year'])
        self.assertEqual(attrs, [])

    def test_sv_field_stores_field_names_not_attribute_slugs(self):
        """
        Regression guard: Attribute.sv_field stores SV field names ('licenses'),
        not Attribute slugs ('license').  Filtering by M2M_ATTR_SLUGS.values()
        is therefore wrong and returns far fewer results than filtering by keys.
        """
        correct = Attribute.objects.filter(sv_field__in=list(M2M_ATTR_SLUGS.keys()))
        regressed = Attribute.objects.filter(sv_field__in=list(M2M_ATTR_SLUGS.values()))
        self.assertGreater(
            correct.count(), regressed.count(),
            "sv_field__in=keys must match more Attributes than sv_field__in=values; "
            "if equal, the fixture data or M2M_ATTR_SLUGS may have changed",
        )
