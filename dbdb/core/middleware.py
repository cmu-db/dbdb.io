from django.conf import settings
from django.http import HttpResponsePermanentRedirect

_LOWERCASE_PREFIXES = ('/db/', '/org/')


class CloudflareAuthCacheMiddleware:
    """Set Cache-Control: private, no-store for authenticated users.

    Skips static file URLs — those should always be publicly cacheable.
    Complements the Cloudflare Cache Rule that bypasses cache when a
    'sessionid' cookie is present.
    """

    def __init__(self, get_response):
        self.get_response = get_response
        self._static_prefix = settings.STATIC_URL

    def __call__(self, request):
        response = self.get_response(request)
        if (request.user.is_authenticated
                and not request.path.startswith(self._static_prefix)):
            response['Cache-Control'] = 'private, no-store'
        return response


class LowercasePathMiddleware:
    """Redirect /db/ and /org/ URLs with uppercase letters to their lowercase equivalent."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        path = request.path_info
        if path != path.lower() and any(path.startswith(p) for p in _LOWERCASE_PREFIXES):
            qs = request.META.get('QUERY_STRING', '')
            url = path.lower()
            if qs:
                url += '?' + qs
            return HttpResponsePermanentRedirect(url)
        return self.get_response(request)
