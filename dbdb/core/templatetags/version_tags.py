from django import template
from django.conf import settings
from django.template.defaultfilters import date as date_filter
from django.utils.html import format_html

register = template.Library()


@register.simple_tag
def sv_created(version):
    """Render SystemVersion.created as a <time> element with clock icon."""
    fmt = getattr(settings, 'DBDB_SV_DATETIME_FORMAT', 'Y-m-d H:i')
    return format_html(
        '<time datetime="{}"><i class="fa-solid fa-clock-rotate-left"></i> {}</time>',
        date_filter(version.created, 'c'),
        date_filter(version.created, fmt),
    )


@register.simple_tag
def sv_ver(ver):
    """Render a SystemVersion.ver number as a styled ver-tag badge."""
    return format_html('<span class="ver-tag">#{}</span>', ver)
