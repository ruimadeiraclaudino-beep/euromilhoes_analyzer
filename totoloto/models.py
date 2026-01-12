"""
Modelos para a aplicacao Totoloto.
"""
from django.db import models


class SorteioTotoloto(models.Model):
    """Modelo para armazenar sorteios do Totoloto."""
    data = models.DateField(unique=True, db_index=True)
    numero1 = models.IntegerField()
    numero2 = models.IntegerField()
    numero3 = models.IntegerField()
    numero4 = models.IntegerField()
    numero5 = models.IntegerField()
    numero_complementar = models.IntegerField(null=True, blank=True)

    # Informacoes adicionais
    jackpot = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    houve_vencedor = models.BooleanField(default=False)

    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-data']
        verbose_name = 'Sorteio Totoloto'
        verbose_name_plural = 'Sorteios Totoloto'

    def __str__(self):
        return f"Totoloto {self.data.strftime('%d/%m/%Y')}: {self.numeros_formatados()}"

    def get_numeros(self):
        """Retorna lista com os 5 numeros sorteados."""
        return sorted([self.numero1, self.numero2, self.numero3, self.numero4, self.numero5])

    def numeros_formatados(self):
        """Retorna numeros formatados como string."""
        nums = self.get_numeros()
        resultado = '-'.join(f'{n:02d}' for n in nums)
        if self.numero_complementar:
            resultado += f' + {self.numero_complementar:02d}'
        return resultado

    def soma_numeros(self):
        """Retorna a soma dos 5 numeros."""
        return sum(self.get_numeros())

    def pares_impares(self):
        """Retorna tupla (pares, impares)."""
        nums = self.get_numeros()
        pares = sum(1 for n in nums if n % 2 == 0)
        return (pares, 5 - pares)


class EstatisticaNumeroTotoloto(models.Model):
    """Estatisticas de frequencia para cada numero do Totoloto (1-49)."""
    numero = models.IntegerField(unique=True)
    frequencia = models.IntegerField(default=0)
    percentagem = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    ultima_aparicao = models.DateField(null=True, blank=True)
    dias_sem_sair = models.IntegerField(default=0)
    gap_medio = models.DecimalField(max_digits=6, decimal_places=2, default=0)
    gap_maximo = models.IntegerField(default=0)

    class Meta:
        ordering = ['numero']
        verbose_name = 'Estatistica Numero Totoloto'
        verbose_name_plural = 'Estatisticas Numeros Totoloto'

    def __str__(self):
        return f"Totoloto Numero {self.numero}: {self.frequencia}x ({self.percentagem}%)"

    @property
    def status(self):
        """Retorna status do numero: quente, frio ou normal."""
        if self.dias_sem_sair > 30:
            return 'frio'
        elif self.frequencia > 0 and self.dias_sem_sair < 7:
            return 'quente'
        return 'normal'


class ApostaGeradaTotoloto(models.Model):
    """Apostas geradas pelo sistema para Totoloto."""
    ESTRATEGIAS = [
        ('aleatorio', 'Aleatorio'),
        ('frequencia', 'Numeros Frequentes'),
        ('equilibrada', 'Equilibrada'),
        ('frios', 'Numeros Frios'),
        ('mista', 'Mista'),
    ]

    numeros = models.JSONField()  # Lista de 5 numeros
    estrategia = models.CharField(max_length=20, choices=ESTRATEGIAS)
    criada_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-criada_em']
        verbose_name = 'Aposta Gerada Totoloto'
        verbose_name_plural = 'Apostas Geradas Totoloto'

    def __str__(self):
        return f"Totoloto Aposta {self.get_estrategia_display()}: {self.numeros_formatados()}"

    def get_numeros(self):
        """Retorna lista de numeros."""
        return sorted(self.numeros) if self.numeros else []

    def numeros_formatados(self):
        """Retorna numeros formatados."""
        return '-'.join(f'{n:02d}' for n in self.get_numeros())
