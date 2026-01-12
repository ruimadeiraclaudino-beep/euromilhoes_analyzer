"""
Modelos de dados para análise do EuroMilhões.
"""
from django.db import models
from django.contrib.auth.models import User
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


class ApostaMultipla(models.Model):
    """
    Regista apostas multiplas (mais de 5 numeros e/ou mais de 2 estrelas).

    Combinacoes possiveis:
    - 5 a 10 numeros (1-50)
    - 2 a 5 estrelas (1-12)

    Total combinacoes = C(n,5) * C(e,2)
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

    # Numeros selecionados (5 a 10) - guardados como JSON
    numeros = models.JSONField(help_text="Lista de 5 a 10 numeros")
    # Estrelas selecionadas (2 a 5) - guardados como JSON
    estrelas = models.JSONField(help_text="Lista de 2 a 5 estrelas")

    # Numero de combinacoes geradas
    total_combinacoes = models.PositiveIntegerField(default=1)

    # Custo da aposta (2.50 EUR por combinacao)
    custo_total = models.DecimalField(max_digits=10, decimal_places=2, default=2.50)

    class Meta:
        ordering = ['-data_geracao']
        verbose_name = "Aposta Múltipla"
        verbose_name_plural = "Apostas Múltiplas"

    def __str__(self):
        return f"Aposta Múltipla {self.id}: {len(self.numeros)}N + {len(self.estrelas)}E ({self.total_combinacoes} comb.)"

    def get_numeros(self):
        return sorted(self.numeros)

    def get_estrelas(self):
        return sorted(self.estrelas)

    def calcular_combinacoes(self):
        """Calcula o numero total de combinacoes."""
        from math import comb
        n_numeros = len(self.numeros)
        n_estrelas = len(self.estrelas)
        return comb(n_numeros, 5) * comb(n_estrelas, 2)

    def gerar_todas_combinacoes(self):
        """Gera todas as combinacoes possiveis da aposta multipla."""
        from itertools import combinations
        todas = []
        for nums in combinations(sorted(self.numeros), 5):
            for ests in combinations(sorted(self.estrelas), 2):
                todas.append({
                    'numeros': list(nums),
                    'estrelas': list(ests)
                })
        return todas

    def verificar_resultado(self, sorteio):
        """
        Verifica todas as combinacoes contra um sorteio.
        Retorna lista de resultados ordenada por acertos.
        """
        numeros_sorteio = set(sorteio.get_numeros())
        estrelas_sorteio = set(sorteio.get_estrelas())

        resultados = []
        for comb in self.gerar_todas_combinacoes():
            acertos_n = len(set(comb['numeros']) & numeros_sorteio)
            acertos_e = len(set(comb['estrelas']) & estrelas_sorteio)
            resultados.append({
                'numeros': comb['numeros'],
                'estrelas': comb['estrelas'],
                'acertos_numeros': acertos_n,
                'acertos_estrelas': acertos_e,
                'premio': self._calcular_premio(acertos_n, acertos_e)
            })

        return sorted(resultados, key=lambda x: (x['acertos_numeros'], x['acertos_estrelas']), reverse=True)

    def _calcular_premio(self, acertos_n, acertos_e):
        """Retorna descricao do premio baseado nos acertos."""
        premios = {
            (5, 2): "1º Prémio (Jackpot)",
            (5, 1): "2º Prémio",
            (5, 0): "3º Prémio",
            (4, 2): "4º Prémio",
            (4, 1): "5º Prémio",
            (4, 0): "6º Prémio",
            (3, 2): "7º Prémio",
            (3, 1): "8º Prémio",
            (2, 2): "9º Prémio",
            (3, 0): "10º Prémio",
            (1, 2): "11º Prémio",
            (2, 1): "12º Prémio",
            (2, 0): "13º Prémio",
        }
        return premios.get((acertos_n, acertos_e), "Sem prémio")

    def save(self, *args, **kwargs):
        """Calcula combinacoes e custo antes de guardar."""
        self.total_combinacoes = self.calcular_combinacoes()
        self.custo_total = self.total_combinacoes * 2.50
        super().save(*args, **kwargs)


class UserProfile(models.Model):
    """
    Perfil do utilizador com preferencias e numeros favoritos.
    """
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='profile'
    )
    numeros_favoritos = models.JSONField(
        default=list,
        blank=True,
        help_text="Lista de numeros favoritos (1-50)"
    )
    estrelas_favoritas = models.JSONField(
        default=list,
        blank=True,
        help_text="Lista de estrelas favoritas (1-12)"
    )
    alertas_ativos = models.BooleanField(
        default=True,
        verbose_name="Alertas Ativos"
    )
    email_alertas = models.EmailField(
        blank=True,
        verbose_name="Email para Alertas"
    )
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Perfil de Utilizador"
        verbose_name_plural = "Perfis de Utilizadores"

    def __str__(self):
        return f"Perfil de {self.user.username}"

    def get_numeros_favoritos(self):
        """Retorna numeros favoritos ordenados."""
        return sorted(self.numeros_favoritos) if self.numeros_favoritos else []

    def get_estrelas_favoritas(self):
        """Retorna estrelas favoritas ordenadas."""
        return sorted(self.estrelas_favoritas) if self.estrelas_favoritas else []

    def tem_aposta_completa(self):
        """Verifica se tem 5 numeros e 2 estrelas favoritos."""
        return len(self.numeros_favoritos) >= 5 and len(self.estrelas_favoritas) >= 2


class Alerta(models.Model):
    """
    Alertas personalizados dos utilizadores.
    """
    TIPOS = [
        ('numero_atrasado', 'Numero nao sai ha X dias'),
        ('jackpot_alto', 'Jackpot acima de X euros'),
        ('numero_saiu', 'Numero favorito saiu'),
        ('estrela_saiu', 'Estrela favorita saiu'),
    ]

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='alertas'
    )
    tipo = models.CharField(max_length=20, choices=TIPOS)
    parametros = models.JSONField(
        default=dict,
        help_text="Parametros do alerta (ex: {'numero': 7, 'dias': 30})"
    )
    ativo = models.BooleanField(default=True)
    criado_em = models.DateTimeField(auto_now_add=True)
    ultimo_disparo = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "Alerta"
        verbose_name_plural = "Alertas"
        ordering = ['-criado_em']

    def __str__(self):
        return f"{self.get_tipo_display()} - {self.user.username}"

    def get_descricao(self):
        """Retorna descricao legivel do alerta."""
        if self.tipo == 'numero_atrasado':
            return f"Numero {self.parametros.get('numero')} nao sai ha {self.parametros.get('dias')} dias"
        elif self.tipo == 'jackpot_alto':
            valor = self.parametros.get('valor', 0)
            return f"Jackpot acima de {valor:,.0f} EUR"
        elif self.tipo == 'numero_saiu':
            return f"Numero {self.parametros.get('numero')} saiu no sorteio"
        elif self.tipo == 'estrela_saiu':
            return f"Estrela {self.parametros.get('estrela')} saiu no sorteio"
        return str(self.parametros)
