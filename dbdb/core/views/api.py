# stdlib imports
import datetime
import json

import jwt

# django imports
from django.conf import settings
from django.db.models import Case, IntegerField, Value, When
from django.http import HttpResponse, JsonResponse
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import csrf_exempt

# project imports
from dbdb.core.models import Organization, System, SystemVisit


# ==============================================
# CounterView
# ==============================================
@method_decorator(csrf_exempt, name='dispatch')
class CounterView(View):

    @staticmethod
    def build_token(origin, **kwargs):
        payload = dict(kwargs)
        payload.update( {
            #'exp': datetime.datetime.utcnow() + datetime.timedelta(seconds=15), # +15 seconds ## disabled expatriation to allow caching
            'iss': f'counter:{origin}',
            'nbf': datetime.datetime.utcnow(),
        })
        s = jwt.encode(payload, settings.SECRET_KEY, algorithm='HS256')
        if isinstance(s, bytes):
            s = s.decode('utf-8')
        return s

    def post(self, request):
        token = request.POST.get('token')

        if not token:
            return JsonResponse({ 'status':'missing token'}, status=400)
        try:
            payload = jwt.decode(
                token,
                settings.SECRET_KEY,
                algorithms=['HS256']
            )

            iss = payload.get('iss')

            if iss == 'counter:system':
                pk = payload['pk']

                # Skip bots
                user_agent = request.headers.get('user-agent', '')
                if user_agent.lower().find("bot") != -1:
                    return JsonResponse({ 'status':'bot' })

                # And add a SystemVisit entry
                x_forwarded_for = request.headers.get('x-forwarded-for')
                if x_forwarded_for:
                    ip = x_forwarded_for.split(',')[-1].strip()
                else:
                    ip = request.META.get('REMOTE_ADDR')

                # save visit
                system_visit = SystemVisit.objects.create(
                    system_id=pk,
                    ip_address=ip,
                    user_agent=user_agent[:127]
                )
                pass
            else:
                return JsonResponse({ 'status':('unrecognized counter: %r' % iss) }, status=400)
            pass
        except jwt.ExpiredSignatureError:
            return JsonResponse({ 'status':'expired counter' }, status=400)
        except jwt.DecodeError:
            return JsonResponse({ 'status':'invalid token' }, status=400)

        return JsonResponse({ 'status':'ok' })

    pass

# ==============================================
# System Name AutoComplete
# ==============================================
def organization_autocomplete(request):
    q = request.GET.get('q', '').strip()
    names = (
        Organization.objects
        .filter(name__icontains=q)
        .order_by('name')
        .values_list('name', flat=True)[:12]
    ) if q else []
    return JsonResponse(list(names), safe=False)


def system_autocomplete(request):
    search_q = request.GET.get('q', '').strip()
    if search_q:
        sqs = System.objects.filter(name__icontains=search_q).annotate(
            exact_match=Case(
                When(name__iexact=search_q, then=Value(0)),
                default=Value(1),
                output_field=IntegerField(),
            )).order_by('exact_match', 'name')
        sqs = sqs.values('name')[:8]
        suggestions = [system["name"] for system in sqs]
    else:
        suggestions = [ ]

    data = json.dumps(suggestions)
    return HttpResponse(data, content_type='application/json')
