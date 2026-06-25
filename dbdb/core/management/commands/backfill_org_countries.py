from dbdb.core.management.base import DbdbBaseCommand

from dbdb.core.models import SystemVersion


class Command(DbdbBaseCommand):
    help = (
        'For each current SystemVersion with exactly one developer org and one country, '
        'copy that country to the org if the org has no countries set.'
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Print what would be changed without saving.',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']

        updated = 0
        skipped_has_country = 0

        for sv in (SystemVersion.objects
                   .filter(is_current=True)
                   .prefetch_related('developer_orgs')
                   .select_related('system')):

            orgs = list(sv.developer_orgs.all())
            if len(orgs) != 1:
                continue

            sv_countries = [c for c in str(sv.countries).split(',') if c.strip()]
            if len(sv_countries) != 1:
                continue

            org = orgs[0]
            org_countries = [c for c in str(org.countries or '').split(',') if c.strip()]

            if org_countries:
                skipped_has_country += 1
                continue

            if dry_run:
                self.stdout.write(
                    f'[DRY RUN] Would set {org.name} ({sv.system.name}) -> {sv_countries[0]}'
                )
            else:
                org.countries = sv.countries
                org.save(update_fields=['countries'])
                self.stdout.write(
                    self.style.SUCCESS(f'Updated {org.name} ({sv.system.name}) -> {sv_countries[0]}')
                )

            updated += 1

        action = 'Would update' if dry_run else 'Updated'
        self.stdout.write(f'\n{action} {updated} organization(s).')
        self.stdout.write(f'Skipped {skipped_has_country} org(s) that already had a country set.')
