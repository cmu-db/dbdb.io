from django import template
from django.utils.html import mark_safe

register = template.Library()


class SectionNode(template.Node):
    def __init__(self, section_name, nodelist):
        self.section_name = section_name
        self.nodelist = nodelist

    def render(self, context):
        # Rendered by PageTitleNode; direct rendering is a no-op.
        return ''


class PageTitleNode(template.Node):
    def __init__(self, nodelist):
        self.nodelist = nodelist

    def render(self, context):
        sections = {}
        for node in self.nodelist:
            if isinstance(node, SectionNode):
                sections[node.section_name] = node.nodelist.render(context)

        kicker = sections.get('kicker', '').strip()
        title  = sections.get('title',  '').strip()
        sub    = sections.get('sub',    '').strip()
        extra  = sections.get('extra',  '').strip()

        parts = ['<div class="page-title">']
        if kicker:
            parts.append(f'    <p class="kicker">{kicker}</p>')
        if title:
            parts.append(f'    {title}')
        if sub:
            parts.append(f'    <p class="sub">{sub}</p>')
        parts.append('    <hr class="title-rule">')
        if extra:
            parts.append(f'    {extra}')
        parts.append('</div>')
        return mark_safe('\n'.join(parts))


@register.tag('page_title')
def do_page_title(parser, token):
    nodelist = parser.parse(('endpage_title',))
    parser.delete_first_token()
    return PageTitleNode(nodelist)


def _section_tag(section_name):
    end = f'endptitle_{section_name}'

    def tag_fn(parser, token):
        nodelist = parser.parse((end,))
        parser.delete_first_token()
        return SectionNode(section_name, nodelist)

    tag_fn.__name__ = f'do_ptitle_{section_name}'
    return tag_fn


register.tag('ptitle_kicker', _section_tag('kicker'))
register.tag('ptitle_title',  _section_tag('title'))
register.tag('ptitle_sub',    _section_tag('sub'))
register.tag('ptitle_extra',  _section_tag('extra'))
