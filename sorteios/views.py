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
from .ml import PrevisaoML


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


class AnalisePadroesView(TemplateView):
    """Vista para analise de padroes nos sorteios."""
    template_name = 'sorteios/analise_padroes.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        analisador = AnalisadorEstatistico()
        padroes = analisador.get_analise_padroes_completa()

        context['total_sorteios'] = padroes['total_sorteios']
        context['combinacoes_pares'] = padroes['combinacoes_pares'][:10]
        context['combinacoes_trios'] = padroes['combinacoes_trios'][:10]
        context['consecutivos'] = padroes['consecutivos']
        context['dezenas'] = padroes['dezenas']
        context['terminacoes'] = padroes['terminacoes']
        context['sequencias'] = padroes['sequencias'][:10]
        context['tendencias'] = padroes['tendencias_soma']

        return context


class PrevisaoMLView(TemplateView):
    """Vista para previsoes ML (experimental)."""
    template_name = 'sorteios/previsao_ml.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        ml = PrevisaoML()
        analise = ml.get_analise_completa()

        context['previsao_equilibrada'] = analise['previsao_equilibrada']
        context['previsao_frequencia'] = analise['previsao_frequencia']
        context['previsao_atraso'] = analise['previsao_atraso']
        context['previsao_tendencia'] = analise['previsao_tendencia']
        context['ranking_numeros'] = analise['ranking_numeros']
        context['ranking_estrelas'] = analise['ranking_estrelas']
        context['precisao'] = analise['precisao_historica']
        context['total_sorteios'] = analise['total_sorteios']

        return context


# API endpoints para padroes e ML

def api_padroes(request):
    """API endpoint para analise de padroes."""
    analisador = AnalisadorEstatistico()
    padroes = analisador.get_analise_padroes_completa()

    # Converter tuplas para listas para JSON
    result = {
        'total_sorteios': padroes['total_sorteios'],
        'combinacoes_pares': [
            {'numeros': list(combo), 'frequencia': freq}
            for combo, freq in padroes['combinacoes_pares']
        ],
        'combinacoes_trios': [
            {'numeros': list(combo), 'frequencia': freq}
            for combo, freq in padroes['combinacoes_trios']
        ],
        'consecutivos': padroes['consecutivos'],
        'dezenas': padroes['dezenas'],
        'terminacoes': padroes['terminacoes'],
        'sequencias': [
            {'numeros': list(seq), 'frequencia': freq}
            for seq, freq in padroes['sequencias']
        ],
        'tendencias_soma': padroes['tendencias_soma']
    }

    # Converter datas para strings
    if 'exemplos' in result['consecutivos']:
        for ex in result['consecutivos']['exemplos']:
            ex['data'] = ex['data'].isoformat()

    # Converter padroes de dezenas
    if 'padroes_comuns' in result['dezenas']:
        result['dezenas']['padroes_comuns'] = [
            {'padrao': list(p), 'frequencia': f}
            for p, f in result['dezenas']['padroes_comuns']
        ]

    return JsonResponse(result)


def api_previsao_ml(request):
    """API endpoint para previsao ML."""
    estrategia = request.GET.get('estrategia', 'equilibrada')

    ml = PrevisaoML()
    previsao = ml.prever_proximos_numeros(estrategia)

    return JsonResponse(previsao)


def api_ranking_ml(request):
    """API endpoint para ranking ML de numeros e estrelas."""
    ml = PrevisaoML()

    return JsonResponse({
        'numeros': ml.get_ranking_numeros(),
        'estrelas': ml.get_ranking_estrelas()
    })


def api_precisao_ml(request):
    """API endpoint para analise de precisao do modelo."""
    janela = int(request.GET.get('janela', 50))
    janela = min(max(janela, 20), 200)  # Limitar entre 20 e 200

    ml = PrevisaoML()
    precisao = ml.analisar_precisao_historica(janela)

    return JsonResponse(precisao)


class GraficosAvancadosView(TemplateView):
    """Vista para graficos avancados com heatmaps e tendencias."""
    template_name = 'sorteios/graficos_avancados.html'

    def get_context_data(self, **kwargs):
        import json
        from collections import defaultdict

        context = super().get_context_data(**kwargs)

        # Dados para heatmap de frequencia por numero
        estatisticas_numeros = list(
            EstatisticaNumero.objects.all().order_by('numero')
            .values('numero', 'frequencia', 'dias_sem_sair')
        )
        context['estatisticas_numeros_json'] = json.dumps(estatisticas_numeros)

        # Dados para heatmap de estrelas
        estatisticas_estrelas = list(
            EstatisticaEstrela.objects.all().order_by('estrela')
            .values('estrela', 'frequencia', 'dias_sem_sair')
        )
        context['estatisticas_estrelas_json'] = json.dumps(estatisticas_estrelas)

        # Dados para tendencias temporais (ultimos 100 sorteios)
        sorteios = Sorteio.objects.order_by('-data')[:100]
        tendencias = []
        for sorteio in reversed(list(sorteios)):
            tendencias.append({
                'data': sorteio.data.isoformat(),
                'soma': sorteio.soma_numeros(),
                'soma_estrelas': sorteio.soma_estrelas(),
                'pares': sum(1 for n in sorteio.get_numeros() if n % 2 == 0),
                'impares': sum(1 for n in sorteio.get_numeros() if n % 2 != 0),
            })
        context['tendencias_json'] = json.dumps(tendencias)

        # Frequencia por ano
        freq_por_ano = defaultdict(lambda: defaultdict(int))
        for sorteio in Sorteio.objects.all():
            ano = sorteio.data.year
            for num in sorteio.get_numeros():
                freq_por_ano[ano][num] += 1

        # Converter defaultdict para dict normal para JSON
        freq_por_ano_dict = {
            str(ano): dict(numeros) for ano, numeros in freq_por_ano.items()
        }
        context['freq_por_ano_json'] = json.dumps(freq_por_ano_dict)

        # Dados para grafico de evolucao de frequencia
        context['total_sorteios'] = Sorteio.objects.count()

        return context


def api_evolucao_frequencia(request):
    """API endpoint para evolucao de frequencia ao longo do tempo."""
    numero = int(request.GET.get('numero', 1))
    sorteios = Sorteio.objects.order_by('data')

    dados = []
    frequencia_acumulada = 0
    total = 0

    for sorteio in sorteios:
        total += 1
        if numero in sorteio.get_numeros():
            frequencia_acumulada += 1

        # Registrar a cada 50 sorteios para nao sobrecarregar
        if total % 50 == 0 or total == sorteios.count():
            dados.append({
                'sorteio': total,
                'data': sorteio.data.isoformat(),
                'frequencia': frequencia_acumulada,
                'percentagem': round(frequencia_acumulada / total * 100, 2)
            })

    return JsonResponse({'numero': numero, 'dados': dados})


def api_heatmap_mensal(request):
    """API endpoint para heatmap de frequencia mensal."""
    from collections import defaultdict

    # Estrutura: {ano: {mes: {numero: frequencia}}}
    dados = defaultdict(lambda: defaultdict(lambda: defaultdict(int)))

    for sorteio in Sorteio.objects.all():
        ano = sorteio.data.year
        mes = sorteio.data.month
        for num in sorteio.get_numeros():
            dados[ano][mes][num] += 1

    # Converter para formato serializavel
    resultado = {}
    for ano, meses in dados.items():
        resultado[ano] = {}
        for mes, numeros in meses.items():
            resultado[ano][mes] = dict(numeros)

    return JsonResponse(resultado)


def api_correlacao_numeros(request):
    """API endpoint para matriz de correlacao entre numeros."""
    from collections import defaultdict

    # Contar co-ocorrencias
    co_ocorrencias = defaultdict(lambda: defaultdict(int))

    for sorteio in Sorteio.objects.all():
        numeros = sorteio.get_numeros()
        for i, n1 in enumerate(numeros):
            for n2 in numeros[i+1:]:
                co_ocorrencias[n1][n2] += 1
                co_ocorrencias[n2][n1] += 1

    # Converter para matriz
    matriz = []
    for i in range(1, 51):
        linha = []
        for j in range(1, 51):
            if i == j:
                linha.append(0)
            else:
                linha.append(co_ocorrencias[i].get(j, 0))
        matriz.append(linha)

    return JsonResponse({'matriz': matriz, 'labels': list(range(1, 51))})
