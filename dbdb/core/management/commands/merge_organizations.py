from dbdb.core.management.base import DbdbBaseCommand
from dbdb.core.models import Organization
from dbdb.core.utils.organizations import find_potential_matches, merge_organizations


class Command(DbdbBaseCommand):
    help = "Merge one or more Organizations into the first ID given, or find potential duplicates"

    def add_arguments(self, parser):
        super().add_arguments(parser)
        parser.add_argument(
            'ids', metavar='ID', type=int, nargs='*',
            help='Organization IDs to merge; the first is the merge target, the rest are merged into it')
        parser.add_argument(
            '--dry-run', action='store_true',
            help='Print what would be merged without making any changes')
        parser.add_argument(
            '--find-matches', metavar='ID', type=int, dest='find_matches',
            help='Find potential duplicate organizations for the given ID')
        parser.add_argument(
            '--find-all', action="store_true",
            help='Exhaustive search for all potential duplicate organizations')

    def handle(self, *args, **options):
        if options['find_all']:
            for o in Organization.objects.all():
                result = self._find_matches(o.id, ignore_nomatch=True)
                if result:
                    self.stdout.write("="*100)
            return None

        if options['find_matches']:
            return self._find_matches(options['find_matches'])

        ids = options['ids']
        if len(ids) < 2:
            self.stderr.write(self.style.ERROR(
                "At least 2 IDs required (target + one or more sources), "
                "or use --find-matches ID to search for duplicates"
            ))
            return False

        orgs = {o.id: o for o in Organization.objects.filter(id__in=ids)}
        missing = [i for i in ids if i not in orgs]
        if missing:
            self.stderr.write(self.style.ERROR(f"Organization IDs not found: {missing}"))
            return None

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

    def _find_matches(self, org_id: int, ignore_nomatch:bool=False) -> bool:
        try:
            org = Organization.objects.get(id=org_id)
        except Organization.DoesNotExist:
            self.stderr.write(self.style.ERROR(f"Organization ID {org_id} not found"))
            return False

        matches = find_potential_matches(org)
        if not matches:
            if not ignore_nomatch:
                self.stdout.write(f"No potential matches found for [{org.id}] {org.name}")
            return False

        self.stdout.write(f"Potential matches for [{org.id}] {org.name}:\n")
        self.stdout.write(f"  {'ID':>5}  {'Name':<50}  Reason")
        self.stdout.write(f"  {'-'*5}  {'-'*50}  {'-'*20}")
        for other, reason in matches:
            self.stdout.write(f"  {other.id:>5}  {other.name:<50}  {reason}")
        return True
