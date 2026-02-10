from django import forms


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


class BootstrapFormMixin:
    """
    Applies Bootstrap classes to fields.
    - checkbox -> form-check-input
    - select -> form-select
    - everything else -> form-control
    """

    def _apply_bootstrap(self) -> None:
        for name, field in self.fields.items():
            w = field.widget

            # Skip hidden inputs
            if isinstance(w, forms.HiddenInput):
                continue

            if getattr(w, "input_type", None) == "checkbox":
                w.attrs.setdefault("class", "form-check-input")
                continue

            if isinstance(w, (forms.Select, forms.SelectMultiple)):
                w.attrs.setdefault("class", "form-select")
            else:
                w.attrs.setdefault("class", "form-control")
