from django.db import models
from django.contrib.auth.models import AbstractUser


class User(AbstractUser):
    """
    Custom user model using Django's AbstractUser.
    """
    email = models.EmailField(unique=True, blank=True, null=True)

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
    is_approved = models.BooleanField(default=False, help_text="Chỉ khi admin duyệt thì mới được hoạt động.")
    is_system_admin = models.BooleanField(default=False, help_text="Admin có toàn quyền trên hệ thống.")
    
    # Link to a store if the user is a store owner or staff
    store = models.ForeignKey(
        'store.Store', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='staff'
    )

    def __str__(self) -> str:
        return self.username
