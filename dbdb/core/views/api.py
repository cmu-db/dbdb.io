# stdlib imports
import datetime
import json

import jwt

# django imports
from django.conf import settings
from django.db.models import Case, IntegerField, Value, When
from django.http import HttpResponse, JsonResponse
from django.contrib.auth.decorators import login_required
from django.views.decorators.cache import never_cache
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import csrf_exempt

# project imports
from dbdb.core.models import CitationUrl, Organization, System, SystemVersion, SystemVisit


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

    @method_decorator(never_cache)
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
@login_required
def citation_url_autocomplete(request):
    q = request.GET.get('q', '').strip()
    urls = (
        CitationUrl.objects
        .filter(url__icontains=q, status=CitationUrl.Status.VALID)
        .order_by('url')
        .values_list('url', flat=True)[:settings.DBDB_AUTOCOMPLETE_CITATION_NUM_ENTRIES]
    ) if q else []
    return JsonResponse(list(urls), safe=False)


def organization_autocomplete(request):
    q = request.GET.get('q', '').strip()
    names = (
        Organization.objects
        .filter(name__icontains=q)
        .order_by('name')
        .values_list('name', flat=True)[:settings.DBDB_AUTOCOMPLETE_ORGANIZATION_NUM_ENTRIES]
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
        sqs = list(sqs.values('id', 'name')[:settings.DBDB_AUTOCOMPLETE_SYSTEM_NUM_ENTRIES])

        # Detect name collisions within the result set — rare, so only fetch
        # developer orgs when at least one duplicate name is present.
        name_counts = {}
        for row in sqs:
            name_counts[row['name']] = name_counts.get(row['name'], 0) + 1
        duplicate_names = {name for name, count in name_counts.items() if count > 1}

        if duplicate_names:
            duplicate_ids = [row['id'] for row in sqs if row['name'] in duplicate_names]
            dev_org_map = {}
            for sv in (SystemVersion.objects
                       .filter(system_id__in=duplicate_ids, is_current=True)
                       .prefetch_related('developer_orgs')
                       .only('system_id')):
                orgs = list(sv.developer_orgs.all())
                if orgs:
                    dev_org_map[sv.system_id] = orgs[0].name

        suggestions = []
        for row in sqs:
            if row['name'] in duplicate_names:
                org_name = dev_org_map.get(row['id'])
                label = f"{row['name']} ({org_name})" if org_name else row['name']
            else:
                label = row['name']
            suggestions.append(label)
    else:
        suggestions = [ ]

    data = json.dumps(suggestions)
    return HttpResponse(data, content_type='application/json')
