from django import forms

from .models import Person


class PersonForm(forms.ModelForm):
    class Meta:
        model = Person
        fields = [
            "photo",
            "first_name",
            "second_name",
            "family_name",
            "dob",
            "gender",
            "nationality",
        ]
        widgets = {
            # Native date picker in modern browsers
            "dob": forms.DateInput(attrs={"type": "date"}),
        }
