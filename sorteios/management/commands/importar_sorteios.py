"""
Comando para importar dados históricos do EuroMilhões.

Uso:
    python manage.py importar_sorteios --fonte csv --ficheiro dados.csv
    python manage.py importar_sorteios --fonte web
    python manage.py importar_sorteios --fonte manual
"""
import csv
from datetime import datetime
from decimal import Decimal

import requests
from bs4 import BeautifulSoup
from django.core.management.base import BaseCommand, CommandError

from sorteios.models import Sorteio
from sorteios.services import AnalisadorEstatistico


class Command(BaseCommand):
    help = 'Importa dados históricos do EuroMilhões'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--fonte',
            type=str,
            choices=['csv', 'web', 'manual'],
            default='csv',
            help='Fonte dos dados: csv, web, ou manual'
        )
        parser.add_argument(
            '--ficheiro',
            type=str,
            help='Caminho para ficheiro CSV (obrigatório se fonte=csv)'
        )
        parser.add_argument(
            '--atualizar-stats',
            action='store_true',
            help='Atualizar estatísticas após importação'
        )
    
    def handle(self, *args, **options):
        fonte = options['fonte']
        
        if fonte == 'csv':
            if not options['ficheiro']:
                raise CommandError('Ficheiro CSV é obrigatório quando fonte=csv')
            self.importar_csv(options['ficheiro'])
        elif fonte == 'web':
            self.importar_web()
        elif fonte == 'manual':
            self.importar_manual()
        
        if options['atualizar_stats']:
            self.stdout.write('A atualizar estatísticas...')
            analisador = AnalisadorEstatistico()
            analisador.atualizar_estatisticas()
            self.stdout.write(self.style.SUCCESS('Estatísticas atualizadas!'))
    
    def importar_csv(self, ficheiro: str):
        """
        Importa sorteios de um ficheiro CSV.
        
        Formato esperado do CSV:
        data,n1,n2,n3,n4,n5,e1,e2,jackpot,vencedor
        2024-01-02,5,12,23,34,45,3,8,130000000,0
        
        OU formato do Kaggle/outros:
        Date,N1,N2,N3,N4,N5,S1,S2
        """
        self.stdout.write(f'A importar de {ficheiro}...')
        
        importados = 0
        duplicados = 0
        erros = 0
        
        try:
            with open(ficheiro, 'r', encoding='utf-8') as f:
                # Tentar detectar o formato
                primeiro_linha = f.readline()
                f.seek(0)
                
                reader = csv.DictReader(f)
                
                for row in reader:
                    try:
                        # Tentar diferentes formatos de coluna
                        data = self._parse_data(row)
                        numeros = self._parse_numeros(row)
                        estrelas = self._parse_estrelas(row)
                        
                        if not data or len(numeros) != 5 or len(estrelas) != 2:
                            erros += 1
                            continue
                        
                        # Verificar se já existe
                        if Sorteio.objects.filter(data=data).exists():
                            duplicados += 1
                            continue
                        
                        # Criar sorteio
                        jackpot = self._parse_jackpot(row)
                        vencedor = self._parse_vencedor(row)
                        
                        Sorteio.objects.create(
                            data=data,
                            numero_1=numeros[0],
                            numero_2=numeros[1],
                            numero_3=numeros[2],
                            numero_4=numeros[3],
                            numero_5=numeros[4],
                            estrela_1=estrelas[0],
                            estrela_2=estrelas[1],
                            jackpot=jackpot,
                            houve_vencedor=vencedor
                        )
                        importados += 1
                        
                    except Exception as e:
                        self.stderr.write(f'Erro na linha: {row} - {e}')
                        erros += 1
        
        except FileNotFoundError:
            raise CommandError(f'Ficheiro não encontrado: {ficheiro}')
        
        self.stdout.write(self.style.SUCCESS(
            f'Importação concluída: {importados} novos, {duplicados} duplicados, {erros} erros'
        ))
    
    def _parse_data(self, row: dict) -> datetime.date:
        """Tenta parsear a data de diferentes formatos de coluna."""
        for key in ['data', 'Data', 'DATE', 'Date', 'date']:
            if key in row:
                valor = row[key]
                # Tentar diferentes formatos
                for fmt in ['%Y-%m-%d', '%d/%m/%Y', '%d-%m-%Y', '%Y/%m/%d']:
                    try:
                        return datetime.strptime(valor, fmt).date()
                    except ValueError:
                        continue
        return None
    
    def _parse_numeros(self, row: dict) -> list:
        """Extrai os 5 números principais."""
        numeros = []
        
        # Formato: n1, n2, ... ou N1, N2, ... ou numero_1, ...
        for i in range(1, 6):
            for key in [f'n{i}', f'N{i}', f'numero_{i}', f'Numero{i}', f'Ball {i}']:
                if key in row:
                    try:
                        numeros.append(int(row[key]))
                        break
                    except (ValueError, TypeError):
                        pass
        
        return sorted(numeros)
    
    def _parse_estrelas(self, row: dict) -> list:
        """Extrai as 2 estrelas."""
        estrelas = []
        
        for i in range(1, 3):
            for key in [f'e{i}', f'E{i}', f'S{i}', f'estrela_{i}', f'Star{i}', f'Lucky Star {i}']:
                if key in row:
                    try:
                        estrelas.append(int(row[key]))
                        break
                    except (ValueError, TypeError):
                        pass
        
        return sorted(estrelas)
    
    def _parse_jackpot(self, row: dict) -> Decimal:
        """Extrai o valor do jackpot."""
        for key in ['jackpot', 'Jackpot', 'JACKPOT', 'premio', 'Prize']:
            if key in row and row[key]:
                try:
                    valor = row[key].replace('€', '').replace(',', '').strip()
                    return Decimal(valor)
                except (ValueError, TypeError, decimal.InvalidOperation):
                    pass
        return None
    
    def _parse_vencedor(self, row: dict) -> bool:
        """Verifica se houve vencedor."""
        for key in ['vencedor', 'Vencedor', 'winner', 'Winner']:
            if key in row:
                valor = str(row[key]).lower()
                return valor in ['1', 'true', 'sim', 'yes', 's', 'y']
        return False
    
    def importar_web(self):
        """
        Importa dados via web scraping.
        
        NOTA: Este método requer adaptação ao site específico.
        Usar com cuidado e respeitar robots.txt e termos de uso.
        """
        self.stdout.write('Importação web...')
        self.stdout.write(self.style.WARNING(
            'A importação web requer configuração específica para o site alvo.\n'
            'Recomenda-se usar um ficheiro CSV com dados históricos.\n'
            'Datasets disponíveis em:\n'
            '  - https://www.kaggle.com/datasets (pesquisar "euromillions")\n'
            '  - https://www.euro-millions.com/results-history\n'
        ))
        
        # Exemplo básico (descomente e adapte conforme necessário)
        """
        url = "https://www.euro-millions.com/results-history-2024"
        headers = {'User-Agent': 'Mozilla/5.0'}
        
        try:
            response = requests.get(url, headers=headers, timeout=30)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'lxml')
            # Adaptar seletores ao site específico
            # ...
            
        except requests.RequestException as e:
            raise CommandError(f'Erro ao aceder ao site: {e}')
        """
    
    def importar_manual(self):
        """Permite inserir sorteios manualmente."""
        self.stdout.write('Modo de inserção manual')
        self.stdout.write('Formato: AAAA-MM-DD n1 n2 n3 n4 n5 e1 e2')
        self.stdout.write('Digite "sair" para terminar\n')
        
        while True:
            try:
                entrada = input('Sorteio: ').strip()
                
                if entrada.lower() == 'sair':
                    break
                
                partes = entrada.split()
                if len(partes) < 8:
                    self.stderr.write('Formato inválido. Usar: AAAA-MM-DD n1 n2 n3 n4 n5 e1 e2')
                    continue
                
                data = datetime.strptime(partes[0], '%Y-%m-%d').date()
                numeros = sorted([int(x) for x in partes[1:6]])
                estrelas = sorted([int(x) for x in partes[6:8]])
                
                # Validações
                if not all(1 <= n <= 50 for n in numeros):
                    self.stderr.write('Números devem estar entre 1 e 50')
                    continue
                
                if not all(1 <= e <= 12 for e in estrelas):
                    self.stderr.write('Estrelas devem estar entre 1 e 12')
                    continue
                
                if Sorteio.objects.filter(data=data).exists():
                    self.stderr.write(f'Sorteio de {data} já existe')
                    continue
                
                Sorteio.objects.create(
                    data=data,
                    numero_1=numeros[0],
                    numero_2=numeros[1],
                    numero_3=numeros[2],
                    numero_4=numeros[3],
                    numero_5=numeros[4],
                    estrela_1=estrelas[0],
                    estrela_2=estrelas[1]
                )
                
                self.stdout.write(self.style.SUCCESS(f'Sorteio de {data} importado!'))
                
            except ValueError as e:
                self.stderr.write(f'Erro: {e}')
            except KeyboardInterrupt:
                break
        
        self.stdout.write('\nInserção manual terminada.')
