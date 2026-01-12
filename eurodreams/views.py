"""
Views para a aplicacao EuroDreams.
"""
import json
from django.shortcuts import render, redirect
from django.views.generic import ListView, TemplateView
from django.contrib import messages

from .models import SorteioEuroDreams, EstatisticaNumeroEuroDreams, EstatisticaDreamEuroDreams, ApostaGeradaEuroDreams
from .services import GeradorEuroDreams


class DashboardEuroDreamsView(TemplateView):
    """Vista principal do EuroDreams."""
    template_name = 'eurodreams/dashboard.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context['total_sorteios'] = SorteioEuroDreams.objects.count()
        context['ultimo_sorteio'] = SorteioEuroDreams.objects.first()

        context['numeros_quentes'] = EstatisticaNumeroEuroDreams.objects.order_by('-frequencia')[:10]
        context['numeros_frios'] = EstatisticaNumeroEuroDreams.objects.order_by('frequencia')[:10]
        context['dreams'] = EstatisticaDreamEuroDreams.objects.order_by('dream')

        context['ultimos_sorteios'] = SorteioEuroDreams.objects.all()[:10]

        estatisticas = EstatisticaNumeroEuroDreams.objects.all().order_by('numero')
        context['numeros_labels'] = json.dumps([e.numero for e in estatisticas])
        context['numeros_frequencias'] = json.dumps([e.frequencia for e in estatisticas])

        return context


class SorteiosEuroDreamsListView(ListView):
    """Lista todos os sorteios do EuroDreams."""
    model = SorteioEuroDreams
    template_name = 'eurodreams/sorteios_list.html'
    context_object_name = 'sorteios'
    paginate_by = 50
    ordering = ['-data']


class EstatisticasEuroDreamsView(ListView):
    """Estatisticas dos numeros do EuroDreams."""
    model = EstatisticaNumeroEuroDreams
    template_name = 'eurodreams/estatisticas.html'
    context_object_name = 'estatisticas'
    ordering = ['numero']

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['dreams'] = EstatisticaDreamEuroDreams.objects.order_by('dream')
        return context


class GeradorEuroDreamsView(TemplateView):
    """Gerador de apostas EuroDreams."""
    template_name = 'eurodreams/gerador.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['estrategias'] = ApostaGeradaEuroDreams.ESTRATEGIAS
        context['apostas_recentes'] = ApostaGeradaEuroDreams.objects.all()[:20]
        return context

    def post(self, request, *args, **kwargs):
        estrategia = request.POST.get('estrategia', 'aleatorio')
        quantidade = int(request.POST.get('quantidade', 1))
        quantidade = min(max(quantidade, 1), 10)

        gerador = GeradorEuroDreams()
        for _ in range(quantidade):
            gerador.gerar_e_guardar(estrategia)

        messages.success(request, f'{quantidade} aposta(s) gerada(s)!')
        return redirect('eurodreams:gerador')
