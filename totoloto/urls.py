"""
URL configuration for Totoloto app.
"""
from django.urls import path
from . import views

app_name = 'totoloto'

urlpatterns = [
    path('', views.DashboardTotolotoView.as_view(), name='dashboard'),
    path('sorteios/', views.SorteiosTotolotoListView.as_view(), name='sorteios'),
    path('estatisticas/', views.EstatisticasTotolotoView.as_view(), name='estatisticas'),
    path('gerador/', views.GeradorTotolotoView.as_view(), name='gerador'),
    path('verificador/', views.VerificadorTotolotoView.as_view(), name='verificador'),
]
