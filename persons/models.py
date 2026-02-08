from django.db import models


class Person(models.Model):
    """
    Stores pure personal data, independent from employment or documents.
    """

    person_id = models.BigAutoField(primary_key=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    first_name = models.CharField(max_length=255)
    second_name = models.CharField(max_length=255)
    family_name = models.CharField(max_length=255)

    dob = models.DateField()

    gender = models.CharField(
        max_length=1,
        choices=(("M", "Male"), ("F", "Female")),
        default="M",
        blank=False,
        null=False,
    )

    # Nationality (country of citizenship). Optional.
    nationality = models.ForeignKey(
        "Country",
        on_delete=models.PROTECT,
        related_name="persons_by_nationality",
        blank=True,
        null=True,
    )

    # Optional personal photo (stored in MEDIA)
    photo = models.ImageField(
        upload_to="persons/photos/",
        blank=True,
        null=True,
    )

    class Meta:
        permissions = [
            ("hr_manager", "Can manage HR (persons)"),
        ]

    def __str__(self) -> str:
        return f"{self.family_name} {self.first_name} {self.second_name}".strip()


class Country(models.Model):
    """
    Reference table for document issuing countries and nationality selection.
    """

    id = models.BigAutoField(primary_key=True)

    code3 = models.CharField(
        max_length=3,
        unique=True,
        db_index=True,
        help_text="Three-letter country code (ISO-3 style)",
    )

    short_name = models.CharField(
        max_length=64,
        db_index=True,
        help_text="Short country name (one word or abbreviation)",
    )

    full_name = models.CharField(
        max_length=255,
        unique=True,
        help_text="Official full country name",
    )

    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "countries"
        ordering = ["code3"]

    def __str__(self) -> str:
        return f"{self.code3} {self.short_name}"


class IDType(models.Model):
    """
    Reference table for identity document types.
    """

    id = models.BigAutoField(primary_key=True)

    code = models.CharField(
        max_length=64,
        unique=True,
        db_index=True,
        help_text="Machine-readable code (e.g. passport, national_id)",
    )

    name = models.CharField(
        max_length=255,
        unique=True,
        help_text="Human-readable document type name",
    )

    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "id_types"
        ordering = ["code"]

    def __str__(self) -> str:
        return self.name


class PersonID(models.Model):
    """
    Universal identity document model.
    One Person -> many documents.
    """

    id = models.BigAutoField(primary_key=True)

    person = models.ForeignKey(
        Person,
        on_delete=models.CASCADE,
        related_name="ids",
    )

    id_type = models.ForeignKey(
        IDType,
        on_delete=models.PROTECT,
        related_name="person_ids",
    )

    issued_country = models.ForeignKey(
        Country,
        on_delete=models.PROTECT,
        related_name="issued_person_ids",
        blank=True,
        null=True,
    )

    issued_on = models.DateField(blank=True, null=True, help_text="Document issue date")

    valid_till = models.DateField(
        blank=True,
        null=True,
        help_text="Expiration date (NULL = unlimited or not applicable)",
    )

    id_number = models.CharField(
        max_length=64,
        db_index=True,
        help_text="Document number (letters and digits allowed)",
    )

    id_std_sequence = models.CharField(
        max_length=256,
        blank=True,
        null=True,
        help_text="Machine-readable sequence (MRZ, barcode, etc.)",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "person_ids"
        ordering = ["person", "id_type", "id_number"]
        constraints = [
            models.UniqueConstraint(
                fields=["person", "id_type", "id_number"],
                name="uq_person_idtype_idnumber",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.person} | {self.id_type} | {self.id_number}"


class PersonIDScan(models.Model):
    """
    Stores files (scans/photos/PDFs) related to a document.
    One document -> many files.
    """

    id = models.BigAutoField(primary_key=True)

    person_id = models.ForeignKey(
        PersonID,
        on_delete=models.CASCADE,
        related_name="scans",
    )

    file = models.FileField(
        upload_to="persons/ids/scans/",
        help_text="Uploaded document scan (PDF/JPEG/PNG)",
    )

    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "person_id_scans"
        ordering = ["-uploaded_at"]

    def __str__(self) -> str:
        return f"Scan for {self.person_id} ({self.uploaded_at:%Y-%m-%d})"
