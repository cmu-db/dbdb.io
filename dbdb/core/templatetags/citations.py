from django import template

from dbdb.core.models import CitationUrl

register = template.Library()

@register.inclusion_tag("components/citation_footnote.html")
def citation_footnote(number: int):
    """
    Renders a citation footnote <a> tag given a citation number
    """
    return {"number": number}

@register.inclusion_tag("components/citation_link.html")
def citation_link(citation: CitationUrl):
    """
    Renders a citation link for a CitationUrl
    """
    return {"c": citation, "Status": CitationUrl.Status}
