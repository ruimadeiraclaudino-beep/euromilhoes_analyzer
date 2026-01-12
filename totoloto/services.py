"""
Servicos para analise e geracao de apostas Totoloto.
"""
import random
from collections import Counter
from datetime import date, timedelta
from decimal import Decimal

from .models import SorteioTotoloto, EstatisticaNumeroTotoloto, ApostaGeradaTotoloto


class AnalisadorTotoloto:
    """Classe para analise estatistica dos sorteios do Totoloto."""

    def __init__(self):
        self.sorteios = SorteioTotoloto.objects.all()
        self.total_sorteios = self.sorteios.count()

    def atualizar_estatisticas(self):
        """Atualiza todas as estatisticas dos numeros."""
        if self.total_sorteios == 0:
            return

        # Contar frequencias
        frequencias = Counter()
        ultima_aparicao = {}
        
        for sorteio in self.sorteios.order_by('data'):
            for num in sorteio.get_numeros():
                frequencias[num] += 1
                ultima_aparicao[num] = sorteio.data

        hoje = date.today()

        # Atualizar ou criar estatisticas para cada numero (1-49)
        for numero in range(1, 50):
            freq = frequencias.get(numero, 0)
            percentagem = Decimal(freq / self.total_sorteios * 100) if self.total_sorteios > 0 else Decimal(0)
            ultima = ultima_aparicao.get(numero)
            dias_sem_sair = (hoje - ultima).days if ultima else 9999

            EstatisticaNumeroTotoloto.objects.update_or_create(
                numero=numero,
                defaults={
                    'frequencia': freq,
                    'percentagem': round(percentagem, 2),
                    'ultima_aparicao': ultima,
                    'dias_sem_sair': dias_sem_sair,
                }
            )

    def get_numeros_quentes(self, n=10):
        """Retorna os N numeros mais frequentes."""
        return list(EstatisticaNumeroTotoloto.objects.order_by('-frequencia')[:n])

    def get_numeros_frios(self, n=10):
        """Retorna os N numeros menos frequentes."""
        return list(EstatisticaNumeroTotoloto.objects.order_by('frequencia')[:n])

    def get_numeros_atrasados(self, n=10):
        """Retorna os N numeros que ha mais tempo nao saem."""
        return list(EstatisticaNumeroTotoloto.objects.order_by('-dias_sem_sair')[:n])

    def analise_distribuicao(self):
        """Analisa distribuicao de pares/impares e baixos/altos."""
        pares_impares = Counter()
        baixos_altos = Counter()
        somas = []

        for sorteio in self.sorteios:
            nums = sorteio.get_numeros()
            pares = sum(1 for n in nums if n % 2 == 0)
            impares = 5 - pares
            pares_impares[(pares, impares)] += 1

            baixos = sum(1 for n in nums if n <= 25)
            altos = 5 - baixos
            baixos_altos[(baixos, altos)] += 1

            somas.append(sum(nums))

        return {
            'pares_impares': pares_impares,
            'baixos_altos': baixos_altos,
            'somas': somas,
            'soma_media': sum(somas) / len(somas) if somas else 0,
            'soma_min': min(somas) if somas else 0,
            'soma_max': max(somas) if somas else 0,
        }


class GeradorTotoloto:
    """Classe para geracao de apostas Totoloto."""

    def __init__(self):
        self.estatisticas = list(EstatisticaNumeroTotoloto.objects.all())

    def gerar_aleatorio(self):
        """Gera aposta completamente aleatoria."""
        numeros = sorted(random.sample(range(1, 50), 5))
        return numeros

    def gerar_frequencia(self):
        """Gera aposta baseada nos numeros mais frequentes."""
        if not self.estatisticas:
            return self.gerar_aleatorio()

        ordenados = sorted(self.estatisticas, key=lambda x: x.frequencia, reverse=True)
        top_numeros = [e.numero for e in ordenados[:20]]
        numeros = sorted(random.sample(top_numeros, 5))
        return numeros

    def gerar_frios(self):
        """Gera aposta com numeros que ha muito nao saem."""
        if not self.estatisticas:
            return self.gerar_aleatorio()

        ordenados = sorted(self.estatisticas, key=lambda x: x.dias_sem_sair, reverse=True)
        top_frios = [e.numero for e in ordenados[:20]]
        numeros = sorted(random.sample(top_frios, 5))
        return numeros

    def gerar_equilibrada(self):
        """Gera aposta equilibrada (pares/impares, baixos/altos)."""
        baixos = list(range(1, 26))
        altos = list(range(26, 50))

        # 2-3 baixos, 2-3 altos
        n_baixos = random.choice([2, 3])
        n_altos = 5 - n_baixos

        numeros_baixos = random.sample(baixos, n_baixos)
        numeros_altos = random.sample(altos, n_altos)

        numeros = sorted(numeros_baixos + numeros_altos)
        return numeros

    def gerar_mista(self):
        """Combina diferentes estrategias."""
        estrategias = [
            self.gerar_frequencia,
            self.gerar_frios,
            self.gerar_equilibrada,
        ]
        estrategia = random.choice(estrategias)
        return estrategia()

    def gerar_aposta(self, estrategia='aleatorio'):
        """Gera uma aposta usando a estrategia especificada."""
        geradores = {
            'aleatorio': self.gerar_aleatorio,
            'frequencia': self.gerar_frequencia,
            'frios': self.gerar_frios,
            'equilibrada': self.gerar_equilibrada,
            'mista': self.gerar_mista,
        }
        gerador = geradores.get(estrategia, self.gerar_aleatorio)
        return gerador()

    def gerar_e_guardar(self, estrategia='aleatorio'):
        """Gera e guarda uma aposta na base de dados."""
        numeros = self.gerar_aposta(estrategia)
        aposta = ApostaGeradaTotoloto.objects.create(
            numeros=numeros,
            estrategia=estrategia,
        )
        return aposta
