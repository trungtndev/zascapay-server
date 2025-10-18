from PIL import Image
from django.db.models.deletion import ProtectedError
from django.views.decorators.csrf import ensure_csrf_cookie
from django.http import HttpResponse
from django.views.generic import TemplateView
from django.utils.decorators import method_decorator
from django.contrib.auth.decorators import login_required
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response
from rest_framework.request import Request
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.views import APIView
from rest_framework.parsers import JSONParser, MultiPartParser, FormParser
from typing import cast
from django.conf import settings
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
import os
import uuid
import logging
from django.utils import timezone

from .models import ProductCategory, Product, Detection
from .serializers import ProductSerializer, ProductCategorySerializer
from .services import (
    compute_product_metrics,
    filter_products,
    filter_categories,
    create_product,
    update_product,
    soft_delete_product,
    restore_product,
)
from ultralytics import YOLO
import torch
import base64
import io
try:
    import cv2
    _HAS_CV2 = True
except Exception:
    _HAS_CV2 = False
logger = logging.getLogger(__name__)

device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
print("Device", device)


# Create your views here.

@method_decorator(ensure_csrf_cookie, name='dispatch')
@method_decorator(login_required, name='dispatch')
class ProductPageView(TemplateView):
    template_name = "product.html"

class StandardResultsSetPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = 'page_size'
    max_page_size = 100


class ProductViewSet(viewsets.ModelViewSet):
    serializer_class = ProductSerializer
    pagination_class = StandardResultsSetPagination
    permission_classes = [IsAuthenticated]

    # Lazy-loaded class-level model reference to avoid reloading per request
    yolo_model = YOLO("yolo12n.pt", verbose=False).to(device)

    def get_queryset(self):
        request = cast(Request, cast(object, self.request))
        return filter_products(request.query_params)

    def create(self, request, *args, **kwargs):
        """Create product from limited fields (form) and handle optional image uploads.

        Only accept: name, sku, category, price, description from request.data. Files from
        request.FILES under key 'images' (multiple allowed) - we save the first image and set image_url.
        """
        # Extract allowed fields only
        allowed = ('name', 'sku', 'category', 'price', 'description')
        payload = {k: request.data.get(k) for k in allowed if request.data.get(k) is not None and request.data.get(k) != ''}

        # Log incoming payload and files for debugging (helps verify price is received)
        try:
            file_keys = []
            if hasattr(request, 'FILES'):
                file_keys = list(request.FILES.keys())
            logger.info('Product create called. payload=%s files=%s user=%s', payload, file_keys, getattr(request, 'user', None))
        except Exception:
            logger.exception('Failed to log product create payload')

        # Validate with serializer
        serializer = self.get_serializer(data=payload)
        serializer.is_valid(raise_exception=True)

        # Create product via service layer
        product = create_product(serializer.validated_data)

        # Handle uploaded images (first one saved)
        files = []
        # Support both 'images' and 'image' keys
        if hasattr(request, 'FILES'):
            files = request.FILES.getlist('images') or request.FILES.getlist('image') or []
        if files:
            logger.info('Product create: received %d files; first=%s', len(files), getattr(files[0], 'name', None))
        if files:
            first = files[0]
            ext = os.path.splitext(first.name)[1]
            fname = f'products/{uuid.uuid4().hex}{ext}'
            saved_name = default_storage.save(fname, ContentFile(first.read()))
            try:
                url = default_storage.url(saved_name)
            except Exception:
                url = os.path.join(getattr(settings, 'MEDIA_URL', '/media/'), saved_name)
            product.image_url = url
            product.save(update_fields=['image_url', 'last_updated_at'])

        out = self.get_serializer(product).data
        headers = self.get_success_headers(out)
        return Response(out, status=status.HTTP_201_CREATED, headers=headers)

    def perform_create(self, serializer):
        instance = create_product(serializer.validated_data)
        serializer.instance = instance

    def perform_update(self, serializer):
        instance = update_product(self.get_object(), serializer.validated_data)
        serializer.instance = instance

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        soft_delete_product(instance)
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=['post'])
    def restore(self, request, pk=None):
        product = restore_product(self.get_object())
        return Response(self.get_serializer(product).data)

    @action(detail=False, methods=['get'])
    def metrics(self, request):
        data = compute_product_metrics()
        return Response(data)

    @action(detail=False, methods=['get'])
    def export(self, request):
        # Export filtered products to CSV (no pagination)
        qs = filter_products(request.query_params).order_by('name')
        # Build CSV
        headers = [
            'id','name','sku','category_name','status','accuracy_rate','detection_count',
            'last_detected_at','last_updated_at','image_url','is_deleted'
        ]
        def row(p):
            return [
                str(p.id or ''),
                p.name or '',
                p.sku or '',
                (p.category.name if p.category_id else ''),
                p.status or '',
                ('' if p.accuracy_rate is None else str(p.accuracy_rate)),
                str(p.detection_count or 0),
                ('' if p.last_detected_at is None else p.last_detected_at.isoformat()),
                ('' if p.last_updated_at is None else p.last_updated_at.isoformat()),
                p.image_url or '',
                '1' if p.is_deleted else '0',
            ]
        # Compose response
        lines = []
        lines.append(','.join(headers))
        for p in qs:
            # Escape commas/quotes by wrapping with quotes and doubling quotes
            def esc(v):
                v = v.replace('"','""')
                if ',' in v or '"' in v or '\n' in v:\
                    return f'"{v}"'
                return v
            lines.append(','.join(esc(col) for col in row(p)))
        content = ('\n'.join(lines)).encode('utf-8')
        resp = HttpResponse(content, content_type='text/csv; charset=utf-8')
        resp['Content-Disposition'] = 'attachment; filename="products_export.csv"'
        return resp

class ScanAPIView(APIView):
    """Public API endpoint for scanning an image.

    Accepts JSON {"image": "data:image/...;base64,..."} or multipart/form-data with file field 'image' or 'file'.
    This read-only variant does NOT write to the database; it only returns the detected classes and the annotated image.
    """
    permission_classes = [AllowAny]
    authentication_classes = []  # disable session authentication & CSRF for this endpoint
    parser_classes = [JSONParser, MultiPartParser, FormParser]
    yolo_model = YOLO("yolo12n.pt", verbose=False).to(device)

    def post(self, request, format=None):
        # support base64 field or uploaded file
        image_b64 = request.data.get('image')
        image_file = None
        if not image_b64:
            image_file = request.FILES.get('image') or request.FILES.get('file') if hasattr(request, 'FILES') else None

        if image_file:
            try:
                image_bytes = image_file.read()
            except Exception:
                return Response({'detail': 'Không thể đọc file ảnh.'}, status=status.HTTP_400_BAD_REQUEST)
        elif image_b64:
            try:
                image_bytes = base64.b64decode(image_b64.split(',')[-1])
            except Exception:
                return Response({'detail': 'Base64 không hợp lệ.'}, status=status.HTTP_400_BAD_REQUEST)
        else:
            return Response({'detail': 'Thiếu ảnh (base64 hoặc file).'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            image = Image.open(io.BytesIO(image_bytes)).convert('RGB')

            results = self.yolo_model(image)
            result = results[0]

            labels = result.names
            boxes = result.boxes

            detections_data = []
            annotated = result.plot(conf=False, probs=False)

            # Only read product info for mapping; do NOT modify DB or create Detection rows
            for cls_id, conf in zip(boxes.cls.tolist(), boxes.conf.tolist()):
                cls_name = labels[int(cls_id)]
                accuracy = round(float(conf) * 100, 2)

                # map to product if exists (read-only)
                product = Product.objects.filter(name__iexact=cls_name).first()

                detections_data.append({
                    'product_id': product.id,
                    'product_name': product.name,
                    'price': str(product.price) if product else None,
                })

            buf = io.BytesIO()
            img = Image.fromarray(cv2.cvtColor(annotated, cv2.COLOR_BGR2RGB))
            img.save(buf, format='JPEG')  # ghi ảnh vào buffer
            buf.seek(0)  # quay về đầu buffer
            annotated_b64 = base64.b64encode(buf.getvalue()).decode()

            return Response({
                'products': detections_data,
                'image': annotated_b64,
            })

        except Exception as e:
            logger.exception('Error in ScanAPIView')
            return Response({'detail': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class ProductCategoryViewSet(viewsets.ModelViewSet):
    serializer_class = ProductCategorySerializer
    queryset = ProductCategory.objects.all().order_by('name')
    pagination_class = StandardResultsSetPagination
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        request = cast(Request, cast(object, self.request))
        return filter_categories(request.query_params)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        try:
            return super().destroy(request, *args, **kwargs)
        except ProtectedError:
            return Response(
                {"detail": "Không thể xóa danh mục vì đang được sử dụng bởi sản phẩm."},
                status=status.HTTP_400_BAD_REQUEST,
            )
