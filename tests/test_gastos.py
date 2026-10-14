"""Despesa por elemento (DCA) e classificação de compras, com dados sintéticos."""
import sys
import unittest
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from gastos import categorizar, conferencia_dca_rreo, elementos, total_dca  # noqa: E402


def dca(ano=2025, consumo=120.0):
    """Total 1000 = pessoal 600 (salários 600) + custeio 400 (consumo + serviços 250, resto não detalhado)."""
    contas = [("TotalDespesas", "Total Geral da Despesa", 1000), ("DO3.1.00.00.00.00", "3.1 - Pessoal", 600),
              ("DO3.1.90.11.00.00", "3.1.90.11.00 - Vencimentos e Vantagens Fixas", 600),
              ("DO3.3.00.00.00.00", "3.3 - Outras Despesas Correntes", 400),
              ("DO3.3.90.30.00.00", "3.3.90.30.00 - Material de Consumo", consumo),
              ("DO3.3.90.39.00.00", "3.3.90.39.00 - Outros Serviços de Terceiros - PJ", 250),
              ("DO3.1.90.13.02.00", "3.1.90.13.02 - INSS (subelemento, não pode somar)", 999)]
    return pd.DataFrame([{"exercicio": ano, "coluna": "Despesas Liquidadas", "cod_conta": c, "conta": n, "valor": v}
                         for c, n, v in contas])


class ElementosTest(unittest.TestCase):
    def test_total_fecha_com_linha_nao_detalhada(self):
        e = elementos(dca())
        self.assertAlmostEqual(e["valor"].sum(), total_dca(dca())[2025])
        sobra = e[e["elemento"].str.contains("não detalhado")]
        self.assertEqual(sobra["valor"].tolist(), [30.0])

    def test_nome_em_linguagem_simples_e_sem_subelemento(self):
        nomes = set(elementos(dca())["elemento"])
        self.assertIn("Material de consumo", nomes)
        self.assertIn("Salários do funcionalismo", nomes)
        self.assertFalse(any("INSS" in n for n in nomes))


class ConferenciaDcaRreoTest(unittest.TestCase):
    def a1(self, liquidado):
        return pd.DataFrame([{"exercicio": 2025, "periodo": 6, "conta": "DESPESAS (EXCETO INTRA-ORÇAMENTÁRIAS) (VIII)",
                              "coluna": "DESPESAS LIQUIDADAS ATÉ O BIMESTRE (h)", "valor": liquidado}])

    def test_confere(self):
        self.assertEqual(conferencia_dca_rreo(dca(), self.a1(1000))["status"].item(), "ok")

    def test_diverge(self):
        r = conferencia_dca_rreo(dca(), self.a1(900))
        self.assertEqual(r["status"].item(), "divergente")
        self.assertEqual(r["diferenca"].item(), 100)


class CategorizarTest(unittest.TestCase):
    def test_categorias(self):
        casos = {"Pavimentação asfáltica da Rua 3": "Obras, pavimentação e sinalização",
                 "AQUISIÇÃO DE MEDICAMENTOS PARA A UBS": "Saúde e medicamentos",
                 "Gêneros alimentícios para a merenda": "Alimentação e merenda",
                 "TARIFA PARA PRESTAÇÃO DE SERVIÇOS BANCÁRIOS": "Tarifas bancárias e telefonia",
                 "Contratação de locutor para a cavalgada": "Eventos e festas",
                 "Algo sem palavra-chave": "Outros", None: "Outros"}
        for objeto, esperado in casos.items():
            with self.subTest(objeto=objeto):
                self.assertEqual(categorizar(objeto), esperado)


if __name__ == "__main__":
    unittest.main()
