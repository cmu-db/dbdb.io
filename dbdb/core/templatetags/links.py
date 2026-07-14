from types import SimpleNamespace
from urllib.parse import unquote
from django import template
from django.conf import settings as django_settings

from dbdb.core.models import AttributeOption, Organization, OrgType, System

register = template.Library()

@register.inclusion_tag("components/system-link.html")
def system_link(system: System):
    """
    Renders a link for a System
    """
    return {"s": system}

@register.inclusion_tag("components/org-link.html")
def org_link(org):
    """
    Renders a link for an Organization (accepts model instance or dict from JSONBAgg).
    """
    if isinstance(org, dict):
        org_type_int = org.get('org_type')
        org = SimpleNamespace(
            name=org['name'],
            slug=org['slug'],
            org_type_obj=OrgType(org_type_int) if org_type_int is not None else None,
        )
    return {"org": org}

@register.inclusion_tag("components/browse-link.html")
def browse_link(key: str, value: str, tooltip: str, label: str = '', icon: str = ''):
    """
    Renders a link for a searching something on browse
    """
    return {
        "key": key,
        "value": value,
        "tooltip": tooltip,
        "label": label,
        "icon": icon or "fa-solid fa-list",
    }

@register.inclusion_tag("components/tag-link.html")
def tag_link(tag: AttributeOption, extra_classes: str = ''):
    """
    Renders a link for a Tag
    """
    return {
        "tag": tag,
        "extra_classes": extra_classes,
    }

@register.filter
def urldecode(value):
    return unquote(value) if value else value


@register.inclusion_tag("components/last-modified.html")
def last_modified(timestamp, url=None, title=None, ver=None):
    return {
        'timestamp': timestamp,
        'url': url,
        'title': title,
        'ver': ver,
        'datetime_format': getattr(django_settings, 'DBDB_SV_DATETIME_FORMAT', 'Y-m-d H:i'),
    }