"""
Testes para a API de estatísticas.
"""
from datetime import date
from decimal import Decimal
from django.urls import reverse
from rest_framework.test import APITestCase, APIClient
from rest_framework import status
from sorteios.models import Sorteio, EstatisticaNumero, EstatisticaEstrela


class EstatisticaNumeroAPITest(APITestCase):
    """Testes para endpoints de estatísticas de números."""

    def setUp(self):
        """Criar dados de teste."""
        self.client = APIClient()

        # Criar estatísticas de teste
        self.stat1 = EstatisticaNumero.objects.create(
            numero=44,
            frequencia=100,
            percentagem=Decimal('2.50'),
            dias_sem_sair=5,
            desvio_esperado=Decimal('0.20')
        )
        self.stat2 = EstatisticaNumero.objects.create(
            numero=22,
            frequencia=50,
            percentagem=Decimal('1.20'),
            dias_sem_sair=30,
            desvio_esperado=Decimal('-0.15')
        )
        self.stat3 = EstatisticaNumero.objects.create(
            numero=33,
            frequencia=75,
            percentagem=Decimal('1.80'),
            dias_sem_sair=100,
            desvio_esperado=Decimal('0.05')
        )

    def test_list_estatisticas_numeros(self):
        """Testar listagem de estatísticas de números."""
        url = reverse('api-numeros-list')
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 3)

    def test_get_estatistica_numero(self):
        """Testar detalhe de estatística por número."""
        url = reverse('api-numeros-detail', args=[44])
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['numero'], 44)
        self.assertEqual(response.data['frequencia'], 100)
        self.assertEqual(response.data['status'], 'quente')

    def test_numeros_quentes(self):
        """Testar endpoint de números quentes."""
        url = reverse('api-numeros-quentes')
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Ordenado por frequência decrescente
        self.assertEqual(response.data[0]['numero'], 44)

    def test_numeros_quentes_limite(self):
        """Testar limite de números quentes."""
        url = reverse('api-numeros-quentes')
        response = self.client.get(url, {'limite': 2})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)

    def test_numeros_frios(self):
        """Testar endpoint de números frios."""
        url = reverse('api-numeros-frios')
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Ordenado por frequência crescente
        self.assertEqual(response.data[0]['numero'], 22)

    def test_numeros_atrasados(self):
        """Testar endpoint de números atrasados."""
        url = reverse('api-numeros-atrasados')
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Ordenado por dias_sem_sair decrescente
        self.assertEqual(response.data[0]['numero'], 33)
        self.assertEqual(response.data[0]['dias_sem_sair'], 100)


class EstatisticaEstrelaAPITest(APITestCase):
    """Testes para endpoints de estatísticas de estrelas."""

    def setUp(self):
        """Criar dados de teste."""
        self.client = APIClient()

        self.stat1 = EstatisticaEstrela.objects.create(
            estrela=2,
            frequencia=200,
            percentagem=Decimal('10.00'),
            desvio_esperado=Decimal('0.15')
        )
        self.stat2 = EstatisticaEstrela.objects.create(
            estrela=11,
            frequencia=100,
            percentagem=Decimal('5.00'),
            desvio_esperado=Decimal('-0.20')
        )

    def test_list_estatisticas_estrelas(self):
        """Testar listagem de estatísticas de estrelas."""
        url = reverse('api-estrelas-list')
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 2)

    def test_estrelas_quentes(self):
        """Testar endpoint de estrelas quentes."""
        url = reverse('api-estrelas-quentes')
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data[0]['estrela'], 2)

    def test_estrelas_frias(self):
        """Testar endpoint de estrelas frias."""
        url = reverse('api-estrelas-frias')
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data[0]['estrela'], 11)


class EstatisticasGeraisAPITest(APITestCase):
    """Testes para endpoint de estatísticas gerais."""

    def setUp(self):
        """Criar dados de teste."""
        self.client = APIClient()

        # Criar sorteios para estatísticas
        Sorteio.objects.create(
            data=date(2024, 1, 5),
            numero_1=5, numero_2=12, numero_3=23, numero_4=34, numero_5=45,
            estrela_1=3, estrela_2=8
        )
        Sorteio.objects.create(
            data=date(2024, 1, 9),
            numero_1=10, numero_2=20, numero_3=30, numero_4=40, numero_5=50,
            estrela_1=1, estrela_2=12
        )

    def test_estatisticas_gerais(self):
        """Testar endpoint de estatísticas gerais."""
        url = reverse('api-estatisticas')
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('total_sorteios', response.data)
        self.assertIn('primeiro_sorteio', response.data)
        self.assertIn('ultimo_sorteio', response.data)
        self.assertIn('numeros_quentes', response.data)
        self.assertIn('numeros_frios', response.data)
        self.assertEqual(response.data['total_sorteios'], 2)
