# Goianápolis em Números

**No ar:** https://goianapolis-em-numeros.streamlit.app

Painel público e gratuito com dados abertos da Prefeitura de Goianápolis (GO), código IBGE 5208400.
Feito em Python + Streamlit + Plotly.

**Contato:** maurolpx@hotmail.com

## Áreas cobertas (13)
Despesas, receitas, IPTU, ISS, saúde, educação, assistência social, segurança, meio ambiente,
infraestrutura, cultura, esporte e mobilidade urbana.

Todas as áreas têm o gasto municipal (SICONFI, despesa por função). Segurança, mobilidade, cultura,
esporte e meio ambiente não têm indicadores municipais de resultado. IPTU, ISS e ITBI vêm da DCA
(anual) do SICONFI. Detalhes em `docs/esboco.md`.

## Páginas
Visão geral · Despesas (filtro por função de governo) · Receitas e tributos (IPTU/ISS/ITBI) · Pessoal (LRF) ·
Transferências (emendas especiais) · Compras (filtro por unidade/órgão do PNCP) · Saúde · Educação ·
Demais áreas · **Com o que foi gasto** · **Alertas** · **Auditoria** · **Conciliação** · **Fornecedores** · **Projeção** · **Capilaridade** · **Denúncia anônima** · Sobre os dados.

A página **Denúncia anônima** não grava, envia nem registra nada: apenas monta um texto na tela e aponta para os canais oficiais (TCM-GO, Fala.BR/CGU, MPGO).

O **ano** escolhido na barra lateral vale para todas as páginas.

### Auditoria e Conciliação: leia antes
Essas páginas mostram **pontos de atenção e indícios para verificação**, gerados por regras automáticas
(participação de dispensa/inexigibilidade, outliers homologado/estimado por IQR, concentração de fornecedores,
objetos repetidos perto do limite de dispensa, gap entre gasto contratável estimado e contratações no PNCP).
**Não são acusações.** O PNCP só tem cobertura razoável a partir de 2023/2024 e o SICONFI é agregado por
função, então não existe correspondência linha a linha entre gasto e contratação.

## Fontes
- SICONFI / Tesouro Nacional: RREO Anexos 01 e 02, DCA Anexo I-C e RGF Anexo 01 (API)
- PNCP: contratações e contratos (API)
- IBGE: Censo 2022 e estimativas de população (API)
- Transferegov: transferências especiais (API)

Não integradas (testadas sem sucesso): INEP/IDEB, DATASUS/FNS/FNDE, API do Portal da Transparência
federal (exige chave), RREO Anexos 08 e 12.

Lista completa em `dados/fontes.md`.

## Como rodar
```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python coleta/siconfi.py        # RREO Anexos 01 e 02
python coleta/siconfi_extra.py  # DCA (IPTU/ISS/ITBI e despesa por elemento) e RGF (pessoal)
python coleta/siconfi_msc.py    # MSC: despesa por área × item × fonte (folha por área)
python coleta/pncp.py           # contratações e contratos
python coleta/ibge.py           # população
python coleta/transferegov.py   # transferências especiais
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

## Privacidade
CPFs de fornecedores pessoa física (e o CPF embutido no nome de MEIs) são mascarados na coleta
(`coleta/privacidade.py`), no formato ***.456.789-**. CNPJs são mantidos.

## Estrutura
- `app.py`: painel e páginas principais
- `ui.py`: tema Plotly, cartões de KPI e formato brasileiro (R$ 1.234,56)
- `analises.py`: regras da Auditoria (classificação por área, IQR, fracionamento, concentração)
- `pagina_auditoria.py`, `pagina_conciliacao.py`: páginas de auditoria e conciliação
- `.streamlit/config.toml`: tema visual
- `coleta/`: scripts de coleta das APIs
- `dados/`: CSVs e lista de fontes
- `docs/esboco.md`: esboço do painel e o levantamento de fontes
