"""Transferências especiais (emendas parlamentares "PIX") para Goianápolis, via API do Transferegov."""
import time
from pathlib import Path

import pandas as pd
import requests

from municipio import CNPJ, IBGE  # noqa: F401

DADOS = Path(__file__).resolve().parent.parent / "dados"
URL = "https://api.transferegov.gestao.gov.br/transferenciasespeciais/plano_acao_especial"


def main():
    params = {"cnpj_beneficiario_plano_acao": f"eq.{CNPJ}",
              "select": "codigo_plano_acao,ano_plano_acao,situacao_plano_acao,nome_parlamentar_emenda_plano_acao,"
                        "valor_custeio_plano_acao,valor_investimento_plano_acao,"
                        "codigo_descricao_areas_politicas_publicas_plano_acao"}
    for tentativa in range(1, 4):
        r = requests.get(URL, params=params, timeout=90,
                         headers={"User-Agent": "painel-goianapolis/1.0", "Accept": "application/json"})
        if r.ok and r.headers.get("content-type", "").startswith("application/json"):
            break
        # APIs do gov.br às vezes devolvem página de bloqueio (HTML) para IPs de datacenter fora do Brasil
        print(f"Tentativa {tentativa}: HTTP {r.status_code}, {r.headers.get('content-type')}: {r.text[:120]!r}")
        time.sleep(10 * tentativa)
    else:
        raise SystemExit("Transferegov não devolveu JSON; a base anterior é mantida.")
    df = pd.DataFrame(r.json())
    df = df.rename(columns=lambda c: c.replace("_plano_acao", ""))
    df["valor_total"] = df["valor_custeio"].astype(float) + df["valor_investimento"].astype(float)
    DADOS.mkdir(exist_ok=True)
    df.to_csv(DADOS / "transferegov_especiais.csv", index=False)
    print(f"{len(df)} planos de ação, total R$ {df['valor_total'].sum():,.2f}")


if __name__ == "__main__":
    main()
