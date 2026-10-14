"""Com o que o dinheiro foi gasto: despesa por elemento (DCA Anexo I-D) e compras do PNCP por tipo.

Só pandas (sem Streamlit), para poder ser testado.
"""
import re

import pandas as pd

LIQUIDADAS = "Despesas Liquidadas"
TOLERANCIA = 1.0
_ELEMENTO = re.compile(r"^DO(\d)\.(\d)\.(\d\d)\.(\d\d)\.00\.00$")
_GRUPO = re.compile(r"^DO(\d)\.(\d)\.00\.00\.00\.00$")

GRUPOS = {"3.1": "Pessoal", "3.2": "Juros da dívida", "3.3": "Custeio e serviços",
          "4.4": "Investimentos", "4.5": "Inversões financeiras", "4.6": "Amortização da dívida"}

# Elemento (grupo.modalidade.elemento) -> (nome em linguagem simples, exemplo do que entra ali).
# Nomes oficiais: Portaria Interministerial STN/SOF 163/2001. Sem correspondência, usa o nome oficial.
ELEMENTOS = {
    "1.01": ("Aposentadorias", ""), "1.03": ("Pensões", ""),
    "1.04": ("Contratos temporários", "servidores contratados por tempo determinado"),
    "1.11": ("Salários do funcionalismo", "vencimentos e vantagens fixas dos servidores"),
    "1.13": ("Encargos patronais", "INSS e outras contribuições pagas pela prefeitura sobre a folha"),
    "1.16": ("Outras despesas variáveis de pessoal", "horas extras, plantões"),
    "1.92": ("Pessoal de anos anteriores", "salários de exercícios passados pagos agora"),
    "1.94": ("Indenizações trabalhistas", ""), "1.99": ("Pessoal a classificar", ""),
    "2.21": ("Juros da dívida", ""),
    "3.08": ("Benefícios assistenciais", ""), "3.14": ("Diárias", "viagens a serviço"),
    "3.18": ("Auxílio a estudantes", ""), "3.30": ("Material de consumo",
                                                    "combustível, medicamentos, alimentos, material escolar e de limpeza"),
    "3.31": ("Premiações", "prêmios culturais, artísticos e esportivos"),
    "3.32": ("Distribuição gratuita", "cestas, kits e materiais doados à população"),
    "3.33": ("Passagens e locomoção", ""), "3.34": ("Terceirização de mão de obra",
                                                    "pessoal de empresas contratadas que substitui servidores"),
    "3.35": ("Consultoria", ""), "3.36": ("Serviços de pessoas físicas", "autônomos, aluguel pago a pessoa física"),
    "3.37": ("Locação de mão de obra", "vigilância, limpeza e apoio terceirizados"),
    "3.39": ("Serviços de empresas", "manutenção, locação, eventos, transporte, energia, assessorias"),
    "3.40": ("Tecnologia da informação", "sistemas, internet, telefonia de dados"),
    "3.41": ("Contribuições a entidades", ""), "3.43": ("Subvenções sociais", "repasses a entidades sem fins lucrativos"),
    "3.46": ("Auxílio-alimentação", ""), "3.47": ("Tributos e contribuições", "impostos e taxas pagos pela prefeitura"),
    "3.48": ("Auxílios a pessoas físicas", ""), "3.91": ("Sentenças judiciais", "condenações pagas por ordem da Justiça"),
    "3.92": ("Despesas de anos anteriores", "contas de exercícios passados pagas agora"),
    "3.93": ("Indenizações e restituições", ""),
    "4.51": ("Obras e instalações", "construção, pavimentação, reformas"),
    "4.52": ("Equipamentos e material permanente", "veículos, máquinas, móveis, computadores"),
    "4.61": ("Compra de imóveis", ""), "6.71": ("Pagamento da dívida (principal)", ""),
}


def elementos(dca: pd.DataFrame) -> pd.DataFrame:
    """Despesa liquidada por elemento e ano. Cada grupo ganha uma linha 'não detalhado na DCA' com a diferença
    entre o total do grupo e a soma dos seus elementos, para o total sempre fechar."""
    d = dca[dca["coluna"] == LIQUIDADAS]
    linhas = []
    for _, r in d.iterrows():
        m = _ELEMENTO.match(str(r["cod_conta"]))
        if not m or m.group(4) == "00":
            continue
        cat, grupo, _mod, elem = m.groups()
        chave = f"{grupo}.{elem}"
        nome, exemplo = ELEMENTOS.get(chave, (re.sub(r"^[\d.]+ - ", "", str(r["conta"])), ""))
        linhas.append({"exercicio": int(r["exercicio"]), "grupo": GRUPOS.get(f"{cat}.{grupo}", f"Grupo {cat}.{grupo}"),
                       "codigo": f"{cat}.{grupo}.{_mod}.{elem}", "elemento": nome, "exemplo": exemplo,
                       "oficial": re.sub(r"^[\d.]+ - ", "", str(r["conta"])), "valor": float(r["valor"])})
    e = pd.DataFrame(linhas, columns=["exercicio", "grupo", "codigo", "elemento", "exemplo", "oficial", "valor"])
    # elementos repetidos em modalidades diferentes somam no mesmo nome
    e = e.groupby(["exercicio", "grupo", "elemento", "exemplo"], as_index=False).agg(
        valor=("valor", "sum"), codigo=("codigo", "first"), oficial=("oficial", "first"))
    residuos = []
    for _, r in d.iterrows():
        m = _GRUPO.match(str(r["cod_conta"]))
        if not m:
            continue
        nome = GRUPOS.get(f"{m.group(1)}.{m.group(2)}")
        if not nome:
            continue
        soma = e[(e["exercicio"] == r["exercicio"]) & (e["grupo"] == nome)]["valor"].sum()
        sobra = float(r["valor"]) - soma
        if sobra >= TOLERANCIA:
            residuos.append({"exercicio": int(r["exercicio"]), "grupo": nome, "elemento": f"{nome}: não detalhado na DCA",
                             "exemplo": "valor do grupo sem abertura por elemento", "codigo": "", "oficial": "",
                             "valor": sobra})
    return pd.concat([e, pd.DataFrame(residuos)], ignore_index=True) if residuos else e


def total_dca(dca: pd.DataFrame) -> pd.Series:
    d = dca[(dca["coluna"] == LIQUIDADAS) & (dca["cod_conta"] == "TotalDespesas")]
    return d.groupby("exercicio")["valor"].sum()


def conferencia_dca_rreo(dca: pd.DataFrame, a1: pd.DataFrame) -> pd.DataFrame:
    """Despesa liquidada no balanço anual (DCA) × 6º bimestre do RREO, ano a ano."""
    ult = a1[a1["periodo"] == a1.groupby("exercicio")["periodo"].transform("max")]
    fechados = ult[ult["periodo"] == 6]
    rreo = fechados[fechados["conta"].astype(str).str.startswith("DESPESAS (EXCETO INTRA")
                    & fechados["coluna"].astype(str).str.startswith("DESPESAS LIQUIDADAS ATÉ")].groupby("exercicio")["valor"].first()
    t = pd.DataFrame({"dca": total_dca(dca), "rreo": rreo}).dropna()
    t["diferenca"] = t["dca"] - t["rreo"]
    t["status"] = t["diferenca"].abs().map(lambda x: "ok" if x < TOLERANCIA else "divergente")
    return t.reset_index(names="exercicio")


# Compras do PNCP por tipo, pelo texto do objeto. A primeira categoria que casar vence; ordem importa.
CATEGORIAS_COMPRA = [
    ("Tarifas bancárias e telefonia", r"tarifa|banc[aá]ri|telefon"),
    ("Obras, pavimentação e sinalização", r"\bobras?\b|paviment|asfalt|reforma|constru|drenag|cal[cç]ad|engenharia|"
                                          r"meio[- ]fio|recapeam|sinaliza"),
    ("Saúde e medicamentos", r"medicament|hospital|sa[uú]de|odontol|exame|laborat|oxig[eê]nio|m[eé]dic|enfermag|farm"),
    ("Alimentação e merenda", r"aliment|merenda|g[eê]neros|cesta|lanche|refei[cç]|hortifr|carne|\bp[aã]es?\b"),
    ("Combustível, veículos e transporte", r"combust|gasolina|diesel|etanol|ve[ií]culo|pneu|transporte|[oô]nibus|frete|"
                                           r"mec[aâ]nic|cilindro"),
    ("Eventos e festas", r"festa|evento|show|cavalgada|carnaval|r[eé]veillon|sonoriz|palco|ornament|decora[cç]|rainha|"
                         r"campeonato|locutor|artist|fotograf"),
    ("Educação e material escolar", r"escol|educa[cç]|did[aá]tic|uniform|pedag|creche|ensino"),
    ("Limpeza, manutenção e conservação", r"limpeza|higien|manuten|conserva|ro[cç]agem|jardin|lixo|res[ií]duo|pintura|"
                                          r"soldag|el[eé]tric|ilumina|purificador"),
    ("Tecnologia, cópias e comunicação", r"software|sistema|inform[aá]tic|computa|notebook|internet|tecnolog|licen[cç]a|"
                                         r"impressora|fotoc[oó]pia|publicidade|divulga|faixa"),
    ("Consultoria e serviços profissionais", r"consultor|assessor|advoc|jur[ií]dic|cont[aá]bil|auditor|treinamento|capacita"),
    ("Locação de imóveis e equipamentos", r"loca[cç][aã]o|aluguel|locar"),
    ("Material de expediente e mobiliário", r"expediente|escrit[oó]rio|mob[ií]li|cadeira|mesa|cortina|papel"),
]
_CATEGORIAS = [(n, re.compile(r, re.IGNORECASE)) for n, r in CATEGORIAS_COMPRA]


def categorizar(objeto) -> str:
    texto = str(objeto or "")
    return next((n for n, r in _CATEGORIAS if r.search(texto)), "Outros")
