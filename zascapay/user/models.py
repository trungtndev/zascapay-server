from django.db import models
from django.contrib.auth.models import AbstractUser


class User(AbstractUser):
    """
    Custom user model using Django's AbstractUser.
    Single concrete user table; roles/permissions can be added later.
    """
    # Keep default fields from AbstractUser (username, email, first_name, last_name, etc.)
    # Add extra fields later as needed.

    def __str__(self) -> str:
        return self.username
