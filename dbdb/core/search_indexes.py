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

    countries = indexes.MultiValueField()
    derived_from = indexes.MultiValueField()
    features = indexes.MultiValueField()
    feature_options = indexes.MultiValueField()

    def get_model(self):
        return SystemVersion

    def index_queryset(self, using=None):
        return self.get_model().objects \
            .filter(is_current=True) \
            .select_related('system')

    def prepare_countries(self, obj):
        values = [
            c
            for c in obj.countries
        ]

        return values

    def prepare_derived_from(self, obj):
        if obj.meta_id is None:
            return []

        values = [
            pk
            for pk in obj.meta.derived_from.values_list('id', flat=True)
        ]

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

    pass
