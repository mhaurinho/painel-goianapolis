"""Despesa liquidada da MSC com códigos traduzidos: área, subfunção, item de despesa, fonte e órgão.

Só pandas (sem Streamlit), para poder ser testado.
"""
import pandas as pd

from gastos import ELEMENTOS, GRUPOS

FUNCOES = {
    "01": "Legislativa", "02": "Judiciária", "03": "Essencial à Justiça", "04": "Administração",
    "05": "Defesa Nacional", "06": "Segurança Pública", "07": "Relações Exteriores", "08": "Assistência Social",
    "09": "Previdência Social", "10": "Saúde", "11": "Trabalho", "12": "Educação", "13": "Cultura",
    "14": "Direitos da Cidadania", "15": "Urbanismo", "16": "Habitação", "17": "Saneamento", "18": "Gestão Ambiental",
    "19": "Ciência e Tecnologia", "20": "Agricultura", "21": "Organização Agrária", "22": "Indústria",
    "23": "Comércio e Serviços", "24": "Comunicações", "25": "Energia", "26": "Transporte", "27": "Desporto e Lazer",
    "28": "Encargos Especiais", "99": "Reserva de Contingência",
}
# Subfunções da Portaria MOG 42/1999 que aparecem em municípios; as demais mostram o código.
SUBFUNCOES = {
    "031": "Ação Legislativa", "032": "Controle Externo", "061": "Ação Judiciária", "062": "Defesa do Interesse Público",
    "091": "Defesa da Ordem Jurídica", "121": "Planejamento e Orçamento", "122": "Administração Geral",
    "123": "Administração Financeira", "124": "Controle Interno", "125": "Normatização e Fiscalização",
    "126": "Tecnologia da Informação", "127": "Ordenamento Territorial", "128": "Formação de Recursos Humanos",
    "129": "Administração de Receitas", "130": "Administração de Concessões", "131": "Comunicação Social",
    "181": "Policiamento", "182": "Defesa Civil", "183": "Informação e Inteligência",
    "241": "Assistência ao Idoso", "242": "Assistência ao Portador de Deficiência",
    "243": "Assistência à Criança e ao Adolescente", "244": "Assistência Comunitária",
    "271": "Previdência Básica", "272": "Previdência do Regime Estatutário", "273": "Previdência Complementar",
    "274": "Previdência Especial", "301": "Atenção Básica", "302": "Assistência Hospitalar e Ambulatorial",
    "303": "Suporte Profilático e Terapêutico", "304": "Vigilância Sanitária", "305": "Vigilância Epidemiológica",
    "306": "Alimentação e Nutrição", "331": "Proteção e Benefícios ao Trabalhador", "332": "Relações de Trabalho",
    "333": "Empregabilidade", "334": "Fomento ao Trabalho", "361": "Ensino Fundamental", "362": "Ensino Médio",
    "363": "Ensino Profissional", "364": "Ensino Superior", "365": "Educação Infantil",
    "366": "Educação de Jovens e Adultos", "367": "Educação Especial", "368": "Educação Básica",
    "391": "Patrimônio Histórico", "392": "Difusão Cultural", "422": "Direitos Individuais, Coletivos e Difusos",
    "451": "Infraestrutura Urbana", "452": "Serviços Urbanos", "453": "Transportes Coletivos Urbanos",
    "481": "Habitação Rural", "482": "Habitação Urbana", "511": "Saneamento Básico Rural",
    "512": "Saneamento Básico Urbano", "541": "Preservação e Conservação Ambiental", "542": "Controle Ambiental",
    "543": "Recuperação de Áreas Degradadas", "544": "Recursos Hídricos", "601": "Promoção da Produção Vegetal",
    "602": "Promoção da Produção Animal", "605": "Abastecimento", "606": "Extensão Rural", "608": "Promoção da Produção Agropecuária",
    "661": "Promoção Industrial", "691": "Promoção Comercial", "695": "Turismo", "751": "Conservação de Energia", "752": "Energia Elétrica",
    "782": "Transporte Rodoviário", "812": "Desporto Comunitário", "813": "Lazer", "841": "Refinanciamento da Dívida Interna",
    "843": "Serviço da Dívida Interna", "846": "Outros Encargos Especiais", "999": "Reserva de Contingência",
}
ORGAOS = {"10131": "Prefeitura (Executivo)", "20231": "Câmara Municipal"}
PESSOAL_LRF = ("Pessoal",)  # grupo 3.1
TERCEIRIZACAO = "Terceirização de mão de obra"  # 3.3.90.34, conta como pessoal na LRF (art. 18, § 1º)


def fonte_grupo(codigo) -> str:
    """Grupo da fonte de recursos (padrão STN a partir de 2023). 1xxx = do ano; 2xxx = saldo de anos anteriores."""
    c = str(codigo or "").split(".")[0].zfill(4)
    g = c[1:3]
    nome = ("Recursos próprios (livres)" if g in ("50", "51") else
            "Fundeb" if g == "54" else
            "Educação: outros repasses" if g in ("55", "56", "57", "58", "59") else
            "Saúde: repasses do SUS" if g in ("60", "61", "62", "63", "64") else
            "Assistência social: repasses" if g in ("65", "66", "67", "68", "69") else
            "Convênios, emendas e outras transferências" if g in ("70", "71", "72", "73", "74", "75", "76", "77", "78", "79") else
            "Previdência" if g in ("80", "81", "82", "83", "84", "85", "86", "87", "88", "89") else
            "Outras fontes")
    return nome + (" · saldo de anos anteriores" if c.startswith("2") else "")


def preparar(msc: pd.DataFrame) -> pd.DataFrame:
    """Acrescenta nomes legíveis às linhas da MSC."""
    m = msc.copy()
    f = m["funcao"].map(lambda x: str(int(x)).zfill(2) if pd.notna(x) else "")
    s = m["subfuncao"].map(lambda x: str(int(x)).zfill(3) if pd.notna(x) else "")
    n = m["natureza_despesa"].astype(str).str.split(".").str[0].str.zfill(8)
    m["area"] = f.map(lambda c: FUNCOES.get(c, f"Função {c}"))
    m["subarea"] = s.map(lambda c: SUBFUNCOES.get(c, f"Subfunção {c}"))
    m["grupo"] = n.map(lambda c: GRUPOS.get(f"{c[0]}.{c[1]}", f"Grupo {c[0]}.{c[1]}"))
    m["item"] = n.map(lambda c: ELEMENTOS.get(f"{c[1]}.{c[4:6]}", (f"Elemento {c[0]}.{c[1]}.{c[2:4]}.{c[4:6]}", ""))[0])
    m["fonte"] = m["fonte_recursos"].map(fonte_grupo)
    m["orgao"] = m["poder_orgao"].map(lambda x: ORGAOS.get(str(x).split(".")[0], f"Órgão {x}"))
    m["pessoal_lrf"] = m["grupo"].isin(PESSOAL_LRF) | (m["item"] == TERCEIRIZACAO)
    return m


def folha(m: pd.DataFrame) -> pd.DataFrame:
    """Só a despesa que a LRF conta como pessoal: grupo 3.1 + terceirização de mão de obra."""
    return m[m["pessoal_lrf"]]
