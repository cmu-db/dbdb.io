from django import template
from django.template.loader import render_to_string
from django.utils.safestring import mark_safe

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


@register.simple_tag
def markdownify_with_cites(text: str, citations: list[int]) -> str:
    """
    Render *text* through markdownify and inject citation footnotes before
    the closing </p> of the last paragraph so they sit inline with the prose.
    """
    from markdownify.templatetags.markdownify import markdownify as md_filter
    html = md_filter(text)
    if not citations:
        return html
    links = ''.join(render_to_string("components/citation_footnote.html", {"number": n}) for n in citations)
    cites_html = f'<span class="cites">{links}</span>'
    last_p = html.rfind('</p>')
    if last_p != -1:
        html = html[:last_p] + cites_html + html[last_p:]
    else:
        html = html + cites_html
    return mark_safe(html)
