from django.db import models
from django.contrib.auth.models import AbstractUser


class User(AbstractUser):
    """
    Custom user model using Django's AbstractUser.
    Single concrete user table; roles/permissions can be added later.
    """
    # Override email to enforce uniqueness at DB level (nullable for safe migration)
    email = models.EmailField(unique=True, blank=True, null=True)

    # Registration/business info
    ACCOUNT_STORE = 'store'
    ACCOUNT_ENTERPRISE = 'enterprise'
    ACCOUNT_INDIVIDUAL = 'individual'
    ACCOUNT_TYPE_CHOICES = [
        (ACCOUNT_STORE, 'Store'),
        (ACCOUNT_ENTERPRISE, 'Enterprise'),
        (ACCOUNT_INDIVIDUAL, 'Individual'),
    ]

    phone = models.CharField(max_length=20, blank=True)
    account_type = models.CharField(max_length=20, choices=ACCOUNT_TYPE_CHOICES, blank=True)
    store_name = models.CharField(max_length=255, blank=True)
    address = models.TextField(blank=True)

    def __str__(self) -> str:
        return self.username
