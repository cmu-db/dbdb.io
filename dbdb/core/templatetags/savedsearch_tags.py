from django import template
from django.core import signing

register = template.Library()

_SALT = 'wu-tang is for the children'


@register.filter
def ss_token(pk):
    """Return a signed, URL-safe token for the given SavedSearch primary key."""
    return signing.dumps(int(pk), salt=_SALT)


def ss_decode(token):
    """Decode a token back to a SavedSearch pk. Returns None on failure."""
    try:
        return signing.loads(token, salt=_SALT)
    except signing.BadSignature:
        return None
