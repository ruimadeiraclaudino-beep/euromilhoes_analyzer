"""
Servicos para analise e geracao de apostas EuroDreams.
"""
import random
from collections import Counter
from datetime import date
from decimal import Decimal

from .models import SorteioEuroDreams, EstatisticaNumeroEuroDreams, EstatisticaDreamEuroDreams, ApostaGeradaEuroDreams


class AnalisadorEuroDreams:
    """Classe para analise estatistica dos sorteios do EuroDreams."""

    def __init__(self):
        self.sorteios = SorteioEuroDreams.objects.all()
        self.total_sorteios = self.sorteios.count()

    def atualizar_estatisticas(self):
        """Atualiza todas as estatisticas."""
        if self.total_sorteios == 0:
            return

        # Contar frequencias numeros
        freq_numeros = Counter()
        freq_dreams = Counter()
        ultima_num = {}
        ultima_dream = {}
        
        for sorteio in self.sorteios.order_by('data'):
            for num in sorteio.get_numeros():
                freq_numeros[num] += 1
                ultima_num[num] = sorteio.data
            freq_dreams[sorteio.dream] += 1
            ultima_dream[sorteio.dream] = sorteio.data

        hoje = date.today()

        # Atualizar numeros (1-40)
        for numero in range(1, 41):
            freq = freq_numeros.get(numero, 0)
            percentagem = Decimal(freq / self.total_sorteios * 100) if self.total_sorteios > 0 else Decimal(0)
            ultima = ultima_num.get(numero)
            dias_sem_sair = (hoje - ultima).days if ultima else 9999

            EstatisticaNumeroEuroDreams.objects.update_or_create(
                numero=numero,
                defaults={
                    'frequencia': freq,
                    'percentagem': round(percentagem, 2),
                    'ultima_aparicao': ultima,
                    'dias_sem_sair': dias_sem_sair,
                }
            )

        # Atualizar dreams (1-5)
        for dream in range(1, 6):
            freq = freq_dreams.get(dream, 0)
            percentagem = Decimal(freq / self.total_sorteios * 100) if self.total_sorteios > 0 else Decimal(0)
            ultima = ultima_dream.get(dream)
            dias_sem_sair = (hoje - ultima).days if ultima else 9999

            EstatisticaDreamEuroDreams.objects.update_or_create(
                dream=dream,
                defaults={
                    'frequencia': freq,
                    'percentagem': round(percentagem, 2),
                    'ultima_aparicao': ultima,
                    'dias_sem_sair': dias_sem_sair,
                }
            )


class GeradorEuroDreams:
    """Classe para geracao de apostas EuroDreams."""

    def __init__(self):
        self.estatisticas = list(EstatisticaNumeroEuroDreams.objects.all())

    def gerar_aleatorio(self):
        """Gera aposta completamente aleatoria."""
        numeros = sorted(random.sample(range(1, 41), 6))
        dream = random.randint(1, 5)
        return numeros, dream

    def gerar_frequencia(self):
        """Gera aposta baseada nos numeros mais frequentes."""
        if not self.estatisticas:
            return self.gerar_aleatorio()

        ordenados = sorted(self.estatisticas, key=lambda x: x.frequencia, reverse=True)
        top_numeros = [e.numero for e in ordenados[:15]]
        numeros = sorted(random.sample(top_numeros, 6))
        dream = random.randint(1, 5)
        return numeros, dream

    def gerar_frios(self):
        """Gera aposta com numeros frios."""
        if not self.estatisticas:
            return self.gerar_aleatorio()

        ordenados = sorted(self.estatisticas, key=lambda x: x.dias_sem_sair, reverse=True)
        top_frios = [e.numero for e in ordenados[:15]]
        numeros = sorted(random.sample(top_frios, 6))
        dream = random.randint(1, 5)
        return numeros, dream

    def gerar_equilibrada(self):
        """Gera aposta equilibrada."""
        baixos = list(range(1, 21))
        altos = list(range(21, 41))

        n_baixos = random.choice([2, 3, 4])
        n_altos = 6 - n_baixos

        numeros = sorted(random.sample(baixos, n_baixos) + random.sample(altos, n_altos))
        dream = random.randint(1, 5)
        return numeros, dream

    def gerar_aposta(self, estrategia='aleatorio'):
        """Gera uma aposta usando a estrategia especificada."""
        geradores = {
            'aleatorio': self.gerar_aleatorio,
            'frequencia': self.gerar_frequencia,
            'frios': self.gerar_frios,
            'equilibrada': self.gerar_equilibrada,
        }
        gerador = geradores.get(estrategia, self.gerar_aleatorio)
        return gerador()

    def gerar_e_guardar(self, estrategia='aleatorio'):
        """Gera e guarda uma aposta na base de dados."""
        numeros, dream = self.gerar_aposta(estrategia)
        aposta = ApostaGeradaEuroDreams.objects.create(
            numeros=numeros,
            dream=dream,
            estrategia=estrategia,
        )
        return aposta
