"""
Testes para analise de padroes e previsoes ML.
"""
from datetime import date
from django.test import TestCase, Client
from django.urls import reverse

from sorteios.models import Sorteio, EstatisticaNumero, EstatisticaEstrela
from sorteios.services import AnalisadorEstatistico
from sorteios.ml import PrevisaoML


class AnalisePadroesTestCase(TestCase):
    """Testes para analise de padroes."""

    def setUp(self):
        """Criar dados de teste."""
        # Criar alguns sorteios para teste
        self.sorteios = []
        datas = [
            date(2024, 1, 2),
            date(2024, 1, 5),
            date(2024, 1, 9),
            date(2024, 1, 12),
            date(2024, 1, 16),
        ]
        numeros_lista = [
            (1, 2, 3, 4, 5),      # Consecutivos
            (10, 20, 30, 40, 50),  # Sem consecutivos
            (11, 12, 23, 24, 35), # Pares de consecutivos
            (5, 15, 25, 35, 45),  # Mesma terminacao
            (7, 14, 21, 28, 42),  # Multiplos de 7
        ]
        estrelas_lista = [
            (1, 2),
            (5, 10),
            (3, 7),
            (2, 11),
            (4, 9),
        ]

        for i, data in enumerate(datas):
            nums = numeros_lista[i]
            ests = estrelas_lista[i]
            sorteio = Sorteio.objects.create(
                data=data,
                numero_1=nums[0],
                numero_2=nums[1],
                numero_3=nums[2],
                numero_4=nums[3],
                numero_5=nums[4],
                estrela_1=ests[0],
                estrela_2=ests[1]
            )
            self.sorteios.append(sorteio)

        self.client = Client()

    def test_analise_consecutivos(self):
        """Testar analise de numeros consecutivos."""
        analisador = AnalisadorEstatistico()
        resultado = analisador.analisar_numeros_consecutivos()

        self.assertIn('total_com_consecutivos', resultado)
        self.assertIn('percentagem', resultado)
        self.assertIn('distribuicao', resultado)
        self.assertGreaterEqual(resultado['total_com_consecutivos'], 0)

    def test_analise_dezenas(self):
        """Testar analise por dezenas."""
        analisador = AnalisadorEstatistico()
        resultado = analisador.analisar_dezenas()

        self.assertIn('frequencia_dezenas', resultado)
        self.assertIn('padroes_comuns', resultado)
        self.assertEqual(len(resultado['frequencia_dezenas']), 5)

    def test_analise_terminacoes(self):
        """Testar analise de terminacoes."""
        analisador = AnalisadorEstatistico()
        resultado = analisador.analisar_terminacoes()

        self.assertIn('frequencia_terminacoes', resultado)
        self.assertIn('terminacoes_repetidas', resultado)

    def test_analise_sequencias(self):
        """Testar analise de sequencias consecutivas."""
        analisador = AnalisadorEstatistico()
        resultado = analisador.analisar_sequencias(2)

        self.assertIsInstance(resultado, list)

    def test_analise_soma_tendencias(self):
        """Testar analise de tendencias de soma."""
        analisador = AnalisadorEstatistico()
        resultado = analisador.analisar_soma_tendencias(5)

        self.assertIn('media_numeros', resultado)
        self.assertIn('tendencia', resultado)
        self.assertIn(resultado['tendencia'], ['subindo', 'descendo', 'estavel'])

    def test_analise_padroes_completa(self):
        """Testar analise completa de padroes."""
        analisador = AnalisadorEstatistico()
        resultado = analisador.get_analise_padroes_completa()

        self.assertIn('combinacoes_pares', resultado)
        self.assertIn('combinacoes_trios', resultado)
        self.assertIn('consecutivos', resultado)
        self.assertIn('dezenas', resultado)
        self.assertIn('terminacoes', resultado)
        self.assertIn('total_sorteios', resultado)

    def test_view_analise_padroes(self):
        """Testar view de analise de padroes."""
        response = self.client.get(reverse('analise_padroes'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'sorteios/analise_padroes.html')

    def test_api_padroes(self):
        """Testar API de padroes."""
        response = self.client.get(reverse('api_padroes'))
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn('total_sorteios', data)
        self.assertIn('combinacoes_pares', data)


class PrevisaoMLTestCase(TestCase):
    """Testes para previsoes ML."""

    def setUp(self):
        """Criar dados de teste."""
        # Criar sorteios suficientes para o modelo ML
        datas_base = date(2024, 1, 1)
        for i in range(100):
            dia = datas_base.toordinal() + i * 3
            data = date.fromordinal(dia)

            # Gerar numeros pseudo-aleatorios baseados no indice
            nums = sorted([
                (i * 7 + 1) % 50 + 1,
                (i * 11 + 2) % 50 + 1,
                (i * 13 + 3) % 50 + 1,
                (i * 17 + 4) % 50 + 1,
                (i * 19 + 5) % 50 + 1,
            ])
            ests = sorted([
                (i * 3 + 1) % 12 + 1,
                (i * 5 + 2) % 12 + 1,
            ])

            # Garantir que sao unicos
            nums = list(dict.fromkeys(nums))
            while len(nums) < 5:
                nums.append((nums[-1] % 50) + 1)
            nums = sorted(set(nums))[:5]

            ests = list(dict.fromkeys(ests))
            while len(ests) < 2:
                ests.append((ests[-1] % 12) + 1)
            ests = sorted(set(ests))[:2]

            Sorteio.objects.create(
                data=data,
                numero_1=nums[0],
                numero_2=nums[1],
                numero_3=nums[2],
                numero_4=nums[3],
                numero_5=nums[4],
                estrela_1=ests[0],
                estrela_2=ests[1]
            )

        self.client = Client()

    def test_previsao_ml_inicializacao(self):
        """Testar inicializacao do modelo ML."""
        ml = PrevisaoML()
        self.assertGreater(ml.total_sorteios, 0)
        self.assertEqual(len(ml.features_numeros), 50)
        self.assertEqual(len(ml.features_estrelas), 12)

    def test_calcular_score_numero(self):
        """Testar calculo de score para numero."""
        ml = PrevisaoML()
        score = ml.calcular_score_numero(23)
        self.assertGreaterEqual(score, 0)
        self.assertLessEqual(score, 1)

    def test_calcular_score_estrela(self):
        """Testar calculo de score para estrela."""
        ml = PrevisaoML()
        score = ml.calcular_score_estrela(5)
        self.assertGreaterEqual(score, 0)
        self.assertLessEqual(score, 1)

    def test_prever_proximos_numeros(self):
        """Testar previsao de proximos numeros."""
        ml = PrevisaoML()
        previsao = ml.prever_proximos_numeros('equilibrada')

        self.assertIn('numeros', previsao)
        self.assertIn('estrelas', previsao)
        self.assertIn('confianca', previsao)
        self.assertIn('aviso', previsao)

        self.assertEqual(len(previsao['numeros']), 5)
        self.assertEqual(len(previsao['estrelas']), 2)

        # Verificar que numeros estao no intervalo correto
        for num in previsao['numeros']:
            self.assertGreaterEqual(num, 1)
            self.assertLessEqual(num, 50)

        for est in previsao['estrelas']:
            self.assertGreaterEqual(est, 1)
            self.assertLessEqual(est, 12)

    def test_diferentes_estrategias(self):
        """Testar diferentes estrategias de previsao."""
        ml = PrevisaoML()

        for estrategia in ['frequencia', 'atraso', 'tendencia', 'equilibrada']:
            previsao = ml.prever_proximos_numeros(estrategia)
            self.assertEqual(previsao['estrategia'], estrategia)
            self.assertEqual(len(previsao['numeros']), 5)

    def test_ranking_numeros(self):
        """Testar ranking de numeros."""
        ml = PrevisaoML()
        ranking = ml.get_ranking_numeros()

        self.assertEqual(len(ranking), 50)
        for item in ranking:
            self.assertIn('numero', item)
            self.assertIn('score', item)
            self.assertIn('frequencia', item)

    def test_ranking_estrelas(self):
        """Testar ranking de estrelas."""
        ml = PrevisaoML()
        ranking = ml.get_ranking_estrelas()

        self.assertEqual(len(ranking), 12)
        for item in ranking:
            self.assertIn('estrela', item)
            self.assertIn('score', item)

    def test_analise_completa(self):
        """Testar analise ML completa."""
        ml = PrevisaoML()
        analise = ml.get_analise_completa()

        self.assertIn('previsao_equilibrada', analise)
        self.assertIn('previsao_frequencia', analise)
        self.assertIn('ranking_numeros', analise)
        self.assertIn('ranking_estrelas', analise)
        self.assertIn('aviso', analise)

    def test_view_previsao_ml(self):
        """Testar view de previsao ML."""
        response = self.client.get(reverse('previsao_ml'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'sorteios/previsao_ml.html')

    def test_api_previsao_ml(self):
        """Testar API de previsao ML."""
        response = self.client.get(reverse('api_previsao_ml'))
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn('numeros', data)
        self.assertIn('estrelas', data)

    def test_api_ranking_ml(self):
        """Testar API de ranking ML."""
        response = self.client.get(reverse('api_ranking_ml'))
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn('numeros', data)
        self.assertIn('estrelas', data)


class GraficosAvancadosTestCase(TestCase):
    """Testes para graficos avancados."""

    def setUp(self):
        """Criar dados de teste."""
        for i in range(10):
            data = date(2024, 1, i + 1)
            Sorteio.objects.create(
                data=data,
                numero_1=(i + 1),
                numero_2=(i + 11),
                numero_3=(i + 21),
                numero_4=(i + 31),
                numero_5=(i + 41) if i + 41 <= 50 else 50,
                estrela_1=(i % 12) + 1,
                estrela_2=((i + 1) % 12) + 1
            )

        # Criar estatisticas
        analisador = AnalisadorEstatistico()
        analisador.atualizar_estatisticas()

        self.client = Client()

    def test_view_graficos_avancados(self):
        """Testar view de graficos avancados."""
        response = self.client.get(reverse('graficos_avancados'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'sorteios/graficos_avancados.html')
        self.assertIn('estatisticas_numeros_json', response.context)
        self.assertIn('tendencias_json', response.context)

    def test_api_evolucao_frequencia(self):
        """Testar API de evolucao de frequencia."""
        response = self.client.get(reverse('api_evolucao_frequencia'), {'numero': 1})
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn('numero', data)
        self.assertIn('dados', data)

    def test_api_heatmap_mensal(self):
        """Testar API de heatmap mensal."""
        response = self.client.get(reverse('api_heatmap_mensal'))
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIsInstance(data, dict)

    def test_api_correlacao_numeros(self):
        """Testar API de correlacao de numeros."""
        response = self.client.get(reverse('api_correlacao_numeros'))
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn('matriz', data)
        self.assertIn('labels', data)
        self.assertEqual(len(data['matriz']), 50)
        self.assertEqual(len(data['labels']), 50)


class ModoEscuroTestCase(TestCase):
    """Testes para verificar que o modo escuro esta implementado."""

    def setUp(self):
        self.client = Client()

    def test_base_template_tem_toggle_tema(self):
        """Verificar que o template base tem o toggle de tema."""
        Sorteio.objects.create(
            data=date(2024, 1, 1),
            numero_1=1, numero_2=2, numero_3=3, numero_4=4, numero_5=5,
            estrela_1=1, estrela_2=2
        )

        response = self.client.get(reverse('dashboard'))
        self.assertEqual(response.status_code, 200)

        content = response.content.decode('utf-8')
        self.assertIn('data-bs-theme', content)
        self.assertIn('themeToggle', content)
        self.assertIn('bi-moon-fill', content)
