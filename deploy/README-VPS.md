# Produção na VPS (Hostinger)

**Fonte da verdade: o branch `main` no GitHub.** Nada é editado direto na VPS: a cada 10 minutos
a VPS confere o GitHub e publica sozinha o que mudou.

```
sua máquina ──git push──▶ GitHub (main) ──timer 10 min──▶ VPS /opt/painel-goianapolis ──▶ nginx :8080
                                                     coleta mensal (IP fixo) ──▶ dados/
```

| Peça | Onde |
|---|---|
| Código | `/opt/painel-goianapolis` (clone do GitHub, dono `painel`) |
| App | `painel-goianapolis.service`: Streamlit em `127.0.0.1:8501`, sempre ativo, sem file watcher, CPU ≤ 150% e RAM ≤ 1,5 GB |
| Proxy | nginx `/etc/nginx/sites-available/painel-goianapolis`, porta **8080**, gzip, cache de `/static/` |
| Deploy | `painel-goianapolis-deploy.timer` → `deploy/atualizar-codigo.sh` (health check e rollback automático) |
| Dados | `painel-goianapolis-coleta.timer` (dia 5, 04:00) → `deploy/coletar-dados.sh` |
| Bases coletadas | `/var/lib/painel-goianapolis/dados` (prevalecem sobre os CSVs do repositório) |

## Instalação (uma vez, como root)
```bash
id painel || useradd --system --home-dir /var/lib/painel-goianapolis --shell /usr/sbin/nologin painel
install -d -o painel -g painel /var/lib/painel-goianapolis
git clone https://github.com/mhaurinho/painel-goianapolis.git /opt/painel-goianapolis
cd /opt/painel-goianapolis && python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
chown -R painel:painel /opt/painel-goianapolis
cp deploy/painel-goianapolis*.service deploy/painel-goianapolis*.timer /etc/systemd/system/
systemctl daemon-reload
systemctl enable --now painel-goianapolis painel-goianapolis-deploy.timer painel-goianapolis-coleta.timer
cp deploy/nginx-painel-goianapolis.conf /etc/nginx/sites-available/painel-goianapolis
ln -sf /etc/nginx/sites-available/painel-goianapolis /etc/nginx/sites-enabled/painel-goianapolis
nginx -t && systemctl reload nginx     # reload suave; nunca "restart"
```

## Operação
```bash
systemctl list-timers 'painel-*'                         # próximos deploys e coletas
journalctl -u painel-goianapolis-deploy -n 30            # últimos deploys
systemctl start painel-goianapolis-coleta                # coletar agora (demora alguns minutos)
journalctl -u painel-goianapolis-coleta -n 50            # o que foi atualizado ou mantido
/opt/painel-goianapolis/deploy/atualizar-codigo.sh --forcar   # republicar o mesmo commit
curl -s http://127.0.0.1:8501/_stcore/health             # ok
```

Se mudar os arquivos `.service`, `.timer` ou o nginx em `deploy/`, copie de novo para
`/etc/systemd/system/` ou `/etc/nginx/` e rode `systemctl daemon-reload` ou `nginx -t && systemctl reload nginx`.
O deploy automático atualiza só o código e as dependências.

**Importante:** não reinicie o nginx nem o docker, e não mexa no pm2 ("eleva-api") nem no site `elevayah`.
