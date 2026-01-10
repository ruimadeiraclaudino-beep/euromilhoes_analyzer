"""
Modelos de dados para análise do EuroMilhões.
"""
from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator


class Sorteio(models.Model):
    """
    Representa um sorteio do EuroMilhões.
    
    EuroMilhões: 5 números de 1-50 + 2 estrelas de 1-12
    """
    data = models.DateField(unique=True, verbose_name="Data do Sorteio")
    concurso = models.PositiveIntegerField(
        unique=True, 
        verbose_name="Número do Concurso",
        null=True, 
        blank=True
    )
    
    # Números principais (1-50)
    numero_1 = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(50)]
    )
    numero_2 = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(50)]
    )
    numero_3 = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(50)]
    )
    numero_4 = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(50)]
    )
    numero_5 = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(50)]
    )
    
    # Estrelas (1-12)
    estrela_1 = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(12)]
    )
    estrela_2 = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(12)]
    )
    
    # Informação do prémio
    jackpot = models.DecimalField(
        max_digits=15, 
        decimal_places=2, 
        null=True, 
        blank=True,
        verbose_name="Jackpot (€)"
    )
    houve_vencedor = models.BooleanField(
        default=False, 
        verbose_name="Houve Vencedor?"
    )
    
    class Meta:
        ordering = ['-data']
        verbose_name = "Sorteio"
        verbose_name_plural = "Sorteios"
    
    def __str__(self):
        numeros = self.get_numeros_str()
        estrelas = self.get_estrelas_str()
        return f"{self.data}: {numeros} + {estrelas}"
    
    def get_numeros(self):
        """Retorna lista ordenada dos 5 números."""
        return sorted([
            self.numero_1, self.numero_2, self.numero_3,
            self.numero_4, self.numero_5
        ])
    
    def get_estrelas(self):
        """Retorna lista ordenada das 2 estrelas."""
        return sorted([self.estrela_1, self.estrela_2])
    
    def get_numeros_str(self):
        """Retorna números formatados como string."""
        return " - ".join(f"{n:02d}" for n in self.get_numeros())
    
    def get_estrelas_str(self):
        """Retorna estrelas formatadas como string."""
        return " - ".join(f"{e:02d}" for e in self.get_estrelas())
    
    def soma_numeros(self):
        """Retorna a soma dos 5 números."""
        return sum(self.get_numeros())
    
    def soma_estrelas(self):
        """Retorna a soma das 2 estrelas."""
        return sum(self.get_estrelas())
    
    def pares_impares(self):
        """Retorna tuplo (pares, ímpares) dos números."""
        numeros = self.get_numeros()
        pares = sum(1 for n in numeros if n % 2 == 0)
        return (pares, 5 - pares)
    
    def baixos_altos(self):
        """Retorna tuplo (baixos 1-25, altos 26-50) dos números."""
        numeros = self.get_numeros()
        baixos = sum(1 for n in numeros if n <= 25)
        return (baixos, 5 - baixos)
    
    def save(self, *args, **kwargs):
        """Ordena números e estrelas antes de guardar."""
        numeros = sorted([
            self.numero_1, self.numero_2, self.numero_3,
            self.numero_4, self.numero_5
        ])
        self.numero_1, self.numero_2, self.numero_3 = numeros[0], numeros[1], numeros[2]
        self.numero_4, self.numero_5 = numeros[3], numeros[4]
        
        estrelas = sorted([self.estrela_1, self.estrela_2])
        self.estrela_1, self.estrela_2 = estrelas[0], estrelas[1]
        
        super().save(*args, **kwargs)


class EstatisticaNumero(models.Model):
    """
    Estatísticas calculadas para cada número (1-50).
    """
    numero = models.PositiveSmallIntegerField(
        unique=True,
        validators=[MinValueValidator(1), MaxValueValidator(50)]
    )
    frequencia = models.PositiveIntegerField(default=0, verbose_name="Frequência Total")
    percentagem = models.DecimalField(
        max_digits=5, 
        decimal_places=2, 
        default=0,
        verbose_name="Percentagem (%)"
    )
    ultima_aparicao = models.DateField(null=True, blank=True, verbose_name="Última Aparição")
    dias_sem_sair = models.PositiveIntegerField(default=0, verbose_name="Dias Sem Sair")
    gap_medio = models.DecimalField(
        max_digits=8, 
        decimal_places=2, 
        default=0,
        verbose_name="Gap Médio (dias)"
    )
    gap_maximo = models.PositiveIntegerField(default=0, verbose_name="Gap Máximo (dias)")
    desvio_esperado = models.DecimalField(
        max_digits=8, 
        decimal_places=4, 
        default=0,
        verbose_name="Desvio do Esperado"
    )
    atualizado_em = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['numero']
        verbose_name = "Estatística de Número"
        verbose_name_plural = "Estatísticas de Números"
    
    def __str__(self):
        return f"Número {self.numero:02d}: {self.frequencia}x ({self.percentagem}%)"
    
    @property
    def status(self):
        """Classifica o número como quente, normal ou frio."""
        if self.desvio_esperado > 0.1:
            return "quente"
        elif self.desvio_esperado < -0.1:
            return "frio"
        return "normal"


class EstatisticaEstrela(models.Model):
    """
    Estatísticas calculadas para cada estrela (1-12).
    """
    estrela = models.PositiveSmallIntegerField(
        unique=True,
        validators=[MinValueValidator(1), MaxValueValidator(12)]
    )
    frequencia = models.PositiveIntegerField(default=0, verbose_name="Frequência Total")
    percentagem = models.DecimalField(
        max_digits=5, 
        decimal_places=2, 
        default=0,
        verbose_name="Percentagem (%)"
    )
    ultima_aparicao = models.DateField(null=True, blank=True, verbose_name="Última Aparição")
    dias_sem_sair = models.PositiveIntegerField(default=0, verbose_name="Dias Sem Sair")
    gap_medio = models.DecimalField(
        max_digits=8, 
        decimal_places=2, 
        default=0,
        verbose_name="Gap Médio (dias)"
    )
    gap_maximo = models.PositiveIntegerField(default=0, verbose_name="Gap Máximo (dias)")
    desvio_esperado = models.DecimalField(
        max_digits=8, 
        decimal_places=4, 
        default=0,
        verbose_name="Desvio do Esperado"
    )
    atualizado_em = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['estrela']
        verbose_name = "Estatística de Estrela"
        verbose_name_plural = "Estatísticas de Estrelas"
    
    def __str__(self):
        return f"Estrela {self.estrela:02d}: {self.frequencia}x ({self.percentagem}%)"
    
    @property
    def status(self):
        """Classifica a estrela como quente, normal ou fria."""
        if self.desvio_esperado > 0.1:
            return "quente"
        elif self.desvio_esperado < -0.1:
            return "fria"
        return "normal"


class ApostaGerada(models.Model):
    """
    Regista apostas geradas pelo sistema.
    """
    ESTRATEGIAS = [
        ('frequencia', 'Baseada em Frequência'),
        ('equilibrada', 'Distribuição Equilibrada'),
        ('aleatorio', 'Aleatório Puro'),
        ('frios', 'Números Frios'),
        ('mista', 'Estratégia Mista'),
    ]
    
    data_geracao = models.DateTimeField(auto_now_add=True)
    estrategia = models.CharField(max_length=20, choices=ESTRATEGIAS)
    
    numero_1 = models.PositiveSmallIntegerField()
    numero_2 = models.PositiveSmallIntegerField()
    numero_3 = models.PositiveSmallIntegerField()
    numero_4 = models.PositiveSmallIntegerField()
    numero_5 = models.PositiveSmallIntegerField()
    estrela_1 = models.PositiveSmallIntegerField()
    estrela_2 = models.PositiveSmallIntegerField()
    
    # Resultado (preenchido após sorteio)
    acertos_numeros = models.PositiveSmallIntegerField(null=True, blank=True)
    acertos_estrelas = models.PositiveSmallIntegerField(null=True, blank=True)
    sorteio_verificado = models.ForeignKey(
        Sorteio, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True
    )
    
    class Meta:
        ordering = ['-data_geracao']
        verbose_name = "Aposta Gerada"
        verbose_name_plural = "Apostas Geradas"
    
    def __str__(self):
        return f"Aposta {self.id} ({self.get_estrategia_display()})"
    
    def get_numeros(self):
        return sorted([
            self.numero_1, self.numero_2, self.numero_3,
            self.numero_4, self.numero_5
        ])
    
    def get_estrelas(self):
        return sorted([self.estrela_1, self.estrela_2])
    
    def verificar_resultado(self, sorteio):
        """Verifica quantos acertos teve contra um sorteio."""
        numeros_sorteio = set(sorteio.get_numeros())
        estrelas_sorteio = set(sorteio.get_estrelas())
        
        self.acertos_numeros = len(set(self.get_numeros()) & numeros_sorteio)
        self.acertos_estrelas = len(set(self.get_estrelas()) & estrelas_sorteio)
        self.sorteio_verificado = sorteio
        self.save()
        
        return (self.acertos_numeros, self.acertos_estrelas)
