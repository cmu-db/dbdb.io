import html as html_lib
import json

from django.forms.widgets import Widget
from django.utils.safestring import mark_safe


class CitationUrlListWidget(Widget):
    """
    Renders citation URLs as individual input rows with Add / Remove buttons.
    All interactivity is handled by generic JS in system-edit.html — no inline
    <script> tags are emitted.

    Form submission: a hidden <input type="hidden"> carries the JSON array so
    CitationUrlListField.value_from_datadict() is unchanged.
    """

    def render(self, name, value, attrs=None, renderer=None):
        if attrs is None:
            attrs = {}

        if isinstance(value, str):
            try:
                url_list = json.loads(value) if value else []
            except json.JSONDecodeError:
                url_list = []
        elif isinstance(value, list):
            url_list = value
        else:
            url_list = []

        widget_id = attrs.get('id', f'id_{name}')

        rows_html = ''.join(
            '<div class="citation-url-row row g-2 mb-1 align-items-center">'
            '<div class="col">'
            f'<input type="text" class="form-control citation-url-input" value="{html_lib.escape(url)}" placeholder="https://…">'
            '</div>'
            '<div class="col-auto">'
            '<button type="button" class="btn-row-remove" onclick="removeCitationRow(this)"><i class="fa-solid fa-circle-xmark"></i></button>'
            '</div>'
            '</div>'
            for url in url_list
        )

        html = (
            f'<div class="citation-url-list-widget" data-hidden-id="{widget_id}">'
            f'<div class="citation-url-rows">{rows_html}</div>'
            f'<button type="button" class="btn btn-sm btn-outline-secondary mt-1" onclick="addCitationRow(this)">+ Add URL</button>'
            f'<input type="hidden" id="{widget_id}" name="{name}" value="{html_lib.escape(json.dumps(url_list))}">'
            f'</div>'
        )
        return mark_safe(html)

    def value_from_datadict(self, data, files, name):
        value = data.get(name, '[]')
        try:
            return json.loads(value) if value else []
        except json.JSONDecodeError:
            return []
