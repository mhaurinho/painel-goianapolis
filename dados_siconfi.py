"""Leitura do RREO Anexo 02 (despesa por função/subfunção) em qualquer bimestre e coluna."""
import pandas as pd

# As 28 funções de governo (Portaria MOG 42/1999); as demais linhas do Anexo 02 são subfunções.
FUNCOES = ["Legislativa", "Judiciária", "Essencial à Justiça", "Administração", "Defesa Nacional",
           "Segurança Pública", "Relações Exteriores", "Assistência Social", "Previdência Social", "Saúde",
           "Trabalho", "Educação", "Cultura", "Direitos da Cidadania", "Urbanismo", "Habitação", "Saneamento",
           "Gestão Ambiental", "Ciência e Tecnologia", "Agricultura", "Organização Agrária", "Indústria",
           "Comércio e Serviços", "Comunicações", "Energia", "Transporte", "Desporto e Lazer", "Encargos Especiais"]

AREAS = {
    "Saúde": ["Saúde"], "Educação": ["Educação"], "Assistência social": ["Assistência Social"],
    "Segurança": ["Segurança Pública"], "Meio ambiente": ["Gestão Ambiental"],
    "Infraestrutura/urbanismo": ["Urbanismo", "Saneamento"], "Cultura": ["Cultura"],
    "Esporte e lazer": ["Desporto e Lazer"], "Mobilidade/transporte": ["Transporte"],
    "Administração": ["Administração"], "Agricultura": ["Agricultura"],
}
_INV = {c: a for a, cs in AREAS.items() for c in cs}

LIQUIDADA = "DESPESAS LIQUIDADAS ATÉ O BIMESTRE"
DOTACAO = "DOTAÇÃO ATUALIZADA"


def area_da_funcao(funcao: str) -> str:
    return _INV.get(funcao, "Outras funções")


def funcoes_por_periodo(a2: pd.DataFrame, coluna: str = LIQUIDADA) -> pd.DataFrame:
    """Valor por (exercicio, periodo, funcao), só despesas exceto intraorçamentárias."""
    d = a2[a2["coluna"].astype(str).str.startswith(coluna)]
    if "rotulo" in d:
        d = d[d["rotulo"].astype(str).str.contains("Exceto Intra", case=False)]
    d = d[d["conta"].isin(FUNCOES)]
    f = d.groupby(["exercicio", "periodo", "conta"], as_index=False)["valor"].sum().rename(columns={"conta": "funcao"})
    f["area"] = f["funcao"].map(area_da_funcao)
    return f


def total_por_periodo(a2: pd.DataFrame, coluna: str = LIQUIDADA) -> pd.DataFrame:
    d = a2[a2["coluna"].astype(str).str.startswith(coluna) & a2["conta"].astype(str).str.startswith("DESPESAS (EXCETO INTRA")]
    return d.groupby(["exercicio", "periodo"], as_index=False)["valor"].first()
