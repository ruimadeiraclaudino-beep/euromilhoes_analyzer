"""
Views para a aplicacao Totoloto.
"""
import json
from django.shortcuts import render, redirect
from django.views.generic import ListView, TemplateView
from django.contrib import messages

from .models import SorteioTotoloto, EstatisticaNumeroTotoloto, ApostaGeradaTotoloto
from .services import AnalisadorTotoloto, GeradorTotoloto


class DashboardTotolotoView(TemplateView):
    """Vista principal do Totoloto."""
    template_name = 'totoloto/dashboard.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context['total_sorteios'] = SorteioTotoloto.objects.count()
        context['ultimo_sorteio'] = SorteioTotoloto.objects.first()

        # Numeros quentes e frios
        context['numeros_quentes'] = EstatisticaNumeroTotoloto.objects.order_by('-frequencia')[:10]
        context['numeros_frios'] = EstatisticaNumeroTotoloto.objects.order_by('frequencia')[:10]
        context['numeros_atrasados'] = EstatisticaNumeroTotoloto.objects.order_by('-dias_sem_sair')[:10]

        # Ultimos sorteios
        context['ultimos_sorteios'] = SorteioTotoloto.objects.all()[:10]

        # Dados para graficos
        estatisticas = EstatisticaNumeroTotoloto.objects.all().order_by('numero')
        context['numeros_labels'] = json.dumps([e.numero for e in estatisticas])
        context['numeros_frequencias'] = json.dumps([e.frequencia for e in estatisticas])

        return context


class SorteiosTotolotoListView(ListView):
    """Lista todos os sorteios do Totoloto."""
    model = SorteioTotoloto
    template_name = 'totoloto/sorteios_list.html'
    context_object_name = 'sorteios'
    paginate_by = 50
    ordering = ['-data']


class EstatisticasTotolotoView(ListView):
    """Estatisticas dos numeros do Totoloto."""
    model = EstatisticaNumeroTotoloto
    template_name = 'totoloto/estatisticas.html'
    context_object_name = 'estatisticas'
    ordering = ['numero']

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['ordem'] = self.request.GET.get('ordem', 'numero')
        return context

    def get_ordering(self):
        ordem = self.request.GET.get('ordem', 'numero')
        ordenacoes = {
            'numero': 'numero',
            'frequencia': '-frequencia',
            'dias_sem_sair': '-dias_sem_sair',
        }
        return ordenacoes.get(ordem, 'numero')


class GeradorTotolotoView(TemplateView):
    """Gerador de apostas Totoloto."""
    template_name = 'totoloto/gerador.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['estrategias'] = ApostaGeradaTotoloto.ESTRATEGIAS
        context['apostas_recentes'] = ApostaGeradaTotoloto.objects.all()[:20]
        return context

    def post(self, request, *args, **kwargs):
        estrategia = request.POST.get('estrategia', 'aleatorio')
        quantidade = int(request.POST.get('quantidade', 1))
        quantidade = min(max(quantidade, 1), 10)

        gerador = GeradorTotoloto()
        for _ in range(quantidade):
            gerador.gerar_e_guardar(estrategia)

        messages.success(request, f'{quantidade} aposta(s) gerada(s) com estrategia "{estrategia}"!')
        return redirect('totoloto:gerador')


class VerificadorTotolotoView(TemplateView):
    """Verificador de apostas Totoloto."""
    template_name = 'totoloto/verificador.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['total_sorteios'] = SorteioTotoloto.objects.count()
        return context

    def post(self, request, *args, **kwargs):
        # Obter numeros do formulario
        numeros = []
        for i in range(1, 6):
            num = request.POST.get(f'numero{i}')
            if num:
                numeros.append(int(num))

        if len(numeros) != 5:
            messages.error(request, 'Introduza 5 numeros validos.')
            return redirect('totoloto:verificador')

        # Verificar contra historico
        resultados = []
        for sorteio in SorteioTotoloto.objects.all():
            acertos = len(set(numeros) & set(sorteio.get_numeros()))
            if acertos >= 2:
                resultados.append({
                    'sorteio': sorteio,
                    'acertos': acertos,
                })

        resultados.sort(key=lambda x: x['sorteio'].data, reverse=True)

        context = self.get_context_data()
        context['numeros'] = sorted(numeros)
        context['resultados'] = resultados
        context['total_vitorias'] = len(resultados)

        return self.render_to_response(context)
