"""
Modulo de Machine Learning para previsoes do EuroMilhoes.

AVISO IMPORTANTE: Este modulo e EXPERIMENTAL e para fins EDUCACIONAIS.
Cada sorteio do EuroMilhoes e um evento independente e aleatorio.
Nenhum modelo de ML pode prever com precisao os resultados de uma loteria.
"""
import random
from collections import Counter
from datetime import date, timedelta
from decimal import Decimal
from typing import List, Dict, Tuple, Optional
import math

from django.db.models import Avg, Count
from django.core.cache import cache

from .models import Sorteio, EstatisticaNumero, EstatisticaEstrela


class PrevisaoML:
    """
    Classe para previsoes usando tecnicas de analise estatistica avancada.

    NOTA: Este nao e um verdadeiro modelo de ML que "aprende" a prever loteria
    (isso e impossivel). Em vez disso, usa analise estatistica para identificar
    padroes historicos e gerar apostas informadas.
    """

    def __init__(self):
        self.sorteios = list(Sorteio.objects.order_by('data'))
        self.total_sorteios = len(self.sorteios)
        self._calcular_features()

    def _calcular_features(self):
        """Calcula features estatisticas de cada numero."""
        if not self.sorteios:
            self.features_numeros = {}
            self.features_estrelas = {}
            return

        # Features dos numeros (1-50)
        self.features_numeros = {}
        for n in range(1, 51):
            self.features_numeros[n] = self._calcular_features_numero(n)

        # Features das estrelas (1-12)
        self.features_estrelas = {}
        for e in range(1, 13):
            self.features_estrelas[e] = self._calcular_features_estrela(e)

    def _calcular_features_numero(self, numero: int) -> Dict:
        """Calcula features para um numero especifico."""
        aparicoes = []
        ultimas_50 = 0
        ultimas_100 = 0

        for i, sorteio in enumerate(self.sorteios):
            if numero in sorteio.get_numeros():
                aparicoes.append(i)
                if i >= len(self.sorteios) - 50:
                    ultimas_50 += 1
                if i >= len(self.sorteios) - 100:
                    ultimas_100 += 1

        frequencia = len(aparicoes)
        frequencia_esperada = self.total_sorteios * 0.1  # 5/50 = 10%

        # Gap medio entre aparicoes
        gaps = []
        for i in range(1, len(aparicoes)):
            gaps.append(aparicoes[i] - aparicoes[i-1])
        gap_medio = sum(gaps) / len(gaps) if gaps else 0

        # Dias desde ultima aparicao
        ultima_aparicao = aparicoes[-1] if aparicoes else 0
        sorteios_sem_sair = len(self.sorteios) - 1 - ultima_aparicao if aparicoes else self.total_sorteios

        # Tendencia recente (comparar ultimos 50 com media historica)
        freq_recente = ultimas_50 / 50 if self.total_sorteios >= 50 else frequencia / self.total_sorteios
        freq_historica = frequencia / self.total_sorteios if self.total_sorteios > 0 else 0
        tendencia = freq_recente - freq_historica

        return {
            'frequencia': frequencia,
            'frequencia_normalizada': frequencia / self.total_sorteios if self.total_sorteios > 0 else 0,
            'desvio': (frequencia - frequencia_esperada) / frequencia_esperada if frequencia_esperada > 0 else 0,
            'gap_medio': gap_medio,
            'sorteios_sem_sair': sorteios_sem_sair,
            'tendencia': tendencia,
            'ultimas_50': ultimas_50,
            'ultimas_100': ultimas_100,
            'quente': ultimas_50 >= 5,  # Media seria 5 em 50 sorteios
            'atrasado': sorteios_sem_sair > gap_medio * 1.5 if gap_medio > 0 else False
        }

    def _calcular_features_estrela(self, estrela: int) -> Dict:
        """Calcula features para uma estrela especifica."""
        aparicoes = []
        ultimas_50 = 0

        for i, sorteio in enumerate(self.sorteios):
            if estrela in sorteio.get_estrelas():
                aparicoes.append(i)
                if i >= len(self.sorteios) - 50:
                    ultimas_50 += 1

        frequencia = len(aparicoes)
        frequencia_esperada = self.total_sorteios * (2/12)  # ~16.67%

        gaps = []
        for i in range(1, len(aparicoes)):
            gaps.append(aparicoes[i] - aparicoes[i-1])
        gap_medio = sum(gaps) / len(gaps) if gaps else 0

        ultima_aparicao = aparicoes[-1] if aparicoes else 0
        sorteios_sem_sair = len(self.sorteios) - 1 - ultima_aparicao if aparicoes else self.total_sorteios

        return {
            'frequencia': frequencia,
            'frequencia_normalizada': frequencia / self.total_sorteios if self.total_sorteios > 0 else 0,
            'desvio': (frequencia - frequencia_esperada) / frequencia_esperada if frequencia_esperada > 0 else 0,
            'gap_medio': gap_medio,
            'sorteios_sem_sair': sorteios_sem_sair,
            'ultimas_50': ultimas_50,
            'quente': ultimas_50 >= 8,  # Media seria ~8 em 50 sorteios
            'atrasado': sorteios_sem_sair > gap_medio * 1.5 if gap_medio > 0 else False
        }

    def calcular_score_numero(self, numero: int, peso_frequencia: float = 0.3,
                               peso_tendencia: float = 0.3, peso_atraso: float = 0.4) -> float:
        """
        Calcula um score para cada numero baseado em multiplos fatores.

        Args:
            numero: Numero a avaliar (1-50)
            peso_frequencia: Peso da frequencia historica
            peso_tendencia: Peso da tendencia recente
            peso_atraso: Peso do atraso (numeros que ha muito nao saem)

        Returns:
            Score normalizado entre 0 e 1
        """
        if numero not in self.features_numeros:
            return 0.5

        f = self.features_numeros[numero]

        # Normalizar componentes para 0-1
        freq_score = min(f['frequencia_normalizada'] / 0.15, 1)  # Normalizar para max 15%

        # Tendencia: converter para 0-1 (neutro = 0.5)
        tendencia_score = 0.5 + f['tendencia'] * 5  # Amplificar diferenca
        tendencia_score = max(0, min(1, tendencia_score))

        # Atraso: numeros mais atrasados tem score mais alto
        gap_esperado = 10  # Em media, um numero sai a cada 10 sorteios
        atraso_score = min(f['sorteios_sem_sair'] / (gap_esperado * 2), 1)

        # Score final ponderado
        score = (
            peso_frequencia * freq_score +
            peso_tendencia * tendencia_score +
            peso_atraso * atraso_score
        )

        return round(score, 4)

    def calcular_score_estrela(self, estrela: int) -> float:
        """Calcula score para uma estrela."""
        if estrela not in self.features_estrelas:
            return 0.5

        f = self.features_estrelas[estrela]

        freq_score = min(f['frequencia_normalizada'] / 0.25, 1)

        gap_esperado = 6  # Em media, uma estrela sai a cada 6 sorteios
        atraso_score = min(f['sorteios_sem_sair'] / (gap_esperado * 2), 1)

        score = 0.5 * freq_score + 0.5 * atraso_score

        return round(score, 4)

    def prever_proximos_numeros(self, estrategia: str = 'equilibrada') -> Dict:
        """
        Gera previsao para o proximo sorteio.

        Args:
            estrategia: 'frequencia', 'atraso', 'equilibrada', 'tendencia'

        Returns:
            Dict com numeros previstos, estrelas e scores
        """
        if not self.sorteios:
            return {'erro': 'Sem dados historicos'}

        # Calcular scores para todos os numeros
        scores_numeros = {}
        for n in range(1, 51):
            if estrategia == 'frequencia':
                scores_numeros[n] = self.calcular_score_numero(n, 0.7, 0.2, 0.1)
            elif estrategia == 'atraso':
                scores_numeros[n] = self.calcular_score_numero(n, 0.1, 0.2, 0.7)
            elif estrategia == 'tendencia':
                scores_numeros[n] = self.calcular_score_numero(n, 0.2, 0.6, 0.2)
            else:  # equilibrada
                scores_numeros[n] = self.calcular_score_numero(n, 0.33, 0.33, 0.34)

        # Calcular scores para estrelas
        scores_estrelas = {e: self.calcular_score_estrela(e) for e in range(1, 13)}

        # Selecionar top 5 numeros
        numeros_ordenados = sorted(scores_numeros.items(), key=lambda x: x[1], reverse=True)

        # Adicionar aleatoriedade para evitar sempre os mesmos numeros
        top_15 = numeros_ordenados[:15]
        pesos = [score for _, score in top_15]
        numeros_selecionados = self._selecionar_ponderado(top_15, 5)

        # Selecionar 2 estrelas
        estrelas_ordenadas = sorted(scores_estrelas.items(), key=lambda x: x[1], reverse=True)
        top_5_estrelas = estrelas_ordenadas[:5]
        estrelas_selecionadas = self._selecionar_ponderado(top_5_estrelas, 2)

        # Calcular confianca (baseado na variancia dos scores)
        scores_list = list(scores_numeros.values())
        media_scores = sum(scores_list) / len(scores_list)
        variancia = sum((s - media_scores) ** 2 for s in scores_list) / len(scores_list)
        confianca = min(variancia * 100, 50)  # Max 50% - loteria e impossivel prever

        return {
            'numeros': sorted(numeros_selecionados),
            'estrelas': sorted(estrelas_selecionadas),
            'scores_numeros': {n: scores_numeros[n] for n in numeros_selecionados},
            'scores_estrelas': {e: scores_estrelas[e] for e in estrelas_selecionadas},
            'confianca': round(confianca, 1),
            'estrategia': estrategia,
            'aviso': 'Previsao experimental - loteria e aleatoria!'
        }

    def _selecionar_ponderado(self, items: List[Tuple[int, float]], n: int) -> List[int]:
        """Seleciona n items com probabilidade ponderada pelos scores."""
        if not items:
            return []

        selecionados = []
        disponiveis = list(items)

        for _ in range(min(n, len(disponiveis))):
            if not disponiveis:
                break

            # Normalizar pesos
            total = sum(score for _, score in disponiveis)
            if total == 0:
                # Se todos os scores sao 0, selecionar aleatoriamente
                idx = random.randint(0, len(disponiveis) - 1)
            else:
                # Selecao ponderada
                r = random.uniform(0, total)
                acumulado = 0
                idx = 0
                for i, (_, score) in enumerate(disponiveis):
                    acumulado += score
                    if acumulado >= r:
                        idx = i
                        break

            selecionados.append(disponiveis[idx][0])
            disponiveis.pop(idx)

        return selecionados

    def analisar_precisao_historica(self, janela: int = 100) -> Dict:
        """
        Analisa a precisao do modelo nos ultimos N sorteios.

        Args:
            janela: Numero de sorteios a analisar

        Returns:
            Dict com metricas de precisao
        """
        if len(self.sorteios) < janela + 10:
            return {'erro': 'Dados insuficientes para analise'}

        acertos_numeros = []
        acertos_estrelas = []

        # Simular previsoes para os ultimos 'janela' sorteios
        for i in range(len(self.sorteios) - janela, len(self.sorteios)):
            # Usar apenas dados anteriores ao sorteio
            sorteios_treino = self.sorteios[:i]
            if len(sorteios_treino) < 50:
                continue

            # Calcular scores com dados de treino
            scores = {}
            for n in range(1, 51):
                aparicoes = sum(1 for s in sorteios_treino[-50:] if n in s.get_numeros())
                scores[n] = aparicoes / 50

            # Top 5 numeros previstos
            previstos = sorted(scores.items(), key=lambda x: x[1], reverse=True)[:10]
            numeros_previstos = [n for n, _ in previstos]

            # Numeros reais
            sorteio_real = self.sorteios[i]
            numeros_reais = sorteio_real.get_numeros()

            # Contar acertos
            acertos = len(set(numeros_previstos[:5]) & set(numeros_reais))
            acertos_top10 = len(set(numeros_previstos) & set(numeros_reais))
            acertos_numeros.append({'top5': acertos, 'top10': acertos_top10})

        if not acertos_numeros:
            return {'erro': 'Nao foi possivel calcular precisao'}

        media_acertos_5 = sum(a['top5'] for a in acertos_numeros) / len(acertos_numeros)
        media_acertos_10 = sum(a['top10'] for a in acertos_numeros) / len(acertos_numeros)

        # Calcular precisao esperada por acaso
        # Probabilidade de acertar k numeros em 5 tentativas de 50
        # E(acertos) = 5 * (5/50) = 0.5 para top 5
        # E(acertos) = 5 * (10/50) = 1.0 para top 10

        return {
            'sorteios_analisados': len(acertos_numeros),
            'media_acertos_top5': round(media_acertos_5, 2),
            'media_acertos_top10': round(media_acertos_10, 2),
            'esperado_acaso_top5': 0.5,
            'esperado_acaso_top10': 1.0,
            'melhoria_percentual_top5': round((media_acertos_5 / 0.5 - 1) * 100, 1) if media_acertos_5 > 0 else 0,
            'melhoria_percentual_top10': round((media_acertos_10 / 1.0 - 1) * 100, 1) if media_acertos_10 > 0 else 0,
            'distribuicao_acertos': Counter(a['top5'] for a in acertos_numeros)
        }

    def get_ranking_numeros(self) -> List[Dict]:
        """Retorna ranking de todos os numeros com scores e features."""
        ranking = []
        for n in range(1, 51):
            f = self.features_numeros.get(n, {})
            ranking.append({
                'numero': n,
                'score': self.calcular_score_numero(n),
                'frequencia': f.get('frequencia', 0),
                'sorteios_sem_sair': f.get('sorteios_sem_sair', 0),
                'tendencia': f.get('tendencia', 0),
                'quente': f.get('quente', False),
                'atrasado': f.get('atrasado', False)
            })

        return sorted(ranking, key=lambda x: x['score'], reverse=True)

    def get_ranking_estrelas(self) -> List[Dict]:
        """Retorna ranking de todas as estrelas com scores e features."""
        ranking = []
        for e in range(1, 13):
            f = self.features_estrelas.get(e, {})
            ranking.append({
                'estrela': e,
                'score': self.calcular_score_estrela(e),
                'frequencia': f.get('frequencia', 0),
                'sorteios_sem_sair': f.get('sorteios_sem_sair', 0),
                'quente': f.get('quente', False),
                'atrasado': f.get('atrasado', False)
            })

        return sorted(ranking, key=lambda x: x['score'], reverse=True)

    def get_analise_completa(self) -> Dict:
        """Retorna analise ML completa."""
        return {
            'previsao_equilibrada': self.prever_proximos_numeros('equilibrada'),
            'previsao_frequencia': self.prever_proximos_numeros('frequencia'),
            'previsao_atraso': self.prever_proximos_numeros('atraso'),
            'previsao_tendencia': self.prever_proximos_numeros('tendencia'),
            'ranking_numeros': self.get_ranking_numeros()[:15],
            'ranking_estrelas': self.get_ranking_estrelas()[:6],
            'precisao_historica': self.analisar_precisao_historica(50),
            'total_sorteios': self.total_sorteios,
            'aviso': 'Analise experimental - cada sorteio e independente e aleatorio!'
        }
