from django import forms

from .models import Person, PersonID, IDType


class MultiFileInput(forms.ClearableFileInput):
    """
    Enable <input type="file" multiple>.
    """

    allow_multiple_selected = True


class MultiFileField(forms.FileField):
    """
    Accepts one OR multiple uploaded files.
    When widget.allow_multiple_selected=True, widget returns a list.
    """

    def clean(self, data, initial=None):
        if not data:
            return []

        # If multiple files were selected, data is a list.
        if isinstance(data, (list, tuple)):
            cleaned_files = []
            errors = []

            for item in data:
                try:
                    cleaned_files.append(super().clean(item, initial))
                except forms.ValidationError as e:
                    errors.extend(e.error_list)

            if errors:
                raise forms.ValidationError(errors)

            return cleaned_files

        # Single file selected
        return [super().clean(data, initial)]


class PersonForm(forms.ModelForm):
    class Meta:
        model = Person
        fields = "__all__"
        widgets = {
            "dob": forms.DateInput(attrs={"type": "date"}),
        }


class PersonIDForm(forms.ModelForm):
    # not a model field - only for uploads
    scans = MultiFileField(
        required=False,
        widget=MultiFileInput(attrs={"multiple": True}),
        help_text="You can upload one or more files (PDF/JPG/PNG).",
        label="Scans",
    )

    class Meta:
        model = PersonID
        fields = [
            "id_type",
            "id_number",
            "issued_country",
            "issued_on",
            "valid_till",
            "id_std_sequence",
        ]
        widgets = {
            "issued_on": forms.DateInput(attrs={"type": "date"}),
            "valid_till": forms.DateInput(attrs={"type": "date"}),
        }


class IDTypeForm(forms.ModelForm):
    class Meta:
        model = IDType
        fields = ["code", "name", "is_active"]
