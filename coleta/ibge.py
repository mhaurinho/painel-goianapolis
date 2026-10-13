"""População de Goianápolis: Censo 2022 (fixo) e estimativas anuais do IBGE (agregado 6579)."""
from pathlib import Path
import pandas as pd
import requests

DADOS = Path(__file__).resolve().parent.parent / "dados"
URL = ("https://servicodados.ibge.gov.br/api/v3/agregados/6579/periodos/2018|2019|2020|2021|2024|2025"
       "/variaveis/9324?localidades=N6%5B5208400%5D")


def main():
    js = requests.get(URL, timeout=90).json()
    serie = js[0]["resultados"][0]["series"][0]["serie"]
    linhas = [{"ano": int(a), "populacao": int(v), "fonte": "IBGE estimativa"} for a, v in serie.items() if v.isdigit()]
    linhas.append({"ano": 2022, "populacao": 13967, "fonte": "IBGE Censo 2022"})
    df = pd.DataFrame(linhas).sort_values("ano")
    DADOS.mkdir(exist_ok=True)
    df.to_csv(DADOS / "ibge_populacao.csv", index=False)
    print(df)


if __name__ == "__main__":
    main()
