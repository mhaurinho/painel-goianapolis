"""Coleta a MSC (Matriz de Saldos Contábeis) do SICONFI: despesa liquidada cruzando função, subfunção,
natureza (até o elemento), fonte de recursos e órgão. É o nível mais detalhado que o Tesouro publica.

Liquidado = liquidado a pagar (6.2.2.1.3.03) + pago (6.2.2.1.3.04) + inscrito em restos a pagar processados
(6.2.2.1.3.07), saldo final (credor - devedor). No meio do ano o que falta pagar está na 6.2.2.1.3.03; em dezembro
ele passa para a 6.2.2.1.3.07. Com essa regra o total confere no centavo com o RREO.
"""
import time
from datetime import date
from pathlib import Path

import pandas as pd
import requests

from municipio import IBGE

URL = "https://apidatalake.tesouro.gov.br/ords/siconfi/tt/msc_orcamentaria"
DADOS = Path(__file__).resolve().parent.parent / "dados"
CONTAS_LIQUIDADO = {"622130300": "liquidado a pagar", "622130400": "pago",
                    "622130700": "inscrito em restos a pagar processados"}


def baixar(ano: int, mes: int) -> list:
    params = {"id_ente": IBGE, "an_referencia": ano, "me_referencia": mes, "co_tipo_matriz": "MSCC",
              "classe_conta": 6, "id_tv": "ending_balance"}
    for tentativa in range(3):
        try:
            r = requests.get(URL, params=params, timeout=180)
            r.raise_for_status()
            return r.json().get("items", [])
        except Exception as e:  # noqa: BLE001
            print(f"Falha MSC {ano}/{mes} ({tentativa + 1}/3): {e}")
            time.sleep(5)
    return []


def main():
    DADOS.mkdir(exist_ok=True)
    hoje = date.today()
    linhas = []
    for ano in range(2021, hoje.year + 1):
        # ano fechado: dezembro; ano corrente: o mês mais recente já publicado
        meses = [12] if ano < hoje.year else range(hoje.month - 1, 0, -1)
        for mes in meses:
            itens = [i for i in baixar(ano, mes) if i.get("conta_contabil") in CONTAS_LIQUIDADO and i.get("natureza_despesa")]
            time.sleep(1)
            if itens:
                print(f"MSC {ano}/{mes:02d}: {len(itens)} linhas")
                for i in itens:
                    sinal = 1 if i["natureza_conta"] == "C" else -1
                    linhas.append({"exercicio": ano, "mes": mes, "funcao": i["funcao"], "subfuncao": i["subfuncao"],
                                   "natureza_despesa": i["natureza_despesa"], "fonte_recursos": i["fonte_recursos"],
                                   "poder_orgao": i["poder_orgao"], "valor": sinal * float(i["valor"])})
                break
    if linhas:
        df = pd.DataFrame(linhas)
        chaves = [c for c in df.columns if c != "valor"]
        df = df.groupby(chaves, as_index=False, dropna=False)["valor"].sum()
        df = df[df["valor"].abs() >= 0.005]
        df.to_csv(DADOS / "siconfi_msc_liquidado.csv", index=False)
        print(f"Salvo siconfi_msc_liquidado.csv: {len(df)} linhas")


if __name__ == "__main__":
    main()
