from django.contrib.auth import authenticate, get_user_model

from rest_framework import serializers
from rest_framework.exceptions import ValidationError

User = get_user_model()
USERNAME_LENGTH = User._meta.get_field(User.USERNAME_FIELD).max_length
PASSWORD_LENGTH = User._meta.get_field('password').max_length


class LoginSerializer(serializers.Serializer):
    username = serializers.CharField(required=True, max_length=USERNAME_LENGTH)
    password = serializers.CharField(required=True, max_length=PASSWORD_LENGTH)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.user = None

    def validate(self, attrs: dict) -> dict:
        """ Find user instance by the given credentials """

        self.user = authenticate(self.context['request'], **attrs)

        if self.user is None:
            raise ValidationError({'detail': 'User not found by the given credentials.'})

        return attrs
