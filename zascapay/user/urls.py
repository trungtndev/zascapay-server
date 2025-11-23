from django.urls import path

from .views import LoginView, LogoutView, RegisterView, UserViewSet


urlpatterns = [
    path('login/', LoginView.as_view(), name='login'),
    path('logout/', LogoutView.as_view(), name='logout'),
    path('register/', RegisterView.as_view(), name='register'),
]

# Admin dashboard page (HTML)
from .views import AdminDashboardView  # noqa: E402
urlpatterns += [
    path('admin-dashboard/', AdminDashboardView.as_view(), name='admin_dashboard'),
]

# Admin-only User management APIs (DRF ViewSet)
# Note: UserViewSet already enforces IsAuthenticated + IsSystemAdmin
urlpatterns += [
    path('api/users/', UserViewSet.as_view({'get': 'list'}), name='admin-user-list'),
    path('api/users/<int:pk>/', UserViewSet.as_view({
        'get': 'retrieve',
        'patch': 'partial_update',
        'put': 'update',
        'delete': 'destroy',
    }), name='admin-user-detail'),
    path('api/users/<int:pk>/approve/', UserViewSet.as_view({'post': 'approve'}), name='admin-user-approve'),
]
