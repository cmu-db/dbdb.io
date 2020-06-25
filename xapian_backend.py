from __future__ import unicode_literals

import datetime
import pickle
import os
import re
import shutil
import sys

import six
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.utils.encoding import force_text

from haystack import connections
from haystack.backends import BaseEngine, BaseSearchBackend, BaseSearchQuery, SearchNode, log_query
from haystack.constants import ID, DJANGO_ID, DJANGO_CT, DEFAULT_OPERATOR
from haystack.exceptions import HaystackError, MissingDependency
from haystack.inputs import AutoQuery
from haystack.models import SearchResult
from haystack.utils import get_identifier, get_model_ct

NGRAM_MIN_LENGTH = 2
NGRAM_MAX_LENGTH = 15

try:
    import xapian
except ImportError:
    raise MissingDependency("The 'xapian' backend requires the installation of 'Xapian'. "
                            "Please refer to the documentation.")

if sys.version_info[0] == 2:
    DirectoryExistsException = OSError
elif sys.version_info[0] == 3:
    DirectoryExistsException = FileExistsError


class NotSupportedError(Exception):
    """
    When the installed version of Xapian doesn't support something and we have
    the old implementation.
    """
    pass

# this maps the different reserved fields to prefixes used to
# create the database:
# id str: unique document id.
# django_id int: id of the django model instance.
# django_ct str: of the content type of the django model.
# field str: name of the field of the index.
TERM_PREFIXES = {
    ID: 'Q',
    DJANGO_ID: 'QQ',
    DJANGO_CT: 'CONTENTTYPE',
    'field': 'X'
}

MEMORY_DB_NAME = ':memory:'

DEFAULT_XAPIAN_FLAGS = (
    xapian.QueryParser.FLAG_PHRASE |
    xapian.QueryParser.FLAG_BOOLEAN |
    xapian.QueryParser.FLAG_LOVEHATE |
    xapian.QueryParser.FLAG_WILDCARD |
    xapian.QueryParser.FLAG_PURE_NOT
)

# Mapping from `HAYSTACK_DEFAULT_OPERATOR` to Xapian operators
XAPIAN_OPTS = {'AND': xapian.Query.OP_AND,
               'OR': xapian.Query.OP_OR,
               'PHRASE': xapian.Query.OP_PHRASE,
               'NEAR': xapian.Query.OP_NEAR
               }

# number of documents checked by default when building facets
# this must be improved to be relative to the total number of docs.
DEFAULT_CHECK_AT_LEAST = 1000

# field types accepted to be serialized as values in Xapian
FIELD_TYPES = {'text', 'integer', 'date', 'datetime', 'float', 'boolean',
    'edge_ngram', 'ngram'}

# defines the format used to store types in Xapian
# this format ensures datetimes are sorted correctly
DATETIME_FORMAT = '%Y%m%d%H%M%S'
INTEGER_FORMAT = '%012d'

# defines the distance given between
# texts with positional information
TERMPOS_DISTANCE = 100

class InvalidIndexError(HaystackError):
    """Raised when an index can not be opened."""
    pass


class XHValueRangeProcessor(xapian.ValueRangeProcessor):
    """
    A Processor to construct ranges of values
    """
    def __init__(self, backend):
        self.backend = backend
        xapian.ValueRangeProcessor.__init__(self)

    def __call__(self, begin, end):
        """
        Construct a tuple for value range processing.
        `begin` -- a string in the format '<field_name>:[low_range]'
        If 'low_range' is omitted, assume the smallest possible value.
        `end` -- a string in the the format '[high_range|*]'. If '*', assume
        the highest possible value.
        Return a tuple of three strings: (column, low, high)
        """
        colon = begin.find(':')
        field_name = begin[:colon]
        begin = begin[colon + 1:len(begin)]
        for field_dict in self.backend.schema:
            if field_dict['field_name'] == field_name:
                field_type = field_dict['type']

                if not begin:
                    if field_type == 'text':
                        begin = 'a'  # TODO: A better way of getting a min text value?
                    elif field_type == 'integer':
                        begin = -sys.maxsize - 1
                    elif field_type == 'float':
                        begin = float('-inf')
                    elif field_type == 'date' or field_type == 'datetime':
                        begin = '00010101000000'
                elif end == '*':
                    if field_type == 'text':
                        end = 'z' * 100  # TODO: A better way of getting a max text value?
                    elif field_type == 'integer':
                        end = sys.maxsize
                    elif field_type == 'float':
                        end = float('inf')
                    elif field_type == 'date' or field_type == 'datetime':
                        end = '99990101000000'

                if field_type == 'float':
                    begin = _term_to_xapian_value(float(begin), field_type)
                    end = _term_to_xapian_value(float(end), field_type)
                elif field_type == 'integer':
                    begin = _term_to_xapian_value(int(begin), field_type)
                    end = _term_to_xapian_value(int(end), field_type)
                return field_dict['column'], str(begin), str(end)


class XHExpandDecider(xapian.ExpandDecider):
    def __call__(self, term):
        """
        Return True if the term should be used for expanding the search
        query, False otherwise.

        Ignore terms related with the content type of objects.
        """
        if term.decode('utf-8').startswith(TERM_PREFIXES[DJANGO_CT]):
            return False
        return True


class XapianSearchBackend(BaseSearchBackend):
    """
    `SearchBackend` defines the Xapian search backend for use with the Haystack
    API for Django search.

    It uses the Xapian Python bindings to interface with Xapian, and as
    such is subject to this bug: <http://trac.xapian.org/ticket/364> when
    Django is running with mod_python or mod_wsgi under Apache.

    Until this issue has been fixed by Xapian, it is neccessary to set
    `WSGIApplicationGroup to %{GLOBAL}` when using mod_wsgi, or
    `PythonInterpreter main_interpreter` when using mod_python.

    In order to use this backend, `PATH` must be included in the
    `connection_options`.  This should point to a location where you would your
    indexes to reside.
    """
    inmemory_db = None

    def __init__(self, connection_alias, **connection_options):
        """
        Instantiates an instance of `SearchBackend`.

        Optional arguments:
            `connection_alias` -- The name of the connection
            `language` -- The stemming language (default = 'english')
            `**connection_options` -- The various options needed to setup
              the backend.

        Also sets the stemming language to be used to `language`.
        """
        super(XapianSearchBackend, self).__init__(connection_alias, **connection_options)

        if not 'PATH' in connection_options:
            raise ImproperlyConfigured("You must specify a 'PATH' in your settings for connection '%s'."
                                       % connection_alias)

        self.path = connection_options.get('PATH')

        if self.path != MEMORY_DB_NAME:
            try:
                os.makedirs(self.path)
            except DirectoryExistsException:
                pass

        self.flags = connection_options.get('FLAGS', DEFAULT_XAPIAN_FLAGS)
        self.language = getattr(settings, 'HAYSTACK_XAPIAN_LANGUAGE', 'english')

        stemming_strategy_string = getattr(settings, 'HAYSTACK_XAPIAN_STEMMING_STRATEGY', 'STEM_SOME')
        self.stemming_strategy = getattr(xapian.QueryParser, stemming_strategy_string, xapian.QueryParser.STEM_SOME)

        # these 4 attributes are caches populated in `build_schema`
        # they are checked in `_update_cache`
        # use property to retrieve them
        self._fields = {}
        self._schema = []
        self._content_field_name = None
        self._columns = {}

    def _update_cache(self):
        """
        To avoid build_schema every time, we cache
        some values: they only change when a SearchIndex
        changes, which typically restarts the Python.
        """
        fields = connections[self.connection_alias].get_unified_index().all_searchfields()
        if self._fields != fields:
            self._fields = fields
            self._content_field_name, self._schema = self.build_schema(self._fields)

    @property
    def schema(self):
        self._update_cache()
        return self._schema

    @property
    def content_field_name(self):
        self._update_cache()
        return self._content_field_name

    @property
    def column(self):
        """
        Returns the column in the database of a given field name.
        """
        self._update_cache()
        return self._columns

    def update(self, index, iterable, commit=True):
        """
        Updates the `index` with any objects in `iterable` by adding/updating
        the database as needed.

        Required arguments:
            `index` -- The `SearchIndex` to process
            `iterable` -- An iterable of model instances to index
        Optional arguments:
            `commit` -- ignored

        For each object in `iterable`, a document is created containing all
        of the terms extracted from `index.full_prepare(obj)` with field prefixes,
        and 'as-is' as needed.  Also, if the field type is 'text' it will be
        stemmed and stored with the 'Z' prefix as well.

        eg. `content:Testing` ==> `testing, Ztest, ZXCONTENTtest, XCONTENTtest`

        Each document also contains an extra term in the format:

        `XCONTENTTYPE<app_name>.<model_name>`

        As well as a unique identifier in the the format:

        `Q<app_name>.<model_name>.<pk>`

        eg.: foo.bar (pk=1) ==> `Qfoo.bar.1`, `XCONTENTTYPEfoo.bar`

        This is useful for querying for a specific document corresponding to
        a model instance.

        The document also contains a pickled version of the object itself and
        the document ID in the document data field.

        Finally, we also store field values to be used for sorting data.  We
        store these in the document value slots (position zero is reserver
        for the document ID).  All values are stored as unicode strings with
        conversion of float, int, double, values being done by Xapian itself
        through the use of the :method:xapian.sortable_serialise method.
        """
        database = self._database(writable=True)

        try:
            term_generator = xapian.TermGenerator()
            term_generator.set_database(database)
            term_generator.set_stemmer(xapian.Stem(self.language))
            try:
                term_generator.set_stemming_strategy(self.stemming_strategy)
            except AttributeError:  
                # Versions before Xapian 1.2.11 do not support stemming strategies for TermGenerator
                pass
            if self.include_spelling is True:
                term_generator.set_flags(xapian.TermGenerator.FLAG_SPELLING)

            def _add_text(termpos, text, weight, prefix=''):
                """
                indexes text appending 2 extra terms
                to identify beginning and ending of the text.
                """
                term_generator.set_termpos(termpos)

                start_term = '%s^' % prefix
                end_term = '%s$' % prefix
                # add begin
                document.add_posting(start_term, termpos, weight)
                # add text
                term_generator.index_text(text, weight, prefix)
                termpos = term_generator.get_termpos()
                # add ending
                termpos += 1
                document.add_posting(end_term, termpos, weight)

                # increase termpos
                term_generator.set_termpos(termpos)
                term_generator.increase_termpos(TERMPOS_DISTANCE)

                return term_generator.get_termpos()

            def _add_literal_text(termpos, text, weight, prefix=''):
                """
                Adds sentence to the document with positional information
                but without processing.

                The sentence is bounded by "^" "$" to allow exact matches.
                """
                text = '^ %s $' % text
                for word in text.split():
                    term = '%s%s' % (prefix, word)
                    document.add_posting(term, termpos, weight)
                    termpos += 1
                termpos += TERMPOS_DISTANCE
                return termpos

            def add_text(termpos, prefix, text, weight):
                """
                Adds text to the document with positional information
                and processing (e.g. stemming).
                """
                termpos = _add_text(termpos, text, weight, prefix=prefix)
                termpos = _add_text(termpos, text, weight, prefix='')
                termpos = _add_literal_text(termpos, text, weight, prefix=prefix)
                termpos = _add_literal_text(termpos, text, weight, prefix='')
                return termpos

            def _get_ngram_lengths(value):
                values = value.split()
                for item in values:
                    for ngram_length in six.moves.range(NGRAM_MIN_LENGTH, NGRAM_MAX_LENGTH + 1):
                        yield item, ngram_length

            for obj in iterable:
                document = xapian.Document()
                term_generator.set_document(document)

                def ngram_terms(value):
                    for item, length in _get_ngram_lengths(value):
                        item_length = len(item)
                        for start in six.moves.range(0, item_length - length + 1):
                            for size in six.moves.range(length, length + 1):
                                end = start + size
                                if end > item_length:
                                    continue
                                yield _to_xapian_term(item[start:end])

                def edge_ngram_terms(value):
                    for item, length in _get_ngram_lengths(value):
                        yield _to_xapian_term(item[0:length])

                def add_edge_ngram_to_document(prefix, value, weight):
                    """
                    Splits the term in ngrams and adds each ngram to the index.
                    The minimum and maximum size of the ngram is respectively
                    NGRAM_MIN_LENGTH and NGRAM_MAX_LENGTH.
                    """
                    for term in edge_ngram_terms(value):
                        document.add_term(term, weight)
                        document.add_term(prefix + term, weight)

                def add_ngram_to_document(prefix, value, weight):
                    """
                    Splits the term in ngrams and adds each ngram to the index.
                    The minimum and maximum size of the ngram is respectively
                    NGRAM_MIN_LENGTH and NGRAM_MAX_LENGTH.
                    """
                    for term in ngram_terms(value):
                        document.add_term(term, weight)
                        document.add_term(prefix + term, weight)

                def add_non_text_to_document(prefix, term, weight):
                    """
                    Adds term to the document without positional information
                    and without processing.

                    If the term is alone, also adds it as "^<term>$"
                    to allow exact matches on single terms.
                    """
                    document.add_term(term, weight)
                    document.add_term(prefix + term, weight)

                def add_datetime_to_document(termpos, prefix, term, weight):
                    """
                    Adds a datetime to document with positional order
                    to allow exact matches on it.
                    """
                    date, time = term.split()
                    document.add_posting(date, termpos, weight)
                    termpos += 1
                    document.add_posting(time, termpos, weight)
                    termpos += 1
                    document.add_posting(prefix + date, termpos, weight)
                    termpos += 1
                    document.add_posting(prefix + time, termpos, weight)
                    termpos += TERMPOS_DISTANCE + 1
                    return termpos

                data = index.full_prepare(obj)
                weights = index.get_field_weights()

                termpos = term_generator.get_termpos()  # identifies the current position in the document.
                for field in self.schema:
                    if field['field_name'] not in list(data.keys()):
                        # not supported fields are ignored.
                        continue

                    if field['field_name'] in weights:
                        weight = int(weights[field['field_name']])
                    else:
                        weight = 1

                    value = data[field['field_name']]

                    if field['field_name'] in (ID, DJANGO_ID, DJANGO_CT):
                        # Private fields are indexed in a different way:
                        # `django_id` is an int and `django_ct` is text;
                        # besides, they are indexed by their (unstemmed) value.
                        if field['field_name'] == DJANGO_ID:
                            value = int(value)
                        value = _term_to_xapian_value(value, field['type'])

                        document.add_term(TERM_PREFIXES[field['field_name']] + value, weight)
                        document.add_value(field['column'], value)
                        continue
                    else:
                        prefix = TERM_PREFIXES['field'] + field['field_name'].upper()

                        # if not multi_valued, we add as a document value
                        # for sorting and facets
                        if field['multi_valued'] == 'false':
                            document.add_value(field['column'], _term_to_xapian_value(value, field['type']))
                        else:
                            for t in value:
                                # add the exact match of each value
                                term = _to_xapian_term(t)
                                termpos = add_text(termpos, prefix, term, weight)
                            continue

                        term = _to_xapian_term(value)
                        if term == '':
                            continue
                        # from here on the term is a string;
                        # we now decide how it is indexed

                        if field['type'] == 'text':
                            # text is indexed with positional information
                            termpos = add_text(termpos, prefix, term, weight)
                        elif field['type'] == 'datetime':
                            termpos = add_datetime_to_document(termpos, prefix, term, weight)
                        elif field['type'] == 'ngram':
                            add_ngram_to_document(prefix, value, weight)
                        elif field['type'] == 'edge_ngram':
                            add_edge_ngram_to_document(prefix, value, weight)
                        else:
                            # all other terms are added without positional information
                            add_non_text_to_document(prefix, term, weight)

                # store data without indexing it
                document.set_data(pickle.dumps(
                    (obj._meta.app_label, obj._meta.model_name, obj.pk, data),
                    pickle.HIGHEST_PROTOCOL
                ))

                # add the id of the document
                document_id = TERM_PREFIXES[ID] + get_identifier(obj)
                document.add_term(document_id)

                # finally, replace or add the document to the database
                database.replace_document(document_id, document)

        except UnicodeDecodeError:
            sys.stderr.write('Chunk failed.\n')
            pass

        finally:
            database.close()

    def remove(self, obj, commit=True):
        """
        Remove indexes for `obj` from the database.

        We delete all instances of `Q<app_name>.<model_name>.<pk>` which
        should be unique to this object.

        Optional arguments:
           `commit` -- ignored
        """
        database = self._database(writable=True)
        database.delete_document(TERM_PREFIXES[ID] + get_identifier(obj))
        database.close()

    def clear(self, models=(), commit=True):
        """
        Clear all instances of `models` from the database or all models, if
        not specified.

        Optional Arguments:
            `models` -- Models to clear from the database (default = [])

        If `models` is empty, an empty query is executed which matches all
        documents in the database.  Afterwards, each match is deleted.

        Otherwise, for each model, a `delete_document` call is issued with
        the term `XCONTENTTYPE<app_name>.<model_name>`.  This will delete
        all documents with the specified model type.
        """
        if not models:
            # Because there does not appear to be a "clear all" method,
            # it's much quicker to remove the contents of the `self.path`
            # folder than it is to remove each document one at a time.
            if os.path.exists(self.path):
                shutil.rmtree(self.path)
        else:
            database = self._database(writable=True)
            for model in models:
                database.delete_document(TERM_PREFIXES[DJANGO_CT] + get_model_ct(model))
            database.close()

    def document_count(self):
        try:
            return self._database().get_doccount()
        except InvalidIndexError:
            return 0

    def _build_models_query(self, query):
        """
        Builds a query from `query` that filters to documents only from registered models.
        """
        registered_models_ct = self.build_models_list()
        if registered_models_ct:
            restrictions = [xapian.Query('%s%s' % (TERM_PREFIXES[DJANGO_CT], model_ct))
                            for model_ct in registered_models_ct]
            limit_query = xapian.Query(xapian.Query.OP_OR, restrictions)

            query = xapian.Query(xapian.Query.OP_AND, query, limit_query)

        return query

    def _check_field_names(self, field_names):
        """
        Raises InvalidIndexError if any of a field_name in field_names is
        not indexed.
        """
        if field_names:
            for field_name in field_names:
                try:
                    self.column[field_name]
                except KeyError:
                    raise InvalidIndexError('Trying to use non indexed field "%s"' % field_name)

    @log_query
    def search(self, query, sort_by=None, start_offset=0, end_offset=None,
               fields='', highlight=False, facets=None, date_facets=None,
               query_facets=None, narrow_queries=None, spelling_query=None,
               limit_to_registered_models=None, result_class=None, **kwargs):
        """
        Executes the Xapian::query as defined in `query`.

        Required arguments:
            `query` -- Search query to execute

        Optional arguments:
            `sort_by` -- Sort results by specified field (default = None)
            `start_offset` -- Slice results from `start_offset` (default = 0)
            `end_offset` -- Slice results at `end_offset` (default = None), if None, then all documents
            `fields` -- Filter results on `fields` (default = '')
            `highlight` -- Highlight terms in results (default = False)
            `facets` -- Facet results on fields (default = None)
            `date_facets` -- Facet results on date ranges (default = None)
            `query_facets` -- Facet results on queries (default = None)
            `narrow_queries` -- Narrow queries (default = None)
            `spelling_query` -- An optional query to execute spelling suggestion on
            `limit_to_registered_models` -- Limit returned results to models registered in
            the current `SearchSite` (default = True)

        Returns:
            A dictionary with the following keys:
                `results` -- A list of `SearchResult`
                `hits` -- The total available results
                `facets` - A dictionary of facets with the following keys:
                    `fields` -- A list of field facets
                    `dates` -- A list of date facets
                    `queries` -- A list of query facets
            If faceting was not used, the `facets` key will not be present

        If `query` is None, returns no results.

        If `INCLUDE_SPELLING` was enabled in the connection options, the
        extra flag `FLAG_SPELLING_CORRECTION` will be passed to the query parser
        and any suggestions for spell correction will be returned as well as
        the results.
        """
        if xapian.Query.empty(query):
            return {
                'results': [],
                'hits': 0,
            }

        self._check_field_names(facets)
        self._check_field_names(date_facets)
        self._check_field_names(query_facets)

        database = self._database()

        if limit_to_registered_models is None:
            limit_to_registered_models = getattr(settings, 'HAYSTACK_LIMIT_TO_REGISTERED_MODELS', True)

        if result_class is None:
            result_class = SearchResult

        if self.include_spelling is True:
            spelling_suggestion = self._do_spelling_suggestion(database, query, spelling_query)
        else:
            spelling_suggestion = ''

        if narrow_queries is not None:
            query = xapian.Query(
                xapian.Query.OP_AND, query, xapian.Query(
                    xapian.Query.OP_AND, [self.parse_query(narrow_query) for narrow_query in narrow_queries]
                )
            )

        if limit_to_registered_models:
            query = self._build_models_query(query)

        enquire = xapian.Enquire(database)
        if hasattr(settings, 'HAYSTACK_XAPIAN_WEIGHTING_SCHEME'):
            enquire.set_weighting_scheme(xapian.BM25Weight(*settings.HAYSTACK_XAPIAN_WEIGHTING_SCHEME))
        enquire.set_query(query)

        if sort_by:
            try:
                _xapian_sort(enquire, sort_by, self.column)
            except NotSupportedError:
                _old_xapian_sort(enquire, sort_by, self.column)

        results = []
        facets_dict = {
            'fields': {},
            'dates': {},
            'queries': {},
        }

        if not end_offset:
            end_offset = database.get_doccount() - start_offset

        ## prepare spies in case of facets
        if facets:
            facets_spies = self._prepare_facet_field_spies(facets)
            for spy in facets_spies:
                enquire.add_matchspy(spy)

        # print enquire.get_query()

        matches = self._get_enquire_mset(database, enquire, start_offset, end_offset)

        for match in matches:
            app_label, model_name, pk, model_data = pickle.loads(self._get_document_data(database, match.document))
            if highlight:
                model_data['highlighted'] = {
                    self.content_field_name: self._do_highlight(
                        model_data.get(self.content_field_name), query
                    )
                }
            results.append(
                result_class(app_label, model_name, pk, match.percent, **model_data)
            )

        if facets:
            # pick single valued facets from spies
            single_facets_dict = self._process_facet_field_spies(facets_spies)

            # pick multivalued valued facets from results
            multi_facets_dict = self._do_multivalued_field_facets(results, facets)

            # merge both results (http://stackoverflow.com/a/38990/931303)
            facets_dict['fields'] = dict(list(single_facets_dict.items()) + list(multi_facets_dict.items()))

        if date_facets:
            facets_dict['dates'] = self._do_date_facets(results, date_facets)

        if query_facets:
            facets_dict['queries'] = self._do_query_facets(results, query_facets)

        return {
            'results': results,
            'hits': self._get_hit_count(database, enquire),
            'facets': facets_dict,
            'spelling_suggestion': spelling_suggestion,
        }

    def more_like_this(self, model_instance, additional_query=None,
                       start_offset=0, end_offset=None,
                       limit_to_registered_models=True, result_class=None, **kwargs):
        """
        Given a model instance, returns a result set of similar documents.

        Required arguments:
            `model_instance` -- The model instance to use as a basis for
                                retrieving similar documents.

        Optional arguments:
            `additional_query` -- An additional query to narrow results
            `start_offset` -- The starting offset (default=0)
            `end_offset` -- The ending offset (default=None), if None, then all documents
            `limit_to_registered_models` -- Limit returned results to models registered in the search (default = True)

        Returns:
            A dictionary with the following keys:
                `results` -- A list of `SearchResult`
                `hits` -- The total available results

        Opens a database connection, then builds a simple query using the
        `model_instance` to build the unique identifier.

        For each document retrieved(should always be one), adds an entry into
        an RSet (relevance set) with the document id, then, uses the RSet
        to query for an ESet (A set of terms that can be used to suggest
        expansions to the original query), omitting any document that was in
        the original query.

        Finally, processes the resulting matches and returns.
        """
        database = self._database()

        if result_class is None:
            result_class = SearchResult

        query = xapian.Query(TERM_PREFIXES[ID] + get_identifier(model_instance))

        enquire = xapian.Enquire(database)
        enquire.set_query(query)

        rset = xapian.RSet()

        if not end_offset:
            end_offset = database.get_doccount()

        match = None
        for match in self._get_enquire_mset(database, enquire, 0, end_offset):
            rset.add_document(match.docid)

        if match is None:
            if not self.silently_fail:
                raise InvalidIndexError('Instance %s with id "%d" not indexed' %
                                        (get_identifier(model_instance), model_instance.id))
            else:
                return {'results': [],
                        'hits': 0}

        query = xapian.Query(
            xapian.Query.OP_ELITE_SET,
            [expand.term for expand in enquire.get_eset(match.document.termlist_count(), rset, XHExpandDecider())],
            match.document.termlist_count()
        )
        query = xapian.Query(
            xapian.Query.OP_AND_NOT, [query, TERM_PREFIXES[ID] + get_identifier(model_instance)]
        )

        if limit_to_registered_models:
            query = self._build_models_query(query)

        if additional_query:
            query = xapian.Query(
                xapian.Query.OP_AND, query, additional_query
            )

        enquire.set_query(query)

        results = []
        matches = self._get_enquire_mset(database, enquire, start_offset, end_offset)

        for match in matches:
            app_label, model_name, pk, model_data = pickle.loads(self._get_document_data(database, match.document))
            results.append(
                result_class(app_label, model_name, pk, match.percent, **model_data)
            )

        return {
            'results': results,
            'hits': self._get_hit_count(database, enquire),
            'facets': {
                'fields': {},
                'dates': {},
                'queries': {},
            },
            'spelling_suggestion': None,
        }

    def parse_query(self, query_string):
        """
        Given a `query_string`, will attempt to return a xapian.Query

        Required arguments:
            ``query_string`` -- A query string to parse

        Returns a xapian.Query
        """
        if query_string == '*':
            return xapian.Query('')  # Match everything
        elif query_string == '':
            return xapian.Query()  # Match nothing

        qp = xapian.QueryParser()
        qp.set_database(self._database())
        qp.set_stemmer(xapian.Stem(self.language))
        qp.set_stemming_strategy(self.stemming_strategy)
        qp.set_default_op(XAPIAN_OPTS[DEFAULT_OPERATOR])
        qp.add_boolean_prefix(DJANGO_CT, TERM_PREFIXES[DJANGO_CT])

        for field_dict in self.schema:
            # since 'django_ct' has a boolean_prefix,
            # we ignore it here.
            if field_dict['field_name'] == DJANGO_CT:
                continue

            qp.add_prefix(
                field_dict['field_name'],
                TERM_PREFIXES['field'] + field_dict['field_name'].upper()
            )

        vrp = XHValueRangeProcessor(self)
        qp.add_valuerangeprocessor(vrp)

        return qp.parse_query(query_string, self.flags)

    def build_schema(self, fields):
        """
        Build the schema from fields.

        :param fields: A list of fields in the index
        :returns: list of dictionaries

        Each dictionary has the keys
         field_name: The name of the field index
         type: what type of value it is
         'multi_valued': if it allows more than one value
         'column': a number identifying it
         'type': the type of the field
         'multi_valued': 'false', 'column': 0}
        """
        content_field_name = ''
        schema_fields = [
            {'field_name': ID,
             'type': 'text',
             'multi_valued': 'false',
             'column': 0},
            {'field_name': DJANGO_ID,
             'type': 'integer',
             'multi_valued': 'false',
             'column': 1},
            {'field_name': DJANGO_CT,
             'type': 'text',
             'multi_valued': 'false',
             'column': 2},
        ]
        self._columns[ID] = 0
        self._columns[DJANGO_ID] = 1
        self._columns[DJANGO_CT] = 2

        column = len(schema_fields)

        for field_name, field_class in sorted(list(fields.items()), key=lambda n: n[0]):
            if field_class.document is True:
                content_field_name = field_class.index_fieldname

            if field_class.indexed is True:
                field_data = {
                    'field_name': field_class.index_fieldname,
                    'type': 'text',
                    'multi_valued': 'false',
                    'column': column,
                }

                if field_class.field_type == 'date':
                    field_data['type'] = 'date'
                elif field_class.field_type == 'datetime':
                    field_data['type'] = 'datetime'
                elif field_class.field_type == 'integer':
                    field_data['type'] = 'integer'
                elif field_class.field_type == 'float':
                    field_data['type'] = 'float'
                elif field_class.field_type == 'boolean':
                    field_data['type'] = 'boolean'
                elif field_class.field_type == 'ngram':
                    field_data['type'] = 'ngram'
                elif field_class.field_type == 'edge_ngram':
                    field_data['type'] = 'edge_ngram'

                if field_class.is_multivalued:
                    field_data['multi_valued'] = 'true'

                schema_fields.append(field_data)
                self._columns[field_data['field_name']] = column
                column += 1

        return content_field_name, schema_fields

    @staticmethod
    def _do_highlight(content, query, tag='em'):
        """
        Highlight `query` terms in `content` with html `tag`.

        This method assumes that the input text (`content`) does not contain
        any special formatting.  That is, it does not contain any html tags
        or similar markup that could be screwed up by the highlighting.

        Required arguments:
            `content` -- Content to search for instances of `text`
            `text` -- The text to be highlighted
        """
        for term in query:
            term = term.decode('utf-8')
            for match in re.findall('[^A-Z]+', term):  # Ignore field identifiers
                match_re = re.compile(match, re.I)
                content = match_re.sub('<%s>%s</%s>' % (tag, term, tag), content)

        return content

    def _prepare_facet_field_spies(self, facets):
        """
        Returns a list of spies based on the facets
        used to count frequencies.
        """
        spies = []
        for facet in facets:
            slot = self.column[facet]
            spy = xapian.ValueCountMatchSpy(slot)
            # add attribute "slot" to know which column this spy is targeting.
            spy.slot = slot
            spies.append(spy)
        return spies

    def _process_facet_field_spies(self, spies):
        """
        Returns a dict of facet names with lists of
        tuples of the form (term, term_frequency)
        from a list of spies that observed the enquire.
        """
        facet_dict = {}
        for spy in spies:
            field = self.schema[spy.slot]
            field_name, field_type = field['field_name'], field['type']

            facet_dict[field_name] = []
            for facet in list(spy.values()):
                if field_type == 'float':
                    # the float term is a Xapian serialized object, which is
                    # in bytes.
                    term = facet.term
                else:
                    term = facet.term.decode('utf-8')

                facet_dict[field_name].append((_from_xapian_value(term, field_type),
                                               facet.termfreq))
        return facet_dict

    def _do_multivalued_field_facets(self, results, field_facets):
        """
        Implements a multivalued field facet on the results.

        This is implemented using brute force - O(N^2) -
        because Xapian does not have it implemented yet
        (see http://trac.xapian.org/ticket/199)
        """
        facet_dict = {}

        for field in field_facets:
            facet_list = {}
            if not self._multi_value_field(field):
                continue

            for result in results:
                field_value = getattr(result, field)
                for item in field_value:  # Facet each item in a MultiValueField
                    facet_list[item] = facet_list.get(item, 0) + 1

            facet_dict[field] = list(facet_list.items())
        return facet_dict

    @staticmethod
    def _do_date_facets(results, date_facets):
        """
        Private method that facets a document by date ranges

        Required arguments:
            `results` -- A list SearchResults to facet
            `date_facets` -- A dictionary containing facet parameters:
                {'field': {'start_date': ..., 'end_date': ...: 'gap_by': '...', 'gap_amount': n}}
                nb., gap must be one of the following:
                    year|month|day|hour|minute|second

        For each date facet field in `date_facets`, generates a list
        of date ranges (from `start_date` to `end_date` by `gap_by`) then
        iterates through `results` and tallies the count for each date_facet.

        Returns a dictionary of date facets (fields) containing a list with
        entries for each range and a count of documents matching the range.

        eg. {
            'pub_date': [
                (datetime.datetime(2009, 1, 1, 0, 0), 5),
                (datetime.datetime(2009, 2, 1, 0, 0), 0),
                (datetime.datetime(2009, 3, 1, 0, 0), 0),
                (datetime.datetime(2008, 4, 1, 0, 0), 1),
                (datetime.datetime(2008, 5, 1, 0, 0), 2),
            ],
        }
        """
        def next_datetime(previous, gap_value, gap_type):
            year = previous.year
            month = previous.month

            if gap_type == 'year':
                next = previous.replace(year=year + gap_value)
            elif gap_type == 'month':
                if month + gap_value <= 12:
                    next = previous.replace(month=month + gap_value)
                else:
                    next = previous.replace(
                        month=((month + gap_value) % 12),
                        year=(year + (month + gap_value) // 12)
                    )
            elif gap_type == 'day':
                next = previous + datetime.timedelta(days=gap_value)
            elif gap_type == 'hour':
                return previous + datetime.timedelta(hours=gap_value)
            elif gap_type == 'minute':
                next = previous + datetime.timedelta(minutes=gap_value)
            elif gap_type == 'second':
                next = previous + datetime.timedelta(seconds=gap_value)
            else:
                raise TypeError('\'gap_by\' must be '
                                '{second, minute, day, month, year}')
            return next

        facet_dict = {}

        for date_facet, facet_params in list(date_facets.items()):
            gap_type = facet_params.get('gap_by')
            gap_value = facet_params.get('gap_amount', 1)
            date_range = facet_params['start_date']

            # construct the bins of the histogram
            facet_list = []
            while date_range < facet_params['end_date']:
                facet_list.append((date_range, 0))
                date_range = next_datetime(date_range, gap_value, gap_type)

            facet_list = sorted(facet_list, key=lambda x: x[0], reverse=True)

            for result in results:
                result_date = getattr(result, date_facet)

                # convert date to datetime
                if not isinstance(result_date, datetime.datetime):
                    result_date = datetime.datetime(result_date.year,
                                                    result_date.month,
                                                    result_date.day)

                # ignore results outside the boundaries.
                if facet_list[0][0] < result_date < facet_list[-1][0]:
                    continue

                # populate the histogram by putting the result on the right bin.
                for n, facet_date in enumerate(facet_list):
                    if result_date > facet_date[0]:
                        # equal to facet_list[n][1] += 1, but for a tuple
                        facet_list[n] = (facet_list[n][0], (facet_list[n][1] + 1))
                        break  # bin found; go to next result

            facet_dict[date_facet] = facet_list

        return facet_dict

    def _do_query_facets(self, results, query_facets):
        """
        Private method that facets a document by query

        Required arguments:
            `results` -- A list SearchResults to facet
            `query_facets` -- A dictionary containing facet parameters:
                {'field': 'query', [...]}

        For each query in `query_facets`, generates a dictionary entry with
        the field name as the key and a tuple with the query and result count
        as the value.

        eg. {'name': ('a*', 5)}
        """
        facet_dict = {}
        for field, query in list(dict(query_facets).items()):
            facet_dict[field] = (query, self.search(self.parse_query(query))['hits'])

        return facet_dict

    @staticmethod
    def _do_spelling_suggestion(database, query, spelling_query):
        """
        Private method that returns a single spelling suggestion based on
        `spelling_query` or `query`.

        Required arguments:
            `database` -- The database to check spelling against
            `query` -- The query to check
            `spelling_query` -- If not None, this will be checked instead of `query`

        Returns a string with a suggested spelling
        """
        if spelling_query:
            if ' ' in spelling_query:
                return ' '.join([database.get_spelling_suggestion(term).decode('utf-8') for term in spelling_query.split()])
            else:
                return database.get_spelling_suggestion(spelling_query).decode('utf-8')

        term_set = set()
        for term in query:
            for match in re.findall('[^A-Z]+', term.decode('utf-8')):  # Ignore field identifiers
                term_set.add(database.get_spelling_suggestion(match).decode('utf-8'))

        return ' '.join(term_set)

    def _database(self, writable=False):
        """
        Private method that returns a xapian.Database for use.

        Optional arguments:
            ``writable`` -- Open the database in read/write mode (default=False)

        Returns an instance of a xapian.Database or xapian.WritableDatabase
        """
        if self.path == MEMORY_DB_NAME:
            if not self.inmemory_db:
                self.inmemory_db = xapian.inmemory_open()
            return self.inmemory_db
        if writable:
            database = xapian.WritableDatabase(self.path, xapian.DB_CREATE_OR_OPEN)
        else:
            try:
                database = xapian.Database(self.path)
            except xapian.DatabaseOpeningError:
                raise InvalidIndexError('Unable to open index at %s' % self.path)

        return database

    @staticmethod
    def _get_enquire_mset(database, enquire, start_offset, end_offset, checkatleast=DEFAULT_CHECK_AT_LEAST):
        """
        A safer version of Xapian.enquire.get_mset

        Simply wraps the Xapian version and catches any `Xapian.DatabaseModifiedError`,
        attempting a `database.reopen` as needed.

        Required arguments:
            `database` -- The database to be read
            `enquire` -- An instance of an Xapian.enquire object
            `start_offset` -- The start offset to pass to `enquire.get_mset`
            `end_offset` -- The end offset to pass to `enquire.get_mset`
        """
        try:
            return enquire.get_mset(start_offset, end_offset, checkatleast)
        except xapian.DatabaseModifiedError:
            database.reopen()
            return enquire.get_mset(start_offset, end_offset, checkatleast)

    @staticmethod
    def _get_document_data(database, document):
        """
        A safer version of Xapian.document.get_data

        Simply wraps the Xapian version and catches any `Xapian.DatabaseModifiedError`,
        attempting a `database.reopen` as needed.

        Required arguments:
            `database` -- The database to be read
            `document` -- An instance of an Xapian.document object
        """
        try:
            return document.get_data()
        except xapian.DatabaseModifiedError:
            database.reopen()
            return document.get_data()

    def _get_hit_count(self, database, enquire):
        """
        Given a database and enquire instance, returns the estimated number
        of matches.

        Required arguments:
            `database` -- The database to be queried
            `enquire` -- The enquire instance
        """
        return self._get_enquire_mset(
            database, enquire, 0, database.get_doccount()
        ).size()

    def _multi_value_field(self, field):
        """
        Private method that returns `True` if a field is multi-valued, else
        `False`.

        Required arguemnts:
            `field` -- The field to lookup

        Returns a boolean value indicating whether the field is multi-valued.
        """
        for field_dict in self.schema:
            if field_dict['field_name'] == field:
                return field_dict['multi_valued'] == 'true'
        return False


class XapianSearchQuery(BaseSearchQuery):
    """
    This class is the Xapian specific version of the SearchQuery class.
    It acts as an intermediary between the ``SearchQuerySet`` and the
    ``SearchBackend`` itself.
    """
    def build_params(self, *args, **kwargs):
        kwargs = super(XapianSearchQuery, self).build_params(*args, **kwargs)

        if self.end_offset is not None:
            kwargs['end_offset'] = self.end_offset - self.start_offset

        return kwargs

    def build_query(self):
        if not self.query_filter:
            query = xapian.Query('')
        else:
            query = self._query_from_search_node(self.query_filter)

        if self.models:
            subqueries = [
                xapian.Query(
                    xapian.Query.OP_SCALE_WEIGHT,
                    xapian.Query('%s%s' % (TERM_PREFIXES[DJANGO_CT], get_model_ct(model))),
                    0  # Pure boolean sub-query
                ) for model in self.models
            ]
            query = xapian.Query(
                xapian.Query.OP_AND, query,
                xapian.Query(xapian.Query.OP_OR, subqueries)
            )

        if self.boost:
            subqueries = [
                xapian.Query(
                    xapian.Query.OP_SCALE_WEIGHT,
                    self._term_query(term, None, None), value
                ) for term, value in list(self.boost.items())
            ]
            query = xapian.Query(
                xapian.Query.OP_AND_MAYBE, query,
                xapian.Query(xapian.Query.OP_OR, subqueries)
            )

        return query

    def _query_from_search_node(self, search_node, is_not=False):
        query_list = []

        for child in search_node.children:
            if isinstance(child, SearchNode):
                query_list.append(
                    self._query_from_search_node(child, child.negated)
                )
            else:
                expression, term = child
                field_name, filter_type = search_node.split_expression(expression)

                constructed_query_list = self._query_from_term(term, field_name, filter_type, is_not)
                query_list.extend(constructed_query_list)

        if search_node.connector == 'OR':
            return xapian.Query(xapian.Query.OP_OR, query_list)
        else:
            return xapian.Query(xapian.Query.OP_AND, query_list)

    def _query_from_term(self, term, field_name, filter_type, is_not):
        """
        Uses arguments to construct a list of xapian.Query's.
        """
        if field_name != 'content' and field_name not in self.backend.column:
            raise InvalidIndexError('field "%s" not indexed' % field_name)

        # It it is an AutoQuery, it has no filters
        # or others, thus we short-circuit the procedure.
        if isinstance(term, AutoQuery):
            if field_name != 'content':
                query = '%s:%s' % (field_name, term.prepare(self))
            else:
                query = term.prepare(self)
            return [self.backend.parse_query(query)]
        query_list = []

        # Handle `ValuesListQuerySet`.
        if hasattr(term, 'values_list'):
            term = list(term)

        if field_name == 'content':
            # content is the generic search:
            # force no field_name search
            # and the field_type to be 'text'.
            field_name = None
            field_type = 'text'

            # we don't know what is the type(term), so we parse it.
            # Ideally this would not be required, but
            # some filters currently depend on the term to make decisions.
            term = _to_xapian_term(term)

            query_list.append(self._filter_contains(term, field_name, field_type, is_not))
            # when filter has no filter_type, haystack uses
            # filter_type = 'content'. Here we remove it
            # since the above query is already doing this
            if filter_type == 'content':
                filter_type = None
        else:
            # get the field_type from the backend
            field_type = self.backend.schema[self.backend.column[field_name]]['type']

        # private fields don't accept 'contains' or 'startswith'
        # since they have no meaning.
        if filter_type in ('contains', 'startswith') and field_name in (ID, DJANGO_ID, DJANGO_CT):
            filter_type = 'exact'

        if field_type == 'text':
            # we don't know what type "term" is, but we know we are searching as text
            # so we parse it like that.
            # Ideally this would not be required since _term_query does it, but
            # some filters currently depend on the term to make decisions.
            if isinstance(term, list):
                term = [_to_xapian_term(term) for term in term]
            else:
                term = _to_xapian_term(term)

        # todo: we should check that the filter is valid for this field_type or raise InvalidIndexError
        if filter_type == 'contains':
            query_list.append(self._filter_contains(term, field_name, field_type, is_not))
        elif filter_type in ('content', 'exact'):
            query_list.append(self._filter_exact(term, field_name, field_type, is_not))
        elif filter_type == 'in':
            query_list.append(self._filter_in(term, field_name, field_type, is_not))
        elif filter_type == 'startswith':
            query_list.append(self._filter_startswith(term, field_name, field_type, is_not))
        elif filter_type == 'endswith':
            raise NotImplementedError("The Xapian search backend doesn't support endswith queries.")
        elif filter_type == 'gt':
            query_list.append(self._filter_gt(term, field_name, field_type, is_not))
        elif filter_type == 'gte':
            query_list.append(self._filter_gte(term, field_name, field_type, is_not))
        elif filter_type == 'lt':
            query_list.append(self._filter_lt(term, field_name, field_type, is_not))
        elif filter_type == 'lte':
            query_list.append(self._filter_lte(term, field_name, field_type, is_not))
        elif filter_type == 'range':
            query_list.append(self._filter_range(term, field_name, field_type, is_not))
        return query_list

    def _all_query(self):
        """
        Returns a match all query.
        """
        return xapian.Query('')

    def _filter_contains(self, term, field_name, field_type, is_not):
        """
        Splits the sentence in terms and join them with OR,
        using stemmed and un-stemmed.

        Assumes term is not a list.
        """
        if field_type == 'text':
            term_list = term.split()
        else:
            term_list = [term]

        query = self._or_query(term_list, field_name, field_type)
        if is_not:
            return xapian.Query(xapian.Query.OP_AND_NOT, self._all_query(), query)
        else:
            return query

    def _filter_in(self, term_list, field_name, field_type, is_not):
        """
        Returns a query that matches exactly ANY term in term_list.

        Notice that:
         A in {B,C} <=> (A = B or A = C)
         ~(A in {B,C}) <=> ~(A = B or A = C)
        Because OP_AND_NOT(C, D) <=> (C and ~D), then D=(A in {B,C}) requires `is_not=False`.

        Assumes term is a list.
        """
        query_list = [self._filter_exact(term, field_name, field_type, is_not=False)
                      for term in term_list]

        if is_not:
            return xapian.Query(xapian.Query.OP_AND_NOT, self._all_query(),
                                xapian.Query(xapian.Query.OP_OR, query_list))
        else:
            return xapian.Query(xapian.Query.OP_OR, query_list)

    def _filter_exact(self, term, field_name, field_type, is_not):
        """
        Returns a query that matches exactly the un-stemmed term
        with positional order.

        Assumes term is not a list.
        """
        if field_type == 'text' and field_name not in (DJANGO_CT,):
            term = '^ %s $' % term
            query = self._phrase_query(term.split(), field_name, field_type)
        else:
            query = self._term_query(term, field_name, field_type, stemmed=False)

        if is_not:
            return xapian.Query(xapian.Query.OP_AND_NOT, self._all_query(), query)
        else:
            return query

    def _filter_startswith(self, term, field_name, field_type, is_not):
        """
        Returns a startswith query on the un-stemmed term.

        Assumes term is not a list.
        """
        if field_type == 'text':
            if len(term.split()) == 1:
                term = '^ %s*' % term
                query = self.backend.parse_query(term)
            else:
                term = '^ %s' % term
                query = self._phrase_query(term.split(), field_name, field_type)
        else:
            term = '^%s*' % term
            query = self.backend.parse_query(term)

        if is_not:
            return xapian.Query(xapian.Query.OP_AND_NOT, self._all_query(), query)
        return query

    def _or_query(self, term_list, field, field_type):
        """
        Joins each item of term_list decorated by _term_query with an OR.
        """
        term_list = [self._term_query(term, field, field_type) for term in term_list]
        return xapian.Query(xapian.Query.OP_OR, term_list)

    def _phrase_query(self, term_list, field_name, field_type):
        """
        Returns a query that matches exact terms with
        positional order (i.e. ["this", "thing"] != ["thing", "this"])
        and no stem.

        If `field_name` is not `None`, restrict to the field.
        """
        term_list = [self._term_query(term, field_name, field_type,
                                      stemmed=False) for term in term_list]

        query = xapian.Query(xapian.Query.OP_PHRASE, term_list)
        return query

    def _term_query(self, term, field_name, field_type, stemmed=True):
        """
        Constructs a query of a single term.

        If `field_name` is not `None`, the term is search on that field only.
        If exact is `True`, the search is restricted to boolean matches.
        """
        constructor = '{prefix}{term}'

        # construct the prefix to be used.
        prefix = ''
        if field_name:
            prefix = TERM_PREFIXES['field'] + field_name.upper()
            term = _to_xapian_term(term)

        if field_name in (ID, DJANGO_ID, DJANGO_CT):
            # to ensure the value is serialized correctly.
            if field_name == DJANGO_ID:
                term = int(term)
            term = _term_to_xapian_value(term, field_type)
            return xapian.Query('%s%s' % (TERM_PREFIXES[field_name], term))

        # we construct the query dates in a slightly different way
        if field_type == 'datetime':
            date, time = term.split()
            return xapian.Query(xapian.Query.OP_AND_MAYBE,
                                constructor.format(prefix=prefix, term=date),
                                constructor.format(prefix=prefix, term=time)
                                )

        # only use stem if field is text or "None"
        if field_type not in ('text', None):
            stemmed = False

        unstemmed_term = constructor.format(prefix=prefix, term=term)
        if stemmed:
            stem = xapian.Stem(self.backend.language)
            stemmed_term = 'Z' + constructor.format(prefix=prefix, term=stem(term).decode('utf-8'))

            return xapian.Query(xapian.Query.OP_OR,
                                xapian.Query(stemmed_term),
                                xapian.Query(unstemmed_term)
                                )
        else:
            return xapian.Query(unstemmed_term)

    def _filter_gt(self, term, field_name, field_type, is_not):
        return self._filter_lte(term, field_name, field_type, is_not=not is_not)

    def _filter_lt(self, term, field_name, field_type, is_not):
        return self._filter_gte(term, field_name, field_type, is_not=not is_not)

    def _filter_gte(self, term, field_name, field_type, is_not):
        """
        Private method that returns a xapian.Query that searches for any term
        that is greater than `term` in a specified `field`.
        """
        vrp = XHValueRangeProcessor(self.backend)
        pos, begin, end = vrp('%s:%s' % (field_name, _term_to_xapian_value(term, field_type)), '*')
        if is_not:
            return xapian.Query(xapian.Query.OP_AND_NOT,
                                self._all_query(),
                                xapian.Query(xapian.Query.OP_VALUE_RANGE, pos, begin, end)
                                )
        return xapian.Query(xapian.Query.OP_VALUE_RANGE, pos, begin, end)

    def _filter_lte(self, term, field_name, field_type, is_not):
        """
        Private method that returns a xapian.Query that searches for any term
        that is less than `term` in a specified `field`.
        """
        vrp = XHValueRangeProcessor(self.backend)
        pos, begin, end = vrp('%s:' % field_name, '%s' % _term_to_xapian_value(term, field_type))
        if is_not:
            return xapian.Query(xapian.Query.OP_AND_NOT,
                                self._all_query(),
                                xapian.Query(xapian.Query.OP_VALUE_RANGE, pos, begin, end)
                                )
        return xapian.Query(xapian.Query.OP_VALUE_RANGE, pos, begin, end)

    def _filter_range(self, term, field_name, field_type, is_not):
        """
        Private method that returns a xapian.Query that searches for any term
        that is between the values from the `term` list.
        """
        vrp = XHValueRangeProcessor(self.backend)
        pos, begin, end = vrp('%s:%s' % (field_name, _term_to_xapian_value(term[0], field_type)),
                              '%s' % _term_to_xapian_value(term[1], field_type))
        if is_not:
            return xapian.Query(xapian.Query.OP_AND_NOT,
                                self._all_query(),
                                xapian.Query(xapian.Query.OP_VALUE_RANGE, pos, begin, end)
                                )
        return xapian.Query(xapian.Query.OP_VALUE_RANGE, pos, begin, end)


def _term_to_xapian_value(term, field_type):
    """
    Converts a term to a serialized
    Xapian value based on the field_type.
    """
    assert field_type in FIELD_TYPES

    def strf(dt):
        """
        Equivalent to datetime.datetime.strptime(dt, DATETIME_FORMAT)
        but accepts years below 1900 (see http://stackoverflow.com/q/10263956/931303)
        """
        return '%04d%02d%02d%02d%02d%02d' % (
            dt.year, dt.month, dt.day, dt.hour, dt.minute, dt.second)

    if field_type == 'boolean':
        assert isinstance(term, bool)
        if term:
            value = 't'
        else:
            value = 'f'

    elif field_type == 'integer':
        value = INTEGER_FORMAT % term
    elif field_type == 'float':
        value = xapian.sortable_serialise(term)
    elif field_type == 'date' or field_type == 'datetime':
        if field_type == 'date':
            # http://stackoverflow.com/a/1937636/931303 and comments
            term = datetime.datetime.combine(term, datetime.time())
        value = strf(term)
    else:  # field_type == 'text'
        value = _to_xapian_term(term)

    return value


def _to_xapian_term(term):
    """
    Converts a Python type to a
    Xapian term that can be indexed.
    """
    return force_text(term).lower()


def _from_xapian_value(value, field_type):
    """
    Converts a serialized Xapian value
    to Python equivalent based on the field_type.

    Doesn't accept multivalued fields.
    """
    assert field_type in FIELD_TYPES
    if field_type == 'boolean':
        if value == 't':
            return True
        elif value == 'f':
            return False
        else:
            InvalidIndexError('Field type "%d" does not accept value "%s"' % (field_type, value))
    elif field_type == 'integer':
        return int(value)
    elif field_type == 'float':
        return xapian.sortable_unserialise(value)
    elif field_type == 'date' or field_type == 'datetime':
        datetime_value = datetime.datetime.strptime(value, DATETIME_FORMAT)
        if field_type == 'datetime':
            return datetime_value
        else:
            return datetime_value.date()
    else:  # field_type == 'text'
        return value


def _old_xapian_sort(enquire, sort_by, column):
    sorter = xapian.MultiValueSorter()

    for sort_field in sort_by:
        if sort_field.startswith('-'):
            reverse = True
            sort_field = sort_field[1:]  # Strip the '-'
        else:
            reverse = False  # Reverse is inverted in Xapian -- http://trac.xapian.org/ticket/311
        sorter.add(column[sort_field], reverse)

    enquire.set_sort_by_key_then_relevance(sorter, True)


def _xapian_sort(enquire, sort_by, column):
    try:
        sorter = xapian.MultiValueKeyMaker()
    except AttributeError:
        raise NotSupportedError

    for sort_field in sort_by:
        if sort_field.startswith('-'):
            reverse = False
            sort_field = sort_field[1:]  # Strip the '-'
        else:
            reverse = True
        sorter.add_value(column[sort_field], reverse)

    enquire.set_sort_by_key_then_relevance(sorter, True)


class XapianEngine(BaseEngine):
    backend = XapianSearchBackend
    query = XapianSearchQuery
