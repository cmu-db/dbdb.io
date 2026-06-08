import logging
import re
import sys
import time
from argparse import ArgumentParser
from pprint import pformat

from django.core.management import CommandError
from django.db.models import Q
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from requests import ConnectTimeout
from requests.exceptions import ConnectionError, InvalidURL, ReadTimeout
from urllib3.exceptions import NewConnectionError, ReadTimeoutError

from dbdb.core.models import CitationUrl, CitationUrlContent
from dbdb.core.utils.citations import *
from dbdb.core.management.base import DbdbBaseCommand

LOG = logging.getLogger(__name__)


def _check_if_exists(c:CitationUrl, url:str) -> CitationUrl|None:
    # Also check the slash-toggled variant so that
    # "https://example.com/path/" and "…/path" are treated as the same URL.
    alt_url = url[:-1] if url.endswith('/') else url + '/'
    other_c = (CitationUrl.objects
               .filter(Q(url=url) | Q(url=alt_url))
               .exclude(pk=c.pk)
               .first())
    return other_c

class Command(DbdbBaseCommand):

    def add_arguments(self, parser: ArgumentParser):
        super().add_arguments(parser)
        status_choices = [s.name.lower() for s in CitationUrl.Status]

        parser.add_argument('citation', metavar='C', type=str, nargs='*',
                    help='One or more citation IDs or URL keywords to process')
        parser.add_argument('--skip-spam', action='store_true',
                    help="Skip spam checks")
        parser.add_argument('--normalize', action='store_true',
                    help="Normalize URLs to avoid duplicates")
        parser.add_argument('--only-new', action='store_true',
                    help="Only visit citations that have never been checked before")
        parser.add_argument("--last-checked", metavar='YYYY-MM-DD', required=False, type=parse_datetime,
                    help="Process URLs there were checked before date",)
        parser.add_argument('--timeout', type=int, default=15,
                    help="How many seconds to wait for each request attempt")
        parser.add_argument('--sleep', type=int, default=5,
                    help="How many seconds to sleep between processing each citation")
        parser.add_argument('--limit', type=int, default=None,
                    help="# of citations to process before exiting")
        parser.add_argument('--statuscode', type=int, default=None, metavar='N',
                    help="Only process citations with HTTP last_statuscode=N (e.g. 404)")
        parser.add_argument('--ignore', metavar='KEYWORD', action='append', default=[],
                    help="Skip any URL containing this keyword (repeatable: --ignore foo --ignore bar)")
        parser.add_argument('--dry-run', action='store_true',
                    help="Print what would be changed without writing to the database")

        agroup = parser.add_argument_group('URL Overrides')
        agroup.add_argument('--set-status', metavar='STATUS', default=None,
                    choices=status_choices,
                    help=f"Directly set CitationUrl.status without fetching. "
                         f"Choices: {', '.join(status_choices)}")
        agroup.add_argument('--set-title', metavar='TITLE', default=None,
                    help="Directly set CitationUrl.last_title without fetching")

        agroup = parser.add_argument_group('URL rewriting')
        agroup.add_argument('--replace-from', metavar='OLD', default=None,
                    help="Substring to find in CitationUrl.url (required with --replace-to)")
        agroup.add_argument('--replace-to', metavar='NEW', default=None,
                    help="Replacement string for --replace-from (required with --replace-from)")
        return

    def handle(self, *args, **options):

        citations = CitationUrl.objects.filter(url__startswith="http")
        if options['citation']:
            q = Q()
            for term in options['citation']:
                term = term.strip()
                if term.isdigit():
                    q |= Q(id=int(term))
                else:
                    q |= Q(url__icontains=term)
            citations = citations.filter(q)
        if options['only_new']:
            citations = citations.filter(last_checked=None)
        if options['last_checked']:
            LOG.info(f"Processing URLs last checked before {options['last_checked']}")
            citations = citations.filter(last_checked__lte=options['last_checked'])
        if options['statuscode'] is not None:
            LOG.info(f"Processing URLs with last_statuscode={options['statuscode']}")
            citations = citations.filter(last_statuscode=options['statuscode'])
        for keyword in options['ignore']:
            LOG.info(f"Ignoring URLs containing: {keyword!r}")
            citations = citations.exclude(url__icontains=keyword)

        set_status = options['set_status']
        set_title = options['set_title']
        dry_run = options['dry_run']
        replace_from = options['replace_from']
        replace_to = options['replace_to']

        if (replace_from is None) != (replace_to is None):
            raise CommandError("--replace-from and --replace-to must be used together")

        if replace_from is not None:
            rewrite_citations = citations.filter(url__contains=replace_from).order_by('id')
            replaced = merged = 0
            for c in rewrite_citations:
                new_url = c.url.replace(replace_from, replace_to)
                LOG.debug(f"{'[dry-run] ' if dry_run else ''}#{c.id}  {c.url}  ->  {new_url}")
                if not dry_run:
                    other_c = _check_if_exists(c, new_url)
                    if other_c:
                        LOG.debug(f"  merging into existing #{other_c.id}")
                        merge_citations(other_c, [c])
                        c.delete()
                        merged += 1
                    else:
                        c.url = new_url
                        c.save(update_fields=['url'])
                        replaced += 1
            if dry_run:
                count = rewrite_citations.count()
                LOG.debug(f"[dry-run] Would rewrite {count} citation(s): {replace_from!r} -> {replace_to!r}")
            else:
                LOG.debug(
                    f"Rewrote {replaced} citation(s), merged {merged} duplicate(s): "
                    f"{replace_from!r} -> {replace_to!r}"
                )
            return
        if set_status is not None or set_title is not None:
            update_fields = {}
            if set_status is not None:
                update_fields['status'] = CitationUrl.Status[set_status.upper()]
            if set_title is not None:
                max_title = CitationUrl._meta.get_field('last_title').max_length
                update_fields['last_title'] = set_title[:max_title]
            for c in citations.order_by('id'):
                prefix = "[dry-run] " if dry_run else ""
                LOG.debug(f"{prefix}#{c.id}  {c.url}")
            if dry_run:
                count = citations.count()
                self.stdout.write(f"[dry-run] Would update {count} citation(s): {update_fields}")
            else:
                count = citations.update(**update_fields)
                self.stdout.write(self.style.SUCCESS(f"Updated {count} citation(s): {update_fields}"))
            return

        citation_ctr = 0
        max_title = CitationUrl._meta.get_field('last_title').max_length
        for c in citations.order_by("id"):
            citation_ctr += 1
            if 'limit' in options and options['limit']:
                if citation_ctr >= options['limit']: break

            prefix = "[dry-run] " if dry_run else ""
            LOG.debug(f"{prefix}#{c.id}  {c.url}")

            # Check if we have a malformed URL that we need to cleanup + merge
            if not c.url.lower().startswith("http"):
                parts = c.url.split(" ")
                if parts[0].isdigit() and len(parts) > 1: c.url = parts[1].strip()
                if parts[0].startswith("ttp:"): c.url = 'h' + parts[0]
            parts = re.match(r"(http(.*?))[\s]+Section.*", c.url, re.IGNORECASE)
            if parts:
                c.url = parts.group(0)

            if options['normalize']:
                orig_url = c.url
                c.url = normalize_url(orig_url)
                if orig_url != c.url:
                    LOG.info(f"NORMALIZE: {orig_url} -> {c.url}")

            # See if this URL already exists. If yes, then we will merge it
            other_c = _check_if_exists(c, c.url)
            if other_c is not None:
                merge_citations(other_c, [c])
                c.delete()
                continue

            # Check again whether this is a valid URL
            if not c.url.lower().startswith("http"):
                LOG.info(f"SKIP: {c}")
                continue

            # First get the list of systems that use this citation
            systems = get_systems(c, current_only=False)

            # If no system is using this citation, we may want to delete it
            if len(systems) == 0:
                LOG.info(f"Did not find any systems using Citation {c}. Skipping...")
                continue

            LOG.info(f"Citation {c} => {systems}")

            if citation_ctr > 1 and 'sleep' in options and int(options['sleep']) > 0:
                LOG.info(f"Sleeping for {options['sleep']} seconds...")
                time.sleep(int(options['sleep']))

            info = None
            try:
                # Just grab the first system to use as a hint
                info = fetch_url_metadata(
                    c.url,
                    system=systems[0],
                    citation_url=c,
                    skip_spamcheck=options["skip_spam"],
                    allow_redirects=False
                )
                c.status = info["status"]
                c.last_statuscode = info["status-code"]
                c.last_contenttype = info["content-type"]
                c.last_contentsize = info["content-length"]
                c.last_cachecontrol = info["cache-control"]
                c.last_etag = info["etag"]
                c.last_modified = info["last-modified"]

                # Check if we need to update the URL
                if "url" in info and c.url != info["url"]:
                    new_url = info["url"]
                    other_c = _check_if_exists(c, new_url)
                    if other_c:
                        merge_citations(other_c, [c])
                        c.delete()
                        continue
                    else:
                        c.url = new_url

                # Don't overwrite the title if we get a dead page and there is already
                # an existing title
                if not(c.status == CitationUrl.Status.DEAD and c.last_title):
                    c.last_title = info["title"]
                    if c.last_title and len(c.last_title) > max_title:
                        c.last_title = c.last_title[:max_title]

            except KeyboardInterrupt:
                sys.exit(0)

            except (TimeoutError,ReadTimeoutError,ConnectTimeout,ReadTimeout,ConnectionError,NewConnectionError) as e:
                LOG.warning(f"Connection failed: {e}")
                c.status = CitationUrl.Status.DEAD
                pass

            except InvalidURL as e:
                LOG.warning(f"Invalid URL: {e}")
                c.status = CitationUrl.Status.IGNORE
                pass

            except:
                LOG.error(f"Failed: {c}")
                c.status = CitationUrl.Status.DEAD
                raise
            finally:
                c.last_checked = timezone.now()
                if dry_run:
                    LOG.info(f"[dry-run] Would save: status={c.get_status_display()} title={c.last_title!r}")
                else:
                    c.save()
                try:
                    raw_bytes = len(c.content.raw.encode('utf-8'))
                    content_info = f"content={raw_bytes:,}b"
                except CitationUrlContent.DoesNotExist:
                    content_info = "no content"
                LOG.info(f"Result: status={c.get_status_display()} {content_info}")
                if info: LOG.debug(pformat(info))
    pass
