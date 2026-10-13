"""Transferências especiais (emendas parlamentares "PIX") para Goianápolis, via API do Transferegov."""
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
    df = pd.DataFrame(requests.get(URL, params=params, timeout=90).json())
    df = df.rename(columns=lambda c: c.replace("_plano_acao", ""))
    df["valor_total"] = df["valor_custeio"].astype(float) + df["valor_investimento"].astype(float)
    DADOS.mkdir(exist_ok=True)
    df.to_csv(DADOS / "transferegov_especiais.csv", index=False)
    print(f"{len(df)} planos de ação, total R$ {df['valor_total'].sum():,.2f}")


if __name__ == "__main__":
    main()
