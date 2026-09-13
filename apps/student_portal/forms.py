from django import forms


class StudentLoginForm(forms.Form):
    email = forms.EmailField(
        label="E-mail",
        widget=forms.EmailInput(
            attrs={"autocomplete": "email", "placeholder": "seuemail@exemplo.com"}
        ),
    )
    password = forms.CharField(
        label="Senha",
        widget=forms.PasswordInput(
            attrs={"autocomplete": "current-password", "placeholder": "Sua senha"}
        ),
    )


class StudentActivationForm(forms.Form):
    email = forms.EmailField(label="E-mail")
    code = forms.CharField(
        label="Código de acesso",
        min_length=6,
        max_length=6,
        widget=forms.TextInput(
            attrs={"inputmode": "numeric", "placeholder": "000000"}
        ),
    )
    password = forms.CharField(
        label="Criar senha",
        min_length=8,
        widget=forms.PasswordInput(),
    )
    password2 = forms.CharField(
        label="Confirmar senha",
        min_length=8,
        widget=forms.PasswordInput(),
    )

    def clean(self):
        data = super().clean()
        if (
            data.get("password")
            and data.get("password2")
            and data["password"] != data["password2"]
        ):
            self.add_error("password2", "As senhas não conferem.")
        return data
