"""Depois da coleta: devolve a versão anterior de cada base que encolheu mais de 10% ou ficou ilegível.

Protege contra coleta parcial (API fora do ar, bloqueio por excesso de requisições). Compara com a versão
do último commit. Uso: python coleta/validar.py
"""
import io
import subprocess
import sys
from pathlib import Path

import pandas as pd

RAIZ = Path(__file__).resolve().parent.parent
MINIMO = 0.9  # a base nova precisa ter pelo menos 90% das linhas da anterior


def versao_anterior(caminho: Path):
    r = subprocess.run(["git", "show", f"HEAD:{caminho.relative_to(RAIZ).as_posix()}"], cwd=RAIZ,
                       capture_output=True)
    return r.stdout if r.returncode == 0 else None


def main() -> int:
    devolvidas = 0
    for caminho in sorted((RAIZ / "dados").glob("*.csv")):
        antes = versao_anterior(caminho)
        if antes is None:
            print(f"nova base: {caminho.name}")
            continue
        n_antes = len(pd.read_csv(io.BytesIO(antes)))
        try:
            n_depois = len(pd.read_csv(caminho))
        except Exception as e:  # noqa: BLE001
            n_depois, motivo = 0, f"ilegível ({e})"
        else:
            motivo = f"{n_antes} -> {n_depois} linhas"
        if n_depois < MINIMO * n_antes:
            caminho.write_bytes(antes)
            devolvidas += 1
            print(f"DEVOLVIDA {caminho.name}: {motivo}")
        else:
            print(f"ok {caminho.name}: {motivo}")
    print(f"{devolvidas} base(s) devolvida(s) à versão anterior")
    return 0


if __name__ == "__main__":
    sys.exit(main())
