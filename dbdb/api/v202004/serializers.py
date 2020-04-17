# stdlib imports
import collections
# third-party imports
from rest_framework import serializers
from rest_framework.reverse import reverse
# project imports
from dbdb.core.models import FeatureOption
from dbdb.core.models import System
from dbdb.core.models import SystemFeature


# serializers

class SystemSerializer(serializers.HyperlinkedModelSerializer):

    class Meta:
        model = System
        fields = [
            'href',
            'name',
            'former_names',
            'start_year',
            'end_year',
            'description',
            'history',
            'acquired_by',
            'developer',
            'countries',
            'features',
            'project_types',
            'urls',
            'version',
        ]

    href = serializers.SerializerMethodField()
    former_names = serializers.SerializerMethodField()
    start_year = serializers.SerializerMethodField()
    end_year = serializers.SerializerMethodField()
    description = serializers.SerializerMethodField()
    history = serializers.SerializerMethodField()
    acquired_by = serializers.SerializerMethodField()
    developer = serializers.SerializerMethodField()
    countries = serializers.SerializerMethodField()
    features = serializers.SerializerMethodField()
    project_types = serializers.SerializerMethodField()
    urls = serializers.SerializerMethodField()
    version = serializers.IntegerField(source='ver', read_only=True)

    def get_acquired_by(self, obj):
        current = obj.get_current()
        return current.acquired_by

    def get_countries(self, obj):
        current = obj.get_current()
        return list( map(str, current.countries) )

    def get_description(self, obj):
        current = obj.get_current()
        return current.description

    def get_developer(self, obj):
        current = obj.get_current()
        return current.developer

    def get_features(self, obj):
        current = obj.get_current()

        sysfeatures = SystemFeature.objects \
            .filter(system=current) \
            .select_related('feature') \
            .order_by('feature__slug')

        items = collections.OrderedDict()
        for sysfeature in sysfeatures:
            empty = True

            f = {
                'name': sysfeature.feature.label,
            }

            if sysfeature.feature.multivalued:
                f['values'] = []
                pass
            else:
                f['value'] = None
                pass

            if sysfeature.feature.multivalued:
                for option in sysfeature.options.all().order_by('slug'):
                    f['values'].append(option.value)
                    empty = False
            else:
                option = sysfeature.options.first()
                if option:
                    f['value'] = option.value
                    empty = False
                pass

            if not empty:
                items[sysfeature.feature_id] = f
            pass

        return list( items.values() )

    def get_former_names(self, obj):
        current = obj.get_current()
        return current.former_names if current.former_names else None

    def get_history(self, obj):
        current = obj.get_current()
        return current.history

    def get_href(self, obj):
        request = self.context['request']
        return reverse('system', args=[obj.slug], request=request)

    def get_end_year(self, obj):
        current = obj.get_current()
        return current.end_year

    def get_project_types(self, obj):
        current = obj.get_current()
        return list( map(str, current.project_types.all()) )

    def get_urls(self, obj):
        current = obj.get_current()
        data = {
            'docs': None if not current.tech_docs else current.tech_docs,
            'homepage': None if not current.url else current.url,
            'source': None if not current.source_url else current.source_url,
            'wikipedia': None if not current.wikipedia_url else current.wikipedia_url,
        }
        return data

    def get_start_year(self, obj):
        current = obj.get_current()
        return current.start_year

    pass

