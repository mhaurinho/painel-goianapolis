"""Escala das séries: nominal, corrigida pelo IPCA e por morador."""
import sys
import unittest
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import valores as V  # noqa: E402

# 1% ao mês em 2024 e 0% em 2025: o índice médio de 2024 fica abaixo do atual, o de 2025 igual.
IPCA = pd.DataFrame({"data": [f"2024-{m:02d}-01" for m in range(1, 13)] + [f"2025-{m:02d}-01" for m in range(1, 13)],
                     "ipca_mensal": [1.0] * 12 + [0.0] * 12})
SERIE = pd.DataFrame({"exercicio": [2024, 2025], "valor": [100.0, 100.0]})


class ValoresTest(unittest.TestCase):
    def setUp(self):
        self.fatores, self.ref = V.fatores_ipca(IPCA)

    def tearDown(self):
        V.configurar(V.NOMINAL, {}, "", None)

    def test_fatores(self):
        self.assertEqual(self.ref, "dez/2025")
        self.assertAlmostEqual(self.fatores[2025], 1.0)
        self.assertGreater(self.fatores[2024], 1.05)

    def test_nominal_nao_altera(self):
        V.configurar(V.NOMINAL, self.fatores, self.ref, None)
        self.assertEqual(V.ajustar(SERIE)["valor"].tolist(), [100.0, 100.0])
        self.assertEqual(V.unidade(), "R$ nominais")

    def test_ipca_corrige_ano_antigo(self):
        V.configurar(V.IPCA, self.fatores, self.ref, None)
        v = V.ajustar(SERIE)["valor"].tolist()
        self.assertGreater(v[0], 105)
        self.assertAlmostEqual(v[1], 100.0)
        self.assertEqual(V.unidade(), "R$ de dez/2025")
        self.assertEqual(SERIE["valor"].tolist(), [100.0, 100.0], "não pode alterar o original")

    def test_por_morador(self):
        V.configurar(V.POR_MORADOR, self.fatores, self.ref, {2024: 10, 2025: 20}.get)
        self.assertEqual(V.ajustar(SERIE)["valor"].tolist(), [10.0, 5.0])

    def test_crescimento_real(self):
        V.configurar(V.NOMINAL, self.fatores, self.ref, None)
        self.assertLess(V.crescimento_real(100, 2024, 100, 2025), 0)  # mesmo nominal = queda real
        self.assertIsNone(V.crescimento_real(100, 2010, 100, 2025))


if __name__ == "__main__":
    unittest.main()
