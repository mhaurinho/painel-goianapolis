"""Conferências entre demonstrativos com dados sintéticos: provam que divergências são detectadas.
Rodar da raiz: python -m unittest discover -s tests -v"""
import sys
import unittest
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from conferencias import conferencias, hierarquia  # noqa: E402

COLUNAS = ["exercicio", "periodo", "rotulo", "conta", "coluna", "valor"]
EXCETO = "Total das Despesas Exceto Intra-Orçamentárias"


def anexo01(liquidado=300.0, periodo=6, ano=2025):
    """Receita 400 = 350 correntes + 50 capital; despesa autorizada 500 ≥ empenhada = liquidada = paga."""
    linhas = [[ano, periodo, "Padrão", conta, "Até o Bimestre (c)", v] for conta, v in
              [("RECEITAS (EXCETO INTRA-ORÇAMENTÁRIAS) (I)", 400), ("RECEITAS CORRENTES", 350), ("RECEITAS DE CAPITAL", 50)]]
    for coluna, v in [("DOTAÇÃO ATUALIZADA (e)", 500), ("DESPESAS EMPENHADAS ATÉ O BIMESTRE (f)", liquidado),
                      ("DESPESAS LIQUIDADAS ATÉ O BIMESTRE (h)", liquidado), ("DESPESAS PAGAS ATÉ O BIMESTRE (j)", liquidado)]:
        linhas.append([ano, periodo, "Padrão", "DESPESAS (EXCETO INTRA-ORÇAMENTÁRIAS) (VIII)", coluna, v])
    return pd.DataFrame(linhas, columns=COLUNAS)


def anexo02(ensino=180.0, ano=2025, periodo=6):
    """Na ordem real da API: total, função, subfunções, ..., reserva (sem subfunção), total geral."""
    contas = [("DESPESAS (EXCETO INTRA-ORÇAMENTÁRIAS) (I)", 300), ("Educação", 200), ("Ensino Fundamental", ensino),
              ("FU12 - Demais Subfunções", 20), ("Saúde", 100), ("Atenção Básica", 100),
              ("Reserva de Contingência", 0), ("TOTAL (III) = (I + II)", 300)]
    linhas = [[ano, periodo, EXCETO, c, col, v] for col in
              ("DOTAÇÃO INICIAL", "DOTAÇÃO ATUALIZADA (a)", "DESPESAS EMPENHADAS ATÉ O BIMESTRE (b)",
               "DESPESAS LIQUIDADAS ATÉ O BIMESTRE (d)") for c, v in contas]
    return pd.DataFrame(linhas, columns=COLUNAS)


def status(a1, a2, ano=2025):
    return {c["teste"]: c["status"] for c in conferencias(a1, a2, ano)}


class HierarquiaTest(unittest.TestCase):
    def test_separa_funcao_subfuncao_e_reserva(self):
        h = hierarquia(anexo02())
        funcoes = h[h["subfuncao"].isna()].set_index("funcao")["liquidado"].to_dict()
        self.assertEqual(funcoes, {"Educação": 200, "Saúde": 100, "Reserva de Contingência": 0})
        self.assertEqual(set(h["subfuncao"].dropna()), {"Ensino Fundamental", "Demais Subfunções", "Atenção Básica"})

    def test_usa_ultimo_bimestre(self):
        a2 = pd.concat([anexo02(ensino=999, periodo=5), anexo02(periodo=6)])
        h = hierarquia(a2)
        self.assertEqual(h.loc[h["subfuncao"] == "Ensino Fundamental", "liquidado"].item(), 180)


class ConferenciasTest(unittest.TestCase):
    def test_bases_coerentes_passam_em_tudo(self):
        self.assertEqual(set(status(anexo01(), anexo02()).values()), {"ok"})

    def test_divergencia_entre_anexos(self):
        r = status(anexo01(liquidado=310), anexo02())
        self.assertEqual(r["Despesa liquidada: Anexo 01 = soma das funções do Anexo 02"], "divergente")

    def test_subfuncoes_que_nao_somam(self):
        r = conferencias(anexo01(), anexo02(ensino=170), 2025)
        item = next(c for c in r if c["teste"] == "Cada função = soma das suas subfunções")
        self.assertEqual(item["status"], "divergente")
        self.assertIn("Educação", item["detalhe"])

    def test_ano_sem_dado(self):
        r = status(anexo01(), anexo02(), ano=2030)
        self.assertIn("sem dado", r.values())


if __name__ == "__main__":
    unittest.main()
