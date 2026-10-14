"""Coleta DCA (Anexo I-C: receitas, inclui IPTU/ISS/ITBI; Anexo I-D: despesa por elemento) e RGF (Anexo 01:
despesa com pessoal) do SICONFI."""
import time
from datetime import date
from pathlib import Path
import pandas as pd
import requests

ID_ENTE = 5208400
BASE = "https://apidatalake.tesouro.gov.br/ords/siconfi/tt"
DADOS = Path(__file__).resolve().parent.parent / "dados"


def get(endpoint, params):
    for tentativa in range(3):
        try:
            r = requests.get(f"{BASE}/{endpoint}", params=params, timeout=90)
            r.raise_for_status()
            return r.json().get("items", [])
        except Exception as e:  # noqa: BLE001
            print(f"Falha {endpoint} {params} ({tentativa + 1}/3): {e}")
            time.sleep(3)
    return []


def dca_despesas():
    """DCA Anexo I-D: despesa anual por natureza até o elemento (material de consumo, obras, serviços...)."""
    linhas = []
    for ano in range(2020, date.today().year):
        itens = get("dca", {"an_exercicio": ano, "no_anexo": "DCA-Anexo I-D", "id_ente": ID_ENTE})
        print(f"DCA I-D {ano}: {len(itens)}")
        linhas += itens
        time.sleep(1)
    if linhas:
        pd.DataFrame(linhas).to_csv(DADOS / "siconfi_dca_despesas.csv", index=False)


def main():
    DADOS.mkdir(exist_ok=True)
    dca_despesas()
    dca = []
    for ano in range(2020, date.today().year):
        itens = get("dca", {"an_exercicio": ano, "no_anexo": "DCA-Anexo I-C", "id_ente": ID_ENTE})
        print(f"DCA {ano}: {len(itens)}")
        dca += itens
        time.sleep(1)
    if dca:
        pd.DataFrame(dca).to_csv(DADOS / "siconfi_dca_receitas.csv", index=False)
    rgf = []
    for ano in range(2020, date.today().year + 1):
        for p in (1, 2, 3):
            itens = get("rgf", {"an_exercicio": ano, "in_periodicidade": "Q", "nr_periodo": p,
                                "co_tipo_demonstrativo": "RGF", "no_anexo": "RGF-Anexo 01",
                                "co_esfera": "M", "co_poder": "E", "id_ente": ID_ENTE})
            print(f"RGF {ano}/{p}: {len(itens)}")
            rgf += itens
            time.sleep(1)
    if rgf:
        pd.DataFrame(rgf).to_csv(DADOS / "siconfi_rgf_pessoal.csv", index=False)


if __name__ == "__main__":
    main()
