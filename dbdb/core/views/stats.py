import collections
from functools import reduce

from django.db.models import Q
from django.shortcuts import render
from django.views import View

from dbdb.core.models import (
    License,
    ProgrammingLanguage,
    ProjectType,
    System,
    SystemVersion,
)

Stat = collections.namedtuple('Stat', ['label', 'items', 'search_field', 'systems', 'count'])
StatItem = collections.namedtuple('StatItem', ['label', 'value', 'slug', 'url'])


# ==============================================
# StatsView
# ==============================================
class StatsView(View):

    template_name = 'core/stats.html'
    default_limit = 10
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

        # Versions
        if stats_type is None or stats_type == "revisions":
            stats.append( self.get_system_stat('Revisions', 'ver', labels, slugs, self.default_limit ) )

        # Views
        if stats_type is None or stats_type == "views":
            stats.append( self.get_system_stat('Views', 'view_count', labels, slugs, self.default_limit ) )

        # Licenses
        if stats_type is None or stats_type == "license":
            limit = -1 if stats_type == "license" else self.default_limit
            labels = dict(License.objects.all().values_list('id', 'name'))
            slugs = dict(License.objects.all().values_list('id', 'slug'))
            stats.append( self.get_version_stat('License', 'licenses', 'license', labels, slugs, False, limit) )

        # Implementation Language
        if stats_type is None or stats_type == "programming":
            limit = -1 if stats_type == "programming" else self.default_limit
            all_values = ProgrammingLanguage.objects.all()
            labels = dict(all_values.values_list('id', 'name'))
            slugs = dict(all_values.values_list('id', 'slug'))
            stats.append( self.get_version_stat('Implementation', 'written_in', 'programming', labels, slugs, False, limit) )

        # Project Type
        if stats_type is None or stats_type == "project_type":
            limit = -1 if stats_type == "project_type" else self.default_limit
            labels = dict(ProjectType.objects.all().values_list('id', 'name'))
            slugs = dict(ProjectType.objects.all().values_list('id', 'slug'))
            stats.append( self.get_version_stat('Project Type', 'project_types', 'type', labels, slugs, False, limit) )

        return render(request, self.template_name, context={
            'activate': 'stats', # NAV-LINKS
            'stats': stats,
            'stats_type': stats_type,
        })

    pass