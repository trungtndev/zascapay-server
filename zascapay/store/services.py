from __future__ import annotations

from typing import Mapping

from django.db import models
from django.db.models import Avg
from django.db.models.query import QuerySet
from django.utils import timezone

from .models import Store, StoreCategory

def filter_stores(params: Mapping[str, str]) -> QuerySet[Store]:
    qs = Store.objects.select_related('category').all()

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
            | models.Q(code__icontains=search)
            | models.Q(address__icontains=search)
        )

    ordering = params.get('ordering')
    if ordering in {'name', '-name', 'code', '-code', 'last_updated_at', '-last_updated_at'}:
        qs = qs.order_by(ordering)

    return qs

def filter_store_categories(params: Mapping[str, str]) -> QuerySet[StoreCategory]:
    qs = StoreCategory.objects.all().order_by('name')
    search = params.get('search')
    if search:
        qs = qs.filter(name__icontains=search)
    return qs

def create_store(data: dict) -> Store:
    return Store.objects.create(**data)

def update_store(instance: Store, data: dict) -> Store:
    for field, value in data.items():
        setattr(instance, field, value)
    instance.save()
    return instance

def soft_delete_store(instance: Store) -> None:
    if not instance.is_deleted:
        instance.is_deleted = True
        instance.save(update_fields=['is_deleted', 'last_updated_at'])

def restore_store(instance: Store) -> Store:
    instance.is_deleted = False
    instance.save(update_fields=['is_deleted', 'last_updated_at'])
    return instance

def compute_store_metrics() -> dict:
    qs = Store.objects.filter(is_deleted=False)
    total = qs.count()
    active = qs.filter(status=Store.Status.ACTIVE).count()
    avg_acc = qs.aggregate(avg_acc=Avg('accuracy_rate'))['avg_acc'] or 0
    return {
        'total_stores': total,
        'active_stores': active,
        'avg_accuracy_rate': round(float(avg_acc), 2),
        'review_count': 0, # Placeholder for now
    }


def bulk_restart_stores(ids):
    qs = Store.objects.filter(id__in=ids)
    count = qs.count()
    # Placeholder: update last_updated_at to now to simulate an action
    qs.update(last_updated_at=timezone.now())
    return count


def bulk_send_alert(ids):
    qs = Store.objects.filter(id__in=ids)
    # Placeholder: increment a dummy field or just return count
    return qs.count()


def bulk_update_model(ids):
    qs = Store.objects.filter(id__in=ids)
    # Placeholder: flag stores for model update (no real field) — simply update last_updated_at
    qs.update(last_updated_at=timezone.now())
    return qs.count()


def bulk_configure(ids):
    qs = Store.objects.filter(id__in=ids)
    # Placeholder: pretend configuration applied
    return qs.count()
