"""
Serviços de análise estatística para EuroMilhões.
"""
import random
from datetime import date, timedelta
from decimal import Decimal
from collections import Counter
from typing import List, Tuple, Dict, Optional

from django.db.models import Avg, Max, Min, Count
from django.utils import timezone

from .models import Sorteio, EstatisticaNumero, EstatisticaEstrela, ApostaGerada


class AnalisadorEstatistico:
    """
    Classe principal para análise estatística dos sorteios.
    """
    
    # Probabilidades teóricas
    PROB_NUMERO = 5 / 50  # 10% - cada número tem 10% de chance
    PROB_ESTRELA = 2 / 12  # 16.67% - cada estrela tem 16.67% de chance
    
    def __init__(self):
        self.sorteios = Sorteio.objects.all()
        self.total_sorteios = self.sorteios.count()
    
    def calcular_frequencias_numeros(self) -> Dict[int, int]:
        """Calcula a frequência de cada número (1-50)."""
        frequencias = Counter()
        
        for sorteio in self.sorteios:
            for num in sorteio.get_numeros():
                frequencias[num] += 1
        
        # Garantir que todos os números estão presentes
        for n in range(1, 51):
            if n not in frequencias:
                frequencias[n] = 0
        
        return dict(sorted(frequencias.items()))
    
    def calcular_frequencias_estrelas(self) -> Dict[int, int]:
        """Calcula a frequência de cada estrela (1-12)."""
        frequencias = Counter()
        
        for sorteio in self.sorteios:
            for est in sorteio.get_estrelas():
                frequencias[est] += 1
        
        # Garantir que todas as estrelas estão presentes
        for e in range(1, 13):
            if e not in frequencias:
                frequencias[e] = 0
        
        return dict(sorted(frequencias.items()))
    
    def calcular_gaps(self, numero: int, tipo: str = 'numero') -> Dict:
        """
        Calcula gaps (intervalos entre aparições) para um número ou estrela.
        
        Args:
            numero: O número ou estrela a analisar
            tipo: 'numero' ou 'estrela'
        
        Returns:
            Dict com gap_medio, gap_maximo, ultima_aparicao, dias_sem_sair
        """
        aparicoes = []
        
        for sorteio in self.sorteios.order_by('data'):
            if tipo == 'numero':
                if numero in sorteio.get_numeros():
                    aparicoes.append(sorteio.data)
            else:
                if numero in sorteio.get_estrelas():
                    aparicoes.append(sorteio.data)
        
        if not aparicoes:
            return {
                'gap_medio': 0,
                'gap_maximo': 0,
                'ultima_aparicao': None,
                'dias_sem_sair': 0
            }
        
        # Calcular gaps entre aparições consecutivas
        gaps = []
        for i in range(1, len(aparicoes)):
            gap = (aparicoes[i] - aparicoes[i-1]).days
            gaps.append(gap)
        
        ultima_aparicao = aparicoes[-1]
        dias_sem_sair = (date.today() - ultima_aparicao).days
        
        return {
            'gap_medio': sum(gaps) / len(gaps) if gaps else 0,
            'gap_maximo': max(gaps) if gaps else 0,
            'ultima_aparicao': ultima_aparicao,
            'dias_sem_sair': dias_sem_sair
        }
    
    def atualizar_estatisticas(self):
        """Atualiza todas as estatísticas na base de dados."""
        if self.total_sorteios == 0:
            return
        
        # Estatísticas de números
        freq_numeros = self.calcular_frequencias_numeros()
        frequencia_esperada = self.total_sorteios * self.PROB_NUMERO
        
        for numero, frequencia in freq_numeros.items():
            gaps = self.calcular_gaps(numero, 'numero')
            percentagem = (frequencia / (self.total_sorteios * 5)) * 100
            desvio = (frequencia - frequencia_esperada) / frequencia_esperada if frequencia_esperada > 0 else 0
            
            EstatisticaNumero.objects.update_or_create(
                numero=numero,
                defaults={
                    'frequencia': frequencia,
                    'percentagem': Decimal(str(round(percentagem, 2))),
                    'ultima_aparicao': gaps['ultima_aparicao'],
                    'dias_sem_sair': gaps['dias_sem_sair'],
                    'gap_medio': Decimal(str(round(gaps['gap_medio'], 2))),
                    'gap_maximo': gaps['gap_maximo'],
                    'desvio_esperado': Decimal(str(round(desvio, 4)))
                }
            )
        
        # Estatísticas de estrelas
        freq_estrelas = self.calcular_frequencias_estrelas()
        frequencia_esperada_estrela = self.total_sorteios * self.PROB_ESTRELA
        
        for estrela, frequencia in freq_estrelas.items():
            gaps = self.calcular_gaps(estrela, 'estrela')
            percentagem = (frequencia / (self.total_sorteios * 2)) * 100
            desvio = (frequencia - frequencia_esperada_estrela) / frequencia_esperada_estrela if frequencia_esperada_estrela > 0 else 0
            
            EstatisticaEstrela.objects.update_or_create(
                estrela=estrela,
                defaults={
                    'frequencia': frequencia,
                    'percentagem': Decimal(str(round(percentagem, 2))),
                    'ultima_aparicao': gaps['ultima_aparicao'],
                    'dias_sem_sair': gaps['dias_sem_sair'],
                    'gap_medio': Decimal(str(round(gaps['gap_medio'], 2))),
                    'gap_maximo': gaps['gap_maximo'],
                    'desvio_esperado': Decimal(str(round(desvio, 4)))
                }
            )
    
    def numeros_quentes(self, n: int = 10) -> List[int]:
        """Retorna os N números mais frequentes."""
        return list(
            EstatisticaNumero.objects.order_by('-frequencia')
            .values_list('numero', flat=True)[:n]
        )
    
    def numeros_frios(self, n: int = 10) -> List[int]:
        """Retorna os N números menos frequentes."""
        return list(
            EstatisticaNumero.objects.order_by('frequencia')
            .values_list('numero', flat=True)[:n]
        )
    
    def estrelas_quentes(self, n: int = 5) -> List[int]:
        """Retorna as N estrelas mais frequentes."""
        return list(
            EstatisticaEstrela.objects.order_by('-frequencia')
            .values_list('estrela', flat=True)[:n]
        )
    
    def estrelas_frias(self, n: int = 5) -> List[int]:
        """Retorna as N estrelas menos frequentes."""
        return list(
            EstatisticaEstrela.objects.order_by('frequencia')
            .values_list('estrela', flat=True)[:n]
        )
    
    def numeros_atrasados(self, n: int = 10) -> List[int]:
        """Retorna os N números que há mais tempo não saem."""
        return list(
            EstatisticaNumero.objects.order_by('-dias_sem_sair')
            .values_list('numero', flat=True)[:n]
        )
    
    def estrelas_atrasadas(self, n: int = 5) -> List[int]:
        """Retorna as N estrelas que há mais tempo não saem."""
        return list(
            EstatisticaEstrela.objects.order_by('-dias_sem_sair')
            .values_list('estrela', flat=True)[:n]
        )
    
    def analise_distribuicao(self) -> Dict:
        """
        Analisa a distribuição dos sorteios.
        
        Returns:
            Dict com estatísticas de distribuição (pares/ímpares, baixos/altos, somas)
        """
        distribuicoes = {
            'pares_impares': Counter(),
            'baixos_altos': Counter(),
            'somas': [],
            'somas_estrelas': []
        }
        
        for sorteio in self.sorteios:
            distribuicoes['pares_impares'][sorteio.pares_impares()] += 1
            distribuicoes['baixos_altos'][sorteio.baixos_altos()] += 1
            distribuicoes['somas'].append(sorteio.soma_numeros())
            distribuicoes['somas_estrelas'].append(sorteio.soma_estrelas())
        
        if distribuicoes['somas']:
            distribuicoes['soma_media'] = sum(distribuicoes['somas']) / len(distribuicoes['somas'])
            distribuicoes['soma_min'] = min(distribuicoes['somas'])
            distribuicoes['soma_max'] = max(distribuicoes['somas'])
        
        return distribuicoes
    
    def combinacoes_frequentes(self, tamanho: int = 2) -> List[Tuple]:
        """
        Encontra as combinações de números mais frequentes.
        
        Args:
            tamanho: Tamanho da combinação (2 para pares, 3 para trios)
        
        Returns:
            Lista de tuplos (combinação, frequência) ordenada por frequência
        """
        from itertools import combinations
        
        combinacoes = Counter()
        
        for sorteio in self.sorteios:
            numeros = sorteio.get_numeros()
            for combo in combinations(numeros, tamanho):
                combinacoes[combo] += 1
        
        return combinacoes.most_common(20)


class GeradorApostas:
    """
    Gera apostas baseadas em diferentes estratégias.
    """
    
    def __init__(self):
        self.analisador = AnalisadorEstatistico()
    
    def gerar_aleatorio(self) -> Tuple[List[int], List[int]]:
        """Gera aposta completamente aleatória."""
        numeros = sorted(random.sample(range(1, 51), 5))
        estrelas = sorted(random.sample(range(1, 13), 2))
        return numeros, estrelas
    
    def gerar_por_frequencia(self, usar_quentes: bool = True) -> Tuple[List[int], List[int]]:
        """
        Gera aposta baseada em frequência.
        
        Args:
            usar_quentes: Se True, favorece números quentes; se False, números frios
        """
        if usar_quentes:
            pool_numeros = self.analisador.numeros_quentes(20)
            pool_estrelas = self.analisador.estrelas_quentes(6)
        else:
            pool_numeros = self.analisador.numeros_frios(20)
            pool_estrelas = self.analisador.estrelas_frias(6)
        
        # Selecionar aleatoriamente do pool
        numeros = sorted(random.sample(pool_numeros, min(5, len(pool_numeros))))
        estrelas = sorted(random.sample(pool_estrelas, min(2, len(pool_estrelas))))
        
        return numeros, estrelas
    
    def gerar_equilibrada(self) -> Tuple[List[int], List[int]]:
        """
        Gera aposta com distribuição equilibrada.
        
        Critérios:
        - 2-3 números pares, 2-3 ímpares
        - 2-3 números baixos (1-25), 2-3 altos (26-50)
        - Soma total entre 100-175 (intervalo mais comum)
        """
        max_tentativas = 100
        
        for _ in range(max_tentativas):
            # Selecionar números baixos e altos
            baixos = random.sample(range(1, 26), 3)
            altos = random.sample(range(26, 51), 2)
            numeros = sorted(baixos + altos)
            
            # Verificar critérios
            soma = sum(numeros)
            pares = sum(1 for n in numeros if n % 2 == 0)
            
            if 100 <= soma <= 175 and 2 <= pares <= 3:
                break
        
        # Estrelas equilibradas
        estrelas = sorted([
            random.choice(range(1, 7)),
            random.choice(range(7, 13))
        ])
        
        return numeros, estrelas
    
    def gerar_mista(self) -> Tuple[List[int], List[int]]:
        """
        Estratégia mista: combina números quentes, frios e equilibra distribuição.
        
        Seleciona:
        - 2 números quentes
        - 2 números frios
        - 1 número atrasado
        - 1 estrela quente + 1 fria
        """
        quentes = self.analisador.numeros_quentes(10)
        frios = self.analisador.numeros_frios(10)
        atrasados = self.analisador.numeros_atrasados(10)
        
        numeros = set()
        
        # 2 quentes
        numeros.update(random.sample(quentes, min(2, len(quentes))))
        
        # 2 frios (que não estejam já selecionados)
        frios_disponiveis = [n for n in frios if n not in numeros]
        numeros.update(random.sample(frios_disponiveis, min(2, len(frios_disponiveis))))
        
        # Completar com atrasados
        while len(numeros) < 5:
            atrasados_disponiveis = [n for n in atrasados if n not in numeros]
            if atrasados_disponiveis:
                numeros.add(random.choice(atrasados_disponiveis))
            else:
                # Fallback para aleatório
                numeros.add(random.choice([n for n in range(1, 51) if n not in numeros]))
        
        # Estrelas
        estrelas_quentes = self.analisador.estrelas_quentes(4)
        estrelas_frias = self.analisador.estrelas_frias(4)
        
        estrela_q = random.choice(estrelas_quentes) if estrelas_quentes else random.randint(1, 6)
        estrelas_frias_disp = [e for e in estrelas_frias if e != estrela_q]
        estrela_f = random.choice(estrelas_frias_disp) if estrelas_frias_disp else random.randint(7, 12)
        
        return sorted(list(numeros))[:5], sorted([estrela_q, estrela_f])
    
    def gerar_e_guardar(self, estrategia: str) -> ApostaGerada:
        """
        Gera e guarda uma aposta na base de dados.
        
        Args:
            estrategia: 'frequencia', 'equilibrada', 'aleatorio', 'frios', 'mista'
        
        Returns:
            Instância de ApostaGerada
        """
        if estrategia == 'frequencia':
            numeros, estrelas = self.gerar_por_frequencia(usar_quentes=True)
        elif estrategia == 'frios':
            numeros, estrelas = self.gerar_por_frequencia(usar_quentes=False)
        elif estrategia == 'equilibrada':
            numeros, estrelas = self.gerar_equilibrada()
        elif estrategia == 'mista':
            numeros, estrelas = self.gerar_mista()
        else:  # aleatorio
            numeros, estrelas = self.gerar_aleatorio()
        
        aposta = ApostaGerada.objects.create(
            estrategia=estrategia,
            numero_1=numeros[0],
            numero_2=numeros[1],
            numero_3=numeros[2],
            numero_4=numeros[3],
            numero_5=numeros[4],
            estrela_1=estrelas[0],
            estrela_2=estrelas[1]
        )
        
        return aposta
    
    def gerar_multiplas(self, estrategia: str, quantidade: int = 5) -> List[ApostaGerada]:
        """Gera múltiplas apostas únicas."""
        apostas = []
        combinacoes_geradas = set()
        max_tentativas = quantidade * 10
        tentativas = 0
        
        while len(apostas) < quantidade and tentativas < max_tentativas:
            aposta = self.gerar_e_guardar(estrategia)
            combo = (tuple(aposta.get_numeros()), tuple(aposta.get_estrelas()))
            
            if combo not in combinacoes_geradas:
                combinacoes_geradas.add(combo)
                apostas.append(aposta)
            else:
                aposta.delete()
            
            tentativas += 1
        
        return apostas
