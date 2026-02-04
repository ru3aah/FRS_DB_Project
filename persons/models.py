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
