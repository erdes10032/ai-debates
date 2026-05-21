from allauth.account.forms import SignupForm
from django import forms
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

User = get_user_model()


class CustomFileInput(forms.ClearableFileInput):
    template_name = 'widgets/custom_file_input.html'


class CustomSignupForm(SignupForm):

    username = forms.CharField(
        max_length=150,
        label=_('Username'),
        widget=forms.TextInput(
            attrs={
                'class': 'input',
            }
        ),
    )

    email = forms.EmailField(
        label=_('Email'),
        widget=forms.EmailInput(
            attrs={
                'class': 'input',
            }
        ),
    )

    gender = forms.ChoiceField(
        choices=User.Gender.choices,
        label=_('Gender'),
        widget=forms.Select(
            attrs={
                'class': 'input',
            }
        ),
    )

    avatar = forms.ImageField(
        required=False,
        label=_('Avatar'),
        widget=CustomFileInput(
            attrs={
                'class': 'input',
                'accept': '.jpg,.jpeg,.png,.webp',
            }
        ),
    )

    bio = forms.CharField(
        required=False,
        label=_('Bio'),
        widget=forms.Textarea(
            attrs={
                'class': 'textarea',
                'rows': 4,
            }
        ),
    )

    def clean_email(self):
        email = self.cleaned_data['email'].lower()

        if User.objects.filter(email=email).exists():
            raise ValidationError(
                _('A user with this email already exists.')
            )

        return email

    def save(self, request):
        user = super().save(request)

        user.username = self.cleaned_data['username']
        user.email = self.cleaned_data['email']
        user.gender = self.cleaned_data['gender']
        user.bio = self.cleaned_data['bio']

        avatar = self.cleaned_data.get('avatar')

        if avatar:
            user.avatar = avatar

        user.save()

        return user


class UserUpdateForm(forms.ModelForm):

    class Meta:
        model = User

        fields = [
            'username',
            'gender',
            'avatar',
            'bio',
        ]

        widgets = {
            'username': forms.TextInput(
                attrs={
                    'class': 'input',
                }
            ),

            'gender': forms.Select(
                attrs={
                    'class': 'input',
                }
            ),

            'avatar': CustomFileInput(
                attrs={
                    'class': 'input',
                    'accept': '.jpg,.jpeg,.png,.webp',
                }
            ),

            'bio': forms.Textarea(
                attrs={
                    'class': 'textarea',
                    'rows': 4,
                }
            ),
        }