# stdlib imports
# django imports
import json

# from django.forms.fields import MultipleChoiceField
# from django.forms.widgets import Textarea
# third-party imports
from captcha.fields import ReCaptchaField
from captcha.widgets import ReCaptchaV2Invisible
from django import forms
from turnstile.fields import TurnstileField
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.validators import URLValidator
from django.forms import formset_factory, widgets

# project imports
from dbdb.core.models import CitationUrl, Feature, FeatureOption, System, SystemVersion
from dbdb.core.utils import citations
from dbdb.core.widgets import CitationUrlListWidget


class CitationUrlListField(forms.Field):
    """
    A form field that accepts a list of URLs.
    Each URL is validated individually.
    """
    widget = CitationUrlListWidget

    def __init__(self, *args, **kwargs):
        self.max_urls = kwargs.pop('max_urls', None)
        super().__init__(*args, **kwargs)
        self.url_validator = URLValidator()

    def to_python(self, value):
        """Normalize data to a list of URL strings."""
        if not value:
            return []

        if isinstance(value, list):
            return value

        if isinstance(value, str):
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                raise ValidationError("Invalid URL list format.")

        return []

    def validate(self, value):
        """Check if value consists of valid URLs."""
        super().validate(value)

        if not value and self.required:
            raise ValidationError("This field is required.")

        if self.max_urls and len(value) > self.max_urls:
            raise ValidationError(
                f"You can only enter up to {self.max_urls} URLs."
            )

        # Validate each URL
        for url in value:
            try:
                self.url_validator(url)
            except ValidationError:
                raise ValidationError(f"Invalid URL: {url}")

    def prepare_value(self, value):
        """Prepare value for display in the widget."""
        if value is not None:
            return json.dumps([c.url for c in value])
        return []

    def clean(self, value):
        url_objs = []
        for url in map(citations.normalize_url, value):
            cit_url, _ = CitationUrl.objects.get_or_create(url=url)
            url_objs.append(cit_url)
        return url_objs


class SystemFeaturesForm(forms.Form):

    def __init__(self, *args, **kwargs):
        try:
            self.system = kwargs.pop('system')
            features = kwargs.pop('features')
        except KeyError:
            features = []

        super().__init__(*args, **kwargs)

        initial = {}

        for feature in features:
            o = feature.options.values_list('value', flat=True)
            if len(o) > 1:
                o = list(o)
            elif len(o) == 1:
                o = o[0]
            else:
                o = None
            initial[feature.feature.label] = {
                'options': o,
                'description': feature.description,
                'citations': [c for c in feature.citations.all()],
                'system': feature.system,
            }
            pass

        features = Feature.objects.all()

        self.features = []
        for feature in features:
            field_prefix = feature.get_sanitized_label()
            initial_value = None
            if feature.multivalued:
                if feature.label in initial:
                    initial_value = initial[feature.label]['options']
                self.fields[f'{field_prefix}_choices'] = forms.MultipleChoiceField(
                    choices=(
                        (x, x) for x in FeatureOption.objects.filter(feature=feature).order_by('value')
                    ),
                    initial=initial_value,
                    required=False
                )
                pass
            else:
                if feature.label in initial:
                    initial_value = initial[feature.label]['options']
                self.fields[f'{field_prefix}_choices'] = forms.ChoiceField(
                    choices=(
                        (x, x) for x in FeatureOption.objects.filter(feature=feature).order_by('value')
                    ),
                    initial=initial_value,
                    required=False
                )
                pass

            initial_desc = None
            initial_cit = None
            initial_sys = None
            if feature.label in initial:
                initial_desc = initial[feature.label]['description']
                initial_cit = initial[feature.label]['citations']
                initial_sys = initial[feature.label]['system']
                pass

            self.fields[f'{field_prefix}_description'] = forms.CharField(
                label='Description',
                help_text="This field supports Markdown Syntax",
                widget=widgets.Textarea(),
                initial=initial_desc,
                required=False
            )

            self.fields[f'{field_prefix}_citations'] = CitationUrlListField(
                label='Citations',
                help_text="Citations URLs",
                initial=initial_cit,
                required=False
            )

            all_systems = [(x.id, x.name) for x in System.objects.exclude(id=self.system.id).order_by('name')]
            derived_ids = set(
                self.system.current().derived_from.values_list('id', flat=True)
            ) if self.system.id else set()
            derived  = [(id_, name) for id_, name in all_systems if id_ in derived_ids]
            others   = [(id_, name) for id_, name in all_systems if id_ not in derived_ids]
            systems  = [(None, '')] + derived + ([('', '─────────')] if derived else []) + others
            self.fields[f'{field_prefix}_system'] = forms.ChoiceField(
                    label='Inherited from System',
                    help_text="Whether this system inherits the capabilities from another system.",
                    choices=systems,
                    initial=initial_sys.id if initial_sys else None,
                    widget=forms.Select(attrs={'onchange': f"toggleFields('{feature.label}')", 'class': 'form-select'}),
                    required=False
                )

            self.fields[f'{field_prefix}_system'].feature_id = feature.id
            self.fields[f'{field_prefix}_choices'].feature_id = feature.id
            self.fields[f'{field_prefix}_description'].feature_id = feature.id
            self.fields[f'{field_prefix}_citations'].feature_id = feature.id
            pass
        return

    pass


# model forms

class CreateUserForm(forms.ModelForm):

    email = forms.EmailField(max_length=254, required=True)
    password = forms.CharField(max_length=128, label='Password', widget=widgets.PasswordInput)
    password2 = forms.CharField(max_length=128, label='Password Confirmation', widget=widgets.PasswordInput)

    captcha = ReCaptchaField(
        widget=ReCaptchaV2Invisible(
            attrs={
                'data-callback': 'onCaptchaSubmit',  # name of JavaScript callback function
                'bind': 'btn_submit'  # submit button's ID in the form template
            }
        )
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.initial_email = None

        initial = getattr(self, 'initial', None)
        if initial and 'email' in initial and initial['email']:
            self.initial_email = initial['email']
            self.fields['email'].widget.attrs['readonly'] = True
            pass

        return

    def clean_email(self):
        if self.initial_email:
            return self.initial_email
        return self.cleaned_data['email']

    def clean_password2(self):
        if self.cleaned_data['password2'] == self.cleaned_data['password']:
            return self.cleaned_data['password2']
        raise ValidationError("The passwords do not match")

    class Meta:
        model = get_user_model()
        fields = ['username', 'email', 'password', 'password2', 'captcha']

    pass

class SystemForm(forms.ModelForm):

    # This is only shown to non-superusers
    orig_name = forms.CharField(max_length=128, label="Name", disabled=True, required=False)

    class Meta:
        model = System
        fields = ['name', 'orig_name', 'slug']

    def clean_slug(self):
        slug = self.cleaned_data.get('slug', '').strip()
        if slug:
            qs = System.objects.filter(slug=slug)
            if self.instance and self.instance.pk:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise forms.ValidationError(f"A system with slug '{slug}' already exists.")
        return slug

class SystemVersionForm(forms.ModelForm):

    description_citations = CitationUrlListField(
        help_text="Citations URLs",
        required=False
    )
    history_citations = CitationUrlListField(
        help_text="Citations URLs",
        required=False
    )
    start_year_citations = CitationUrlListField(
        help_text="Citations URLs",
        required=False
    )
    end_year_citations = CitationUrlListField(
        help_text="Citations URLs",
        required=False
    )

    # CitationUrl FK fields — rendered as URL inputs; view handles get_or_create
    system_url = forms.URLField(
        required=False, label='Website URL',
        widget=forms.URLInput(attrs={'class': 'form-control'}))
    docs_url = forms.URLField(
        required=False, label='Tech Docs URL',
        widget=forms.URLInput(attrs={'class': 'form-control'}))
    sourcerepo_url = forms.URLField(
        required=False, label='Source Code URL',
        widget=forms.URLInput(attrs={'class': 'form-control'}))
    wikipedia_url = forms.URLField(
        required=False, label='Wikipedia URL',
        widget=forms.URLInput(attrs={'class': 'form-control'}))
    linkedin_url = forms.URLField(
        required=False, label='LinkedIn URL',
        widget=forms.URLInput(attrs={'class': 'form-control'}))

    def clean_twitter_handle(self):
        data = self.cleaned_data['twitter_handle']
        if data and data[0] != '@':
            raise ValidationError("Invalid Twitter handle. Expected to start with '@' character")
        return data

    class Meta:
        model = SystemVersion
        fields = [
            'logo',
            'description',
            'description_citations',
            'history',
            'history_citations',
            'twitter_handle',
            'start_year',
            'start_year_citations',
            'end_year',
            'end_year_citations',
            'tags',
            'governance',
            'project_types',
            'countries',
            'former_names',
            'derived_from',
            'embedded',
            'inspired_by',
            'compatible_with',
            'hosted_services',
            'licenses',
            'oses',
            'supported_languages',
            'written_in',
            'comment',
        ]

    pass


class AcquisitionForm(forms.Form):
    organization = forms.CharField(
        max_length=200, required=False,
        label='Acquired By',
        widget=forms.TextInput(attrs={'placeholder': 'Organization name', 'class': 'form-control'}))
    year = forms.IntegerField(
        required=False, min_value=1800, max_value=2200,
        label='Year',
        widget=forms.NumberInput(attrs={'placeholder': 'Year', 'class': 'form-control'}))
    citation_url = forms.URLField(
        max_length=500, required=False,
        label='Citation URL',
        widget=forms.URLInput(attrs={'placeholder': 'https://…', 'class': 'form-control'}))

    def has_data(self):
        return bool(self.cleaned_data.get('organization'))


AcquisitionFormSet = formset_factory(AcquisitionForm, extra=0, can_delete=True)


class SystemSuggestionForm(forms.Form):

    name = forms.CharField(
        max_length=100,
        label='System Name',
        widget=forms.TextInput(attrs={'placeholder': 'e.g. CockroachDB'}),
    )
    system_url = forms.URLField(
        max_length=500,
        label='System URL',
        widget=forms.URLInput(attrs={'placeholder': 'https://www.example.com'}),
    )
    sourcerepo_url = forms.URLField(
        max_length=500,
        required=False,
        label='Source Code URL',
        widget=forms.URLInput(attrs={'placeholder': 'https://github.com/org/project'}),
    )
    logo_url = forms.URLField(
        max_length=500,
        required=False,
        label='Logo Image URL',
        widget=forms.URLInput(attrs={'placeholder': 'https://www.example.com/logo.png'}),
    )
    is_my_system = forms.BooleanField(
        required=False,
        label='This is my system and I want to edit the entry',
    )
    email = forms.EmailField(
        max_length=100,
        required=False,
        label='Your Email',
        widget=forms.EmailInput(attrs={'placeholder': 'you@example.edu'}),
    )
    captcha = TurnstileField()

    def clean(self):
        cleaned = super().clean()
        if cleaned.get('is_my_system') and not cleaned.get('email'):
            self.add_error('email', 'Email is required when you want to edit the entry.')
        return cleaned


class DeveloperOrgForm(forms.Form):
    organization = forms.CharField(
        max_length=200, required=False,
        label='Developer Organization',
        widget=forms.TextInput(attrs={'placeholder': 'Organization name', 'class': 'form-control'}))


DeveloperOrgFormSet = formset_factory(DeveloperOrgForm, extra=0, can_delete=True)

