"""
Configuração do Django Admin para EuroMilhões Analyzer.
"""
from django.contrib import admin
from .models import Sorteio, EstatisticaNumero, EstatisticaEstrela, ApostaGerada


@admin.register(Sorteio)
class SorteioAdmin(admin.ModelAdmin):
    list_display = ['data', 'concurso', 'numeros_display', 'estrelas_display', 'jackpot', 'houve_vencedor']
    list_filter = ['houve_vencedor', 'data']
    search_fields = ['concurso']
    date_hierarchy = 'data'
    ordering = ['-data']
    
    def numeros_display(self, obj):
        return obj.get_numeros_str()
    numeros_display.short_description = 'Números'
    
    def estrelas_display(self, obj):
        return obj.get_estrelas_str()
    estrelas_display.short_description = 'Estrelas'


@admin.register(EstatisticaNumero)
class EstatisticaNumeroAdmin(admin.ModelAdmin):
    list_display = ['numero', 'frequencia', 'percentagem', 'dias_sem_sair', 'gap_medio', 'status_display']
    list_filter = ['atualizado_em']
    ordering = ['numero']
    readonly_fields = ['atualizado_em']
    
    def status_display(self, obj):
        return obj.status.title()
    status_display.short_description = 'Status'


@admin.register(EstatisticaEstrela)
class EstatisticaEstrelaAdmin(admin.ModelAdmin):
    list_display = ['estrela', 'frequencia', 'percentagem', 'dias_sem_sair', 'gap_medio', 'status_display']
    list_filter = ['atualizado_em']
    ordering = ['estrela']
    readonly_fields = ['atualizado_em']
    
    def status_display(self, obj):
        return obj.status.title()
    status_display.short_description = 'Status'


@admin.register(ApostaGerada)
class ApostaGeradaAdmin(admin.ModelAdmin):
    list_display = ['id', 'data_geracao', 'estrategia', 'numeros_display', 'estrelas_display', 'acertos_numeros', 'acertos_estrelas']
    list_filter = ['estrategia', 'data_geracao']
    ordering = ['-data_geracao']
    
    def numeros_display(self, obj):
        return ' - '.join(f'{n:02d}' for n in obj.get_numeros())
    numeros_display.short_description = 'Números'
    
    def estrelas_display(self, obj):
        return ' - '.join(f'{e:02d}' for e in obj.get_estrelas())
    estrelas_display.short_description = 'Estrelas'
