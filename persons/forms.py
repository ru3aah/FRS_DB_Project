# persons/forms.py
from django import forms
from django.core.exceptions import ValidationError

from .models import IDType, Person, PersonID, PersonIDScan
from .widgets import BootstrapFormMixin, MultiFileField, MultiFileInput


class PersonForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = Person
        exclude = ["company"]
        widgets = {
            "dob": forms.DateInput(attrs={"type": "date"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._apply_bootstrap()


class PersonIDForm(BootstrapFormMixin, forms.ModelForm):
    # not a model field - only for uploads
    scans = MultiFileField(
        required=False,
        widget=MultiFileInput(
            attrs={
                "multiple": True,
                "accept": ".pdf,.jpg,.jpeg,.png",
            }
        ),
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

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Apply Bootstrap for model fields + "scans"
        self._apply_bootstrap()

        # Ensure scans also has proper class (it is a file input)
        self.fields["scans"].widget.attrs.setdefault("class", "form-control")


class PersonIDScanForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = PersonIDScan
        fields = ["scan_name", "file"]
        widgets = {
            "scan_name": forms.TextInput(),
            "file": forms.ClearableFileInput(
                attrs={"accept": ".pdf,.jpg,.jpeg,.png"},
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._apply_bootstrap()

        # File input should be form-control in Bootstrap
        self.fields["file"].widget.attrs.setdefault("class", "form-control")


class IDTypeForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = IDType
        fields = ["code", "name", "is_active"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._apply_bootstrap()
