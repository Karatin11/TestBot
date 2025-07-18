from __future__ import annotations

from rest_framework import serializers

from api.user.models import User
from django.contrib.auth import authenticate
from rest_framework import serializers
from rest_framework.exceptions import AuthenticationFailed
from django.contrib.auth import get_user_model


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ("id", "username", "email", "password")
        extra_kwargs = {"password": {"write_only": True}}  # noqa: RUF012

class LoginSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField(write_only=True)
    user = None

    def validate(self, data):
        username = data.get('username')
        password = data.get('password')

        if username and password:
            user = authenticate(username=username, password=password)
            if user is None:
                raise serializers.ValidationError("Неверные учетные данные.")
            if not user.is_active:
                raise serializers.ValidationError("Пользователь неактивен.")
            self.user = user
            data['user'] = user
            return data
        else:
            raise serializers.ValidationError("Введите имя пользователя и пароль.")