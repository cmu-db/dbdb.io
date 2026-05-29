import datetime
import random

import pytz

from django.db.models import Count, Q
from django.shortcuts import render
from django.utils import timezone
from django.views import View

from dbdb.core.models import SavedSearch, System, SystemVersion


# ==============================================
# HomeView
# ==============================================
class HomeView(View):

    ITEMS_TO_SHOW = 5

    template_name = 'core/home.html'

    def get(self, request):
        # calculate date window
        start_date = timezone.now().astimezone(pytz.utc) - datetime.timedelta(days=30) # rolling 30 days
        start_date = datetime.datetime.combine(start_date.date(), datetime.time(0, 0, 0))
        start_date = pytz.utc.localize(start_date)

        # get top systems by modified date
        most_recent = System.objects \
            .order_by('-modified')
        most_recent = most_recent[:HomeView.ITEMS_TO_SHOW]

        # get top systems by number of (windowed) versions
        most_versions = System.objects \
            .annotate(num_versions=Count('versions__id', filter=Q(versions__created__gte=start_date))) \
            .order_by('-num_versions', 'name') \
            .filter(num_versions__gt=0)
        most_versions = most_versions[:HomeView.ITEMS_TO_SHOW]

        # get top systems by number of (windowed) visits
        most_visits = System.objects \
            .annotate(num_visits=Count('visits__id', filter=Q(visits__created__gte=start_date))) \
            .order_by('-num_visits', 'name') \
            .filter(num_visits__gt=0)
        most_visits = most_visits[:HomeView.ITEMS_TO_SHOW]

        # count numb systems
        num_systems = System.objects.all().count()

        now = timezone.now()

        # find the most recent year that has at least one SystemVersion
        new_in_year = now.year
        while not SystemVersion.objects.filter(start_year=new_in_year).exists():
            new_in_year -= 1

        # pick 3 saved searches per hour using a deterministic seed
        hour_seed = now.year * 1000000 + now.month * 10000 + now.day * 100 + now.hour
        all_saved_searches = list(SavedSearch.objects.all())
        if len(all_saved_searches) >= 3:
            featured_searches = random.Random(hour_seed).sample(all_saved_searches, 3)
        else:
            featured_searches = all_saved_searches

        return render(request, self.template_name, {
            'activate': "home",
            'most_recent': most_recent,
            'most_versions': most_versions,
            'most_visits': most_visits,

            'no_nav_search': True,
            'num_systems': num_systems,
            'featured_searches': featured_searches,
            'new_in_year': new_in_year,
        })

    pass