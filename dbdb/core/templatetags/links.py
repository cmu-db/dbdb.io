from django import template

from dbdb.core.models import AttributeOption, Organization, System

register = template.Library()

@register.inclusion_tag("components/system_link.html")
def system_link(system: System):
    """
    Renders a link for a System
    """
    return {"s": system}

@register.inclusion_tag("components/org_link.html")
def org_link(org: Organization):
    """
    Renders a link for an Organization
    """
    return {"org": org}

@register.inclusion_tag("components/browse_link.html")
def browse_link(key: str, value: str, tooltip: str, label: str = None, icon: str = None):
    """
    Renders a link for a searching something on browse
    """
    return {
        "key": key,
        "value": value,
        "tooltip": tooltip,
        "label": label,
        "icon": icon or "fa-solid fa-table-list",
    }

@register.inclusion_tag("components/tag_link.html")
def tag_link(tag: AttributeOption, extra_classes: str = ''):
    """
    Renders a link for a Tag
    """
    return {
        "tag": tag,
        "extra_classes": extra_classes,
    }