"""Página Projeção: despesa liquidada projetada para o fim do ano × dotação atualizada."""
import pandas as pd
import plotly.express as px
import streamlit as st

from dados_siconfi import DOTACAO, LIQUIDADA, funcoes_por_periodo, total_por_periodo
from ui import brl, brl_curto, cabecalho, faltando, grafico, kpis, ler, num, pct

ANOS_SAZONALIDADE = 3


def _tabela(a2: pd.DataFrame, ano: int):
    liq = funcoes_por_periodo(a2, LIQUIDADA)
    dot = funcoes_por_periodo(a2, DOTACAO)
    p = int(liq.loc[liq["exercicio"] == ano, "periodo"].max())
    # por área + total
    def por_area(df):
        g = df.groupby(["exercicio", "periodo", "area"], as_index=False)["valor"].sum()
        t = df.groupby(["exercicio", "periodo"], as_index=False)["valor"].sum().assign(area="TOTAL")
        return pd.concat([g, t], ignore_index=True)
    L, D = por_area(liq), por_area(dot)
    atual = L[(L["exercicio"] == ano) & (L["periodo"] == p)].set_index("area")["valor"]
    dotacao = D[(D["exercicio"] == ano) & (D["periodo"] == p)].set_index("area")["valor"]
    anteriores = [a for a in sorted(L["exercicio"].unique()) if ano - ANOS_SAZONALIDADE <= a < ano
                  and 6 in set(L.loc[L["exercicio"] == a, "periodo"])]
    # sazonalidade: fração do liquidado anual já atingida no bimestre p, média dos anos anteriores
    fr = []
    for a in anteriores:
        x = L[L["exercicio"] == a].pivot_table(index="area", columns="periodo", values="valor", aggfunc="sum")
        if p in x and 6 in x:
            fr.append((x[p] / x[6]).rename(a))
    frac = pd.concat(fr, axis=1).mean(axis=1) if fr else pd.Series(dtype=float)
    out = pd.DataFrame({"liquidado_ate_bimestre": atual, "dotacao_atualizada": dotacao})
    out["projecao_linear"] = out["liquidado_ate_bimestre"] / p * 6
    out["fracao_historica"] = frac.reindex(out.index).fillna(frac.get("TOTAL"))
    out["projecao_sazonal"] = out["liquidado_ate_bimestre"] / out["fracao_historica"]
    for k in ("linear", "sazonal"):
        out[f"excesso_{k}_pct"] = 100 * (out[f"projecao_{k}"] / out["dotacao_atualizada"] - 1)
    def alerta(r):
        e = [r["excesso_linear_pct"], r["excesso_sazonal_pct"]]
        if all(pd.notna(v) and v > 0 for v in e):
            return "🔴 possível estouro (2 cenários)"
        if any(pd.notna(v) and v > 0 for v in e):
            return "🟡 possível estouro (1 cenário)"
        return "🟢 dentro da dotação"
    out["situacao"] = out.apply(alerta, axis=1)
    out = out.reset_index().rename(columns={"index": "area"})
    return out.sort_values("liquidado_ate_bimestre", ascending=False), p, anteriores


def pagina(ANO: int):
    cabecalho("Projeção orçamentária do ano",
              "Despesa liquidada projetada para dezembro, comparada com a **dotação atualizada**, por área e no total.",
              "SICONFI, RREO Anexo 02 (despesa liquidada e dotação atualizada por função, por bimestre).")
    a2 = ler("siconfi_rreo_anexo02.csv")
    if a2 is None:
        return faltando("siconfi_rreo_anexo02.csv", "coleta/siconfi.py")
    if ANO not in set(a2["exercicio"]):
        return st.info(f"Sem RREO de {ANO}.")
    t, p, anteriores = _tabela(a2, ANO)
    if p == 6:
        st.info(f"{ANO} já está completo (6º bimestre): os valores abaixo mostram a execução final; a projeção é "
                "igual ao realizado. Escolha o ano corrente na barra lateral para ver a projeção.")
    tot = t[t["area"] == "TOTAL"].iloc[0]
    st.markdown(f"""
**Fórmulas** (bimestre atual *p* = {p}):
- **Linear:** projeção = liquidado até o bimestre ÷ {p} × 6. Total: {brl(tot['liquidado_ate_bimestre'])} ÷ {p} × 6 = **{brl(tot['projecao_linear'])}**
- **Sazonal:** projeção = liquidado até o bimestre ÷ *f*, onde *f* é a fração do liquidado anual já atingida no {p}º
  bimestre, em média, nos anos {", ".join(map(str, anteriores)) or "(sem histórico)"}. Total: *f* = {pct(100 * tot['fracao_historica'])}
  → {brl(tot['liquidado_ate_bimestre'])} ÷ {num(tot['fracao_historica'], 4)} = **{brl(tot['projecao_sazonal'])}**
- **Dotação atualizada** (total): {brl(tot['dotacao_atualizada'])}
""")
    kpis([("Liquidado até o bimestre", brl_curto(tot["liquidado_ate_bimestre"]), brl(tot["liquidado_ate_bimestre"])),
          ("Projeção linear", brl_curto(tot["projecao_linear"]), f"{pct(tot['excesso_linear_pct'])} sobre a dotação"),
          ("Projeção sazonal", brl_curto(tot["projecao_sazonal"]), f"{pct(tot['excesso_sazonal_pct'])} sobre a dotação"),
          ("Dotação atualizada", brl_curto(tot["dotacao_atualizada"]), brl(tot["dotacao_atualizada"]))])
    if "estouro" in tot["situacao"]:
        st.error(f"Total: {tot['situacao']}.")
    areas = t[t["area"] != "TOTAL"]
    estouros = areas[areas["situacao"].str.contains("estouro")]
    if not estouros.empty:
        st.warning("Áreas com possível estouro: " + ", ".join(f"{a} ({s.split(' ')[0]})" for a, s in
                                                               zip(estouros["area"], estouros["situacao"])))
    g = areas.melt(id_vars="area", value_vars=["dotacao_atualizada", "projecao_linear", "projecao_sazonal"],
                   var_name="serie", value_name="valor").replace(
        {"dotacao_atualizada": "Dotação atualizada", "projecao_linear": "Projeção linear", "projecao_sazonal": "Projeção sazonal"})
    grafico(px.bar(g, x="valor", y="area", color="serie", barmode="group", orientation="h",
                   title=f"Projeção × dotação por área ({ANO}, base: {p}º bimestre)",
                   labels={"valor": "R$", "area": "", "serie": ""}), "x")
    cfg = {c: st.column_config.NumberColumn(format="localized") for c in
           ("liquidado_ate_bimestre", "dotacao_atualizada", "projecao_linear", "projecao_sazonal")}
    cfg.update({"fracao_historica": st.column_config.NumberColumn("f (sazonal)", format="%.3f"),
                "excesso_linear_pct": st.column_config.NumberColumn("Linear vs dotação (%)", format="%.1f"),
                "excesso_sazonal_pct": st.column_config.NumberColumn("Sazonal vs dotação (%)", format="%.1f")})
    st.dataframe(t, width="stretch", hide_index=True, column_config=cfg)
    st.caption("**Limitações:** a despesa não é linear (13º salário, obras e empenhos concentrados no fim do ano); a "
               "sazonalidade usa só os anos anteriores disponíveis e pode mudar com novos programas; a dotação pode "
               "ser ampliada por créditos adicionais ao longo do ano; áreas sem histórico usam a fração do total. "
               "\"Possível estouro\" significa que, mantido o ritmo, a despesa passaria da dotação atual; não é uma "
               "constatação de irregularidade.")
