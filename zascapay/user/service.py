from typing import Any, Dict, Optional
from django.contrib.auth import get_user_model
from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.db import IntegrityError, transaction

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
        for field in ['username', 'email', 'first_name', 'last_name', 'is_active']:
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

