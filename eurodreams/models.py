"""
Modelos para a aplicacao EuroDreams.
"""
from django.db import models


class SorteioEuroDreams(models.Model):
    """Modelo para armazenar sorteios do EuroDreams."""
    data = models.DateField(unique=True, db_index=True)
    numero1 = models.IntegerField()
    numero2 = models.IntegerField()
    numero3 = models.IntegerField()
    numero4 = models.IntegerField()
    numero5 = models.IntegerField()
    numero6 = models.IntegerField()
    dream = models.IntegerField()  # 1-5

    # Informacoes adicionais
    houve_vencedor = models.BooleanField(default=False)

    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-data']
        verbose_name = 'Sorteio EuroDreams'
        verbose_name_plural = 'Sorteios EuroDreams'

    def __str__(self):
        return f"EuroDreams {self.data.strftime('%d/%m/%Y')}: {self.numeros_formatados()}"

    def get_numeros(self):
        """Retorna lista com os 6 numeros sorteados."""
        return sorted([self.numero1, self.numero2, self.numero3, 
                      self.numero4, self.numero5, self.numero6])

    def numeros_formatados(self):
        """Retorna numeros formatados como string."""
        nums = self.get_numeros()
        return '-'.join(f'{n:02d}' for n in nums) + f' + Dream {self.dream}'

    def soma_numeros(self):
        """Retorna a soma dos 6 numeros."""
        return sum(self.get_numeros())


class EstatisticaNumeroEuroDreams(models.Model):
    """Estatisticas de frequencia para cada numero do EuroDreams (1-40)."""
    numero = models.IntegerField(unique=True)
    frequencia = models.IntegerField(default=0)
    percentagem = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    ultima_aparicao = models.DateField(null=True, blank=True)
    dias_sem_sair = models.IntegerField(default=0)

    class Meta:
        ordering = ['numero']
        verbose_name = 'Estatistica Numero EuroDreams'
        verbose_name_plural = 'Estatisticas Numeros EuroDreams'

    def __str__(self):
        return f"EuroDreams Numero {self.numero}: {self.frequencia}x"

    @property
    def status(self):
        if self.dias_sem_sair > 30:
            return 'frio'
        elif self.frequencia > 0 and self.dias_sem_sair < 7:
            return 'quente'
        return 'normal'


class EstatisticaDreamEuroDreams(models.Model):
    """Estatisticas de frequencia para cada Dream (1-5)."""
    dream = models.IntegerField(unique=True)
    frequencia = models.IntegerField(default=0)
    percentagem = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    ultima_aparicao = models.DateField(null=True, blank=True)
    dias_sem_sair = models.IntegerField(default=0)

    class Meta:
        ordering = ['dream']
        verbose_name = 'Estatistica Dream EuroDreams'
        verbose_name_plural = 'Estatisticas Dreams EuroDreams'


class ApostaGeradaEuroDreams(models.Model):
    """Apostas geradas pelo sistema para EuroDreams."""
    ESTRATEGIAS = [
        ('aleatorio', 'Aleatorio'),
        ('frequencia', 'Numeros Frequentes'),
        ('equilibrada', 'Equilibrada'),
        ('frios', 'Numeros Frios'),
    ]

    numeros = models.JSONField()  # Lista de 6 numeros
    dream = models.IntegerField()
    estrategia = models.CharField(max_length=20, choices=ESTRATEGIAS)
    criada_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-criada_em']
        verbose_name = 'Aposta Gerada EuroDreams'
        verbose_name_plural = 'Apostas Geradas EuroDreams'

    def get_numeros(self):
        return sorted(self.numeros) if self.numeros else []

    def numeros_formatados(self):
        return '-'.join(f'{n:02d}' for n in self.get_numeros()) + f' + Dream {self.dream}'
