from django.core.exceptions import ValidationError as DjangoValidationError, ValidationError
from django.contrib.auth import get_user_model, login as auth_login, logout as auth_logout
from django.contrib import messages
from django.shortcuts import redirect, render
from django.views import View
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.permissions import BasePermission, IsAuthenticated
from rest_framework.views import APIView
from django.utils.decorators import method_decorator
from django.views.decorators.cache import never_cache

from .serializers import UserSerializer
from .service import UserService

User = get_user_model()



class IsSystemAdmin(BasePermission):
    """
    Chỉ admin hệ thống mới có quyền truy cập.
    """
    message = "Chỉ admin mới được phép truy cập."

    def has_permission(self, request, view):
        return request.user.is_authenticated and getattr(request.user, "is_system_admin", False)


class UserViewSet(viewsets.ViewSet):
    """CRUD endpoints for non-admin users using the service layer."""
    permission_classes = [IsAuthenticated, IsSystemAdmin]


    def list(self, request: Request) -> Response:
        users = UserService.list_users()
        data = UserSerializer(users, many=True, context={'request': request}).data
        return Response(data)

    @action(detail=True, methods=['post'])
    def approve(self, request, pk=None):
        """
        Admin duyệt user mới đăng ký
        """
        try:
            user = UserService.get_user(int(pk))
            user.is_approved = True
            user.save()
            return Response({'detail': f'User {user.username} đã được duyệt.'})
        except ValidationError:
            return Response({'detail': 'User không tồn tại.'}, status=404)

    def retrieve(self, request: Request, pk: str | int = None) -> Response:
        try:
            user = UserService.get_user(int(pk))
        except DjangoValidationError as e:
            return Response({'detail': 'Not found.'}, status=status.HTTP_404_NOT_FOUND)
        data = UserSerializer(user, context={'request': request}).data
        return Response(data)

    # def create(self, request: Request) -> Response:
    #     serializer = UserSerializer(data=request.data, context={'request': request})
    #     serializer.is_valid(raise_exception=True)
    #     try:
    #         user = UserService.create_user(serializer.validated_data)
    #     except DjangoValidationError as e:
    #         return Response({'detail': str(e)}, status=status.HTTP_400_BAD_REQUEST)
    #     out = UserSerializer(user, context={'request': request}).data
    #     return Response(out, status=status.HTTP_201_CREATED)

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



class ProfileView(APIView):
    """
    User bình thường xem và chỉnh sửa profile của chính mình.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        serializer = UserSerializer(request.user, context={'request': request})
        return Response(serializer.data)

    def patch(self, request):
        serializer = UserSerializer(request.user, data=request.data, partial=True, context={'request': request})
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)



class LoginView(View):
    template_name = 'login.html'

    def get(self, request):
        return render(request, self.template_name)

    def post(self, request):
        identifier = request.POST.get('email') or ''  # can be email or username
        password = request.POST.get('password') or ''
        remember = request.POST.get('remember')
        error = None
        user = None  # initialize to avoid potential unbound warning
        try:
            # Bỏ qua kiểm tra duyệt ở bước auth để tự xử lý redirect theo yêu cầu
            user = UserService.authenticate(identifier, password, enforce_approval=False)
        except DjangoValidationError as e:
            error = str(e)
        if error:
            context = {'error': error, 'email_value': identifier}
            return render(request, self.template_name, context, status=400)
        # Nếu chưa được duyệt: thông báo và về trang chủ, KHÔNG đăng nhập
        if not getattr(user, 'is_approved', False) and not getattr(user, 'is_system_admin', False):
            messages.warning(request, 'Tài khoản của bạn chưa được admin duyệt. Vui lòng quay lại sau.')
            return redirect('home')
        # Log the user in
        auth_login(request, user)
        if not remember:
            request.session.set_expiry(0)
        next_url = request.GET.get('next')
        if next_url:
            return redirect(next_url)
        if getattr(user, 'is_system_admin', False):
            return redirect('admin_dashboard')
        return redirect('product_list')


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
        # Do NOT auto-login nếu chưa được duyệt
        if getattr(user, 'is_system_admin', False):
            auth_login(request, user)
            return redirect('admin_dashboard')
        if not getattr(user, 'is_approved', False):
            messages.warning(request, 'Đăng ký thành công. Tài khoản đang chờ admin duyệt trước khi sử dụng.')
            return redirect('home')
        # In case hệ thống có cơ chế auto-duyệt nào đó
        auth_login(request, user)
        return redirect('product_list')


class AdminDashboardView(View):
    template_name = 'admin_dashboard.html'

    @method_decorator(never_cache)
    def dispatch(self, request, *args, **kwargs):
        # Only allow logged-in system admins
        if not request.user.is_authenticated:
            return redirect('login')
        if not getattr(request.user, 'is_system_admin', False):
            return redirect('product_list')
        return super().dispatch(request, *args, **kwargs)

    def get(self, request):
        # Basic counts for header stats (lazy, can optimize later)
        from user.models import User as UserModel
        from payment.models import Order, Payment
        user_count = UserModel.objects.filter(is_staff=False, is_superuser=False).count()
        pending_users = UserModel.objects.filter(is_approved=False, is_staff=False, is_superuser=False).count()
        order_count = Order.objects.count()
        payment_count = Payment.objects.count()
        context = {
            'user_count': user_count,
            'pending_users': pending_users,
            'order_count': order_count,
            'payment_count': payment_count,
        }
        return render(request, self.template_name, context)
