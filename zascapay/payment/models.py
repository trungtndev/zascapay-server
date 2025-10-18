from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator
from product.models import Product

class Order(models.Model):
    """Đơn hàng."""

    class Status(models.TextChoices):
        PENDING = 'pending', 'Chờ Xử Lý'
        PROCESSING = 'processing', 'Đang Xử Lý'
        COMPLETED = 'completed', 'Hoàn Thành'
        CANCELLED = 'cancelled', 'Đã Hủy'
        REFUNDED = 'refunded', 'Đã Hoàn Tiền'

    # Use explicit primary key column named `order_id` instead of Django's default `id`.
    # Note: changing primary key requires a migration and careful data migration in production.
    order_id = models.AutoField(primary_key=True)

    @property
    def id(self):
        """Compatibility alias so code expecting `.id` still works.

        This returns the primary key `order_id`. It's read-only and intended
        to make minimal changes elsewhere in the codebase when migrating
        the PK column name.
        """
        return self.order_id

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='orders',
    )
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    total_amount = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(0)])
    currency = models.CharField(max_length=8, default='VND')
    shipping_address = models.TextField(blank=True, null=True)
    is_paid = models.BooleanField(default=False)
    metadata = models.JSONField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'orders'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user'], name='idx_orders_user'),
            models.Index(fields=['status'], name='idx_orders_status'),
        ]
        verbose_name = 'Đơn hàng'
        verbose_name_plural = 'Đơn hàng'

    def __str__(self) -> str:
        return f"Order #{self.pk} - {self.user} - {self.status}"


class OrderItem(models.Model):
    """Một mục trong đơn hàng, tham chiếu tới `product.Product`."""

    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name='items',
    )
    product = models.ForeignKey(
        'product.Product',
        on_delete=models.PROTECT,
        related_name='order_items',
    )
    sku = models.CharField(max_length=50, blank=True)
    name = models.CharField(max_length=255, blank=True)
    quantity = models.PositiveIntegerField(default=1, validators=[MinValueValidator(1)])
    unit_price = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(0)])
    line_total = models.DecimalField(max_digits=14, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'order_items'
        indexes = [
            models.Index(fields=['order'], name='idx_order_items_order'),
            models.Index(fields=['product'], name='idx_order_items_product'),
        ]
        verbose_name = 'Mục đơn hàng'
        verbose_name_plural = 'Mục đơn hàng'

    def save(self, *args, **kwargs):
        # Ensure line_total is consistent with quantity and unit_price
        if self.unit_price is not None and self.quantity is not None:
            self.line_total = self.unit_price * self.quantity
        super().save(*args, **kwargs)

    def __str__(self) -> str:  # pragma: no cover
        return f"{self.name or self.product} x{self.quantity}"


class Payment(models.Model):
    """Thanh toán cho một đơn hàng."""

    class Status(models.TextChoices):
        PENDING = 'pending', 'Chờ'
        SUCCESS = 'success', 'Thành Công'
        FAILED = 'failed', 'Thất Bại'
        REFUNDED = 'refunded', 'Hoàn Tiền'

    class Method(models.TextChoices):
        CARD = 'card', 'Card'
        BANK_TRANSFER = 'bank_transfer', 'Chuyển Khoản'
        CASH = 'cash', 'Tiền Mặt'
        WALLET = 'wallet', 'Ví'
        OTHER = 'other', 'Khác'

    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name='payments',
        null=True,
        blank=True,
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name='payments',
        null=True,
        blank=True,
    )
    currency = models.CharField(max_length=8, default='VND')
    method = models.CharField(max_length=30, choices=Method.choices, default=Method.CARD)
    provider_transaction_id = models.CharField(max_length=255, blank=True, null=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    processed_at = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    metadata = models.JSONField(blank=True, null=True)

    class Meta:
        db_table = 'payments'
        indexes = [
            models.Index(fields=['order'], name='idx_payments_order'),
            models.Index(fields=['status'], name='idx_payments_status'),
        ]
        verbose_name = 'Thanh toán'
        verbose_name_plural = 'Thanh toán'

    def __str__(self) -> str:  # pragma: no cover
        order_info = f"Order #{self.order.pk}" if self.order else "No-Order"
        return f"Payment #{self.pk} - {order_info} - {self.status}"
