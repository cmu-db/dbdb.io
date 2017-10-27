from django.core.exceptions import ValidationError
from django.forms import ModelForm
from django.forms import fields
from django.forms import widgets
from django.contrib.auth import get_user_model


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