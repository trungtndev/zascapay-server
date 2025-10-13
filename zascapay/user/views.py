from django.core.exceptions import ValidationError as DjangoValidationError
from django.contrib.auth import get_user_model, login as auth_login, logout as auth_logout
from django.shortcuts import redirect, render
from django.views import View
from rest_framework import status, viewsets
from rest_framework.request import Request
from rest_framework.response import Response

from .serializers import UserSerializer
from .service import UserService

User = get_user_model()


class UserViewSet(viewsets.ViewSet):
    """CRUD endpoints for non-admin users using the service layer."""

    def list(self, request: Request) -> Response:
        users = UserService.list_users()
        data = UserSerializer(users, many=True, context={'request': request}).data
        return Response(data)

    def retrieve(self, request: Request, pk: str | int = None) -> Response:
        try:
            user = UserService.get_user(int(pk))
        except DjangoValidationError as e:
            return Response({'detail': 'Not found.'}, status=status.HTTP_404_NOT_FOUND)
        data = UserSerializer(user, context={'request': request}).data
        return Response(data)

    def create(self, request: Request) -> Response:
        serializer = UserSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        try:
            user = UserService.create_user(serializer.validated_data)
        except DjangoValidationError as e:
            return Response({'detail': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        out = UserSerializer(user, context={'request': request}).data
        return Response(out, status=status.HTTP_201_CREATED)

    def update(self, request: Request, pk: str | int = None) -> Response:
        serializer = UserSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        try:
            user = UserService.update_user(int(pk), serializer.validated_data)
        except DjangoValidationError as e:
            msg = str(e)
            if 'not found' in msg.lower():
                return Response({'detail': 'Not found.'}, status=status.HTTP_404_NOT_FOUND)
            return Response({'detail': msg}, status=status.HTTP_400_BAD_REQUEST)
        out = UserSerializer(user, context={'request': request}).data
        return Response(out)

    def partial_update(self, request: Request, pk: str | int = None) -> Response:
        serializer = UserSerializer(data=request.data, context={'request': request}, partial=True)
        serializer.is_valid(raise_exception=True)
        try:
            user = UserService.update_user(int(pk), serializer.validated_data)
        except DjangoValidationError as e:
            msg = str(e)
            if 'not found' in msg.lower():
                return Response({'detail': 'Not found.'}, status=status.HTTP_404_NOT_FOUND)
            return Response({'detail': msg}, status=status.HTTP_400_BAD_REQUEST)
        out = UserSerializer(user, context={'request': request}).data
        return Response(out)

    def destroy(self, request: Request, pk: str | int = None) -> Response:
        try:
            UserService.delete_user(int(pk))
        except DjangoValidationError as e:
            return Response({'detail': 'Not found.'}, status=status.HTTP_404_NOT_FOUND)
        return Response(status=status.HTTP_204_NO_CONTENT)


class LoginView(View):
    template_name = 'login.html'

    def get(self, request):
        return render(request, self.template_name)

    def post(self, request):
        identifier = request.POST.get('email') or ''  # can be email or username
        password = request.POST.get('password') or ''
        remember = request.POST.get('remember')
        error = None
        try:
            user = UserService.authenticate(identifier, password)
        except DjangoValidationError as e:
            error = str(e)
        if error:
            # Re-render login with error and keep the identifier field
            context = {'error': error, 'email_value': identifier}
            return render(request, self.template_name, context, status=400)
        # Log the user in
        auth_login(request, user)
        # Session expiry: if not remember, expire at browser close
        if not remember:
            request.session.set_expiry(0)
        next_url = request.GET.get('next') or '/'
        return redirect(next_url)


class LogoutView(View):
    def post(self, request):
        auth_logout(request)
        return redirect('login')

    # Allow GET for convenience
    def get(self, request):
        return self.post(request)


class RegisterView(View):
    template_name = 'register.html'

    def get(self, request):
        return render(request, self.template_name)

    def post(self, request):
        payload = {
            'first_name': request.POST.get('first_name'),
            'last_name': request.POST.get('last_name'),
            'email': request.POST.get('email'),
            'phone': request.POST.get('phone'),
            'account_type': request.POST.get('account_type'),
            'store_name': request.POST.get('store_name'),
            'address': request.POST.get('address'),
            'password': request.POST.get('password'),
            'password_confirm': request.POST.get('password_confirm'),
            'terms': request.POST.get('terms') in ['on', 'true', '1', True],
        }
        try:
            user = UserService.register(payload)
        except DjangoValidationError as e:
            # Re-render with error and keep entered values (except passwords)
            values = payload.copy()
            values.pop('password', None)
            values.pop('password_confirm', None)
            return render(request, self.template_name, {'error': str(e), 'values': values}, status=400)
        # Auto-login after registration
        auth_login(request, user)
        return redirect('/')
