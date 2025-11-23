from rest_framework import serializers
from .models import Order, OrderItem, Payment


class OrderItemSerializer(serializers.ModelSerializer):
    product_id = serializers.IntegerField(read_only=True)

    class Meta:
        model = OrderItem
        fields = ['id', 'product_id', 'sku', 'name', 'quantity', 'unit_price', 'line_total', 'created_at']
        read_only_fields = ['id', 'line_total', 'created_at']


# Compact item serializer used specifically on Payment responses
class PaymentItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrderItem
        fields = ['id', 'name', 'unit_price', 'quantity']
        read_only_fields = ['id', 'name', 'unit_price', 'quantity']


class OrderSerializer(serializers.ModelSerializer):
    # expose the primary key column named `order_id`
    order_id = serializers.IntegerField(read_only=True)
    items = OrderItemSerializer(many=True, read_only=True)
    user_id = serializers.IntegerField(read_only=True)

    class Meta:
        model = Order
        # expose order_id instead of default `id`
        fields = ['order_id', 'user_id', 'status', 'total_amount', 'currency', 'shipping_address', 'is_paid', 'metadata', 'created_at', 'updated_at', 'items']
        read_only_fields = ['order_id', 'created_at', 'updated_at', 'is_paid', 'total_amount']


class OrderCreateItemSerializer(serializers.Serializer):
    product_id = serializers.IntegerField()
    quantity = serializers.IntegerField(min_value=1)
    unit_price = serializers.DecimalField(max_digits=12, decimal_places=2, required=False)


class OrderCreateSerializer(serializers.Serializer):
    shipping_address = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    currency = serializers.CharField(default='VND')
    metadata = serializers.JSONField(required=False)
    items = OrderCreateItemSerializer(many=True)

    def validate_items(self, value):
        if not value:
            raise serializers.ValidationError('Order must contain at least one item.')
        return value


class PaymentSerializer(serializers.ModelSerializer):
    # expose the related order's primary key under `order_id` (Order model uses `order_id`)
    order_id = serializers.IntegerField(source='order.order_id', read_only=True)
    store_id = serializers.IntegerField(source='store.id', read_only=True)
    # amount is not stored on Payment model any more; expose it from the related Order when available
    amount = serializers.SerializerMethodField()
    # include purchased items from the related order (compact fields)
    items = PaymentItemSerializer(source='order.items', many=True, read_only=True)

    class Meta:
        model = Payment
        fields = ['id', 'order_id', 'store_id', 'amount', 'items', 'currency', 'method', 'provider_transaction_id', 'status', 'processed_at', 'created_at', 'metadata']
        read_only_fields = ['id', 'status', 'processed_at', 'created_at']

    def get_amount(self, obj):
        if obj.order:
            return obj.order.total_amount
        return None


class PaymentCreateSerializer(serializers.Serializer):
    # Client must provide order_id only; amount is derived from Order.total_amount on server
    order_id = serializers.IntegerField(required=True)
    # Allow clients to optionally specify the store that will be linked to the payment
    store_id = serializers.IntegerField(required=False)
    currency = serializers.CharField(default='VND')
    # Make method optional with a default so clients don't need to include it
    method = serializers.ChoiceField(choices=[(m.value, m.label) for m in Payment.Method], required=False, default=Payment.Method.CARD)
    metadata = serializers.JSONField(required=False)

    def validate(self, data):
        return data
