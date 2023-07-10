from django.contrib.postgres.search import SearchConfig, SearchVectorField
from django.db.models import Func
from django.db.models.expressions import ExpressionList

class SearchVector(Func):
    """
    Replacement of `django.contrib.postgres.search.SearchVector` that
    works around limitations of the later with regards to indexing.

    See https://code.djangoproject.com/ticket/31304#comment:6
    """

    function = 'to_tsvector'
    output_field = SearchVectorField()

    def __init__(self, *expressions, config=None):
        expressions = (
            SearchConfig.from_parameter(config),
            ExpressionList(*expressions, arg_joiner=" || ' ' || "),
        )
        super().__init__(*expressions)
    pass