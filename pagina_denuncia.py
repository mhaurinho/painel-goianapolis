"""Página Denúncia anônima: só monta um texto na tela. Não grava, não envia e não registra nada."""
import streamlit as st

from ui import cabecalho

TIPOS = ["Sobrepreço ou superfaturamento", "Fracionamento de despesa / dispensa indevida", "Direcionamento de licitação",
         "Obra paralisada, atrasada ou mal executada", "Serviço pago e não prestado", "Funcionário fantasma / folha",
         "Uso indevido de bens ou veículos públicos", "Nepotismo", "Desvio de recursos de saúde",
         "Desvio de recursos de educação/Fundeb", "Outro"]

CANAIS = [
    ("Ouvidoria do TCM-GO (contas e gestão municipal)", "https://www.tcmgo.tc.br/ouvidoria/",
     "Tem a opção **\"Denúncia anônima\"**, que pede só um e-mail para acompanhamento (você pode usar um e-mail que "
     "não o identifique). O TCM-GO informa que admite denúncias anônimas, mas só apura as que trazem indícios, "
     "tempo/lugar e elementos de convicção. Não use o \"Ticket\" do TCM-GO para denúncia anônima: ele é público. "
     "[Perguntas frequentes](https://www.tcmgo.tc.br/site/o-tcm/perguntas-frequentes/)"),
    ("Fala.BR / CGU (quando envolve dinheiro federal)", "https://falabr.cgu.gov.br/web/manifestacao/criar/selecionar-assunto?anonimo=true&tipo=1",
     "Para recursos federais repassados ao município (convênios, SUS, FNDE, emendas). Escolha **Denúncia → "
     "Continuar sem se identificar**. Segundo a CGU, denúncia anônima não recebe protocolo nem resposta, e o "
     "endereço IP não é registrado. [FAQ da CGU](https://www.gov.br/cgu/pt-br/assuntos/ouvidoria/faq-denuncias)"),
    ("Ouvidoria do MPGO (Ministério Público de Goiás)", "https://www.mpgo.mp.br/ouvidoria/cidadao/manifestacaoCidadaoCadastro3NEW.do?idOuvidoria=7",
     "O formulário da Ouvidoria orienta: **para não ser identificado, preencha o nome como \"Anônimo\"**; a "
     "denúncia anônima só é recebida com elementos suficientes para averiguação. Atenção: o formulário de "
     "[Denúncia](https://www.mpgo.mp.br/denuncia/) do MPGO exige cadastro (permite pedir sigilo dos dados) e "
     "informa que denúncias anônimas por ele só são recebidas presencialmente ou por carta à unidade do MP."),
]


def pagina():
    cabecalho("Denúncia anônima",
              "Monte um texto organizado com o que você viu no painel e envie **você mesmo** por um canal oficial.")
    st.error("**Este painel NÃO recebe denúncias.** Nada do que você digitar aqui é gravado, enviado ou registrado "
             "pelo painel: o texto só aparece na sua tela para você copiar. Ao fechar ou recarregar a página, ele some.")
    st.warning("""
**Proteja sua identidade**
- Sites (inclusive o Streamlit Cloud, onde este painel roda, e os próprios canais oficiais) podem registrar o
  **endereço IP** de quem acessa.
- Use a **opção anônima do canal oficial** (veja abaixo). Se quiser mais proteção, acesse de outra rede (não a do
  trabalho) ou pelo navegador **Tor**.
- **Não coloque dados pessoais** no texto: nome, CPF, cargo, telefone, nem detalhes que só você saberia.
- Descreva fatos verificáveis (o quê, onde, quando, valor, número do contrato/PNCP). Indício não é prova:
  a apuração cabe aos órgãos de controle.
""")
    with st.form("denuncia", clear_on_submit=False, border=True):
        tipo = st.selectbox("Tipo de irregularidade", TIPOS)
        descricao = st.text_area("Descrição dos fatos (sem dados pessoais)", height=180,
                                 placeholder="Ex.: a contratação X foi dividida em várias dispensas no mesmo mês...")
        referencia = st.text_input("Item do painel ou link de referência (opcional)",
                                   placeholder="Ex.: Auditoria > possível fracionamento, ou link do PNCP")
        gerar = st.form_submit_button("Gerar texto")
    if gerar:
        if not descricao.strip():
            st.info("Escreva a descrição dos fatos para gerar o texto.")
        else:
            texto = (f"Município: Goianápolis (GO)\n"
                     f"Tipo de irregularidade: {tipo}\n\n"
                     f"Descrição dos fatos:\n{descricao.strip()}\n\n"
                     f"Referência: {referencia.strip() or 'não informada'}\n"
                     "Fonte dos dados consultados: painel Goianápolis em Números "
                     "(dados públicos do SICONFI/Tesouro Nacional e do PNCP).\n"
                     "Observação: os dados indicam pontos para verificação, não comprovam irregularidade.")
            st.markdown("**Copie o texto abaixo** (ícone no canto do quadro) e cole no canal escolhido:")
            st.code(texto, language=None, wrap_lines=True)

    st.subheader("Canais oficiais que aceitam denúncia anônima")
    for nome, url, nota in CANAIS:
        with st.container(border=True):
            st.link_button(nome, url)
            st.markdown(nota)
    st.caption("Links verificados em 13/10/2026. Imprensa: não encontramos um canal público oficial de denúncias de "
               "veículos de Goiás que pudéssemos confirmar, por isso não listamos nenhum.")
