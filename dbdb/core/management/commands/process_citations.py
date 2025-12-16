import re
import sys
import time
from pprint import pprint

from django.utils import timezone
from django.core.management import BaseCommand
from requests import ConnectTimeout
from requests.exceptions import ConnectionError, ReadTimeout
from urllib3.exceptions import MaxRetryError, NewConnectionError

from dbdb.core.models import CitationUrl
from dbdb.core.utils.citations import *


class Command(BaseCommand):

    def add_arguments(self, parser):
        parser.add_argument('citation', metavar='C', type=str, nargs='?',
                    help='Citation URL to force process')
        parser.add_argument('--ignore-spam', action='store_true',
                    help="Ignore spam checks")
        parser.add_argument('--only-new', action='store_true',
                    help="Only visit citations that have never been checked before")
        parser.add_argument('--timeout', type=int, default=15,
                    help="How many seconds to wait for each request attempt")
        parser.add_argument('--sleep', type=int, default=5,
                    help="How many seconds to sleep between processing each citation")
        parser.add_argument('--limit', type=int, default=None,
                    help="# of citations to process before exiting")
        return

    def handle(self, *args, **options):

        citations = CitationUrl.objects.all() # filter(is_current=True)
        if options['citation']:
            keyword = options['citation'].strip()
            if keyword.isdigit():
                citations = citations.filter(id=int(keyword))
            else:
                citations = citations.filter(url__icontains=keyword)
        if options['only_new']:
            citations = citations.filter(last_checked=None)

        citation_ctr = 0
        for c in citations.order_by("id"):
            # First get the list of systems that use this citation
            systems = get_systems(c, current_only=False)
            self.stdout.write(f"Citation {c} => {systems}")

            # If no system is using this citation, we may want to delete it
            if len(systems) == 0:
                self.stdout.write(f"Did not find any systems using Citation {c}. Skipping...")
                continue

            # Check if we have a malformed URL that we need to merge
            fixed_url = None
            if not c.url.lower().startswith("http"):
                parts = c.url.split(" ")
                if parts[0].isdigit() and len(parts) > 1: fixed_url = parts[1].strip()
                if parts[0].startswith("ttp:"): fixed_url = 'h' + parts[0]

            parts = re.match(r"(http(.*?))[\s]+Section.*", c.url, re.IGNORECASE)
            if parts:
                fixed_url = parts.group(0)
                print(f"'{c.url} -> {fixed_url}")

            if fixed_url:
                # See if this URL already exists. If yes, then we will merge it
                other_c = CitationUrl.objects.filter(url=fixed_url)
                if other_c.exists():
                    merge_citations(other_c[0], [c])
                    c.delete()
                    continue
                # Otherwise just change this Citation's URL
                else:
                    c.url = fixed_url
                    c.save()
                    continue

            # Check again whether this is a valid URL
            if not c.url.lower().startswith("http"):
                print(f"SKIP: {c}")
                continue

            if citation_ctr > 0 and 'sleep' in options and int(options['sleep']) > 0:
                self.stdout.write(f"Sleeping for {options['sleep']} seconds...")
                time.sleep(int(options['sleep']))

            print(f"{citation_ctr}: Citation: {c}")
            info = None
            try:
                # Just grab the first system to use as a hint
                system_name = systems[0].name

                info = fetch_url_metadata(c.url, system_name=system_name, skip_spamcheck=options["ignore_spam"])
                c.last_status = info["status-code"]
                c.last_contenttype = info["content-type"]
                c.last_contentsize = info["content-length"]
                c.last_cachecontrol = info["cache-control"]
                c.last_etag = info["etag"]
                c.last_modified = info["last-modified"]
                c.dead = info["dead"]

                # Don't overwrite the title if we get a dead page and there is already
                # an existing title
                if not(c.dead and c.last_title):
                    c.last_title = info["title"]

            except (TimeoutError,ConnectTimeout,ReadTimeout,ConnectionError,NewConnectionError) as e:
                self.stdout.write(f"Connection failed: {e}")
                c.dead = True
                pass

            except SpamPageError as e:
                self.stdout.write(f"Spam page error: {e}")
                pass

            except:
                self.stdout.write(f"Failed: {c}")
                c.dead = True
                raise
            finally:
                c.last_checked = timezone.now()
                c.save()
                print(f"Result: ")
                pprint(info)
                print()

            citation_ctr += 1
            if 'limit' in options and options['limit']:
                if citation_ctr >= options['limit']: break
    pass
