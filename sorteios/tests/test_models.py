"""
Testes para os modelos.
"""
from datetime import date
from decimal import Decimal
from django.test import TestCase
from sorteios.models import Sorteio, EstatisticaNumero, EstatisticaEstrela, ApostaGerada


class SorteioModelTest(TestCase):
    """Testes para o modelo Sorteio."""

    def setUp(self):
        """Criar sorteio de teste."""
        self.sorteio = Sorteio.objects.create(
            data=date(2024, 1, 5),
            numero_1=5,
            numero_2=12,
            numero_3=23,
            numero_4=34,
            numero_5=45,
            estrela_1=3,
            estrela_2=8,
            jackpot=Decimal('50000000.00'),
            houve_vencedor=False
        )

    def test_sorteio_creation(self):
        """Testar criação de sorteio."""
        self.assertEqual(self.sorteio.data, date(2024, 1, 5))
        self.assertFalse(self.sorteio.houve_vencedor)

    def test_get_numeros(self):
        """Testar método get_numeros retorna lista ordenada."""
        numeros = self.sorteio.get_numeros()
        self.assertEqual(numeros, [5, 12, 23, 34, 45])
        self.assertEqual(len(numeros), 5)

    def test_get_estrelas(self):
        """Testar método get_estrelas retorna lista ordenada."""
        estrelas = self.sorteio.get_estrelas()
        self.assertEqual(estrelas, [3, 8])
        self.assertEqual(len(estrelas), 2)

    def test_soma_numeros(self):
        """Testar soma dos números."""
        soma = self.sorteio.soma_numeros()
        self.assertEqual(soma, 5 + 12 + 23 + 34 + 45)

    def test_soma_estrelas(self):
        """Testar soma das estrelas."""
        soma = self.sorteio.soma_estrelas()
        self.assertEqual(soma, 3 + 8)

    def test_pares_impares(self):
        """Testar contagem de pares e ímpares."""
        pares, impares = self.sorteio.pares_impares()
        # 12, 34 são pares (2), 5, 23, 45 são ímpares (3)
        self.assertEqual(pares, 2)
        self.assertEqual(impares, 3)

    def test_baixos_altos(self):
        """Testar contagem de baixos e altos."""
        baixos, altos = self.sorteio.baixos_altos()
        # 5, 12, 23 são baixos (<=25), 34, 45 são altos (>25)
        self.assertEqual(baixos, 3)
        self.assertEqual(altos, 2)

    def test_numeros_ordenados_ao_guardar(self):
        """Testar que números são ordenados ao guardar."""
        sorteio = Sorteio.objects.create(
            data=date(2024, 1, 6),
            numero_1=45,  # Desordenado propositadamente
            numero_2=5,
            numero_3=34,
            numero_4=12,
            numero_5=23,
            estrela_1=8,
            estrela_2=3
        )
        # Após save, devem estar ordenados
        self.assertEqual(sorteio.numero_1, 5)
        self.assertEqual(sorteio.numero_5, 45)
        self.assertEqual(sorteio.estrela_1, 3)
        self.assertEqual(sorteio.estrela_2, 8)

    def test_str_representation(self):
        """Testar representação string do sorteio."""
        str_repr = str(self.sorteio)
        self.assertIn('2024-01-05', str_repr)
        self.assertIn('05', str_repr)  # Primeiro número formatado


class EstatisticaNumeroModelTest(TestCase):
    """Testes para o modelo EstatisticaNumero."""

    def test_status_quente(self):
        """Testar status quente quando desvio > 0.1."""
        stat = EstatisticaNumero.objects.create(
            numero=44,
            frequencia=100,
            desvio_esperado=Decimal('0.15')
        )
        self.assertEqual(stat.status, 'quente')

    def test_status_frio(self):
        """Testar status frio quando desvio < -0.1."""
        stat = EstatisticaNumero.objects.create(
            numero=22,
            frequencia=50,
            desvio_esperado=Decimal('-0.15')
        )
        self.assertEqual(stat.status, 'frio')

    def test_status_normal(self):
        """Testar status normal quando desvio entre -0.1 e 0.1."""
        stat = EstatisticaNumero.objects.create(
            numero=33,
            frequencia=75,
            desvio_esperado=Decimal('0.05')
        )
        self.assertEqual(stat.status, 'normal')


class ApostaGeradaModelTest(TestCase):
    """Testes para o modelo ApostaGerada."""

    def setUp(self):
        """Criar aposta e sorteio de teste."""
        self.sorteio = Sorteio.objects.create(
            data=date(2024, 1, 5),
            numero_1=5,
            numero_2=12,
            numero_3=23,
            numero_4=34,
            numero_5=45,
            estrela_1=3,
            estrela_2=8
        )
        self.aposta = ApostaGerada.objects.create(
            estrategia='mista',
            numero_1=5,
            numero_2=12,
            numero_3=20,  # Diferente
            numero_4=34,
            numero_5=50,  # Diferente
            estrela_1=3,
            estrela_2=10  # Diferente
        )

    def test_verificar_resultado(self):
        """Testar verificação de resultado."""
        acertos_num, acertos_est = self.aposta.verificar_resultado(self.sorteio)
        # Acertos números: 5, 12, 34 = 3
        # Acertos estrelas: 3 = 1
        self.assertEqual(acertos_num, 3)
        self.assertEqual(acertos_est, 1)
        self.assertEqual(self.aposta.sorteio_verificado, self.sorteio)
