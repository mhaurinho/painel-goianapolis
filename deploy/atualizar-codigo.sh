#!/usr/bin/env bash
# Publica o main do GitHub na VPS. Sem mudança, não faz nada. Se o painel não responder após
# o deploy, volta ao commit anterior. Reinicia SÓ o painel-goianapolis.
set -euo pipefail
# Tudo dentro de main: o bash lê a função inteira antes de executar, então o reset do
# repositório (que troca este próprio arquivo) não afeta a execução em andamento.
main() {
  APP=/opt/painel-goianapolis
  DADOS_COLETADOS=/var/lib/painel-goianapolis/dados
  git_painel() { runuser -u painel -- git -C "$APP" "$@"; }

  git_painel fetch --quiet origin main
  atual=$(git_painel rev-parse HEAD)
  novo=$(git_painel rev-parse origin/main)
  if [[ "$atual" == "$novo" && "${1:-}" != "--forcar" ]]; then
    exit 0
  fi
  echo "Deploy ${atual:0:7} -> ${novo:0:7}"

  aplicar() {
    git_painel reset --quiet --hard "$1"
    if ! git_painel diff --quiet "$atual" "$1" -- requirements.txt || [[ "${2:-}" == pip ]]; then
      runuser -u painel -- "$APP/.venv/bin/pip" install --quiet -r "$APP/requirements.txt"
    fi
    # Bases coletadas na VPS são mais novas que as do repositório: prevalecem.
    if compgen -G "$DADOS_COLETADOS/*.csv" > /dev/null; then
      cp -p "$DADOS_COLETADOS"/*.csv "$APP/dados/"
    fi
    runuser -u painel -- "$APP/.venv/bin/python" -m compileall -q "$APP"/*.py
    systemctl restart painel-goianapolis
  }

  saudavel() {
    for _ in $(seq 1 20); do
      curl -fsS --max-time 3 http://127.0.0.1:8501/_stcore/health > /dev/null 2>&1 && return 0
      sleep 1
    done
    return 1
  }

  if aplicar "$novo" && saudavel; then
    echo "Publicado ${novo:0:7}"
  else
    echo "Falha no deploy de ${novo:0:7}; voltando para ${atual:0:7}" >&2
    aplicar "$atual" pip || true
    saudavel || echo "ATENÇÃO: painel continua fora do ar" >&2
    exit 1
  fi
}
main "$@"; exit $?
