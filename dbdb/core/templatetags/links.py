from django import template

from dbdb.core.models import System, Tag

register = template.Library()

@register.inclusion_tag("components/system_link.html")
def system_link(system: System):
    """
    Renders a link for a System
    """
    return {"s": system}

@register.inclusion_tag("components/browse_link.html")
def browse_link(key: str, value: str, tooltip: str, label: str = None):
    """
    Renders a link for a searching something on browse
    """
    return {
        "key": key,
        "value": value,
        "tooltip": tooltip,
        "label": label,
    }

@register.inclusion_tag("components/tag_link.html")
def tag_link(tag: Tag):
    """
    Renders a link for a Tag
    """
    return {"tag": tag}