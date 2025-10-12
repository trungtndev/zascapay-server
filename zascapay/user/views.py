from django.core.exceptions import ValidationError as DjangoValidationError
from django.contrib.auth import get_user_model
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
