"""Regras de classificação e indicadores usados nas páginas Auditoria e Conciliação.

Os resultados são PONTOS DE ATENÇÃO PARA VERIFICAÇÃO, nunca conclusões sobre irregularidades.
"""
import re
import unicodedata

import pandas as pd

# Limite de dispensa por valor (Lei 14.133/2021, art. 75, II), por ano de vigência.
# 2024: Decreto 11.871/2023 · 2025: Decreto 12.343/2024 · 2026: Decreto 12.807/2025 (planalto.gov.br)
LIMITE_DISPENSA = {2024: 59906.02, 2025: 62725.59, 2026: 65492.11}
# 2023: valor do Decreto 11.317/2022 não verificado; usamos o de 2024 como referência conservadora
# (é maior que o de 2023, então só sinaliza grupos que superariam também o limite do ano seguinte).
LIMITE_REFERENCIA_2023 = 59906.02


def limite_dispensa(ano: int) -> float:
    return LIMITE_DISPENSA.get(int(ano), LIMITE_REFERENCIA_2023 if int(ano) <= 2023 else max(LIMITE_DISPENSA.values()))


UNIDADE_AREA = {"FMS": "Saúde", "FME": "Educação", "FMAS": "Assistência social", "FMMA": "Meio ambiente"}

PALAVRAS_AREA = [
    ("Saúde", r"saude|medic|hospital|odont|ubs|farmac|ambulat|exame|vacin|psf|esf\b"),
    ("Educação", r"escol|educa|ensino|merenda|aluno|creche|pedag|transporte escolar|alimentacao escolar"),
    ("Assistência social", r"assistencia social|cras|creas|vulnerab|cesta basica|beneficio eventual"),
    ("Infraestrutura/urbanismo", r"paviment|asfalt|obra|constru|reforma|drenag|iluminac|limpeza urbana|saneam|esgot|engenharia|meio-fio|calcad"),
    ("Mobilidade/transporte", r"veicul|onibus|combust|pneu|frota|estrada|patrol|maquina|rodovi"),
    ("Cultura", r"cultur|festa|evento|show|artist"),
    ("Esporte e lazer", r"esport|quadra|desport|campeonato|lazer"),
    ("Meio ambiente", r"ambient|arboriz|residuo|aterro|coleta de lixo"),
    ("Agricultura", r"agricult|rural|produtor|agro"),
    ("Segurança", r"seguranca|vigilan|guarda|monitoramento"),
]


def _norm(txt: str) -> str:
    txt = unicodedata.normalize("NFKD", str(txt)).encode("ascii", "ignore").decode().lower()
    return re.sub(r"\s+", " ", txt)


def area_pncp(unidade, objeto) -> str:
    """Área aproximada de uma contratação do PNCP: pela unidade (fundos municipais) ou por palavras do objeto."""
    u = str(unidade or "").strip().upper()
    if u in UNIDADE_AREA:
        return UNIDADE_AREA[u]
    o = _norm(objeto)
    for area, padrao in PALAVRAS_AREA:
        if re.search(padrao, o):
            return area
    return "Administração/não identificada"


def chave_objeto(objeto: str, n: int = 6) -> str:
    """Chave simples para agrupar objetos parecidos: primeiras n palavras significativas."""
    pare = {"de", "da", "do", "das", "dos", "para", "e", "a", "o", "em", "com", "por", "no", "na", "aquisicao",
            "contratacao", "empresa", "servicos", "servico", "prestacao", "fornecimento", "visando", "atender",
            "municipio", "goianapolis", "secretaria", "municipal"}
    palavras = [p for p in re.findall(r"[a-z]{3,}", _norm(objeto)) if p not in pare]
    return " ".join(palavras[:n])


def outliers_iqr(df: pd.DataFrame) -> pd.DataFrame:
    """Contratações com razão homologado/estimado atípica.

    Muitas contratações têm razão exatamente 1 (homologado = estimado), o que zera o IQR. Por isso o IQR é
    calculado só sobre as razões diferentes de 1; fora da faixa [Q1-1,5·IQR, Q3+1,5·IQR] é ponto de atenção.
    Homologado acima do estimado (razão > 1) também é sempre sinalizado.
    """
    x = df[(df["valorEstimado"] > 0) & (df["valorHomologado"] > 0)].copy()
    if x.empty:
        return x
    x["razao"] = x["valorHomologado"] / x["valorEstimado"]
    base = x.loc[(x["razao"] - 1).abs() > 1e-6, "razao"]
    if len(base) >= 8:
        q1, q3 = base.quantile([0.25, 0.75])
        iqr = q3 - q1
        lo, hi = q1 - 1.5 * iqr, min(q3 + 1.5 * iqr, 1.0)
    else:
        lo, hi = 0.5, 1.0
    out = x[(x["razao"] < lo) | (x["razao"] > hi + 1e-6)].copy()
    out.attrs["faixa"] = (lo, hi)
    out.attrs["base"] = len(base)
    return out.sort_values("razao")


def possivel_fracionamento(df: pd.DataFrame) -> pd.DataFrame:
    """Dispensas do mesmo ano, com objeto parecido, cada uma abaixo do limite mas cuja soma o supera."""
    d = df[df["modalidade"].astype(str).str.contains("Dispensa", case=False)].copy()
    if d.empty:
        return d
    d["valor"] = d["valorHomologado"].where(d["valorHomologado"] > 0, d["valorEstimado"])
    d["chave"] = d["objeto"].map(chave_objeto)
    d["limite"] = d["ano"].map(limite_dispensa)
    d = d[(d["valor"] > 0) & (d["valor"] < d["limite"]) & (d["chave"] != "")]
    g = (d.groupby(["ano", "chave"])
           .agg(qtd=("valor", "size"), soma=("valor", "sum"), maior=("valor", "max"), limite=("limite", "first"),
                exemplo=("objeto", "first"))
           .reset_index())
    g = g[(g["qtd"] >= 2) & (g["soma"] > g["limite"])]
    return g.sort_values("soma", ascending=False)


def concentracao_fornecedores(contratos: pd.DataFrame) -> pd.DataFrame:
    c = contratos.dropna(subset=["fornecedor"])
    g = c.groupby("fornecedor").agg(contratos=("valorGlobal", "size"), valor=("valorGlobal", "sum")).reset_index()
    total = g["valor"].sum()
    g["participacao"] = 100 * g["valor"] / total if total else 0
    return g.sort_values("valor", ascending=False)


def hhi(participacoes_pct: pd.Series) -> float:
    """Índice Herfindahl-Hirschman (0–10.000)."""
    return float((participacoes_pct ** 2).sum())


SITUACOES_INVALIDAS = ("Revogada", "Anulada", "Suspensa")


def contratacoes_validas(df: pd.DataFrame) -> pd.DataFrame:
    """Remove contratações revogadas, anuladas ou suspensas (não devem entrar em somas de valor)."""
    if "situacao" not in df:
        return df
    return df[~df["situacao"].astype(str).isin(SITUACOES_INVALIDAS)]


def possiveis_duplicidades(df: pd.DataFrame) -> pd.DataFrame:
    """Contratações distintas no PNCP com mesmo ano, objeto e valor estimado (possível publicação em duplicidade)."""
    chave = ["ano", "objeto", "valorEstimado"]
    d = df[df.duplicated(chave, keep=False)].sort_values(chave)
    return d


def qualidade_pncp(c: pd.DataFrame, k: pd.DataFrame | None = None) -> dict:
    pub = pd.to_datetime(c.get("dataPublicacao"), errors="coerce").dt.year
    out = {
        "contratacoes": len(c),
        "invalidas": int(c["situacao"].astype(str).isin(SITUACOES_INVALIDAS).sum()) if "situacao" in c else 0,
        "sem_homologado": int((pd.to_numeric(c["valorHomologado"], errors="coerce").fillna(0) == 0).sum()),
        "ano_diferente_publicacao": int((pub.notna() & (pub != c["ano"])).sum()),
        "duplicidades": int(c.duplicated(["ano", "objeto", "valorEstimado"]).sum()),
        "razao_menor_1pct": int(((pd.to_numeric(c["valorHomologado"], errors="coerce") > 0)
                                 & (pd.to_numeric(c["valorHomologado"], errors="coerce")
                                    < 0.01 * pd.to_numeric(c["valorEstimado"], errors="coerce"))).sum()),
    }
    if k is not None:
        out["contratos"] = len(k)
        out["contratos_sem_compra"] = int((~k["numeroControlePncpCompra"].isin(c["numeroControlePNCP"])).sum())
        out["contratos_abaixo_100"] = int((pd.to_numeric(k["valorGlobal"], errors="coerce") < 100).sum())
    return out
