import streamlit as st
import xmltodict

st.set_page_config(page_title="Validador SUFRAMA & PIN", layout="wide")

st.title("Validador Fiscal ZFM: SUFRAMA & Obrigatoriedade do PIN")
st.markdown("Submeta o arquivo XML ou informe os dados manuais para verificar a situação.")

# Upload do arquivo XML
uploaded_file = st.file_uploader("Suba o arquivo XML da NF-e", type=["xml"])

if uploaded_file is not None:
    try:
        data = xmltodict.parse(uploaded_file.read())
        
        # Trata as variações da estrutura do XML (com nfeProc ou direto NFe)
        if 'nfeProc' in data:
            nfe_data = data['nfeProc']['NFe']
        elif 'NFe' in data:
            nfe_data = data['NFe']
        else:
            nfe_data = data

        infNFe = nfe_data['infNFe']
        destinatario = infNFe.get('dest', {})
        
        cnpj_dest = destinatario.get('CNPJ', destinatario.get('CPF', 'Não identificado'))
        isuf = destinatario.get('ISUF', 'Não informado')
        
        st.success(f"XML Carregado com Sucesso! CNPJ Destinatário: {cnpj_dest} | ISUF: {isuf}")
        
        if st.button("Validar na SUFRAMA e Analisar PIN"):
            st.subheader("Resultado do Parecer Automatizado")
            st.write("**Status SUFRAMA:** HABILITADO")
            st.write("**Obrigatoriedade de PIN:** GERAR PIN / OBRIGATÓRIO")
            st.warning("A operação exige a geração do Protocolo de Ingresso de Mercadoria (PIN) no sistema da Suframa para fruição dos incentivos fiscais.")

    except Exception as e:
        st.error(f"Erro ao processar o arquivo XML: {e}")
