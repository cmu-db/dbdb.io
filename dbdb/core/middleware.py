from django.http import HttpResponsePermanentRedirect


class LowercasePathMiddleware:
    """Redirect any URL containing uppercase letters to its lowercase equivalent."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        path = request.path_info
        if path != path.lower():
            qs = request.META.get('QUERY_STRING', '')
            url = path.lower()
            if qs:
                url += '?' + qs
            return HttpResponsePermanentRedirect(url)
        return self.get_response(request)
