"""Hierarquia função → subfunção com todas as etapas da despesa e conferências entre demonstrativos.

Só pandas (sem Streamlit), para poder ser testado. Usa o último bimestre publicado de cada exercício.
"""
import re

import pandas as pd

from dados_siconfi import FUNCOES

# Além das 28 funções, o Anexo 02 traz as reservas como "função" sem subfunções; sem elas, a dotação
# da reserva seria somada como se fosse subfunção de Encargos Especiais.
FUNCOES_ANEXO02 = set(FUNCOES) | {"Reserva de Contingência", "Reserva do RPPS"}
ETAPAS_A2 = {"DOTAÇÃO INICIAL": "orcado", "DOTAÇÃO ATUALIZADA": "autorizado",
             "DESPESAS EMPENHADAS ATÉ O BIMESTRE": "empenhado", "DESPESAS LIQUIDADAS ATÉ O BIMESTRE": "liquidado"}
TOLERANCIA = 1.0  # R$; diferenças menores são arredondamento


def ultimo_bimestre(df: pd.DataFrame) -> pd.DataFrame:
    return df[df["periodo"] == df.groupby("exercicio")["periodo"].transform("max")]


def hierarquia(a2: pd.DataFrame) -> pd.DataFrame:
    """Uma linha por (exercicio, funcao, subfuncao) com orçado, autorizado, empenhado e liquidado.
    subfuncao vazia (None) = linha de total da função."""
    d = ultimo_bimestre(a2)
    if "rotulo" in d:
        d = d[d["rotulo"].astype(str).str.contains("Exceto Intra", case=False)]
    linhas = []
    for prefixo, etapa in ETAPAS_A2.items():
        bloco = d[d["coluna"].astype(str).str.startswith(prefixo)]
        for ano, g in bloco.groupby("exercicio", sort=False):
            funcao = None
            for conta, valor in zip(g["conta"].astype(str), g["valor"]):
                if conta in FUNCOES_ANEXO02:
                    funcao, sub = conta, None
                elif funcao and not conta.upper().startswith(("DESPESAS", "TOTAL")):
                    sub = re.sub(r"^FU\d+ - ", "", conta)  # "FU12 - Demais Subfunções" -> "Demais Subfunções"
                else:
                    funcao = None
                    continue
                linhas.append({"exercicio": int(ano), "funcao": funcao, "subfuncao": sub, "etapa": etapa, "valor": valor})
    if not linhas:
        return pd.DataFrame(columns=["exercicio", "funcao", "subfuncao", *ETAPAS_A2.values()])
    h = pd.DataFrame(linhas).fillna({"subfuncao": ""})
    h = h.pivot_table(index=["exercicio", "funcao", "subfuncao"], columns="etapa", values="valor", aggfunc="sum")
    h = h.reset_index().replace({"subfuncao": {"": None}})
    h.columns.name = None
    return h


def _a1(a1: pd.DataFrame, ano: int, conta_inicio: str, coluna_inicio: str):
    d = ultimo_bimestre(a1)
    x = d[(d["exercicio"] == ano) & d["conta"].astype(str).str.startswith(conta_inicio)
          & d["coluna"].astype(str).str.startswith(coluna_inicio)]["valor"]
    return float(x.iloc[0]) if len(x) and pd.notna(x.iloc[0]) else None


def conferencias(a1: pd.DataFrame, a2: pd.DataFrame, ano: int) -> list[dict]:
    """Testes de consistência entre os demonstrativos. status: ok | divergente | sem dado."""
    res = []

    def comparar(teste, x, y, rx, ry):
        if x is None or y is None:
            res.append({"teste": teste, "status": "sem dado", "detalhe": "Um dos lados não foi publicado."})
            return
        dif = x - y
        res.append({"teste": teste, "status": "ok" if abs(dif) < TOLERANCIA else "divergente",
                    "detalhe": f"{rx} {_r(x)} · {ry} {_r(y)} · diferença {_r(dif)}"})

    h = hierarquia(a2) if a2 is not None else pd.DataFrame()
    h = h[h["exercicio"] == ano] if not h.empty else h
    funcoes = h[h["subfuncao"].isna()] if not h.empty else h
    for etapa, coluna, nome in (("liquidado", "DESPESAS LIQUIDADAS ATÉ", "liquidada"),
                                ("empenhado", "DESPESAS EMPENHADAS ATÉ", "empenhada")):
        soma = float(funcoes[etapa].sum()) if not funcoes.empty and etapa in funcoes else None
        comparar(f"Despesa {nome}: Anexo 01 = soma das funções do Anexo 02",
                 _a1(a1, ano, "DESPESAS (EXCETO INTRA", coluna), soma, "Anexo 01", "Anexo 02")

    if not h.empty and "liquidado" in h:
        subs = h[h["subfuncao"].notna()].groupby("funcao")["liquidado"].sum()
        tot = funcoes.set_index("funcao")["liquidado"].reindex(subs.index)
        ruins = (tot - subs).abs()
        ruins = ruins[ruins >= TOLERANCIA]
        res.append({"teste": "Cada função = soma das suas subfunções", "status": "ok" if ruins.empty else "divergente",
                    "detalhe": f"{len(subs)} funções conferidas" if ruins.empty else "Divergem: " + ", ".join(ruins.index)})

    rec = _a1(a1, ano, "RECEITAS (EXCETO INTRA", "Até o Bimestre")
    cor = _a1(a1, ano, "RECEITAS CORRENTES", "Até o Bimestre")
    cap = _a1(a1, ano, "RECEITAS DE CAPITAL", "Até o Bimestre")
    comparar("Receita total = correntes + capital", rec, None if cor is None else cor + (cap or 0), "Total", "Soma")

    etapas = [("autorizado", "DOTAÇÃO ATUALIZADA"), ("empenhado", "DESPESAS EMPENHADAS ATÉ"),
              ("liquidado", "DESPESAS LIQUIDADAS ATÉ"), ("pago", "DESPESAS PAGAS ATÉ")]
    vals = [(n, _a1(a1, ano, "DESPESAS (EXCETO INTRA", c)) for n, c in etapas]
    quebras = [f"{a} menor que {b}" for (a, va), (b, vb) in zip(vals, vals[1:])
               if va is not None and vb is not None and va + TOLERANCIA < vb]
    res.append({"teste": "Ordem lógica: autorizado ≥ empenhado ≥ liquidado ≥ pago",
                "status": "ok" if not quebras else "divergente",
                "detalhe": "Sequência respeitada" if not quebras else "; ".join(quebras)})
    return res


def _r(v: float) -> str:
    return "R$ " + f"{v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
