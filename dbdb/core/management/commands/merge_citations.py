from django.core.management import BaseCommand

from dbdb.core.models import CitationUrl
from dbdb.core.utils.citations import merge_citations


class Command(BaseCommand):
    help = "Merge one or more CitationUrls into the first ID given"

    def add_arguments(self, parser):
        parser.add_argument(
            'ids', metavar='ID', type=int, nargs='+',
            help='CitationUrl IDs to merge; the first is the merge target, the rest are merged into it')
        parser.add_argument(
            '--dry-run', action='store_true',
            help='Print what would be merged without making any changes')

    def handle(self, *args, **options):
        ids = options['ids']
        if len(ids) < 2:
            self.stderr.write(self.style.ERROR("At least 2 IDs required (target + one or more sources)"))
            return

        citations = {c.id: c for c in CitationUrl.objects.filter(id__in=ids)}
        missing = [i for i in ids if i not in citations]
        if missing:
            self.stderr.write(self.style.ERROR(f"CitationUrl IDs not found: {missing}"))
            return

        merge_to   = citations[ids[0]]
        merge_from = [citations[i] for i in ids[1:]]

        self.stdout.write(f"Target : [{merge_to.id}] {merge_to.url}")
        for c in merge_from:
            self.stdout.write(f"  Source: [{c.id}] {c.url}")

        if options['dry_run']:
            self.stdout.write("Dry run — no changes made.")
            return

        merge_citations(merge_to, merge_from)
        self.stdout.write(self.style.SUCCESS(
            f"Merged {len(merge_from)} citation(s) into [{merge_to.id}] {merge_to.url}"
        ))
