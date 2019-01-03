# stdlib imports
import datetime
# third-party imports
from haystack import indexes
# local imports
from .models import Feature
from .models import FeatureOption
from .models import SystemVersion


class SystemVersionIndex(indexes.SearchIndex, indexes.Indexable):

    text = indexes.NgramField(document=True, use_template=True)

    created = indexes.DateTimeField(model_attr='created')
    letter = indexes.CharField()
    logo = indexes.CharField(model_attr='logo')
    name = indexes.CharField(model_attr='system__name')
    slug = indexes.CharField(model_attr='system__slug')
    start_year = indexes.IntegerField(model_attr='start_year', null=True)
    end_year = indexes.IntegerField(model_attr='end_year', null=True)

    lowercase_name = indexes.NgramField()

    compatible_with = indexes.MultiValueField()
    countries = indexes.MultiValueField()
    derived_from = indexes.MultiValueField()
    inspired_by = indexes.MultiValueField()
    oses = indexes.MultiValueField()
    written_langs = indexes.MultiValueField()
    project_types = indexes.MultiValueField()
    licenses = indexes.MultiValueField()

    features = indexes.MultiValueField()
    feature_options = indexes.MultiValueField()

    def get_model(self):
        return SystemVersion

    def index_queryset(self, using=None):
        return self.get_model().objects \
            .filter(is_current=True) \
            .select_related('system')

    def prepare_compatible_with(self, obj):
        if obj.meta_id is None:
            return []

        values = list(
            obj.meta.compatible_with.values_list('slug', flat=True)
        )

        return values

    def prepare_countries(self, obj):
        values = [
            c
            for c in obj.countries
        ]

        return values

    def prepare_derived_from(self, obj):
        if obj.meta_id is None:
            return []

        values = list(
            obj.meta.derived_from.values_list('slug', flat=True)
        )

        return values

    def prepare_inspired_by(self, obj):
        if obj.meta_id is None:
            return []

        values = list(
            obj.meta.inspired_by.values_list('slug', flat=True)
        )

        return values

    def prepare_oses(self, obj):
        if obj.meta_id is None:
            return []

        values = [
            pk
            for pk in obj.meta.oses.values_list('slug', flat=True)
        ]

        return values

    def prepare_written_langs(self, obj):
        if obj.meta_id is None:
            return []

        values = [
            pk
            for pk in obj.meta.written_in.values_list('slug', flat=True)
        ]

        return values

    def prepare_project_types(self, obj):
        values = list(
            obj.project_types.values_list('slug', flat=True)
        )

        return values

    def prepare_licenses(self, obj):
        if obj.meta_id is None:
            return []

        values = list(
            obj.meta.licenses.values_list('slug', flat=True)
        )

        return values

    def prepare_features(self, obj):
        values = [
            pk
            for pk in Feature.objects \
                .filter(system_features__system_id=obj.id) \
                .values_list('id', flat=True)
        ]

        return values

    def prepare_feature_options(self, obj):
        values = [
            pk
            for pk in FeatureOption.objects \
                .filter(system_features__system_id=obj.id) \
                .values_list('id', flat=True)
        ]

        return values

    def prepare_letter(self, obj):
        return obj.system.name[0].lower()

    def prepare_lowercase_name(self, obj):
        return obj.system.name.lower().strip()

    pass
