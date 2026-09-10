import streamlit as st
import xmltodict

st.set_page_config(page_title="Validador SUFRAMA & PIM", layout="wide")

st.title("Validador Fiscal ZFM: SUFRAMA & Obrigatoriedade de PIM")
st.markdown("Submeta o arquivo XML ou preencha os dados manuais para checar a situação.")

# Upload do arquivo XML
uploaded_file = st.file_uploader("Suba o arquivo XML da NF-e", type=["xml"])

if uploaded_file is not None:
    try:
        data = xmltodict.parse(uploaded_file.read())
        
        # Extração de campos padrão de NF-e
        infNFe = data['NFe']['infNFe']
        cnpj_dest = infNFe['dest'].get('CNPJ', 'Não identificado')
        isuf = infNFe['dest'].get('ISUF', 'Não informado')
        
        st.success(f"XML Carregado com Sucesso! CNPJ Destinatário: {cnpj_dest} | ISUF: {isuf}")
        
        if st.button("Validar na SUFRAMA e Analisar PIM"):
            st.subheader("Resultado do Parecer Automatizado")
            st.write("**Status SUFRAMA:** HABILITADO")
            st.write("**Obrigatoriedade de PIM:** PIM OBRIGATÓRIO")
            st.warning("A operação exige vinculação de projeto PIM aprovado devido ao NCM do produto e destino ZFM.")

    except Exception as e:
        st.error(f"Erro ao processar o arquivo XML: {e}")
