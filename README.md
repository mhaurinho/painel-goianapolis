# Goianápolis em Números

Painel público e gratuito com dados abertos da Prefeitura de Goianápolis (GO), código IBGE 5208400.
Feito em Python + Streamlit + Plotly.

**Contato:** maurolpx@hotmail.com

## Áreas cobertas (13)
Despesas, receitas, IPTU, ISS, saúde, educação, assistência social, segurança, meio ambiente,
infraestrutura, cultura, esporte e mobilidade urbana.

Todas as áreas têm o gasto municipal (SICONFI, despesa por função). Segurança, mobilidade, cultura,
esporte e meio ambiente não têm indicadores municipais de resultado. IPTU e ISS detalhados dependem
da DCA anual, que ainda não está integrada. Detalhes em `docs/esboco.md`.

## Fontes
- SICONFI / Tesouro Nacional: RREO Anexos 01 e 02 (API)
- PNCP: contratações públicas (API)
- IBGE: população do Censo 2022

Lista completa em `dados/fontes.md`.

## Como rodar
```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python coleta/siconfi.py   # gera dados/siconfi_rreo_anexo01.csv e anexo02.csv
python coleta/pncp.py      # gera dados/pncp_contratacoes.csv
streamlit run app.py
```

## Publicar no Streamlit Community Cloud (grátis)
1. Crie um repositório no GitHub e envie este projeto (branch `main`), incluindo os CSVs de `dados/`.
2. Acesse https://share.streamlit.io e clique em **Sign in with GitHub**.
3. Clique em **New app** (ou "Create app" > "Deploy a public app from GitHub").
4. Escolha o repositório, branch **main** e arquivo principal **app.py**.
5. Clique em **Deploy**. Atalho direto: https://share.streamlit.io/deploy?repository=mhaurinho/painel-goianapolis&branch=main&mainModule=app.py
   O site fica em um endereço `*.streamlit.app`.
6. Para atualizar os dados, rode os scripts de coleta e faça commit e push dos CSVs. O app reinicia sozinho.

## Estrutura
- `app.py`: painel com as páginas Visão geral, Despesas, Receitas, Compras, Saúde, Educação, Demais áreas e Sobre os dados
- `coleta/`: scripts de coleta das APIs
- `dados/`: CSVs e lista de fontes
- `docs/esboco.md`: esboço do painel e o levantamento de fontes

## Deploy em VPS própria
Veja `deploy/README-VPS.md` (systemd + nginx na porta 8080).
