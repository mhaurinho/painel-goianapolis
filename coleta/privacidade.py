"""Mascaramento de CPF (LGPD) antes de gravar bases públicas.

O PNCP publica o CPF de fornecedores pessoa física e o nome empresarial de MEI costuma trazer o CPF do
titular. O painel não precisa do número completo: mantém só os 6 dígitos do meio, como no padrão usado
pelo governo federal (***.456.789-**), o que ainda permite agrupar o mesmo fornecedor. CNPJ não é alterado.
"""
import re

CPF = re.compile(r"(?<![\d./])(\d{3})\.?(\d{3})\.?(\d{3})-?(\d{2})(?![\d/])")


def mascarar_cpf(texto):
    if not isinstance(texto, str):
        return texto
    return CPF.sub(lambda m: f"***.{m.group(2)}.{m.group(3)}-**", texto)


def mascarar_colunas(df, colunas=("fornecedor", "niFornecedor", "objeto")):
    for coluna in colunas:
        if coluna in df:
            df[coluna] = df[coluna].map(mascarar_cpf)
    return df
