from django import template

from dbdb.core.models import System

register = template.Library()

@register.inclusion_tag("components/system_link.html")
def system_link(system: System):
    """
    Renders a link for a System
    """
    return {"s": system}

@register.inclusion_tag("components/browse_link.html")
def browse_link(key: str, value: str, label: str):
    """
    Renders a link for a System
    """
    return {"key": key, "value": value, "label": label}
