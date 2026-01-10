"""
Serializers para a API REST do EuroMilhões Analyzer.
"""
from rest_framework import serializers
from .models import Sorteio, EstatisticaNumero, EstatisticaEstrela, ApostaGerada


class SorteioSerializer(serializers.ModelSerializer):
    """Serializer para sorteios."""
    numeros = serializers.SerializerMethodField()
    estrelas = serializers.SerializerMethodField()

    class Meta:
        model = Sorteio
        fields = [
            'id', 'data', 'concurso',
            'numero_1', 'numero_2', 'numero_3', 'numero_4', 'numero_5',
            'estrela_1', 'estrela_2',
            'numeros', 'estrelas',
            'jackpot', 'houve_vencedor'
        ]

    def get_numeros(self, obj):
        return obj.get_numeros()

    def get_estrelas(self, obj):
        return obj.get_estrelas()


class SorteioResumoSerializer(serializers.ModelSerializer):
    """Serializer resumido para listas."""
    numeros = serializers.SerializerMethodField()
    estrelas = serializers.SerializerMethodField()

    class Meta:
        model = Sorteio
        fields = ['id', 'data', 'numeros', 'estrelas', 'jackpot']

    def get_numeros(self, obj):
        return obj.get_numeros()

    def get_estrelas(self, obj):
        return obj.get_estrelas()


class EstatisticaNumeroSerializer(serializers.ModelSerializer):
    """Serializer para estatísticas de números."""
    status = serializers.ReadOnlyField()

    class Meta:
        model = EstatisticaNumero
        fields = [
            'numero', 'frequencia', 'percentagem',
            'ultima_aparicao', 'dias_sem_sair',
            'gap_medio', 'gap_maximo', 'desvio_esperado',
            'status', 'atualizado_em'
        ]


class EstatisticaEstrelaSerializer(serializers.ModelSerializer):
    """Serializer para estatísticas de estrelas."""
    status = serializers.ReadOnlyField()

    class Meta:
        model = EstatisticaEstrela
        fields = [
            'estrela', 'frequencia', 'percentagem',
            'ultima_aparicao', 'dias_sem_sair',
            'gap_medio', 'gap_maximo', 'desvio_esperado',
            'status', 'atualizado_em'
        ]


class ApostaGeradaSerializer(serializers.ModelSerializer):
    """Serializer para apostas geradas."""
    numeros = serializers.SerializerMethodField()
    estrelas = serializers.SerializerMethodField()
    estrategia_display = serializers.CharField(source='get_estrategia_display', read_only=True)

    class Meta:
        model = ApostaGerada
        fields = [
            'id', 'data_geracao', 'estrategia', 'estrategia_display',
            'numero_1', 'numero_2', 'numero_3', 'numero_4', 'numero_5',
            'estrela_1', 'estrela_2',
            'numeros', 'estrelas',
            'acertos_numeros', 'acertos_estrelas', 'sorteio_verificado'
        ]

    def get_numeros(self, obj):
        return obj.get_numeros()

    def get_estrelas(self, obj):
        return obj.get_estrelas()


class GerarApostaSerializer(serializers.Serializer):
    """Serializer para gerar apostas via API."""
    ESTRATEGIAS = ['frequencia', 'equilibrada', 'aleatorio', 'frios', 'mista']

    estrategia = serializers.ChoiceField(choices=ESTRATEGIAS, default='mista')
    quantidade = serializers.IntegerField(min_value=1, max_value=10, default=1)


class EstatisticasGeraisSerializer(serializers.Serializer):
    """Serializer para estatísticas gerais."""
    total_sorteios = serializers.IntegerField()
    primeiro_sorteio = serializers.DateField()
    ultimo_sorteio = serializers.DateField()
    numeros_quentes = serializers.ListField(child=serializers.IntegerField())
    numeros_frios = serializers.ListField(child=serializers.IntegerField())
    estrelas_quentes = serializers.ListField(child=serializers.IntegerField())
    estrelas_frias = serializers.ListField(child=serializers.IntegerField())
