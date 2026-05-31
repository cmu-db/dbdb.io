from django.core.management import BaseCommand

from dbdb.core.models import Organization
from dbdb.core.utils.organizations import merge_organizations


class Command(BaseCommand):
    help = "Merge one or more Organizations into the first ID given"

    def add_arguments(self, parser):
        parser.add_argument(
            'ids', metavar='ID', type=int, nargs='+',
            help='Organization IDs to merge; the first is the merge target, the rest are merged into it')
        parser.add_argument(
            '--dry-run', action='store_true',
            help='Print what would be merged without making any changes')

    def handle(self, *args, **options):
        ids = options['ids']
        if len(ids) < 2:
            self.stderr.write(self.style.ERROR("At least 2 IDs required (target + one or more sources)"))
            return

        orgs = {o.id: o for o in Organization.objects.filter(id__in=ids)}
        missing = [i for i in ids if i not in orgs]
        if missing:
            self.stderr.write(self.style.ERROR(f"Organization IDs not found: {missing}"))
            return

        merge_to   = orgs[ids[0]]
        merge_from = [orgs[i] for i in ids[1:]]

        self.stdout.write(f"Target : [{merge_to.id}] {merge_to.name}")
        for o in merge_from:
            self.stdout.write(f"  Source: [{o.id}] {o.name}")

        if options['dry_run']:
            self.stdout.write("Dry run — no changes made.")
            return

        merge_organizations(merge_to, merge_from)
        self.stdout.write(self.style.SUCCESS(
            f"Merged {len(merge_from)} organization(s) into [{merge_to.id}] {merge_to.name}"
        ))
