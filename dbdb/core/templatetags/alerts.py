from django import template
from django.utils.html import conditional_escape, mark_safe

register = template.Library()

_ICON_DEFAULTS = {
    'info':    'fa-solid fa-circle-info',
    'warning': 'fa-solid fa-triangle-exclamation',
    'error':   'fa-solid fa-circle-xmark',
    'success': 'fa-solid fa-circle-check',
}


class AlertNode(template.Node):
    def __init__(self, nodelist, alert_type, icon, title, extra_classes, alert_id):
        self.nodelist     = nodelist
        self.alert_type   = alert_type
        self.icon         = icon
        self.title        = title
        self.extra_classes = extra_classes
        self.alert_id     = alert_id

    def _resolve(self, val, context):
        if isinstance(val, template.FilterExpression):
            resolved = val.resolve(context, ignore_failures=True)
            return str(resolved) if resolved is not None else ''
        return val or ''

    def render(self, context):
        content    = self.nodelist.render(context)
        alert_type = self._resolve(self.alert_type, context).lower().strip()
        icon       = self._resolve(self.icon, context)
        title      = self._resolve(self.title, context)
        extra      = self._resolve(self.extra_classes, context)
        alert_id   = self._resolve(self.alert_id, context)

        # Normalise aliases
        if alert_type == 'danger':
            alert_type = 'error'
        elif alert_type in ('debug', ''):
            alert_type = 'info'

        if not icon:
            icon = _ICON_DEFAULTS.get(alert_type, '')

        css_parts = ['page-alert', f'page-alert--{alert_type}']
        if extra:
            css_parts.extend(extra.split())

        attrs = f'class="{" ".join(css_parts)}" role="alert"'
        if alert_id:
            attrs = f'id="{conditional_escape(alert_id)}" {attrs}'

        parts = [f'<div {attrs}>']
        if icon:
            parts.append(
                f'<i class="{conditional_escape(icon)} page-alert-icon" aria-hidden="true"></i>'
            )
        parts.append('<div class="page-alert-body">')
        if title:
            parts.append(f'<strong class="page-alert-title">{conditional_escape(title)}</strong> ')
        parts.append(content.strip())
        parts.append('</div></div>')
        return mark_safe(''.join(parts))


@register.tag('alert')
def do_alert(parser, token):
    """
    Block tag that renders an editorial alert box.

    Keyword arguments (all optional):
      type          – "info" | "warning" | "error" | "success"  (default: "info")
      icon          – FontAwesome class string; omit to use the type default
      title         – Optional bold heading rendered before the block content
      extra_classes – Additional CSS classes on the outer div
      id            – HTML id attribute (useful for JS-controlled hidden alerts)

    Usage::

        {% load alerts %}
        {% alert type="warning" icon="fa-solid fa-clock-rotate-left" title="Heads up" %}
            Content here, may include HTML, template variables, even forms.
        {% endalert %}
    """
    bits = token.split_contents()

    _key_map = {
        'type':          'alert_type',
        'icon':          'icon',
        'title':         'title',
        'extra_classes': 'extra_classes',
        'id':            'alert_id',
    }
    kwargs = {v: '' for v in _key_map.values()}
    kwargs['alert_type'] = 'info'

    for bit in bits[1:]:
        if '=' not in bit:
            continue
        key, _, raw = bit.partition('=')
        dest = _key_map.get(key.strip())
        if dest is None:
            continue
        raw = raw.strip()
        if (raw.startswith('"') and raw.endswith('"')) or \
           (raw.startswith("'") and raw.endswith("'")):
            kwargs[dest] = raw[1:-1]
        else:
            kwargs[dest] = parser.compile_filter(raw)

    nodelist = parser.parse(('endalert',))
    parser.delete_first_token()
    return AlertNode(nodelist, **kwargs)
