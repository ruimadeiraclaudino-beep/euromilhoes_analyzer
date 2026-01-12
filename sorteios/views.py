"""
Views para a aplicação EuroMilhões Analyzer.
"""
from django.shortcuts import render, redirect, get_object_or_404
from django.views.generic import ListView, DetailView, TemplateView, FormView
from django.views.generic.edit import UpdateView
from django.http import JsonResponse, HttpResponse
from django.db.models import Avg, Max, Min, Count
from django.contrib import messages
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy

from .models import Sorteio, EstatisticaNumero, EstatisticaEstrela, ApostaGerada, ApostaMultipla, UserProfile, Alerta
from .services import AnalisadorEstatistico, GeradorApostas
from .forms import LoginForm, RegisterForm, ProfileForm, NumerosFavoritosForm, AlertaForm, VerificadorApostaForm
from .ml import PrevisaoML


class DashboardView(TemplateView):
    """Vista principal com resumo das estatísticas."""
    template_name = 'sorteios/dashboard.html'

    def get_context_data(self, **kwargs):
        import json
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

        # Dados para gráficos (serializados como JSON)
        estatisticas_numeros = EstatisticaNumero.objects.all().order_by('numero')
        context['numeros_labels'] = json.dumps([e.numero for e in estatisticas_numeros])
        context['numeros_frequencias'] = json.dumps([e.frequencia for e in estatisticas_numeros])

        estatisticas_estrelas = EstatisticaEstrela.objects.all().order_by('estrela')
        context['estrelas_labels'] = json.dumps([e.estrela for e in estatisticas_estrelas])
        context['estrelas_frequencias'] = json.dumps([e.frequencia for e in estatisticas_estrelas])

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
    """Interface para gerar apostas simples e múltiplas."""
    template_name = 'sorteios/gerador_apostas.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['estrategias'] = ApostaGerada.ESTRATEGIAS
        context['apostas_recentes'] = ApostaGerada.objects.all()[:20]
        context['apostas_multiplas_recentes'] = ApostaMultipla.objects.all()[:10]
        context['tabela_combinacoes'] = GeradorApostas.calcular_tabela_combinacoes()
        return context

    def post(self, request, *args, **kwargs):
        tipo_aposta = request.POST.get('tipo_aposta', 'simples')
        estrategia = request.POST.get('estrategia', 'aleatorio')
        gerador = GeradorApostas()

        if tipo_aposta == 'multipla':
            n_numeros = int(request.POST.get('n_numeros', 6))
            n_estrelas = int(request.POST.get('n_estrelas', 3))
            n_numeros = min(max(n_numeros, 5), 10)
            n_estrelas = min(max(n_estrelas, 2), 5)

            aposta = gerador.gerar_aposta_multipla(estrategia, n_numeros, n_estrelas)
            messages.success(
                request,
                f'Aposta múltipla gerada: {n_numeros} números + {n_estrelas} estrelas = '
                f'{aposta.total_combinacoes} combinações ({aposta.custo_total:.2f}€)'
            )
        else:
            quantidade = int(request.POST.get('quantidade', 1))
            quantidade = min(max(quantidade, 1), 10)

            apostas = gerador.gerar_multiplas(estrategia, quantidade)
            messages.success(
                request,
                f'{len(apostas)} aposta(s) simples gerada(s) com estratégia "{estrategia}"!'
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


# ============================================
# AUTENTICACAO E PERFIL DE UTILIZADOR
# ============================================

class UserLoginView(FormView):
    """Vista de login."""
    template_name = 'sorteios/auth/login.html'
    form_class = LoginForm
    success_url = reverse_lazy('dashboard')

    def form_valid(self, form):
        user = form.get_user()
        login(self.request, user)
        messages.success(self.request, f'Bem-vindo, {user.username}!')
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Entrar'
        return context


class UserRegisterView(FormView):
    """Vista de registo."""
    template_name = 'sorteios/auth/register.html'
    form_class = RegisterForm
    success_url = reverse_lazy('dashboard')

    def form_valid(self, form):
        user = form.save()
        login(self.request, user)
        messages.success(self.request, f'Conta criada com sucesso! Bem-vindo, {user.username}!')
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Criar Conta'
        return context


def user_logout(request):
    """Vista de logout."""
    logout(request)
    messages.info(request, 'Sessao terminada com sucesso.')
    return redirect('dashboard')


class UserProfileView(LoginRequiredMixin, UpdateView):
    """Vista do perfil do utilizador."""
    template_name = 'sorteios/auth/profile.html'
    form_class = ProfileForm
    success_url = reverse_lazy('profile')
    login_url = reverse_lazy('login')

    def get_object(self):
        profile, created = UserProfile.objects.get_or_create(
            user=self.request.user,
            defaults={'email_alertas': self.request.user.email}
        )
        return profile

    def form_valid(self, form):
        messages.success(self.request, 'Perfil atualizado com sucesso!')
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Meu Perfil'
        context['apostas_count'] = ApostaGerada.objects.count()
        context['alertas_count'] = Alerta.objects.filter(user=self.request.user).count()
        return context


class NumerosFavoritosView(LoginRequiredMixin, FormView):
    """Vista para gerir numeros favoritos."""
    template_name = 'sorteios/numeros_favoritos.html'
    form_class = NumerosFavoritosForm
    success_url = reverse_lazy('numeros_favoritos')
    login_url = reverse_lazy('login')

    def get_initial(self):
        profile = self.get_profile()
        return {
            'numeros': ', '.join(str(n) for n in profile.get_numeros_favoritos()),
            'estrelas': ', '.join(str(e) for e in profile.get_estrelas_favoritas()),
        }

    def get_profile(self):
        profile, _ = UserProfile.objects.get_or_create(
            user=self.request.user,
            defaults={'email_alertas': self.request.user.email}
        )
        return profile

    def form_valid(self, form):
        profile = self.get_profile()
        profile.numeros_favoritos = form.cleaned_data['numeros']
        profile.estrelas_favoritas = form.cleaned_data['estrelas']
        profile.save()
        messages.success(self.request, 'Numeros favoritos atualizados!')
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        profile = self.get_profile()
        context['profile'] = profile

        # Estatisticas dos numeros favoritos
        if profile.numeros_favoritos:
            context['estatisticas_numeros'] = EstatisticaNumero.objects.filter(
                numero__in=profile.numeros_favoritos
            ).order_by('numero')

        if profile.estrelas_favoritas:
            context['estatisticas_estrelas'] = EstatisticaEstrela.objects.filter(
                estrela__in=profile.estrelas_favoritas
            ).order_by('estrela')

        return context


class AlertasView(LoginRequiredMixin, TemplateView):
    """Vista para gerir alertas."""
    template_name = 'sorteios/alertas.html'
    login_url = reverse_lazy('login')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['alertas'] = Alerta.objects.filter(user=self.request.user)
        context['form'] = AlertaForm()
        return context

    def post(self, request, *args, **kwargs):
        form = AlertaForm(request.POST)
        if form.is_valid():
            alerta = form.save(commit=False)
            alerta.user = request.user
            alerta.save()
            messages.success(request, 'Alerta criado com sucesso!')
        else:
            messages.error(request, 'Erro ao criar alerta.')
        return redirect('alertas')


@login_required
def alerta_toggle(request, pk):
    """Ativar/desativar um alerta."""
    alerta = get_object_or_404(Alerta, pk=pk, user=request.user)
    alerta.ativo = not alerta.ativo
    alerta.save()
    status = 'ativado' if alerta.ativo else 'desativado'
    messages.success(request, f'Alerta {status}!')
    return redirect('alertas')


@login_required
def alerta_delete(request, pk):
    """Eliminar um alerta."""
    alerta = get_object_or_404(Alerta, pk=pk, user=request.user)
    alerta.delete()
    messages.success(request, 'Alerta eliminado!')
    return redirect('alertas')


# ============================================
# VERIFICADOR DE APOSTAS
# ============================================

class VerificadorApostasView(FormView):
    """Vista para verificar apostas contra historico."""
    template_name = 'sorteios/verificador.html'
    form_class = VerificadorApostaForm

    def form_valid(self, form):
        numeros = form.cleaned_data['numeros']
        estrelas = form.cleaned_data['estrelas']

        # Verificar contra todos os sorteios
        resultados = []
        for sorteio in Sorteio.objects.all():
            acertos_n = len(set(numeros) & set(sorteio.get_numeros()))
            acertos_e = len(set(estrelas) & set(sorteio.get_estrelas()))
            premio = self._calcular_premio(acertos_n, acertos_e)

            if premio['categoria']:
                resultados.append({
                    'sorteio': sorteio,
                    'acertos_numeros': acertos_n,
                    'acertos_estrelas': acertos_e,
                    'premio': premio,
                })

        # Ordenar por data descendente
        resultados.sort(key=lambda x: x['sorteio'].data, reverse=True)

        context = self.get_context_data(form=form)
        context['resultados'] = resultados
        context['numeros'] = numeros
        context['estrelas'] = estrelas
        context['total_sorteios'] = Sorteio.objects.count()
        context['total_vitorias'] = len(resultados)
        context['resumo'] = self._gerar_resumo(resultados)

        return self.render_to_response(context)

    def _calcular_premio(self, acertos_n, acertos_e):
        """Calcula o premio baseado nos acertos."""
        premios = {
            (5, 2): {'categoria': '1o Premio (Jackpot)', 'ordem': 1},
            (5, 1): {'categoria': '2o Premio', 'ordem': 2},
            (5, 0): {'categoria': '3o Premio', 'ordem': 3},
            (4, 2): {'categoria': '4o Premio', 'ordem': 4},
            (4, 1): {'categoria': '5o Premio', 'ordem': 5},
            (4, 0): {'categoria': '6o Premio', 'ordem': 6},
            (3, 2): {'categoria': '7o Premio', 'ordem': 7},
            (3, 1): {'categoria': '8o Premio', 'ordem': 8},
            (2, 2): {'categoria': '9o Premio', 'ordem': 9},
            (3, 0): {'categoria': '10o Premio', 'ordem': 10},
            (1, 2): {'categoria': '11o Premio', 'ordem': 11},
            (2, 1): {'categoria': '12o Premio', 'ordem': 12},
            (2, 0): {'categoria': '13o Premio', 'ordem': 13},
        }
        return premios.get((acertos_n, acertos_e), {'categoria': None, 'ordem': 99})

    def _gerar_resumo(self, resultados):
        """Gera resumo dos resultados."""
        from collections import Counter
        categorias = Counter(r['premio']['categoria'] for r in resultados)
        return dict(categorias.most_common())


# ============================================
# ANALISE POR DIA DA SEMANA
# ============================================

class AnaliseDiaSemanaView(TemplateView):
    """Analise de padroes por dia da semana (Terca vs Sexta)."""
    template_name = 'sorteios/analise_dia_semana.html'

    def get_context_data(self, **kwargs):
        import json
        from collections import Counter

        context = super().get_context_data(**kwargs)

        # Separar sorteios por dia da semana
        # Terca = 1, Sexta = 4 (weekday())
        sorteios_terca = []
        sorteios_sexta = []

        for sorteio in Sorteio.objects.all():
            if sorteio.data.weekday() == 1:  # Terca
                sorteios_terca.append(sorteio)
            elif sorteio.data.weekday() == 4:  # Sexta
                sorteios_sexta.append(sorteio)

        context['terca'] = self._analisar_dia(sorteios_terca, 'Terca-feira')
        context['sexta'] = self._analisar_dia(sorteios_sexta, 'Sexta-feira')

        # Comparacao
        context['comparacao'] = self._comparar_dias(context['terca'], context['sexta'])

        # Dados para graficos
        context['terca_freq_json'] = json.dumps(context['terca']['frequencias_numeros'])
        context['sexta_freq_json'] = json.dumps(context['sexta']['frequencias_numeros'])

        return context

    def _analisar_dia(self, sorteios, nome):
        """Analisa sorteios de um dia especifico."""
        from collections import Counter

        if not sorteios:
            return {'nome': nome, 'total': 0}

        freq_numeros = Counter()
        freq_estrelas = Counter()
        somas = []
        pares_impares = Counter()

        for sorteio in sorteios:
            for num in sorteio.get_numeros():
                freq_numeros[num] += 1
            for est in sorteio.get_estrelas():
                freq_estrelas[est] += 1
            somas.append(sorteio.soma_numeros())
            pares_impares[sorteio.pares_impares()] += 1

        return {
            'nome': nome,
            'total': len(sorteios),
            'frequencias_numeros': [freq_numeros.get(i, 0) for i in range(1, 51)],
            'frequencias_estrelas': [freq_estrelas.get(i, 0) for i in range(1, 13)],
            'top_numeros': freq_numeros.most_common(10),
            'top_estrelas': freq_estrelas.most_common(5),
            'soma_media': sum(somas) / len(somas) if somas else 0,
            'soma_min': min(somas) if somas else 0,
            'soma_max': max(somas) if somas else 0,
            'pares_impares': dict(pares_impares.most_common()),
        }

    def _comparar_dias(self, terca, sexta):
        """Compara estatisticas entre Terca e Sexta."""
        if terca['total'] == 0 or sexta['total'] == 0:
            return {}

        # Numeros que saem mais numa do que noutra
        diff_numeros = []
        for i in range(50):
            freq_t = terca['frequencias_numeros'][i] / terca['total'] if terca['total'] > 0 else 0
            freq_s = sexta['frequencias_numeros'][i] / sexta['total'] if sexta['total'] > 0 else 0
            diff = freq_t - freq_s
            if abs(diff) > 0.02:  # Diferenca significativa (>2%)
                diff_numeros.append({
                    'numero': i + 1,
                    'diff': round(diff * 100, 2),
                    'favorece': 'Terca' if diff > 0 else 'Sexta',
                })

        diff_numeros.sort(key=lambda x: abs(x['diff']), reverse=True)

        return {
            'diff_soma_media': round(terca['soma_media'] - sexta['soma_media'], 2),
            'numeros_diferentes': diff_numeros[:10],
        }


# ============================================
# EVOLUCAO DO JACKPOT
# ============================================

class EvolucaoJackpotView(TemplateView):
    """Vista para evolucao do jackpot ao longo do tempo."""
    template_name = 'sorteios/evolucao_jackpot.html'

    def get_context_data(self, **kwargs):
        import json
        from decimal import Decimal

        context = super().get_context_data(**kwargs)

        # Obter sorteios com jackpot
        sorteios = Sorteio.objects.exclude(jackpot__isnull=True).order_by('data')

        historico = []
        jackpots = []
        sequencia_atual = 0
        maior_sequencia = 0

        for sorteio in sorteios:
            historico.append({
                'data': sorteio.data.isoformat(),
                'jackpot': float(sorteio.jackpot) if sorteio.jackpot else 0,
                'houve_vencedor': sorteio.houve_vencedor,
            })
            if sorteio.jackpot:
                jackpots.append(float(sorteio.jackpot))

            if sorteio.houve_vencedor:
                if sequencia_atual > maior_sequencia:
                    maior_sequencia = sequencia_atual
                sequencia_atual = 0
            else:
                sequencia_atual += 1

        context['historico_json'] = json.dumps(historico)
        context['total_sorteios'] = len(historico)

        if jackpots:
            context['jackpot_medio'] = round(sum(jackpots) / len(jackpots) / 1000000, 1)
            context['jackpot_maximo'] = round(max(jackpots) / 1000000, 1)
            context['jackpot_minimo'] = round(min(jackpots) / 1000000, 1)
        else:
            context['jackpot_medio'] = 0
            context['jackpot_maximo'] = 0
            context['jackpot_minimo'] = 0

        context['maior_sequencia_sem_vencedor'] = max(maior_sequencia, sequencia_atual)

        # Jackpot atual
        ultimo = Sorteio.objects.first()
        if ultimo and ultimo.jackpot:
            context['jackpot_atual'] = round(float(ultimo.jackpot) / 1000000, 1)
        else:
            context['jackpot_atual'] = 0

        # Contagem de vencedores
        context['total_vencedores'] = Sorteio.objects.filter(houve_vencedor=True).count()

        return context


# ============================================
# BACKTEST DE ESTRATEGIAS
# ============================================

class BacktestView(TemplateView):
    """Vista para backtesting de estrategias."""
    template_name = 'sorteios/backtest.html'

    def get_context_data(self, **kwargs):
        import json
        context = super().get_context_data(**kwargs)
        context['estrategias'] = ApostaGerada.ESTRATEGIAS
        context['total_sorteios_disponivel'] = Sorteio.objects.count()
        return context

    def post(self, request, *args, **kwargs):
        import json
        from collections import Counter

        estrategia = request.POST.get('estrategia', 'frequencia')
        n_sorteios = int(request.POST.get('n_sorteios', 100))
        n_sorteios = min(max(n_sorteios, 10), Sorteio.objects.count())

        # Obter sorteios ordenados por data
        sorteios = list(Sorteio.objects.order_by('-data')[:n_sorteios])

        gerador = GeradorApostas()
        resultados = []
        premios_counter = Counter()
        total_acertos_n = 0
        total_acertos_e = 0

        for sorteio in reversed(sorteios):
            # Gerar aposta usando estrategia
            aposta = gerador.gerar_e_guardar(estrategia)
            numeros_aposta = aposta.get_numeros()
            estrelas_aposta = aposta.get_estrelas()

            acertos_n = len(set(numeros_aposta) & set(sorteio.get_numeros()))
            acertos_e = len(set(estrelas_aposta) & set(sorteio.get_estrelas()))

            total_acertos_n += acertos_n
            total_acertos_e += acertos_e

            premio = self._calcular_premio(acertos_n, acertos_e)
            if premio['categoria']:
                premios_counter[premio['categoria']] += 1

            resultados.append({
                'data': sorteio.data.isoformat(),
                'numeros_sorteio': sorteio.get_numeros(),
                'estrelas_sorteio': sorteio.get_estrelas(),
                'numeros_aposta': numeros_aposta,
                'estrelas_aposta': estrelas_aposta,
                'acertos_n': acertos_n,
                'acertos_e': acertos_e,
                'premio': premio['categoria'],
            })

            # Limpar aposta de teste
            aposta.delete()

        context = self.get_context_data()
        context['resultados'] = resultados
        context['resultados_json'] = json.dumps(resultados)
        context['estrategia_usada'] = estrategia
        context['n_sorteios'] = n_sorteios
        context['media_acertos_n'] = round(total_acertos_n / n_sorteios, 2)
        context['media_acertos_e'] = round(total_acertos_e / n_sorteios, 2)
        context['distribuicao_premios'] = dict(premios_counter.most_common())
        context['total_vitorias'] = sum(premios_counter.values())

        return self.render_to_response(context)

    def _calcular_premio(self, acertos_n, acertos_e):
        """Calcula o premio baseado nos acertos."""
        premios = {
            (5, 2): {'categoria': '1o Premio (Jackpot)', 'ordem': 1},
            (5, 1): {'categoria': '2o Premio', 'ordem': 2},
            (5, 0): {'categoria': '3o Premio', 'ordem': 3},
            (4, 2): {'categoria': '4o Premio', 'ordem': 4},
            (4, 1): {'categoria': '5o Premio', 'ordem': 5},
            (4, 0): {'categoria': '6o Premio', 'ordem': 6},
            (3, 2): {'categoria': '7o Premio', 'ordem': 7},
            (3, 1): {'categoria': '8o Premio', 'ordem': 8},
            (2, 2): {'categoria': '9o Premio', 'ordem': 9},
            (3, 0): {'categoria': '10o Premio', 'ordem': 10},
            (1, 2): {'categoria': '11o Premio', 'ordem': 11},
            (2, 1): {'categoria': '12o Premio', 'ordem': 12},
            (2, 0): {'categoria': '13o Premio', 'ordem': 13},
        }
        return premios.get((acertos_n, acertos_e), {'categoria': None, 'ordem': 99})


# ============================================
# SIMULADOR DE INVESTIMENTO
# ============================================

class SimuladorView(TemplateView):
    """Vista para simulacao de investimento."""
    template_name = 'sorteios/simulador.html'

    CUSTO_APOSTA = 2.50

    # Valores medios de premio (aproximados em EUR)
    VALORES_PREMIOS = {
        '1o Premio (Jackpot)': 50000000,
        '2o Premio': 500000,
        '3o Premio': 50000,
        '4o Premio': 5000,
        '5o Premio': 500,
        '6o Premio': 100,
        '7o Premio': 50,
        '8o Premio': 20,
        '9o Premio': 15,
        '10o Premio': 13,
        '11o Premio': 10,
        '12o Premio': 8,
        '13o Premio': 4,
    }

    def get_context_data(self, **kwargs):
        import json
        context = super().get_context_data(**kwargs)
        context['estrategias'] = ApostaGerada.ESTRATEGIAS
        context['total_sorteios_disponivel'] = Sorteio.objects.count()
        context['custo_aposta'] = self.CUSTO_APOSTA
        return context

    def post(self, request, *args, **kwargs):
        import json
        from decimal import Decimal
        from collections import Counter

        estrategia = request.POST.get('estrategia', 'frequencia')
        apostas_por_sorteio = int(request.POST.get('apostas_por_sorteio', 1))
        apostas_por_sorteio = min(max(apostas_por_sorteio, 1), 10)

        # Usar todo o historico
        sorteios = list(Sorteio.objects.order_by('data'))

        gerador = GeradorApostas()
        historico = []
        total_investido = Decimal('0')
        total_ganho = Decimal('0')
        premios_counter = Counter()
        maiores_vitorias = []

        for sorteio in sorteios:
            custo = Decimal(str(self.CUSTO_APOSTA)) * apostas_por_sorteio
            total_investido += custo
            ganho_sorteio = Decimal('0')

            for _ in range(apostas_por_sorteio):
                # Gerar aposta
                aposta = gerador.gerar_e_guardar(estrategia)
                numeros_aposta = aposta.get_numeros()
                estrelas_aposta = aposta.get_estrelas()

                acertos_n = len(set(numeros_aposta) & set(sorteio.get_numeros()))
                acertos_e = len(set(estrelas_aposta) & set(sorteio.get_estrelas()))

                premio = self._calcular_premio(acertos_n, acertos_e)
                if premio['categoria']:
                    valor_premio = Decimal(str(self.VALORES_PREMIOS.get(premio['categoria'], 0)))
                    ganho_sorteio += valor_premio
                    premios_counter[premio['categoria']] += 1

                    if valor_premio > 1000:
                        maiores_vitorias.append({
                            'data': sorteio.data.isoformat(),
                            'premio': premio['categoria'],
                            'valor': float(valor_premio),
                        })

                # Limpar aposta de teste
                aposta.delete()

            total_ganho += ganho_sorteio

            historico.append({
                'data': sorteio.data.isoformat(),
                'investido_acumulado': float(total_investido),
                'ganho_acumulado': float(total_ganho),
                'saldo': float(total_ganho - total_investido),
            })

        # Calcular ROI
        if total_investido > 0:
            roi = ((total_ganho - total_investido) / total_investido) * 100
        else:
            roi = Decimal('0')

        # Ordenar maiores vitorias
        maiores_vitorias.sort(key=lambda x: x['valor'], reverse=True)

        context = self.get_context_data()
        context['historico_json'] = json.dumps(historico)
        context['estrategia_usada'] = estrategia
        context['apostas_por_sorteio'] = apostas_por_sorteio
        context['total_sorteios'] = len(sorteios)
        context['total_investido'] = float(total_investido)
        context['total_ganho'] = float(total_ganho)
        context['lucro_prejuizo'] = float(total_ganho - total_investido)
        context['roi'] = float(roi)
        context['distribuicao_premios'] = dict(premios_counter.most_common())
        context['maiores_vitorias'] = maiores_vitorias[:20]

        return self.render_to_response(context)

    def _calcular_premio(self, acertos_n, acertos_e):
        """Calcula o premio baseado nos acertos."""
        premios = {
            (5, 2): {'categoria': '1o Premio (Jackpot)', 'ordem': 1},
            (5, 1): {'categoria': '2o Premio', 'ordem': 2},
            (5, 0): {'categoria': '3o Premio', 'ordem': 3},
            (4, 2): {'categoria': '4o Premio', 'ordem': 4},
            (4, 1): {'categoria': '5o Premio', 'ordem': 5},
            (4, 0): {'categoria': '6o Premio', 'ordem': 6},
            (3, 2): {'categoria': '7o Premio', 'ordem': 7},
            (3, 1): {'categoria': '8o Premio', 'ordem': 8},
            (2, 2): {'categoria': '9o Premio', 'ordem': 9},
            (3, 0): {'categoria': '10o Premio', 'ordem': 10},
            (1, 2): {'categoria': '11o Premio', 'ordem': 11},
            (2, 1): {'categoria': '12o Premio', 'ordem': 12},
            (2, 0): {'categoria': '13o Premio', 'ordem': 13},
        }
        return premios.get((acertos_n, acertos_e), {'categoria': None, 'ordem': 99})


# ============================================
# EXPORTAR APOSTAS PARA PDF
# ============================================

def exportar_apostas_pdf(request):
    """Exporta apostas geradas para PDF."""
    from io import BytesIO
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import cm
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
    from datetime import datetime

    # Obter apostas a exportar
    tipo = request.GET.get('tipo', 'simples')
    quantidade = int(request.GET.get('quantidade', 10))
    quantidade = min(max(quantidade, 1), 50)

    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, topMargin=2*cm, bottomMargin=2*cm)
    styles = getSampleStyleSheet()
    elements = []

    # Titulo
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=24,
        spaceAfter=30,
        textColor=colors.HexColor('#003399'),
        alignment=1  # Center
    )
    elements.append(Paragraph('EuroMilhoes Analyzer', title_style))
    elements.append(Paragraph('Apostas Geradas', styles['Heading2']))
    elements.append(Spacer(1, 0.5*cm))

    # Data de geracao
    elements.append(Paragraph(
        f'Gerado em: {datetime.now().strftime("%d/%m/%Y %H:%M")}',
        styles['Normal']
    ))
    elements.append(Spacer(1, 1*cm))

    if tipo == 'multipla':
        # Exportar apostas multiplas
        apostas = ApostaMultipla.objects.order_by('-criada_em')[:quantidade]

        for i, aposta in enumerate(apostas, 1):
            elements.append(Paragraph(
                f'Aposta Multipla #{i} - {aposta.get_estrategia_display()}',
                styles['Heading3']
            ))

            # Numeros
            numeros_str = ', '.join(f'{n:02d}' for n in aposta.get_numeros())
            estrelas_str = ', '.join(f'{e:02d}' for e in aposta.get_estrelas())

            data = [
                ['Numeros:', numeros_str],
                ['Estrelas:', estrelas_str],
                ['Combinacoes:', str(aposta.total_combinacoes)],
                ['Custo:', f'{aposta.custo_total:.2f} EUR'],
            ]

            t = Table(data, colWidths=[4*cm, 12*cm])
            t.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#003399')),
                ('TEXTCOLOR', (0, 0), (0, -1), colors.white),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 0), (-1, -1), 10),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
                ('TOPPADDING', (0, 0), (-1, -1), 8),
                ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#dee2e6')),
            ]))
            elements.append(t)
            elements.append(Spacer(1, 0.5*cm))

            # Tabela de combinacoes
            if aposta.total_combinacoes <= 20:
                combinacoes = aposta.gerar_todas_combinacoes()
                elements.append(Paragraph('Todas as Combinacoes:', styles['Heading4']))

                combo_data = [['#', 'Numeros', 'Estrelas']]
                for j, combo in enumerate(combinacoes, 1):
                    nums = ', '.join(f'{n:02d}' for n in combo['numeros'])
                    ests = ', '.join(f'{e:02d}' for e in combo['estrelas'])
                    combo_data.append([str(j), nums, ests])

                t2 = Table(combo_data, colWidths=[1.5*cm, 8*cm, 4*cm])
                t2.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#003399')),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                    ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                    ('FONTSIZE', (0, 0), (-1, -1), 9),
                    ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
                    ('TOPPADDING', (0, 0), (-1, -1), 6),
                    ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#dee2e6')),
                    ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f8f9fa')]),
                ]))
                elements.append(t2)

            elements.append(Spacer(1, 1*cm))

    else:
        # Exportar apostas simples
        apostas = ApostaGerada.objects.order_by('-criada_em')[:quantidade]

        # Criar tabela de apostas
        data = [['#', 'Numeros', 'Estrelas', 'Estrategia', 'Data']]

        for i, aposta in enumerate(apostas, 1):
            numeros = ' '.join(f'{n:02d}' for n in aposta.get_numeros())
            estrelas = ' '.join(f'{e:02d}' for e in aposta.get_estrelas())
            data.append([
                str(i),
                numeros,
                estrelas,
                aposta.get_estrategia_display(),
                aposta.criada_em.strftime('%d/%m/%Y')
            ])

        t = Table(data, colWidths=[1*cm, 5*cm, 2.5*cm, 4*cm, 3*cm])
        t.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#003399')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
            ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#dee2e6')),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f8f9fa')]),
        ]))
        elements.append(t)

    # Rodape com aviso
    elements.append(Spacer(1, 2*cm))
    footer_style = ParagraphStyle(
        'Footer',
        parent=styles['Normal'],
        fontSize=8,
        textColor=colors.gray,
        alignment=1
    )
    elements.append(Paragraph(
        'Analise estatistica para fins educacionais. Jogo responsavel.',
        footer_style
    ))

    doc.build(elements)

    buffer.seek(0)
    response = HttpResponse(buffer, content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="euromilhoes_apostas_{datetime.now().strftime("%Y%m%d_%H%M")}.pdf"'

    return response


class ExportarPDFView(TemplateView):
    """Vista para interface de exportacao PDF."""
    template_name = 'sorteios/exportar_pdf.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['total_apostas_simples'] = ApostaGerada.objects.count()
        context['total_apostas_multiplas'] = ApostaMultipla.objects.count()
        return context
