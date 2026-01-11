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

from .models import Sorteio, EstatisticaNumero, EstatisticaEstrela, ApostaGerada, ApostaMultipla


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

    def analisar_numeros_consecutivos(self) -> Dict:
        """
        Analisa a ocorrência de números consecutivos nos sorteios.

        Returns:
            Dict com estatísticas de consecutivos
        """
        contagem_consecutivos = Counter()
        sorteios_com_consecutivos = 0
        exemplos = []

        for sorteio in self.sorteios:
            numeros = sorted(sorteio.get_numeros())
            consecutivos = 0
            pares_consecutivos = []

            for i in range(len(numeros) - 1):
                if numeros[i + 1] - numeros[i] == 1:
                    consecutivos += 1
                    pares_consecutivos.append((numeros[i], numeros[i + 1]))

            if consecutivos > 0:
                sorteios_com_consecutivos += 1
                contagem_consecutivos[consecutivos] += 1
                if len(exemplos) < 5:
                    exemplos.append({
                        'data': sorteio.data,
                        'numeros': numeros,
                        'consecutivos': pares_consecutivos
                    })

        percentagem = (sorteios_com_consecutivos / self.total_sorteios * 100) if self.total_sorteios > 0 else 0

        return {
            'total_com_consecutivos': sorteios_com_consecutivos,
            'percentagem': round(percentagem, 2),
            'distribuicao': dict(contagem_consecutivos),
            'exemplos': exemplos
        }

    def analisar_dezenas(self) -> Dict:
        """
        Analisa a distribuição por dezenas (1-10, 11-20, 21-30, 31-40, 41-50).

        Returns:
            Dict com contagem por dezena e padrões mais comuns
        """
        dezenas_counter = Counter()
        padroes_dezenas = Counter()

        for sorteio in self.sorteios:
            numeros = sorteio.get_numeros()
            dezenas = []

            for num in numeros:
                if num <= 10:
                    dezena = 1
                elif num <= 20:
                    dezena = 2
                elif num <= 30:
                    dezena = 3
                elif num <= 40:
                    dezena = 4
                else:
                    dezena = 5
                dezenas.append(dezena)
                dezenas_counter[dezena] += 1

            # Padrão de dezenas (ex: "1-2-3-4-5" significa 1 número de cada dezena)
            padrao = tuple(sorted(Counter(dezenas).items()))
            padroes_dezenas[padrao] += 1

        return {
            'frequencia_dezenas': dict(dezenas_counter),
            'padroes_comuns': padroes_dezenas.most_common(10)
        }

    def analisar_terminacoes(self) -> Dict:
        """
        Analisa a distribuição por terminações (último dígito).

        Returns:
            Dict com contagem por terminação e padrões
        """
        terminacoes_counter = Counter()
        terminacoes_repetidas = Counter()

        for sorteio in self.sorteios:
            numeros = sorteio.get_numeros()
            terminacoes = [num % 10 for num in numeros]

            for term in terminacoes:
                terminacoes_counter[term] += 1

            # Verificar terminações repetidas
            term_count = Counter(terminacoes)
            repetidas = sum(1 for c in term_count.values() if c > 1)
            terminacoes_repetidas[repetidas] += 1

        return {
            'frequencia_terminacoes': dict(sorted(terminacoes_counter.items())),
            'terminacoes_repetidas': dict(terminacoes_repetidas)
        }

    def analisar_sequencias(self, tamanho: int = 3) -> List[Tuple]:
        """
        Encontra sequências de números consecutivos que mais aparecem.

        Args:
            tamanho: Tamanho da sequência (2, 3, etc.)

        Returns:
            Lista de (sequência, frequência)
        """
        sequencias = Counter()

        for sorteio in self.sorteios:
            numeros = sorted(sorteio.get_numeros())

            # Procurar sequências consecutivas
            for i in range(len(numeros) - tamanho + 1):
                subsequencia = numeros[i:i + tamanho]
                # Verificar se é consecutiva
                if all(subsequencia[j + 1] - subsequencia[j] == 1 for j in range(len(subsequencia) - 1)):
                    sequencias[tuple(subsequencia)] += 1

        return sequencias.most_common(15)

    def analisar_soma_tendencias(self, ultimos_n: int = 50) -> Dict:
        """
        Analisa tendências nas somas dos últimos N sorteios.

        Args:
            ultimos_n: Número de sorteios a analisar

        Returns:
            Dict com média, tendência e faixas
        """
        sorteios_recentes = list(self.sorteios.order_by('-data')[:ultimos_n])

        if not sorteios_recentes:
            return {'erro': 'Sem dados suficientes'}

        somas = [s.soma_numeros() for s in sorteios_recentes]
        somas_estrelas = [s.soma_estrelas() for s in sorteios_recentes]

        # Calcular faixas
        faixas = {
            'muito_baixa': (21, 95),
            'baixa': (96, 115),
            'media': (116, 145),
            'alta': (146, 175),
            'muito_alta': (176, 255)
        }

        distribuicao_faixas = Counter()
        for soma in somas:
            for nome, (min_val, max_val) in faixas.items():
                if min_val <= soma <= max_val:
                    distribuicao_faixas[nome] += 1
                    break

        # Tendência (subindo ou descendo)
        primeira_metade = somas[:len(somas)//2]
        segunda_metade = somas[len(somas)//2:]

        media_primeira = sum(primeira_metade) / len(primeira_metade) if primeira_metade else 0
        media_segunda = sum(segunda_metade) / len(segunda_metade) if segunda_metade else 0

        if media_segunda > media_primeira * 1.05:
            tendencia = 'subindo'
        elif media_segunda < media_primeira * 0.95:
            tendencia = 'descendo'
        else:
            tendencia = 'estavel'

        return {
            'media_numeros': round(sum(somas) / len(somas), 1),
            'media_estrelas': round(sum(somas_estrelas) / len(somas_estrelas), 1),
            'min_soma': min(somas),
            'max_soma': max(somas),
            'tendencia': tendencia,
            'distribuicao_faixas': dict(distribuicao_faixas),
            'ultimas_somas': somas[:10]
        }

    def get_analise_padroes_completa(self) -> Dict:
        """
        Retorna análise completa de padrões.

        Returns:
            Dict com todas as análises de padrões
        """
        return {
            'combinacoes_pares': self.combinacoes_frequentes(2),
            'combinacoes_trios': self.combinacoes_frequentes(3),
            'consecutivos': self.analisar_numeros_consecutivos(),
            'dezenas': self.analisar_dezenas(),
            'terminacoes': self.analisar_terminacoes(),
            'sequencias': self.analisar_sequencias(2),
            'tendencias_soma': self.analisar_soma_tendencias(50),
            'total_sorteios': self.total_sorteios
        }


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

    def gerar_aposta_multipla(
        self,
        estrategia: str,
        n_numeros: int = 6,
        n_estrelas: int = 3
    ) -> ApostaMultipla:
        """
        Gera uma aposta multipla (mais de 5 numeros e/ou 2 estrelas).

        Args:
            estrategia: 'frequencia', 'equilibrada', 'aleatorio', 'frios', 'mista'
            n_numeros: Quantidade de numeros a selecionar (5-10)
            n_estrelas: Quantidade de estrelas a selecionar (2-5)

        Returns:
            Instancia de ApostaMultipla
        """
        # Validar limites
        n_numeros = max(5, min(10, n_numeros))
        n_estrelas = max(2, min(5, n_estrelas))

        # Obter pools baseados na estrategia
        if estrategia == 'frequencia':
            pool_numeros = self.analisador.numeros_quentes(25)
            pool_estrelas = self.analisador.estrelas_quentes(8)
        elif estrategia == 'frios':
            pool_numeros = self.analisador.numeros_frios(25)
            pool_estrelas = self.analisador.estrelas_frias(8)
        elif estrategia == 'equilibrada':
            # Equilibrar baixos/altos
            baixos = list(range(1, 26))
            altos = list(range(26, 51))
            n_baixos = n_numeros // 2 + n_numeros % 2
            n_altos = n_numeros // 2
            pool_numeros = random.sample(baixos, n_baixos) + random.sample(altos, n_altos)
            pool_estrelas = list(range(1, 13))
        elif estrategia == 'mista':
            quentes = self.analisador.numeros_quentes(15)
            frios = self.analisador.numeros_frios(15)
            atrasados = self.analisador.numeros_atrasados(10)
            pool_numeros = list(set(quentes + frios + atrasados))
            pool_estrelas = list(range(1, 13))
        else:  # aleatorio
            pool_numeros = list(range(1, 51))
            pool_estrelas = list(range(1, 13))

        # Selecionar numeros e estrelas
        numeros = sorted(random.sample(pool_numeros, min(n_numeros, len(pool_numeros))))
        estrelas = sorted(random.sample(pool_estrelas, min(n_estrelas, len(pool_estrelas))))

        # Completar se necessario
        while len(numeros) < n_numeros:
            novo = random.choice([n for n in range(1, 51) if n not in numeros])
            numeros.append(novo)
            numeros = sorted(numeros)

        while len(estrelas) < n_estrelas:
            nova = random.choice([e for e in range(1, 13) if e not in estrelas])
            estrelas.append(nova)
            estrelas = sorted(estrelas)

        # Criar e guardar aposta multipla
        aposta = ApostaMultipla.objects.create(
            estrategia=estrategia,
            numeros=numeros,
            estrelas=estrelas
        )

        return aposta

    @staticmethod
    def calcular_tabela_combinacoes():
        """
        Retorna tabela com numero de combinacoes e custos para apostas multiplas.

        Returns:
            Dict com combinacoes possiveis e respetivos custos
        """
        from math import comb

        tabela = {}
        for n in range(5, 11):  # 5 a 10 numeros
            for e in range(2, 6):  # 2 a 5 estrelas
                combinacoes = comb(n, 5) * comb(e, 2)
                custo = combinacoes * 2.50
                tabela[(n, e)] = {
                    'numeros': n,
                    'estrelas': e,
                    'combinacoes': combinacoes,
                    'custo': custo
                }
        return tabela
