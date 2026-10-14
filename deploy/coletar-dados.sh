#!/usr/bin/env bash
# Coleta as bases numa área separada e só troca as do painel se cada arquivo novo existir e não
# tiver encolhido mais que 10% (protege contra coleta parcial por falha ou bloqueio da API).
set -uo pipefail
APP=/opt/painel-goianapolis
BASE=/var/lib/painel-goianapolis
AREA="$BASE/coleta"
GUARDA="$BASE/dados"

rm -rf "$AREA" && mkdir -p "$AREA/dados" "$GUARDA"
cp -r "$APP/coleta" "$AREA/"
chown -R painel:painel "$BASE"

for script in "$AREA"/coleta/*.py; do
  nome=$(basename "$script")
  [[ "$nome" == municipio.py ]] && continue
  echo "== $nome"
  (cd "$AREA" && runuser -u painel -- timeout 3600 "$APP/.venv/bin/python" "coleta/$nome") || echo "falhou: $nome"
done

trocadas=0
for novo in "$AREA"/dados/*.csv; do
  [[ -e "$novo" ]] || continue
  nome=$(basename "$novo")
  linhas_novo=$(wc -l < "$novo")
  linhas_atual=$(wc -l < "$APP/dados/$nome" 2>/dev/null || echo 0)
  if (( linhas_novo > 1 && linhas_novo * 10 >= linhas_atual * 9 )); then
    install -o painel -g painel -m 644 "$novo" "$GUARDA/$nome"
    install -o painel -g painel -m 644 "$novo" "$APP/dados/.$nome.tmp"
    mv -f "$APP/dados/.$nome.tmp" "$APP/dados/$nome"   # troca atômica
    echo "atualizada: $nome ($linhas_atual -> $linhas_novo linhas)"
    trocadas=$((trocadas + 1))
  else
    echo "mantida: $nome (nova com $linhas_novo linhas, atual com $linhas_atual)"
  fi
done

# O app guarda as bases em cache sem prazo; reiniciar é o que faz os dados novos aparecerem.
(( trocadas > 0 )) && systemctl restart painel-goianapolis
echo "Bases atualizadas: $trocadas"
