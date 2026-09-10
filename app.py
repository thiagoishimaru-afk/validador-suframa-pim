import streamlit as st
import xmltodict
import requests
import pandas as pd
import os

# Configuração da Página
st.set_page_config(
    page_title="Validador SUFRAMA & PIN - Virbac", 
    page_icon="📦",
    layout="wide"
)

# Estilização CSS personalizada (Cores Virbac)
st.markdown("""
    <style>
    .main-header {
        background-color: #003B80;
        padding: 20px;
        border-radius: 8px;
        color: white;
        margin-bottom: 20px;
        border-bottom: 4px solid #E30613;
    }
    .main-title {
        font-size: 26px;
        font-weight: bold;
        margin: 0;
        color: #FFFFFF;
    }
    .main-subtitle {
        font-size: 13px;
        color: #D1E0FF;
        margin-top: 4px;
    }
    </style>
""", unsafe_allow_html=True)

# Logo Virbac
NOME_ARQUIVO_LOGO = "logo.jpg"
if os.path.exists(NOME_ARQUIVO_LOGO):
    st.sidebar.image(NOME_ARQUIVO_LOGO, width=180)
else:
    st.sidebar.markdown("### **VIRBAC**")

st.sidebar.subheader("Painel de Controle")
st.sidebar.info("Módulo de Consulta Automatizada da SUFRAMA e Validação do PIN-e via API CNPJá.")

# CHAVE API CNPJÁ FORNECIDA
TOKEN_CONFIGURADO = "6990e991-24ae-4dff-99ae-ede83c192f80-9445ff19-2f86-4d58-92ba-dfa2143724df"

# Cabeçalho do Topo
st.markdown("""
    <div class="main-header">
        <div class="main-title">VIRBAC | Validador Fiscal ZFM & SUFRAMA</div>
        <div class="main-subtitle">Análise Detalhada por Produto, Consulta CNPJá API e Regras do PIN-e</div>
    </div>
""", unsafe_allow_html=True)

# Função para consultar a API oficial da CNPJá
@st.cache_data(ttl=3600)
def consultar_suframa_cnpja(cnpj):
    cnpj_limpo = ''.join(filter(str.isdigit, str(cnpj)))
    if not cnpj_limpo or len(cnpj_limpo) != 14:
        return {"isuf": "N/D", "situacao": "CNPJ INVÁLIDO", "dt_cad": "N/D"}
    
    url = f"https://api.cnpja.com/office/{cnpj_limpo}"
    headers = {
        "Authorization": TOKEN_CONFIGURADO
    }

    try:
        response = requests.get(url, headers=headers, timeout=8)
        
        if response.status_code == 200:
            dados = response.json()
            
            # Busca inscrição no nó suframa ou no array de inscrições especiais (registrations)
            isuf_encontrado = None
            sit_suframa = "HABILITADO"
            dt_cad = "N/D"

            # 1. Checa objeto direto suframa
            suf = dados.get('suframa', {})
            if isinstance(suf, dict) and suf.get('number'):
                isuf_encontrado = suf.get('number')
                sit_suframa = suf.get('status', 'HABILITADO')
                dt_cad = suf.get('registrationDate', 'N/D')

            # 2. Checa array de inscrições especiais (registrations / inscricoes)
            if not isuf_encontrado:
                registros = dados.get('registrations', []) or dados.get('inscricoes', [])
                for reg in registros:
                    if isinstance(reg, dict):
                        tipo = str(reg.get('type', '')).upper()
                        nome = str(reg.get('name', '')).upper()
                        if 'SUFRAMA' in tipo or 'SUFRAMA' in nome:
                            isuf_encontrado = reg.get('number') or reg.get('numero')
                            sit_suframa = reg.get('status', 'HABILITADO')
                            dt_cad = reg.get('date', 'N/D')
                            break

            status_empresa = str(dados.get('status', {}).get('text', 'ATIVA')).upper()
            is_ativo = "ATIV" in status_empresa or "HABILITAD" in str(sit_suframa).upper()

            return {
                "isuf": str(isuf_encontrado) if isuf_encontrado else "NÃO CADASTRADO",
                "situacao": "HABILITADO" if is_ativo else "INATIVO/IRREGULAR",
                "dt_cad": dt_cad
            }
        elif response.status_code in [401, 403]:
            return {"isuf": "TOKEN INVÁLIDO OU NÃO AUTORIZADO", "situacao": "HABILITADO", "dt_cad": "N/D"}
        else:
            return {"isuf": f"ERRO API ({response.status_code})", "situacao": "HABILITADO", "dt_cad": "N/D"}
            
    except Exception:
        return {"isuf": "TIMEOUT API", "situacao": "HABILITADO", "dt_cad": "N/D"}

# Upload dos XMLs
st.subheader("📤 Upload dos Arquivos XML")
uploaded_files = st.file_uploader(
    "Suba até 50 arquivos XML para análise item a item:", 
    type=["xml"], 
    accept_multiple_files=True
)

if uploaded_files:
    if len(uploaded_files) > 50:
        st.warning("⚠️ Limite de 50 XMLs por lote atingido. Processando os 50 primeiros arquivos.")
        uploaded_files = uploaded_files[:50]

    relatorio_produtos = []
    relatorio_nfs = []
    
    origens_nacionais = ['0', '3', '4', '5', '8']
    ufs_suframa = ['AM', 'AC', 'RO', 'RR', 'AP']

    progress_bar = st.progress(0)
    status_text = st.empty()
    total_files = len(uploaded_files)

    for index, file in enumerate(uploaded_files):
        status_text.text(f"Consultando CNPJá API e processando arquivo {index + 1} de {total_files}: {file.name}")
        
        try:
            data = xmltodict.parse(file.read())
            
            if 'nfeProc' in data:
                nfe_data = data['nfeProc']['NFe']
            elif 'NFe' in data:
                nfe_data = data['NFe']
            else:
                nfe_data = data

            infNFe = nfe_data['infNFe']
            ide = infNFe.get('ide', {})
            destinatario = infNFe.get('dest', {})
            ender_dest = destinatario.get('enderDest', {})
            total = infNFe.get('total', {}).get('ICMSTot', {})

            numero_nf = ide.get('nNF', 'N/D')
            valor_total_nf = float(total.get('vNF', 0.0))
            cnpj_dest = destinatario.get('CNPJ', destinatario.get('CPF', 'Não identificado'))
            isuf_xml = destinatario.get('ISUF', 'Não informado')
            cidade_dest = ender_dest.get('xMun', 'N/D')
            uf_dest = ender_dest.get('UF', 'N/D')

            # CONSULTA API CNPJÁ COM O TOKEN DA VIRBAC
            dados_cnpja = consultar_suframa_cnpja(cnpj_dest)
            isuf_api = dados_cnpja["isuf"]

            # LÓGICA DE VALIDAÇÃO E COMPARATIVO DE INSCRIÇÃO
            isuf_xml_limpo = ''.join(filter(str.isdigit, str(isuf_xml)))
            isuf_api_limpo = ''.join(filter(str.isdigit, str(isuf_api)))

            if isuf_xml not in ['Não informado', '', None]:
                isuf_exibicao = isuf_xml
                if isuf_api_limpo != "" and isuf_api_limpo == isuf_xml_limpo:
                    status_valida_isuf = "🟢 VÁLIDO (XML coincide com a API CNPJá)"
                elif isuf_api_limpo != "" and isuf_api != "NÃO CADASTRADO":
                    status_valida_isuf = f"🔴 DIVERGENTE (XML: {isuf_xml} | API: {isuf_api})"
                else:
                    status_valida_isuf = "🟢 INFORMADO NO XML"
            else:
                if isuf_api_limpo != "":
                    isuf_exibicao = isuf_api
                    status_valida_isuf = "🟡 BUSCADO NA API CNPJá (Preenchido no XML ausente)"
                else:
                    isuf_exibicao = "NÃO INFORMADO NO XML"
                    status_valida_isuf = "🔴 AUSENTE NO XML (CNPJ sem cadastro retornado)"

            # Processamento dos Itens
            detalhes = infNFe.get('det', [])
            if not isinstance(detalhes, list):
                detalhes = [detalhes]

            itens_com_pin = 0

            for n_item, det in enumerate(detalhes, 1):
                prod = det.get('prod', {})
                imposto = det.get('imposto', {})
                icms = imposto.get('ICMS', {})
                
                xProd = prod.get('xProd', 'Sem Descrição')
                ncm = prod.get('NCM', 'N/D')
                cfop = prod.get('CFOP', 'N/D')
                vProd = float(prod.get('vProd', 0.0))

                origem = "N/D"
                for k, v in icms.items():
                    if isinstance(v, dict) and 'orig' in v:
                        origem = str(v.get('orig', 'N/D'))
                        break

                # Regra de Exigência do PIN (Origens 0, 3, 4, 5 e 8)
                is_nacional = origem in origens_nacionais
                if uf_dest not in ufs_suframa:
                    status_pin_prod = "🟢 DISPENSADO (Fora ZFM)"
                elif "INATIVO" in dados_cnpja["situacao"] or "IRREGULAR" in dados_cnpja["situacao"]:
                    status_pin_prod = "🔴 BLOQUEADO (Suframa Inativo)"
                elif is_nacional:
                    status_pin_prod = "🟡 GERAR PIN (Obrigatório)"
                    itens_com_pin += 1
                else:
                    status_pin_prod = "🟢 DISPENSADO (Origem Estrangeira)"

                relatorio_produtos.append({
                    "Nº NF": numero_nf,
                    "Item": n_item,
                    "Descrição Produto": xProd,
                    "NCM": ncm,
                    "CFOP": cfop,
                    "Origem": origem,
                    "Valor Prod (R$)": f"R$ {vProd:,.2f}",
                    "Diagnóstico PIN Produto": status_pin_prod,
                    "Cidade Destino": cidade_dest,
                    "UF": uf_dest,
                    "CNPJ Destinatário": cnpj_dest,
                    "ISUF (XML)": isuf_xml,
                    "ISUF (API CNPJá)": isuf_api,
                    "Inscrição SUFRAMA Final": isuf_exibicao,
                    "Status Validação ISUF": status_valida_isuf,
                    "Data de Cadastro": dados_cnpja["dt_cad"],
                    "Situação Cadastral": dados_cnpja["situacao"],
                    "Código Situação Cadastral": "01" if dados_cnpja["situacao"] == "HABILITADO" else "02",
                    "ICMS Benefício": "SIM" if uf_dest in ufs_suframa else "NÃO",
                    "ICMS Propósito": "Incentivo Fiscal ZFM / ALC",
                    "ICMS Base Legal": "Convênio ICMS 65/88",
                    "IPI Benefício": "SIM" if uf_dest in ufs_suframa else "NÃO",
                    "IPI Propósito": "Isenção IPI ZFM",
                    "IPI Base Legal": "Art. 81 do RIPI/2010",
                    "Arquivo XML": file.name
                })

            relatorio_nfs.append({
                "Nº NF": numero_nf,
                "Valor Total": f"R$ {valor_total_nf:,.2f}",
                "UF": uf_dest,
                "CNPJ Destinatário": cnpj_dest,
                "Inscrição SUFRAMA": isuf_exibicao,
                "Validação Inscrição": status_valida_isuf,
                "Situação Cadastral": dados_cnpja["situacao"],
                "Itens com PIN": f"{itens_com_pin}/{len(detalhes)}",
                "Diagnóstico NF": "🟡 GERAR PIN" if itens_com_pin > 0 else "🟢 DISPENSADO"
            })

        except Exception as e:
            st.error(f"Erro ao ler arquivo {file.name}: {e}")

        progress_bar.progress((index + 1) / total_files)

    status_text.empty()
    progress_bar.empty()

    tab1, tab2 = st.tabs(["📦 Visão Detalhada POR PRODUTO", "📄 Resumo POR NOTA FISCAL"])

    df_prod = pd.DataFrame(relatorio_produtos)
    df_nf = pd.DataFrame(relatorio_nfs)

    with tab1:
        st.subheader("📋 Análise Item a Item (Integração Oficial CNPJá API)")
        st.dataframe(df_prod, use_container_width=True)
        
        csv_prod = df_prod.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="📥 Baixar Relatório Completo de Produtos (CSV / Excel)",
            data=csv_prod,
            file_name="relatorio_produtos_suframa_pin.csv",
            mime="text/csv",
            type="primary"
        )

    with tab2:
        st.subheader("📄 Resumo das Notas Fiscais Processadas")
        st.dataframe(df_nf, use_container_width=True)
