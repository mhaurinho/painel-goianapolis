"""Coleta contratações publicadas no PNCP pelo município de Goianápolis (IBGE 5208400)."""
import time
from datetime import date
from pathlib import Path
import pandas as pd
import requests

from municipio import CNPJ, IBGE  # noqa: F401

URL = "https://pncp.gov.br/api/consulta/v1/contratacoes/publicacao"
DADOS = Path(__file__).resolve().parent.parent / "dados"
MODALIDADES = range(1, 14)  # códigos de modalidade do PNCP


def get(url, params):
    """GET com novas tentativas (o PNCP responde 429 quando há muitas requisições)."""
    for tentativa in range(5):
        r = requests.get(url, params=params, timeout=90)
        if r.status_code == 429:
            time.sleep(10 * (tentativa + 1))
            continue
        return r
    r.raise_for_status()
    return r


def baixar_ano(ano: int) -> list:
    fim = min(date(ano, 12, 31), date.today())
    linhas = []
    for mod in MODALIDADES:
        pagina = 1
        while True:
            params = {"dataInicial": f"{ano}0101", "dataFinal": fim.strftime("%Y%m%d"),
                      "codigoModalidadeContratacao": mod, "codigoMunicipioIbge": IBGE,
                      "pagina": pagina, "tamanhoPagina": 50}
            try:
                r = get(URL, params)
                if r.status_code == 204:
                    break
                r.raise_for_status()
                js = r.json()
            except Exception as e:  # noqa: BLE001
                print(f"Falha {ano} mod {mod} pág {pagina}: {e}")
                break
            dados = js.get("data", [])
            for d in dados:
                linhas.append({
                    "numeroControlePNCP": d.get("numeroControlePNCP"),
                    "ano": d.get("anoCompra"),
                    "modalidadeId": d.get("modalidadeId"),
                    "modalidade": d.get("modalidadeNome"),
                    "unidadeOrgao": (d.get("unidadeOrgao") or {}).get("nomeUnidade"),
                    "objeto": d.get("objetoCompra"),
                    "valorEstimado": d.get("valorTotalEstimado"),
                    "valorHomologado": d.get("valorTotalHomologado"),
                    "situacao": d.get("situacaoCompraNome"),
                    "dataPublicacao": d.get("dataPublicacaoPncp"),
                    "orgao": (d.get("orgaoEntidade") or {}).get("razaoSocial"),
                })
            if pagina >= js.get("totalPaginas", 1):
                break
            pagina += 1
            time.sleep(0.5)
    print(f"{ano}: {len(linhas)} contratações")
    return linhas


URL_CONTRATOS = "https://pncp.gov.br/api/consulta/v1/contratos"


def baixar_contratos(ano: int) -> list:
    fim = min(date(ano, 12, 31), date.today())
    linhas, pagina = [], 1
    while True:
        params = {"dataInicial": f"{ano}0101", "dataFinal": fim.strftime("%Y%m%d"),
                  "cnpjOrgao": CNPJ, "pagina": pagina, "tamanhoPagina": 50}
        try:
            r = get(URL_CONTRATOS, params)
            if r.status_code == 204:
                break
            r.raise_for_status()
            js = r.json()
        except Exception as e:  # noqa: BLE001
            print(f"Falha contratos {ano} pág {pagina}: {e}")
            break
        for d in js.get("data", []):
            linhas.append({
                "numeroControlePncpCompra": d.get("numeroControlePncpCompra"),
                "ano": d.get("anoContrato"),
                "fornecedor": d.get("nomeRazaoSocialFornecedor"),
                "niFornecedor": d.get("niFornecedor"),
                "objeto": d.get("objetoContrato"),
                "valorGlobal": d.get("valorGlobal"),
                "dataAssinatura": d.get("dataAssinatura"),
                "unidadeOrgao": (d.get("unidadeOrgao") or {}).get("nomeUnidade"),
            })
        if pagina >= js.get("totalPaginas", 1):
            break
        pagina += 1
        time.sleep(0.5)
    print(f"contratos {ano}: {len(linhas)}")
    return linhas


def main():
    DADOS.mkdir(exist_ok=True)
    contratos = []
    for ano in range(2023, date.today().year + 1):
        contratos += baixar_contratos(ano)
    if contratos:
        pd.DataFrame(contratos).to_csv(DADOS / "pncp_contratos.csv", index=False)
        print(f"Salvo pncp_contratos.csv: {len(contratos)} linhas")
    linhas = []
    for ano in range(2023, date.today().year + 1):
        linhas += baixar_ano(ano)
    if linhas:
        pd.DataFrame(linhas).to_csv(DADOS / "pncp_contratacoes.csv", index=False)
        print(f"Salvo pncp_contratacoes.csv: {len(linhas)} linhas")


if __name__ == "__main__":
    main()
