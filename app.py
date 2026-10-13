"""Goianápolis em Números: painel público de dados municipais (Streamlit + Plotly)."""
import pandas as pd
import plotly.express as px
import streamlit as st

from ui import CSS, brl, brl_curto, cabecalho, faltando, grafico, kpis, ler, num

POPULACAO = 13967  # Censo 2022 (IBGE)

st.set_page_config(page_title="Goianápolis em Números", page_icon="📊", layout="wide")
st.markdown(CSS, unsafe_allow_html=True)


def rreo_final(df: pd.DataFrame) -> pd.DataFrame:
    """Mantém o último bimestre disponível de cada ano (dados acumulados no ano)."""
    ult = df.groupby("exercicio")["periodo"].transform("max")
    return df[df["periodo"] == ult]


AREAS = {
    "Saúde": ["Saúde"], "Educação": ["Educação"], "Assistência social": ["Assistência Social"],
    "Segurança": ["Segurança Pública"], "Meio ambiente": ["Gestão Ambiental"],
    "Infraestrutura/urbanismo": ["Urbanismo", "Saneamento"], "Cultura": ["Cultura"],
    "Esporte e lazer": ["Desporto e Lazer"], "Mobilidade/transporte": ["Transporte"],
}


def despesa_por_funcao(df: pd.DataFrame) -> pd.DataFrame:
    d = rreo_final(df)
    d = d[d["coluna"].astype(str).str.contains("LIQUIDADAS ATÉ O BIMESTRE", case=False, na=False)]
    d = d[d["conta"].isin(sum(AREAS.values(), []))]
    d = d.groupby(["exercicio", "conta"], as_index=False)["valor"].max()
    inv = {c: a for a, cs in AREAS.items() for c in cs}
    d["area"] = d["conta"].map(inv)
    return d.groupby(["exercicio", "area"], as_index=False)["valor"].sum()


def valor_rreo(da, conta_sub, coluna_sub):
    x = da[da["conta"].astype(str).str.contains(conta_sub, case=False, regex=False)
           & da["coluna"].astype(str).str.contains(coluna_sub, case=False, regex=False)]
    return float(x["valor"].iloc[0]) if len(x) else None


def pg_visao():
    cabecalho("Goianápolis em Números",
              "Painel público com dados abertos do município de Goianápolis (GO), código IBGE 5208400.",
              "SICONFI/Tesouro Nacional (RREO, último bimestre de cada ano) e IBGE (Censo 2022).")
    a1 = ler("siconfi_rreo_anexo01.csv")
    if a1 is None:
        return faltando("siconfi_rreo_anexo01.csv", "coleta/siconfi.py")
    d = rreo_final(a1)
    ano = int(d["exercicio"].max())
    da = d[d["exercicio"] == ano]
    rec = valor_rreo(da, "RECEITAS (EXCETO INTRA", "Até o Bimestre")
    desp = valor_rreo(da, "DESPESAS (EXCETO INTRA", "LIQUIDADAS ATÉ O BIMESTRE")
    kpis([
        ("População (Censo 2022)", num(POPULACAO)),
        (f"Receita realizada {ano}", brl_curto(rec), brl(rec)),
        (f"Despesa liquidada {ano}", brl_curto(desp), brl(desp)),
        ("Receita per capita", brl(rec / POPULACAO) if rec else "n/d"),
    ])


def pg_despesas():
    cabecalho("Para onde vai o dinheiro", "Despesa liquidada por área (função de governo).",
              "SICONFI, RREO Anexo 02.")
    a2 = ler("siconfi_rreo_anexo02.csv")
    if a2 is None:
        return faltando("siconfi_rreo_anexo02.csv", "coleta/siconfi.py")
    d = despesa_por_funcao(a2)
    if d.empty:
        return st.warning("Não foi possível identificar a despesa liquidada por função nos dados.")
    ano = st.selectbox("Ano", sorted(d["exercicio"].unique(), reverse=True))
    da = d[d["exercicio"] == ano].sort_values("valor")
    kpis([(f"Total nas áreas listadas ({ano})", brl_curto(da["valor"].sum()), brl(da["valor"].sum())),
          ("Maior área", da.iloc[-1]["area"] if len(da) else "n/d")])
    grafico(px.bar(da, x="valor", y="area", orientation="h", title=f"Despesa liquidada por área em {ano}",
                   labels={"valor": "R$", "area": ""}), "x")
    grafico(px.line(d, x="exercicio", y="valor", color="area", markers=True, title="Evolução anual por área",
                    labels={"valor": "R$", "exercicio": "Ano", "area": "Área"}))


def pg_receitas():
    cabecalho("De onde vem o dinheiro", "Receitas realizadas por categoria.", "SICONFI, RREO Anexo 01.")
    a1 = ler("siconfi_rreo_anexo01.csv")
    if a1 is None:
        return faltando("siconfi_rreo_anexo01.csv", "coleta/siconfi.py")
    d = rreo_final(a1)
    contas = ["RECEITAS CORRENTES", "Impostos", "Transferências Correntes", "OUTRAS RECEITAS CORRENTES",
              "RECEITAS DE CAPITAL"]
    x = d[d["conta"].isin(contas) & d["coluna"].astype(str).str.contains("Até o Bimestre", case=False)]
    x = x.groupby(["exercicio", "conta"], as_index=False)["valor"].max()
    if x.empty:
        return st.warning("Contas de receita não encontradas no arquivo.")
    grafico(px.bar(x, x="exercicio", y="valor", color="conta", barmode="group", title="Receitas realizadas por ano",
                   labels={"valor": "R$", "exercicio": "Ano", "conta": ""}))


def pg_compras():
    cabecalho("Compras públicas", "Contratações publicadas pela prefeitura no PNCP.",
              "Portal Nacional de Contratações Públicas (pncp.gov.br).")
    df = ler("pncp_contratacoes.csv")
    if df is None:
        return faltando("pncp_contratacoes.csv", "coleta/pncp.py")
    anos = sorted(df["ano"].dropna().unique(), reverse=True)
    sel = st.multiselect("Ano", anos, default=anos[:1])
    f = df[df["ano"].isin(sel)] if sel else df
    kpis([("Contratações", num(len(f))), ("Valor homologado", brl_curto(f["valorHomologado"].sum()),
                                          brl(f["valorHomologado"].sum()))])
    g = f.groupby("modalidade", as_index=False)["valorHomologado"].sum().sort_values("valorHomologado")
    grafico(px.bar(g, x="valorHomologado", y="modalidade", orientation="h", title="Valor homologado por modalidade",
                   labels={"valorHomologado": "R$", "modalidade": ""}), "x")
    busca = st.text_input("Buscar no objeto")
    if busca:
        f = f[f["objeto"].astype(str).str.contains(busca, case=False)]
    st.dataframe(f, width="stretch", hide_index=True,
                 column_config={"valorEstimado": st.column_config.NumberColumn("Estimado (R$)", format="localized"),
                                "valorHomologado": st.column_config.NumberColumn("Homologado (R$)", format="localized")})


def pg_area(nome: str, extra: str = ""):
    a2 = ler("siconfi_rreo_anexo02.csv")
    if a2 is None:
        return faltando("siconfi_rreo_anexo02.csv", "coleta/siconfi.py")
    d = despesa_por_funcao(a2)
    d = d[d["area"] == nome]
    if d.empty:
        return st.warning("Sem dados de despesa para esta área.")
    d = d.assign(per_capita=d["valor"] / POPULACAO)
    ult = d.iloc[-1]
    kpis([(f"Despesa liquidada {int(ult['exercicio'])}", brl_curto(ult["valor"]), brl(ult["valor"])),
          ("Per capita", brl(ult["per_capita"]))])
    c1, c2 = st.columns(2)
    with c1:
        grafico(px.bar(d, x="exercicio", y="valor", title="Despesa liquidada", labels={"valor": "R$", "exercicio": "Ano"}))
    with c2:
        grafico(px.bar(d, x="exercicio", y="per_capita", title="Per capita (pop. Censo 2022)",
                       labels={"per_capita": "R$/hab.", "exercicio": "Ano"}))
    if extra:
        st.info(extra)


def pg_saude():
    cabecalho("Saúde", "Gasto municipal com saúde.", "SICONFI, RREO Anexo 02.")
    pg_area("Saúde", "Indicadores do DATASUS ainda não integrados.")


def pg_educacao():
    cabecalho("Educação", "Gasto municipal com educação.", "SICONFI, RREO Anexo 02.")
    pg_area("Educação", "Matrículas e IDEB (INEP) ainda não integrados.")


def pg_demais():
    cabecalho("Demais áreas", "Gasto por área de política pública.", "SICONFI, RREO Anexo 02.")
    area = st.selectbox("Área", ["Assistência social", "Segurança", "Meio ambiente", "Infraestrutura/urbanismo",
                                 "Cultura", "Esporte e lazer", "Mobilidade/transporte"])
    avisos = {"Segurança": "Indicadores de criminalidade são estaduais (SSP-GO); aqui só o gasto municipal.",
              "Mobilidade/transporte": "Não há dados municipais públicos de trânsito; só gasto.",
              "Cultura": "Sem indicadores municipais de resultado; só gasto.",
              "Esporte e lazer": "Sem indicadores municipais de resultado; só gasto.",
              "Meio ambiente": "Dados externos (MapBiomas/INPE) ainda não integrados."}
    pg_area(area, avisos.get(area, ""))


def pg_sobre():
    cabecalho("Sobre os dados")
    st.markdown("""
- **SICONFI / Tesouro Nacional**: RREO Anexos 01 e 02 (API, atualização bimestral).
- **PNCP**: contratações publicadas pela prefeitura (API).
- **IBGE**: população do Censo 2022.

Veja `dados/fontes.md` e `docs/esboco.md` no repositório.
""")


PAGINAS = {"Visão geral": pg_visao, "Despesas": pg_despesas, "Receitas": pg_receitas, "Compras": pg_compras,
           "Saúde": pg_saude, "Educação": pg_educacao, "Demais áreas": pg_demais, "Sobre os dados": pg_sobre}
escolha = st.sidebar.radio("Páginas", list(PAGINAS))
PAGINAS[escolha]()
