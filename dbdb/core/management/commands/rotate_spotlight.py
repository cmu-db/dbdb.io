"""
rotate_spotlight — rotate the homepage spotlight to the next eligible system.

Picks the system deterministically based on the current ISO week number and the
count of spotlight-eligible systems, so the result is stable if run multiple
times in the same week. The chosen system is never the same as the current one
(when more than one eligible system exists).

Usage:
    python manage.py rotate_spotlight [--dry-run] [--force]
"""
from datetime import date

from django.core.management.base import BaseCommand
from django.db import transaction

from dbdb.core.models import System


class Command(BaseCommand):
    help = 'Rotate the homepage spotlight to the next eligible system'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run', action='store_true',
            help='Show what would change without modifying the database',
        )
        parser.add_argument(
            '--force', action='store_true',
            help='Rotate even if the current system is already the one this week would pick',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        force   = options['force']
        prefix  = '[DRY RUN] ' if dry_run else ''

        eligible = list(System.objects.filter(spotlight_eligible=True).order_by('pk'))
        count    = len(eligible)

        if count == 0:
            self.stdout.write(self.style.WARNING('No spotlight-eligible systems found. Nothing to do.'))
            return

        year, week, _ = date.today().isocalendar()
        seed = year * 53 + week
        idx  = seed % count

        current = System.objects.filter(spotlight_enabled=True).first()
        chosen = eligible[idx]

        self.stdout.write(f'Eligible pool : {count} system{"s" if count != 1 else ""}')
        self.stdout.write(f'Current       : {current.name if current else "(none)"}')

        # Idempotency guard: this week's algorithm would pick the current system —
        # nothing to do unless the caller wants to force a rotation.
        if current is not None and chosen.pk == current.pk:
            if not force:
                self.stdout.write(self.style.SUCCESS('Already showing the correct system for this week. Use --force to rotate anyway.'))
                return
            # --force: advance past current so we actually rotate to a different system
            if count > 1:
                idx = (idx + 1) % count
                chosen = eligible[idx]

        self.stdout.write(f'Selected      : {chosen.name}')

        if dry_run:
            self.stdout.write(f'{prefix}Would set spotlight_enabled=True for: {chosen.name}')
            return

        with transaction.atomic():
            System.objects.update(spotlight_enabled=False)
            System.objects.filter(pk=chosen.pk).update(spotlight_enabled=True)

        self.stdout.write(self.style.SUCCESS('Spotlight updated.'))
