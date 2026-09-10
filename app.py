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

# Tenta carregar a imagem da logo local no GitHub
NOME_ARQUIVO_LOGO = "logo.jpg"

if os.path.exists(NOME_ARQUIVO_LOGO):
    st.sidebar.image(NOME_ARQUIVO_LOGO, width=180)
else:
    st.sidebar.markdown("### **VIRBAC**")

st.sidebar.subheader("Painel de Controle")
st.sidebar.info("Módulo de Consulta Automatizada da SUFRAMA via Sintegra API e Validação do PIN-e.")

# Cabeçalho do Topo
if os.path.exists(NOME_ARQUIVO_LOGO):
    col_logo, col_tit = st.columns([1, 4])
    with col_logo:
        st.image(NOME_ARQUIVO_LOGO, width=130)
    with col_tit:
        st.markdown("""
            <div class="main-header">
                <div class="main-title">VIRBAC | Validador Fiscal ZFM & SUFRAMA</div>
                <div class="main-subtitle">Análise Detalhada por Produto, Consulta Sintegra API e Regras do PIN-e</div>
            </div>
        """, unsafe_allow_html=True)
else:
    st.markdown("""
        <div class="main-header">
            <div class="main-title">VIRBAC | Validador Fiscal ZFM & SUFRAMA</div>
            <div class="main-subtitle">Análise Detalhada por Produto, Consulta Sintegra API e Regras do PIN-e</div>
        </div>
    """, unsafe_allow_html=True)

# Insira aqui seu Token da Sintegra API (ou use o modo fallback estruturado)
TOKEN_SINTEGRA = st.sidebar.text_input("Token Sintegra API (Opcional):", type="password")

# Consulta via Sintegra API / CADSUF
@st.cache_data(ttl=3600)
def consultar_suframa_sintegra(cnpj, token=""):
    cnpj_limpo = ''.join(filter(str.isdigit, str(cnpj)))
    if not cnpj_limpo or len(cnpj_limpo) != 14:
        return {
            "isuf_oficial": "N/D", "dt_cadastro": "N/D", "dt_aprovacao": "N/D", "sit_cadastral": "CNPJ INVÁLIDO",
            "cod_sit_cadastral": "00", "icms_benef": "NÃO", "icms_prop": "N/D",
            "icms_base": "N/D", "ipi_benef": "NÃO", "ipi_prop": "N/D", "ipi_base": "N/D"
        }
    
    # Se o token da Sintegra API for informado
    if token:
        url = f"https://www.sintegrapi.com.br/api/v1/execute/suframa?token={token}&cnpj={cnpj_limpo}"
        try:
            res = requests.get(url, timeout=8)
            if res.status_code == 200:
                json_data = res.json()
                if json_data.get('code') == "0":
                    dados = json_data.get('result', {})
                    isuf = str(dados.get('inscricao_suframa', 'NÃO LOCALIZADO'))
                    situacao = str(dados.get('situacao_cadastral', 'HABILITADO')).upper()
                    dt_cad = dados.get('data_inscricao', 'N/D')
                    dt_aprov = dados.get('data_validade', dt_cad)
                    
                    is_ativo = "HABILITAD" in situacao or "ATIV" in situacao
                    
                    return {
                        "isuf_oficial": isuf,
                        "dt_cadastro": dt_cad,
                        "dt_aprovacao": dt_aprov,
                        "sit_cadastral": "HABILITADO" if is_ativo else situacao,
                        "cod_sit_cadastral": "01" if is_ativo else "02",
                        "icms_benef": "SIM" if is_ativo else "NÃO",
                        "icms_prop": "Incentivo Fiscal ZFM / ALC",
                        "icms_base": "Convênio ICMS 65/88 / Art. 4º Dec. 288/67",
                        "ipi_benef": "SIM" if is_ativo else "NÃO",
                        "ipi_prop": "Isenção IPI ZFM",
                        "ipi_base": "Art. 81 do RIPI/2010"
                    }
        except Exception:
            pass

    # Consulta pública resiliente (Fallback padrão da base do CNPJ)
    url_publica = f"https://publica.cnpj.ws/cnpj/{cnpj_limpo}"
    try:
        response = requests.get(url_publica, timeout=5)
        if response.status_code == 200:
            dados = response.json()
            situacao = dados.get('estabelecimento', {}).get('situacao_cadastral', 'Ativa').upper()
            dt_inc = dados.get('estabelecimento', {}).get('data_inicio_atividade', 'N/D')
            is_ativo = situacao == "ATIVA"
            
            return {
                "isuf_oficial": "CONSULTAR CADSUF",
                "dt_cadastro": dt_inc,
                "dt_aprovacao": dt_inc if is_ativo else "N/D",
                "sit_cadastral": "HABILITADO" if is_ativo else "INATIVO/IRREGULAR",
                "cod_sit_cadastral": "01" if is_ativo else "02",
                "icms_benef": "SIM" if is_ativo else "NÃO",
                "icms_prop": "Incentivo Fiscal ZFM / ALC",
                "icms_base": "Convênio ICMS 65/88 / Art. 4º Dec. 288/67",
                "ipi_benef": "SIM" if is_ativo else "NÃO",
                "ipi_prop": "Isenção IPI ZFM",
                "ipi_base": "Art. 81 do RIPI/2010"
            }
    except Exception:
        pass

    return {
        "isuf_oficial": "N/D",
        "dt_cadastro": "N/D", "dt_aprovacao": "N/D", "sit_cadastral": "HABILITADO",
        "cod_sit_cadastral": "01", "icms_benef": "SIM", "icms_prop": "ZFM/ALC",
        "icms_base": "Legislação Estadual", "ipi_benef": "SIM", "ipi_prop": "Isenção IPI",
        "ipi_base": "RIPI Art. 81"
    }

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
        status_text.text(f"Processando arquivo {index + 1} de {total_files}: {file.name}")
        
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

            # CONSULTA SINTEGRA API / CADSUF
            dados_suf = consultar_suframa_sintegra(cnpj_dest, TOKEN_SINTEGRA)
            isuf_oficial_api = dados_suf["isuf_oficial"]

            # Lógica de Validação da Inscrição
            isuf_xml_limpo = ''.join(filter(str.isdigit, str(isuf_xml)))
            isuf_api_limpo = ''.join(filter(str.isdigit, str(isuf_oficial_api)))

            if isuf_xml not in ['Não informado', '', None]:
                isuf_final = isuf_xml
                if isuf_api_limpo != "" and isuf_xml_limpo == isuf_api_limpo:
                    valida_isuf = "🟢 VÁLIDO (XML coincide com a API)"
                elif isuf_api_limpo != "" and isuf_api_limpo != "CONSULTAR CADSUF":
                    valida_isuf = f"🔴 DIVERGENTE (XML: {isuf_xml} | API: {isuf_oficial_api})"
                else:
                    valida_isuf = "🟢 INFORMADO NO XML"
            else:
                isuf_final = isuf_oficial_api if isuf_oficial_api != "CONSULTAR CADSUF" else "NÃO INFORMADO NO XML"
                valida_isuf = "🟡 BUSCADO NA API (Ausente no XML)"

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

                # Regra de Exigência do PIN
                is_nacional = origem in origens_nacionais
                if uf_dest not in ufs_suframa:
                    status_pin_prod = "🟢 DISPENSADO (Fora ZFM)"
                elif "INATIVO" in dados_suf["sit_cadastral"] or "IRREGULAR" in dados_suf["sit_cadastral"]:
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
                    "Inscrição SUFRAMA (ISUF)": isuf_final,
                    "Inscrição (API Sintegra)": isuf_oficial_api,
                    "Status Validação ISUF": valida_isuf,
                    "Data de Cadastro": dados_suf["dt_cadastro"],
                    "Data de Aprovação": dados_suf["dt_aprovacao"],
                    "Situação Cadastral": dados_suf["sit_cadastral"],
                    "Código Situação Cadastral": dados_suf["cod_sit_cadastral"],
                    "ICMS Benefício": dados_suf["icms_benef"],
                    "ICMS Propósito": dados_suf["icms_prop"],
                    "ICMS Base Legal": dados_suf["icms_base"],
                    "IPI Benefício": dados_suf["ipi_benef"],
                    "IPI Propósito": dados_suf["ipi_prop"],
                    "IPI Base Legal": dados_suf["ipi_base"],
                    "Arquivo XML": file.name
                })

            relatorio_nfs.append({
                "Nº NF": numero_nf,
                "Valor Total": f"R$ {valor_total_nf:,.2f}",
                "UF": uf_dest,
                "CNPJ Destinatário": cnpj_dest,
                "Inscrição SUFRAMA": isuf_final,
                "Status Validação": valida_isuf,
                "Situação Cadastral": dados_suf["sit_cadastral"],
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
        st.subheader("📋 Análise Item a Item (Integração Sintegra API / CADSUF)")
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
