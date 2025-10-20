from django.db import models


class ProductCategory(models.Model):
    """Danh mục sản phẩm."""
    name = models.CharField(max_length=150, unique=True)
    description = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'product_category'
        ordering = ['name']
        verbose_name = 'Danh mục sản phẩm'
        verbose_name_plural = 'Danh mục sản phẩm'

    def __str__(self) -> str:  # pragma: no cover - safe string repr
        return self.name


class Product(models.Model):
    """Sản phẩm."""

    class Status(models.TextChoices):
        ACTIVE = 'active', 'Hoạt Động'
        TRAINING = 'training', 'Đang Huấn Luyện'
        REVIEW = 'review', 'Cần Xem Xét'
        INACTIVE = 'inactive', 'Ngừng Hoạt Động'

    name = models.CharField(max_length=200)
    description = models.TextField(blank=True, null=True)
    sku = models.CharField(max_length=50, unique=True)
    category = models.ForeignKey(
        ProductCategory,
        on_delete=models.PROTECT,
        related_name='products',
        db_column='category_id',
    )
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.ACTIVE)
    accuracy_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0, null=True)  # store percent, e.g. 94.25
    detection_count = models.PositiveIntegerField(default=0)
    last_detected_at = models.DateTimeField(blank=True, null=True)
    last_updated_at = models.DateTimeField(auto_now=True)
    image_url = models.URLField(blank=True, null=True)
    is_deleted = models.BooleanField(default=False)
    price = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    class Meta:
        db_table = 'product'
        indexes = [
            models.Index(fields=['sku'], name='idx_product_sku'),
            models.Index(fields=['status'], name='idx_product_status'),
            models.Index(fields=['is_deleted'], name='idx_product_deleted'),
        ]
        ordering = ['name']
        verbose_name = 'Sản phẩm'
        verbose_name_plural = 'Sản phẩm'

    def __str__(self) -> str:  # pragma: no cover
        return f"{self.name} ({self.sku})"


class Detection(models.Model):
    """Class detection được phát hiện bởi YOLO, liên kết tới `Product`."""
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=200)
    accuracy = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0,
        null=True,
        help_text='Accuracy percent, e.g. 94.25'
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name='detections',
        db_column='product_id',
    )
    store = models.ForeignKey(
        'store.Store',
        on_delete=models.CASCADE,
        related_name='detections',
        db_column='store_id',
        null=True, # Detections can be unassociated with a store
        blank=True,
    )

    class Meta:
        db_table = 'detection'
        indexes = [
            models.Index(fields=['name'], name='idx_det_name'),
            models.Index(fields=['product'], name='idx_det_product'),
            models.Index(fields=['store'], name='idx_det_store'),
        ]
        verbose_name = 'Detection'
        verbose_name_plural = 'Detections'

    def __str__(self) -> str:  # pragma: no cover
        acc_display = f"{self.accuracy}%" if self.accuracy is not None else "n/a"
        return f"{self.name} ({acc_display})"
