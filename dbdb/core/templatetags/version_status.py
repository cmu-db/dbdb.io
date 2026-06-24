from django import template
from django.utils.safestring import mark_safe

register = template.Library()


@register.simple_tag
def ver_status(approved, is_current=False):
    """
    Renders a unified version-status badge.
    approved=False → Pending  (amber)
    approved=True, is_current=True  → Live       (green)
    approved=True, is_current=False → Superseded (muted)
    """
    if not approved:
        return mark_safe('<span class="status pending align-middle">Pending</span>')
    if is_current:
        return mark_safe('<span class="status live align-middle">Live</span>')
    return mark_safe('<span class="status super align-middle">Superseded</span>')
