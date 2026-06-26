from django import template

register = template.Library()


@register.inclusion_tag("components/system_logo.html")
def system_logo(version, system):
    """
    Renders the factbox logo block for a SystemVersion.

    When a logo exists: wraps it in a link to the logos page and shows a
    "Logo Versions" link below, sizing the image with logo-tall/logo-normal
    based on aspect ratio.
    When no logo: falls back to the mono-tile initials box.
    """
    logo = version.logo
    logo_url = None
    is_svg = False
    is_tall = False
    if logo:
        logo_url = logo.url
        is_svg = logo_url.lower().endswith('.svg')
        h = getattr(version, 'logo_height', 0) or 0
        w = getattr(version, 'logo_width', 0) or 0
        is_tall = h > w
    return {
        'logo': logo,
        'logo_url': logo_url,
        'is_svg': is_svg,
        'is_tall': is_tall,
        'system': system,
        'version': version,
    }


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
