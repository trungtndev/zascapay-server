from rest_framework import serializers
from .models import Product, ProductCategory


class ProductCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductCategory
        fields = [
            'id',
            'name',
            'description',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class ProductSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source='category.name', read_only=True)
    status_display = serializers.SerializerMethodField()
    created_at = serializers.DateTimeField(read_only=True)

    class Meta:
        model = Product
        fields = [
            'id',
            'name',
            'description',
            'sku',
            'category',
            'category_name',
            'status',
            'status_display',
            'accuracy_rate',
            'detection_count',
            'last_detected_at',
            'last_updated_at',
            'created_at',
            'image_url',
            'price',
            'is_deleted',
        ]
        read_only_fields = ['id', 'last_updated_at', 'created_at']

    def get_status_display(self, obj):
        try:
            return obj.get_status_display()
        except Exception:
            return obj.status

    def validate_accuracy_rate(self, value):
        if value is None:
            return value
        if value < 0 or value > 100:
            raise serializers.ValidationError('accuracy_rate phải nằm trong khoảng 0..100 (phần trăm).')
        return value


# ------------------------------------------------------------------
# Detection serializer used by the scan API
# ------------------------------------------------------------------
from .models import Detection


class DetectionSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source='product.name', read_only=True)

    class Meta:
        model = Detection
        fields = [
            'id',
            'name',
            'accuracy',
            'product',
            'product_name',
        ]
        read_only_fields = ['id', 'product_name']
