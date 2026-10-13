"""Página Auditoria: pontos de atenção para verificação (não são acusações)."""
import pandas as pd
import plotly.express as px
import streamlit as st

from analises import (area_pncp, concentracao_fornecedores, hhi, limite_dispensa, outliers_iqr,
                      possivel_fracionamento)
from ui import brl, brl_curto, cabecalho, faltando, grafico, kpis, ler, num, pct

AVISO = """
**Como ler esta página.** Os itens abaixo são **pontos de atenção para verificação**, gerados por regras
automáticas sobre dados públicos. **Não indicam irregularidade** por si sós: cada caso pode ter justificativa
legal (por exemplo, dispensas emergenciais, inexigibilidade por exclusividade, credenciamento, contratos com bancos
para folha de pagamento).

**Limitações:** o PNCP só tem cobertura razoável a partir de 2023/2024 e depende do que a prefeitura publica;
o SICONFI é agregado por função, então **não há correspondência linha a linha** entre gasto e contratação;
a área de cada contratação é estimada pela unidade (FMS, FME, FMAS, FMMA) ou por palavras do objeto.
"""


def preparar(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    for c in ("valorEstimado", "valorHomologado"):
        df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0)
    df["area"] = [area_pncp(u, o) for u, o in zip(df.get("unidadeOrgao", [None] * len(df)), df["objeto"])]
    df["direta"] = df["modalidade"].astype(str).str.contains("Dispensa|Inexigib", case=False)
    return df


def pagina(ANO: int, despesa_por_funcao):
    cabecalho("Auditoria: pontos de atenção para verificação",
              "Cruzamentos automáticos entre o gasto (SICONFI) e as contratações publicadas (PNCP).",
              "PNCP (contratações e contratos) e SICONFI (RREO Anexo 02).")
    st.info(AVISO)
    c = ler("pncp_contratacoes.csv")
    if c is None:
        return faltando("pncp_contratacoes.csv", "coleta/pncp.py")
    c = preparar(c)
    todos = st.toggle("Considerar todos os anos do PNCP (ignorar o filtro de ano)", value=False)
    f = c if todos else c[c["ano"] == ANO]
    rotulo = "todos os anos" if todos else str(ANO)
    if f.empty:
        return st.warning(f"Sem contratações no PNCP para {rotulo}. Experimente outro ano (a cobertura começa em 2023).")

    # 1. contratação direta
    st.subheader("1. Participação de dispensa e inexigibilidade")
    dir_qtd = 100 * f["direta"].mean()
    tot_val = f["valorHomologado"].sum()
    dir_val = 100 * f.loc[f["direta"], "valorHomologado"].sum() / tot_val if tot_val else None
    kpis([("Contratações analisadas", num(len(f))), ("Diretas (quantidade)", pct(dir_qtd)),
          ("Diretas (valor homologado)", pct(dir_val))])
    g = c.groupby(["ano", "direta"], as_index=False).agg(qtd=("objeto", "size"))
    g["tipo"] = g["direta"].map({True: "Dispensa/inexigibilidade", False: "Demais modalidades"})
    grafico(px.bar(g, x="ano", y="qtd", color="tipo", title="Contratações por tipo e ano (PNCP)",
                   labels={"qtd": "Quantidade", "ano": "Ano", "tipo": ""}), None)

    # 2. homologado x estimado
    st.subheader("2. Homologado muito diferente do estimado (outliers por IQR)")
    out = outliers_iqr(f)
    if out.empty:
        st.success("Nenhum outlier encontrado no recorte.")
    else:
        lo, hi = out.attrs.get("faixa", (None, None))
        st.markdown(f"{num(len(out))} contratações com razão homologado/estimado fora da faixa "
                    f"[{num(lo, 2)}; {num(hi, 2)}]. Razões muito baixas podem indicar boa negociação **ou** "
                    "estimativa inflada; razões acima de 1 merecem conferência do preço.")
        st.dataframe(out[["ano", "modalidade", "objeto", "valorEstimado", "valorHomologado", "razao"]],
                     width="stretch", hide_index=True,
                     column_config={"valorEstimado": st.column_config.NumberColumn("Estimado (R$)", format="localized"),
                                    "valorHomologado": st.column_config.NumberColumn("Homologado (R$)", format="localized"),
                                    "razao": st.column_config.NumberColumn("Razão", format="%.2f")})

    # 3. fornecedores
    st.subheader("3. Concentração de fornecedores (contratos no PNCP)")
    k = ler("pncp_contratos.csv")
    if k is None:
        faltando("pncp_contratos.csv", "coleta/pncp.py")
    else:
        k["valorGlobal"] = pd.to_numeric(k["valorGlobal"], errors="coerce").fillna(0)
        kf = k if todos else k[k["ano"] == ANO]
        if kf.empty:
            st.info(f"Sem contratos publicados no PNCP para {rotulo}.")
        else:
            conc = concentracao_fornecedores(kf)
            top5 = conc.head(5)["participacao"].sum()
            kpis([("Contratos", num(len(kf))), ("Fornecedores distintos", num(len(conc))),
                  ("Participação dos 5 maiores", pct(top5)),
                  ("HHI", num(hhi(conc["participacao"])), "Acima de 2.500 = alta concentração (referência usual)")])
            grafico(px.bar(conc.head(10).sort_values("valor"), x="valor", y="fornecedor", orientation="h",
                           title="10 maiores fornecedores por valor global", labels={"valor": "R$", "fornecedor": ""}), "x")

    # 4. fracionamento
    st.subheader("4. Objetos repetidos perto do limite de dispensa (possível fracionamento)")
    fr = possivel_fracionamento(f)
    st.caption("Limite do art. 75, II da Lei 14.133/2021: R$ 59.906,02 (2024), R$ 62.725,59 (2025), "
               "R$ 65.492,11 (2026). Para 2023, o valor do decreto não foi verificado; usamos o de 2024 como "
               "referência. O limite legal é anual por **natureza** da despesa; o agrupamento aqui é aproximado "
               "(primeiras palavras do objeto).")
    if fr.empty:
        st.success("Nenhum grupo encontrado no recorte.")
    else:
        st.markdown(f"{num(len(fr))} grupos de dispensas com objeto parecido cuja soma no ano supera o limite.")
        st.dataframe(fr, width="stretch", hide_index=True,
                     column_config={c_: st.column_config.NumberColumn(format="localized")
                                    for c_ in ("soma", "maior", "limite")})

    # 5. gasto alto x poucas contratações
    st.subheader("5. Áreas com gasto alto e poucas contratações no PNCP")
    d = despesa_por_funcao()
    if d is None:
        return faltando("siconfi_rreo_anexo02.csv", "coleta/siconfi.py")
    anos = sorted(set(c["ano"]) & set(d["exercicio"])) if todos else [ANO]
    gasto = d[d["exercicio"].isin(anos)].groupby("area", as_index=False)["valor"].sum()
    contr = c[c["ano"].isin(anos)].groupby("area", as_index=False).agg(
        contratacoes=("objeto", "size"), homologado=("valorHomologado", "sum"))
    m = gasto.merge(contr, on="area", how="left").fillna({"contratacoes": 0, "homologado": 0})
    m["homologado_por_gasto"] = 100 * m["homologado"] / m["valor"]
    m = m.sort_values("valor", ascending=False)
    grafico(px.scatter(m, x="valor", y="contratacoes", size="valor", color="area", text="area",
                       title="Gasto liquidado (SICONFI) × nº de contratações (PNCP)",
                       labels={"valor": "Gasto liquidado (R$)", "contratacoes": "Contratações no PNCP", "area": ""}), "x")
    st.dataframe(m, width="stretch", hide_index=True,
                 column_config={"valor": st.column_config.NumberColumn("Gasto liquidado (R$)", format="localized"),
                                "homologado": st.column_config.NumberColumn("Homologado PNCP (R$)", format="localized"),
                                "homologado_por_gasto": st.column_config.NumberColumn("PNCP / gasto (%)", format="%.1f")})
    st.caption("Grande parte do gasto em saúde e educação é folha de pagamento e não passa por licitação; "
               "veja a página Conciliação para uma estimativa que desconta pessoal.")
