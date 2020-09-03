# stdlib imports
# django imports
from django.core.management import BaseCommand
from django.conf import settings
from django.contrib.auth import get_user_model

from dbdb.core.models import System
from dbdb.core.models import SystemFeature
from dbdb.core.models import SystemVersion
from dbdb.core.models import SystemVersionMetadata
from dbdb.core.views import EmptyFieldsView

class Command(BaseCommand):

    FIELD_REWARD = 10
    CITATION_REWARD = 5

    def handle(self, *args, **options):

        version_fields, meta_fields = EmptyFieldsView.build_search_fields(True)
        version_fields = set(version_fields) - set([
            "is_current",
        ])
        meta_fields = set(meta_fields) - set([
            "systemversion",
        ])


        for ver in SystemVersion.objects.filter(is_current=True):
            print(ver)
            score = 0

            for field in sorted(version_fields):
                val = getattr(ver, field)
                if field.endswith("_citations"):
                    print(" +", field, "=>", val)
                    score += self.CITATION_REWARD

                elif not val is None and val != '':
                    score += self.FIELD_REWARD
                    print(" +", field)
            # FOR

            for field in sorted(meta_fields):
                val = getattr(ver.meta, field)
                if not val is None and val != '':
                    score += self.FIELD_REWARD
                    print(" +", field)
            # FOR

            print("SCORE:", score)
            break
        # FOR
        return

    pass
