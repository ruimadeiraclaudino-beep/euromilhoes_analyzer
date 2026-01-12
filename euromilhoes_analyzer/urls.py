"""
URL configuration for euromilhoes_analyzer project.
"""
from django.contrib import admin
from django.urls import path, include
from rest_framework.routers import DefaultRouter

from sorteios.api import (
    SorteioViewSet, EstatisticaNumeroViewSet, EstatisticaEstrelaViewSet,
    ApostaViewSet, EstatisticasGeraisView, VerificarApostaView
)
from sorteios.auth import (
    LoginView, LogoutView, RegisterView, ProfileView, RefreshTokenView
)

# Router para API REST
router = DefaultRouter()
router.register(r'sorteios', SorteioViewSet, basename='api-sorteios')
router.register(r'estatisticas/numeros', EstatisticaNumeroViewSet, basename='api-numeros')
router.register(r'estatisticas/estrelas', EstatisticaEstrelaViewSet, basename='api-estrelas')
router.register(r'apostas', ApostaViewSet, basename='api-apostas')

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('sorteios.urls')),
    path('totoloto/', include('totoloto.urls')),
    path('eurodreams/', include('eurodreams.urls')),

    # API REST
    path('api/', include(router.urls)),
    path('api/estatisticas/', EstatisticasGeraisView.as_view(), name='api-estatisticas'),
    path('api/verificar/', VerificarApostaView.as_view(), name='api-verificar'),

    # Autenticação
    path('api/auth/login/', LoginView.as_view(), name='api-login'),
    path('api/auth/logout/', LogoutView.as_view(), name='api-logout'),
    path('api/auth/register/', RegisterView.as_view(), name='api-register'),
    path('api/auth/profile/', ProfileView.as_view(), name='api-profile'),
    path('api/auth/refresh/', RefreshTokenView.as_view(), name='api-refresh-token'),
]
