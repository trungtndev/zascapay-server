from django.shortcuts import get_object_or_404
from decimal import Decimal

from rest_framework import viewsets, status
from rest_framework import mixins
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAdminUser, AllowAny
from django.contrib.auth import get_user_model
import logging

logger = logging.getLogger(__name__)

from .serializers import (
    OrderSerializer,
    OrderCreateSerializer,
    PaymentSerializer,
    PaymentCreateSerializer,
)
from .services import OrderService, PaymentService
from .models import Order, Payment

User = get_user_model()


class OrderViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    """ViewSet for listing, retrieving, creating and managing orders.

    - list: public (shows all orders).
    - retrieve: public.
    - create: allow anonymous clients to create orders if they provide `user_id` in payload; otherwise must be authenticated.
    - cancel: POST action to cancel an order (owner or staff).
    - pay: POST action to pay for an order (owner or staff) — authenticated or provide matching user_id.
    """
    serializer_class = OrderSerializer
    # Make order endpoints public (no auth required to view/create), but actions enforce ownership where needed
    permission_classes = [AllowAny]
    queryset = Order.objects.all().order_by('-created_at')

    def get_queryset(self):
        # Public listing: return all orders
        return super().get_queryset()

    def get_serializer_class(self):
        if self.action == 'create':
            return OrderCreateSerializer
        return OrderSerializer

    def create(self, request, *args, **kwargs):
        serializer = OrderCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        items = data.get('items')
        shipping_address = data.get('shipping_address')
        currency = data.get('currency', 'VND')
        metadata = data.get('metadata')
        # If request is authenticated, attach user; otherwise create order without user (store-managed)
        user = request.user if (request.user and request.user.is_authenticated) else None
        order = OrderService.create_order(user, items=items, shipping_address=shipping_address, currency=currency, metadata=metadata)
        out = OrderSerializer(order, context={'request': request}).data

        print("orders response:", out)
        return Response(out, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'], permission_classes=[IsAdminUser])
    def cancel(self, request, pk=None):
        """Staff-only cancel (store owner manages orders)."""
        order = get_object_or_404(Order, pk=pk)
        try:
            # pass the explicit primary key `order_id` to the service
            order = OrderService.cancel_order(order.order_id, user=request.user if request.user.is_authenticated else None)
        except ValueError as exc:
            return Response({'detail': str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(OrderSerializer(order).data)

    @action(detail=True, methods=['post'], permission_classes=[IsAdminUser])
    def pay(self, request, pk=None):
        """Staff-only pay action: store owner triggers payment for an order.

        Client-supplied `amount` is rejected — amount is derived from the order's total_amount.
        """
        order = get_object_or_404(Order, pk=pk)

        # Reject client-provided amount to enforce server-side amount derivation
        if 'amount' in request.data:
            return Response({'detail': 'Do not provide `amount`; it is derived from the order.'}, status=status.HTTP_400_BAD_REQUEST)

        # Derive amount from order.total_amount
        amount = order.total_amount
        try:
            amount = Decimal(str(amount))
        except Exception:
            return Response({'detail': 'Invalid order total amount'}, status=status.HTTP_400_BAD_REQUEST)

        if amount <= 0:
            return Response({'detail': 'Order total_amount must be positive to create a payment.'}, status=status.HTTP_400_BAD_REQUEST)

        # Use staff user if authenticated, else None
        pay_user = request.user if (request.user and request.user.is_authenticated) else None
        try:
            payment = PaymentService.process_payment(
                pay_user,
                order=order,
                amount=amount,
                currency=order.currency or 'VND',
                method=request.data.get('method', Payment.Method.CARD),
                metadata=request.data.get('metadata')
            )
        except Exception as exc:
            return Response({'detail': str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(PaymentSerializer(payment).data, status=status.HTTP_201_CREATED)


class PaymentViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet, mixins.CreateModelMixin):
    """ViewSet for payments. Creation triggers payment processing via PaymentService.

    Now requires only `order_id` in create requests: amount will be derived server-side from the order's total_amount.
    """
    serializer_class = PaymentSerializer
    # Public payment endpoints (creation can be anonymous); admin-only for refund action remains
    permission_classes = [AllowAny]
    # optimize queries: include related order & user and prefetch order items used by serializer
    queryset = Payment.objects.select_related('order', 'user').prefetch_related('order__items').order_by('-created_at')

    def get_queryset(self):
        # Ensure the optimized queryset is used for list/retrieve to avoid N+1 when serializing items
        return self.queryset

    def create(self, request, *args, **kwargs):
        # Log incoming request for debugging (payload and content type)
        try:
            payload_snapshot = request.data
        except Exception:
            payload_snapshot = '<unreadable payload>'
        logger.debug("Payment.create called. user=%s, content_type=%s, payload=%s", getattr(request, 'user', None), request.content_type, payload_snapshot)

        # Reject client-supplied amount to enforce server-side derivation
        if 'amount' in payload_snapshot:
            logger.warning("Payment.create rejected client-supplied amount: %s", payload_snapshot.get('amount'))
            return Response({'detail': 'Do not provide `amount`; it is derived from the order.'}, status=status.HTTP_400_BAD_REQUEST)

        serializer = PaymentCreateSerializer(data=payload_snapshot)
        if not serializer.is_valid():
            # Log serializer errors and return them so client can see why request is invalid
            logger.info("Payment.create serializer errors: %s", serializer.errors)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        data = serializer.validated_data
        order_id = data.get('order_id')
        if not order_id:
            return Response({'detail': 'order_id is required.'}, status=status.HTTP_400_BAD_REQUEST)

        order = get_object_or_404(Order, pk=order_id)

        # Derive amount from order total_amount
        amount = order.total_amount
        try:
            amount = Decimal(str(amount))
        except Exception:
            return Response({'detail': 'Invalid order total amount'}, status=status.HTTP_400_BAD_REQUEST)

        if amount <= 0:
            return Response({'detail': 'Order total_amount must be positive to create a payment.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            # determine payment user: prefer authenticated user, else None
            pay_user = request.user if (request.user and request.user.is_authenticated) else None
            payment = PaymentService.process_payment(
                pay_user,
                order=order,
                amount=amount,
                currency=data.get('currency', 'VND'),
                method=data.get('method', Payment.Method.CARD),
                metadata=data.get('metadata')
            )
        except Exception as exc:
            return Response({'detail': str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(PaymentSerializer(payment).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'], permission_classes=[IsAdminUser])
    def refund(self, request, pk=None):
        # Admin-only refund endpoint
        payment = get_object_or_404(Payment, pk=pk)

        # If client provided an amount, use it; otherwise derive from the linked order's total_amount
        amount_input = request.data.get('amount')
        if amount_input is None:
            if payment.order and getattr(payment.order, 'total_amount', None) is not None:
                amount = payment.order.total_amount
            else:
                return Response({'detail': 'Refund amount not provided and payment has no linked order total.'}, status=status.HTTP_400_BAD_REQUEST)
        else:
            amount = amount_input

        try:
            amount = Decimal(str(amount))
        except Exception:
            return Response({'detail': 'Invalid amount'}, status=status.HTTP_400_BAD_REQUEST)
        try:
            payment = PaymentService.refund_payment(payment.id, amount)
        except Exception as exc:
            return Response({'detail': str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(PaymentSerializer(payment).data)
