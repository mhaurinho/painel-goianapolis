"""Página Pessoal (LRF): limite da Lei de Responsabilidade Fiscal e onde está a folha (área, subárea, fonte)."""
import pandas as pd
import plotly.express as px
import streamlit as st

from msc import folha, preparar
from ui import (CORAL, brl, brl_curto, cabecalho, faltando, frases, grafico, heroi, ler, num, pct)

MESES = ["", "janeiro", "fevereiro", "março", "abril", "maio", "junho", "julho", "agosto", "setembro", "outubro",
         "novembro", "dezembro"]
# O que a LRF determina em cada faixa (arts. 22, 23 e 59 da LC 101/2000).
FAIXAS = [
    ("Limite máximo", "acima do limite máximo",
     "O excedente precisa ser eliminado nos dois quadrimestres seguintes; enquanto isso, o município não pode receber "
     "transferências voluntárias nem contratar operações de crédito (art. 23).", "alerta"),
    ("Limite prudencial", "acima do limite prudencial",
     "A lei proíbe reajustes não previstos em lei, criação de cargos, novas contratações (exceto reposição em "
     "educação, saúde e segurança) e horas extras (art. 22).", "alerta"),
    ("Limite de alerta", "acima do limite de alerta",
     "O Tribunal de Contas notifica o município para que acompanhe o gasto (art. 59).", "atencao"),
]


@st.cache_data
def msc_preparada() -> pd.DataFrame | None:
    m = ler("siconfi_msc_liquidado.csv")
    return None if m is None else preparar(m)


def rotulo_periodo(m: pd.DataFrame, ano: int) -> str:
    mes = int(m.loc[m["exercicio"] == ano, "mes"].max())
    return f"{ano}" if mes == 12 else f"{ano}, até {MESES[mes]}"


def pagina(ANO: int, p: pd.DataFrame | None, populacao: int):
    cabecalho("Despesa com pessoal (LRF)",
              "Quanto da receita vai para a folha, se o município está dentro da Lei de Responsabilidade Fiscal "
              "e **onde está a folha**: em que área, em que serviço e paga com que dinheiro.",
              "SICONFI: RGF Anexo 01 (limite da LRF, Poder Executivo) e MSC (folha por área, subárea e fonte).")
    if p is None:
        return faltando("siconfi_rgf_pessoal.csv", "coleta/siconfi_extra.py")
    pa = p[p["exercicio"] == ANO].set_index("indicador")["valor"]
    dtp = pa.get("Despesa com pessoal (% RCL)")
    if dtp is not None and pd.notna(dtp):
        q = int(p.loc[p["exercicio"] == ANO, "periodo"].max())
        faixa = next(((nome, txt, tom) for lim, nome, txt, tom in FAIXAS
                      if pa.get(lim) is not None and dtp > pa.get(lim)), None)
        selos = [("info", f"{q}º quadrimestre de {ANO} (12 meses)")]
        selos += [("alerta" if dtp > pa.get(lim, 999) else "info", f"{lim.lower()}: {pct(pa.get(lim))}")
                  for lim in ("Limite de alerta", "Limite prudencial", "Limite máximo") if pa.get(lim) is not None]
        if faixa:
            nome, txt, _ = faixa
            frase = f"da Receita Corrente Líquida foi para pessoal no Poder Executivo: <b>{nome}</b>. {txt}"
        else:
            frase = "da Receita Corrente Líquida foi para pessoal no Poder Executivo, <b>dentro dos limites da LRF</b>."
        heroi(f"Pessoal em % da receita · {ANO}", pct(dtp, 2), frase, selos)

    m = msc_preparada()
    if m is not None and ANO in set(m["exercicio"]):
        f = folha(m)
        fa = f[f["exercicio"] == ANO]
        total = fa["valor"].sum()
        periodo = rotulo_periodo(m, ANO)
        terc = fa.loc[fa["item"] == "Terceirização de mão de obra", "valor"].sum()
        vinculada = fa.loc[~fa["fonte"].str.startswith("Recursos próprios"), "valor"].sum()
        top = fa.groupby("area")["valor"].sum().sort_values(ascending=False)
        itens = [(brl_curto(total), f"de folha em {periodo}: salários, encargos e terceirização, incluindo a Câmara. "
                  f"São {brl(total / populacao, 0)} por morador.", "ok")]
        if len(top) >= 2:
            itens.append((pct(top.iloc[:2].sum() / total * 100, 0),
                          f"da folha está em {top.index[0]} e {top.index[1]}.", "ok"))
        if terc:
            itens.append((brl_curto(terc), f"em terceirização de mão de obra ({pct(terc / total * 100, 0)} da folha). "
                          "A LRF manda contar como gasto com pessoal.", "atencao"))
        itens.append((pct(vinculada / total * 100, 0), "da folha é paga com dinheiro carimbado (Fundeb, SUS e "
                      "outros repasses), que só pode ser usado naquela área.", "ok"))
        frases(itens)
        ant = f[(f["exercicio"] == ANO - 1) & (f["item"] == "Terceirização de mão de obra")]["valor"].sum()
        if ant > 0 and terc > 2 * ant:
            st.caption(f"A terceirização passou de {brl_curto(ant)} em {ANO - 1} para {brl_curto(terc)} em {periodo}. "
                       "Como a LRF conta a terceirização que substitui servidores como gasto com pessoal, essa mudança "
                       "pesa diretamente no percentual acima. Parte dela pode ser reclassificação de serviços que antes "
                       "eram lançados como \"serviços de empresas\".")

        st.subheader(f"Onde está a folha · {periodo}")
        st.caption("Clique em uma área para ver os serviços (subfunções); clique no topo para voltar.")
        arv = fa.groupby(["area", "subarea"], as_index=False)["valor"].sum()
        arv = arv[arv["valor"] > 0].assign(raiz="Folha")
        fig = px.treemap(arv, path=["raiz", "area", "subarea"], values="valor")
        fig.update_traces(texttemplate="<b>%{label}</b><br>%{value:,.0f}<br>%{percentRoot:.1%}",
                          hovertemplate="<b>%{label}</b><br>R$ %{value:,.2f} · %{percentRoot:.1%}<extra></extra>",
                          root_color="#F3F5F1", marker=dict(cornerradius=4))
        fig.update_layout(height=480, margin=dict(t=30, l=4, r=4, b=4), showlegend=False)
        grafico(fig, None)

        c1, c2 = st.columns(2)
        with c1:
            fo = fa.groupby("fonte", as_index=False)["valor"].sum().sort_values("valor")
            fig = px.bar(fo, x="valor", y="fonte", orientation="h", title="Com que dinheiro a folha é paga",
                         text=[brl_curto(v) for v in fo["valor"]], labels={"valor": "R$", "fonte": ""})
            fig.update_traces(textposition="outside", cliponaxis=False)
            fig.update_layout(margin=dict(r=90))
            fig.update_xaxes(visible=False)  # o valor já está no rótulo de cada barra
            grafico(fig, "x")
        with c2:
            it = fa.groupby("item", as_index=False)["valor"].sum().sort_values("valor")
            fig = px.bar(it, x="valor", y="item", orientation="h", title="Do que a folha é feita",
                         text=[brl_curto(v) for v in it["valor"]], labels={"valor": "R$", "item": ""},
                         color=it["item"].eq("Terceirização de mão de obra").map({True: "t", False: "f"}),
                         color_discrete_map={"t": CORAL, "f": "#2C5C50"})
            fig.update_traces(textposition="outside", cliponaxis=False)
            fig.update_layout(margin=dict(r=90), showlegend=False)
            fig.update_xaxes(visible=False)
            grafico(fig, "x")

        tab = fa.pivot_table(index="area", columns="item", values="valor", aggfunc="sum", fill_value=0)
        tab["Total"] = tab.sum(axis=1)
        tab = tab.sort_values("Total", ascending=False)
        tab["R$ por morador"] = (tab["Total"] / populacao).round(2)
        tab["% da folha"] = tab["Total"] / total
        cols = [c for c in ("Salários do funcionalismo", "Encargos patronais", "Terceirização de mão de obra") if c in tab]
        outros = [c for c in tab.columns if c not in cols + ["Total", "R$ por morador", "% da folha"]]
        tab["Outros de pessoal"] = tab[outros].sum(axis=1)
        tab = tab[cols + ["Outros de pessoal", "Total", "R$ por morador", "% da folha"]].reset_index()
        st.dataframe(tab.rename(columns={"area": "Área"}), width="stretch", hide_index=True, column_config={
            **{c: st.column_config.NumberColumn(format="localized") for c in cols + ["Outros de pessoal", "Total", "R$ por morador"]},
            "% da folha": st.column_config.ProgressColumn(format="percent", min_value=0, max_value=float(tab["% da folha"].max()))})

        ev = f.groupby(["exercicio", "area"], as_index=False)["valor"].sum()
        ev["periodo"] = ev["exercicio"].map(lambda a: rotulo_periodo(m, a))
        principais = list(top.index[:5])
        ev["area"] = ev["area"].where(ev["area"].isin(principais), "Demais áreas")
        ev = ev.groupby(["exercicio", "periodo", "area"], as_index=False)["valor"].sum()
        grafico(px.bar(ev[ev["exercicio"] <= ANO], x="periodo", y="valor", color="area",
                       title="Folha por área ao longo dos anos (valores nominais)",
                       labels={"valor": "R$", "periodo": "", "area": ""}))
        st.caption("A folha da MSC inclui a Câmara Municipal; o limite da LRF acima é só do Poder Executivo. "
                   "Fontes agrupadas pelo padrão do Tesouro: 'recursos próprios' são impostos e transferências "
                   "sem destino obrigatório.")
    elif m is not None:
        st.info(f"A matriz contábil (MSC) de {ANO} não está disponível; a abertura por área começa em "
                f"{int(m['exercicio'].min())}.")
    else:
        faltando("siconfi_msc_liquidado.csv", "coleta/siconfi_msc.py")

    st.subheader("Pessoal em % da receita ao longo dos anos")
    fig = px.line(p[p["exercicio"] <= ANO], x="exercicio", y="valor", color="indicador", markers=True,
                  labels={"valor": "% da RCL", "exercicio": "Ano", "indicador": ""})
    fig.update_yaxes(ticksuffix="%")
    grafico(fig, None)
    if dtp is not None and pd.notna(dtp):
        st.caption(f"Em {ANO}: {num(dtp, 2)}% da RCL. Cada ano mostra o último quadrimestre publicado.")
