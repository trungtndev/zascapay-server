from django.db import models
from django.conf import settings
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    # Allow type checkers to resolve 'product' module used in string FKs
    import product  # noqa: F401

class StoreCategory(models.Model):
    name = models.CharField(max_length=150, unique=True)
    description = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'store_category'
        ordering = ['name']
        verbose_name = 'Danh mục cửa hàng'
        verbose_name_plural = 'Danh mục cửa hàng'

    def __str__(self):
        return self.name

class Store(models.Model):
    class Status(models.TextChoices):
        ACTIVE = 'active', 'Hoạt Động'
        INACTIVE = 'inactive', 'Ngừng Hoạt Động'

    name = models.CharField(max_length=200)
    description = models.TextField(blank=True, null=True)
    code = models.CharField(max_length=50, unique=True)
    address = models.TextField(blank=True, null=True)
    category = models.ForeignKey(
        StoreCategory,
        on_delete=models.PROTECT,
        related_name='stores',
        db_column='category_id',
    )
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='owned_stores'
    )
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.ACTIVE)
    accuracy_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0, null=True)
    detection_count = models.PositiveIntegerField(default=0)
    last_detected_at = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    last_updated_at = models.DateTimeField(auto_now=True)
    image_url = models.URLField(blank=True, null=True)
    is_deleted = models.BooleanField(default=False)

    class Meta:
        db_table = 'store'
        indexes = [
            models.Index(fields=['code'], name='idx_store_code'),
            models.Index(fields=['status'], name='idx_store_status'),
            models.Index(fields=['is_deleted'], name='idx_store_deleted'),
        ]
        ordering = ['name']
        verbose_name = 'Cửa hàng'
        verbose_name_plural = 'Cửa hàng'

    def __str__(self):
        return f"{self.name} ({self.code})"

class StoreInventory(models.Model):
    """Links products to a store, creating a many-to-many relationship with per-store price."""
    store = models.ForeignKey(Store, on_delete=models.CASCADE, related_name='inventory')
    product = models.ForeignKey('product.Product', on_delete=models.CASCADE, related_name='stores')
    quantity = models.PositiveIntegerField(default=0)
    price = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    added_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'store_inventory'
        unique_together = ('store', 'product')
        verbose_name = 'Kho hàng'
        verbose_name_plural = 'Kho hàng'
