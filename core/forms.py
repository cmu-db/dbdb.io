from django.core.exceptions import ValidationError
from django.forms import ModelForm, Form
from django.forms import fields
from django.forms import widgets
from django.contrib.auth import get_user_model
from django.forms.widgets import Textarea

from core.models import SystemVersion, SystemVersionMetadata, FeatureOption
from .models import System, Feature


class CreateUserForm(ModelForm):
    email = fields.EmailField(max_length=254, required=True)
    password = fields.CharField(max_length=128, label='Password', widget=widgets.PasswordInput)
    password2 = fields.CharField(max_length=128, label='Password Confirmation', widget=widgets.PasswordInput)

    def clean_password2(self):
        if self.cleaned_data['password2'] == self.cleaned_data['password']:
            return self.cleaned_data['password2']
        raise ValidationError("The passwords don't match")

    class Meta:
        model = get_user_model()
        fields = ['username', 'email', 'password', 'password2']


class SystemForm(ModelForm):
    class Meta:
        model = System
        fields = ['name']


class SystemVersionForm(ModelForm):
    class Meta:
        model = SystemVersion
        fields = [
            'logo',
            'description',
            'history',
            'website',
            'tech_docs',
            'developer',
            'start_year',
            'end_year',
            'project_type',
        ]


class SystemVersionMetadataForm(ModelForm):
    class Meta:
        model = SystemVersionMetadata
        exclude = ['system']


class SystemFeaturesForm(Form):
    def __init__(self, *args, **kwargs):
        try:
            instance = kwargs.pop('instance')
        except KeyError:
            instance = []
        super(SystemFeaturesForm, self).__init__(*args, **kwargs)
        initial = {}

        for option in instance:
            o = option.value.values_list('value', flat=True)
            if len(o) > 1:
                o = list(o)
            elif len(o) == 1:
                o = o[0]
            else:
                o = None
            initial[option.feature.label] = {
                'options': o,
                'description': option.description
            }

        features = Feature.objects.all()

        for feature in features:
            initial_value = None
            if feature.multivalued:
                if feature.label in initial:
                    initial_value = initial[feature.label]['options']
                self.fields[feature.label] = fields.MultipleChoiceField(
                    choices=(
                        (x, x) for x in FeatureOption.objects.filter(feature=feature)
                    ),
                    initial=initial_value,
                    required=False
                )
            else:
                if feature.label in initial:
                    initial_value = initial[feature.label]['options']
                self.fields[feature.label] = fields.ChoiceField(
                    choices=(
                        (x, x) for x in FeatureOption.objects.filter(feature=feature)
                    ),
                    initial=initial_value,
                    required=False
                )
            if feature.label in initial:
                initial_value = initial[feature.label]['description']
            self.fields[feature.label+'_description'] = fields.CharField(
                help_text="This field supports Markdown Syntax",
                widget=Textarea(),
                initial=initial_value,
                required=False
            )


class AdvancedSearchForm(Form):
    def __init__(self, *args, **kwargs):
        super(AdvancedSearchForm, self).__init__(*args, **kwargs)
        features = Feature.objects.all()

        for feature in features:
            self.fields[feature.label] = fields.MultipleChoiceField(
                choices=(
                    (x, x) for x in FeatureOption.objects.filter(feature=feature)
                ), required=False
            )