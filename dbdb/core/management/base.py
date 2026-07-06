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


class EnricherBaseCommand(DbdbBaseCommand):
    """
    Base class for LLM-enrichment management commands.

    Adds the shared enricher arguments (--dry-run, --fields, --model,
    --enricher, --include-urls, --recrawl-after) so subclasses only need to
    declare their entity-specific positional arguments.
    """

    def add_arguments(self, parser):
        super().add_arguments(parser)
        from dbdb.core.utils.enrichment import BaseEnricher
        enricher_choices = sorted(BaseEnricher._get_registry())
        parser.add_argument('keywords', nargs='*', metavar='KEYWORD',
                            help='One or more slugs or name keywords to match')
        parser.add_argument('--dry-run', action='store_true',
                            help='Show what would be filled without saving')
        parser.add_argument('--fields', default=None,
                            help='Comma-separated list of field names to target')
        parser.add_argument('--model', default=None,
                            help='Override LLM model name')
        parser.add_argument('--enricher', required=False, default=None, choices=enricher_choices,
                            metavar='ENRICHER',
                            help=f'LLM backend to use: {", ".join(enricher_choices)}')
        parser.add_argument('--include-urls', action='store_true',
                            help="Crawl the target's existing URLs and pass page text to the LLM")
        parser.add_argument('--recrawl-after', type=int, default=7, metavar='DAYS',
                            help='Re-fetch a URL only if cached content is older than N days (default: 7)')
        parser.add_argument('--skip-field', action='append', default=[], metavar='FIELD',
                            help='Exclude a field from enrichment (may be repeated)')
        parser.add_argument('--skip-spamcheck', action='store_true',
                            help='Disable spam checking when retrieving URLs')
        parser.add_argument('--skip-errors', action='store_true',
                            help='Print errors from individual enrichments and continue instead of stopping')
        parser.add_argument('--limit', type=int, default=None, metavar='N',
                            help='Stop after successfully enriching N entries')
        parser.add_argument(
            '--mode',
            choices=['enrich', 'extract-urls', 'both'],
            default='enrich',
            help=(
                "'enrich' (default): LLM fills missing fields from search/crawl. "
                "'extract-urls': LLM scans the target's homepage HTML for specific missing URLs. "
                "'both': run both modes (Systems will create only one pending version)."
            ),
        )
