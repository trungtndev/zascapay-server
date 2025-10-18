from decimal import Decimal
from django.db import transaction
from django.utils import timezone
from django.shortcuts import get_object_or_404
from typing import List, Dict, Optional

from .models import Order, OrderItem, Payment
from product.models import Product


class PaymentService:
    """Service that encapsulates payment operations (simulated).

    NOTE: This implements a simple, synchronous 'fake' payment processor for
    local/dev use. Replace or extend with integration to actual payment
    providers (Stripe, PayPal, etc.) in production.
    """

    @staticmethod
    @transaction.atomic
    def process_payment(user, order: Optional[Order], amount: Decimal, currency: str, method: str, metadata: Optional[dict] = None) -> Payment:
        # Basic validation
        if order and order.is_paid:
            raise ValueError('Order is already paid')
        if amount <= 0:
            raise ValueError('Amount must be positive')

        # If order provided, ensure amount does not exceed order total (and optionally matches)
        if order:
            order_total = order.total_amount
            if amount > order_total:
                raise ValueError('Amount cannot exceed order total_amount')

        # Simulate provider transaction id
        provider_tx = f"SIM-{int(timezone.now().timestamp())}-{user.id if user else 'anon'}"

        # Create Payment record — note: Payment model no longer stores amount; we keep order reference and other metadata
        payment = Payment.objects.create(
            order=order,
            user=user,
            currency=currency,
            method=method,
            provider_transaction_id=provider_tx,
            status=Payment.Status.SUCCESS,
            processed_at=timezone.now(),
            metadata=metadata or {},
        )

        # mark order paid when applicable
        if order:
            order.is_paid = True
            order.status = Order.Status.PROCESSING if order.status == Order.Status.PENDING else order.status
            order.save(update_fields=['is_paid', 'status', 'updated_at'])

        return payment

    @staticmethod
    @transaction.atomic
    def refund_payment(payment_id: int, amount: Decimal) -> Payment:
        payment = get_object_or_404(Payment, pk=payment_id)
        if payment.status != Payment.Status.SUCCESS:
            raise ValueError('Only successful payments can be refunded')

        # Determine original amount from the linked order if available
        original_amount = payment.order.total_amount if payment.order else None
        if original_amount is None:
            raise ValueError('Cannot determine original payment amount for refund')

        if amount <= 0 or amount > original_amount:
            raise ValueError('Invalid refund amount')

        # Mark the original payment refunded and record processed_at
        payment.status = Payment.Status.REFUNDED
        payment.processed_at = timezone.now()
        payment.save(update_fields=['status', 'processed_at'])

        # If associated order exists, mark it unpaid / refunded
        if payment.order:
            payment.order.is_paid = False
            payment.order.status = Order.Status.REFUNDED
            payment.order.save(update_fields=['is_paid', 'status', 'updated_at'])

        return payment

    @staticmethod
    def get_payment_status(payment_id: int) -> str:
        payment = get_object_or_404(Payment, pk=payment_id)
        return payment.status


class OrderService:
    """Service handling order creation and lifecycle.

    Methods here perform DB changes and enforce business rules. They are
    deliberately small and composable so views remain thin.
    """

    @staticmethod
    @transaction.atomic
    def create_order(user, items: List[Dict], shipping_address: Optional[str] = None, currency: str = 'VND', metadata: Optional[dict] = None) -> Order:
        """Create an Order and its OrderItems.

        `items` is a list of dicts with keys: product_id (int), quantity (int), optional unit_price (Decimal).
        If unit_price is absent, product.price is used.
        """
        if not items:
            raise ValueError('Order must contain at least one item')

        # Lock selected products to avoid race conditions if needed
        product_ids = [int(it['product_id']) for it in items]
        products = {p.id: p for p in Product.objects.filter(id__in=product_ids)}

        total = Decimal('0')
        # Pre-validate items and compute total
        prepared = []
        for it in items:
            pid = int(it['product_id'])
            qty = int(it.get('quantity', 1))
            if qty <= 0:
                raise ValueError('Quantity must be positive')
            prod = products.get(pid)
            if not prod:
                raise ValueError(f'Product {pid} not found')
            unit_price = Decimal(str(it.get('unit_price'))) if it.get('unit_price') is not None else prod.price
            line_total = unit_price * qty
            total += line_total
            prepared.append((prod, qty, unit_price, line_total))

        order = Order.objects.create(
            user=user,
            status=Order.Status.PENDING,
            total_amount=total,
            currency=currency,
            shipping_address=shipping_address or '',
            metadata=metadata or {},
        )

        for prod, qty, unit_price, line_total in prepared:
            OrderItem.objects.create(
                order=order,
                product=prod,
                sku=prod.sku,
                name=prod.name,
                quantity=qty,
                unit_price=unit_price,
                line_total=line_total,
            )

        return order

    @staticmethod
    def get_order_details(order_id: int, user=None) -> Order:
        qs = Order.objects.select_related('user').prefetch_related('items__product')
        if user and not user.is_staff:
            return get_object_or_404(qs, pk=order_id, user=user)
        return get_object_or_404(qs, pk=order_id)

    @staticmethod
    @transaction.atomic
    def cancel_order(order_id: int, user=None) -> Order:
        order = OrderService.get_order_details(order_id, user=user)
        if order.status in (Order.Status.COMPLETED, Order.Status.REFUNDED):
            raise ValueError('Cannot cancel a completed or refunded order')

        order.status = Order.Status.CANCELLED
        # if paid, mark unpaid (refund should be handled separately)
        order.is_paid = False
        order.save(update_fields=['status', 'is_paid', 'updated_at'])
        return order
