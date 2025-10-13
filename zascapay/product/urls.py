from django.urls import path

from .views import ProductPageView, ProductViewSet, ProductCategoryViewSet

urlpatterns = [
    # HTML page (Hybrid View-API): /product/
    path('products/', ProductPageView.as_view(), name='product_list'),

    # Product API
    path('api/products/', ProductViewSet.as_view({'get': 'list', 'post': 'create'}), name='product-list'),
    path('api/products/metrics/', ProductViewSet.as_view({'get': 'metrics'}), name='product-metrics'),
    path('api/products/export/', ProductViewSet.as_view({'get': 'export'}), name='product-export'),
    path('api/products/<int:pk>/', ProductViewSet.as_view({
        'get': 'retrieve',
        'patch': 'partial_update',
        'put': 'update',
        'delete': 'destroy',
    }), name='product-detail'),
    path('api/products/<int:pk>/restore/', ProductViewSet.as_view({'post': 'restore'}), name='product-restore'),

    # Category API
    path('api/categories/', ProductCategoryViewSet.as_view({'get': 'list', 'post': 'create'}), name='category-list'),
    path('api/categories/<int:pk>/', ProductCategoryViewSet.as_view({
        'get': 'retrieve',
        'patch': 'partial_update',
        'put': 'update',
        'delete': 'destroy',
    }), name='category-detail'),
]
