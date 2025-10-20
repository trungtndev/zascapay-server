from django.urls import path

from .views import StorePageView, StoreViewSet, StoreCategoryViewSet

urlpatterns = [
    # HTML page
    path('stores/', StorePageView.as_view(), name='store_list'),

    # Store API
    path('api/stores/', StoreViewSet.as_view({'get': 'list', 'post': 'create'}), name='store-list'),
    path('api/stores/metrics/', StoreViewSet.as_view({'get': 'metrics'}), name='store-metrics'),
    path('api/stores/export/', StoreViewSet.as_view({'get': 'export'}), name='store-export'),
    path('api/stores/<int:pk>/', StoreViewSet.as_view({
        'get': 'retrieve',
        'patch': 'partial_update',
        'put': 'update',
        'delete': 'destroy',
    }), name='store-detail'),
    path('api/stores/<int:pk>/restore/', StoreViewSet.as_view({'post': 'restore'}), name='store-restore'),

    # Bulk action endpoints
    path('api/stores/bulk_restart/', StoreViewSet.as_view({'post': 'bulk_restart'}), name='store-bulk-restart'),
    path('api/stores/bulk_alert/', StoreViewSet.as_view({'post': 'bulk_alert'}), name='store-bulk-alert'),
    path('api/stores/bulk_update_model/', StoreViewSet.as_view({'post': 'bulk_update_model'}), name='store-bulk-update-model'),
    path('api/stores/bulk_configure/', StoreViewSet.as_view({'post': 'bulk_configure'}), name='store-bulk-configure'),

    # Category API
    path('api/categories/', StoreCategoryViewSet.as_view({'get': 'list', 'post': 'create'}), name='category-list'),
    path('api/categories/<int:pk>/', StoreCategoryViewSet.as_view({
        'get': 'retrieve',
        'put': 'update',
        'patch': 'partial_update',
        'delete': 'destroy',
    }), name='category-detail'),
]
