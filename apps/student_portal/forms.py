from django import forms
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError


class StudentLoginForm(forms.Form):
    email = forms.EmailField(
        label="E-mail",
        widget=forms.EmailInput(
            attrs={
                "autocomplete": "email",
                "placeholder": "seuemail@exemplo.com",
            }
        ),
    )
    password = forms.CharField(
        label="Senha",
        widget=forms.PasswordInput(
            attrs={
                "autocomplete": "current-password",
                "placeholder": "Sua senha",
            }
        ),
    )


class StudentActivationForm(forms.Form):
    email = forms.EmailField(label="E-mail")
    code = forms.CharField(
        label="Código de acesso",
        min_length=6,
        max_length=6,
        widget=forms.TextInput(
            attrs={
                "inputmode": "numeric",
                "autocomplete": "one-time-code",
                "placeholder": "000000",
            }
        ),
    )
    password = forms.CharField(
        label="Criar senha",
        min_length=8,
        widget=forms.PasswordInput(
            attrs={"autocomplete": "new-password"}
        ),
    )
    password2 = forms.CharField(
        label="Confirmar senha",
        min_length=8,
        widget=forms.PasswordInput(
            attrs={"autocomplete": "new-password"}
        ),
    )

    def clean(self):
        data = super().clean()

        password = data.get("password")
        password2 = data.get("password2")

        if password and password2 and password != password2:
            self.add_error(
                "password2",
                "As senhas não conferem.",
            )

        if password:
            try:
                validate_password(password)
            except ValidationError as exc:
                self.add_error("password", exc)

        return data
