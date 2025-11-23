from django.shortcuts import get_object_or_404
from decimal import Decimal

from rest_framework import viewsets, status
from rest_framework import mixins
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAdminUser, AllowAny, IsAuthenticated
from rest_framework.authentication import TokenAuthentication, SessionAuthentication
from django.db.models import Q
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
from store.models import Store


class OrderViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    serializer_class = OrderSerializer
    # Require auth via DRF Token or Session
    authentication_classes = [TokenAuthentication, SessionAuthentication]
    permission_classes = [IsAuthenticated]
    queryset = Order.objects.all().order_by('-created_at')

    def get_queryset(self):
        # Scope orders to the current user unless staff/system admin
        qs = super().get_queryset()
        user = getattr(self.request, 'user', None)
        if user and (getattr(user, 'is_staff', False) or getattr(user, 'is_system_admin', False)):
            return qs
        return qs.filter(user=user)

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
        # Attach the authenticated user to the order
        user = request.user
        order = OrderService.create_order(user, items=items, shipping_address=shipping_address, currency=currency, metadata=metadata)
        out = OrderSerializer(order, context={'request': request}).data
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
        Optional `store_id` in request body links the payment to a specific store. If omitted,
        the view will attempt to derive a store owned by the authenticated user (if any).
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

        # Determine store: prefer explicit store_id in request, else try to find a store owned by the user
        store = None
        store_id = request.data.get('store_id')
        if store_id:
            store = get_object_or_404(Store, pk=store_id)
        else:
            if request.user and request.user.is_authenticated:
                # pick the first store owned by the user if any
                store = Store.objects.filter(owner=request.user).first()

        try:
            payment = PaymentService.process_payment(
                store,
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
    Optionally accepts `store_id` to link the payment to a store.
    """
    serializer_class = PaymentSerializer
    # Require auth via DRF Token or Session
    authentication_classes = [TokenAuthentication, SessionAuthentication]
    permission_classes = [IsAuthenticated]
    # optimize queries: include related order & store and prefetch order items used by serializer
    queryset = Payment.objects.select_related('order', 'store').prefetch_related('order__items').order_by('-created_at')

    def get_queryset(self):
        # Scope payments to user's orders or user's stores (owner)
        user = getattr(self.request, 'user', None)
        qs = self.queryset
        if user and (getattr(user, 'is_staff', False) or getattr(user, 'is_system_admin', False)):
            return qs
        return qs.filter(Q(order__user=user) | Q(store__owner=user))

    def create(self, request, *args, **kwargs):
        # Log incoming request for debugging (payload and content type)
        try:
            payload_snapshot = request.data
        except Exception:
            payload_snapshot = '<unreadable payload>'
        logger.debug("Payment.create called. user=%s, content_type=%s, payload=%s", getattr(request, 'user', None), request.content_type, payload_snapshot)

        # Reject client-supplied amount to enforce server-side derivation
        if isinstance(payload_snapshot, dict) and 'amount' in payload_snapshot:
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

        # Authorize: user must own the order or the store
        user = request.user
        if not (order.user_id == user.id or Store.objects.filter(owner=user, payments__order=order).exists() or Store.objects.filter(owner=user).exists()):
            return Response({'detail': 'Not allowed for this order.'}, status=status.HTTP_403_FORBIDDEN)

        # Derive amount from order total_amount
        amount = order.total_amount
        try:
            amount = Decimal(str(amount))
        except Exception:
            return Response({'detail': 'Invalid order total amount'}, status=status.HTTP_400_BAD_REQUEST)

        if amount <= 0:
            return Response({'detail': 'Order total_amount must be positive to create a payment.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            # determine store: prefer explicit store_id in payload, else try to derive from authenticated user
            store = None
            store_id = data.get('store_id')
            if store_id:
                store = get_object_or_404(Store, pk=store_id)
            else:
                if request.user and request.user.is_authenticated:
                    store = Store.objects.filter(owner=request.user).first()

            payment = PaymentService.process_payment(
                store,
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
