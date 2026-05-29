from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from dbdb.core.models import Feature, FeatureOption, SystemFeature


class Command(BaseCommand):
    help = 'Replace "Object-Relational" with "Relational" in the Data Model feature across all SystemVersions'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Print what would be done without writing to the database.',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        if dry_run:
            self.stdout.write(self.style.WARNING('DRY RUN — no changes will be written.\n'))

        try:
            feature = Feature.objects.get(slug='data-model')
        except Feature.DoesNotExist:
            raise CommandError('Feature with slug "data-model" not found.')

        try:
            old_opt = FeatureOption.objects.get(feature=feature, value='Object-Relational')
        except FeatureOption.DoesNotExist:
            raise CommandError('FeatureOption "Object-Relational" not found for feature "Data Model".')

        try:
            new_opt = FeatureOption.objects.get(feature=feature, value='Relational')
        except FeatureOption.DoesNotExist:
            raise CommandError('FeatureOption "Relational" not found for feature "Data Model".')

        affected = SystemFeature.objects.filter(options=old_opt).select_related(
            'version__system'
        )
        count = affected.count()
        self.stdout.write(f'Found {count} SystemFeature record(s) with "Object-Relational".')

        updated = 0
        with transaction.atomic():
            for sf in affected:
                self.stdout.write(
                    f'  {sf.version.system.name} (v{sf.version.ver}): Object-Relational → Relational'
                )
                if not dry_run:
                    sf.options.remove(old_opt)
                    sf.options.add(new_opt)
                    updated += 1

            if dry_run:
                transaction.set_rollback(True)

        if dry_run:
            self.stdout.write(self.style.WARNING(
                f'\nDry run complete. {count} record(s) would be updated.'
            ))
        else:
            self.stdout.write(self.style.SUCCESS(
                f'\nDone. {updated} SystemFeature record(s) updated.'
            ))
