"""Componentes visuais e formatação brasileira compartilhados pelo painel."""
from pathlib import Path
import pandas as pd
import plotly.graph_objects as go
import plotly.io as pio
import streamlit as st

DADOS = Path(__file__).resolve().parent / "dados"

PALETA = ["#1B6F4A", "#E0A526", "#2F80ED", "#C0504D", "#7A5BA6", "#3BA99C", "#8C8C8C", "#D97A2B", "#4C6A92"]

pio.templates["goianapolis"] = go.layout.Template(
    layout=go.Layout(
        font=dict(family="Inter, Segoe UI, sans-serif", size=13, color="#1F2933"),
        colorway=PALETA,
        plot_bgcolor="white", paper_bgcolor="white",
        margin=dict(l=10, r=10, t=50, b=10),
        xaxis=dict(gridcolor="#EEF1EF", zeroline=False),
        yaxis=dict(gridcolor="#EEF1EF", zeroline=False),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0),
        title=dict(font=dict(size=15)),
        separators=",.",  # vírgula decimal, ponto de milhar
    )
)
pio.templates.default = "plotly_white+goianapolis"


def brl(v, casas: int = 2) -> str:
    """Formata no padrão brasileiro: R$ 1.234,56."""
    if v is None or pd.isna(v):
        return "n/d"
    s = f"{float(v):,.{casas}f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return f"R$ {s}"


def brl_curto(v) -> str:
    """R$ 1,2 mi / R$ 350,0 mil, para cartões."""
    if v is None or pd.isna(v):
        return "n/d"
    v = float(v)
    for lim, suf in ((1e9, "bi"), (1e6, "mi"), (1e3, "mil")):
        if abs(v) >= lim:
            return f"R$ {v / lim:,.1f} {suf}".replace(",", "X").replace(".", ",").replace("X", ".")
    return brl(v)


def num(v, casas: int = 0) -> str:
    if v is None or pd.isna(v):
        return "n/d"
    return f"{float(v):,.{casas}f}".replace(",", "X").replace(".", ",").replace("X", ".")


def pct(v, casas: int = 1) -> str:
    return "n/d" if v is None or pd.isna(v) else f"{num(v, casas)}%"


def cabecalho(titulo: str, subtitulo: str = "", fonte: str = ""):
    st.title(titulo)
    if subtitulo:
        st.markdown(subtitulo)
    if fonte:
        st.caption(f"Fonte: {fonte}")
    st.divider()


def kpis(itens):
    """itens: lista de (rótulo, valor, ajuda opcional)."""
    cols = st.columns(len(itens))
    for col, item in zip(cols, itens):
        rotulo, valor, *ajuda = item
        col.metric(rotulo, valor, help=ajuda[0] if ajuda else None, border=True)


def grafico(fig, eixo_reais: str | None = "y"):
    if eixo_reais == "y":
        fig.update_yaxes(tickprefix="R$ ", tickformat=",.0f")
    elif eixo_reais == "x":
        fig.update_xaxes(tickprefix="R$ ", tickformat=",.0f")
    st.plotly_chart(fig, width="stretch", config={"displaylogo": False, "locale": "pt-BR"})


@st.cache_data
def ler(nome: str):
    caminho = DADOS / nome
    if not caminho.exists():
        return None
    return pd.read_csv(caminho)


def faltando(nome: str, script: str):
    st.warning(f"Arquivo `dados/{nome}` não encontrado. Rode `python {script}` para coletar os dados.")


CSS = """
<style>
div[data-testid="stMetric"] {background: #F7FAF8;}
div[data-testid="stMetricValue"] {font-size: 1.5rem;}
</style>
"""
