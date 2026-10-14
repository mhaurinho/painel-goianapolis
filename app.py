"""Goianápolis em Números: painel público de dados municipais (Streamlit + Plotly)."""
import importlib
import sys
import unicodedata

import pandas as pd
import plotly.express as px
import streamlit as st

# No Streamlit Cloud, um redeploy pode reexecutar app.py sem recarregar os módulos locais já importados;
# aí a importação de uma função nova falha (ImportError). Recarregamos os módulos do projeto a cada execução.
for _mod in ("ui", "dados_siconfi", "analises", "alertas", "pagina_auditoria", "pagina_conciliacao",
             "pagina_fornecedores", "pagina_projecao", "pagina_capilaridade", "pagina_denuncia"):
    if _mod in sys.modules:
        importlib.reload(sys.modules[_mod])

from ui import (CSS, TINTA, VERDE, brl, brl_curto, cabecalho, definir_secao, faltando, frases, grafico, heroi,
                kpis, ler, num, pct)

POP_CENSO = 13967  # Censo 2022 (IBGE)

st.set_page_config(page_title="Goianápolis em Números", page_icon="📊", layout="wide")
st.markdown(CSS, unsafe_allow_html=True)

from dados_siconfi import AREAS, FUNCOES  # noqa: E402


# ---------------------------------------------------------------- preparação de dados
def rreo_final(df: pd.DataFrame) -> pd.DataFrame:
    """Último bimestre disponível de cada ano (valores acumulados no ano)."""
    ult = df.groupby("exercicio")["periodo"].transform("max")
    return df[df["periodo"] == ult]


@st.cache_data
def anexo02_liquidado() -> pd.DataFrame | None:
    """Linhas do Anexo 02 (despesa liquidada, exceto intraorçamentária) já com a função de cada subfunção."""
    a2 = ler("siconfi_rreo_anexo02.csv")
    if a2 is None:
        return None
    d = rreo_final(a2)
    d = d[d["coluna"].astype(str).str.startswith("DESPESAS LIQUIDADAS ATÉ O BIMESTRE")]
    if "rotulo" in d:
        d = d[d["rotulo"].astype(str).str.contains("Exceto Intra", case=False)]
    linhas, atual = [], None
    for _, r in d.iterrows():
        conta = str(r["conta"])
        if conta.upper().startswith(("DESPESAS", "TOTAL")) or "TOTAL" in conta.upper():
            atual = None
            continue
        if conta in FUNCOES:
            atual = conta
            linhas.append({"exercicio": r["exercicio"], "funcao": conta, "subfuncao": None, "valor": r["valor"]})
        elif atual:
            linhas.append({"exercicio": r["exercicio"], "funcao": atual, "subfuncao": conta, "valor": r["valor"]})
    return pd.DataFrame(linhas)


@st.cache_data
def total_rreo2() -> pd.Series | None:
    a2 = ler("siconfi_rreo_anexo02.csv")
    if a2 is None:
        return None
    d = rreo_final(a2)
    d = d[d["coluna"].astype(str).str.startswith("DESPESAS LIQUIDADAS ATÉ O BIMESTRE")
          & d["conta"].astype(str).str.startswith("DESPESAS (EXCETO INTRA")]
    return d.groupby("exercicio")["valor"].first()


@st.cache_data
def despesa_por_funcao() -> pd.DataFrame | None:
    """Despesa liquidada por área. Funções fora de AREAS entram em "Outras funções", e o total fecha com o RREO."""
    base = anexo02_liquidado()
    if base is None:
        return None
    f = base[base["subfuncao"].isna()].groupby(["exercicio", "funcao"], as_index=False)["valor"].sum()
    inv = {c: a for a, cs in AREAS.items() for c in cs}
    f["area"] = f["funcao"].map(inv).fillna("Outras funções")
    return f.groupby(["exercicio", "area"], as_index=False)["valor"].sum()


@st.cache_data
def subfuncoes() -> pd.DataFrame | None:
    base = anexo02_liquidado()
    return None if base is None else base[base["subfuncao"].notna()].reset_index(drop=True)


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


st.logo("assets/logo.svg", size="large")
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
    dpf = despesa_por_funcao()
    x = dpf[dpf["exercicio"] == ANO].sort_values("valor", ascending=False) if dpf is not None else pd.DataFrame()

    sic, _, pn, _ = calcular_alertas(ANO)
    sic = sic[sic["area"] != "TOTAL (referência)"] if not sic.empty else sic
    contar = lambda t, cor: int(t["nivel"].str.contains(cor).sum()) if not t.empty else 0  # noqa: E731
    vermelho, amarelo = contar(sic, "vermelho") + contar(pn, "vermelho"), contar(sic, "amarelo") + contar(pn, "amarelo")

    periodo = "ano fechado" if per == 6 else f"parcial, até o {per}º bimestre"
    selos = [("info", f"{ANO} · {periodo}"), ("info", f"{num(pop)} habitantes")]
    if vermelho:
        selos.append(("alerta", f"{vermelho} alerta(s) vermelho(s) de gasto"))
    if amarelo:
        selos.append(("atencao", f"{amarelo} alerta(s) amarelo(s)"))
    if not (vermelho or amarelo):
        selos.append(("ok", "nenhum alerta de gasto"))
    if desp and rec:
        saldo = rec - desp
        resultado = (f"<b>sobraram {brl_curto(saldo)}</b>" if saldo >= 0 else f"<b>faltaram {brl_curto(-saldo)}</b>")
        heroi(f"Goianápolis · GO · {ANO}", brl_curto(desp),
              f"foi o que a prefeitura efetivamente gastou{' até agora' if per < 6 else ''} em {ANO}: "
              f"<b>{brl(desp / pop, 0)} por morador</b>. Entraram {brl_curto(rec)}; {resultado}.", selos)

    itens = []
    if not x.empty and desp:
        top2 = x.head(2)
        itens.append((pct(top2["valor"].sum() / desp * 100, 0), f"da despesa foi para {top2['area'].iloc[0]} e "
                      f"{top2['area'].iloc[1]}." if len(top2) == 2 else "da despesa foi para a maior área.", "ok"))
    if rec:
        itens.append((brl(rec / pop, 0), "de receita por morador no ano, somando arrecadação própria e repasses.", "ok"))
    itens.append((str(vermelho + amarelo), "áreas ou unidades gastaram acima da média histórica do mesmo período. "
                  "Sinal para acompanhar, não irregularidade.", "alerta" if vermelho else "atencao" if amarelo else "ok"))
    frases(itens)
    if vermelho or amarelo:
        st.page_link(_paginas["Alertas"], label="Ver os alertas em detalhe", icon="🚨")

    c1, c2 = st.columns([3, 2])
    with c1:
        if not x.empty:
            fig = px.treemap(x, path=["area"], values="valor", title=f"Despesa liquidada por área em {ANO}")
            fig.update_traces(texttemplate="%{label}<br>%{percentRoot:.1%}",
                              hovertemplate="%{label}: R$ %{value:,.2f}<extra></extra>")
            grafico(fig, None)
    with c2:
        serie = []
        for ano_, dd in d[d["exercicio"] <= ANO].groupby("exercicio"):
            for rot, cnt, col in (("Receita", "RECEITAS (EXCETO INTRA", "Até o Bimestre"),
                                  ("Despesa liquidada", "DESPESAS (EXCETO INTRA", "LIQUIDADAS ATÉ O BIMESTRE")):
                x = dd[dd["conta"].astype(str).str.startswith(cnt) & dd["coluna"].astype(str).str.contains(col, case=False)]
                if len(x):
                    serie.append({"ano": ano_, "tipo": rot, "valor": float(x["valor"].iloc[0])})
        if serie:
            fig = px.line(pd.DataFrame(serie), x="ano", y="valor", color="tipo", markers=True,
                          title="Receita × despesa", labels={"valor": "R$", "ano": "Ano", "tipo": ""},
                          color_discrete_map={"Receita": VERDE, "Despesa liquidada": TINTA})
            fig.update_traces(line_width=3, marker_size=8)
            grafico(fig)


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
    tot = total_rreo2()
    if not areas and tot is not None and ANO in tot.index:
        dif = da["valor"].sum() - tot[ANO]
        st.caption(f"Conferência: soma das funções = total do RREO Anexo 02 ({brl(tot[ANO])}); diferença {brl(dif)}.")
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
            outras = [f for f in FUNCOES if f not in sum(AREAS.values(), [])]
            s = s[s["funcao"].isin(sum((AREAS.get(a, outras) for a in areas), []))]
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
    x["conta"] = x["conta"].replace({"RECEITAS CORRENTES": "Receitas correntes", "RECEITAS DE CAPITAL": "Receitas de capital",
                                     "OUTRAS RECEITAS CORRENTES": "Outras receitas correntes"})
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
    from analises import normalizar_unidade
    df = df.assign(unidadeOrgao=df["unidadeOrgao"].map(normalizar_unidade)) if "unidadeOrgao" in df else df
    incluir = st.toggle("Incluir revogadas/anuladas/suspensas", value=False)
    f = df[df["ano"] == ANO]
    n_publicadas = len(f)
    if not incluir and "situacao" in f:
        f = f[~f["situacao"].astype(str).isin(("Revogada", "Anulada", "Suspensa"))]
    if "unidadeOrgao" in f:
        unidades = st.sidebar.multiselect("Unidade/órgão (PNCP)", sorted(df["unidadeOrgao"].dropna().unique()))
        if unidades:
            f = f[f["unidadeOrgao"].isin(unidades)]
    if f.empty:
        return st.info(f"Nenhuma contratação de {ANO} no arquivo do PNCP.")
    kpis([("Contratações publicadas", num(n_publicadas), "Todas as publicadas no PNCP no ano, em qualquer situação"),
          ("Consideradas nas somas", num(len(f)), "Exclui revogadas, anuladas e suspensas (use a chave acima para incluir)"),
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
    st.subheader("Qualidade dos dados (conferências automáticas)")
    from analises import qualidade_pncp
    tot = total_rreo2()
    dpf = despesa_por_funcao()
    if tot is not None and dpf is not None:
        conf = dpf.groupby("exercicio")["valor"].sum().to_frame("soma_funcoes").join(tot.rename("total_rreo"))
        conf["diferenca"] = conf["soma_funcoes"] - conf["total_rreo"]
        st.markdown("**RREO Anexo 02:** soma das funções × total de despesa liquidada (deve ser zero).")
        st.dataframe(conf.reset_index(), width="stretch", hide_index=True,
                     column_config={c: st.column_config.NumberColumn(format="localized")
                                    for c in ("soma_funcoes", "total_rreo", "diferenca")})
    c, k = ler("pncp_contratacoes.csv"), ler("pncp_contratos.csv")
    if c is not None:
        q = qualidade_pncp(c, k)
        st.markdown(f"""
**PNCP** ({num(q['contratacoes'])} contratações, {num(q.get('contratos', 0))} contratos):
- {num(q['invalidas'])} contratações revogadas, anuladas ou suspensas, **excluídas das somas** por padrão;
- {num(q['sem_homologado'])} sem valor homologado (R$ 0), em geral ainda não concluídas;
- {num(q['ano_diferente_publicacao'])} com ano da compra diferente do ano de publicação no PNCP (o painel usa o ano da compra);
- {num(q['duplicidades'])} com mesmo ano, objeto e valor estimado de outra contratação (possível duplicidade; veja a Auditoria);
- {num(q['razao_menor_1pct'])} com homologado menor que 1% do estimado (provável erro de digitação ou unidade);
- {num(q.get('contratos_sem_compra', 0))} contrato(s) sem a contratação correspondente no arquivo;
- {num(q.get('contratos_abaixo_100', 0))} contratos com valor global abaixo de R$ 100 (por exemplo, tarifas bancárias).
""")

    from alertas import ANOS_HISTORICO, LIMIAR_AMARELO, LIMIAR_VERMELHO, MIN_PUBLICACOES_ANO
    from analises import IQR_FATOR, LIMITE_DISPENSA, LIMITE_REFERENCIA_2023, RAZAO_HOMOLOGADO_MINIMA, VALOR_CONTRATO_MINIMO
    from pagina_fornecedores import HHI_ELEVADO, PARTICIPACAO_ELEVADA
    from pagina_projecao import ANOS_SAZONALIDADE
    lim = "; ".join(f"{a}: {brl(v)}" for a, v in sorted(LIMITE_DISPENSA.items()))
    st.markdown(f"""
### Limiares fixos usados nas análises
São escolhas de método do painel (não são regras legais, exceto o limite de dispensa). Mudá-los muda os sinais exibidos.

| Onde | Limiar | Por quê |
|---|---|---|
| Alertas | 🟡 acima de {LIMIAR_AMARELO:.0f}% e 🔴 acima de {LIMIAR_VERMELHO:.0f}% sobre a média do mesmo período nos {ANOS_HISTORICO} anos anteriores | Critério pedido para o painel; valores nominais |
| Alertas (PNCP) | ano com menos de {MIN_PUBLICACOES_ANO} contratações no mesmo intervalo fica fora da média | A adoção do PNCP pelo município foi irregular (2 publicações em 2024) |
| Fornecedores | HHI acima de {num(HHI_ELEVADO)} ou um fornecedor com mais de {PARTICIPACAO_ELEVADA:.0f}% → "concentração elevada — ponto de atenção" | 2.500 é a referência usual de mercado muito concentrado (escala 0–10.000) |
| Auditoria (homologado × estimado) | fora de Q1 − {num(IQR_FATOR, 1)}·IQR a Q3 + {num(IQR_FATOR, 1)}·IQR (teto 1) | Regra usual de valores atípicos |
| Qualidade do PNCP | homologado menor que {pct(100 * RAZAO_HOMOLOGADO_MINIMA, 0)} do estimado | Provável erro de digitação ou de unidade |
| Qualidade do PNCP | contrato com valor global abaixo de {brl(VALOR_CONTRATO_MINIMO)} | Ex.: tarifas bancárias registradas como contrato |
| Possível fracionamento | limite de dispensa do art. 75, II, da Lei 14.133/2021 ({lim}; até 2023 usa {brl(LIMITE_REFERENCIA_2023)} como referência; depois de 2026, o maior valor conhecido) | Valores dos decretos de atualização |
| Projeção | sazonalidade = média dos {ANOS_SAZONALIDADE} anos anteriores completos | Histórico do SICONFI desde 2020 |
""")

def _tabela_alertas(t, col_nome, rotulo):
    cfg = {"atual": st.column_config.NumberColumn("Atual (R$)", format="localized"),
           "media_historica": st.column_config.NumberColumn("Média histórica (R$)", format="localized"),
           "variacao_pct": st.column_config.NumberColumn("Variação (%)", format="%.1f"),
           "acima_do_total_pp": st.column_config.NumberColumn(
               "Variação descontado o crescimento do TOTAL (%)", format="%.1f",
               help="(1 + variação da área) ÷ (1 + variação do TOTAL) − 1. Positivo: a área cresceu mais que o orçamento."),
           col_nome: st.column_config.TextColumn(rotulo), "nivel": st.column_config.TextColumn("Nível")}
    cols = [col_nome, "atual", "media_historica", "variacao_pct"] + (["acima_do_total_pp"] if "acima_do_total_pp" in t else []) + ["nivel"]
    st.dataframe(t[cols], width="stretch", hide_index=True, column_config=cfg)


def calcular_alertas(ano):
    from alertas import alertas_pncp, alertas_siconfi
    a2, c = ler("siconfi_rreo_anexo02.csv"), ler("pncp_contratacoes.csv")
    sic, per = alertas_siconfi(a2, ano) if a2 is not None else (pd.DataFrame(), None)
    pn, desc = alertas_pncp(c, ano) if c is not None else (pd.DataFrame(), None)
    return sic, per, pn, desc


def pg_alertas():
    from alertas import ANOS_HISTORICO, LIMIAR_AMARELO, LIMIAR_VERMELHO
    cabecalho("Alertas automáticos de gasto",
              f"Compara o gasto acumulado do período atual com a **média do mesmo período nos {ANOS_HISTORICO} anos "
              f"anteriores**. 🟡 acima de {LIMIAR_AMARELO:.0f}% · 🔴 acima de {LIMIAR_VERMELHO:.0f}%.",
              "SICONFI (RREO Anexo 02, liquidado acumulado por bimestre) e PNCP (homologado por unidade).")
    st.info("São **sinais para acompanhamento**, não irregularidades. Os valores são **nominais** (sem correção "
            "pela inflação) e o orçamento do município cresceu bastante no período; compare cada área com a linha "
            "**TOTAL (referência)** e a coluna *descontado o crescimento do TOTAL*. No PNCP, o histórico é curto (a partir de 2023) e o valor homologado entra na "
            "data de publicação, não na execução.")
    sic, per, pn, desc = calcular_alertas(ANO)
    st.subheader("Áreas (função de governo), SICONFI")
    if sic.empty:
        st.info(f"Sem RREO de {ANO}.")
    else:
        st.caption(sic["comparacao"].iloc[0])
        _tabela_alertas(sic, "area", "Área")
        g = sic.dropna(subset=["variacao_pct"])
        fig = px.bar(g.sort_values("variacao_pct"), x="variacao_pct", y="area", orientation="h", color="nivel",
                     color_discrete_map={"🔴 vermelho": "#E8553A", "🟡 amarelo": "#E9A21B", "🟢 normal": "#0A8F6E"},
                     title="Variação sobre a média histórica (%)", labels={"variacao_pct": "%", "area": "", "nivel": ""})
        fig.add_vline(x=LIMIAR_AMARELO, line_dash="dot", line_color="#E9A21B")
        fig.add_vline(x=LIMIAR_VERMELHO, line_dash="dot", line_color="#E8553A")
        grafico(fig, None)
    st.subheader("Unidades do PNCP (valor homologado)")
    if pn.empty:
        st.info(f"Sem contratações publicadas no PNCP em {ANO}.")
    else:
        st.caption(desc)
        _tabela_alertas(pn, "unidadeOrgao", "Unidade")


def pg_fornecedores():
    from pagina_fornecedores import pagina
    pagina(ANO)


def pg_projecao():
    from pagina_projecao import pagina
    pagina(ANO)


def pg_capilaridade():
    from pagina_capilaridade import pagina
    pagina(ANO)


def pg_denuncia():
    from pagina_denuncia import pagina
    pagina()


def pg_auditoria():
    from pagina_auditoria import pagina
    pagina(ANO, despesa_por_funcao)


def pg_conciliacao():
    from pagina_conciliacao import pagina
    pagina(ANO, despesa_por_funcao)


# Navegação em grupos: o visitante encontra primeiro o panorama e sabe onde estão as conferências.
GRUPOS = {
    "Panorama": [("Visão geral", pg_visao, "📊"), ("Alertas", pg_alertas, "🚨")],
    "Dinheiro": [("Receitas e tributos", pg_receitas, "💰"), ("Despesas", pg_despesas, "💸"),
                 ("Pessoal (LRF)", pg_pessoal, "👥"), ("Transferências", pg_transferencias, "🔁"),
                 ("Projeção", pg_projecao, "📈")],
    "Áreas": [("Saúde", pg_saude, "🏥"), ("Educação", pg_educacao, "🎓"), ("Demais áreas", pg_demais, "🧭"),
              ("Capilaridade", pg_capilaridade, "🔬")],
    "Compras": [("Compras", pg_compras, "🧾"), ("Fornecedores", pg_fornecedores, "🏢")],
    "Confiança": [("Conciliação", pg_conciliacao, "✅"), ("Auditoria", pg_auditoria, "🔎"),
                  ("Sobre os dados", pg_sobre, "📚")],
    "Participe": [("Denúncia anônima", pg_denuncia, "📣")],
}


def _pagina(grupo, titulo, funcao, icone, padrao=False):
    def executar():
        definir_secao(grupo)
        funcao()
    slug = unicodedata.normalize("NFKD", titulo).encode("ascii", "ignore").decode().lower()
    slug = "".join(ch if ch.isalnum() else "-" for ch in slug).strip("-").replace("--", "-")
    return st.Page(executar, title=titulo, icon=icone, url_path=slug, default=padrao)


_paginas = {t: _pagina(g, t, f, i, padrao=(t == "Visão geral")) for g, itens in GRUPOS.items() for t, f, i in itens}
navegacao = st.navigation({g: [_paginas[t] for t, _, _ in itens] for g, itens in GRUPOS.items()}, expanded=True)


def rodape_sidebar():
    linhas = []
    a1 = ler("siconfi_rreo_anexo01.csv")
    if a1 is not None:
        ult = a1.sort_values(["exercicio", "periodo"]).iloc[-1]
        linhas.append(f"SICONFI: até o {int(ult['periodo'])}º bimestre de {int(ult['exercicio'])}")
    c = ler("pncp_contratacoes.csv")
    if c is not None and "dataPublicacao" in c:
        dt = pd.to_datetime(c["dataPublicacao"], errors="coerce").max()
        if pd.notna(dt):
            linhas.append(f"PNCP: última publicação em {dt:%d/%m/%Y}")
    st.sidebar.divider()
    st.sidebar.caption("**Dados disponíveis**  \n" + "  \n".join(linhas) +
                       "  \n[Código e fontes no GitHub](https://github.com/mhaurinho/painel-goianapolis)")


rodape_sidebar()
navegacao.run()
