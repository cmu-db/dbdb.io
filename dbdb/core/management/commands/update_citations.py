from django.core.management.base import BaseCommand, CommandError

from dbdb.core.models import CitationUrl


class Command(BaseCommand):
    help = 'Bulk-update CitationUrl.status matched by ID or URL substring'

    def add_arguments(self, parser):
        parser.add_argument(
            'keyword',
            help='A numeric CitationUrl ID for an exact match, or a string for url__icontains lookup',
        )
        parser.add_argument(
            '--status',
            required=True,
            metavar='STATUS',
            help='New status value: name (e.g. "valid") or integer (e.g. 1). '
                 'Choices: ' + ', '.join(
                     f'{s.value}={s.name.lower()}' for s in CitationUrl.Status
                 ),
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be updated without writing to the database.',
        )

    def _resolve_status(self, raw):
        """Return a CitationUrl.Status member from a name or integer string."""
        # Try integer
        try:
            val = int(raw)
            return CitationUrl.Status(val)
        except (ValueError, KeyError):
            pass
        # Try name (case-insensitive)
        upper = raw.strip().upper()
        for member in CitationUrl.Status:
            if member.name == upper:
                return member
        valid = ', '.join(f'{s.value}/{s.name.lower()}' for s in CitationUrl.Status)
        raise CommandError(f'Unknown status {raw!r}. Valid values: {valid}')

    def handle(self, *args, **options):
        keyword  = options['keyword']
        dry_run  = options['dry_run']

        new_status = self._resolve_status(options['status'])

        # Build queryset: numeric → exact ID, else → url__icontains
        try:
            pk = int(keyword)
            qs = CitationUrl.objects.filter(pk=pk)
            match_desc = f'id={pk}'
        except ValueError:
            qs = CitationUrl.objects.filter(url__icontains=keyword)
            match_desc = f'url__icontains={keyword!r}'

        citations = list(qs.order_by('id'))

        if not citations:
            self.stdout.write(self.style.WARNING(f'No CitationUrls matched {match_desc}.'))
            return

        # Print preview table
        col_id  = max(len('ID'),  max(len(str(c.pk))  for c in citations))
        col_url = max(len('URL'), max(len(c.url)       for c in citations))
        col_old = max(len('Old Status'), max(len(CitationUrl.Status(c.status).name) for c in citations))

        sep = f'+{"-"*(col_id+2)}+{"-"*(col_url+2)}+{"-"*(col_old+2)}+'
        hdr = f'| {"ID":<{col_id}} | {"URL":<{col_url}} | {"Old Status":<{col_old}} |'
        self.stdout.write(sep)
        self.stdout.write(hdr)
        self.stdout.write(sep)
        for c in citations:
            old_name = CitationUrl.Status(c.status).name
            self.stdout.write(f'| {str(c.pk):<{col_id}} | {c.url:<{col_url}} | {old_name:<{col_old}} |')
        self.stdout.write(sep)

        prefix = '[DRY RUN] ' if dry_run else ''
        self.stdout.write(
            f'\n{prefix}{len(citations)} citation(s) matched. '
            f'Status → {new_status.name} ({new_status.value})\n'
        )

        if dry_run:
            return

        updated = qs.update(status=new_status.value)
        self.stdout.write(self.style.SUCCESS(f'Updated {updated} citation(s).'))
