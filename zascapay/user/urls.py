from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import LoginView, LogoutView, RegisterView


urlpatterns = [
    path('login/', LoginView.as_view(), name='login'),
    path('logout/', LogoutView.as_view(), name='logout'),
    path('register/', RegisterView.as_view(), name='register'),
]
