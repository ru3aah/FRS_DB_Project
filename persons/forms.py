from django import forms

from .models import Person


class PersonForm(forms.ModelForm):
    """
    Person create/update form with sane widgets for Bootstrap templates.
    """

    class Meta:
        model = Person
        fields = (
            "first_name",
            "second_name",
            "family_name",
            "dob",
            "gender",
            "nationality",
            "photo",
        )
        widgets = {
            "dob": forms.DateInput(attrs={"type": "date"}),
        }
