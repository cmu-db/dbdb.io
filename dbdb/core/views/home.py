import datetime
import random

import pytz

from django.conf import settings
from django.db.models import Count, Q
from django.shortcuts import render
from django.utils import timezone
from django.views import View

from dbdb.core.models import Feature, FeatureOption, SavedSearch, System, SystemFeature, SystemVersion


def _attach_data_models(systems):
    ids = [s.id for s in systems]
    sf_map = {}
    for sf in (SystemFeature.objects
               .filter(version__is_current=True, version__system_id__in=ids, feature__slug='data-model')
               .prefetch_related('options', 'system')):
        vals = [o.value for o in sf.get_my_or_parent_options()]
        if vals:
            sf_map[sf.version.system_id] = ' · '.join(vals[:2])
    for s in systems:
        s.data_model_str = sf_map.get(s.id, '')
    return systems


# ==============================================
# HomeView
# ==============================================
class HomeView(View):

    template_name = 'core/home.html'

    def get(self, request):
        # calculate date window
        start_date = timezone.now().astimezone(pytz.utc) - datetime.timedelta(days=30) # rolling 30 days
        start_date = datetime.datetime.combine(start_date.date(), datetime.time(0, 0, 0))
        start_date = pytz.utc.localize(start_date)

        now = timezone.now()

        # get top systems by modified date
        most_recent = list(System.objects.order_by('-modified')[:settings.DBDB_HOME_LISTINGS_NUM_ENTRIES])
        _attach_data_models(most_recent)
        for s in most_recent:
            delta = (now - s.modified).days
            if delta == 0:
                s.metric = "today"
            elif delta == 1:
                s.metric = "1d ago"
            else:
                s.metric = f"{delta}d ago"

        # get top systems by number of (windowed) versions
        most_versions = list(
            System.objects
            .annotate(num_versions=Count('versions__id', filter=Q(versions__created__gte=start_date)))
            .order_by('-num_versions', 'name')
            .filter(num_versions__gt=0)[:settings.DBDB_HOME_LISTINGS_NUM_ENTRIES]
        )
        _attach_data_models(most_versions)
        for s in most_versions:
            s.metric = f"{s.num_versions} ✎"

        # get top systems by number of (windowed) visits
        most_visits = list(
            System.objects
            .annotate(num_visits=Count('visits__id', filter=Q(visits__created__gte=start_date)))
            .order_by('-num_visits', 'name')
            .filter(num_visits__gt=0)[:settings.DBDB_HOME_LISTINGS_NUM_ENTRIES]
        )
        _attach_data_models(most_visits)
        for s in most_visits:
            v = s.num_visits
            s.metric = f"{v/1000:.1f}k" if v >= 1000 else str(v)

        # count num systems
        num_systems = System.objects.all().count()

        # find the most recent year that has at least one SystemVersion
        new_in_year = now.year
        while not SystemVersion.objects.filter(start_year=new_in_year).exists():
            new_in_year -= 1

        # pick N saved searches per hour using a deterministic seed
        hour_seed = now.year * 1000000 + now.month * 10000 + now.day * 100 + now.hour
        all_saved_searches = list(SavedSearch.objects.all())
        if len(all_saved_searches) >= settings.DBDB_HOME_SAVEDSEARCH_NUM_ENTRIES:
            featured_searches = random.Random(hour_seed).sample(all_saved_searches, settings.DBDB_HOME_SAVEDSEARCH_NUM_ENTRIES)
        else:
            featured_searches = all_saved_searches

        # data models with system counts for Browse by Data Model section
        dm_feature = Feature.objects.filter(slug='data-model').first()
        data_models = list(
            FeatureOption.objects
            .filter(feature=dm_feature)
            .annotate(system_count=Count('system_features__version__system', distinct=True))
            .filter(system_count__gt=0)
            .order_by('-system_count')
        ) if dm_feature else []

        # editor's pick: first spotlight_enabled system
        spotlight_version = None
        spotlight_data_model = None
        spotlight_system = System.objects.filter(spotlight_enabled=True).order_by('name').first()
        if spotlight_system:
            spotlight_version = (
                SystemVersion.objects
                .filter(system=spotlight_system, is_current=True)
                .prefetch_related('licenses', 'tags')
                .first()
            )
        if spotlight_version and data_models:
            sp_dm_slugs = set(
                SystemFeature.objects
                .filter(version=spotlight_version, feature__slug='data-model')
                .values_list('options__slug', flat=True)
            )
            for dm in data_models:  # already ordered by -system_count
                if dm.slug in sp_dm_slugs:
                    spotlight_data_model = dm
                    break

        return render(request, self.template_name, {
            'activate': "home",
            'most_recent': most_recent,
            'most_versions': most_versions,
            'most_visits': most_visits,

            'no_nav_search': True,
            'num_systems': num_systems,
            'featured_searches': featured_searches,
            'new_in_year': new_in_year,
            'data_models': data_models,
            'spotlight_version': spotlight_version,
            'spotlight_data_model': spotlight_data_model,
        })

    pass
