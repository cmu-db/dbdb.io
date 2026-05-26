import datetime

from django.conf import settings
from django.db.models import Q
from django.http import HttpResponse
from django.http.response import Http404
from django.shortcuts import redirect, render
from django.urls import reverse
from django.views import View

from lxml import etree

from dbdb.core.models import System, SystemVersion

SITEMAP_NAMESPACE = 'https://www.sitemaps.org/schemas/sitemap/0.9'
SITEMAP_PREFIX = '{%s}' % SITEMAP_NAMESPACE
SITEMAP_NSMAP = {None: SITEMAP_NAMESPACE}


# ==============================================
# EmptyFieldsView
# ==============================================
class EmptyFieldsView(View):

    template_name = 'core/empty-fields.html'

    def build_search_fields(include_citations=False):
        import django.db.models.fields

        IGNORE_TYPES = [
            django.db.models.fields.AutoField,
            django.db.models.fields.related.ForeignKey,
            #django.db.models.fields.related.ManyToManyField,
        ]
        IGNORE_NAMES = [
            "ver",
            "comment",
            "features",
            "created",
            "is_current",
            "systemversion",
        ]

        version_fields = [ ]
        for f in SystemVersion._meta.get_fields():
            if f.name.endswith("_citations") and not include_citations:
                continue

            if type(f) not in IGNORE_TYPES and \
               f.name not in IGNORE_NAMES:
                version_fields.append(f.name)

                # SPECIAL!
                # I want to be able to find all the non-SVG logos
                if f.name == "logo": version_fields.append(f.name + "__SVG")
        ## FOR

        return (version_fields)
    ## DEF

    def get(self, request):
        import django.db.models.fields

        if not request.user.is_authenticated:
            return redirect( settings.LOGIN_URL + '?next=' + reverse('fields') )
        elif not request.user.is_superuser and not request.user.is_staff:
            raise Http404()

        version_fields = EmptyFieldsView.build_search_fields()
        versions = SystemVersion.objects.filter(is_current=True)

        search_field = request.GET.get('field')
        search_reverse = request.GET.get('reverse', False)
        if search_field:
            query = None
            field = None

            if search_field in version_fields:
                # SPECIAL
                if search_field.endswith("__SVG"):
                    field = SystemVersion._meta.get_field(search_field[:-5])
                else:
                    field = SystemVersion._meta.get_field(search_field)
                field_name = field.name
                field_type = type(field)

                # We have to query the different field types a certain way
                if field_type == django.db.models.fields.PositiveIntegerField:
                    query = Q(**{field_name: None})
                elif field_type == django.db.models.fields.related.ManyToManyField:
                    query = Q(**{field_name: None})
                elif search_field.endswith("__SVG"):
                    query = Q(logo__endswith=".svg")
                else:
                    query = Q(**{field_name: ''})

            else:
                raise Exception("Invalid field '%s'" % search_field)

            if search_reverse:
                versions = versions.filter(~query)
            else:
                versions = versions.filter(query)

            # convert query list to regular list
            # and add href/url to each
            versions = list( versions.order_by('system__name') )
            for version in versions:
                version.href = request.build_absolute_uri( version.system.get_absolute_url() )
                if type(field) == django.db.models.fields.related.ManyToManyField:
                    method_handle = getattr(version, search_field + "_str")
                    version.value = method_handle()
                else:
                    version.value = getattr(version, field_name, None)
                pass
        ## IF

        num_systems = System.objects.all().count()
        fields = sorted(version_fields)

        return render(request, self.template_name, {
            'activate': 'empty', # NAV-LINKS
            'versions': versions,
            'field': search_field,
            'reverse': search_reverse,
            'fields': fields,
            'match_percent': "%.1f" % (100 * (len(versions) / num_systems)),
            'num_systems': num_systems,
        })

    pass


# ==============================================
# SitemapView
# ==============================================
class SitemapView(View):

    def get(self, request):
        response = HttpResponse(content_type='text/xml; charset=utf-8')

        root = etree.Element(SITEMAP_PREFIX+'urlset', nsmap=SITEMAP_NSMAP)
        tree = etree.ElementTree(root)

        # Stats Page
        url = etree.SubElement(root, 'url')
        loc = etree.SubElement(url, 'loc')
        loc.text = request.build_absolute_uri( reverse('stats') )
        lastmod = etree.SubElement(url, 'lastmod')
        lastmod.text = datetime.date.today().isoformat()
        changefreq = etree.SubElement(url, 'changefreq')
        changefreq.text = 'weekly'

        # Systems
        for system in System.objects.order_by('name').iterator():
            url = etree.SubElement(root, 'url')
            loc = etree.SubElement(url, 'loc')
            loc.text = request.build_absolute_uri( reverse('system', args=[system.slug]) )
            lastmod = etree.SubElement(url, 'lastmod')
            lastmod.text = system.modified.date().isoformat()
            changefreq = etree.SubElement(url, 'changefreq')
            changefreq.text = 'weekly'
            pass

        tree.write(response, encoding='UTF-8', pretty_print=True, xml_declaration=True)

        return response

    pass