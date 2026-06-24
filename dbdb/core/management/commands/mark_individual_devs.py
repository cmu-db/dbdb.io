from dbdb.core.management.base import DbdbBaseCommand
from dbdb.core.models import SystemVersion
from dbdb.core.signals import maybe_mark_individual


class Command(DbdbBaseCommand):
    help = 'Mark solo hobby-project developer orgs as Individual where the name looks like a person'

    def handle(self, *args, **options):
        versions = (
            SystemVersion.objects
            .filter(is_current=True,
                    project_types__attribute__slug='project-type',
                    project_types__slug='hobby')
            .prefetch_related('developer_orgs')
            .distinct()
        )

        updated = []
        for version in versions:
            orgs = list(version.developer_orgs.all())
            if len(orgs) != 1:
                continue
            if maybe_mark_individual(orgs[0]):
                updated.append(f"{version.system.name}: {orgs[0].name}")

        if updated:
            self.stdout.write(self.style.SUCCESS(f"Marked {len(updated)} org(s) as Individual:"))
            for entry in updated:
                self.stdout.write(f"  {entry}")
        else:
            self.stdout.write("No orgs updated.")
