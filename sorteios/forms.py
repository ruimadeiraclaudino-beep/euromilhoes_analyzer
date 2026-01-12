"""
Formularios para a aplicacao EuroMilhoes Analyzer.
"""
from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator, MaxValueValidator

from .models import UserProfile, Alerta


class LoginForm(AuthenticationForm):
    """Formulario de login personalizado."""
    username = forms.CharField(
        label="Nome de utilizador",
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Nome de utilizador',
            'autofocus': True,
        })
    )
    password = forms.CharField(
        label="Password",
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Password',
        })
    )


class RegisterForm(UserCreationForm):
    """Formulario de registo de novo utilizador."""
    email = forms.EmailField(
        label="Email",
        required=True,
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'email@exemplo.com',
        })
    )

    class Meta:
        model = User
        fields = ['username', 'email', 'password1', 'password2']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['username'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'Nome de utilizador',
        })
        self.fields['password1'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'Password',
        })
        self.fields['password2'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'Confirmar password',
        })

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data['email']
        if commit:
            user.save()
            # Criar perfil automaticamente
            UserProfile.objects.create(user=user, email_alertas=user.email)
        return user


class ProfileForm(forms.ModelForm):
    """Formulario de edicao do perfil."""
    first_name = forms.CharField(
        label="Nome",
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    last_name = forms.CharField(
        label="Apelido",
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    email = forms.EmailField(
        label="Email",
        required=True,
        widget=forms.EmailInput(attrs={'class': 'form-control'})
    )

    class Meta:
        model = UserProfile
        fields = ['alertas_ativos', 'email_alertas']
        widgets = {
            'alertas_ativos': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'email_alertas': forms.EmailInput(attrs={'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.user:
            self.fields['first_name'].initial = self.instance.user.first_name
            self.fields['last_name'].initial = self.instance.user.last_name
            self.fields['email'].initial = self.instance.user.email

    def save(self, commit=True):
        profile = super().save(commit=False)
        if commit:
            # Atualizar dados do User
            user = profile.user
            user.first_name = self.cleaned_data['first_name']
            user.last_name = self.cleaned_data['last_name']
            user.email = self.cleaned_data['email']
            user.save()
            profile.save()
        return profile


class NumerosFavoritosForm(forms.Form):
    """Formulario para selecionar numeros e estrelas favoritos."""
    numeros = forms.CharField(
        label="Numeros Favoritos (1-50)",
        help_text="Introduza ate 5 numeros separados por virgula (ex: 7, 23, 35, 42, 49)",
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': '7, 23, 35, 42, 49',
        })
    )
    estrelas = forms.CharField(
        label="Estrelas Favoritas (1-12)",
        help_text="Introduza ate 2 estrelas separadas por virgula (ex: 3, 9)",
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': '3, 9',
        })
    )

    def clean_numeros(self):
        data = self.cleaned_data['numeros']
        try:
            numeros = [int(n.strip()) for n in data.split(',') if n.strip()]
        except ValueError:
            raise forms.ValidationError("Introduza apenas numeros separados por virgula.")

        if len(numeros) > 10:
            raise forms.ValidationError("Maximo de 10 numeros.")

        for n in numeros:
            if n < 1 or n > 50:
                raise forms.ValidationError(f"O numero {n} deve estar entre 1 e 50.")

        if len(numeros) != len(set(numeros)):
            raise forms.ValidationError("Nao pode repetir numeros.")

        return sorted(numeros)

    def clean_estrelas(self):
        data = self.cleaned_data['estrelas']
        try:
            estrelas = [int(e.strip()) for e in data.split(',') if e.strip()]
        except ValueError:
            raise forms.ValidationError("Introduza apenas numeros separados por virgula.")

        if len(estrelas) > 5:
            raise forms.ValidationError("Maximo de 5 estrelas.")

        for e in estrelas:
            if e < 1 or e > 12:
                raise forms.ValidationError(f"A estrela {e} deve estar entre 1 e 12.")

        if len(estrelas) != len(set(estrelas)):
            raise forms.ValidationError("Nao pode repetir estrelas.")

        return sorted(estrelas)


class AlertaForm(forms.ModelForm):
    """Formulario para criar/editar alertas."""

    class Meta:
        model = Alerta
        fields = ['tipo', 'ativo']
        widgets = {
            'tipo': forms.Select(attrs={'class': 'form-select'}),
            'ativo': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    # Campos dinamicos baseados no tipo
    numero = forms.IntegerField(
        required=False,
        min_value=1,
        max_value=50,
        widget=forms.NumberInput(attrs={'class': 'form-control'})
    )
    estrela = forms.IntegerField(
        required=False,
        min_value=1,
        max_value=12,
        widget=forms.NumberInput(attrs={'class': 'form-control'})
    )
    dias = forms.IntegerField(
        required=False,
        min_value=1,
        max_value=365,
        widget=forms.NumberInput(attrs={'class': 'form-control'})
    )
    valor_jackpot = forms.IntegerField(
        required=False,
        min_value=1000000,
        widget=forms.NumberInput(attrs={'class': 'form-control'})
    )

    def clean(self):
        cleaned_data = super().clean()
        tipo = cleaned_data.get('tipo')

        parametros = {}

        if tipo == 'numero_atrasado':
            numero = cleaned_data.get('numero')
            dias = cleaned_data.get('dias')
            if not numero:
                raise forms.ValidationError("Selecione um numero.")
            if not dias:
                raise forms.ValidationError("Indique o numero de dias.")
            parametros = {'numero': numero, 'dias': dias}

        elif tipo == 'jackpot_alto':
            valor = cleaned_data.get('valor_jackpot')
            if not valor:
                raise forms.ValidationError("Indique o valor do jackpot.")
            parametros = {'valor': valor}

        elif tipo == 'numero_saiu':
            numero = cleaned_data.get('numero')
            if not numero:
                raise forms.ValidationError("Selecione um numero.")
            parametros = {'numero': numero}

        elif tipo == 'estrela_saiu':
            estrela = cleaned_data.get('estrela')
            if not estrela:
                raise forms.ValidationError("Selecione uma estrela.")
            parametros = {'estrela': estrela}

        cleaned_data['parametros'] = parametros
        return cleaned_data

    def save(self, commit=True):
        alerta = super().save(commit=False)
        alerta.parametros = self.cleaned_data.get('parametros', {})
        if commit:
            alerta.save()
        return alerta


class VerificadorApostaForm(forms.Form):
    """Formulario para verificar uma aposta."""
    numero_1 = forms.IntegerField(
        min_value=1, max_value=50,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'placeholder': '1-50'})
    )
    numero_2 = forms.IntegerField(
        min_value=1, max_value=50,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'placeholder': '1-50'})
    )
    numero_3 = forms.IntegerField(
        min_value=1, max_value=50,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'placeholder': '1-50'})
    )
    numero_4 = forms.IntegerField(
        min_value=1, max_value=50,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'placeholder': '1-50'})
    )
    numero_5 = forms.IntegerField(
        min_value=1, max_value=50,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'placeholder': '1-50'})
    )
    estrela_1 = forms.IntegerField(
        min_value=1, max_value=12,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'placeholder': '1-12'})
    )
    estrela_2 = forms.IntegerField(
        min_value=1, max_value=12,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'placeholder': '1-12'})
    )

    def clean(self):
        cleaned_data = super().clean()

        numeros = [
            cleaned_data.get('numero_1'),
            cleaned_data.get('numero_2'),
            cleaned_data.get('numero_3'),
            cleaned_data.get('numero_4'),
            cleaned_data.get('numero_5'),
        ]
        numeros = [n for n in numeros if n is not None]

        if len(numeros) != len(set(numeros)):
            raise forms.ValidationError("Os numeros nao podem ser repetidos.")

        estrelas = [
            cleaned_data.get('estrela_1'),
            cleaned_data.get('estrela_2'),
        ]
        estrelas = [e for e in estrelas if e is not None]

        if len(estrelas) != len(set(estrelas)):
            raise forms.ValidationError("As estrelas nao podem ser repetidas.")

        cleaned_data['numeros'] = sorted(numeros)
        cleaned_data['estrelas'] = sorted(estrelas)

        return cleaned_data
