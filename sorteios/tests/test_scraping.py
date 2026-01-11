"""
Testes para o comando de web scraping atualizar_sorteios.
"""
from datetime import date
from unittest.mock import patch, MagicMock
from io import StringIO

from django.test import TestCase
from django.core.management import call_command

from sorteios.models import Sorteio
from sorteios.management.commands.atualizar_sorteios import EuroMilhoesScraper


class EuroMilhoesScraperTestCase(TestCase):
    """Testes para a classe EuroMilhoesScraper."""

    def setUp(self):
        """Configurar scraper para testes."""
        self.scraper = EuroMilhoesScraper()

    def test_parse_data_portuguesa_formato_dd_mm_yyyy(self):
        """Testar parsing de data no formato dd-mm-yyyy."""
        resultado = self.scraper._parse_data_portuguesa('30-12-2025')
        self.assertEqual(resultado, date(2025, 12, 30))

    def test_parse_data_portuguesa_formato_yyyy_mm_dd(self):
        """Testar parsing de data no formato yyyy-mm-dd."""
        resultado = self.scraper._parse_data_portuguesa('2025-12-30')
        self.assertEqual(resultado, date(2025, 12, 30))

    def test_parse_data_portuguesa_formato_extenso(self):
        """Testar parsing de data em formato extenso portugues."""
        resultado = self.scraper._parse_data_portuguesa('30 de dezembro de 2025')
        self.assertEqual(resultado, date(2025, 12, 30))

    def test_parse_data_portuguesa_todos_meses(self):
        """Testar parsing de todos os meses em portugues."""
        meses = [
            ('15 de janeiro de 2024', date(2024, 1, 15)),
            ('15 de fevereiro de 2024', date(2024, 2, 15)),
            ('15 de março de 2024', date(2024, 3, 15)),
            ('15 de marco de 2024', date(2024, 3, 15)),  # sem acento
            ('15 de abril de 2024', date(2024, 4, 15)),
            ('15 de maio de 2024', date(2024, 5, 15)),
            ('15 de junho de 2024', date(2024, 6, 15)),
            ('15 de julho de 2024', date(2024, 7, 15)),
            ('15 de agosto de 2024', date(2024, 8, 15)),
            ('15 de setembro de 2024', date(2024, 9, 15)),
            ('15 de outubro de 2024', date(2024, 10, 15)),
            ('15 de novembro de 2024', date(2024, 11, 15)),
            ('15 de dezembro de 2024', date(2024, 12, 15)),
        ]
        for texto, esperado in meses:
            resultado = self.scraper._parse_data_portuguesa(texto)
            self.assertEqual(resultado, esperado, f"Falhou para: {texto}")

    def test_parse_data_portuguesa_invalida(self):
        """Testar que data invalida retorna None."""
        resultado = self.scraper._parse_data_portuguesa('texto invalido')
        self.assertIsNone(resultado)

    def test_parse_data_portuguesa_mes_invalido(self):
        """Testar que mes invalido retorna None."""
        resultado = self.scraper._parse_data_portuguesa('15 de mesfalso de 2024')
        self.assertIsNone(resultado)

    def test_parse_result_row_valido(self):
        """Testar parsing de uma linha de resultado valida."""
        from bs4 import BeautifulSoup

        html = '''
        <tr class="resultRow">
            <td class="date"><a href="/pt/resultados/02-01-2026">02-01-2026</a></td>
            <td>
                <ul>
                    <li class="resultBall ball">8</li>
                    <li class="resultBall ball">27</li>
                    <li class="resultBall ball">42</li>
                    <li class="resultBall ball">44</li>
                    <li class="resultBall ball">46</li>
                    <li class="resultBall lucky-star">1</li>
                    <li class="resultBall lucky-star">10</li>
                </ul>
            </td>
        </tr>
        '''
        soup = BeautifulSoup(html, 'html.parser')
        row = soup.find('tr', class_='resultRow')

        resultado = self.scraper._parse_result_row(row)

        self.assertIsNotNone(resultado)
        self.assertEqual(resultado['data'], date(2026, 1, 2))
        self.assertEqual(resultado['numeros'], [8, 27, 42, 44, 46])
        self.assertEqual(resultado['estrelas'], [1, 10])

    def test_parse_result_row_sem_data(self):
        """Testar que linha sem data retorna None."""
        from bs4 import BeautifulSoup

        html = '''
        <tr class="resultRow">
            <td class="date"></td>
        </tr>
        '''
        soup = BeautifulSoup(html, 'html.parser')
        row = soup.find('tr', class_='resultRow')

        resultado = self.scraper._parse_result_row(row)
        self.assertIsNone(resultado)

    def test_parse_result_row_numeros_incompletos(self):
        """Testar que linha com numeros incompletos retorna None."""
        from bs4 import BeautifulSoup

        html = '''
        <tr class="resultRow">
            <td class="date"><a href="/pt/resultados/02-01-2026">02-01-2026</a></td>
            <td>
                <ul>
                    <li class="resultBall ball">8</li>
                    <li class="resultBall ball">27</li>
                    <li class="resultBall lucky-star">1</li>
                </ul>
            </td>
        </tr>
        '''
        soup = BeautifulSoup(html, 'html.parser')
        row = soup.find('tr', class_='resultRow')

        resultado = self.scraper._parse_result_row(row)
        self.assertIsNone(resultado)

    def test_parse_result_row_numeros_fora_intervalo(self):
        """Testar que numeros fora do intervalo sao ignorados."""
        from bs4 import BeautifulSoup

        html = '''
        <tr class="resultRow">
            <td class="date"><a href="/pt/resultados/02-01-2026">02-01-2026</a></td>
            <td>
                <ul>
                    <li class="resultBall ball">8</li>
                    <li class="resultBall ball">27</li>
                    <li class="resultBall ball">42</li>
                    <li class="resultBall ball">44</li>
                    <li class="resultBall ball">99</li>
                    <li class="resultBall lucky-star">1</li>
                    <li class="resultBall lucky-star">10</li>
                </ul>
            </td>
        </tr>
        '''
        soup = BeautifulSoup(html, 'html.parser')
        row = soup.find('tr', class_='resultRow')

        resultado = self.scraper._parse_result_row(row)
        # Deve retornar None porque so tem 4 numeros validos
        self.assertIsNone(resultado)


class ScraperMockedRequestsTestCase(TestCase):
    """Testes com requests mockados."""

    def setUp(self):
        """Configurar scraper para testes."""
        self.scraper = EuroMilhoesScraper()

    @patch('sorteios.management.commands.atualizar_sorteios.requests.Session')
    def test_scrape_resultados_recentes_sucesso(self, mock_session_class):
        """Testar scraping de resultados recentes com sucesso."""
        mock_session = MagicMock()
        mock_session_class.return_value = mock_session

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = '''
        <html>
        <body>
            <tr class="resultRow">
                <td class="date"><a href="/pt/resultados/02-01-2026">02-01-2026</a></td>
                <td>
                    <ul>
                        <li class="resultBall ball">8</li>
                        <li class="resultBall ball">27</li>
                        <li class="resultBall ball">42</li>
                        <li class="resultBall ball">44</li>
                        <li class="resultBall ball">46</li>
                        <li class="resultBall lucky-star">1</li>
                        <li class="resultBall lucky-star">10</li>
                    </ul>
                </td>
            </tr>
        </body>
        </html>
        '''
        mock_session.get.return_value = mock_response

        scraper = EuroMilhoesScraper()
        resultados = scraper.scrape_resultados_recentes()

        self.assertEqual(len(resultados), 1)
        self.assertEqual(resultados[0]['data'], date(2026, 1, 2))
        self.assertEqual(resultados[0]['numeros'], [8, 27, 42, 44, 46])
        self.assertEqual(resultados[0]['estrelas'], [1, 10])

    @patch('sorteios.management.commands.atualizar_sorteios.requests.Session')
    def test_scrape_arquivo_ano_404(self, mock_session_class):
        """Testar scraping de ano que retorna 404."""
        mock_session = MagicMock()
        mock_session_class.return_value = mock_session

        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_session.get.return_value = mock_response

        scraper = EuroMilhoesScraper()
        resultados = scraper.scrape_arquivo_ano(1999)

        self.assertEqual(len(resultados), 0)


class ComandoAtualizarSorteiosTestCase(TestCase):
    """Testes para o comando Django atualizar_sorteios."""

    def setUp(self):
        """Criar dados de teste."""
        # Criar um sorteio existente
        Sorteio.objects.create(
            data=date(2025, 12, 31),
            numero_1=1, numero_2=2, numero_3=3, numero_4=4, numero_5=5,
            estrela_1=1, estrela_2=2
        )

    @patch('sorteios.management.commands.atualizar_sorteios.EuroMilhoesScraper')
    def test_comando_dry_run(self, mock_scraper_class):
        """Testar comando em modo dry-run."""
        mock_scraper = MagicMock()
        mock_scraper_class.return_value = mock_scraper
        mock_scraper.scrape_resultados_recentes.return_value = [
            {
                'data': date(2026, 1, 2),
                'numeros': [8, 27, 42, 44, 46],
                'estrelas': [1, 10]
            }
        ]

        out = StringIO()
        call_command('atualizar_sorteios', '--dry-run', stdout=out)

        output = out.getvalue()
        self.assertIn('DRY RUN', output)
        self.assertIn('2026-01-02', output)

        # Verificar que nao foi criado novo sorteio
        self.assertEqual(Sorteio.objects.count(), 1)

    @patch('sorteios.management.commands.atualizar_sorteios.EuroMilhoesScraper')
    def test_comando_importa_novos(self, mock_scraper_class):
        """Testar que comando importa novos sorteios."""
        mock_scraper = MagicMock()
        mock_scraper_class.return_value = mock_scraper
        mock_scraper.scrape_resultados_recentes.return_value = [
            {
                'data': date(2026, 1, 2),
                'numeros': [8, 27, 42, 44, 46],
                'estrelas': [1, 10]
            }
        ]

        out = StringIO()
        call_command('atualizar_sorteios', '--no-stats', stdout=out)

        output = out.getvalue()
        self.assertIn('1 novos sorteios', output)

        # Verificar que foi criado novo sorteio
        self.assertEqual(Sorteio.objects.count(), 2)
        novo = Sorteio.objects.get(data=date(2026, 1, 2))
        self.assertEqual(novo.get_numeros(), [8, 27, 42, 44, 46])
        self.assertEqual(novo.get_estrelas(), [1, 10])

    @patch('sorteios.management.commands.atualizar_sorteios.EuroMilhoesScraper')
    def test_comando_ignora_duplicados(self, mock_scraper_class):
        """Testar que comando ignora sorteios duplicados."""
        mock_scraper = MagicMock()
        mock_scraper_class.return_value = mock_scraper
        mock_scraper.scrape_resultados_recentes.return_value = [
            {
                'data': date(2025, 12, 31),  # Ja existe
                'numeros': [1, 2, 3, 4, 5],
                'estrelas': [1, 2]
            }
        ]

        out = StringIO()
        call_command('atualizar_sorteios', '--no-stats', stdout=out)

        output = out.getvalue()
        self.assertIn('ja esta atualizada', output)

        # Verificar que nao foi criado novo sorteio
        self.assertEqual(Sorteio.objects.count(), 1)

    @patch('sorteios.management.commands.atualizar_sorteios.EuroMilhoesScraper')
    def test_comando_sem_resultados(self, mock_scraper_class):
        """Testar comando quando nao ha resultados."""
        mock_scraper = MagicMock()
        mock_scraper_class.return_value = mock_scraper
        mock_scraper.scrape_resultados_recentes.return_value = []

        out = StringIO()
        call_command('atualizar_sorteios', stdout=out)

        output = out.getvalue()
        self.assertIn('Nenhum resultado encontrado', output)

    @patch('sorteios.management.commands.atualizar_sorteios.EuroMilhoesScraper')
    def test_comando_ano_especifico(self, mock_scraper_class):
        """Testar comando com opcao --ano."""
        mock_scraper = MagicMock()
        mock_scraper_class.return_value = mock_scraper
        mock_scraper.scrape_arquivo_ano.return_value = [
            {
                'data': date(2024, 6, 15),
                'numeros': [10, 20, 30, 40, 50],
                'estrelas': [3, 7]
            }
        ]

        out = StringIO()
        call_command('atualizar_sorteios', '--ano', '2024', '--no-stats', stdout=out)

        mock_scraper.scrape_arquivo_ano.assert_called_once_with(2024)
        self.assertEqual(Sorteio.objects.count(), 2)

    @patch('sorteios.management.commands.atualizar_sorteios.EuroMilhoesScraper')
    def test_comando_todos(self, mock_scraper_class):
        """Testar comando com opcao --todos."""
        mock_scraper = MagicMock()
        mock_scraper_class.return_value = mock_scraper
        mock_scraper.scrape_todos_anos.return_value = [
            {
                'data': date(2004, 2, 13),
                'numeros': [5, 10, 15, 20, 25],
                'estrelas': [2, 8]
            }
        ]

        out = StringIO()
        call_command('atualizar_sorteios', '--todos', '--no-stats', stdout=out)

        mock_scraper.scrape_todos_anos.assert_called_once()
        self.assertEqual(Sorteio.objects.count(), 2)


class ScraperLogTestCase(TestCase):
    """Testes para o sistema de logging do scraper."""

    def test_log_com_stdout(self):
        """Testar que log funciona com stdout."""
        out = StringIO()
        scraper = EuroMilhoesScraper(stdout=out)

        scraper.log("Mensagem de teste")

        self.assertIn("Mensagem de teste", out.getvalue())

    def test_log_sem_stdout(self):
        """Testar que log funciona sem stdout (sem erro)."""
        scraper = EuroMilhoesScraper()
        # Nao deve lancar excecao
        scraper.log("Mensagem de teste")
