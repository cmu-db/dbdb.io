import collections
from functools import reduce

from django.db.models import Count, Q
from django.shortcuts import render
from django.views import View

from dbdb.core.models import (
    AttributeOption,
    Feature,
    FeatureOption,
    Organization,
    System,
    SystemFeature,
    SystemVersion,
)

Stat = collections.namedtuple('Stat', ['label', 'items', 'search_field', 'systems', 'count', 'organizations'], defaults=[False])
StatItem = collections.namedtuple('StatItem', ['label', 'value', 'slug', 'url'])


# ==============================================
# StatsView
# ==============================================
class StatsView(View):

    template_name = 'core/stats.html'
    default_limit = 30
    is_privileged = False

    def get_bycountries(self, limit):
        def reduce_countries(mapping, item):
            countries = item.countries.split(',')
            for c in countries:
                if c:
                    mapping[c] = mapping.get(c, 0) + 1
            return mapping

        system_countries = SystemVersion.objects \
            .filter(is_current=True) \
            .values_list('system_id', 'countries', named=True)
        system_countries = reduce(reduce_countries, system_countries, {})

        system_countries = [
            StatItem(k, v, k, None)
            for k,v in system_countries.items()
        ]
        system_countries.sort(key=lambda i: i.value, reverse=True)

        stat = Stat(
            'Country of Origin',
            system_countries[:limit],
            'country',
            False,
            len(system_countries)
        )

        return stat

    def get_version_stat(self, title, field, search_field, labels, slugs, is_systems, limit):

        def reduce_counts(mapping, item):
            assert mapping is not None
            if item is not None:
                mapping[item] = mapping.get(item, 0) + 1

        values = SystemVersion.objects \
            .filter(is_current=True) \
            .filter(~Q(**{field: None})) \
            .values_list('system_id', field, named=True)

        counts = { }
        for v in values:
            counts[v[1]] = counts.get(v[1], 0) + 1
        #counts = reduce(reduce_counts, values, { })

        stat_items = [ ]

        if is_systems:
            stat_items = [
                StatItem(System.objects.get(id=k), v, slugs[k], None)
                for k,v in counts.items()
            ]
        else:
            stat_items = [
                StatItem(labels[k], v, slugs[k], None)
                for k,v in counts.items()
            ]

        stat_items.sort(key=lambda i: i.value, reverse=True)
        stat = Stat(
            title,
            stat_items[:limit],
            search_field,
            is_systems,
            len(stat_items)
        )

        return stat

    def get_attributeoption_stat(self, title, attr_slug, sv_related_name, search_field, limit):
        """Count current SystemVersion rows linked to each AttributeOption of a given Attribute."""
        options = (
            AttributeOption.objects
            .filter(attribute__slug=attr_slug)
            .annotate(
                count=Count(sv_related_name, filter=Q(**{sv_related_name + '__is_current': True}))
            )
            .filter(count__gt=0)
            .order_by('-count')
        )
        stat_items = [StatItem(opt.name, opt.count, opt.slug, None) for opt in options]
        return Stat(title, stat_items[:limit], search_field, False, len(stat_items))

    def get_feature_stat(self, title, feature_slug, limit):
        """Count current SystemVersions using each FeatureOption of a given Feature.

        When SystemFeature.system is set and the row has no own options, the
        options are inherited from that system's current SystemFeature for the
        same feature (one level of inheritance, matching get_my_or_parent_options).
        """
        sf_list = list(
            SystemFeature.objects
            .filter(feature__slug=feature_slug, version__is_current=True)
            .prefetch_related('options')
            .select_related('version')
        )

        # Map system_id → direct FeatureOptions so parent lookups are O(1)
        direct_opts_by_system = {}
        for sf in sf_list:
            opts = list(sf.options.all())
            if opts:
                direct_opts_by_system[sf.version.system_id] = opts

        counter = collections.Counter()
        for sf in sf_list:
            opts = list(sf.options.all())
            if opts:
                effective = opts
            elif sf.system_id is not None:
                effective = direct_opts_by_system.get(sf.system_id, [])
            else:
                effective = []
            for opt in effective:
                counter[opt] += 1

        stat_items = [
            StatItem(opt.value, count, opt.slug, None)
            for opt, count in sorted(counter.items(), key=lambda x: -x[1])
            if count > 0
        ]
        return Stat(title, stat_items[:limit], feature_slug, False, len(stat_items))

    def get_system_stat(self, title, field, labels, slugs, limit):
        values = System.objects \
            .order_by('-'+field)[:limit]
            #.values_list('id', field, named=True)

        stat_items = [ ]
        for s in values:
            if field == 'view_count' and self.is_privileged == False:
                value = "#%02d" % (len(stat_items)+1)
            else:
                value = getattr(s, field)
            stat_items.append(StatItem(s, value, s.slug, s.get_absolute_url))
        # FOR

        # stat_items.sort(key=lambda i: i.value, reverse=True)
        stat = Stat(
            title,
            stat_items[:limit],
            None,
            True,
            len(stat_items)
        )

        return stat


    def get_org_stat(self, title, count_field, count_filter, search_field, limit):
        orgs = (
            Organization.objects
            .annotate(count=Count(count_field, filter=count_filter))
            .filter(count__gt=0)
            .order_by('-count')
        )
        stat_items = [
            StatItem(org, org.count, org.slug, None)
            for org in orgs[:limit]
        ]
        return Stat(title, stat_items, search_field, False, len(stat_items), organizations=True)

    def get(self, request, stats_type=None):
        self.is_privileged = request.user.is_superuser or request.user.is_staff
        stats = []

        # Countries
        if stats_type is None or stats_type == "country":
            limit = -1 if stats_type == "country" else self.default_limit
            stats.append( self.get_bycountries(limit) )

        all_values = System.objects.all()
        labels = dict(all_values.values_list('id', 'name'))
        slugs = dict(all_values.values_list('id', 'slug'))

        # Data Model
        if stats_type is None or stats_type == "data-model":
            limit = -1 if stats_type == "data-model" else self.default_limit
            stats.append(self.get_feature_stat('Data Model', 'data-model', limit))

        # Query Interface
        if stats_type is None or stats_type == "query-interface":
            limit = -1 if stats_type == "query-interface" else self.default_limit
            stats.append(self.get_feature_stat('Query Interface', 'query-interface', limit))

        # Compatibility
        if stats_type is None or stats_type == "compatible":
            stats.append( self.get_version_stat('Compatibility', 'compatible_with', 'compatible', labels, slugs, True, self.default_limit) )

        # Derived From
        if stats_type is None or stats_type == "derived":
            stats.append( self.get_version_stat('Derived From', 'derived_from', 'derived', labels, slugs, True, self.default_limit) )

        # Embeds
        if stats_type is None or stats_type == "embeds":
            stats.append( self.get_version_stat('Embeds / Uses', 'embedded', 'embeds', labels, slugs, True, self.default_limit ) )

        # Hosted By
        if stats_type is None or stats_type == "hosted_by":
            stats.append( self.get_version_stat('Hosted Offerings', 'hosted_services', 'hosted_by', labels, slugs, True, self.default_limit) )

        # # Versions
        # if stats_type is None or stats_type == "revisions":
        #     stats.append( self.get_system_stat('Revisions', 'ver', labels, slugs, self.default_limit ) )
        #
        # # Views
        # if stats_type is None or stats_type == "views":
        #     stats.append( self.get_system_stat('Views', 'view_count', labels, slugs, self.default_limit ) )

        # Licenses
        if stats_type is None or stats_type == "license":
            limit = -1 if stats_type == "license" else self.default_limit
            stats.append(self.get_attributeoption_stat('License', 'license', 'system_licenses', 'license', limit))

        # Implementation Language
        if stats_type is None or stats_type == "programming":
            limit = -1 if stats_type == "programming" else self.default_limit
            stats.append(self.get_attributeoption_stat('Implementation', 'programming-language', 'system_written_in', 'programming-language', limit))

        # Project Type
        if stats_type is None or stats_type == "project_type":
            limit = -1 if stats_type == "project_type" else self.default_limit
            stats.append(self.get_attributeoption_stat('Project Type', 'project-type', 'system_project_types', 'project-type', limit))

        # Developer Organizations
        if stats_type is None or stats_type == "developer":
            limit = -1 if stats_type == "developer" else self.default_limit
            stats.append(self.get_org_stat(
                'Developers',
                'developed_systems',
                Q(developed_systems__is_current=True),
                'developer',
                limit,
            ))

        # Acquisition Organizations
        if stats_type is None or stats_type == "acquired-by":
            limit = -1 if stats_type == "acquired-by" else self.default_limit
            stats.append(self.get_org_stat(
                'Acquisitions',
                'acquisitions',
                Q(acquisitions__version__is_current=True),
                'acquired-by',
                limit,
            ))

        num_systems = SystemVersion.objects.filter(is_current=True).count()

        return render(request, self.template_name, context={
            'activate': 'stats', # NAV-LINKS
            'stats': stats,
            'stats_type': stats_type,
            'num_systems': num_systems,
        })

    pass
