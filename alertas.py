"""Alertas automáticos: gasto do período atual comparado com a média do mesmo período em anos anteriores.

São sinais para acompanhamento, não irregularidades. Os valores são nominais (sem correção pela inflação).
"""
import pandas as pd

from analises import contratacoes_validas, normalizar_unidade
from dados_siconfi import funcoes_por_periodo, total_por_periodo

LIMIAR_AMARELO = 20.0  # % acima da média histórica
LIMIAR_VERMELHO = 50.0
ANOS_HISTORICO = 3
# PNCP: um ano só entra na média se tiver ao menos esta quantidade de contratações válidas publicadas no mesmo
# intervalo (a adoção do PNCP pelo município foi irregular: 2 publicações em 2024, por exemplo).
MIN_PUBLICACOES_ANO = 10


def nivel(var_pct) -> str:
    if pd.isna(var_pct):
        return "sem histórico"
    if var_pct > LIMIAR_VERMELHO:
        return "🔴 vermelho"
    if var_pct > LIMIAR_AMARELO:
        return "🟡 amarelo"
    return "🟢 normal"


def alertas_siconfi(a2: pd.DataFrame, ano: int) -> tuple[pd.DataFrame, int | None]:
    """Liquidado acumulado até o último bimestre de `ano`, por área, contra a média do mesmo bimestre nos anos anteriores."""
    f = funcoes_por_periodo(a2)
    if f.empty or ano not in set(f["exercicio"]):
        return pd.DataFrame(), None
    p = int(f.loc[f["exercicio"] == ano, "periodo"].max())
    por_area = f[f["periodo"] == p].groupby(["exercicio", "area"], as_index=False)["valor"].sum()
    tot = total_por_periodo(a2)
    tot = tot[tot["periodo"] == p].assign(area="TOTAL (referência)")[["exercicio", "area", "valor"]]
    base = pd.concat([por_area, tot], ignore_index=True)
    anteriores = [a for a in sorted(base["exercicio"].unique()) if ano - ANOS_HISTORICO <= a < ano]
    atual = base[base["exercicio"] == ano].set_index("area")["valor"]
    hist = base[base["exercicio"].isin(anteriores)].groupby("area")["valor"].mean()
    out = pd.DataFrame({"atual": atual, "media_historica": hist}).dropna(subset=["atual"])
    out["variacao_pct"] = 100 * (out["atual"] / out["media_historica"] - 1)
    out["nivel"] = out["variacao_pct"].map(nivel)
    # crescimento acima do orçamento total: compara a variação da área com a do TOTAL (anula inflação e expansão geral)
    var_total = out.loc["TOTAL (referência)", "variacao_pct"] if "TOTAL (referência)" in out.index else float("nan")
    out["acima_do_total_pp"] = 100 * ((1 + out["variacao_pct"] / 100) / (1 + var_total / 100) - 1)
    out["comparacao"] = f"{p}º bimestre de {ano} × média do {p}º bimestre de " + ", ".join(map(str, anteriores))
    return out.reset_index().rename(columns={"index": "area"}).sort_values("variacao_pct", ascending=False), p


def alertas_pncp(c: pd.DataFrame, ano: int) -> tuple[pd.DataFrame, str | None]:
    """Homologado por unidade no ano até a data da última publicação, contra o mesmo intervalo dos anos anteriores."""
    if c is None or "unidadeOrgao" not in c:
        return pd.DataFrame(), None
    c = contratacoes_validas(c).copy()
    c["unidadeOrgao"] = c["unidadeOrgao"].map(normalizar_unidade)
    c["pub"] = pd.to_datetime(c["dataPublicacao"], errors="coerce")
    c["valorHomologado"] = pd.to_numeric(c["valorHomologado"], errors="coerce").fillna(0)
    c = c.dropna(subset=["pub"])
    c["ano_pub"] = c["pub"].dt.year
    atual = c[c["ano_pub"] == ano]
    if atual.empty:
        return pd.DataFrame(), None
    corte = atual["pub"].max()
    doy = corte.dayofyear
    janela = c[c["pub"].dt.dayofyear <= doy]
    g = janela.groupby(["ano_pub", "unidadeOrgao"], as_index=False)["valorHomologado"].sum()
    n_pub = janela.groupby("ano_pub").size()
    anteriores = [a for a in sorted(g["ano_pub"].unique()) if ano - ANOS_HISTORICO <= a < ano
                  and n_pub.get(a, 0) >= MIN_PUBLICACOES_ANO]
    excluidos = [a for a in range(ano - ANOS_HISTORICO, ano) if a not in anteriores and n_pub.get(a, 0) > 0]
    at = g[g["ano_pub"] == ano].set_index("unidadeOrgao")["valorHomologado"]
    # anos sem nenhuma publicação da unidade contam como zero na média
    piv = g[g["ano_pub"].isin(anteriores)].pivot(index="unidadeOrgao", columns="ano_pub", values="valorHomologado")
    piv = piv.reindex(columns=anteriores).fillna(0)
    hist = piv.mean(axis=1) if anteriores else pd.Series(dtype=float)
    out = pd.DataFrame({"atual": at, "media_historica": hist}).fillna({"atual": 0})
    out = out[out["atual"] > 0]
    out["variacao_pct"] = 100 * (out["atual"] / out["media_historica"].where(out["media_historica"] > 0) - 1)
    out["nivel"] = out["variacao_pct"].map(nivel)
    desc = f"01/01 a {corte:%d/%m} de {ano} × média do mesmo intervalo em " + (", ".join(map(str, anteriores)) or "nenhum ano")
    if excluidos:
        desc += (f" (fora da média por terem menos de {MIN_PUBLICACOES_ANO} publicações no intervalo: "
                 + ", ".join(f"{a} ({n_pub[a]})" for a in excluidos) + ")")
    return out.reset_index().rename(columns={"index": "unidadeOrgao"}).sort_values("variacao_pct", ascending=False), desc
