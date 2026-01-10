"""
Comando para atualizar estatísticas do EuroMilhões.

Uso:
    python manage.py atualizar_estatisticas
"""
from django.core.management.base import BaseCommand

from sorteios.models import Sorteio
from sorteios.services import AnalisadorEstatistico


class Command(BaseCommand):
    help = 'Atualiza todas as estatísticas baseadas nos sorteios existentes'
    
    def handle(self, *args, **options):
        total_sorteios = Sorteio.objects.count()
        
        if total_sorteios == 0:
            self.stdout.write(self.style.WARNING(
                'Nenhum sorteio encontrado. Importe dados primeiro com:\n'
                '  python manage.py importar_sorteios --fonte csv --ficheiro dados.csv'
            ))
            return
        
        self.stdout.write(f'A processar {total_sorteios} sorteios...')
        
        analisador = AnalisadorEstatistico()
        analisador.atualizar_estatisticas()
        
        self.stdout.write(self.style.SUCCESS(
            f'Estatísticas atualizadas com sucesso!\n'
            f'  - 50 estatísticas de números\n'
            f'  - 12 estatísticas de estrelas'
        ))
        
        # Mostrar resumo
        self.stdout.write('\n--- TOP 5 Números Quentes ---')
        for n in analisador.numeros_quentes(5):
            self.stdout.write(f'  Número {n:02d}')
        
        self.stdout.write('\n--- TOP 5 Números Frios ---')
        for n in analisador.numeros_frios(5):
            self.stdout.write(f'  Número {n:02d}')
        
        self.stdout.write('\n--- TOP 3 Estrelas Quentes ---')
        for e in analisador.estrelas_quentes(3):
            self.stdout.write(f'  Estrela {e:02d}')
