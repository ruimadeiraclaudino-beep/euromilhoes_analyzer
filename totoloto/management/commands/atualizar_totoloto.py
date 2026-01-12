"""
Comando para atualizar automaticamente os sorteios do Totoloto via web scraping.

Fonte: jogossantacasa.pt

Uso:
    python manage.py atualizar_totoloto
    python manage.py atualizar_totoloto --ultimos 10
    python manage.py atualizar_totoloto --ano 2024
    python manage.py atualizar_totoloto --todos
"""
import time
import re
from datetime import datetime, date
from decimal import Decimal

import requests
from bs4 import BeautifulSoup
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from totoloto.models import SorteioTotoloto, EstatisticaNumeroTotoloto
from totoloto.services import AnalisadorTotoloto


class TotolotoScraper:
    """Scraper para obter resultados do Totoloto da Santa Casa."""

    BASE_URL = "https://www.jogossantacasa.pt/web/SCCart498"

    HEADERS = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'pt-PT,pt;q=0.9,en;q=0.8',
    }

    # Mapeamento de meses em portugues
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

        Formatos suportados:
        - "30 de dezembro de 2025"
        - "30-12-2025"
        - "2025-12-30"
        - "30/12/2025"
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
        Scrape os resultados mais recentes do Totoloto.

        Returns:
            Lista de dicts com dados dos sorteios
        """
        resultados = []
        url = self.BASE_URL

        self.log(f"A buscar resultados do Totoloto...")

        try:
            response = self.session.get(url, timeout=30)
            response.raise_for_status()

            soup = BeautifulSoup(response.text, 'html.parser')

            # Procurar secoes de resultados
            # A estrutura do site da Santa Casa pode variar
            # Tentamos varias abordagens

            # Abordagem 1: Procurar tabela de resultados
            result_tables = soup.select('.results, .resultados, table.resultados')

            for table in result_tables:
                rows = table.select('tr')
                for row in rows:
                    result = self._parse_result_row_santa_casa(row)
                    if result:
                        resultados.append(result)

            # Abordagem 2: Procurar divs com classes especificas
            if not resultados:
                result_divs = soup.select('.resultado, .draw-result, .concurso')
                for div in result_divs:
                    result = self._parse_result_div_santa_casa(div)
                    if result:
                        resultados.append(result)

            # Abordagem 3: Procurar numeros com formato especifico
            if not resultados:
                result = self._parse_resultado_principal(soup)
                if result:
                    resultados.append(result)

            self.log(f"Encontrados {len(resultados)} sorteios")

        except requests.RequestException as e:
            self.log(f"Erro ao aceder {url}: {e}", error=True)

        return resultados

    def _parse_result_row_santa_casa(self, row) -> dict:
        """Parse uma linha de resultado da tabela Santa Casa."""
        try:
            # Extrair data
            date_cell = row.select_one('td.data, td:first-child')
            if not date_cell:
                return None

            data = self._parse_data(date_cell.text)
            if not data:
                return None

            # Extrair numeros (5 bolas)
            balls = row.select('.ball, .numero, .bola')
            numeros = []
            for ball in balls[:5]:
                try:
                    num = int(ball.text.strip())
                    if 1 <= num <= 49:
                        numeros.append(num)
                except ValueError:
                    pass

            if len(numeros) != 5:
                # Tentar extrair de texto
                text = row.get_text()
                nums = re.findall(r'\b(\d{1,2})\b', text)
                numeros = [int(n) for n in nums if 1 <= int(n) <= 49][:5]

            if len(numeros) != 5:
                return None

            # Extrair numero complementar
            complementar = None
            comp_elem = row.select_one('.complementar, .bola-complementar')
            if comp_elem:
                try:
                    complementar = int(comp_elem.text.strip())
                except ValueError:
                    pass

            return {
                'data': data,
                'numeros': sorted(numeros),
                'complementar': complementar
            }

        except Exception:
            return None

    def _parse_result_div_santa_casa(self, div) -> dict:
        """Parse um div de resultado."""
        try:
            # Procurar data
            date_elem = div.select_one('.data, .date, time')
            if not date_elem:
                return None

            data = self._parse_data(date_elem.text)
            if not data:
                return None

            # Procurar numeros
            balls = div.select('.ball, .numero, .bola, span.n')
            numeros = []
            for ball in balls:
                try:
                    num = int(ball.text.strip())
                    if 1 <= num <= 49:
                        numeros.append(num)
                except ValueError:
                    pass

            if len(numeros) < 5:
                return None

            return {
                'data': data,
                'numeros': sorted(numeros[:5]),
                'complementar': numeros[5] if len(numeros) > 5 else None
            }

        except Exception:
            return None

    def _parse_resultado_principal(self, soup) -> dict:
        """Parse resultado principal da pagina."""
        try:
            # Procurar data do sorteio
            date_elem = soup.select_one('.data-sorteio, .draw-date, h2.date, .concurso-data')
            if not date_elem:
                return None

            data = self._parse_data(date_elem.text)
            if not data:
                # Tentar hoje se nao encontrar data
                data = date.today()

            # Procurar bolas/numeros
            balls = soup.select('.ball, .numero, .bola, .winning-number')
            numeros = []

            for ball in balls:
                try:
                    num = int(ball.text.strip())
                    if 1 <= num <= 49 and num not in numeros:
                        numeros.append(num)
                except ValueError:
                    pass

            if len(numeros) >= 5:
                return {
                    'data': data,
                    'numeros': sorted(numeros[:5]),
                    'complementar': numeros[5] if len(numeros) > 5 else None
                }

            return None

        except Exception:
            return None

    def scrape_arquivo_ano(self, ano: int) -> list:
        """
        Scrape resultados de um ano especifico.

        O site da Santa Casa pode ter uma estrutura diferente para arquivos.
        """
        resultados = []

        # URL do arquivo pode variar
        urls_tentar = [
            f"https://www.jogossantacasa.pt/web/SCCartaz498/totoloto/historico/{ano}",
            f"https://www.jogossantacasa.pt/web/SCCartaz498/{ano}",
        ]

        for url in urls_tentar:
            self.log(f"A tentar {url}...")

            try:
                response = self.session.get(url, timeout=30)

                if response.status_code == 404:
                    continue

                response.raise_for_status()
                soup = BeautifulSoup(response.text, 'html.parser')

                # Tentar extrair resultados
                tables = soup.select('table')
                for table in tables:
                    rows = table.select('tr')
                    for row in rows:
                        result = self._parse_result_row_santa_casa(row)
                        if result and result['data'].year == ano:
                            resultados.append(result)

                if resultados:
                    break

                time.sleep(0.5)

            except requests.RequestException as e:
                self.log(f"Erro: {e}", warning=True)

        self.log(f"Encontrados {len(resultados)} sorteios de {ano}")
        return resultados


class Command(BaseCommand):
    help = 'Atualiza automaticamente os sorteios do Totoloto via web scraping'

    def add_arguments(self, parser):
        parser.add_argument(
            '--ultimos',
            type=int,
            default=20,
            help='Numero de ultimos sorteios a verificar (default: 20)'
        )
        parser.add_argument(
            '--ano',
            type=int,
            help='Importar todos os sorteios de um ano especifico'
        )
        parser.add_argument(
            '--todos',
            action='store_true',
            help='Importar todos os sorteios historicos desde 2004'
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
        self.stdout.write('Totoloto - Atualizacao Automatica')
        self.stdout.write('=' * 60)

        resultados = []

        # Importar de CSV se especificado
        if options['csv']:
            resultados = self.importar_csv(options['csv'])
        else:
            scraper = TotolotoScraper(stdout=self.stdout, style=self.style)

            if options['todos']:
                self.stdout.write('\nA importar todos os sorteios historicos...')
                ano_atual = date.today().year
                for ano in range(2004, ano_atual + 1):
                    resultados.extend(scraper.scrape_arquivo_ano(ano))
            elif options['ano']:
                self.stdout.write(f"\nA importar sorteios de {options['ano']}...")
                resultados = scraper.scrape_arquivo_ano(options['ano'])
            else:
                self.stdout.write('\nA verificar resultados recentes...')
                resultados = scraper.scrape_resultados_recentes()

        if not resultados:
            self.stdout.write(self.style.WARNING('\nNenhum resultado encontrado.'))
            self.stdout.write('\nSugestao: Use --csv para importar de um ficheiro CSV.')
            self.stdout.write('Formato CSV: data,n1,n2,n3,n4,n5,complementar')
            return

        self.stdout.write(f'\nEncontrados {len(resultados)} sorteios.')

        # Filtrar duplicados
        novos = []
        duplicados = 0

        for r in resultados:
            if not SorteioTotoloto.objects.filter(data=r['data']).exists():
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
                    f"  {r['data']}: {r['numeros']} + {r.get('complementar', '-')}"
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
                    SorteioTotoloto.objects.create(
                        data=r['data'],
                        numero1=r['numeros'][0],
                        numero2=r['numeros'][1],
                        numero3=r['numeros'][2],
                        numero4=r['numeros'][3],
                        numero5=r['numeros'][4],
                        numero_complementar=r.get('complementar'),
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
            analisador = AnalisadorTotoloto()
            analisador.atualizar_estatisticas()
            self.stdout.write(self.style.SUCCESS('Estatisticas atualizadas!'))

        # Resumo final
        total = SorteioTotoloto.objects.count()
        ultimo = SorteioTotoloto.objects.first()
        self.stdout.write(f'\nTotal de sorteios na base de dados: {total}')
        if ultimo:
            self.stdout.write(f'Ultimo sorteio: {ultimo.data}')
            self.stdout.write(f'  Numeros: {ultimo.get_numeros()}')

    def importar_csv(self, ficheiro: str) -> list:
        """
        Importa sorteios de um ficheiro CSV.

        Formato esperado:
        data,n1,n2,n3,n4,n5,complementar
        2024-01-02,5,12,23,34,45,7
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

                        # Parse numeros
                        numeros = []
                        for i in range(1, 6):
                            for key in [f'n{i}', f'N{i}', f'numero_{i}', f'Numero{i}']:
                                if key in row:
                                    try:
                                        numeros.append(int(row[key]))
                                        break
                                    except (ValueError, TypeError):
                                        pass

                        if len(numeros) != 5:
                            continue

                        # Parse complementar
                        complementar = None
                        for key in ['complementar', 'Complementar', 'comp', 'C']:
                            if key in row and row[key]:
                                try:
                                    complementar = int(row[key])
                                    break
                                except (ValueError, TypeError):
                                    pass

                        resultados.append({
                            'data': data,
                            'numeros': sorted(numeros),
                            'complementar': complementar
                        })

                    except Exception as e:
                        self.stderr.write(f'Erro na linha: {row} - {e}')

        except FileNotFoundError:
            self.stderr.write(f'Ficheiro nao encontrado: {ficheiro}')

        return resultados
