import logging

from django.core.management.base import BaseCommand

LOG = logging.getLogger(__name__)


class DbdbBaseCommand(BaseCommand):
    """
    Base class for all DBDB management commands.

    Adds a --debug flag that, when set, switches the 'dbdb' root logger to
    DEBUG level before handle() runs.  Every LOG.debug() call in every
    dbdb.* module then emits automatically — no per-command wiring needed.
    """

    def add_arguments(self, parser):
        super().add_arguments(parser)
        parser.add_argument(
            '--debug', action='store_true',
            help='Enable DEBUG-level logging for all dbdb modules',
        )

    def execute(self, *args, **options):
        if options.get('debug'):
            logging.getLogger('dbdb').setLevel(logging.DEBUG)
            LOG.debug("Debug logging enabled")
        return super().execute(*args, **options)
