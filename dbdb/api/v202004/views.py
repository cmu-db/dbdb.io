# django imports
from django.shortcuts import render
# third-party imports
from rest_framework import generics
# project imports
from dbdb.core.models import System
from dbdb.core.models import SystemVersion
# local imports
from .serializers import SystemSerializer


# class based views

class SystemsView(generics.ListAPIView):

    queryset = System.objects.all()
    serializer_class = SystemSerializer

    def paginate_queryset(self, queryset):
        if self.paginator is None:
            return None

        items = self.paginator.paginate_queryset(queryset, self.request, view=self)

        # db optimizations - versions
        ids = { item.id for item in items }
        versions = SystemVersion.objects.filter(system_id__in=ids, is_current=True)
        versions_map = { sv.system_id : sv for sv in versions }
        for item in items:
            item._current = versions_map[item.id]

        return items

    pass
