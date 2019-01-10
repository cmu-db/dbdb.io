# stdlib imports
# django imports
from django.core.management import BaseCommand
# third-party imports
from haystack.inputs import AutoQuery
from haystack.query import SearchQuerySet


class Command(BaseCommand):

    def add_arguments(self, parser):
        parser.add_argument('query', nargs='*')
        return

    def handle(self, *args, **options):
        queries = (
            'VoltDB',
            'voltdb',
            'volt',
            'pavlo',
            'Stonebraker',
            'stonebraker',
            'stormdb',
            'storm',
        )

        if options['query']:
            queries = options['query']

        for query in queries:
            print( 'Searching for: %r' % query )

            sqs = SearchQuerySet()
            sqs = sqs.filter(content=AutoQuery(query))
            sqs = list(sqs)

            for i,item in enumerate(sqs):
                print( '% 2d)' % (i+1), item.name )
            
            if not sqs:
                print( ' NO RESULTS' )
            
            print()
            pass
        return

    pass
