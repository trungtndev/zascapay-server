from django.urls import path

from .views import OrderViewSet, PaymentViewSet

urlpatterns = [
    # Orders
    path('api/orders/', OrderViewSet.as_view({'get': 'list', 'post': 'create'}), name='order-list'),
    path('api/orders/<int:pk>/', OrderViewSet.as_view({'get': 'retrieve'}), name='order-detail'),
    path('api/orders/<int:pk>/cancel/', OrderViewSet.as_view({'post': 'cancel'}), name='order-cancel'),
    path('api/orders/<int:pk>/pay/', OrderViewSet.as_view({'post': 'pay'}), name='order-pay'),

    # Payments
    path('api/payments/', PaymentViewSet.as_view({'get': 'list', 'post': 'create'}), name='payment-list'),
    path('api/payments/<int:pk>/', PaymentViewSet.as_view({'get': 'retrieve'}), name='payment-detail'),
    path('api/payments/<int:pk>/refund/', PaymentViewSet.as_view({'post': 'refund'}), name='payment-refund'),
]

