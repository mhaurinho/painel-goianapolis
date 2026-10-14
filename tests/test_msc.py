"""Tradução dos códigos da MSC e recorte da folha (LRF)."""
import sys
import unittest
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from msc import folha, fonte_grupo, preparar  # noqa: E402


def linhas():
    base = {"exercicio": 2025, "mes": 12, "poder_orgao": 10131}
    return pd.DataFrame([
        {**base, "funcao": 12, "subfuncao": 361, "natureza_despesa": 31901101, "fonte_recursos": 1540, "valor": 100.0},
        {**base, "funcao": 10, "subfuncao": 301, "natureza_despesa": 33903401, "fonte_recursos": 1600, "valor": 50.0},
        {**base, "funcao": 10, "subfuncao": 301, "natureza_despesa": 33903001, "fonte_recursos": 1500, "valor": 30.0},
        {**base, "funcao": 1, "subfuncao": 31, "natureza_despesa": 31901101, "fonte_recursos": 2500,
         "poder_orgao": 20231, "valor": 20.0},
    ])


class MscTest(unittest.TestCase):
    def test_nomes(self):
        m = preparar(linhas())
        self.assertEqual(m["area"].tolist(), ["Educação", "Saúde", "Saúde", "Legislativa"])
        self.assertEqual(m["subarea"].tolist()[:2], ["Ensino Fundamental", "Atenção Básica"])
        self.assertEqual(m["item"].tolist()[:3], ["Salários do funcionalismo", "Terceirização de mão de obra",
                                                  "Material de consumo"])
        self.assertEqual(m["orgao"].tolist()[-1], "Câmara Municipal")

    def test_folha_inclui_terceirizacao_e_exclui_material(self):
        f = folha(preparar(linhas()))
        self.assertEqual(f["valor"].sum(), 170.0)
        self.assertNotIn("Material de consumo", set(f["item"]))

    def test_fontes(self):
        self.assertEqual(fonte_grupo(1500), "Recursos próprios (livres)")
        self.assertEqual(fonte_grupo("1540"), "Fundeb")
        self.assertEqual(fonte_grupo(1600), "Saúde: repasses do SUS")
        self.assertEqual(fonte_grupo(2500), "Recursos próprios (livres) · saldo de anos anteriores")
        self.assertEqual(fonte_grupo(None), "Outras fontes")


if __name__ == "__main__":
    unittest.main()
