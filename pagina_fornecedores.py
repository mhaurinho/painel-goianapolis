"""Página Fornecedores: ranking e concentração dos contratos publicados no PNCP."""
import pandas as pd
import plotly.express as px
import streamlit as st

from analises import concentracao_fornecedores, hhi
from ui import brl, brl_curto, cabecalho, faltando, grafico, kpis, ler, num, pct

HHI_ELEVADO = 2500  # referência usual de mercado concentrado (escala 0–10.000)
PARTICIPACAO_ELEVADA = 40.0  # % de um único fornecedor


def pagina(ANO: int):
    cabecalho("Fornecedores",
              "Ranking dos fornecedores pelos **contratos** publicados no PNCP, com indicadores de concentração.",
              "PNCP: contratos (fornecedor, valor global) ligados às contratações (modalidade).")
    k, c = ler("pncp_contratos.csv"), ler("pncp_contratacoes.csv")
    if k is None:
        return faltando("pncp_contratos.csv", "coleta/pncp.py")
    k = k.copy()
    k["valorGlobal"] = pd.to_numeric(k["valorGlobal"], errors="coerce").fillna(0)
    if c is not None:
        mod = c.drop_duplicates("numeroControlePNCP").set_index("numeroControlePNCP")["modalidade"]
        k["modalidade"] = k["numeroControlePncpCompra"].map(mod).fillna("Não identificada")
    else:
        k["modalidade"] = "Não identificada"

    c1, c2 = st.columns([1, 2])
    with c1:
        todos = st.toggle("Todos os anos", value=False, help=f"Desligado: só contratos de {ANO}.")
    with c2:
        mods = st.multiselect("Modalidade", sorted(k["modalidade"].unique()))
    f = k if todos else k[k["ano"] == ANO]
    if mods:
        f = f[f["modalidade"].isin(mods)]
    if f.empty:
        return st.info("Nenhum contrato no PNCP para o filtro escolhido (a cobertura começa em 2023).")

    r = concentracao_fornecedores(f)
    r["posicao"] = range(1, len(r) + 1)
    indice = hhi(r["participacao"])
    top5 = r.head(5)["participacao"].sum()
    maior = r.iloc[0]
    kpis([("Contratos", num(len(f))), ("Valor total", brl_curto(f["valorGlobal"].sum()), brl(f["valorGlobal"].sum())),
          ("Fornecedores", num(len(r))), ("Top 5", pct(top5)),
          ("HHI", num(indice), "Índice Herfindahl-Hirschman: soma dos quadrados das participações (%). "
                               "0 a 10.000; acima de 2.500 costuma indicar mercado concentrado.")])
    if indice > HHI_ELEVADO or maior["participacao"] > PARTICIPACAO_ELEVADA:
        st.warning(f"**Concentração elevada: ponto de atenção.** HHI {num(indice)}; maior fornecedor "
                   f"({maior['fornecedor']}) com {pct(maior['participacao'])} do valor. Concentração, sozinha, "
                   "**não é irregularidade**: em município pequeno pode haver poucos fornecedores, contratos únicos "
                   "de grande valor (obras) ou fornecedores exclusivos.")
    else:
        st.success(f"HHI {num(indice)}: concentração abaixo da referência de {num(HHI_ELEVADO)}.")

    grafico(px.bar(r.head(15).sort_values("valor"), x="valor", y="fornecedor", orientation="h",
                   hover_data={"contratos": True, "participacao": ":.1f"},
                   title="15 maiores fornecedores por valor global", labels={"valor": "R$", "fornecedor": ""}), "x")
    acum = r.assign(acumulado=r["participacao"].cumsum())
    fig = px.line(acum.head(30), x="posicao", y="acumulado", markers=True, title="Participação acumulada (curva de concentração)",
                  labels={"posicao": "Nº de fornecedores (do maior para o menor)", "acumulado": "% do valor"})
    fig.update_yaxes(ticksuffix="%", range=[0, 101])
    grafico(fig, None)
    st.dataframe(r[["posicao", "fornecedor", "contratos", "valor", "participacao"]], width="stretch", hide_index=True,
                 column_config={"posicao": st.column_config.NumberColumn("#"),
                                "valor": st.column_config.NumberColumn("Valor global (R$)", format="localized"),
                                "participacao": st.column_config.NumberColumn("Participação (%)", format="%.1f")})
    st.caption("Limitações: valor global é o valor do contrato na assinatura (pode incluir vários anos); contratos de "
               "valor muito baixo (por exemplo, tarifas bancárias) aumentam a contagem sem pesar no valor; o PNCP só "
               "tem cobertura razoável a partir de 2023.")
