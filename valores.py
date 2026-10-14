"""Escala das séries históricas: valores nominais, corrigidos pela inflação (IPCA) ou por morador.

O modo é escolhido na barra lateral e vale para os gráficos de evolução de todas as páginas.
Só pandas (sem Streamlit), para poder ser testado.
"""
import pandas as pd

NOMINAL, IPCA, POR_MORADOR = "Nominais", "Corrigidos pela inflação (IPCA)", "Por morador"
MODOS = [NOMINAL, IPCA, POR_MORADOR]
MESES = ["", "jan", "fev", "mar", "abr", "mai", "jun", "jul", "ago", "set", "out", "nov", "dez"]
_estado = {"modo": NOMINAL, "fatores": {}, "referencia": "", "populacao": None}


def fatores_ipca(ipca: pd.DataFrame | None) -> tuple[dict, str]:
    """Fator que leva cada ano a preços do último mês com IPCA publicado. Usa o índice médio do ano,
    porque a despesa de um ano se espalha pelos doze meses."""
    if ipca is None or ipca.empty:
        return {}, ""
    i = ipca.assign(data=pd.to_datetime(ipca["data"])).sort_values("data")
    i["indice"] = (1 + i["ipca_mensal"] / 100).cumprod()
    atual = i["indice"].iloc[-1]
    media = i.groupby(i["data"].dt.year)["indice"].mean()
    ultimo = i["data"].iloc[-1]
    return {int(a): float(atual / v) for a, v in media.items()}, f"{MESES[ultimo.month]}/{ultimo.year}"


def configurar(modo: str, fatores: dict, referencia: str, populacao):
    """populacao: função ano -> habitantes."""
    _estado.update(modo=modo if modo in MODOS else NOMINAL, fatores=fatores, referencia=referencia,
                   populacao=populacao)


def modo() -> str:
    return _estado["modo"]


def unidade() -> str:
    if _estado["modo"] == IPCA and _estado["fatores"]:
        return f"R$ de {_estado['referencia']}"
    return "R$ por morador" if _estado["modo"] == POR_MORADOR else "R$ nominais"


def ajustar(df: pd.DataFrame, valor: str = "valor", ano: str = "exercicio") -> pd.DataFrame:
    """Devolve uma cópia com a coluna de valor na escala escolhida."""
    d = df.copy()
    anos = d[ano].astype(int)
    if _estado["modo"] == IPCA and _estado["fatores"]:
        d[valor] = d[valor] * anos.map(_estado["fatores"]).fillna(1.0)
    elif _estado["modo"] == POR_MORADOR and _estado["populacao"]:
        d[valor] = d[valor] / anos.map(_estado["populacao"])
    return d


def crescimento_real(v0: float, a0: int, v1: float, a1: int) -> float | None:
    """Variação de v0 (ano a0) para v1 (ano a1), descontada a inflação, em %."""
    f = _estado["fatores"]
    if a0 not in f or a1 not in f or not v0:
        return None
    return (v1 * f[a1]) / (v0 * f[a0]) * 100 - 100
