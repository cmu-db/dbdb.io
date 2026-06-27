import datetime
import random

import pytz

from django.conf import settings
from django.db.models import Count, Q
from django.db.models.aggregates import Max
from django.shortcuts import render
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.cache import cache_control
from meta.views import MetadataMixin

from dbdb.core.models import Feature, SavedSearch, System, SystemFeature, SystemVersion


def _attach_data_models(systems):
    # Supports both System objects (no system_id attr → use s.id)
    # and SystemVersion objects (have a system_id attr).
    def _sys_id(s):
        return getattr(s, 'system_id', s.id)

    ids = [_sys_id(s) for s in systems]
    sf_map = {}
    for sf in (SystemFeature.objects
               .filter(version__is_current=True, version__system_id__in=ids, feature__slug='data-model')
               .prefetch_related('options', 'system')):
        opts = set(sf.get_my_or_parent_options())
        if opts:
            sf_map[sf.version.system_id] = opts
    for s in systems:
        sid = _sys_id(s)
        if sid in sf_map:
            s.all_data_models = sf_map[sid]
        else:
            # No direct data-model feature; fall back to all_data_models() which
            # recurses into hosted_services.
            sv = s if isinstance(s, SystemVersion) else None
            if sv is None:
                try:
                    sv = s.current()
                except SystemVersion.DoesNotExist:
                    pass
            s.all_data_models = sv.all_data_models() if sv else set()
    return systems


# ==============================================
# HomeView
# ==============================================
@method_decorator(cache_control(public=True, max_age=3600), name='dispatch')
class HomeView(MetadataMixin, View):

    template_name = 'core/home.html'
    title = f'{settings.DBDB_SITE_NAME}{settings.DBDB_TITLE_SEPARATOR}{settings.DBDB_SITE_TAGLINE}'
    description = 'The encyclopedia of database systems from Carnegie Mellon University.'
    twitter_type = 'summary'

    def get_meta_extra_props(self, context=None):
        from django.contrib.humanize.templatetags.humanize import intcomma
        return {
            'twitter:label1': '# of Systems',
            'twitter:data1': intcomma(self.num_systems),
            'twitter:label2': 'Last Updated',
            'twitter:data2': f'{self.newest_sv.created:%B %-d, %Y}' if self.newest_sv else "-",
        }

    def get(self, request):
        # calculate date window
        start_date = timezone.now().astimezone(pytz.utc) - datetime.timedelta(days=30) # rolling 30 days
        start_date = datetime.datetime.combine(start_date.date(), datetime.time(0, 0, 0))
        start_date = pytz.utc.localize(start_date)

        now = timezone.now()

        # get top systems by current SystemVersion creation date
        most_recent = list(
            System.objects
            .annotate(sv_created=Max('versions__created', filter=Q(versions__is_current=True)))
            .order_by('-sv_created')[:settings.DBDB_HOME_LISTINGS_NUM_ENTRIES]
        )
        _attach_data_models(most_recent)
        for s in most_recent:
            delta = (now - s.sv_created).days
            if delta == 0:
                s.metric = "today"
            elif delta == 1:
                s.metric = "1d ago"
            else:
                s.metric = f"{delta}d ago"
        self.newest_sv = most_recent[0].current()

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
        prev_start_date = start_date - datetime.timedelta(days=30)
        most_visits = list(
            System.objects
            .annotate(num_visits=Count('visits__id', filter=Q(visits__created__gte=start_date)))
            .order_by('-num_visits', 'name')
            .filter(num_visits__gt=0)[:settings.DBDB_HOME_LISTINGS_NUM_ENTRIES]
        )
        _attach_data_models(most_visits)

        # Fetch previous-period visit counts for the trend arrow
        prev_visits_map = dict(
            System.objects
            .filter(id__in=[s.id for s in most_visits])
            .annotate(prev_visits=Count(
                'visits__id',
                filter=Q(visits__created__gte=prev_start_date, visits__created__lt=start_date)
            ))
            .values_list('id', 'prev_visits')
        )
        for s in most_visits:
            prev = prev_visits_map.get(s.id, 0)
            s.visits_delta = s.num_visits - prev
            if prev == 0:
                s.metric = "new"
            else:
                pct = round(s.visits_delta / prev * 100)
                s.metric = f"+{pct}%" if pct >= 0 else f"{pct}%"

        # count num systems
        self.num_systems = System.objects.all().count()

        # find the most recent year that has at least one SystemVersion
        years_start = SystemVersion.objects.filter(is_current=True, start_year__gt=0).aggregate(
            start_year=Max('start_year')
        )
        new_in_year = years_start["start_year"]

        # pick N saved searches per hour using a deterministic seed
        hour_seed = now.year * 1000000 + now.month * 10000 + now.day * 100 + now.hour
        all_saved_searches = list(SavedSearch.objects.all())
        if len(all_saved_searches) >= settings.DBDB_HOME_SAVEDSEARCH_NUM_ENTRIES:
            featured_searches = random.Random(hour_seed).sample(all_saved_searches, settings.DBDB_HOME_SAVEDSEARCH_NUM_ENTRIES)
        else:
            featured_searches = all_saved_searches

        # data models with system counts for Browse by Data Model section
        # Use the same two-pass inheritance logic as StatsView.get_feature_stat() so
        # systems that inherit a data model via SystemFeature.system are counted correctly.
        dm_feature = Feature.objects.filter(slug='data-model').first()
        if dm_feature:
            sf_list = list(
                SystemFeature.objects
                .filter(feature=dm_feature, version__is_current=True)
                .prefetch_related('options')
                .select_related('version')
            )
            direct_opts_by_system = {}
            for sf in sf_list:
                opts = list(sf.options.all())
                if opts:
                    direct_opts_by_system[sf.version.system_id] = opts

            counts = {}
            for sf in sf_list:
                opts = list(sf.options.all())
                if opts:
                    effective = opts
                elif sf.system_id is not None:
                    effective = direct_opts_by_system.get(sf.system_id, [])
                else:
                    effective = []
                for opt in effective:
                    counts[opt] = counts.get(opt, 0) + 1

            data_models = []
            for opt, count in sorted(counts.items(), key=lambda x: -x[1]):
                opt.system_count = count
                data_models.append(opt)
        else:
            data_models = []

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
            'meta': self.get_meta(),
            'activate': "home",
            'most_recent': most_recent,
            'most_versions': most_versions,
            'most_visits': most_visits,

            'no_nav_search': True,
            'num_systems': self.num_systems,
            'featured_searches': featured_searches,
            'new_in_year': new_in_year,
            'data_models': data_models,
            'spotlight_version': spotlight_version,
            'spotlight_data_model': spotlight_data_model,
        })

    pass
