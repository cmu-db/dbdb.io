from django import template

register = template.Library()


@register.filter
def strftime(dt, fmt):
    if not dt:
        return ''
    return dt.strftime(fmt)
