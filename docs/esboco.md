# Goianápolis (GO): fontes de dados públicos e esboço de painel gratuito

Código IBGE 5208400. CNPJ do município: 02.506.012/0001-18 (conforme o PNCP). Verificações feitas em 13/10/2026.
Legenda: ✅ verificado nesta pesquisa · ⚠️ existe, mas não consegui confirmar o conteúdo ou o formato · ❌ não há dado municipal (só estadual ou federal)

## 1. Fontes verificadas

| Fonte | O que tem para Goianápolis | Formato | Atualização | Status |
|---|---|---|---|---|
| Portal da Transparência municipal (Megasoft): https://goianapolis.megasofttransparencia.com.br/ | Portal oficial (despesas, receitas etc.) | O site responde (HTTP 200), mas é uma aplicação em JavaScript. Não consegui ver se dá para exportar CSV | Não verificada | ⚠️ |
| Acesso à Informação da prefeitura: https://acessoainformacao.goianapolis.go.gov.br/ | Pela busca: receitas, dívida ativa, contratos, ordem cronológica de pagamentos, RGF, RREO, balanço, licitações (página "atualizado em 26/02/2026") | HTML e PDF (a confirmar) | Não verificada | ⚠️ (bloqueia acesso automatizado: HTTP 403 via curl) |
| 1Doc (ouvidoria e central de serviços): https://goianapolis.1doc.com.br/b.php?pg=o%2Ftransparencia | Estatísticas de atendimento. Para 01/2026 aparece "Sem dados disponíveis" | HTML | Mensal | ⚠️ |
| **SICONFI / Tesouro (API)**: `https://apidatalake.tesouro.gov.br/ords/siconfi/tt/rreo?an_exercicio=2025&nr_periodo=6&co_tipo_demonstrativo=RREO&no_anexo=RREO-Anexo%2001&id_ente=5208400` | RREO Anexo 01 (receitas e despesas) e **Anexo 02 (despesa por função e subfunção)**, com dados de 2025 para Goianápolis. As funções incluem Saúde, Educação, Assistência Social, Segurança Pública, Gestão Ambiental, Urbanismo, Saneamento, Transporte, Cultura e Desporto e Lazer | **API JSON** | Bimestral (RREO) / quadrimestral (RGF) / anual (DCA) | ✅ |
| **PNCP (API de consulta)**: `https://pncp.gov.br/api/consulta/v1/contratacoes/publicacao?dataInicial=20260101&dataFinal=20261013&codigoModalidadeContratacao=6&codigoMunicipioIbge=5208400&pagina=1` | Contratações de 2026 do MUNICÍPIO DE GOIANÁPOLIS (por exemplo, a compra 06/2026, homologada em R$ 84.100,00) | **API JSON** | Contínua (conforme a prefeitura publica) | ✅ |
| TCM-GO "Acompanhe seu Município": https://www.tcmgo.tc.br/site/portal-da-transparencia/acompanhe-seu-municipio/ | Índices de Saúde, Educação e Pessoal e balancetes | HTML (o site responde, HTTP 200). Não testei a exportação | Não verificada | ⚠️ |
| TCM-GO Portal do Cidadão: https://portalcidadao.tcmgo.tc.br/new-portal-cidadao | Todos os municípios: PPA, LDO, LOA e Observatório (educação, assistência e saúde). Segundo o TCM-GO, permite exportar em vários formatos | Exportação (segundo o TCM-GO) | Não verificada | ⚠️ |
| IBGE API: https://servicodados.ibge.gov.br/api/v1/localidades/municipios/5208400 | Cadastro do município; o Censo 2022 está no SIDRA | API JSON | Censo / estimativas anuais | ✅ |
| INEP (microdados do Censo Escolar): https://www.gov.br/inep/pt-br/acesso-a-informacao/dados-abertos/microdados/censo-escolar | Escolas e matrículas de todos os municípios (é preciso filtrar por 5208400) | CSV (ZIP) | Anual | ✅ página / ⚠️ recorte municipal não testado |
| DATASUS TabNet: http://tabnet.datasus.gov.br | SIH, SIM, SINASC etc. por município | HTML/CSV (TabNet) | Mensal ou anual | ⚠️ (não respondeu no teste, timeout) |
| Portal da Transparência de Goiás: https://transparencia.go.gov.br | **Dados do ESTADO**, não do município. Útil para repasses e para a ação estadual (segurança, por exemplo) | HTML | Não verificada | ✅ site / ❌ municipal |
| Obrasgov / Transferegov | Obras e convênios com recurso federal | API (a confirmar) | Não verificada | ⚠️ (não testei) |

**IPTU e ISS:** não achei a linha "IPTU" com esse nome no RREO Anexo 01 da API. É provável que o detalhamento esteja na **DCA (anual)** do SICONFI, mas ainda falta verificar. Dados por imóvel ou por contribuinte **não são públicos**: dependem de convênio com a prefeitura.

## 2. Cobertura por área de política pública (ordenada pela viabilidade em 1 a 2 semanas)

| # | Área | Dado municipal público | Visualizações | Perguntas respondidas | Viabilidade |
|---|---|---|---|---|---|
| 1 | Despesas (geral e por função) | ✅ SICONFI RREO Anexo 02 (API) | Barras por função; série bimestral; empenhado × liquidado × pago | Quanto se gasta em cada área? Quanto do orçado já foi executado? | Alta |
| 2 | Receitas | ✅ SICONFI RREO Anexo 01 (API) | Previsto × arrecadado; composição (próprias × transferências) | Quanto o município depende de FPM e ICMS? A arrecadação está dentro do previsto? | Alta |
| 3 | Compras e licitações | ✅ PNCP (API) | Tabela com busca; valor por modalidade; principais fornecedores | O que a prefeitura compra, de quem e por qual modalidade? | Alta |
| 4 | Saúde | ✅ gasto (SICONFI, função Saúde) · ⚠️ indicadores (DATASUS, TCM-GO) | Gasto por subfunção (Atenção Básica, Hospitalar); nascimentos e internações por ano | A prefeitura cumpre o mínimo de 15%? Quanto vai para a atenção básica? | Média/alta |
| 5 | Educação | ✅ gasto (SICONFI) · ✅/⚠️ INEP (Censo Escolar, IDEB) | Gasto por subfunção (Infantil, Fundamental); matrículas por etapa; IDEB | O município cumpre o mínimo de 25%? Quantas crianças há na rede? | Média/alta |
| 6 | Assistência social | ✅ gasto (SICONFI: Assistência ao Idoso, à Criança e ao Adolescente, Comunitária) · ⚠️ CadÚnico e Bolsa Família (MDS, não testado) | Gasto por subfunção; famílias no CadÚnico | Quanto se investe e quantas famílias são atendidas? | Média |
| 7 | Infraestrutura / urbanismo / saneamento | ✅ gasto (SICONFI: Urbanismo, Infra-Estrutura Urbana, Saneamento) · ⚠️ obras (PNCP e Obrasgov) | Gasto por ano; lista de contratos de obras | Quanto se investe em cidade e saneamento? Que obras foram contratadas? | Média |
| 8 | Cultura | ✅ gasto (SICONFI: Cultura, Difusão Cultural) · ❌ indicadores municipais | Gasto por ano e per capita | Quanto o município investe em cultura? | Alta (só financeiro) |
| 9 | Esporte e lazer | ✅ gasto (SICONFI: Desporto e Lazer) · ❌ indicadores | Gasto por ano e per capita | Idem | Alta (só financeiro) |
| 10 | Meio ambiente | ✅ gasto (SICONFI: Gestão Ambiental) · ⚠️ dados externos (MapBiomas, INPE), não testados | Gasto; uso do solo (se houver tempo) | Quanto se gasta com meio ambiente? | Média/baixa |
| 11 | Mobilidade urbana / transporte | ✅ gasto (SICONFI: Transporte, Transporte Rodoviário) · ❌ dados municipais de trânsito | Gasto por ano | Quanto se gasta com transporte e estradas? | Alta (só financeiro) |
| 12 | Segurança | ✅ gasto municipal (SICONFI: Segurança Pública, Policiamento) · ❌ criminalidade só estadual (SSP-GO) ou federal, não verificada | Gasto por ano | Quanto a prefeitura gasta com segurança? (A polícia é estadual.) | Baixa para indicadores |
| 13 | IPTU / ISS | ⚠️ total anual provavelmente na DCA (SICONFI) · ❌ nada por imóvel ou contribuinte | Série anual de IPTU e ISS; arrecadação per capita | A arrecadação própria está crescendo? | Média (exige confirmar a DCA) |

**Observação:** o SICONFI garante que **todas** as áreas tenham pelo menos o lado financeiro (quanto se gasta). Indicadores de resultado (crimes, trânsito, qualidade ambiental, frequência em equipamentos de cultura e esporte) não existem em nível municipal ou dependem de dados internos da prefeitura.

## 3. Esboço do painel gratuito ("Goianápolis em Números")

**Páginas:**
1. **Visão geral:** população (IBGE), receita total, despesa total, % aplicado em saúde e em educação, nível de dependência de transferências.
2. **Para onde vai o dinheiro:** treemap ou barras por função (todas as áreas) e evolução anual de 2020 a 2025 (SICONFI Anexo 02).
3. **De onde vem o dinheiro:** receitas próprias × transferências, previsto × realizado (Anexo 01) e IPTU/ISS (DCA, se confirmado).
4. **Compras públicas:** contratações do PNCP com filtros e principais fornecedores.
5. **Saúde:** gasto por subfunção e indicadores do DATASUS.
6. **Educação:** gasto por subfunção e matrículas e IDEB (INEP).
7. **Assistência social, cultura, esporte, meio ambiente, mobilidade e segurança:** página "Demais áreas" com gasto anual e per capita de cada uma, mais o aviso das áreas sem indicador municipal.
8. **Comparação regional:** per capita de Goianápolis comparado com municípios vizinhos de porte parecido. O SICONFI tem os mesmos dados para todos (os municípios exatos ainda não foram escolhidos).
9. **Sobre os dados:** fontes, data da última atualização e limitações.

**Stack sugerida:** Python (requests + pandas) para baixar os dados das APIs do SICONFI e do PNCP e os CSVs do INEP, gravando em Parquet/CSV. Para o painel, **Streamlit** (gratuito no Streamlit Community Cloud, todo o código no GitHub) ou **Looker Studio** (gratuito, alimentado por Google Sheets). O Power BI público ("Publicar na Web") também é uma opção, mas não serve se o painel tiver dados sigilosos. Atualização automática pelo GitHub Actions (agendada após cada bimestre do RREO).

## 4. Plano de trabalho (10 dias úteis)

- **Dia 1:** inventário das fontes. Testar a exportação no Megasoft, no TCM-GO e na DCA do SICONFI (para IPTU e ISS) e baixar uma amostra de cada fonte.
- **Dia 2:** script de coleta do SICONFI (RREO Anexos 01 e 02 de 2020 a 2025, mais a DCA) e tratamento das funções e subfunções.
- **Dia 3:** script do PNCP (paginação, todas as modalidades) e IBGE (população para o cálculo per capita).
- **Dia 4:** INEP (Censo Escolar, recorte 5208400) e DATASUS (SIM, SINASC, SIH via TabNet ou PySUS).
- **Dia 5:** modelo de dados único e checagem dos totais contra os RREOs publicados pela prefeitura.
- **Dia 6:** páginas 1 a 3 (visão geral, despesas, receitas).
- **Dia 7:** páginas 4 a 6 (compras, saúde, educação).
- **Dia 8:** páginas 7 e 8 (demais áreas e comparação regional).
- **Dia 9:** publicação (Streamlit Cloud ou Looker), automação da atualização e página "Sobre os dados".
- **Dia 10:** revisão, texto explicativo e uma apresentação de uma página para levar à prefeitura e à Câmara, incluindo uma proposta da "versão 2", que usaria dados internos (IPTU por imóvel, obras, frota), com contratação nos termos da Lei 14.133/2021.

**Versão mínima em 1 semana:** dias 1 a 3, 5, 6 e 9 (só SICONFI e PNCP), ou seja, despesas por todas as áreas, receitas e compras.

## Pendências (não verificadas)
- Se o portal Megasoft e o site de acesso à informação permitem exportar CSV, e com que frequência são atualizados.
- Se a DCA do SICONFI tem as linhas de IPTU e ISS para Goianápolis.
- Os dados de Goianápolis no DATASUS (TabNet fora do ar no teste), no MDS/CadÚnico, no Obrasgov e na SSP-GO.
- Os formatos de exportação do Portal do Cidadão do TCM-GO.
