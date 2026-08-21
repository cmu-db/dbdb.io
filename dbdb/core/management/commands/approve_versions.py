import logging

from django.contrib.auth import get_user_model
from django.core.management.base import CommandError
from django.db import transaction
from django.utils import timezone

from dbdb.core.management.base import DbdbBaseCommand
from dbdb.core.models import System, SystemVersion
from dbdb.core.utils.versions import finalize_new_version

LOG = logging.getLogger(__name__)
UserModel = get_user_model()


class Command(DbdbBaseCommand):
    help = 'Approve the pending SystemVersion for one or more systems'

    def add_arguments(self, parser):
        super().add_arguments(parser)
        parser.add_argument(
            'slugs', nargs='+', metavar='SLUG',
            help='One or more System slugs whose pending version should be approved',
        )
        parser.add_argument(
            '--dry-run', action='store_true',
            help='Show what would be approved without saving',
        )
        parser.add_argument(
            '--creator', metavar='USERNAME', default=None,
            help='Set SystemVersion.creator to this user (default: keep existing creator)',
        )
        parser.add_argument(
            '--latest-timestamp', action='store_true',
            help='Update SystemVersion.created to the current timestamp after approval',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        latest_timestamp = options['latest_timestamp']
        slugs = options['slugs']

        creator_user = None
        if options['creator']:
            try:
                creator_user = UserModel.objects.get(username=options['creator'])
            except UserModel.DoesNotExist:
                raise CommandError(f"User '{options['creator']}' not found")

        for slug in slugs:
            try:
                system = System.objects.get(slug=slug)
            except System.DoesNotExist:
                LOG.warning("System '%s' not found, skipping", slug)
                continue

            pending = system.pending_version()
            if pending is None:
                LOG.info("System '%s' has no pending version, skipping", slug)
                continue

            LOG.info(
                "System '%s': pending ver %d by '%s'",
                slug, pending.ver, pending.creator.username,
            )

            if dry_run:
                self.stdout.write(
                    f"[DRY RUN] Would approve '{slug}' ver {pending.ver}"
                    + (f" (creator → {creator_user.username})" if creator_user else "")
                    + (" (timestamp → now)" if latest_timestamp else "")
                )
                continue

            with transaction.atomic():
                system.versions.update(is_current=False)
                pending.approved = True
                pending.is_current = True
                if creator_user:
                    pending.creator = creator_user
                pending.save()
                if latest_timestamp:
                    SystemVersion.objects.filter(pk=pending.pk).update(created=timezone.now())
                system.ver = pending.ver
                system.modified = timezone.now()
                system.save()
                finalize_new_version(pending)

            LOG.info("Approved '%s' ver %d", slug, pending.ver)
