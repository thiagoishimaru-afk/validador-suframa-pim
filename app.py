import streamlit as st
import xmltodict

st.set_page_config(page_title="Validador SUFRAMA & PIN", layout="wide")

st.title("Validador Fiscal ZFM: SUFRAMA & Obrigatoriedade do PIN")
st.markdown("Submeta o arquivo XML da NF-e para verificar a necessidade de emissão do PIN-e.")

# Upload do arquivo XML
uploaded_file = st.file_uploader("Suba o arquivo XML da NF-e", type=["xml"])

if uploaded_file is not None:
    try:
        data = xmltodict.parse(uploaded_file.read())
        
        # Trata estruturas nfeProc ou NFe direto
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
        uf_dest = destinatario.get('enderDest', {}).get('UF', '')
        
        # Leitura dos Itens / Produtos para checar CFOP e benefícios
        detalhes = infNFe.get('det', [])
        if not isinstance(detalhes, list):
            detalhes = [detalhes]

        produtos_analisados = []
        tem_incentivo_fiscal = False
        
        for det in detalhes:
            prod = det.get('prod', {})
            imposto = det.get('imposto', {})
            
            nome_prod = prod.get('xProd', 'Produto sem nome')
            ncm = prod.get('NCM', 'N/D')
            cfop = prod.get('CFOP', 'N/D')
            
            # Verifica se há desoneração de ICMS/IPI/PIS/COFINS no item
            icms = imposto.get('ICMS', {})
            vICMSDeson = 0.0
            for k, v in icms.items():
                if isinstance(v, dict) and 'vICMSDeson' in v:
                    vICMSDeson = float(v.get('vICMSDeson', 0))
            
            if vICMSDeson > 0 or isuf != 'Não informado':
                tem_incentivo_fiscal = True
                
            produtos_analisados.append({
                "produto": nome_prod,
                "ncm": ncm,
                "cfop": cfop,
                "desoneracao": vICMSDeson
            })

        # Exibição dos Dados Extraídos
        st.subheader("📋 Dados Gerais da Operação Extraídos do XML")
        col1, col2, col3 = st.columns(3)
        col1.metric("CNPJ Destinatário", cnpj_dest)
        col2.metric("Inscrição SUFRAMA (ISUF)", isuf)
        col3.metric("UF de Destino", uf_dest)

        # Região de Abrangência da SUFRAMA
        ufs_suframa = ['AM', 'AC', 'RO', 'RR', 'AP']
        
        # --- LÓGICA DE VALIDAÇÃO DA REGRA DO PIN ---
        st.subheader("🔍 Parecer Técnico de Validação do PIN")
        
        if uf_dest not in ufs_suframa:
            st.info("ℹ️ **PIN DISPENSADO**: A UF de destino da mercadoria não faz parte da Região de Abrangência da SUFRAMA.")
        elif isuf == 'Não informado':
            st.warning("⚠️ **PIN NÃO PERMITIDO / DISPENSADO**: O destinatário não possui Inscrição SUFRAMA (ISUF) informada no XML ou não está habilitado.")
        elif tem_incentivo_fiscal or uf_dest in ufs_suframa:
            st.success("✅ **PIN-e OBRIGATÓRIO**: A operação destina-se à área incentivada e possui Inscrição SUFRAMA / desoneração fiscal atrelada. É necessária a geração do PIN no sistema SINAL da Suframa.")
        else:
            st.info("ℹ️ **PIN DISPENSADO**: A Nota Fiscal não possui desoneração ou incentivos fiscais aplicados aos produtos.")

        # Exibição da tabela de itens
        st.subheader("📦 Itens Analisados no XML")
        st.dataframe(produtos_analisados)

    except Exception as e:
        st.error(f"Erro ao processar o arquivo XML: {e}")
