from rest_framework import status, permissions
from rest_framework.views import APIView, Response

from django.contrib.auth import login, logout
from drf_yasg.utils import swagger_auto_schema

from . import serializers


class LoginView(APIView):
    """ Log in with credentials """

    permission_classes = permissions.AllowAny,

    @swagger_auto_schema(
        request_body=serializers.LoginSerializer,
        responses={
            '200': 'Successfully logged in',
            '400': 'Wrong credentials or user is inactive or already logged in',
        }
    )
    def post(self, request):
        if request.user.is_authenticated:
            return Response(
                {'detail': 'You are already logged in.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        serializer = serializers.LoginSerializer(
            data=request.data,
            context={'request': request, 'view': self}
        )

        serializer.is_valid(raise_exception=True)
        login(request, serializer.user)
        return Response({'detail': 'Successfully logged in.'})


class LogoutView(APIView):
    @staticmethod
    def get(request):
        logout(request)
        return Response({'detail': 'Successfully logged out.'})
