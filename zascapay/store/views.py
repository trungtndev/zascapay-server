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
from rest_framework.permissions import IsAuthenticated
from typing import cast
import logging

from .models import StoreCategory
from .serializers import StoreSerializer, StoreCategorySerializer
from .services import (
    compute_store_metrics,
    filter_stores,
    filter_store_categories,
    create_store,
    update_store,
    soft_delete_store,
    restore_store,
    bulk_restart_stores,
    bulk_send_alert,
    bulk_update_model,
    bulk_configure,
)

logger = logging.getLogger(__name__)

@method_decorator(ensure_csrf_cookie, name='dispatch')
@method_decorator(login_required, name='dispatch')
class StorePageView(TemplateView):
    template_name = "store.html"

class StandardResultsSetPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = 'page_size'
    max_page_size = 100

class StoreViewSet(viewsets.ModelViewSet):
    serializer_class = StoreSerializer
    pagination_class = StandardResultsSetPagination
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        request = cast(Request, cast(object, self.request))
        return filter_stores(request.query_params)

    def perform_create(self, serializer):
        data = dict(serializer.validated_data)
        # confidence is a write-only UI field (slider) not persisted on the model
        data.pop('confidence', None)
        instance = create_store(data)
        serializer.instance = instance

    def perform_update(self, serializer):
        data = dict(serializer.validated_data)
        data.pop('confidence', None)
        instance = update_store(self.get_object(), data)
        serializer.instance = instance

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        soft_delete_store(instance)
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=['post'])
    def restore(self, request, pk=None):
        store = restore_store(self.get_object())
        return Response(self.get_serializer(store).data)

    @action(detail=False, methods=['get'])
    def metrics(self, request):
        data = compute_store_metrics()
        return Response(data)

    @action(detail=False, methods=['get'])
    def export(self, request):
        qs = filter_stores(request.query_params).order_by('name')
        headers = [
            'id','name','code','category_name','status','address',
            'last_updated_at','is_deleted'
        ]
        def row(s):
            return [
                str(s.id or ''),
                s.name or '',
                s.code or '',
                (s.category.name if s.category_id else ''),
                s.status or '',
                s.address or '',
                ('' if s.last_updated_at is None else s.last_updated_at.isoformat()),
                '1' if s.is_deleted else '0',
            ]
        def esc(v):
            v = v.replace('"','""')
            if ',' in v or '"' in v or '\n' in v:
                return f'"{v}"'
            return v
        lines = []
        lines.append(','.join(headers))
        for s in qs:
            lines.append(','.join(esc(col) for col in row(s)))
        content = ('\n'.join(lines)).encode('utf-8')
        resp = HttpResponse(content, content_type='text/csv; charset=utf-8')
        resp['Content-Disposition'] = 'attachment; filename="stores_export.csv"'
        return resp

    @action(detail=False, methods=['post'])
    def bulk_restart(self, request):
        ids = request.data.get('ids') or []
        if not isinstance(ids, (list, tuple)):
            return Response({'detail': 'ids must be a list'}, status=status.HTTP_400_BAD_REQUEST)
        count = 0
        try:
            count = bulk_restart_stores(ids)
        except Exception as e:
            logger.exception('bulk_restart failed')
            return Response({'detail': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        return Response({'count': count})

    @action(detail=False, methods=['post'])
    def bulk_alert(self, request):
        ids = request.data.get('ids') or []
        if not isinstance(ids, (list, tuple)):
            return Response({'detail': 'ids must be a list'}, status=status.HTTP_400_BAD_REQUEST)
        try:
            count = bulk_send_alert(ids)
        except Exception as e:
            logger.exception('bulk_alert failed')
            return Response({'detail': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        return Response({'count': count})

    @action(detail=False, methods=['post'])
    def bulk_update_model(self, request):
        ids = request.data.get('ids') or []
        if not isinstance(ids, (list, tuple)):
            return Response({'detail': 'ids must be a list'}, status=status.HTTP_400_BAD_REQUEST)
        try:
            count = bulk_update_model(ids)
        except Exception as e:
            logger.exception('bulk_update_model failed')
            return Response({'detail': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        return Response({'count': count})

    @action(detail=False, methods=['post'])
    def bulk_configure(self, request):
        ids = request.data.get('ids') or []
        if not isinstance(ids, (list, tuple)):
            return Response({'detail': 'ids must be a list'}, status=status.HTTP_400_BAD_REQUEST)
        try:
            count = bulk_configure(ids)
        except Exception as e:
            logger.exception('bulk_configure failed')
            return Response({'detail': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        return Response({'count': count})

class StoreCategoryViewSet(viewsets.ModelViewSet):
    serializer_class = StoreCategorySerializer
    queryset = StoreCategory.objects.all().order_by('name')
    pagination_class = StandardResultsSetPagination
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        request = cast(Request, cast(object, self.request))
        return filter_store_categories(request.query_params)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        try:
            return super().destroy(request, *args, **kwargs)
        except ProtectedError:
            return Response(
                {"detail": "Cannot delete category because it is in use by a store."},
                status=status.HTTP_400_BAD_REQUEST,
            )
