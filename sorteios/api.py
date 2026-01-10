"""
Views da API REST para EuroMilhões Analyzer.
"""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny
from django_filters.rest_framework import DjangoFilterBackend
from django_filters import rest_framework as filters

from .models import Sorteio, EstatisticaNumero, EstatisticaEstrela, ApostaGerada
from .serializers import (
    SorteioSerializer, SorteioResumoSerializer,
    EstatisticaNumeroSerializer, EstatisticaEstrelaSerializer,
    ApostaGeradaSerializer, GerarApostaSerializer, EstatisticasGeraisSerializer
)
from .services import GeradorApostas, AnalisadorEstatistico


class SorteioFilter(filters.FilterSet):
    """Filtros para sorteios."""
    data_min = filters.DateFilter(field_name='data', lookup_expr='gte')
    data_max = filters.DateFilter(field_name='data', lookup_expr='lte')
    ano = filters.NumberFilter(field_name='data', lookup_expr='year')
    mes = filters.NumberFilter(field_name='data', lookup_expr='month')
    numero = filters.NumberFilter(method='filter_numero')
    estrela = filters.NumberFilter(method='filter_estrela')
    com_vencedor = filters.BooleanFilter(field_name='houve_vencedor')

    class Meta:
        model = Sorteio
        fields = ['data', 'houve_vencedor']

    def filter_numero(self, queryset, name, value):
        """Filtra sorteios que contêm um número específico."""
        return queryset.filter(
            numero_1=value
        ) | queryset.filter(
            numero_2=value
        ) | queryset.filter(
            numero_3=value
        ) | queryset.filter(
            numero_4=value
        ) | queryset.filter(
            numero_5=value
        )

    def filter_estrela(self, queryset, name, value):
        """Filtra sorteios que contêm uma estrela específica."""
        return queryset.filter(estrela_1=value) | queryset.filter(estrela_2=value)


class SorteioViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API endpoint para sorteios.

    Endpoints:
    - GET /api/sorteios/ - Lista todos os sorteios
    - GET /api/sorteios/{id}/ - Detalhe de um sorteio
    - GET /api/sorteios/ultimo/ - Último sorteio
    - GET /api/sorteios/por_ano/ - Sorteios agrupados por ano
    """
    queryset = Sorteio.objects.all().order_by('-data')
    serializer_class = SorteioSerializer
    filterset_class = SorteioFilter
    ordering_fields = ['data', 'jackpot']
    ordering = ['-data']

    def get_serializer_class(self):
        if self.action == 'list':
            return SorteioResumoSerializer
        return SorteioSerializer

    @action(detail=False, methods=['get'])
    def ultimo(self, request):
        """Retorna o último sorteio."""
        sorteio = Sorteio.objects.order_by('-data').first()
        if sorteio:
            serializer = SorteioSerializer(sorteio)
            return Response(serializer.data)
        return Response({'error': 'Sem sorteios'}, status=status.HTTP_404_NOT_FOUND)

    @action(detail=False, methods=['get'])
    def por_ano(self, request):
        """Retorna contagem de sorteios por ano."""
        from django.db.models import Count
        from django.db.models.functions import ExtractYear

        resultado = (
            Sorteio.objects
            .annotate(ano=ExtractYear('data'))
            .values('ano')
            .annotate(total=Count('id'))
            .order_by('ano')
        )
        return Response(list(resultado))


class EstatisticaNumeroViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API endpoint para estatísticas de números.

    Endpoints:
    - GET /api/estatisticas/numeros/ - Lista estatísticas de todos os números
    - GET /api/estatisticas/numeros/{numero}/ - Estatísticas de um número
    - GET /api/estatisticas/numeros/quentes/ - Top números quentes
    - GET /api/estatisticas/numeros/frios/ - Top números frios
    - GET /api/estatisticas/numeros/atrasados/ - Números mais atrasados
    """
    queryset = EstatisticaNumero.objects.all()
    serializer_class = EstatisticaNumeroSerializer
    lookup_field = 'numero'
    ordering_fields = ['numero', 'frequencia', 'dias_sem_sair', 'desvio_esperado']

    @action(detail=False, methods=['get'])
    def quentes(self, request):
        """Top 10 números mais frequentes."""
        limite = int(request.query_params.get('limite', 10))
        numeros = EstatisticaNumero.objects.order_by('-frequencia')[:limite]
        serializer = self.get_serializer(numeros, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def frios(self, request):
        """Top 10 números menos frequentes."""
        limite = int(request.query_params.get('limite', 10))
        numeros = EstatisticaNumero.objects.order_by('frequencia')[:limite]
        serializer = self.get_serializer(numeros, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def atrasados(self, request):
        """Top 10 números que há mais tempo não saem."""
        limite = int(request.query_params.get('limite', 10))
        numeros = EstatisticaNumero.objects.order_by('-dias_sem_sair')[:limite]
        serializer = self.get_serializer(numeros, many=True)
        return Response(serializer.data)


class EstatisticaEstrelaViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API endpoint para estatísticas de estrelas.

    Endpoints:
    - GET /api/estatisticas/estrelas/ - Lista estatísticas de todas as estrelas
    - GET /api/estatisticas/estrelas/{estrela}/ - Estatísticas de uma estrela
    - GET /api/estatisticas/estrelas/quentes/ - Top estrelas quentes
    - GET /api/estatisticas/estrelas/frias/ - Top estrelas frias
    """
    queryset = EstatisticaEstrela.objects.all()
    serializer_class = EstatisticaEstrelaSerializer
    lookup_field = 'estrela'
    ordering_fields = ['estrela', 'frequencia', 'dias_sem_sair', 'desvio_esperado']

    @action(detail=False, methods=['get'])
    def quentes(self, request):
        """Top estrelas mais frequentes."""
        limite = int(request.query_params.get('limite', 5))
        estrelas = EstatisticaEstrela.objects.order_by('-frequencia')[:limite]
        serializer = self.get_serializer(estrelas, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def frias(self, request):
        """Top estrelas menos frequentes."""
        limite = int(request.query_params.get('limite', 5))
        estrelas = EstatisticaEstrela.objects.order_by('frequencia')[:limite]
        serializer = self.get_serializer(estrelas, many=True)
        return Response(serializer.data)


class ApostaViewSet(viewsets.ModelViewSet):
    """
    API endpoint para apostas geradas.

    Endpoints:
    - GET /api/apostas/ - Lista apostas geradas
    - POST /api/apostas/gerar/ - Gera nova(s) aposta(s)
    """
    queryset = ApostaGerada.objects.all().order_by('-data_geracao')
    serializer_class = ApostaGeradaSerializer

    @action(detail=False, methods=['post'])
    def gerar(self, request):
        """Gera nova(s) aposta(s) com a estratégia especificada."""
        serializer = GerarApostaSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        estrategia = serializer.validated_data['estrategia']
        quantidade = serializer.validated_data['quantidade']

        gerador = GeradorApostas()

        if quantidade == 1:
            aposta = gerador.gerar_e_guardar(estrategia)
            return Response(
                ApostaGeradaSerializer(aposta).data,
                status=status.HTTP_201_CREATED
            )
        else:
            apostas = gerador.gerar_multiplas(estrategia, quantidade)
            return Response(
                ApostaGeradaSerializer(apostas, many=True).data,
                status=status.HTTP_201_CREATED
            )


class EstatisticasGeraisView(APIView):
    """
    API endpoint para estatísticas gerais.

    GET /api/estatisticas/
    """
    def get(self, request):
        analisador = AnalisadorEstatistico()

        primeiro = Sorteio.objects.order_by('data').first()
        ultimo = Sorteio.objects.order_by('-data').first()

        data = {
            'total_sorteios': analisador.total_sorteios,
            'primeiro_sorteio': primeiro.data if primeiro else None,
            'ultimo_sorteio': ultimo.data if ultimo else None,
            'numeros_quentes': analisador.numeros_quentes(10),
            'numeros_frios': analisador.numeros_frios(10),
            'estrelas_quentes': analisador.estrelas_quentes(5),
            'estrelas_frias': analisador.estrelas_frias(5),
        }

        return Response(data)


class VerificarApostaView(APIView):
    """
    Verifica uma aposta contra o último sorteio.

    POST /api/verificar/
    Body: {"numeros": [1, 2, 3, 4, 5], "estrelas": [1, 2]}
    """
    permission_classes = [AllowAny]

    def post(self, request):
        numeros = request.data.get('numeros', [])
        estrelas = request.data.get('estrelas', [])

        # Validações
        if len(numeros) != 5:
            return Response(
                {'error': 'Deve fornecer exatamente 5 números'},
                status=status.HTTP_400_BAD_REQUEST
            )
        if len(estrelas) != 2:
            return Response(
                {'error': 'Deve fornecer exatamente 2 estrelas'},
                status=status.HTTP_400_BAD_REQUEST
            )

        if not all(1 <= n <= 50 for n in numeros):
            return Response(
                {'error': 'Números devem estar entre 1 e 50'},
                status=status.HTTP_400_BAD_REQUEST
            )
        if not all(1 <= e <= 12 for e in estrelas):
            return Response(
                {'error': 'Estrelas devem estar entre 1 e 12'},
                status=status.HTTP_400_BAD_REQUEST
            )

        ultimo_sorteio = Sorteio.objects.order_by('-data').first()
        if not ultimo_sorteio:
            return Response(
                {'error': 'Sem sorteios na base de dados'},
                status=status.HTTP_404_NOT_FOUND
            )

        numeros_sorteio = set(ultimo_sorteio.get_numeros())
        estrelas_sorteio = set(ultimo_sorteio.get_estrelas())

        acertos_numeros = len(set(numeros) & numeros_sorteio)
        acertos_estrelas = len(set(estrelas) & estrelas_sorteio)

        # Determinar prémio (simplificado)
        premios = {
            (5, 2): '1º Prémio (Jackpot)',
            (5, 1): '2º Prémio',
            (5, 0): '3º Prémio',
            (4, 2): '4º Prémio',
            (4, 1): '5º Prémio',
            (3, 2): '6º Prémio',
            (4, 0): '7º Prémio',
            (2, 2): '8º Prémio',
            (3, 1): '9º Prémio',
            (3, 0): '10º Prémio',
            (1, 2): '11º Prémio',
            (2, 1): '12º Prémio',
            (2, 0): '13º Prémio',
        }
        premio = premios.get((acertos_numeros, acertos_estrelas), 'Sem prémio')

        return Response({
            'aposta': {
                'numeros': sorted(numeros),
                'estrelas': sorted(estrelas)
            },
            'sorteio': {
                'data': ultimo_sorteio.data,
                'numeros': ultimo_sorteio.get_numeros(),
                'estrelas': ultimo_sorteio.get_estrelas()
            },
            'resultado': {
                'acertos_numeros': acertos_numeros,
                'acertos_estrelas': acertos_estrelas,
                'premio': premio
            }
        })
