from django.forms import HiddenInput, ModelForm
from models import SystemVersion

# DEFINE FIELDS IN THE ORDER THEY SHOULD APPEAR IN THE FRONT END.

# Hidden fields
hidden = [
    'system',
    'version_number',
    'current',
    'creator'
]

# Basic data on database
basic_data = [
    'version_message',
    'description',
    'history',
    'logo_orig',
    'website',
    'tech_docs',
    'developer',
    'start_year',
    'end_year'
]

# Additional data related to models
models = [
    'project_type',
    'written_in',
    'supported_languages',
    'oses',
    'licenses',
    'derived_from'
]

# Database features
features = ['support_systemarchitecture', 'options_systemarchitecture', 'description_systemarchitecture',
            'support_datamodel', 'options_datamodel', 'description_datamodel',
            'support_storagemodel', 'options_storagemodel', 'description_storagemodel',
            'support_queryinterface', 'options_queryinterface', 'description_queryinterface',
            'support_storagearchitecture', 'options_storagearchitecture', 'description_storagearchitecture',
            'support_concurrencycontrol', 'options_concurrencycontrol', 'description_concurrencycontrol',
            'support_isolationlevels', 'options_isolationlevels', 'description_isolationlevels',
            'support_indexes', 'options_indexes', 'description_indexes',
            'support_foreignkeys', 'options_foreignkeys', 'description_foreignkeys',
            'support_logging', 'options_logging', 'description_logging',
            'support_checkpoints', 'options_checkpoints', 'description_checkpoints',
            'support_views', 'options_views', 'description_views',
            'support_queryexecution', 'options_queryexecution', 'description_queryexecution',
            'support_storedprocedures', 'options_storedprocedures', 'description_storedprocedures',
            'support_joins', 'options_joins', 'description_joins',
            'support_querycompilation', 'options_querycompilation', 'description_querycompilation',
            'support_accessmethods', 'options_accessmethods', 'description_accessmethods']


class SystemVersionForm(ModelForm):
    class Meta:
        model = SystemVersion
        fields = []
        fields.extend(hidden)
        fields.extend(basic_data)
        fields.extend(models)
        fields.extend(features)

        widgets = {}
        for field in hidden:
            widgets[field] = HiddenInput()