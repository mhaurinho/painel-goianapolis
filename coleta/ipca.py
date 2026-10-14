"""Coleta o IPCA mensal (série 433 do SGS / Banco Central) para corrigir valores pela inflação."""
import time
from datetime import date
from pathlib import Path

import pandas as pd
import requests

URL = "https://api.bcb.gov.br/dados/serie/bcdata.sgs.433/dados"
DADOS = Path(__file__).resolve().parent.parent / "dados"


def main():
    DADOS.mkdir(exist_ok=True)
    params = {"formato": "json", "dataInicial": "01/01/2019", "dataFinal": date.today().strftime("%d/%m/%Y")}
    for tentativa in range(1, 6):  # a API do SGS oscila com 502 com frequência
        r = requests.get(URL, params=params, timeout=60, headers={"User-Agent": "painel-goianapolis/1.0"})
        if r.ok:
            break
        print(f"Tentativa {tentativa}: HTTP {r.status_code}")
        time.sleep(3 * tentativa)
    r.raise_for_status()
    df = pd.DataFrame(r.json())
    df["data"] = pd.to_datetime(df["data"], format="%d/%m/%Y").dt.strftime("%Y-%m-%d")
    df["ipca_mensal"] = pd.to_numeric(df["valor"])
    df[["data", "ipca_mensal"]].to_csv(DADOS / "ipca.csv", index=False)
    print(f"Salvo ipca.csv: {len(df)} meses, até {df['data'].max()}")


if __name__ == "__main__":
    main()
