from django import template

register = template.Library()


@register.inclusion_tag("components/mono_tile.html")
def mono_tile(logo, name:str, alias:str='thumb', extra_classes:str='', lazy:bool=True):
    """
    Renders a mono-tile box containing either a system logo image or the
    system's initial letter as a fallback.

    logo         – ThumbnailerFieldFile or raw string path (from .values())
    name         – Display name; first letter used as fallback initial
    alias        – easy-thumbnails alias for resizing (default: 'thumb')
    extra_classes – Additional CSS classes appended to the outer <span>
    lazy         – Whether to add loading="lazy" to the <img> tag
    """
    logo_url = None
    is_svg = False
    if logo:
        try:
            logo_url = logo.url                 # ThumbnailerFieldFile
        except AttributeError:
            logo_url = f'/media/{logo}'         # raw string from .values()
        is_svg = logo_url.lower().endswith('.svg')
    return {
        'logo': logo,
        'logo_url': logo_url,
        'is_svg': is_svg,
        'name': name,
        'alias': alias,
        'extra_classes': extra_classes,
        'lazy': lazy,
    }
