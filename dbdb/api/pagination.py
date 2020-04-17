# third-party imports
from rest_framework.pagination import LimitOffsetPagination


# classes

class StandardPagination(LimitOffsetPagination):

    default_limit = 10
    max_limit = 100

    pass
