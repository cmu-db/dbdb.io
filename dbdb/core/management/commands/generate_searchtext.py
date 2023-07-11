from django.core.management import BaseCommand

from dbdb.core.models import SystemSearchText
from dbdb.core.models import SystemVersion

class Command(BaseCommand):

    def handle(self, *args, **options):
        SystemSearchText.objects.all().delete()

        for s in SystemVersion.objects.filter(is_current=True).order_by("-id"):
            try:
                sstext = SystemSearchText()
                sstext.system = s.system
                sstext.name = s.system.name
                sstext.search_text = s.generate_searchtext()
                sstext.save()
                print("Created", s.system)
            except:
                print("Failed", s.system)
                raise
    pass
