# Fontes de dados (Goianápolis, IBGE 5208400)

- SICONFI (API RREO): https://apidatalake.tesouro.gov.br/ords/siconfi/tt/rreo?an_exercicio=2025&nr_periodo=6&co_tipo_demonstrativo=RREO&no_anexo=RREO-Anexo%2002&id_ente=5208400
- PNCP (API de consulta): https://pncp.gov.br/api/consulta/v1/contratacoes/publicacao?dataInicial=20260101&dataFinal=20261013&codigoModalidadeContratacao=6&codigoMunicipioIbge=5208400&pagina=1
- Portal da Transparência municipal: https://goianapolis.megasofttransparencia.com.br/
- Acesso à Informação da prefeitura: https://acessoainformacao.goianapolis.go.gov.br/
- 1Doc (ouvidoria): https://goianapolis.1doc.com.br/b.php?pg=o%2Ftransparencia
- TCM-GO, Acompanhe seu Município: https://www.tcmgo.tc.br/site/portal-da-transparencia/acompanhe-seu-municipio/
- TCM-GO, Portal do Cidadão: https://portalcidadao.tcmgo.tc.br/new-portal-cidadao
- IBGE Cidades: https://www.ibge.gov.br/cidades-e-estados/go/goianapolis.html
- IBGE API: https://servicodados.ibge.gov.br/api/v1/localidades/municipios/5208400
- INEP, Censo Escolar: https://www.gov.br/inep/pt-br/acesso-a-informacao/dados-abertos/microdados/censo-escolar
- DATASUS TabNet: http://tabnet.datasus.gov.br
- Portal da Transparência de Goiás (dados do estado): https://transparencia.go.gov.br

## Fontes adicionadas (verificadas em 13/10/2026)
- SICONFI DCA Anexo I-C (IPTU, ISS, ITBI, anual): https://apidatalake.tesouro.gov.br/ords/siconfi/tt/dca?an_exercicio=2024&no_anexo=DCA-Anexo%20I-C&id_ente=5208400
- SICONFI RGF Anexo 01 (pessoal × LRF, quadrimestral): https://apidatalake.tesouro.gov.br/ords/siconfi/tt/rgf?an_exercicio=2025&in_periodicidade=Q&nr_periodo=3&co_tipo_demonstrativo=RGF&no_anexo=RGF-Anexo%2001&co_esfera=M&co_poder=E&id_ente=5208400
- PNCP contratos (fornecedores): https://pncp.gov.br/api/consulta/v1/contratos?dataInicial=20250101&dataFinal=20251231&cnpjOrgao=02506012000118&pagina=1
- IBGE população estimada (agregado 6579): https://servicodados.ibge.gov.br/api/v3/agregados/6579/periodos/2024|2025/variaveis/9324?localidades=N6[5208400]
- Transferegov, transferências especiais: https://api.transferegov.gestao.gov.br/transferenciasespeciais/plano_acao_especial?cnpj_beneficiario_plano_acao=eq.02506012000118

## Testadas sem sucesso
- INEP/IDEB (download.inep.gov.br): sem resposta.
- API do Portal da Transparência federal: exige chave (HTTP 401).
- RREO Anexos 08 (MDE/Fundeb) e 12 (saúde): não disponíveis na API do SICONFI para o município.
- DATASUS, FNS e FNDE: sem API municipal simples verificada.
