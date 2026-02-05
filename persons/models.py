from django.db import models


class Person(models.Model):
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

    # Optional photo (stored in MEDIA)
    photo = models.ImageField(
        upload_to="persons/photos/",
        blank=True,
        null=True,
    )

    def __str__(self) -> str:
        return f"{self.family_name} {self.first_name} {self.second_name}".strip()
