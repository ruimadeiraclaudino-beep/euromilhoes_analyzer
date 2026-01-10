"""
Testes para a API de apostas.
"""
from datetime import date
from django.urls import reverse
from rest_framework.test import APITestCase, APIClient
from rest_framework import status
from django.contrib.auth.models import User
from rest_framework.authtoken.models import Token
from sorteios.models import Sorteio, ApostaGerada, EstatisticaNumero, EstatisticaEstrela


class ApostaAPITest(APITestCase):
    """Testes para endpoints de apostas."""

    def setUp(self):
        """Criar dados de teste."""
        self.client = APIClient()

        # Criar utilizador e token
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.token = Token.objects.create(user=self.user)

        # Criar sorteio para testes
        self.sorteio = Sorteio.objects.create(
            data=date(2024, 1, 5),
            numero_1=5, numero_2=12, numero_3=23, numero_4=34, numero_5=45,
            estrela_1=3, estrela_2=8
        )

        # Criar estatísticas básicas para o gerador funcionar
        for i in range(1, 51):
            EstatisticaNumero.objects.create(
                numero=i,
                frequencia=50 + i,
                dias_sem_sair=i
            )
        for i in range(1, 13):
            EstatisticaEstrela.objects.create(
                estrela=i,
                frequencia=20 + i,
                dias_sem_sair=i
            )

        # Criar aposta de teste
        self.aposta = ApostaGerada.objects.create(
            estrategia='mista',
            numero_1=1, numero_2=2, numero_3=3, numero_4=4, numero_5=5,
            estrela_1=1, estrela_2=2
        )

    def test_list_apostas_public(self):
        """Testar listagem de apostas (público)."""
        url = reverse('api-apostas-list')
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_gerar_aposta_sem_autenticacao(self):
        """Testar que gerar aposta requer autenticação."""
        url = reverse('api-apostas-gerar')
        response = self.client.post(url, {'estrategia': 'mista'})

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_gerar_aposta_com_autenticacao(self):
        """Testar gerar aposta com autenticação."""
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.token.key}')

        url = reverse('api-apostas-gerar')
        response = self.client.post(url, {'estrategia': 'mista'})

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn('numeros', response.data)
        self.assertIn('estrelas', response.data)
        self.assertEqual(len(response.data['numeros']), 5)
        self.assertEqual(len(response.data['estrelas']), 2)

    def test_gerar_aposta_estrategia_aleatorio(self):
        """Testar gerar aposta aleatória."""
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.token.key}')

        url = reverse('api-apostas-gerar')
        response = self.client.post(url, {'estrategia': 'aleatorio'})

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['estrategia'], 'aleatorio')

    def test_gerar_aposta_estrategia_frequencia(self):
        """Testar gerar aposta por frequência."""
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.token.key}')

        url = reverse('api-apostas-gerar')
        response = self.client.post(url, {'estrategia': 'frequencia'})

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['estrategia'], 'frequencia')

    def test_gerar_aposta_estrategia_equilibrada(self):
        """Testar gerar aposta equilibrada."""
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.token.key}')

        url = reverse('api-apostas-gerar')
        response = self.client.post(url, {'estrategia': 'equilibrada'})

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['estrategia'], 'equilibrada')

    def test_gerar_multiplas_apostas(self):
        """Testar gerar múltiplas apostas."""
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.token.key}')

        url = reverse('api-apostas-gerar')
        response = self.client.post(url, {'estrategia': 'mista', 'quantidade': 3})

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(len(response.data), 3)

    def test_gerar_aposta_estrategia_invalida(self):
        """Testar gerar aposta com estratégia inválida."""
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.token.key}')

        url = reverse('api-apostas-gerar')
        response = self.client.post(url, {'estrategia': 'invalida'})

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_gerar_aposta_quantidade_limite(self):
        """Testar limite de quantidade de apostas."""
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.token.key}')

        url = reverse('api-apostas-gerar')
        response = self.client.post(url, {'estrategia': 'mista', 'quantidade': 100})

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class VerificarApostaAPITest(APITestCase):
    """Testes para endpoint de verificação de apostas."""

    def setUp(self):
        """Criar dados de teste."""
        self.client = APIClient()

        self.sorteio = Sorteio.objects.create(
            data=date(2024, 1, 5),
            numero_1=5, numero_2=12, numero_3=23, numero_4=34, numero_5=45,
            estrela_1=3, estrela_2=8
        )

    def test_verificar_aposta_jackpot(self):
        """Testar verificação de aposta vencedora (jackpot)."""
        url = reverse('api-verificar')
        response = self.client.post(url, {
            'numeros': [5, 12, 23, 34, 45],
            'estrelas': [3, 8]
        }, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['resultado']['acertos_numeros'], 5)
        self.assertEqual(response.data['resultado']['acertos_estrelas'], 2)
        self.assertIn('Jackpot', response.data['resultado']['premio'])

    def test_verificar_aposta_parcial(self):
        """Testar verificação de aposta com acertos parciais."""
        url = reverse('api-verificar')
        response = self.client.post(url, {
            'numeros': [5, 12, 23, 1, 2],  # 3 acertos
            'estrelas': [3, 1]  # 1 acerto
        }, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['resultado']['acertos_numeros'], 3)
        self.assertEqual(response.data['resultado']['acertos_estrelas'], 1)

    def test_verificar_aposta_sem_acertos(self):
        """Testar verificação de aposta sem acertos."""
        url = reverse('api-verificar')
        response = self.client.post(url, {
            'numeros': [1, 2, 3, 4, 6],
            'estrelas': [1, 2]
        }, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['resultado']['acertos_numeros'], 0)
        self.assertEqual(response.data['resultado']['acertos_estrelas'], 0)
        self.assertEqual(response.data['resultado']['premio'], 'Sem prémio')

    def test_verificar_aposta_numeros_invalidos(self):
        """Testar verificação com números inválidos."""
        url = reverse('api-verificar')
        response = self.client.post(url, {
            'numeros': [1, 2, 3, 4],  # Falta um número
            'estrelas': [1, 2]
        }, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_verificar_aposta_numeros_fora_range(self):
        """Testar verificação com números fora do intervalo."""
        url = reverse('api-verificar')
        response = self.client.post(url, {
            'numeros': [1, 2, 3, 4, 51],  # 51 é inválido
            'estrelas': [1, 2]
        }, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_verificar_aposta_estrelas_invalidas(self):
        """Testar verificação com estrelas inválidas."""
        url = reverse('api-verificar')
        response = self.client.post(url, {
            'numeros': [1, 2, 3, 4, 5],
            'estrelas': [1, 13]  # 13 é inválido
        }, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
