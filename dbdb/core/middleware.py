from django.http import HttpResponsePermanentRedirect

_LOWERCASE_PREFIXES = ('/db/', '/org/')


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
