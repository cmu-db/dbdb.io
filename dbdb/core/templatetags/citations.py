from django import template

register = template.Library()

@register.inclusion_tag("components/citation_link.html")
def citation_link(number    ):
    """
    Renders a citation <a> tag given a citation number
    """
    return {"number": number}
