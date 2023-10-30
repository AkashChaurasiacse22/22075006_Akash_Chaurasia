from django import forms
from .models import URL

class URL_Form(forms.Form):
    Long_url=forms.URLField()