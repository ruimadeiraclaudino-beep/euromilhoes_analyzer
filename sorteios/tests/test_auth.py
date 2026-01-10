"""
Testes para a API de autenticação.
"""
from django.urls import reverse
from rest_framework.test import APITestCase, APIClient
from rest_framework import status
from django.contrib.auth.models import User
from rest_framework.authtoken.models import Token


class LoginAPITest(APITestCase):
    """Testes para endpoint de login."""

    def setUp(self):
        """Criar utilizador de teste."""
        self.client = APIClient()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )

    def test_login_success(self):
        """Testar login com sucesso."""
        url = reverse('api-login')
        response = self.client.post(url, {
            'username': 'testuser',
            'password': 'testpass123'
        })

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('token', response.data)
        self.assertIn('user', response.data)
        self.assertEqual(response.data['user']['username'], 'testuser')

    def test_login_invalid_credentials(self):
        """Testar login com credenciais inválidas."""
        url = reverse('api-login')
        response = self.client.post(url, {
            'username': 'testuser',
            'password': 'wrongpassword'
        })

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertIn('error', response.data)

    def test_login_missing_username(self):
        """Testar login sem username."""
        url = reverse('api-login')
        response = self.client.post(url, {
            'password': 'testpass123'
        })

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_login_missing_password(self):
        """Testar login sem password."""
        url = reverse('api-login')
        response = self.client.post(url, {
            'username': 'testuser'
        })

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_login_nonexistent_user(self):
        """Testar login com utilizador inexistente."""
        url = reverse('api-login')
        response = self.client.post(url, {
            'username': 'nonexistent',
            'password': 'testpass123'
        })

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class RegisterAPITest(APITestCase):
    """Testes para endpoint de registo."""

    def setUp(self):
        """Criar cliente de teste."""
        self.client = APIClient()

    def test_register_success(self):
        """Testar registo com sucesso."""
        url = reverse('api-register')
        response = self.client.post(url, {
            'username': 'newuser',
            'email': 'newuser@example.com',
            'password': 'newpass123'
        })

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn('token', response.data)
        self.assertIn('user', response.data)
        self.assertEqual(response.data['user']['username'], 'newuser')

        # Verificar que utilizador foi criado
        self.assertTrue(User.objects.filter(username='newuser').exists())

    def test_register_duplicate_username(self):
        """Testar registo com username duplicado."""
        User.objects.create_user(
            username='existinguser',
            email='existing@example.com',
            password='pass123'
        )

        url = reverse('api-register')
        response = self.client.post(url, {
            'username': 'existinguser',
            'email': 'new@example.com',
            'password': 'newpass123'
        })

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_register_duplicate_email(self):
        """Testar registo com email duplicado."""
        User.objects.create_user(
            username='existinguser',
            email='existing@example.com',
            password='pass123'
        )

        url = reverse('api-register')
        response = self.client.post(url, {
            'username': 'newuser',
            'email': 'existing@example.com',
            'password': 'newpass123'
        })

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_register_short_username(self):
        """Testar registo com username muito curto."""
        url = reverse('api-register')
        response = self.client.post(url, {
            'username': 'ab',  # Mínimo é 3
            'email': 'test@example.com',
            'password': 'newpass123'
        })

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_register_invalid_email(self):
        """Testar registo com email inválido."""
        url = reverse('api-register')
        response = self.client.post(url, {
            'username': 'newuser',
            'email': 'not-an-email',
            'password': 'newpass123'
        })

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_register_short_password(self):
        """Testar registo com password muito curta."""
        url = reverse('api-register')
        response = self.client.post(url, {
            'username': 'newuser',
            'email': 'test@example.com',
            'password': 'abc'  # Mínimo é 4
        })

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class LogoutAPITest(APITestCase):
    """Testes para endpoint de logout."""

    def setUp(self):
        """Criar utilizador e token de teste."""
        self.client = APIClient()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.token = Token.objects.create(user=self.user)

    def test_logout_success(self):
        """Testar logout com sucesso."""
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.token.key}')

        url = reverse('api-logout')
        response = self.client.post(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Verificar que token foi apagado
        self.assertFalse(Token.objects.filter(user=self.user).exists())

    def test_logout_without_auth(self):
        """Testar logout sem autenticação."""
        url = reverse('api-logout')
        response = self.client.post(url)

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class ProfileAPITest(APITestCase):
    """Testes para endpoint de perfil."""

    def setUp(self):
        """Criar utilizador e token de teste."""
        self.client = APIClient()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.token = Token.objects.create(user=self.user)

    def test_profile_authenticated(self):
        """Testar acesso ao perfil autenticado."""
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.token.key}')

        url = reverse('api-profile')
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('user', response.data)
        self.assertEqual(response.data['user']['username'], 'testuser')

    def test_profile_unauthenticated(self):
        """Testar acesso ao perfil sem autenticação."""
        url = reverse('api-profile')
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class RefreshTokenAPITest(APITestCase):
    """Testes para endpoint de refresh de token."""

    def setUp(self):
        """Criar utilizador e token de teste."""
        self.client = APIClient()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.token = Token.objects.create(user=self.user)
        self.old_token_key = self.token.key

    def test_refresh_token_success(self):
        """Testar refresh de token com sucesso."""
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.token.key}')

        url = reverse('api-refresh-token')
        response = self.client.post(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('token', response.data)

        # Verificar que é um token diferente
        self.assertNotEqual(response.data['token'], self.old_token_key)

        # Verificar que token antigo já não funciona
        self.assertFalse(Token.objects.filter(key=self.old_token_key).exists())

    def test_refresh_token_unauthenticated(self):
        """Testar refresh de token sem autenticação."""
        url = reverse('api-refresh-token')
        response = self.client.post(url)

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class PermissionsAPITest(APITestCase):
    """Testes para verificar permissões da API."""

    def setUp(self):
        """Criar dados de teste."""
        self.client = APIClient()
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
        self.token = Token.objects.create(user=self.user)

    def test_public_endpoints_accessible(self):
        """Testar que endpoints públicos são acessíveis sem auth."""
        public_urls = [
            reverse('api-sorteios-list'),
            reverse('api-numeros-list'),
            reverse('api-estrelas-list'),
            reverse('api-estatisticas'),
        ]

        for url in public_urls:
            response = self.client.get(url)
            self.assertIn(
                response.status_code,
                [status.HTTP_200_OK, status.HTTP_404_NOT_FOUND],
                f"URL {url} deveria ser pública"
            )

    def test_protected_endpoints_require_auth(self):
        """Testar que endpoints protegidos requerem autenticação."""
        url = reverse('api-apostas-gerar')
        response = self.client.post(url, {'estrategia': 'mista'})

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_protected_endpoints_with_auth(self):
        """Testar que endpoints protegidos funcionam com autenticação."""
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.token.key}')

        # Criar estatísticas necessárias
        from sorteios.models import EstatisticaNumero, EstatisticaEstrela
        for i in range(1, 51):
            EstatisticaNumero.objects.create(numero=i, frequencia=50)
        for i in range(1, 13):
            EstatisticaEstrela.objects.create(estrela=i, frequencia=20)

        url = reverse('api-apostas-gerar')
        response = self.client.post(url, {'estrategia': 'aleatorio'})

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
