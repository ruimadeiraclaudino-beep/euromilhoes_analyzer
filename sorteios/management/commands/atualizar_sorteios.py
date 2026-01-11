"""
Comando para atualizar automaticamente os sorteios do EuroMilhoes via web scraping.

Fonte: euro-millions.com/pt (versao portuguesa)

Uso:
    python manage.py atualizar_sorteios
    python manage.py atualizar_sorteios --ultimos 10
    python manage.py atualizar_sorteios --ano 2024
    python manage.py atualizar_sorteios --todos
"""
import time
import re
from datetime import datetime, date
from decimal import Decimal

import requests
from bs4 import BeautifulSoup
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from sorteios.models import Sorteio
from sorteios.services import AnalisadorEstatistico


class EuroMilhoesScraper:
    """Scraper para obter resultados do EuroMilhoes (fonte portuguesa)."""

    BASE_URL = "https://www.euro-millions.com/pt"

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
        'outubro': 10, 'novembro': 11, 'dezembro': 12
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

    def _parse_data_portuguesa(self, texto: str) -> date:
        """
        Converte data em portugues para objeto date.

        Formatos suportados:
        - "30 de dezembro de 2025"
        - "30-12-2025"
        - "2025-12-30"
        """
        texto = texto.strip().lower()

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
        Scrape os resultados mais recentes da pagina principal.

        Returns:
            Lista de dicts com dados dos sorteios
        """
        resultados = []
        url = f"{self.BASE_URL}/resultados"

        self.log(f"A buscar resultados recentes de {url}...")

        try:
            response = self.session.get(url, timeout=30)
            response.raise_for_status()

            soup = BeautifulSoup(response.text, 'html.parser')

            # Procurar linhas de resultados na tabela
            result_rows = soup.select('tr.resultRow')

            for row in result_rows:
                try:
                    result = self._parse_result_row(row)
                    if result:
                        resultados.append(result)
                except Exception as e:
                    self.log(f"Erro ao processar linha: {e}", warning=True)

            self.log(f"Encontrados {len(resultados)} sorteios na pagina de resultados")

        except requests.RequestException as e:
            self.log(f"Erro ao aceder {url}: {e}", error=True)

        return resultados

    def scrape_arquivo_ano(self, ano: int) -> list:
        """
        Scrape todos os resultados de um ano especifico.

        Args:
            ano: Ano a buscar (ex: 2024)

        Returns:
            Lista de dicts com dados dos sorteios
        """
        resultados = []
        url = f"{self.BASE_URL}/arquivo-de-resultados-{ano}"

        self.log(f"A buscar arquivo de {ano}...")

        try:
            response = self.session.get(url, timeout=30)

            if response.status_code == 404:
                self.log(f"Arquivo de {ano} nao encontrado", warning=True)
                return resultados

            response.raise_for_status()

            soup = BeautifulSoup(response.text, 'html.parser')

            # Procurar linhas de resultados
            result_rows = soup.select('tr.resultRow')

            for row in result_rows:
                try:
                    result = self._parse_result_row(row)
                    if result:
                        resultados.append(result)
                except Exception as e:
                    self.log(f"Erro ao processar linha: {e}", warning=True)

            self.log(f"Encontrados {len(resultados)} sorteios em {ano}")

            # Pequena pausa para nao sobrecarregar o servidor
            time.sleep(0.5)

        except requests.RequestException as e:
            self.log(f"Erro ao aceder {url}: {e}", error=True)

        return resultados

    def _parse_result_row(self, row) -> dict:
        """
        Parse uma linha de resultado da tabela.

        Args:
            row: Elemento BeautifulSoup da linha

        Returns:
            Dict com data, numeros e estrelas ou None
        """
        # Extrair data do link
        date_link = row.select_one('td.date a')
        if not date_link:
            return None

        # A data pode estar no href (formato dd-mm-yyyy)
        href = date_link.get('href', '')
        date_match = re.search(r'(\d{2}-\d{2}-\d{4})', href)

        if date_match:
            data = self._parse_data_portuguesa(date_match.group(1))
        else:
            # Tentar extrair do texto
            date_text = date_link.text.strip()
            data = self._parse_data_portuguesa(date_text)

        if not data:
            return None

        # Extrair numeros
        balls = row.select('li.resultBall.ball')
        numeros = []
        for ball in balls[:5]:
            try:
                num = int(ball.text.strip())
                if 1 <= num <= 50:
                    numeros.append(num)
            except ValueError:
                pass

        # Extrair estrelas
        stars = row.select('li.resultBall.lucky-star')
        estrelas = []
        for star in stars[:2]:
            try:
                num = int(star.text.strip())
                if 1 <= num <= 12:
                    estrelas.append(num)
            except ValueError:
                pass

        if len(numeros) != 5 or len(estrelas) != 2:
            return None

        return {
            'data': data,
            'numeros': sorted(numeros),
            'estrelas': sorted(estrelas),
        }

    def scrape_todos_anos(self, ano_inicio: int = 2004) -> list:
        """
        Scrape todos os resultados desde o ano de inicio.

        Args:
            ano_inicio: Ano inicial (default: 2004, inicio do EuroMilhoes)

        Returns:
            Lista de dicts com dados dos sorteios
        """
        resultados = []
        ano_atual = date.today().year

        for ano in range(ano_inicio, ano_atual + 1):
            resultados_ano = self.scrape_arquivo_ano(ano)
            resultados.extend(resultados_ano)

        return resultados


class Command(BaseCommand):
    help = 'Atualiza automaticamente os sorteios do EuroMilhoes via web scraping (fonte portuguesa)'

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

    def handle(self, *args, **options):
        scraper = EuroMilhoesScraper(stdout=self.stdout, style=self.style)

        self.stdout.write('='*60)
        self.stdout.write('EuroMilhoes Portugal - Atualizacao Automatica')
        self.stdout.write('Fonte: euro-millions.com/pt')
        self.stdout.write('='*60)

        # Obter resultados
        resultados = []

        if options['todos']:
            self.stdout.write('\nA importar todos os sorteios historicos (2004-presente)...')
            self.stdout.write('Isto pode demorar alguns minutos...\n')
            resultados = scraper.scrape_todos_anos()
        elif options['ano']:
            self.stdout.write(f"\nA importar sorteios de {options['ano']}...")
            resultados = scraper.scrape_arquivo_ano(options['ano'])
        else:
            self.stdout.write('\nA verificar resultados recentes...')
            resultados = scraper.scrape_resultados_recentes()

        if not resultados:
            self.stdout.write(self.style.WARNING('\nNenhum resultado encontrado.'))
            return

        self.stdout.write(f'\nEncontrados {len(resultados)} sorteios.')

        # Filtrar duplicados
        novos = []
        duplicados = 0

        for r in resultados:
            if not Sorteio.objects.filter(data=r['data']).exists():
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
                    f"  {r['data']}: {r['numeros']} + {r['estrelas']}"
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
                    Sorteio.objects.create(
                        data=r['data'],
                        numero_1=r['numeros'][0],
                        numero_2=r['numeros'][1],
                        numero_3=r['numeros'][2],
                        numero_4=r['numeros'][3],
                        numero_5=r['numeros'][4],
                        estrela_1=r['estrelas'][0],
                        estrela_2=r['estrelas'][1],
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
            analisador = AnalisadorEstatistico()
            analisador.atualizar_estatisticas()
            self.stdout.write(self.style.SUCCESS('Estatisticas atualizadas!'))

        # Resumo final
        total = Sorteio.objects.count()
        ultimo = Sorteio.objects.first()
        self.stdout.write(f'\nTotal de sorteios na base de dados: {total}')
        if ultimo:
            self.stdout.write(f'Ultimo sorteio: {ultimo.data}')
            self.stdout.write(f'  Numeros: {ultimo.get_numeros()}')
            self.stdout.write(f'  Estrelas: {ultimo.get_estrelas()}')
