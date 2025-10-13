from __future__ import annotations

from typing import Mapping

from django.db import models
from django.db.models import Avg, QuerySet

from .models import Product, ProductCategory


# --------------------------
# Query builders / services
# --------------------------

def filter_products(params: Mapping[str, str]) -> QuerySet[Product]:
    """Return a filtered Product queryset based on request params.

    Supported params: search, status, category, min_accuracy, max_accuracy,
    include_deleted (true/1), ordering.
    """
    qs = Product.objects.select_related('category').all()

    include_deleted = str(params.get('include_deleted', '')).lower() in {'1', 'true'}
    if not include_deleted:
        qs = qs.filter(is_deleted=False)

    status_value = params.get('status')
    if status_value:
        qs = qs.filter(status=status_value)

    category_id = params.get('category')
    if category_id:
        qs = qs.filter(category_id=category_id)

    search = params.get('search')
    if search:
        qs = qs.filter(
            models.Q(name__icontains=search)
            | models.Q(sku__icontains=search)
            | models.Q(description__icontains=search)
        )

    min_acc = params.get('min_accuracy')
    max_acc = params.get('max_accuracy')
    try:
        if min_acc is not None:
            qs = qs.filter(accuracy_rate__gte=float(min_acc))
    except (TypeError, ValueError):
        pass
    try:
        if max_acc is not None:
            qs = qs.filter(accuracy_rate__lte=float(max_acc))
    except (TypeError, ValueError):
        pass

    allowed = {
        'name', '-name', 'sku', '-sku', 'accuracy_rate', '-accuracy_rate',
        'detection_count', '-detection_count', 'last_detected_at', '-last_detected_at',
        'last_updated_at', '-last_updated_at'
    }
    ordering = params.get('ordering')
    if ordering in allowed:
        qs = qs.order_by(ordering)

    return qs


def filter_categories(params: Mapping[str, str]) -> QuerySet[ProductCategory]:
    qs = ProductCategory.objects.all().order_by('name')
    search = params.get('search')
    if search:
        qs = qs.filter(name__icontains=search)
    return qs


# --------------------------
# CRUD helpers
# --------------------------

def create_product(data: dict) -> Product:
    return Product.objects.create(**data)


def update_product(instance: Product, data: dict) -> Product:
    for field, value in data.items():
        setattr(instance, field, value)
    instance.save()
    return instance


def soft_delete_product(instance: Product) -> None:
    if not instance.is_deleted:
        instance.is_deleted = True
        instance.save(update_fields=['is_deleted', 'last_updated_at'])


def restore_product(instance: Product) -> Product:
    instance.is_deleted = False
    instance.save(update_fields=['is_deleted', 'last_updated_at'])
    return instance


# --------------------------
# Metrics
# --------------------------

def compute_product_metrics() -> dict:
    """Compute dashboard metrics for products.

    Returns a dict with:
      - total_products
      - active_products
      - avg_accuracy_rate
      - review_count
      - training_count
      - need_review (alias of review_count)
    """
    qs = Product.objects.filter(is_deleted=False)
    total = qs.count()
    active = qs.filter(status=Product.Status.ACTIVE).count()
    review = qs.filter(status=Product.Status.REVIEW).count()
    training = qs.filter(status=Product.Status.TRAINING).count()

    agg = qs.aggregate(avg_acc=Avg('accuracy_rate'))
    avg_acc = float(agg['avg_acc'] or 0)

    return {
        'total_products': total,
        'active_products': active,
        'avg_accuracy_rate': round(avg_acc, 2),
        'review_count': review,
        'training_count': training,
        'need_review': review,
    }
