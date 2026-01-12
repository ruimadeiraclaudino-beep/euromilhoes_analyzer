"""
URL configuration for EuroDreams app.
"""
from django.urls import path
from . import views

app_name = 'eurodreams'

urlpatterns = [
    path('', views.DashboardEuroDreamsView.as_view(), name='dashboard'),
    path('sorteios/', views.SorteiosEuroDreamsListView.as_view(), name='sorteios'),
    path('estatisticas/', views.EstatisticasEuroDreamsView.as_view(), name='estatisticas'),
    path('gerador/', views.GeradorEuroDreamsView.as_view(), name='gerador'),
]
