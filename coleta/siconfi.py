"""Coleta RREO (Anexos 01 e 02) do SICONFI para Goianápolis (IBGE 5208400)."""
import time
from pathlib import Path
import pandas as pd
import requests

ID_ENTE = 5208400
URL = "https://apidatalake.tesouro.gov.br/ords/siconfi/tt/rreo"
DADOS = Path(__file__).resolve().parent.parent / "dados"
ANOS = range(2020, 2026)


def baixar(anexo: str) -> pd.DataFrame:
    linhas = []
    for ano in ANOS:
        for periodo in range(1, 7):
            params = {"an_exercicio": ano, "nr_periodo": periodo,
                      "co_tipo_demonstrativo": "RREO", "no_anexo": anexo, "id_ente": ID_ENTE}
            try:
                r = requests.get(URL, params=params, timeout=60)
                r.raise_for_status()
                itens = r.json().get("items", [])
                linhas.extend(itens)
                print(f"{anexo} {ano}/{periodo}: {len(itens)} linhas")
            except Exception as e:  # noqa: BLE001
                print(f"Falha {anexo} {ano}/{periodo}: {e}")
            time.sleep(1)  # respeitar limite da API
    return pd.DataFrame(linhas)


def main():
    DADOS.mkdir(exist_ok=True)
    for anexo, nome in [("RREO-Anexo 01", "siconfi_rreo_anexo01.csv"),
                        ("RREO-Anexo 02", "siconfi_rreo_anexo02.csv")]:
        df = baixar(anexo)
        if not df.empty:
            df.to_csv(DADOS / nome, index=False)
            print(f"Salvo {nome}: {len(df)} linhas")


if __name__ == "__main__":
    main()
