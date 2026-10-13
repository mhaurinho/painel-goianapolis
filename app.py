"""Goianápolis em Números: painel público de dados municipais (Streamlit + Plotly)."""
from pathlib import Path
import pandas as pd
import plotly.express as px
import streamlit as st

DADOS = Path(__file__).resolve().parent / "dados"
POPULACAO = 13967  # Censo 2022 (IBGE)

st.set_page_config(page_title="Goianápolis em Números", page_icon="📊", layout="wide")


@st.cache_data
def ler(nome: str):
    caminho = DADOS / nome
    if not caminho.exists():
        return None
    return pd.read_csv(caminho)


def faltando(nome: str, script: str):
    st.warning(f"Arquivo `dados/{nome}` não encontrado. Rode `python {script}` para coletar os dados.")


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
    col = d["coluna"].astype(str)
    d = d[col.str.contains("LIQUIDADAS ATÉ O BIMESTRE", case=False, na=False)]
    d = d[d["conta"].isin(sum(AREAS.values(), []))]
    d = d.groupby(["exercicio", "conta"], as_index=False)["valor"].max()
    inv = {c: a for a, cs in AREAS.items() for c in cs}
    d["area"] = d["conta"].map(inv)
    return d.groupby(["exercicio", "area"], as_index=False)["valor"].sum()


def pg_visao():
    st.title("Goianápolis em Números")
    st.caption("Município de Goianápolis (GO), IBGE 5208400. População: 13.967 (Censo 2022).")
    a1 = ler("siconfi_rreo_anexo01.csv")
    if a1 is None:
        return faltando("siconfi_rreo_anexo01.csv", "coleta/siconfi.py")
    d = rreo_final(a1)
    ano = int(d["exercicio"].max())
    da = d[d["exercicio"] == ano]
    def v(conta_sub, coluna_sub):
        x = da[da["conta"].astype(str).str.contains(conta_sub, case=False, regex=False)
               & da["coluna"].astype(str).str.contains(coluna_sub, case=False, regex=False)]
        return float(x["valor"].iloc[0]) if len(x) else None
    rec = v("RECEITAS (EXCETO INTRA", "Até o Bimestre")
    desp = v("DESPESAS (EXCETO INTRA", "LIQUIDADAS ATÉ O BIMESTRE")
    c1, c2, c3 = st.columns(3)
    c1.metric(f"Receita realizada {ano}", f"R$ {rec:,.0f}".replace(",", ".") if rec else "n/d")
    c2.metric(f"Despesa liquidada {ano}", f"R$ {desp:,.0f}".replace(",", ".") if desp else "n/d")
    c3.metric("Receita per capita", f"R$ {rec/POPULACAO:,.0f}".replace(",", ".") if rec else "n/d")
    st.info("Fonte: SICONFI/Tesouro Nacional, RREO (último bimestre disponível de cada ano).")


def pg_despesas():
    st.header("Para onde vai o dinheiro")
    a2 = ler("siconfi_rreo_anexo02.csv")
    if a2 is None:
        return faltando("siconfi_rreo_anexo02.csv", "coleta/siconfi.py")
    d = despesa_por_funcao(a2)
    if d.empty:
        return st.warning("Não foi possível identificar a despesa liquidada por função nos dados.")
    ano = st.selectbox("Ano", sorted(d["exercicio"].unique(), reverse=True))
    da = d[d["exercicio"] == ano].sort_values("valor")
    st.plotly_chart(px.bar(da, x="valor", y="area", orientation="h",
                           title=f"Despesa liquidada por área em {ano} (R$)"), width="stretch")
    st.plotly_chart(px.line(d, x="exercicio", y="valor", color="area", markers=True,
                            title="Evolução anual por área (R$)"), width="stretch")
    st.caption("Fonte: SICONFI, RREO Anexo 02 (despesa por função).")


def pg_receitas():
    st.header("De onde vem o dinheiro")
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
    st.plotly_chart(px.bar(x, x="exercicio", y="valor", color="conta", barmode="group",
                           title="Receitas realizadas por ano (R$)"), width="stretch")
    st.caption("IPTU e ISS detalhados dependem da DCA (anual), ainda não incluída. Fonte: SICONFI, RREO Anexo 01.")


def pg_compras():
    st.header("Compras públicas (PNCP)")
    df = ler("pncp_contratacoes.csv")
    if df is None:
        return faltando("pncp_contratacoes.csv", "coleta/pncp.py")
    anos = sorted(df["ano"].dropna().unique(), reverse=True)
    sel = st.multiselect("Ano", anos, default=anos[:1])
    f = df[df["ano"].isin(sel)] if sel else df
    st.metric("Contratações", len(f))
    g = f.groupby("modalidade", as_index=False)["valorHomologado"].sum()
    st.plotly_chart(px.bar(g, x="modalidade", y="valorHomologado", title="Valor homologado por modalidade (R$)"),
                    width="stretch")
    busca = st.text_input("Buscar no objeto")
    if busca:
        f = f[f["objeto"].astype(str).str.contains(busca, case=False)]
    st.dataframe(f, width="stretch")
    st.caption("Fonte: Portal Nacional de Contratações Públicas (pncp.gov.br).")


def pg_area(nome: str, extra: str = ""):
    st.header(nome)
    a2 = ler("siconfi_rreo_anexo02.csv")
    if a2 is None:
        return faltando("siconfi_rreo_anexo02.csv", "coleta/siconfi.py")
    d = despesa_por_funcao(a2)
    d = d[d["area"] == nome]
    if d.empty:
        return st.warning("Sem dados de despesa para esta área.")
    d = d.assign(per_capita=d["valor"] / POPULACAO)
    c1, c2 = st.columns(2)
    c1.plotly_chart(px.bar(d, x="exercicio", y="valor", title="Despesa liquidada (R$)"), width="stretch")
    c2.plotly_chart(px.bar(d, x="exercicio", y="per_capita", title="Per capita (R$/hab., pop. 2022)"),
                    width="stretch")
    if extra:
        st.info(extra)


def pg_demais():
    st.header("Demais áreas")
    area = st.selectbox("Área", ["Assistência social", "Segurança", "Meio ambiente", "Infraestrutura/urbanismo",
                                 "Cultura", "Esporte e lazer", "Mobilidade/transporte"])
    avisos = {"Segurança": "Indicadores de criminalidade são estaduais (SSP-GO); aqui só o gasto municipal.",
              "Mobilidade/transporte": "Não há dados municipais públicos de trânsito; só gasto.",
              "Cultura": "Sem indicadores municipais de resultado; só gasto.",
              "Esporte e lazer": "Sem indicadores municipais de resultado; só gasto.",
              "Meio ambiente": "Dados externos (MapBiomas/INPE) ainda não integrados."}
    pg_area(area, avisos.get(area, ""))


def pg_sobre():
    st.header("Sobre os dados")
    st.markdown("""
- **SICONFI / Tesouro Nacional**: RREO Anexos 01 e 02 (API, atualização bimestral).
- **PNCP**: contratações publicadas pela prefeitura (API).
- **IBGE**: população do Censo 2022.
- Saúde (DATASUS), educação (INEP) e assistência (MDS) ainda mostram só o gasto; os indicadores estão no roteiro.

Veja `dados/fontes.md` e `docs/esboco.md` no repositório.
""")


PAGINAS = {
    "Visão geral": pg_visao, "Despesas": pg_despesas, "Receitas": pg_receitas, "Compras": pg_compras,
    "Saúde": lambda: pg_area("Saúde", "Indicadores do DATASUS serão adicionados."),
    "Educação": lambda: pg_area("Educação", "Matrículas e IDEB (INEP) serão adicionados."),
    "Demais áreas": pg_demais, "Sobre os dados": pg_sobre,
}
escolha = st.sidebar.radio("Páginas", list(PAGINAS))
PAGINAS[escolha]()
