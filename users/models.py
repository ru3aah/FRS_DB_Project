from django.contrib.auth.models import AbstractUser
from django.db import models

from persons.models import Person


class CustomUser(AbstractUser):
    """
    Логин по email. Каждый user связан с Person (не каждый Person является User).
    """

    username = None  # отключаем username
    email = models.EmailField("email address", unique=True)

    person = models.OneToOneField(
        Person,
        on_delete=models.PROTECT,
        related_name="user",
        null=False,
        blank=False,
    )

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []  # т.к. username отключен

    def __str__(self) -> str:
        return self.email
