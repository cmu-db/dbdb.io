import json

from django.forms.widgets import Widget
from django.utils.safestring import mark_safe


class CitationUrlListWidget(Widget):
    """
    A widget that displays a scrollable list of URLs with Add/Remove buttons.
    Uses Bootstrap 5.3 styling.
    """

    def render(self, name, value, attrs=None, renderer=None):
        if attrs is None:
            attrs = {}

        # Parse the value (could be JSON string or list)
        if isinstance(value, str):
            try:
                url_list = json.loads(value) if value else []
            except json.JSONDecodeError:
                url_list = []
        elif isinstance(value, list):
            url_list = value
        else:
            url_list = []

        # Generate options HTML
        options_html = ''.join(
            f'<option value="{url}">{url}</option>'
            for url in url_list
        )

        # Create the widget ID
        widget_id = attrs.get('id', f'id_{name}')

        html = f'''
        <div class="url-list-widget" data-field-name="{name}">
            <div class="mb-2">
                <select id="{widget_id}_select" 
                        class="form-select" 
                        size="2"
                        style="height: 4rem; overflow-y: auto;">
                    {options_html}
                </select>
            </div>
            <div class="btn-group" role="group">
                <button type="button" 
                        class="btn btn-sm btn-outline-secondary mt-1" 
                        onclick="addURL_{widget_id}()">
                    + Add URL
                </button>
                <button type="button" 
                        class="btn btn-sm btn-outline-danger mt-1"
                        onclick="removeURL_{widget_id}()">
                    - Remove URL
                </button>
            </div>
            <input type="hidden" 
                   id="{widget_id}" 
                   name="{name}" 
                   value='{json.dumps(url_list)}'>
        </div>

        <script>
        function addURL_{widget_id}() {{
            const url = prompt("Enter a URL:");
            if (url && url.trim()) {{
                const select = document.getElementById('{widget_id}_select');
                const hiddenInput = document.getElementById('{widget_id}');

                // Add to select
                const option = document.createElement('option');
                option.value = url.trim();
                option.text = url.trim();
                select.add(option);

                // Update hidden input
                const urls = Array.from(select.options).map(opt => opt.value);
                hiddenInput.value = JSON.stringify(urls);
            }}
        }}

        function removeURL_{widget_id}() {{
            const select = document.getElementById('{widget_id}_select');
            const hiddenInput = document.getElementById('{widget_id}');
            const selectedIndex = select.selectedIndex;

            if (selectedIndex === -1) {{
                alert("Please select a URL to remove.");
                return;
            }}

            const selectedURL = select.options[selectedIndex].value;
            const confirmed = confirm(`Are you sure you want to remove this URL?\\n\\n${{selectedURL}}`);

            if (confirmed) {{
                select.remove(selectedIndex);

                // Update hidden input
                const urls = Array.from(select.options).map(opt => opt.value);
                hiddenInput.value = JSON.stringify(urls);
            }}
        }}
        </script>
        '''
        return mark_safe(html)

    def value_from_datadict(self, data, files, name):
        """Extract the value from the submitted form data."""
        value = data.get(name, '[]')
        try:
            return json.loads(value) if value else []
        except json.JSONDecodeError:
            return []
