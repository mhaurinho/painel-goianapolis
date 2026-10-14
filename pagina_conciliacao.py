"""Página Conciliação: execução orçamentária (SICONFI) e comparação gasto × contratações (PNCP)."""
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import streamlit as st

from analises import area_pncp, contratacoes_validas
from ui import brl, brl_curto, cabecalho, faltando, grafico, kpis, ler, pct

AVISO = """
**Indícios para verificação, não conclusões.** A comparação entre gasto (SICONFI) e contratações (PNCP) é
**aproximada**: o SICONFI é agregado por função e ano (regime de liquidação); o PNCP registra o valor de cada
contratação no ano da compra (que pode cobrir vários anos ou nem ser executado); a área de cada contratação é
estimada pela unidade ou pelo objeto; e o PNCP só tem cobertura razoável a partir de 2023/2024. Um "gap" alto
pode ter explicações legítimas: contratos anteriores ao PNCP, atas de outros órgãos, diárias, convênios, tarifas
públicas, consórcios, etc.
"""

COLS = {"empenhada": "DESPESAS EMPENHADAS ATÉ O BIMESTRE", "liquidada": "DESPESAS LIQUIDADAS ATÉ O BIMESTRE",
        "paga": "DESPESAS PAGAS ATÉ O BIMESTRE"}
GRUPOS_NAO_LICITAVEIS = ["PESSOAL E ENCARGOS SOCIAIS", "JUROS E ENCARGOS DA DÍVIDA", "AMORTIZAÇÃO DA DÍVIDA"]
# Funções sem contratação típica (encargos, previdência, legislativo, que tem CNPJ e compras próprias)
FUNCOES_EXCLUIDAS = ["Encargos Especiais", "Previdência Social", "Legislativa"]


@st.cache_data
def execucao() -> pd.DataFrame | None:
    a1 = ler("siconfi_rreo_anexo01.csv")
    if a1 is None:
        return None
    ult = a1.groupby("exercicio")["periodo"].transform("max")
    d = a1[a1["periodo"] == ult]
    conta, col = d["conta"].astype(str), d["coluna"].astype(str)
    linhas = []
    for ano, da in d.groupby("exercicio"):
        c, k = da["conta"].astype(str), da["coluna"].astype(str)
        def pega(cmask, coltxt):
            x = da[cmask & k.str.startswith(coltxt)]["valor"]
            return float(x.iloc[0]) if len(x) else None
        rec = pega(c.str.startswith("RECEITAS (EXCETO INTRA"), "Até o Bimestre")
        tot = c.str.startswith("DESPESAS (EXCETO INTRA")
        row = {"exercicio": int(ano), "periodo": int(da["periodo"].max()), "receita": rec}
        for nome, txt in COLS.items():
            row[nome] = pega(tot, txt)
        nl = 0.0
        for g in GRUPOS_NAO_LICITAVEIS:
            v = pega(c == g, COLS["liquidada"])
            row[g] = v or 0.0
            nl += v or 0.0
        row["nao_licitavel"] = nl
        linhas.append(row)
    e = pd.DataFrame(linhas)
    e["resultado"] = e["receita"] - e["empenhada"]
    e["contratavel"] = e["liquidada"] - e["nao_licitavel"]
    return e.sort_values("exercicio")


def pagina(ANO: int, despesa_por_funcao):
    cabecalho("Conciliação: execução orçamentária e contratações",
              "Receita × despesa (empenhada, liquidada, paga), resultado orçamentário e comparação entre o gasto "
              "por área e as contratações publicadas no PNCP.",
              "SICONFI (RREO Anexos 01 e 02) e PNCP.")
    e = execucao()
    if e is None:
        return faltando("siconfi_rreo_anexo01.csv", "coleta/siconfi.py")
    e = e[e["exercicio"] <= ANO]

    st.subheader("1. Execução orçamentária por ano")
    ea = e[e["exercicio"] == ANO]
    if ea.empty:
        st.info(f"Sem RREO de {ANO}.")
    else:
        r = ea.iloc[0]
        if r["periodo"] < 6:
            st.caption(f"{ANO}: acumulado até o {int(r['periodo'])}º bimestre. Em ano incompleto o resultado tende a "
                       "parecer pior, porque contratos anuais são empenhados no início do ano (empenho global/estimativo).")
        kpis([("Receita realizada", brl_curto(r["receita"]), brl(r["receita"])),
              ("Despesa empenhada", brl_curto(r["empenhada"]), brl(r["empenhada"])),
              ("Despesa liquidada", brl_curto(r["liquidada"]), brl(r["liquidada"])),
              ("Despesa paga", brl_curto(r["paga"]), brl(r["paga"])),
              ("Resultado orçamentário", brl_curto(r["resultado"]),
               "Receita realizada − despesa empenhada. Positivo = superávit.")])
        fig = go.Figure(go.Waterfall(
            x=["Receita realizada", "Pessoal e encargos", "Dívida (juros + amortização)", "Demais despesas",
               "Resultado (s/ liquidação)"],
            measure=["absolute", "relative", "relative", "relative", "total"],
            y=[r["receita"], -r["PESSOAL E ENCARGOS SOCIAIS"],
               -(r["JUROS E ENCARGOS DA DÍVIDA"] + r["AMORTIZAÇÃO DA DÍVIDA"]),
               -(r["liquidada"] - r["nao_licitavel"]), 0],
            connector={"line": {"color": "#B0B7B3"}},
            increasing={"marker": {"color": "#0A8F6E"}}, decreasing={"marker": {"color": "#E8553A"}},
            totals={"marker": {"color": "#2878A0"}}))
        fig.update_layout(title=f"Da receita ao resultado em {ANO} (despesa liquidada)")
        grafico(fig)
    longo = e.melt(id_vars="exercicio", value_vars=["receita", "empenhada", "liquidada", "paga"],
                   var_name="tipo", value_name="valor")
    longo["tipo"] = longo["tipo"].map({"receita": "Receita realizada", "empenhada": "Empenhada",
                                       "liquidada": "Liquidada", "paga": "Paga"})
    grafico(px.bar(longo, x="exercicio", y="valor", color="tipo", barmode="group",
                   title="Receita × despesa por ano", labels={"valor": "R$", "exercicio": "Ano", "tipo": ""}))
    res = e[["exercicio", "resultado"]].copy()
    res["sinal"] = res["resultado"].map(lambda v: "Superávit" if v >= 0 else "Déficit")
    grafico(px.bar(res, x="exercicio", y="resultado", color="sinal", title="Resultado orçamentário (receita − empenhada)",
                   color_discrete_map={"Superávit": "#0A8F6E", "Déficit": "#E8553A"},
                   labels={"resultado": "R$", "exercicio": "Ano", "sinal": ""}))
    st.caption("**Por fonte/vínculo (saúde, educação/Fundeb):** os anexos do RREO com vinculações (Anexo 08, MDE, e "
               "Anexo 12, saúde) não estão disponíveis na API do SICONFI para Goianápolis (só Anexos 01, 02, 03, "
               "06, 07, 09 e 14). Esses dados ficam no SIOPE/SIOPS e nos índices do TCM-GO, ainda não integrados.")

    st.subheader("2. Gasto por área × contratações no PNCP (gap)")
    st.warning(AVISO)
    d = despesa_por_funcao()
    c = ler("pncp_contratacoes.csv")
    if d is None or c is None:
        return faltando("pncp_contratacoes.csv", "coleta/pncp.py")
    c = contratacoes_validas(c).copy()
    c["valorHomologado"] = pd.to_numeric(c["valorHomologado"], errors="coerce").fillna(0)
    c["area"] = [area_pncp(u, o) for u, o in zip(c.get("unidadeOrgao", [None] * len(c)), c["objeto"])]
    anos = sorted(a for a in set(c["ano"].dropna().astype(int)) & set(e["exercicio"]) if a >= 2023)
    if not anos:
        return st.info("Sem anos em comum entre PNCP (a partir de 2023) e SICONFI até o ano selecionado.")
    linhas = []
    for ano in anos:
        r = e[e["exercicio"] == ano].iloc[0]
        fator = r["contratavel"] / r["liquidada"] if r["liquidada"] else 0  # parcela não-pessoal/não-dívida
        da = d[(d["exercicio"] == ano) & (d["area"] != "Outras funções")]  # legislativo, previdência, encargos
        pa = c[c["ano"] == ano].groupby("area")["valorHomologado"].sum()
        for _, x in da.iterrows():
            linhas.append({"ano": ano, "area": x["area"], "liquidado": x["valor"],
                           "contratavel_estimado": x["valor"] * fator, "pncp_homologado": pa.get(x["area"], 0.0)})
        linhas.append({"ano": ano, "area": "Administração/não identificada", "liquidado": None,
                       "contratavel_estimado": None, "pncp_homologado": pa.get("Administração/não identificada", 0.0)})
    g = pd.DataFrame(linhas)
    g["gap"] = g["contratavel_estimado"] - g["pncp_homologado"]
    g["cobertura_pct"] = 100 * g["pncp_homologado"] / g["contratavel_estimado"]
    ver = st.selectbox("Ano da comparação", anos[::-1])
    ga = g[(g["ano"] == ver) & g["contratavel_estimado"].notna()].sort_values("gap", ascending=False)
    tot_c, tot_p = ga["contratavel_estimado"].sum(), g.loc[g["ano"] == ver, "pncp_homologado"].sum()
    kpis([("Gasto contratável estimado (áreas)", brl_curto(tot_c), brl(tot_c)),
          ("Homologado no PNCP (todas as áreas)", brl_curto(tot_p), brl(tot_p)),
          ("Cobertura PNCP / gasto contratável", pct(100 * tot_p / tot_c) if tot_c else "n/d")])
    fig = px.bar(ga.melt(id_vars="area", value_vars=["contratavel_estimado", "pncp_homologado"],
                         var_name="serie", value_name="valor").replace(
                     {"contratavel_estimado": "Gasto contratável estimado", "pncp_homologado": "Homologado no PNCP"}),
                 x="valor", y="area", color="serie", barmode="group", orientation="h",
                 title=f"Gasto contratável estimado × homologado no PNCP, {ver}",
                 labels={"valor": "R$", "area": "", "serie": ""})
    grafico(fig, "x")
    tabela = ga[["area", "liquidado", "contratavel_estimado", "pncp_homologado", "gap", "cobertura_pct"]]
    maxgap = max(float(tabela["gap"].abs().max() or 1), 1)

    def cor(v):
        if pd.isna(v):
            return ""
        a = min(abs(v) / maxgap, 1)
        return f"background-color: rgba(192, 80, 77, {0.12 + 0.6 * a:.2f})" if v > 0 else \
            f"background-color: rgba(27, 111, 74, {0.12 + 0.6 * a:.2f})"
    fmt = {c_: (lambda v: brl(v, 0)) for c_ in ("liquidado", "contratavel_estimado", "pncp_homologado", "gap")}
    fmt["cobertura_pct"] = lambda v: pct(v)
    st.dataframe(tabela.style.map(cor, subset=["gap"]).format(fmt, na_rep="n/d"), width="stretch", hide_index=True)
    st.caption("Gasto contratável estimado = liquidado da área × (1 − participação de pessoal e dívida no total "
               "liquidado do ano). É uma aproximação: a proporção real de pessoal varia muito entre as áreas. "
               "Vermelho = gasto sem contratação correspondente no PNCP (quanto mais forte, maior o gap); "
               "verde = PNCP acima do gasto estimado.")
    st.session_state["_gap_tabela"] = g
