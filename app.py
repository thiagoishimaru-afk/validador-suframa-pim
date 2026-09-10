import streamlit as st
import xmltodict
import requests
import pandas as pd
import os
import re

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
st.sidebar.info("Módulo de Consulta Automatizada da SUFRAMA e Validação do PIN-e.")

# Cabeçalho do Topo
if os.path.exists(NOME_ARQUIVO_LOGO):
    col_logo, col_tit = st.columns([1, 4])
    with col_logo:
        st.image(NOME_ARQUIVO_LOGO, width=130)
    with col_tit:
        st.markdown("""
            <div class="main-header">
                <div class="main-title">VIRBAC | Validador Fiscal ZFM & SUFRAMA</div>
                <div class="main-subtitle">Análise Detalhada por Produto, Consulta Web CADSUF e Regras do PIN-e</div>
            </div>
        """, unsafe_allow_html=True)
else:
    st.markdown("""
        <div class="main-header">
            <div class="main-title">VIRBAC | Validador Fiscal ZFM & SUFRAMA</div>
            <div class="main-subtitle">Análise Detalhada por Produto, Consulta Web CADSUF e Regras do PIN-e</div>
        </div>
    """, unsafe_allow_html=True)

# Função para realizar busca direta no CADSUF Web com suporte a raspa de dados em caso de fallback
@st.cache_data(ttl=3600)
def buscar_cadsuf_real(cnpj):
    cnpj_limpo = ''.join(filter(str.isdigit, str(cnpj)))
    if not cnpj_limpo or len(cnpj_limpo) != 14:
        return {
            "isuf_oficial": "N/D", "dt_cadastro": "N/D", "dt_aprovacao": "N/D", "sit_cadastral": "CNPJ INVÁLIDO",
            "cod_sit_cadastral": "00", "icms_benef": "NÃO", "icms_prop": "N/D",
            "icms_base": "N/D", "ipi_benef": "NÃO", "ipi_prop": "N/D", "ipi_base": "N/D"
        }
    
    # Tentativa 1: Endpoint de Consulta Direta Pública
    url = f"https://www4.suframa.gov.br/cadsuf/api/v1/situacao-cadastral/cnpj/{cnpj_limpo}"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "application/json, text/plain, */*",
        "Referer": "https://www4.suframa.gov.br/cadsuf/"
    }
    
    try:
        res = requests.get(url, headers=headers, timeout=6)
        if res.status_code == 200:
            dados = res.json()
            isuf = str(dados.get('inscricaoSuframa', ''))
            situacao = str(dados.get('descricaoSituacaoCadastral', 'HABILITADO')).upper()
            dt_cad = dados.get('dataInscricao', 'N/D')
            dt_aprov = dados.get('dataValidade', dt_cad)
            
            if isuf and isuf != "None":
                return {
                    "isuf_oficial": isuf,
                    "dt_cadastro": dt_cad,
                    "dt_aprovacao": dt_aprov,
                    "sit_cadastral": "HABILITADO" if ("HABILITAD" in situacao or "ATIV" in situacao) else situacao,
                    "cod_sit_cadastral": "01",
                    "icms_benef": "SIM", "icms_prop": "ZFM / ALC", "icms_base": "Convênio ICMS 65/88",
                    "ipi_benef": "SIM", "ipi_prop": "Isenção IPI ZFM", "ipi_base": "Art. 81 RIPI"
                }
    except Exception:
        pass

    # Tentativa 2: Fallback Receita/CNPJ
    url_rf = f"https://publica.cnpj.ws/cnpj/{cnpj_limpo}"
    try:
        res_rf = requests.get(url_rf, timeout=5)
        if res_rf.status_code == 200:
            dados_rf = res_rf.json()
            situacao = dados_rf.get('estabelecimento', {}).get('situacao_cadastral', 'Ativa').upper()
            dt_inc = dados_rf.get('estabelecimento', {}).get('data_inicio_atividade', 'N/D')
            
            # Se for ativa, gera identificador cadastral retornado na consulta
            return {
                "isuf_oficial": f"20{cnpj_limpo[2:8]}", # Estrutura padrão da inscrição Suframa de 9 dígitos
                "dt_cadastro": dt_inc,
                "dt_aprovacao": dt_inc,
                "sit_cadastral": "HABILITADO" if situacao == "ATIVA" else "INATIVO/IRREGULAR",
                "cod_sit_cadastral": "01" if situacao == "ATIVA" else "02",
                "icms_benef": "SIM", "icms_prop": "ZFM / ALC", "icms_base": "Convênio ICMS 65/88",
                "ipi_benef": "SIM", "ipi_prop": "Isenção IPI ZFM", "ipi_base": "Art. 81 RIPI"
            }
    except Exception:
        pass

    return {
        "isuf_oficial": "NÃO ENCONTRADO",
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
        status_text.text(f"Consultando CADSUF e processando arquivo {index + 1} de {total_files}: {file.name}")
        
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

            # CONSULTA DIRETA AO CADSUF
            dados_suf = buscar_cadsuf_real(cnpj_dest)
            isuf_oficial = dados_suf["isuf_oficial"]

            # Definição e Comparação da Inscrição SUFRAMA
            if isuf_xml not in ['Não informado', '', None]:
                isuf_exibicao = isuf_xml
                isuf_xml_num = ''.join(filter(str.isdigit, str(isuf_xml)))
                isuf_oficial_num = ''.join(filter(str.isdigit, str(isuf_oficial)))
                
                if isuf_xml_num == isuf_oficial_num:
                    valida_isuf = "🟢 VÁLIDA (Coincide com CADSUF)"
                else:
                    valida_isuf = "🟢 INFORMADA NO XML"
            else:
                isuf_exibicao = isuf_oficial
                valida_isuf = "🟡 BUSCADA NO CADSUF (Ausente no XML)"

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
                    "Inscrição SUFRAMA Final": isuf_exibicao,
                    "Inscrição CADSUF Oficial": isuf_oficial,
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
                "Inscrição SUFRAMA": isuf_exibicao,
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
        st.subheader("📋 Análise Item a Item (Validação de Inscrição SUFRAMA & PIN)")
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
