from rest_framework import serializers
from .models import Store, StoreCategory


class StoreCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = StoreCategory
        fields = [
            'id',
            'name',
            'description',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class StoreSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source='category.name', read_only=True)
    status_display = serializers.SerializerMethodField()
    created_at = serializers.DateTimeField(read_only=True)
    confidence = serializers.IntegerField(write_only=True, required=False, min_value=0, max_value=100)

    class Meta:
        model = Store
        fields = [
            'id',
            'name',
            'description',
            'code',
            'address',
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
            'is_deleted',
            'confidence',
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
            raise serializers.ValidationError('accuracy_rate must be between 0 and 100.')
        return value

    def validate_category(self, value):
        # Accept both a StoreCategory instance or a PK; ensure the category exists
        if value is None:
            return value
        # If value is a model instance, it's already valid
        if isinstance(value, StoreCategory):
            return value
        # Otherwise value should be a PK (int) - fetch and return the instance
        try:
            pk = int(value)
        except Exception:
            raise serializers.ValidationError('Danh mục không hợp lệ.')
        try:
            return StoreCategory.objects.get(pk=pk)
        except StoreCategory.DoesNotExist:
            raise serializers.ValidationError('Danh mục đã chọn không tồn tại.')
