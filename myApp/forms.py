from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User


class CustomUserCreationForm(UserCreationForm):
    """Custom signup form with email field"""
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={
            'class': 'w-full px-3 py-2 bg-[color:var(--bg-subtle)] border border-[color:var(--border-default)] rounded-lg text-[color:var(--text-primary)] placeholder:text-[color:var(--text-muted)] focus:outline-none focus:border-electric-violet focus:ring-2 focus:ring-electric-violet/30',
            'placeholder': 'Enter your email'
        }),
        help_text='Required. We\'ll use this to send you important updates.'
    )
    
    class Meta:
        model = User
        fields = ('username', 'email', 'password1', 'password2')
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Style the username field
        self.fields['username'].widget.attrs.update({
            'class': 'w-full px-3 py-2 bg-[color:var(--bg-subtle)] border border-[color:var(--border-default)] rounded-lg text-[color:var(--text-primary)] placeholder:text-[color:var(--text-muted)] focus:outline-none focus:border-electric-violet focus:ring-2 focus:ring-electric-violet/30',
            'placeholder': 'Choose a username'
        })
        # Style the password fields
        self.fields['password1'].widget.attrs.update({
            'class': 'w-full px-3 py-2 bg-[color:var(--bg-subtle)] border border-[color:var(--border-default)] rounded-lg text-[color:var(--text-primary)] placeholder:text-[color:var(--text-muted)] focus:outline-none focus:border-electric-violet focus:ring-2 focus:ring-electric-violet/30',
            'placeholder': 'Create a password'
        })
        self.fields['password2'].widget.attrs.update({
            'class': 'w-full px-3 py-2 bg-[color:var(--bg-subtle)] border border-[color:var(--border-default)] rounded-lg text-[color:var(--text-primary)] placeholder:text-[color:var(--text-muted)] focus:outline-none focus:border-electric-violet focus:ring-2 focus:ring-electric-violet/30',
            'placeholder': 'Confirm your password'
        })
    
    def clean_email(self):
        """Validate email uniqueness"""
        email = self.cleaned_data.get('email')
        if email and User.objects.filter(email=email).exists():
            raise forms.ValidationError('A user with this email already exists.')
        return email
    
    def save(self, commit=True):
        """Save user with email to database"""
        user = super().save(commit=False)
        user.email = self.cleaned_data['email']
        # Ensure email is saved to database
        if commit:
            user.save()
            # Verify email was saved (for debugging/logging)
            user.refresh_from_db()
        return user


class AdminLoginForm(forms.Form):
    username = forms.CharField(
        max_length=150,
        widget=forms.TextInput(attrs={
            "placeholder": "Username",
            "autocomplete": "username",
            "class": "w-full rounded-2xl border border-slate-200/80 bg-white/90 text-slate-900 placeholder:text-slate-400 px-4 py-3 outline-none focus:border-blue-400 focus:ring-2 focus:ring-blue-300",
        }),
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            "placeholder": "Password",
            "autocomplete": "current-password",
            "class": "w-full rounded-2xl border border-slate-200/80 bg-white/90 text-slate-900 placeholder:text-slate-400 px-4 py-3 outline-none focus:border-blue-400 focus:ring-2 focus:ring-blue-300",
        }),
    )

