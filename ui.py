"""Componentes visuais e formatação brasileira compartilhados pelo painel."""
from html import escape
from pathlib import Path
import pandas as pd
import plotly.graph_objects as go
import plotly.io as pio
import streamlit as st

DADOS = Path(__file__).resolve().parent / "dados"

TINTA = "#0C2621"   # fundo escuro, textos fortes
VERDE = "#0A8F6E"   # cor principal: dinheiro executado, recurso próprio
LIMA = "#C8F169"    # destaque sobre fundo escuro
CORAL = "#E8553A"   # alerta
AMBAR = "#E9A21B"   # atenção, dado parcial
PALETA = [VERDE, "#2878A0", AMBAR, "#7564A4", "#3FB39B", CORAL, "#657D3D", "#6D8194", "#9A683E", "#1F6F5C", "#B98AC4"]

pio.templates["goianapolis"] = go.layout.Template(
    layout=go.Layout(
        font=dict(family="Inter, Segoe UI, sans-serif", size=13, color="#334B47"),
        colorway=PALETA,
        plot_bgcolor="white", paper_bgcolor="white",
        margin=dict(l=10, r=10, t=50, b=60),
        xaxis=dict(gridcolor="#EDF2EF", zeroline=False, showgrid=False),
        yaxis=dict(gridcolor="#EDF2EF", zeroline=False),
        legend=dict(orientation="h", yanchor="top", y=-0.14, x=0, title_text=""),  # abaixo, sem cobrir o título
        title=dict(font=dict(size=15, color=TINTA), x=0, xanchor="left"),
        hoverlabel=dict(bgcolor=TINTA, font_color="white", bordercolor=TINTA),
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


_secao = {"nome": "TRANSPARÊNCIA MUNICIPAL"}


def definir_secao(nome: str):
    """Grupo de navegação da página atual; aparece acima do título."""
    _secao["nome"] = nome.upper()


def cabecalho(titulo: str, subtitulo: str = "", fonte: str = ""):
    st.markdown(f'<div class="eyebrow">{escape(_secao["nome"])}</div><h1 class="titulo">{escape(titulo)}</h1>',
                unsafe_allow_html=True)
    if subtitulo:
        st.markdown(f'<div class="subtitulo">\n\n{subtitulo}\n\n</div>', unsafe_allow_html=True)
    if fonte:
        st.caption(f"Fonte: {fonte}")


def heroi(rotulo: str, numero: str, frase_html: str, selos=()):
    """Abertura de página: um número que importa e a frase que o explica.
    selos: lista de (tom, texto), tom em ok | alerta | atencao | info."""
    chips = "".join(f'<span class="chip chip-{escape(t)}">{escape(x)}</span>' for t, x in selos)
    st.markdown(f'<section class="hero"><div class="hero-label">{escape(rotulo)}</div>'
                f'<div class="hero-number">{escape(numero)}</div><p class="hero-text">{frase_html}</p>'
                f'<div class="chips">{chips}</div></section>', unsafe_allow_html=True)


def frases(itens):
    """Cartões 'frase-dado': número forte + leitura em linguagem comum. itens: (número, texto, tom)."""
    html = "".join(f'<div class="fact fact-{escape(tom)}"><div class="fact-n">{escape(n)}</div><p>{escape(t)}</p></div>'
                   for n, t, tom in itens)
    st.markdown(f'<div class="facts">{html}</div>', unsafe_allow_html=True)


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
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=JetBrains+Mono:wght@500;700&display=swap');
:root { --ink:#0C2621; --verde:#0A8F6E; --lima:#C8F169; --coral:#E8553A; --ambar:#E9A21B; --muted:#536B63;
  --line:#DCE6DF; --bg:#F3F5F1; --mono:'JetBrains Mono', ui-monospace, monospace; }
.block-container { max-width: 1320px; padding-top: 3.2rem; }
[data-testid="stSidebar"] a { color: var(--lima) !important; }
[data-testid="stSidebarNav"] [data-testid="stNavSectionHeader"] { color: var(--lima) !important; font-weight: 800;
  letter-spacing: 1.6px; font-size: 11px; text-transform: uppercase; }
[data-testid="stSidebarNav"] a[aria-current="page"] { background: rgba(200,241,105,.14); }
[data-testid="stSidebarNav"] a[aria-current="page"] span { color: var(--lima) !important; font-weight: 700; }
.eyebrow { color: var(--verde); font-size: 11px; font-weight: 800; letter-spacing: 2.2px; margin-bottom: 4px; }
h1.titulo { font-size: clamp(2rem, 4vw, 3rem); color: var(--ink); letter-spacing: -1.4px; font-weight: 800;
  line-height: 1.08; padding: 0 0 6px; }
.subtitulo p { color: var(--muted); font-size: 16px; line-height: 1.6; max-width: 820px; }
.hero { background: radial-gradient(120% 140% at 100% 0%, #16443A 0%, var(--ink) 55%); color: #fff; border-radius: 20px;
  padding: clamp(22px, 4vw, 42px); margin: 6px 0 16px; position: relative; overflow: hidden; }
.hero::after { content: ""; position: absolute; right: -60px; bottom: -60px; width: 240px; height: 240px;
  border-radius: 50%; border: 36px solid rgba(200,241,105,.08); }
.hero-label { color: var(--lima); font-size: 12px; font-weight: 800; letter-spacing: 2.4px; text-transform: uppercase; }
.hero-number { font-size: clamp(2.6rem, 7.5vw, 5.4rem); font-weight: 800; letter-spacing: -3px; line-height: 1; margin: 10px 0 14px; }
.hero-text { font-size: clamp(1rem, 1.6vw, 1.25rem); line-height: 1.5; color: #D8E6DF; max-width: 800px; margin: 0; }
.hero-text b { color: var(--lima); }
.chips { display: flex; flex-wrap: wrap; gap: 8px; margin-top: 20px; position: relative; z-index: 1; }
.chip { font-family: var(--mono); font-size: 12px; padding: 6px 11px; border-radius: 999px;
  border: 1px solid rgba(255,255,255,.22); color: #E6F0EB; }
.chip-ok { border-color: rgba(200,241,105,.6); color: var(--lima); }
.chip-alerta { border-color: rgba(232,85,58,.85); color: #FFB3A3; }
.chip-atencao { border-color: rgba(233,162,27,.85); color: #FFD88A; }
.facts { display: grid; grid-template-columns: repeat(auto-fit, minmax(210px, 1fr)); gap: 14px; margin: 0 0 18px; }
.fact { background: #fff; border: 1px solid var(--line); border-radius: 14px; padding: 18px 20px; border-left: 5px solid var(--verde); }
.fact-alerta { border-left-color: var(--coral); } .fact-atencao { border-left-color: var(--ambar); }
.fact-n { font-size: clamp(1.5rem, 2.4vw, 2.1rem); font-weight: 800; color: var(--ink); letter-spacing: -1px; line-height: 1.1; }
.fact p { color: var(--muted); margin: 8px 0 0; font-size: 14.5px; line-height: 1.5; }
div[data-testid="stMetric"] { background: #fff; border-radius: 14px; border-color: var(--line) !important; padding: 16px 18px; }
div[data-testid="stMetricLabel"] { color: var(--muted); }
div[data-testid="stMetricValue"] { font-size: clamp(1.1rem, 1.7vw, 1.6rem); font-weight: 800; color: var(--ink); letter-spacing: -.5px; }
div[data-testid="stMetricValue"] > div, div[data-testid="stMetricLabel"] p { white-space: normal !important;
  overflow: visible !important; text-overflow: clip !important; }  /* valores longos quebram linha em vez de "R$ 86..." */
[data-testid="stPlotlyChart"] { background: #fff; border: 1px solid var(--line); border-radius: 14px; padding: 8px; overflow: hidden; }
h2, h3 { color: var(--ink); letter-spacing: -.5px; font-weight: 800 !important; }
@media (max-width: 640px) {
  .block-container { padding: 1.4rem 1rem 2rem; }
  h1.titulo, .hero-number { letter-spacing: -1px; }
}
</style>
"""
