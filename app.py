"""Goianápolis em Números: painel público de dados municipais (Streamlit + Plotly)."""
import pandas as pd
import plotly.express as px
import streamlit as st

from ui import CSS, brl, brl_curto, cabecalho, faltando, grafico, kpis, ler, num, pct

POP_CENSO = 13967  # Censo 2022 (IBGE)

st.set_page_config(page_title="Goianápolis em Números", page_icon="📊", layout="wide")
st.markdown(CSS, unsafe_allow_html=True)

AREAS = {
    "Saúde": ["Saúde"], "Educação": ["Educação"], "Assistência social": ["Assistência Social"],
    "Segurança": ["Segurança Pública"], "Meio ambiente": ["Gestão Ambiental"],
    "Infraestrutura/urbanismo": ["Urbanismo", "Saneamento"], "Cultura": ["Cultura"],
    "Esporte e lazer": ["Desporto e Lazer"], "Mobilidade/transporte": ["Transporte"],
    "Administração": ["Administração"], "Agricultura": ["Agricultura"],
}


# ---------------------------------------------------------------- preparação de dados
def rreo_final(df: pd.DataFrame) -> pd.DataFrame:
    """Último bimestre disponível de cada ano (valores acumulados no ano)."""
    ult = df.groupby("exercicio")["periodo"].transform("max")
    return df[df["periodo"] == ult]


@st.cache_data
def despesa_por_funcao() -> pd.DataFrame | None:
    a2 = ler("siconfi_rreo_anexo02.csv")
    if a2 is None:
        return None
    d = rreo_final(a2)
    d = d[d["coluna"].astype(str).str.contains("LIQUIDADAS ATÉ O BIMESTRE", case=False, na=False)]
    d = d[d["conta"].isin(sum(AREAS.values(), []))]
    d = d.groupby(["exercicio", "conta"], as_index=False)["valor"].max()
    inv = {c: a for a, cs in AREAS.items() for c in cs}
    d["area"] = d["conta"].map(inv)
    return d.groupby(["exercicio", "area"], as_index=False)["valor"].sum()


@st.cache_data
def subfuncoes() -> pd.DataFrame | None:
    """Despesa liquidada por subfunção, com a função (área) de origem pela ordem das linhas do RREO."""
    a2 = ler("siconfi_rreo_anexo02.csv")
    if a2 is None:
        return None
    d = rreo_final(a2)
    d = d[d["coluna"].astype(str).str.contains("LIQUIDADAS ATÉ O BIMESTRE", case=False, na=False)]
    funcoes = set(sum(AREAS.values(), []))
    linhas, atual = [], None
    for _, r in d.iterrows():
        conta = str(r["conta"])
        if conta in funcoes:
            atual = conta
        elif atual and "DESPESAS" not in conta.upper():
            linhas.append({"exercicio": r["exercicio"], "funcao": atual, "subfuncao": conta, "valor": r["valor"]})
    return pd.DataFrame(linhas)


@st.cache_data
def populacao() -> dict:
    df = ler("ibge_populacao.csv")
    return {} if df is None else dict(zip(df["ano"], df["populacao"]))


def pop_ano(ano: int) -> int:
    p = populacao()
    if not p:
        return POP_CENSO
    anos = sorted(p)
    anteriores = [a for a in anos if a <= ano]
    return int(p[anteriores[-1]] if anteriores else p[anos[0]])


@st.cache_data
def tributos() -> pd.DataFrame | None:
    dca = ler("siconfi_dca_receitas.csv")
    if dca is None:
        return None
    d = dca[dca["coluna"] == "Receitas Brutas Realizadas"].copy()
    nome = d["conta"].astype(str)
    regras = {"IPTU": nome.str.contains("Predial e Territorial Urbana"),
              "ISS": nome.str.contains("Serviços de Qualquer Natureza"),
              "ITBI": nome.str.contains("Inter Vivos"),
              "Total de impostos": nome.str.match(r"^1\.1\.1\.0\.00\.0\.0"),
              "Receitas correntes": nome.str.match(r"^1\.0\.0\.0\.00\.0\.0")}
    partes = []
    for trib, m in regras.items():
        x = d[m].groupby("exercicio", as_index=False)["valor"].max()
        x["tributo"] = trib
        partes.append(x)
    return pd.concat(partes, ignore_index=True)


@st.cache_data
def pessoal() -> pd.DataFrame | None:
    rgf = ler("siconfi_rgf_pessoal.csv")
    if rgf is None:
        return None
    ult = rgf.groupby("exercicio")["periodo"].transform("max")
    r = rgf[rgf["periodo"] == ult]
    conta = r["conta"].astype(str)
    pctcol = r["coluna"].astype(str).str.contains("% sobre a RCL", case=False)
    def serie(mask, nome):
        x = r[mask & pctcol].groupby("exercicio", as_index=False)["valor"].first()
        x["indicador"] = nome
        return x
    out = pd.concat([serie(conta.str.startswith("DESPESA TOTAL COM PESSOAL"), "Despesa com pessoal (% RCL)"),
                     serie(conta.str.startswith("LIMITE MÁXIMO"), "Limite máximo"),
                     serie(conta.str.startswith("LIMITE PRUDENCIAL"), "Limite prudencial"),
                     serie(conta.str.startswith("LIMITE DE ALERTA"), "Limite de alerta")], ignore_index=True)
    out["periodo"] = out["exercicio"].map(r.groupby("exercicio")["periodo"].max())
    return out


# ---------------------------------------------------------------- filtros globais
def anos_disponiveis() -> list[int]:
    anos = set()
    for nome, col in (("siconfi_rreo_anexo01.csv", "exercicio"), ("pncp_contratacoes.csv", "ano")):
        df = ler(nome)
        if df is not None:
            anos |= set(int(a) for a in df[col].dropna().unique())
    return sorted(anos, reverse=True) or [2025]


st.sidebar.title("Goianápolis em Números")
def ano_padrao(anos):
    """Ano padrão: o mais recente com RREO completo (6º bimestre) no SICONFI."""
    a1 = ler("siconfi_rreo_anexo01.csv")
    if a1 is not None:
        completos = a1.groupby("exercicio")["periodo"].max()
        completos = completos[completos == 6]
        if len(completos) and int(completos.index.max()) in anos:
            return anos.index(int(completos.index.max()))
    return 0


_ANOS = anos_disponiveis()
ANO = st.sidebar.selectbox("Ano (filtro global)", _ANOS, index=ano_padrao(_ANOS),
                           help="Vale para todas as páginas. Séries históricas mostram os anos até o selecionado.")


def ate_ano(df, col="exercicio"):
    return df[df[col] <= ANO]


# ---------------------------------------------------------------- páginas
def pg_visao():
    cabecalho("Goianápolis em Números",
              f"Painel público com dados abertos do município de Goianápolis (GO), IBGE 5208400. Ano selecionado: **{ANO}**.",
              "SICONFI/Tesouro Nacional (RREO, último bimestre do ano) e IBGE.")
    a1 = ler("siconfi_rreo_anexo01.csv")
    if a1 is None:
        return faltando("siconfi_rreo_anexo01.csv", "coleta/siconfi.py")
    d = rreo_final(a1)
    da = d[d["exercicio"] == ANO]
    if da.empty:
        return st.info(f"Ainda não há RREO de {ANO} no SICONFI.")
    def v(c, col):
        x = da[da["conta"].astype(str).str.contains(c, case=False, regex=False)
               & da["coluna"].astype(str).str.contains(col, case=False, regex=False)]
        return float(x["valor"].iloc[0]) if len(x) else None
    rec = v("RECEITAS (EXCETO INTRA", "Até o Bimestre")
    desp = v("DESPESAS (EXCETO INTRA", "LIQUIDADAS ATÉ O BIMESTRE")
    pop = pop_ano(ANO)
    per = int(da["periodo"].max())
    kpis([("População", num(pop), "IBGE: estimativa do ano ou Censo 2022"),
          ("Receita realizada", brl_curto(rec), brl(rec)),
          ("Despesa liquidada", brl_curto(desp), brl(desp)),
          ("Receita per capita", brl(rec / pop) if rec else "n/d")])
    if per < 6:
        st.caption(f"{ANO}: dados acumulados até o {per}º bimestre.")
    dpf = despesa_por_funcao()
    if dpf is not None:
        x = dpf[dpf["exercicio"] == ANO].sort_values("valor", ascending=False)
        grafico(px.treemap(x, path=["area"], values="valor", title=f"Despesa liquidada por área em {ANO}"), None)


def pg_despesas():
    cabecalho("Para onde vai o dinheiro",
              "Despesa liquidada por **função de governo** (usada aqui como aproximação da área/secretaria; "
              "não corresponde exatamente ao organograma da prefeitura).", "SICONFI, RREO Anexo 02.")
    d = despesa_por_funcao()
    if d is None:
        return faltando("siconfi_rreo_anexo02.csv", "coleta/siconfi.py")
    areas = st.sidebar.multiselect("Área (função de governo)", sorted(d["area"].unique()))
    if areas:
        d = d[d["area"].isin(areas)]
    da = d[d["exercicio"] == ANO].sort_values("valor")
    if da.empty:
        return st.info(f"Sem dados de {ANO}.")
    kpis([("Total das áreas exibidas", brl_curto(da["valor"].sum()), brl(da["valor"].sum())),
          ("Maior área", da.iloc[-1]["area"]), ("Per capita (total exibido)", brl(da["valor"].sum() / pop_ano(ANO)))])
    grafico(px.bar(da, x="valor", y="area", orientation="h", title=f"Despesa liquidada por área em {ANO}",
                   labels={"valor": "R$", "area": ""}), "x")
    grafico(px.line(ate_ano(d), x="exercicio", y="valor", color="area", markers=True, title="Evolução anual",
                    labels={"valor": "R$", "exercicio": "Ano", "area": "Área"}))
    sf = subfuncoes()
    if sf is not None and not sf.empty:
        s = sf[sf["exercicio"] == ANO]
        if areas:
            s = s[s["funcao"].isin(sum((AREAS[a] for a in areas), []))]
        s = s[s["valor"] > 0].sort_values("valor", ascending=False)
        with st.expander("Detalhe por subfunção"):
            st.dataframe(s, width="stretch", hide_index=True,
                         column_config={"valor": st.column_config.NumberColumn("Liquidado (R$)", format="localized")})


def pg_receitas():
    cabecalho("De onde vem o dinheiro", "Receitas realizadas e arrecadação própria (IPTU, ISS, ITBI).",
              "SICONFI: RREO Anexo 01 (bimestral) e DCA Anexo I-C (anual).")
    a1 = ler("siconfi_rreo_anexo01.csv")
    if a1 is None:
        return faltando("siconfi_rreo_anexo01.csv", "coleta/siconfi.py")
    d = rreo_final(a1)
    contas = ["RECEITAS CORRENTES", "Impostos", "Transferências Correntes", "OUTRAS RECEITAS CORRENTES",
              "RECEITAS DE CAPITAL"]
    x = d[d["conta"].isin(contas) & d["coluna"].astype(str).str.contains("Até o Bimestre", case=False)]
    x = ate_ano(x.groupby(["exercicio", "conta"], as_index=False)["valor"].max())
    grafico(px.bar(x, x="exercicio", y="valor", color="conta", barmode="group", title="Receitas realizadas por ano",
                   labels={"valor": "R$", "exercicio": "Ano", "conta": ""}))
    st.subheader("Arrecadação própria: IPTU, ISS e ITBI")
    t = tributos()
    if t is None:
        return faltando("siconfi_dca_receitas.csv", "coleta/siconfi_extra.py")
    t = ate_ano(t)
    ta = t[t["exercicio"] == ANO].set_index("tributo")["valor"]
    if ta.empty:
        st.info(f"A DCA de {ANO} ainda não está no SICONFI (é anual). Mostrando a série disponível.")
    else:
        rc = ta.get("Receitas correntes")
        proprios = sum(ta.get(k, 0) for k in ("IPTU", "ISS", "ITBI"))
        kpis([("IPTU", brl_curto(ta.get("IPTU")), brl(ta.get("IPTU"))),
              ("ISS", brl_curto(ta.get("ISS")), brl(ta.get("ISS"))),
              ("ITBI", brl_curto(ta.get("ITBI")), brl(ta.get("ITBI"))),
              ("IPTU+ISS+ITBI / receitas correntes", pct(100 * proprios / rc) if rc else "n/d")])
    tt = t[t["tributo"].isin(["IPTU", "ISS", "ITBI"])]
    grafico(px.line(tt, x="exercicio", y="valor", color="tributo", markers=True, title="Arrecadação por tributo",
                    labels={"valor": "R$", "exercicio": "Ano", "tributo": ""}))
    pc = tt.assign(per_capita=tt.apply(lambda r: r["valor"] / pop_ano(int(r["exercicio"])), axis=1))
    grafico(px.bar(pc, x="exercicio", y="per_capita", color="tributo", barmode="group",
                   title="Arrecadação per capita", labels={"per_capita": "R$/hab.", "exercicio": "Ano", "tributo": ""}))
    st.caption("Em 2020–2021 o ISS não aparece com o código atual na DCA; a série pode estar incompleta nesses anos.")


def pg_pessoal():
    cabecalho("Despesa com pessoal (LRF)",
              "Despesa total com pessoal do Poder Executivo em % da Receita Corrente Líquida ajustada.",
              "SICONFI, RGF Anexo 01 (quadrimestral; último quadrimestre disponível do ano).")
    p = pessoal()
    if p is None:
        return faltando("siconfi_rgf_pessoal.csv", "coleta/siconfi_extra.py")
    p = ate_ano(p)
    pa = p[p["exercicio"] == ANO].set_index("indicador")["valor"]
    if not pa.empty:
        q = int(p.loc[p["exercicio"] == ANO, "periodo"].max())
        st.caption(f"{ANO}: posição do {q}º quadrimestre (últimos 12 meses).")
        dtp, lim = pa.get("Despesa com pessoal (% RCL)"), pa.get("Limite máximo")
        if dtp is not None and lim is not None and dtp > lim:
            st.error(f"Despesa com pessoal ({pct(dtp)}) acima do limite máximo da LRF ({pct(lim)}).")
        elif dtp is not None and pa.get("Limite de alerta") is not None and dtp > pa.get("Limite de alerta"):
            st.warning(f"Despesa com pessoal ({pct(dtp)}) acima do limite de alerta.")
        kpis([("Despesa com pessoal", pct(pa.get("Despesa com pessoal (% RCL)"))),
              ("Limite de alerta", pct(pa.get("Limite de alerta"))),
              ("Limite prudencial", pct(pa.get("Limite prudencial"))),
              ("Limite máximo", pct(pa.get("Limite máximo")))])
    fig = px.line(p, x="exercicio", y="valor", color="indicador", markers=True, title="Pessoal em % da RCL",
                  labels={"valor": "% da RCL", "exercicio": "Ano", "indicador": ""})
    fig.update_yaxes(ticksuffix="%")
    grafico(fig, None)


def pg_transferencias():
    cabecalho("Transferências especiais (emendas parlamentares)",
              "Planos de ação de transferências especiais (\"emendas PIX\") com Goianápolis como beneficiário.",
              "Transferegov, API de Transferências Especiais.")
    t = ler("transferegov_especiais.csv")
    if t is None:
        return faltando("transferegov_especiais.csv", "coleta/transferegov.py")
    t = t[t["ano"] <= ANO]
    kpis([("Planos de ação (até o ano)", num(len(t))), ("Valor total", brl_curto(t["valor_total"].sum()),
                                                          brl(t["valor_total"].sum())),
          (f"Valor em {ANO}", brl_curto(t.loc[t["ano"] == ANO, "valor_total"].sum()))])
    g = t.groupby("ano", as_index=False)["valor_total"].sum()
    grafico(px.bar(g, x="ano", y="valor_total", title="Valor por ano", labels={"valor_total": "R$", "ano": "Ano"}))
    st.dataframe(t, width="stretch", hide_index=True,
                 column_config={c: st.column_config.NumberColumn(format="localized")
                                for c in ("valor_custeio", "valor_investimento", "valor_total")})


def pg_compras():
    cabecalho("Compras públicas", "Contratações publicadas pela prefeitura no PNCP.",
              "Portal Nacional de Contratações Públicas (pncp.gov.br).")
    df = ler("pncp_contratacoes.csv")
    if df is None:
        return faltando("pncp_contratacoes.csv", "coleta/pncp.py")
    f = df[df["ano"] == ANO]
    if "unidadeOrgao" in f:
        unidades = st.sidebar.multiselect("Unidade/órgão (PNCP)", sorted(df["unidadeOrgao"].dropna().unique()))
        if unidades:
            f = f[f["unidadeOrgao"].isin(unidades)]
    if f.empty:
        return st.info(f"Nenhuma contratação de {ANO} no arquivo do PNCP.")
    kpis([("Contratações", num(len(f))),
          ("Valor estimado", brl_curto(f["valorEstimado"].sum()), brl(f["valorEstimado"].sum())),
          ("Valor homologado", brl_curto(f["valorHomologado"].sum()), brl(f["valorHomologado"].sum()))])
    c1, c2 = st.columns(2)
    with c1:
        g = f.groupby("modalidade", as_index=False)["valorHomologado"].sum().sort_values("valorHomologado")
        grafico(px.bar(g, x="valorHomologado", y="modalidade", orientation="h", title="Homologado por modalidade",
                       labels={"valorHomologado": "R$", "modalidade": ""}), "x")
    with c2:
        if "unidadeOrgao" in f:
            g = f.groupby("unidadeOrgao", as_index=False)["valorHomologado"].sum().sort_values("valorHomologado")
            grafico(px.bar(g, x="valorHomologado", y="unidadeOrgao", orientation="h", title="Homologado por unidade",
                           labels={"valorHomologado": "R$", "unidadeOrgao": ""}), "x")
    busca = st.text_input("Buscar no objeto")
    if busca:
        f = f[f["objeto"].astype(str).str.contains(busca, case=False)]
    st.dataframe(f, width="stretch", hide_index=True,
                 column_config={"valorEstimado": st.column_config.NumberColumn("Estimado (R$)", format="localized"),
                                "valorHomologado": st.column_config.NumberColumn("Homologado (R$)", format="localized")})


def pg_area(nome: str, extra: str = ""):
    d = despesa_por_funcao()
    if d is None:
        return faltando("siconfi_rreo_anexo02.csv", "coleta/siconfi.py")
    d = ate_ano(d[d["area"] == nome])
    if d.empty:
        return st.warning("Sem dados de despesa para esta área.")
    d = d.assign(per_capita=d.apply(lambda r: r["valor"] / pop_ano(int(r["exercicio"])), axis=1))
    da = d[d["exercicio"] == ANO]
    if not da.empty:
        r = da.iloc[0]
        kpis([(f"Despesa liquidada {ANO}", brl_curto(r["valor"]), brl(r["valor"])), ("Per capita", brl(r["per_capita"]))])
    c1, c2 = st.columns(2)
    with c1:
        grafico(px.bar(d, x="exercicio", y="valor", title="Despesa liquidada", labels={"valor": "R$", "exercicio": "Ano"}))
    with c2:
        grafico(px.bar(d, x="exercicio", y="per_capita", title="Per capita",
                       labels={"per_capita": "R$/hab.", "exercicio": "Ano"}))
    if extra:
        st.info(extra)


def pg_saude():
    cabecalho("Saúde", "Gasto municipal com saúde.", "SICONFI, RREO Anexo 02; IBGE (população).")
    pg_area("Saúde", "Indicadores do DATASUS (nascimentos, internações) ainda não integrados.")


def pg_educacao():
    cabecalho("Educação", "Gasto municipal com educação.", "SICONFI, RREO Anexo 02; IBGE (população).")
    pg_area("Educação", "IDEB e matrículas (INEP) não integrados: o download do INEP não respondeu nos testes.")


def pg_demais():
    cabecalho("Demais áreas", "Gasto por área de política pública.", "SICONFI, RREO Anexo 02; IBGE (população).")
    area = st.selectbox("Área", ["Assistência social", "Segurança", "Meio ambiente", "Infraestrutura/urbanismo",
                                 "Cultura", "Esporte e lazer", "Mobilidade/transporte", "Agricultura", "Administração"])
    avisos = {"Segurança": "Indicadores de criminalidade são estaduais (SSP-GO); aqui só o gasto municipal.",
              "Mobilidade/transporte": "Não há dados municipais públicos de trânsito; só gasto.",
              "Cultura": "Sem indicadores municipais de resultado; só gasto.",
              "Esporte e lazer": "Sem indicadores municipais de resultado; só gasto.",
              "Meio ambiente": "Dados externos (MapBiomas/INPE) ainda não integrados."}
    pg_area(area, avisos.get(area, ""))


def pg_sobre():
    cabecalho("Sobre os dados")
    st.markdown("""
### Fontes integradas (verificadas, com dados de Goianápolis)
| Fonte | Conteúdo | Atualização | Script |
|---|---|---|---|
| SICONFI, RREO Anexos 01 e 02 | Receitas; despesa por função e subfunção | Bimestral | `coleta/siconfi.py` |
| SICONFI, DCA Anexo I-C | Receitas detalhadas: IPTU, ISS, ITBI | Anual | `coleta/siconfi_extra.py` |
| SICONFI, RGF Anexo 01 | Despesa com pessoal × limites da LRF | Quadrimestral | `coleta/siconfi_extra.py` |
| PNCP, contratações e contratos | Compras, modalidades, unidades, fornecedores | Contínua | `coleta/pncp.py` |
| IBGE, agregado 6579 + Censo 2022 | População | Anual | `coleta/ibge.py` |
| Transferegov, Transferências Especiais | Emendas parlamentares "PIX" | Contínua | `coleta/transferegov.py` |

### Fontes não integradas
- **INEP / IDEB:** o download (download.inep.gov.br) não respondeu nos testes.
- **DATASUS (TabNet), FNS e FNDE:** não há API simples verificada para o recorte municipal.
- **Portal da Transparência federal (API):** exige chave de acesso (HTTP 401 sem chave).
- **Portal da prefeitura (Megasoft) e acesso à informação:** sem exportação automatizável verificada.

### Limitações
- "Área" é a **função de governo** do SICONFI, uma aproximação da secretaria, não o organograma.
- O PNCP só cobre bem as compras a partir de 2023; anos anteriores aparecem incompletos.
- Per capita usa a estimativa do IBGE do ano (ou o Censo 2022 / o ano anterior mais próximo).
""")


PAGINAS = {"Visão geral": pg_visao, "Despesas": pg_despesas, "Receitas e tributos": pg_receitas,
           "Pessoal (LRF)": pg_pessoal, "Transferências": pg_transferencias, "Compras": pg_compras,
           "Saúde": pg_saude, "Educação": pg_educacao, "Demais áreas": pg_demais, "Sobre os dados": pg_sobre}
escolha = st.sidebar.radio("Páginas", list(PAGINAS))
PAGINAS[escolha]()
