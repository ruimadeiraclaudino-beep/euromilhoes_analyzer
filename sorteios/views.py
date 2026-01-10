"""
Views para a aplicação EuroMilhões Analyzer.
"""
from django.shortcuts import render, redirect, get_object_or_404
from django.views.generic import ListView, DetailView, TemplateView
from django.http import JsonResponse
from django.db.models import Avg, Max, Min, Count
from django.contrib import messages

from .models import Sorteio, EstatisticaNumero, EstatisticaEstrela, ApostaGerada
from .services import AnalisadorEstatistico, GeradorApostas


class DashboardView(TemplateView):
    """Vista principal com resumo das estatísticas."""
    template_name = 'sorteios/dashboard.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Estatísticas gerais
        context['total_sorteios'] = Sorteio.objects.count()
        context['ultimo_sorteio'] = Sorteio.objects.first()
        
        # Números quentes e frios
        context['numeros_quentes'] = EstatisticaNumero.objects.order_by('-frequencia')[:10]
        context['numeros_frios'] = EstatisticaNumero.objects.order_by('frequencia')[:10]
        context['numeros_atrasados'] = EstatisticaNumero.objects.order_by('-dias_sem_sair')[:10]
        
        # Estrelas
        context['estrelas_quentes'] = EstatisticaEstrela.objects.order_by('-frequencia')[:5]
        context['estrelas_frias'] = EstatisticaEstrela.objects.order_by('frequencia')[:5]
        
        # Últimos sorteios
        context['ultimos_sorteios'] = Sorteio.objects.all()[:10]
        
        # Dados para gráficos
        estatisticas_numeros = EstatisticaNumero.objects.all().order_by('numero')
        context['numeros_labels'] = [e.numero for e in estatisticas_numeros]
        context['numeros_frequencias'] = [e.frequencia for e in estatisticas_numeros]
        
        estatisticas_estrelas = EstatisticaEstrela.objects.all().order_by('estrela')
        context['estrelas_labels'] = [e.estrela for e in estatisticas_estrelas]
        context['estrelas_frequencias'] = [e.frequencia for e in estatisticas_estrelas]
        
        return context


class SorteiosListView(ListView):
    """Lista todos os sorteios com paginação."""
    model = Sorteio
    template_name = 'sorteios/sorteios_list.html'
    context_object_name = 'sorteios'
    paginate_by = 50
    ordering = ['-data']


class SorteioDetailView(DetailView):
    """Detalhes de um sorteio específico."""
    model = Sorteio
    template_name = 'sorteios/sorteio_detail.html'
    context_object_name = 'sorteio'


class EstatisticasNumerosView(ListView):
    """Estatísticas detalhadas dos números."""
    model = EstatisticaNumero
    template_name = 'sorteios/estatisticas_numeros.html'
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
            'gap_medio': '-gap_medio',
        }
        return ordenacoes.get(ordem, 'numero')


class EstatisticasEstrelasView(ListView):
    """Estatísticas detalhadas das estrelas."""
    model = EstatisticaEstrela
    template_name = 'sorteios/estatisticas_estrelas.html'
    context_object_name = 'estatisticas'
    ordering = ['estrela']


class GeradorApostasView(TemplateView):
    """Interface para gerar apostas."""
    template_name = 'sorteios/gerador_apostas.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['estrategias'] = ApostaGerada.ESTRATEGIAS
        context['apostas_recentes'] = ApostaGerada.objects.all()[:20]
        return context
    
    def post(self, request, *args, **kwargs):
        estrategia = request.POST.get('estrategia', 'aleatorio')
        quantidade = int(request.POST.get('quantidade', 1))
        quantidade = min(max(quantidade, 1), 10)  # Limitar entre 1 e 10
        
        gerador = GeradorApostas()
        apostas = gerador.gerar_multiplas(estrategia, quantidade)
        
        messages.success(
            request, 
            f'{len(apostas)} aposta(s) gerada(s) com estratégia "{estrategia}"!'
        )
        
        return redirect('gerador_apostas')


class AnaliseDistribuicaoView(TemplateView):
    """Análise de distribuição dos sorteios."""
    template_name = 'sorteios/analise_distribuicao.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        analisador = AnalisadorEstatistico()
        distribuicao = analisador.analise_distribuicao()
        
        context['pares_impares'] = dict(distribuicao['pares_impares'])
        context['baixos_altos'] = dict(distribuicao['baixos_altos'])
        
        if distribuicao.get('somas'):
            context['soma_media'] = round(distribuicao['soma_media'], 1)
            context['soma_min'] = distribuicao['soma_min']
            context['soma_max'] = distribuicao['soma_max']
        
        # Combinações mais frequentes
        context['pares_frequentes'] = analisador.combinacoes_frequentes(2)[:10]
        context['trios_frequentes'] = analisador.combinacoes_frequentes(3)[:10]
        
        return context


# API Views para gráficos dinâmicos

def api_frequencias_numeros(request):
    """API endpoint para dados de frequência dos números."""
    estatisticas = EstatisticaNumero.objects.all().order_by('numero')
    data = {
        'labels': [e.numero for e in estatisticas],
        'frequencias': [e.frequencia for e in estatisticas],
        'percentagens': [float(e.percentagem) for e in estatisticas],
    }
    return JsonResponse(data)


def api_frequencias_estrelas(request):
    """API endpoint para dados de frequência das estrelas."""
    estatisticas = EstatisticaEstrela.objects.all().order_by('estrela')
    data = {
        'labels': [e.estrela for e in estatisticas],
        'frequencias': [e.frequencia for e in estatisticas],
        'percentagens': [float(e.percentagem) for e in estatisticas],
    }
    return JsonResponse(data)


def api_evolucao_numero(request, numero):
    """API endpoint para evolução de um número específico."""
    sorteios = Sorteio.objects.order_by('data')
    
    datas = []
    frequencia_acumulada = []
    count = 0
    
    for sorteio in sorteios:
        if numero in sorteio.get_numeros():
            count += 1
        datas.append(sorteio.data.isoformat())
        frequencia_acumulada.append(count)
    
    return JsonResponse({
        'numero': numero,
        'datas': datas,
        'frequencia_acumulada': frequencia_acumulada,
    })


def api_gerar_aposta(request):
    """API endpoint para gerar uma aposta."""
    estrategia = request.GET.get('estrategia', 'aleatorio')
    
    gerador = GeradorApostas()
    aposta = gerador.gerar_e_guardar(estrategia)
    
    return JsonResponse({
        'id': aposta.id,
        'numeros': aposta.get_numeros(),
        'estrelas': aposta.get_estrelas(),
        'estrategia': aposta.get_estrategia_display(),
    })
