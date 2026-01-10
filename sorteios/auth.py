"""
Views de autenticação para a API.
"""
from django.contrib.auth import authenticate
from django.contrib.auth.models import User
from rest_framework import status
from rest_framework.authtoken.models import Token
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import serializers


class LoginSerializer(serializers.Serializer):
    """Serializer para login."""
    username = serializers.CharField()
    password = serializers.CharField(write_only=True)


class RegisterSerializer(serializers.Serializer):
    """Serializer para registo de utilizadores."""
    username = serializers.CharField(min_length=3, max_length=150)
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, min_length=4)

    def validate_username(self, value):
        if User.objects.filter(username=value).exists():
            raise serializers.ValidationError("Username já existe.")
        return value

    def validate_email(self, value):
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("Email já registado.")
        return value


class UserSerializer(serializers.ModelSerializer):
    """Serializer para dados do utilizador."""
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'date_joined']


class LoginView(APIView):
    """
    Endpoint para login e obtenção de token.

    POST /api/auth/login/
    Body: {"username": "user", "password": "pass"}
    Returns: {"token": "...", "user": {...}}
    """
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = authenticate(
            username=serializer.validated_data['username'],
            password=serializer.validated_data['password']
        )

        if not user:
            return Response(
                {'error': 'Credenciais inválidas'},
                status=status.HTTP_401_UNAUTHORIZED
            )

        token, created = Token.objects.get_or_create(user=user)

        return Response({
            'token': token.key,
            'user': UserSerializer(user).data
        })


class LogoutView(APIView):
    """
    Endpoint para logout (invalidar token).

    POST /api/auth/logout/
    Headers: Authorization: Token <token>
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        # Apagar token do utilizador
        request.user.auth_token.delete()
        return Response({'message': 'Logout efetuado com sucesso'})


class RegisterView(APIView):
    """
    Endpoint para registo de novos utilizadores.

    POST /api/auth/register/
    Body: {"username": "user", "email": "email@example.com", "password": "pass"}
    Returns: {"token": "...", "user": {...}}
    """
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = User.objects.create_user(
            username=serializer.validated_data['username'],
            email=serializer.validated_data['email'],
            password=serializer.validated_data['password']
        )

        token = Token.objects.create(user=user)

        return Response({
            'token': token.key,
            'user': UserSerializer(user).data
        }, status=status.HTTP_201_CREATED)


class ProfileView(APIView):
    """
    Endpoint para ver/atualizar perfil do utilizador autenticado.

    GET /api/auth/profile/
    Returns: {"user": {...}, "apostas_geradas": N}
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        from .models import ApostaGerada

        return Response({
            'user': UserSerializer(request.user).data,
            'apostas_geradas': ApostaGerada.objects.count(),
            'is_staff': request.user.is_staff
        })


class RefreshTokenView(APIView):
    """
    Endpoint para regenerar token.

    POST /api/auth/refresh/
    Headers: Authorization: Token <token>
    Returns: {"token": "new_token"}
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        # Apagar token antigo e criar novo
        request.user.auth_token.delete()
        new_token = Token.objects.create(user=request.user)

        return Response({
            'token': new_token.key,
            'message': 'Token regenerado com sucesso'
        })
