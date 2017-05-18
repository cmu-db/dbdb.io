from django.forms import ModelForm, Select, SelectMultiple, Textarea
from models import SystemVersion

features = []
for feature in SystemVersion().get_features():
    features.append('support_' + feature['field'])
    features.append('description_' + feature['field'])

models = [
    'project_type',
    'written_in',
    'support_languages',
    'oses',
    'licenses',
    'derived_from'
]


class SystemVersionForm(ModelForm):
    class Meta:
        model = SystemVersion

        fields = [
            'version_message',
            'description',
            'history',
            'logo_orig',
            'website',
            'tech_docs',
            'developer',
            'start_year',
            'end_year',
        ]
        fields.extend(models)
        fields.extend(features)

        widgets = {
            'description': Textarea(attrs={'data-provide': 'markdown', 'rows': '6'}),
            'history': Textarea(attrs={'data-provide': 'markdown', 'rows': '6'})
        }

        for m in models:
            widgets[m] = SelectMultiple(attrs={'class': 'selectpicker', 'data-live-search': 'true', 'data-size': '10'})
        widgets['project_type'] = Select(attrs={'class': 'selectpicker', 'data-live-search': 'true', 'data-size': '10'})

        for feature in features:
            if 'description_' in feature:
                widgets[feature] = Textarea(attrs={'data-provide': 'markdown', 'rows': '6'})
