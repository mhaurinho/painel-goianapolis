# Deploy na VPS (Hostinger)

Método: **venv + systemd + nginx** (sem Docker), ao lado do projeto existente "eleva", que não é alterado.

- Código: `/opt/painel-goianapolis` (git clone deste repositório)
- Usuário de sistema: `painel` (sem login)
- Serviço: `painel-goianapolis.service`, com Streamlit em `127.0.0.1:8501`
- Nginx: arquivo novo `/etc/nginx/sites-available/painel-goianapolis` (link em `sites-enabled`), ouvindo na porta **8080**
- Firewall: `ufw allow 8080/tcp`
- URL pública: `http://187.127.56.56:8080`

## Instalação (feita uma vez)
```bash
id painel || useradd --system --no-create-home --shell /usr/sbin/nologin painel
git clone https://github.com/mhaurinho/painel-goianapolis.git /opt/painel-goianapolis
cd /opt/painel-goianapolis
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
chown -R painel:painel /opt/painel-goianapolis
cp deploy/painel-goianapolis.service /etc/systemd/system/
systemctl daemon-reload && systemctl enable --now painel-goianapolis
cp deploy/nginx-painel-goianapolis.conf /etc/nginx/sites-available/painel-goianapolis
ln -s /etc/nginx/sites-available/painel-goianapolis /etc/nginx/sites-enabled/painel-goianapolis
nginx -t && nginx -s reload     # reload suave; nunca "restart"
ufw allow 8080/tcp
```

## Atualizar dados e código
```bash
cd /opt/painel-goianapolis
sudo -u painel git pull
sudo -u painel .venv/bin/python coleta/siconfi.py
sudo -u painel .venv/bin/python coleta/pncp.py
systemctl restart painel-goianapolis   # reinicia SÓ o painel
```

## Verificação
```bash
systemctl status painel-goianapolis
curl -s http://127.0.0.1:8501/_stcore/health   # ok
curl -sI http://187.127.56.56:8080/
```

**Importante:** não reinicie o nginx nem o docker e não mexa no pm2 ("eleva-api") nem no site `elevayah`.
