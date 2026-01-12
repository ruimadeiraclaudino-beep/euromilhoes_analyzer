"""
URL configuration for sorteios app.
"""
from django.urls import path
from . import views

urlpatterns = [
    # Paginas principais
    path('', views.DashboardView.as_view(), name='dashboard'),
    path('sorteios/', views.SorteiosListView.as_view(), name='sorteios_list'),
    path('sorteios/<int:pk>/', views.SorteioDetailView.as_view(), name='sorteio_detail'),

    # Estatisticas
    path('estatisticas/numeros/', views.EstatisticasNumerosView.as_view(), name='estatisticas_numeros'),
    path('estatisticas/estrelas/', views.EstatisticasEstrelasView.as_view(), name='estatisticas_estrelas'),
    path('analise/', views.AnaliseDistribuicaoView.as_view(), name='analise_distribuicao'),

    # Analise de padroes
    path('padroes/', views.AnalisePadroesView.as_view(), name='analise_padroes'),

    # Previsoes ML (experimental)
    path('previsao/', views.PrevisaoMLView.as_view(), name='previsao_ml'),

    # Graficos avancados
    path('graficos/', views.GraficosAvancadosView.as_view(), name='graficos_avancados'),

    # Gerador de apostas
    path('gerador/', views.GeradorApostasView.as_view(), name='gerador_apostas'),

    # API endpoints
    path('api/frequencias/numeros/', views.api_frequencias_numeros, name='api_frequencias_numeros'),
    path('api/frequencias/estrelas/', views.api_frequencias_estrelas, name='api_frequencias_estrelas'),
    path('api/evolucao/<int:numero>/', views.api_evolucao_numero, name='api_evolucao_numero'),
    path('api/gerar-aposta/', views.api_gerar_aposta, name='api_gerar_aposta'),

    # API endpoints para padroes e ML
    path('api/padroes/', views.api_padroes, name='api_padroes'),
    path('api/ml/previsao/', views.api_previsao_ml, name='api_previsao_ml'),
    path('api/ml/ranking/', views.api_ranking_ml, name='api_ranking_ml'),
    path('api/ml/precisao/', views.api_precisao_ml, name='api_precisao_ml'),

    # API endpoints para graficos avancados
    path('api/graficos/evolucao/', views.api_evolucao_frequencia, name='api_evolucao_frequencia'),
    path('api/graficos/heatmap-mensal/', views.api_heatmap_mensal, name='api_heatmap_mensal'),
    path('api/graficos/correlacao/', views.api_correlacao_numeros, name='api_correlacao_numeros'),

    # Autenticacao
    path('conta/login/', views.UserLoginView.as_view(), name='login'),
    path('conta/registar/', views.UserRegisterView.as_view(), name='register'),
    path('conta/logout/', views.user_logout, name='logout'),
    path('conta/perfil/', views.UserProfileView.as_view(), name='profile'),

    # Numeros favoritos e alertas
    path('conta/favoritos/', views.NumerosFavoritosView.as_view(), name='numeros_favoritos'),
    path('conta/alertas/', views.AlertasView.as_view(), name='alertas'),
    path('conta/alertas/<int:pk>/toggle/', views.alerta_toggle, name='alerta_toggle'),
    path('conta/alertas/<int:pk>/delete/', views.alerta_delete, name='alerta_delete'),

    # Novas funcionalidades
    path('verificador/', views.VerificadorApostasView.as_view(), name='verificador'),
    path('analise/dia-semana/', views.AnaliseDiaSemanaView.as_view(), name='analise_dia_semana'),
    path('jackpot/', views.EvolucaoJackpotView.as_view(), name='evolucao_jackpot'),
    path('backtest/', views.BacktestView.as_view(), name='backtest'),
    path('simulador/', views.SimuladorView.as_view(), name='simulador'),
    path('exportar/', views.ExportarPDFView.as_view(), name='exportar_pdf'),
    path('exportar/download/', views.exportar_apostas_pdf, name='exportar_pdf_download'),
]
