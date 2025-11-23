from typing import Any, Dict, Optional
from django.contrib.auth import get_user_model
from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.db import IntegrityError, transaction
from django.db.models import Q
import re

User = get_user_model()


class UserService:
    """Service layer for managing non-admin users (no staff/superuser)."""

    @staticmethod
    def _assert_non_admin_payload(payload: Dict[str, Any]) -> None:
        # Prevent elevating privileges via payload
        if payload.get('is_staff') or payload.get('is_superuser'):
            raise ValidationError('Admin flags are not allowed for this resource.')

    @staticmethod
    def list_users() -> list[User]:
        return list(User.objects.filter(is_staff=False, is_superuser=False).order_by('id'))

    @staticmethod
    def get_user(user_id: int) -> User:
        try:
            user = User.objects.get(id=user_id, is_staff=False, is_superuser=False)
        except ObjectDoesNotExist:
            raise ValidationError('User not found')
        return user

    @staticmethod
    @transaction.atomic
    def create_user(payload: Dict[str, Any]) -> User:
        UserService._assert_non_admin_payload(payload)
        username: str = payload.get('username') or ''
        email: str = payload.get('email') or ''
        password: Optional[str] = payload.get('password')
        first_name: str = payload.get('first_name') or ''
        last_name: str = payload.get('last_name') or ''
        if not username:
            raise ValidationError('username is required')
        if not password:
            raise ValidationError('password is required')
        try:
            user = User(
                username=username,
                email=email,
                first_name=first_name,
                last_name=last_name,
                is_staff=False,
                is_superuser=False,
            )
            user.set_password(password)
            user.full_clean(exclude=['password'])
            user.save()
            return user
        except IntegrityError as e:
            raise ValidationError(f'Integrity error: {e}')

    @staticmethod
    @transaction.atomic
    def update_user(user_id: int, payload: Dict[str, Any]) -> User:
        UserService._assert_non_admin_payload(payload)
        user = UserService.get_user(user_id)
        # Only allow a limited set of fields to be updated
        for field in ['username', 'email', 'first_name', 'last_name', 'is_active', 'phone', 'account_type',
                      'store_name', 'address']:
            if field in payload and payload[field] is not None:
                setattr(user, field, payload[field])
        if 'password' in payload and payload['password']:
            user.set_password(payload['password'])
        user.full_clean(exclude=['password'])
        user.save()
        return user

    @staticmethod
    @transaction.atomic
    def delete_user(user_id: int) -> None:
        user = UserService.get_user(user_id)
        user.delete()

    # --- Auth ---
    @staticmethod
    def authenticate(identifier: str, password: str, *, enforce_approval: bool = True) -> User:
        """
        Authenticate a user by username OR email and return the user if valid.
        - If enforce_approval is True (default), unapproved users are rejected.
        - If False, approval is ignored (used to allow custom post-login handling).
        Raises ValidationError on failure.
        """
        ident = (identifier or '').strip()
        if not ident or not password:
            raise ValidationError('Email/Username and password are required')

        # Try username first, then email
        try:
            user = User.objects.get(Q(username__iexact=ident) | Q(email__iexact=ident))
        except ObjectDoesNotExist:
            raise ValidationError('Invalid credentials')
        except Exception:
            # In case of multiple matches by email or other issues, don't leak info
            raise ValidationError('Invalid credentials')

        if not user.is_active:
            raise ValidationError('Tài khoản đã bị vô hiệu hóa')
        if not user.check_password(password):
            raise ValidationError('Invalid credentials')
        if enforce_approval and not getattr(user, 'is_approved', False):
            raise ValidationError('Tài khoản của bạn chưa được admin duyệt')
        return user

    # --- Registration ---
    @staticmethod
    def _sanitize_base_username(s: str) -> str:
        s = s.lower()
        s = re.sub(r'[^a-z0-9._-]', '', s)
        s = s.strip('._-')
        return s or 'user'

    @staticmethod
    def generate_username_from_email(email: str) -> str:
        base = (email or '').split('@')[0]
        base = UserService._sanitize_base_username(base)
        candidate = base
        idx = 1
        while User.objects.filter(username__iexact=candidate).exists():
            idx += 1
            candidate = f"{base}{idx}"
        return candidate

    @staticmethod
    @transaction.atomic
    def register(payload: Dict[str, Any]) -> User:
        """
        Create a new non-admin user from registration payload.
        Required: first_name, last_name, email, phone, account_type, store_name, password, password_confirm, terms.
        Optional: address.
        """
        # Basic required checks
        email = (payload.get('email') or '').strip()
        password = payload.get('password') or ''
        password_confirm = payload.get('password_confirm') or ''
        first_name = (payload.get('first_name') or '').strip()
        last_name = (payload.get('last_name') or '').strip()
        phone = (payload.get('phone') or '').strip()
        account_type = (payload.get('account_type') or '').strip()
        store_name = (payload.get('store_name') or '').strip()
        address = (payload.get('address') or '').strip()
        terms = payload.get('terms')

        if not terms:
            raise ValidationError('Bạn phải đồng ý với điều khoản.')
        if not email:
            raise ValidationError('Email là bắt buộc.')
        if not first_name or not last_name:
            raise ValidationError('Họ tên là bắt buộc.')
        if not phone:
            raise ValidationError('Số điện thoại là bắt buộc.')
        if account_type not in ['store', 'enterprise', 'individual']:
            raise ValidationError('Loại tài khoản không hợp lệ.')
        if not store_name:
            raise ValidationError('Tên cửa hàng/công ty là bắt buộc.')
        if len(password) < 8:
            raise ValidationError('Mật khẩu phải có ít nhất 8 ký tự.')
        if password != password_confirm:
            raise ValidationError('Mật khẩu xác nhận không khớp.')

        # Ensure unique email
        if User.objects.filter(email__iexact=email).exists():
            raise ValidationError('Email đã được sử dụng.')

        username = UserService.generate_username_from_email(email)

        user = User(
            username=username,
            email=email,
            first_name=first_name,
            last_name=last_name,
            phone=phone,
            account_type=account_type,
            # store_name=store_name,
            # address=address,
            is_staff=False,
            is_superuser=False,
            is_approved=False,
        )
        user.set_password(password)
        user.full_clean(exclude=['password'])
        user.save()
        if account_type == 'store':
            from store.models import Store, StoreCategory
            def generate_store_code(store_name: str) -> str:
                base_code = re.sub(r'[^a-zA-Z0-9]', '', store_name).lower()
                candidate = base_code
                idx = 1
                while Store.objects.filter(code=candidate).exists():
                    idx += 1
                    candidate = f"{base_code}{idx}"
                return candidate

            # Ví dụ: gán category mặc định nếu chưa chọn
            default_category, _ = StoreCategory.objects.get_or_create(name='Khác')
            Store.objects.create(
                name=store_name,
                address=address,
                owner=user,
                code=generate_store_code(store_name),
                category=default_category,
                status=Store.Status.ACTIVE
            )
        return user
