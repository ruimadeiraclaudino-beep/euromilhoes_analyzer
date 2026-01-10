"""
Testes para a API de sorteios.
"""
from datetime import date
from decimal import Decimal
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APITestCase, APIClient
from rest_framework import status
from django.contrib.auth.models import User
from rest_framework.authtoken.models import Token
from sorteios.models import Sorteio


class SorteioAPITest(APITestCase):
    """Testes para endpoints de sorteios."""

    def setUp(self):
        """Criar dados de teste."""
        self.client = APIClient()

        # Criar sorteios de teste
        self.sorteio1 = Sorteio.objects.create(
            data=date(2024, 1, 5),
            numero_1=5, numero_2=12, numero_3=23, numero_4=34, numero_5=45,
            estrela_1=3, estrela_2=8,
            jackpot=Decimal('50000000.00'),
            houve_vencedor=False
        )
        self.sorteio2 = Sorteio.objects.create(
            data=date(2024, 1, 9),
            numero_1=10, numero_2=20, numero_3=30, numero_4=40, numero_5=50,
            estrela_1=1, estrela_2=12,
            jackpot=Decimal('75000000.00'),
            houve_vencedor=True
        )

    def test_list_sorteios(self):
        """Testar listagem de sorteios (público)."""
        url = reverse('api-sorteios-list')
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 2)

    def test_get_sorteio_detail(self):
        """Testar detalhe de um sorteio."""
        url = reverse('api-sorteios-detail', args=[self.sorteio1.id])
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['data'], '2024-01-05')
        self.assertEqual(response.data['numeros'], [5, 12, 23, 34, 45])
        self.assertEqual(response.data['estrelas'], [3, 8])

    def test_get_ultimo_sorteio(self):
        """Testar endpoint de último sorteio."""
        url = reverse('api-sorteios-ultimo')
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Deve retornar o mais recente (2024-01-09)
        self.assertEqual(response.data['data'], '2024-01-09')

    def test_filter_by_ano(self):
        """Testar filtro por ano."""
        url = reverse('api-sorteios-list')
        response = self.client.get(url, {'ano': 2024})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 2)

    def test_filter_by_numero(self):
        """Testar filtro por número."""
        url = reverse('api-sorteios-list')
        response = self.client.get(url, {'numero': 45})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Apenas sorteio1 tem o número 45
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['data'], '2024-01-05')

    def test_filter_by_estrela(self):
        """Testar filtro por estrela."""
        url = reverse('api-sorteios-list')
        response = self.client.get(url, {'estrela': 12})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Apenas sorteio2 tem a estrela 12
        self.assertEqual(len(response.data['results']), 1)

    def test_filter_com_vencedor(self):
        """Testar filtro por vencedor."""
        url = reverse('api-sorteios-list')
        response = self.client.get(url, {'com_vencedor': 'true'})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
        self.assertTrue(response.data['results'][0]['jackpot'])

    def test_por_ano_action(self):
        """Testar action por_ano."""
        url = reverse('api-sorteios-por-ano')
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsInstance(response.data, list)

    def test_ordering(self):
        """Testar ordenação."""
        url = reverse('api-sorteios-list')
        response = self.client.get(url, {'ordering': 'data'})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Ordenado por data ascendente
        self.assertEqual(response.data['results'][0]['data'], '2024-01-05')

    def test_sorteio_not_found(self):
        """Testar sorteio inexistente."""
        url = reverse('api-sorteios-detail', args=[9999])
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
