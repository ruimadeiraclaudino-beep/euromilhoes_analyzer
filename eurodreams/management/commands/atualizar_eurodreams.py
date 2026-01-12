"""
Comando para atualizar automaticamente os sorteios do EuroDreams via web scraping.

EuroDreams: Lancado em Novembro 2023
- 6 numeros de 1-40
- 1 Dream de 1-5
- Sorteios: Segundas e Quintas

Fonte: eurodreams.com ou jogossantacasa.pt

Uso:
    python manage.py atualizar_eurodreams
    python manage.py atualizar_eurodreams --todos
    python manage.py atualizar_eurodreams --csv dados.csv
"""
import time
import re
from datetime import datetime, date
from decimal import Decimal

import requests
from bs4 import BeautifulSoup
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from eurodreams.models import SorteioEuroDreams, EstatisticaNumeroEuroDreams, EstatisticaDreamEuroDreams
from eurodreams.services import AnalisadorEuroDreams


class EuroDreamsScraper:
    """Scraper para obter resultados do EuroDreams."""

    BASE_URL = "https://www.euro-dreams.com/pt"
    ALT_URL = "https://www.jogossantacasa.pt/web/SCCartaz/eurodreams"

    HEADERS = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'pt-PT,pt;q=0.9,en;q=0.8',
    }

    MESES_PT = {
        'janeiro': 1, 'fevereiro': 2, 'março': 3, 'marco': 3,
        'abril': 4, 'maio': 5, 'junho': 6,
        'julho': 7, 'agosto': 8, 'setembro': 9,
        'outubro': 10, 'novembro': 11, 'dezembro': 12,
        'jan': 1, 'fev': 2, 'mar': 3, 'abr': 4, 'mai': 5, 'jun': 6,
        'jul': 7, 'ago': 8, 'set': 9, 'out': 10, 'nov': 11, 'dez': 12
    }

    def __init__(self, stdout=None, style=None):
        self.stdout = stdout
        self.style = style
        self.session = requests.Session()
        self.session.headers.update(self.HEADERS)

    def log(self, message, success=False, warning=False, error=False):
        """Log message to stdout if available."""
        if self.stdout:
            if success and self.style:
                self.stdout.write(self.style.SUCCESS(message))
            elif warning and self.style:
                self.stdout.write(self.style.WARNING(message))
            elif error and self.style:
                self.stdout.write(self.style.ERROR(message))
            else:
                self.stdout.write(message)

    def _parse_data(self, texto: str) -> date:
        """
        Converte data em portugues para objeto date.
        """
        if not texto:
            return None

        texto = texto.strip().lower()

        # Formato: dd/mm/yyyy
        match = re.match(r'(\d{1,2})/(\d{1,2})/(\d{4})', texto)
        if match:
            dia, mes, ano = match.groups()
            return date(int(ano), int(mes), int(dia))

        # Formato: dd-mm-yyyy
        match = re.match(r'(\d{1,2})-(\d{1,2})-(\d{4})', texto)
        if match:
            dia, mes, ano = match.groups()
            return date(int(ano), int(mes), int(dia))

        # Formato: yyyy-mm-dd
        match = re.match(r'(\d{4})-(\d{1,2})-(\d{1,2})', texto)
        if match:
            ano, mes, dia = match.groups()
            return date(int(ano), int(mes), int(dia))

        # Formato: "30 de dezembro de 2025"
        match = re.match(r'(\d{1,2})\s+de\s+(\w+)\s+de\s+(\d{4})', texto)
        if match:
            dia, mes_nome, ano = match.groups()
            mes = self.MESES_PT.get(mes_nome)
            if mes:
                return date(int(ano), mes, int(dia))

        return None

    def scrape_resultados_recentes(self) -> list:
        """
        Scrape os resultados mais recentes do EuroDreams.
        """
        resultados = []

        # Tentar diferentes URLs
        urls = [
            f"{self.BASE_URL}/resultados",
            self.BASE_URL,
            self.ALT_URL,
        ]

        for url in urls:
            self.log(f"A tentar {url}...")

            try:
                response = self.session.get(url, timeout=30)

                if response.status_code != 200:
                    continue

                soup = BeautifulSoup(response.text, 'html.parser')

                # Procurar resultados em tabela
                result_rows = soup.select('tr.resultRow, tr.result-row, .resultado')
                for row in result_rows:
                    result = self._parse_result_row(row)
                    if result:
                        resultados.append(result)

                # Procurar resultado principal
                if not resultados:
                    result = self._parse_resultado_principal(soup)
                    if result:
                        resultados.append(result)

                if resultados:
                    break

                time.sleep(0.5)

            except requests.RequestException as e:
                self.log(f"Erro: {e}", warning=True)

        self.log(f"Encontrados {len(resultados)} sorteios")
        return resultados

    def _parse_result_row(self, row) -> dict:
        """Parse uma linha de resultado."""
        try:
            # Extrair data
            date_elem = row.select_one('td.date a, .data, .date')
            if not date_elem:
                return None

            # Tentar extrair data do href ou texto
            href = date_elem.get('href', '') if hasattr(date_elem, 'get') else ''
            date_match = re.search(r'(\d{2}-\d{2}-\d{4})', href)

            if date_match:
                data = self._parse_data(date_match.group(1))
            else:
                data = self._parse_data(date_elem.text if hasattr(date_elem, 'text') else str(date_elem))

            if not data:
                return None

            # Extrair numeros (6 bolas)
            balls = row.select('li.resultBall.ball, .ball, .numero, .bola')
            numeros = []
            for ball in balls[:6]:
                try:
                    num = int(ball.text.strip())
                    if 1 <= num <= 40:
                        numeros.append(num)
                except ValueError:
                    pass

            if len(numeros) != 6:
                return None

            # Extrair Dream (1-5)
            dream = None
            dream_elem = row.select_one('li.resultBall.dream, .dream, .sonho')
            if dream_elem:
                try:
                    dream = int(dream_elem.text.strip())
                    if not (1 <= dream <= 5):
                        dream = None
                except ValueError:
                    pass

            if not dream:
                # Tentar extrair do texto
                text = row.get_text() if hasattr(row, 'get_text') else str(row)
                dream_match = re.search(r'dream[:\s]*(\d)', text, re.IGNORECASE)
                if dream_match:
                    dream = int(dream_match.group(1))

            if not dream:
                return None

            return {
                'data': data,
                'numeros': sorted(numeros),
                'dream': dream
            }

        except Exception:
            return None

    def _parse_resultado_principal(self, soup) -> dict:
        """Parse resultado principal da pagina."""
        try:
            # Procurar data
            date_elem = soup.select_one('.data-sorteio, .draw-date, .result-date')
            data = None
            if date_elem:
                data = self._parse_data(date_elem.text)

            if not data:
                # Usar data atual se nao encontrar
                data = date.today()

            # Procurar numeros
            balls = soup.select('.ball, .numero, .winning-number')
            numeros = []
            for ball in balls:
                try:
                    num = int(ball.text.strip())
                    if 1 <= num <= 40 and num not in numeros:
                        numeros.append(num)
                except ValueError:
                    pass

            if len(numeros) < 6:
                return None

            # Procurar Dream
            dream = None
            dream_elem = soup.select_one('.dream, .dream-number, .sonho')
            if dream_elem:
                try:
                    dream = int(dream_elem.text.strip())
                except ValueError:
                    pass

            if not dream:
                return None

            return {
                'data': data,
                'numeros': sorted(numeros[:6]),
                'dream': dream
            }

        except Exception:
            return None

    def scrape_arquivo(self) -> list:
        """
        Scrape todos os resultados historicos.
        EuroDreams comecou em Novembro 2023.
        """
        resultados = []

        # Tentar pagina de arquivo
        urls = [
            f"{self.BASE_URL}/arquivo-de-resultados",
            f"{self.BASE_URL}/results-history",
        ]

        for url in urls:
            self.log(f"A tentar arquivo: {url}...")

            try:
                response = self.session.get(url, timeout=30)
                if response.status_code != 200:
                    continue

                soup = BeautifulSoup(response.text, 'html.parser')

                result_rows = soup.select('tr.resultRow, tr.result-row, .resultado')
                for row in result_rows:
                    result = self._parse_result_row(row)
                    if result:
                        resultados.append(result)

                if resultados:
                    break

            except requests.RequestException as e:
                self.log(f"Erro: {e}", warning=True)

            time.sleep(0.5)

        return resultados


class Command(BaseCommand):
    help = 'Atualiza automaticamente os sorteios do EuroDreams via web scraping'

    def add_arguments(self, parser):
        parser.add_argument(
            '--todos',
            action='store_true',
            help='Importar todos os sorteios historicos'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Apenas mostrar o que seria importado, sem gravar'
        )
        parser.add_argument(
            '--no-stats',
            action='store_true',
            help='Nao atualizar estatisticas apos importacao'
        )
        parser.add_argument(
            '--csv',
            type=str,
            help='Importar de ficheiro CSV em vez de web scraping'
        )

    def handle(self, *args, **options):
        self.stdout.write('=' * 60)
        self.stdout.write('EuroDreams - Atualizacao Automatica')
        self.stdout.write('6 Numeros (1-40) + 1 Dream (1-5)')
        self.stdout.write('=' * 60)

        resultados = []

        # Importar de CSV se especificado
        if options['csv']:
            resultados = self.importar_csv(options['csv'])
        else:
            scraper = EuroDreamsScraper(stdout=self.stdout, style=self.style)

            if options['todos']:
                self.stdout.write('\nA importar todos os sorteios historicos...')
                resultados = scraper.scrape_arquivo()
            else:
                self.stdout.write('\nA verificar resultados recentes...')
                resultados = scraper.scrape_resultados_recentes()

        if not resultados:
            self.stdout.write(self.style.WARNING('\nNenhum resultado encontrado.'))
            self.stdout.write('\nSugestao: Use --csv para importar de um ficheiro CSV.')
            self.stdout.write('Formato CSV: data,n1,n2,n3,n4,n5,n6,dream')
            self.stdout.write('\nExemplo:')
            self.stdout.write('  2024-01-15,3,12,18,25,33,40,2')
            return

        self.stdout.write(f'\nEncontrados {len(resultados)} sorteios.')

        # Filtrar duplicados
        novos = []
        duplicados = 0

        for r in resultados:
            if not SorteioEuroDreams.objects.filter(data=r['data']).exists():
                novos.append(r)
            else:
                duplicados += 1

        self.stdout.write(f'Novos: {len(novos)}, Ja existentes: {duplicados}')

        if not novos:
            self.stdout.write(self.style.SUCCESS('\nBase de dados ja esta atualizada!'))
            return

        # Dry run
        if options['dry_run']:
            self.stdout.write('\n[DRY RUN] Sorteios que seriam importados:')
            for r in sorted(novos, key=lambda x: x['data'], reverse=True)[:10]:
                self.stdout.write(
                    f"  {r['data']}: {r['numeros']} + Dream {r['dream']}"
                )
            if len(novos) > 10:
                self.stdout.write(f'  ... e mais {len(novos) - 10} sorteios')
            return

        # Importar
        self.stdout.write('\nA importar novos sorteios...')
        importados = 0
        erros = 0

        with transaction.atomic():
            for r in novos:
                try:
                    SorteioEuroDreams.objects.create(
                        data=r['data'],
                        numero_1=r['numeros'][0],
                        numero_2=r['numeros'][1],
                        numero_3=r['numeros'][2],
                        numero_4=r['numeros'][3],
                        numero_5=r['numeros'][4],
                        numero_6=r['numeros'][5],
                        dream=r['dream'],
                    )
                    importados += 1
                except Exception as e:
                    self.stderr.write(f"Erro ao importar {r['data']}: {e}")
                    erros += 1

        self.stdout.write(self.style.SUCCESS(
            f'\nImportacao concluida: {importados} novos sorteios!'
        ))

        if erros > 0:
            self.stdout.write(self.style.WARNING(f'Erros: {erros}'))

        # Atualizar estatisticas
        if not options['no_stats'] and importados > 0:
            self.stdout.write('\nA atualizar estatisticas...')
            analisador = AnalisadorEuroDreams()
            analisador.atualizar_estatisticas()
            self.stdout.write(self.style.SUCCESS('Estatisticas atualizadas!'))

        # Resumo final
        total = SorteioEuroDreams.objects.count()
        ultimo = SorteioEuroDreams.objects.first()
        self.stdout.write(f'\nTotal de sorteios na base de dados: {total}')
        if ultimo:
            self.stdout.write(f'Ultimo sorteio: {ultimo.data}')
            self.stdout.write(f'  Numeros: {ultimo.get_numeros()}')
            self.stdout.write(f'  Dream: {ultimo.dream}')

    def importar_csv(self, ficheiro: str) -> list:
        """
        Importa sorteios de um ficheiro CSV.

        Formato esperado:
        data,n1,n2,n3,n4,n5,n6,dream
        2024-01-15,3,12,18,25,33,40,2
        """
        import csv

        self.stdout.write(f'A importar de {ficheiro}...')
        resultados = []

        try:
            with open(ficheiro, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)

                for row in reader:
                    try:
                        # Parse data
                        data = None
                        for key in ['data', 'Data', 'DATE', 'Date', 'date']:
                            if key in row:
                                for fmt in ['%Y-%m-%d', '%d/%m/%Y', '%d-%m-%Y']:
                                    try:
                                        data = datetime.strptime(row[key], fmt).date()
                                        break
                                    except ValueError:
                                        continue
                            if data:
                                break

                        if not data:
                            continue

                        # Parse numeros (6)
                        numeros = []
                        for i in range(1, 7):
                            for key in [f'n{i}', f'N{i}', f'numero_{i}', f'Numero{i}']:
                                if key in row:
                                    try:
                                        numeros.append(int(row[key]))
                                        break
                                    except (ValueError, TypeError):
                                        pass

                        if len(numeros) != 6:
                            continue

                        # Parse dream
                        dream = None
                        for key in ['dream', 'Dream', 'DREAM', 'sonho', 'Sonho']:
                            if key in row and row[key]:
                                try:
                                    dream = int(row[key])
                                    break
                                except (ValueError, TypeError):
                                    pass

                        if not dream or not (1 <= dream <= 5):
                            continue

                        resultados.append({
                            'data': data,
                            'numeros': sorted(numeros),
                            'dream': dream
                        })

                    except Exception as e:
                        self.stderr.write(f'Erro na linha: {row} - {e}')

        except FileNotFoundError:
            self.stderr.write(f'Ficheiro nao encontrado: {ficheiro}')

        return resultados
