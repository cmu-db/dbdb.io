from django.shortcuts import get_object_or_404, render
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.cache import cache_control

from dbdb.core.models import Attribute, DocPage, Feature


def _sidebar_context():
    features = Feature.objects.order_by('category', 'label').only('slug', 'label', 'category')
    groups = {}
    for f in features:
        groups.setdefault(f.get_category_display(), []).append(f)
    feature_groups = [
        (cat_label, groups[cat_label])
        for _, cat_label in Feature.Category.choices
        if cat_label in groups
    ]
    attributes = list(Attribute.objects.order_by('name').only('slug', 'name'))
    return feature_groups, attributes


# ==============================================
# DocOverviewView
# ==============================================
@method_decorator(cache_control(public=True, max_age=14400), name='dispatch')
class DocOverviewView(View):

    template_name = 'core/docs/overview.html'

    def get(self, request):
        feature_groups, attributes = _sidebar_context()
        feature_count = sum(len(features) for _, features in feature_groups)
        return render(request, self.template_name, {
            'activate': 'docs',
            'feature_groups': feature_groups,
            'attributes': attributes,
            'doc_active': 'home',
            'feature_count': feature_count,
        })


# ==============================================
# DocFeatureView
# ==============================================
@method_decorator(cache_control(public=True, max_age=14400), name='dispatch')
class DocFeatureView(View):

    template_name = 'core/docs/feature.html'

    def get(self, request, slug):
        feature = get_object_or_404(
            Feature.objects.prefetch_related('options', 'options__citations', 'citations'),
            slug=slug,
        )
        feature_groups, attributes = _sidebar_context()
        return render(request, self.template_name, {
            'activate': 'docs',
            'feature': feature,
            'feature_groups': feature_groups,
            'attributes': attributes,
            'doc_active': slug,
        })


# ==============================================
# DocAttributeView
# ==============================================
@method_decorator(cache_control(public=True, max_age=14400), name='dispatch')
class DocAttributeView(View):

    template_name = 'core/docs/attribute.html'

    def get(self, request, slug):
        attribute = get_object_or_404(
            Attribute.objects.prefetch_related('options', 'options__citations', 'citations'),
            slug=slug,
        )
        feature_groups, attributes = _sidebar_context()
        return render(request, self.template_name, {
            'activate': 'docs',
            'attribute': attribute,
            'feature_groups': feature_groups,
            'attributes': attributes,
            'doc_active': slug,
        })


# ==============================================
# DocSysAttrsView
# ==============================================
@method_decorator(cache_control(public=True, max_age=14400), name='dispatch')
class DocSysAttrsView(View):

    template_name = 'core/docs/system-attributes.html'

    def get(self, request):
        page = (DocPage.objects
                .filter(slug='system-attributes')
                .prefetch_related('citations')
                .first())
        fields = (DocPage.objects
                  .filter(parent__slug='system-attributes')
                  .prefetch_related('citations')
                  .order_by('sort_order', 'title'))
        feature_groups, attributes = _sidebar_context()
        return render(request, self.template_name, {
            'activate': 'docs',
            'page': page,
            'fields': fields,
            'feature_groups': feature_groups,
            'attributes': attributes,
            'doc_active': 'sys-attrs',
        })
