from django.http import JsonResponse
from django.contrib.auth import logout as auth_logout
from django.shortcuts import redirect
from django.utils.deprecation import MiddlewareMixin
from django.contrib import messages


class ApprovalRequiredMiddleware(MiddlewareMixin):
    """
    Chặn toàn bộ hành động của user chưa được duyệt (trừ một số route công khai).
    - HTML: đăng xuất + thông báo cảnh báo + về trang chủ.
    - API (Accept JSON): trả về 403 JSON.
    Admin (is_system_admin=True) không bị chặn.
    """

    PUBLIC_PATH_PREFIXES = (
        '/static/', '/media/',  # assets
    )
    PUBLIC_PATHS = (
        '/',            # home
        '/login/',
        '/register/',
    )

    def process_request(self, request):
        user = getattr(request, 'user', None)
        path = request.path or '/'

        # Allow public paths and static/media early
        if path.startswith(self.PUBLIC_PATH_PREFIXES) or path in self.PUBLIC_PATHS:
            return None

        # Require approval for authenticated non-admin users
        if user and user.is_authenticated and not getattr(user, 'is_system_admin', False):
            if not getattr(user, 'is_approved', False):
                accepts = request.META.get('HTTP_ACCEPT', '')
                is_json = 'application/json' in accepts or request.headers.get('X-Requested-With') == 'XMLHttpRequest'
                auth_logout(request)
                if is_json:
                    return JsonResponse({'detail': 'Tài khoản của bạn chưa được admin duyệt.'}, status=403)
                messages.warning(request, 'Tài khoản của bạn chưa được admin duyệt. Vui lòng quay lại sau.')
                return redirect('home')
        return None
