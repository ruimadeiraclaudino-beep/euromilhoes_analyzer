"""
URL configuration for sorteios app.
"""
from django.urls import path
from . import views

urlpatterns = [
    # Páginas principais
    path('', views.DashboardView.as_view(), name='dashboard'),
    path('sorteios/', views.SorteiosListView.as_view(), name='sorteios_list'),
    path('sorteios/<int:pk>/', views.SorteioDetailView.as_view(), name='sorteio_detail'),
    
    # Estatísticas
    path('estatisticas/numeros/', views.EstatisticasNumerosView.as_view(), name='estatisticas_numeros'),
    path('estatisticas/estrelas/', views.EstatisticasEstrelasView.as_view(), name='estatisticas_estrelas'),
    path('analise/', views.AnaliseDistribuicaoView.as_view(), name='analise_distribuicao'),
    
    # Gerador de apostas
    path('gerador/', views.GeradorApostasView.as_view(), name='gerador_apostas'),
    
    # API endpoints
    path('api/frequencias/numeros/', views.api_frequencias_numeros, name='api_frequencias_numeros'),
    path('api/frequencias/estrelas/', views.api_frequencias_estrelas, name='api_frequencias_estrelas'),
    path('api/evolucao/<int:numero>/', views.api_evolucao_numero, name='api_evolucao_numero'),
    path('api/gerar-aposta/', views.api_gerar_aposta, name='api_gerar_aposta'),
]
