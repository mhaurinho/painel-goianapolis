"""Página Capilaridade: detalhamento por órgão/unidade/modalidade e locais citados no objeto das contratações."""
import re

import pandas as pd
import plotly.express as px
import streamlit as st

from analises import contratacoes_validas, normalizar_unidade
from ui import brl, brl_curto, cabecalho, faltando, grafico, kpis, ler, num

# Padrões simples: tipo de local + nome que vem depois (até vírgula, ponto, ponto e vírgula, parêntese ou " - ")
_NOME = r"([A-ZÀ-Ú0-9][\wÀ-ú'.ºª\- ]{2,60}?)(?=,|;|\.|\)|\(| - | e (?:CMEI|CMAI|ESCOLA|UBS)|$)"
PADROES = [
    ("Escola", r"\b(?:ESCOLA|E\.M\.|COL[EÉ]GIO)(?: MUNICIPAL| ESTADUAL)?\s+" + _NOME),
    ("CMEI/CMAI/creche", r"\b(CMEI|CMAI|CRECHE)\s+" + _NOME),
    ("UBS/posto/PSF", r"\b(?:UBS|UNIDADE B[AÁ]SICA DE SA[UÚ]DE|POSTO DE SA[UÚ]DE|PSF|ESF)\s+" + _NOME),
    ("Rua/avenida", r"\b(?:RUA|AVENIDA|AV\.|RODOVIA|ESTRADA)\s+" + _NOME),
    ("Setor/bairro/povoado", r"\b(?:SETOR|BAIRRO|JARDIM|RESIDENCIAL|VILA|POVOADO|DISTRITO)\s+" + _NOME),
]


def link_pncp(numero_controle: str) -> str | None:
    """02506012000118-1-000005/2026 -> https://pncp.gov.br/app/editais/02506012000118/2026/5"""
    m = re.match(r"^(\d{14})-\d-(\d+)/(\d{4})$", str(numero_controle))
    if not m:
        return None
    cnpj, seq, ano = m.groups()
    return f"https://pncp.gov.br/app/editais/{cnpj}/{ano}/{int(seq)}"


_INICIO_INVALIDO = ("DE ", "DO ", "DA ", "DOS ", "DAS ", "MUNICIPAL", "PARA ", "A ", "O ", "OU ", "E ", "QUE ",
                    "TENHA ", "COM ", "EM ", "NO ", "NA ", "SEJA", "ONDE", "POR ")


def extrair_locais(objeto: str) -> list[tuple[str, str]]:
    txt = str(objeto).upper()
    txt = re.sub(r"\bPROF(?:ª|ESSORA|ESSOR)?\.?\s", "PROF ", txt)  # "Prof." não encerra o nome
    txt = re.sub(r"\bPORFESSORA\b", "PROFESSORA", txt)
    achados = []
    for tipo, padrao in PADROES:
        for m in re.finditer(padrao, txt):
            nome = m.group(m.lastindex).strip(" -.'")
            if tipo == "CMEI/CMAI/creche":
                nome = f"{m.group(1)} {nome}"
            if len(nome) >= 4 and not (nome + " ").startswith(_INICIO_INVALIDO) and nome not in ("PROF", "CMEI"):
                achados.append((tipo, nome.title()))
    return list(dict.fromkeys(achados))


def pagina(ANO: int):
    cabecalho("Capilaridade: até onde os dados chegam",
              "Detalhamento das contratações por órgão, unidade e modalidade, e locais citados no texto do objeto.",
              "PNCP (contratações). SICONFI não tem unidade gestora (veja abaixo).")
    st.info("**SICONFI:** os arquivos do RREO, DCA e RGF são **agregados no nível do município** (ente). Não há "
            "campo de unidade gestora, secretaria ou estabelecimento; o menor detalhe é **função/subfunção** "
            "(páginas Despesas e Conciliação). O detalhamento por unidade abaixo vem só do **PNCP**.")
    c = ler("pncp_contratacoes.csv")
    if c is None:
        return faltando("pncp_contratacoes.csv", "coleta/pncp.py")
    c = contratacoes_validas(c).copy()
    todos = st.toggle("Todos os anos", value=False, help=f"Desligado: só contratações de {ANO}.")
    if not todos:
        c = c[c["ano"] == ANO]
    if c.empty:
        return st.info(f"Sem contratações no PNCP para {ANO} (a cobertura começa em 2023).")
    c["valorHomologado"] = pd.to_numeric(c["valorHomologado"], errors="coerce").fillna(0)
    c["valorEstimado"] = pd.to_numeric(c["valorEstimado"], errors="coerce").fillna(0)
    c["valor"] = c["valorHomologado"].where(c["valorHomologado"] > 0, c["valorEstimado"])
    c["unidade"] = c["unidadeOrgao"].map(normalizar_unidade) if "unidadeOrgao" in c else "Não informada"
    c["orgao"] = c.get("orgao", pd.Series("Município", index=c.index)).fillna("Município").astype(str).str.title()
    c["link"] = c["numeroControlePNCP"].map(link_pncp)

    st.subheader("Órgão → unidade → modalidade")
    st.caption("Valor = homologado ou, se ainda não houver, estimado.")
    g = c[c["valor"] > 0]
    fig = px.treemap(g, path=["orgao", "unidade", "modalidade"], values="valor",
                     title="Contratações por órgão, unidade e modalidade")
    fig.update_traces(hovertemplate="%{label}<br>R$ %{value:,.2f}<extra></extra>",
                      texttemplate="%{label}<br>%{percentRoot:.1%}")
    grafico(fig, None)

    st.subheader("Locais citados no objeto")
    st.caption("**Local citado no objeto (extração automática, pode conter erros).** Busca palavras como escola, "
               "CMEI, UBS, rua, setor e bairro no texto da contratação. O valor é o da contratação inteira (pode "
               "atender vários locais).")
    linhas = []
    for _, r in c.iterrows():
        for tipo, nome in extrair_locais(r["objeto"]):
            linhas.append({"tipo": tipo, "local": nome, "ano": r["ano"], "valor": r["valor"],
                           "objeto": r["objeto"], "link": r["link"]})
    if not linhas:
        return st.info("Nenhum local identificado nos objetos do recorte.")
    L = pd.DataFrame(linhas)
    kpis([("Contratações com local citado", num(L["link"].nunique())), ("Locais distintos", num(L["local"].nunique())),
          ("Contratações no recorte", num(len(c)))])
    resumo = L.groupby(["tipo", "local"], as_index=False).agg(contratacoes=("link", "nunique"), valor=("valor", "sum"))
    grafico(px.bar(resumo.sort_values("valor").tail(20), x="valor", y="local", color="tipo", orientation="h",
                   title="Locais mais citados (valor das contratações que os mencionam)",
                   labels={"valor": "R$", "local": "", "tipo": ""}), "x")
    st.dataframe(L.sort_values("valor", ascending=False), width="stretch", hide_index=True,
                 column_config={"valor": st.column_config.NumberColumn("Valor (R$)", format="localized"),
                                "link": st.column_config.LinkColumn("PNCP", display_text="abrir")})
