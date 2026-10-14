"""Página Com o que foi gasto: despesa por elemento (DCA) e exemplos de compras publicadas no PNCP."""
import pandas as pd
import plotly.express as px
import streamlit as st

from analises import contratacoes_validas
from gastos import categorizar, conferencia_dca_rreo, elementos
from pagina_pessoal import msc_preparada, rotulo_periodo
from ui import TINTA, VERDE, brl, brl_curto, cabecalho, faltando, frases, grafico, heroi, ler, pct, selos_conferencia

FORA_DA_COMPRA = {"Pessoal", "Juros da dívida", "Amortização da dívida"}
CORES_GRUPO = {"Pessoal": "#2C5C50", "Custeio e serviços": VERDE, "Investimentos": "#2878A0",
               "Amortização da dívida": "#8FA39A", "Juros da dívida": "#8FA39A", "Inversões financeiras": TINTA}


@st.cache_data
def _elementos():
    dca = ler("siconfi_dca_despesas.csv")
    return None if dca is None else elementos(dca)


@st.cache_data
def _conferencia():
    dca, a1 = ler("siconfi_dca_despesas.csv"), ler("siconfi_rreo_anexo01.csv")
    return None if dca is None or a1 is None else conferencia_dca_rreo(dca, a1)


def _variacao(e, ano):
    ant = e[e["exercicio"] == ano - 1].set_index("elemento")["valor"]
    return lambda nome, v: (v / ant[nome] - 1) * 100 if nome in ant and ant[nome] > 0 else None


def pagina(ANO: int):
    cabecalho("Com o que o dinheiro foi gasto",
              "Da área para a **natureza da despesa**: salários, material de consumo, serviços, obras, equipamentos. "
              "Vem do balanço anual que a prefeitura envia ao Tesouro, que detalha cada real liquidado por elemento.",
              "SICONFI: DCA Anexo I-D (balanço anual) e RREO; PNCP para os exemplos de compras.")
    e = _elementos()
    if e is None or e.empty:
        return faltando("siconfi_dca_despesas.csv", "coleta/siconfi_extra.py")
    anos = sorted(e["exercicio"].unique())
    ano = ANO if ANO in anos else max([a for a in anos if a <= ANO] or anos)
    if ano != ANO:
        st.info(f"O balanço de {ANO} só é publicado até 30 de abril do ano seguinte. Mostrando **{ano}**, o mais recente.")
    ea = e[e["exercicio"] == ano].sort_values("valor", ascending=False)
    total = ea["valor"].sum()
    compras = ea[~ea["grupo"].isin(FORA_DA_COMPRA)]
    var = _variacao(e, ano)

    conf = _conferencia()
    linha = conf[conf["exercicio"] == ano] if conf is not None else pd.DataFrame()
    selos = [("info", f"balanço anual de {ano}"), ("info", f"total liquidado {brl_curto(total)}")]
    if not linha.empty:
        ok = linha["status"].iloc[0] == "ok"
        selos.insert(0, ("ok" if ok else "atencao",
                         "✓ confere com o RREO" if ok else f"difere do RREO em {brl_curto(abs(linha['diferenca'].iloc[0]))}"))
    top3 = ", ".join(f"<b>{r.elemento.lower()} ({brl_curto(r.valor)})</b>" for r in compras.head(3).itertuples())
    heroi(f"Fora salários e dívida · {ano}", brl_curto(compras["valor"].sum()),
          f"foram para comprar bens, contratar serviços e fazer obras: {pct(compras['valor'].sum() / total * 100, 0)} "
          f"de tudo o que a prefeitura liquidou. Os maiores: {top3}.", selos)

    itens = []
    for r in compras.head(4).itertuples():
        v = var(r.elemento, r.valor)
        tendencia = f" {'+' if v >= 0 else ''}{pct(v, 0)} em relação a {ano - 1}." if v is not None else ""
        itens.append((brl_curto(r.valor), f"{r.elemento}{': ' + r.exemplo if r.exemplo else ''}.{tendencia}", "ok"))
    frases(itens)
    saltos = [(n, v) for n, x in zip(compras["elemento"], compras["valor"])
              if (v := var(n, x)) is not None and abs(v) >= 100 and x >= 0.01 * total]
    if saltos:
        st.caption("Variações muito grandes de um ano para outro ("
                   + ", ".join(f"{n.lower()} {'+' if v >= 0 else ''}{pct(v, 0)}" for n, v in saltos)
                   + ") costumam vir de **reclassificação contábil**: o mesmo tipo de gasto passa a ser lançado em outro "
                   "elemento. Compare com os itens do mesmo grupo antes de concluir que houve gasto novo.")

    st.subheader("Do total até o elemento de despesa")
    st.caption("Clique em um grupo para abrir os elementos; clique no topo para voltar.")
    arv = ea[ea["valor"] > 0].assign(raiz=f"Despesa liquidada {ano}")
    fig = px.treemap(arv, path=["raiz", "grupo", "elemento"], values="valor", color="grupo", custom_data=["exemplo"],
                     color_discrete_map={"(?)": "#F3F5F1", **CORES_GRUPO})
    fig.update_traces(texttemplate="<b>%{label}</b><br>%{value:,.0f}<br>%{percentRoot:.1%}",
                      hovertemplate="<b>%{label}</b><br>R$ %{value:,.2f} · %{percentRoot:.1%}<br>%{customdata[0]}<extra></extra>",
                      root_color="#F3F5F1", marker=dict(cornerradius=4))
    fig.update_layout(height=560, margin=dict(t=40, l=4, r=4, b=4), showlegend=False)
    grafico(fig, None)

    st.subheader("Como cada item evoluiu")
    principais = list(e[~e["grupo"].isin(FORA_DA_COMPRA) & (e["exercicio"] == ano)]
                      .sort_values("valor", ascending=False)["elemento"].head(6))
    escolhidos = st.multiselect("Itens no gráfico", sorted(e["elemento"].unique()), default=principais)
    ev = e[e["elemento"].isin(escolhidos) & (e["exercicio"] <= ano)]
    if not ev.empty:
        grafico(px.line(ev, x="exercicio", y="valor", color="elemento", markers=True,
                        title="Despesa liquidada por elemento (valores nominais)",
                        labels={"valor": "R$", "exercicio": "Ano", "elemento": ""}))

    st.subheader(f"Todos os itens de {ano}")
    tabela = pd.DataFrame({
        "Item": ea["elemento"], "Grupo": ea["grupo"], "O que entra": ea["exemplo"], "Liquidado (R$)": ea["valor"],
        "% do total": ea["valor"] / total,
        f"Variação sobre {ano - 1}": [None if (v := var(n, x)) is None else v / 100 for n, x in zip(ea["elemento"], ea["valor"])],
        "Nome oficial": ea["oficial"]})
    st.dataframe(tabela, width="stretch", hide_index=True, column_config={
        "Liquidado (R$)": st.column_config.NumberColumn(format="localized"),
        "% do total": st.column_config.ProgressColumn(format="percent", min_value=0, max_value=float(tabela["% do total"].max())),
        f"Variação sobre {ano - 1}": st.column_config.NumberColumn(format="percent")})

    if conf is not None and not conf.empty:
        st.subheader("O balanço anual confere com o relatório bimestral?")
        st.caption("A DCA (balanço anual) e o RREO do 6º bimestre trazem a despesa liquidada do mesmo ano. "
                   "Diferenças podem vir de retificações, de despesas intraorçamentárias ou de ajustes de "
                   "encerramento. Não indicam, sozinhas, irregularidade.")
        selos_conferencia([{"teste": f"{int(r.exercicio)}: DCA = RREO do 6º bimestre", "status": r.status,
                            "detalhe": f"DCA {brl(r.dca)} · RREO {brl(r.rreo)} · diferença {brl(r.diferenca)}"}
                           for r in conf.sort_values("exercicio", ascending=False).itertuples()])

    dentro_da_area(ANO)

    st.subheader(f"Exemplos de compras publicadas no PNCP em {ANO}")
    c = ler("pncp_contratacoes.csv")
    if c is None:
        return faltando("pncp_contratacoes.csv", "coleta/pncp.py")
    c = contratacoes_validas(c)
    c = c[c["ano"] == ANO].assign(categoria=lambda x: x["objeto"].map(categorizar))
    if c.empty:
        return st.info(f"Nenhuma compra de {ANO} publicada no PNCP.")
    base = compras["valor"].sum() if ano == ANO else None
    st.caption("Classificação automática pelo texto do objeto: é aproximada. O PNCP mostra o valor homologado "
               "na data da compra, que pode ser executado em mais de um ano"
               + (f"; em {ANO}, o homologado publicado equivale a {pct(c['valorHomologado'].sum() / base * 100, 0)} "
                  "da despesa com bens, serviços e obras." if base else "."))
    g = c.groupby("categoria", as_index=False).agg(compras=("objeto", "size"), valor=("valorHomologado", "sum"))
    g = g.sort_values("valor")
    fig = px.bar(g, x="valor", y="categoria", orientation="h", text=[f"{brl_curto(v)} · {n} compras" for v, n in
                                                                    zip(g["valor"], g["compras"])],
                 title=f"Valor homologado por tipo de compra ({ANO})", labels={"valor": "R$", "categoria": ""})
    fig.update_traces(textposition="outside", cliponaxis=False)
    fig.update_layout(height=max(300, 40 * len(g) + 120), margin=dict(r=140))
    grafico(fig, "x")
    tipo = st.selectbox("Ver as compras de um tipo", ["Todas"] + list(g.sort_values("valor", ascending=False)["categoria"]))
    lista = c if tipo == "Todas" else c[c["categoria"] == tipo]
    lista = lista.sort_values("valorHomologado", ascending=False)
    st.dataframe(lista[["objeto", "categoria", "modalidade", "valorHomologado", "dataPublicacao", "numeroControlePNCP"]]
                 .rename(columns={"objeto": "Objeto", "categoria": "Tipo", "modalidade": "Modalidade",
                                  "valorHomologado": "Homologado (R$)", "dataPublicacao": "Publicação",
                                  "numeroControlePNCP": "Controle PNCP"}),
                 width="stretch", hide_index=True,
                 column_config={"Homologado (R$)": st.column_config.NumberColumn(format="localized")})


def dentro_da_area(ANO: int):
    """Cruza área × item de despesa pela MSC: em Saúde, quanto foi pessoal, material, serviço..."""
    m = msc_preparada()
    if m is None or ANO not in set(m["exercicio"]):
        return
    ma = m[m["exercicio"] == ANO]
    periodo = rotulo_periodo(m, ANO)
    st.subheader(f"Dentro de uma área · {periodo}")
    st.caption("Cruzamento da área de governo com o item de despesa, pela matriz contábil (MSC) que a prefeitura "
               "envia ao Tesouro. O total confere com o RREO.")
    areas = list(ma.groupby("area")["valor"].sum().sort_values(ascending=False).index)
    area = st.selectbox("Área", areas, key="area_gastos")
    x = ma[ma["area"] == area]
    total = x["valor"].sum()
    por_item = x.groupby(["grupo", "item"], as_index=False)["valor"].sum().sort_values("valor")
    por_item = por_item[por_item["valor"] > 0]
    fig = px.bar(por_item, x="valor", y="item", orientation="h", color="grupo", color_discrete_map=CORES_GRUPO,
                 text=[f"{brl_curto(v)} · {pct(v / total * 100, 0)}" for v in por_item["valor"]],
                 title=f"{area}: com o que foi gasto ({brl_curto(total)})", labels={"valor": "R$", "item": "", "grupo": ""})
    fig.update_traces(textposition="outside", cliponaxis=False)
    fig.update_layout(height=max(320, 34 * len(por_item) + 140), margin=dict(r=130))
    fig.update_yaxes(categoryorder="total ascending")  # maior no topo, independentemente do grupo (cor)
    grafico(fig, "x")
    sub = x.groupby(["subarea", "item"], as_index=False)["valor"].sum()
    sub = sub[sub["valor"] > 0].pivot_table(index="item", columns="subarea", values="valor", aggfunc="sum", fill_value=0)
    if sub.shape[1] > 1:
        with st.expander(f"{area} por serviço (subfunção) e item"):
            st.dataframe(sub.reset_index().rename(columns={"item": "Item"}), width="stretch", hide_index=True,
                         column_config={c: st.column_config.NumberColumn(format="localized") for c in sub.columns})
