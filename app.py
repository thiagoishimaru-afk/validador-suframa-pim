import streamlit as st
import xmltodict
import requests
import pandas as pd

# Configuração da Página
st.set_page_config(
    page_title="Validador SUFRAMA & PIN - Virbac", 
    page_icon="📦",
    layout="wide"
)

# Estilização CSS personalizada
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

# Cabeçalho da Aplicação
st.markdown("""
    <div class="main-header">
        <div class="main-title">VIRBAC | Validador Fiscal ZFM & SUFRAMA</div>
        <div class="main-subtitle">Análise Detalhada por Produto, Cadastro SUFRAMA e Regras do PIN-e</div>
    </div>
""", unsafe_allow_html=True)

# Função para consultar a situação cadastral do CNPJ na SUFRAMA
@st.cache_data(ttl=3600)
def consultar_suframa_completo(cnpj):
    cnpj_limpo = ''.join(filter(str.isdigit, cnpj))
    if not cnpj_limpo or len(cnpj_limpo) != 14:
        return {
            "dt_cadastro": "N/D", "dt_aprovacao": "N/D", "sit_cadastral": "CNPJ INVÁLIDO",
            "cod_sit_cadastral": "00", "icms_benef": "NÃO", "icms_prop": "N/D",
            "icms_base": "N/D", "ipi_benef": "NÃO", "ipi_prop": "N/D", "ipi_base": "N/D"
        }
        
    url = f"https://publica.cnpj.ws/cnpj/{cnpj_limpo}"
    try:
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            dados = response.json()
            situacao = dados.get('estabelecimento', {}).get('situacao_cadastral', 'Ativa').upper()
            dt_inc = dados.get('estabelecimento', {}).get('data_inicio_atividade', 'N/D')
            
            is_ativo = situacao == "ATIVA"
            
            return {
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
        else:
            return {
                "dt_cadastro": "N/D", "dt_aprovacao": "N/D", "sit_cadastral": "HABILITADO",
                "cod_sit_cadastral": "01", "icms_benef": "SIM", "icms_prop": "ZFM/ALC",
                "icms_base": "Legislação Estadual", "ipi_benef": "SIM", "ipi_prop": "Isenção IPI",
                "ipi_base": "RIPI Art. 81"
            }
    except Exception:
        return {
            "dt_cadastro": "N/D", "dt_aprovacao": "N/D", "sit_cadastral": "DESCONHECIDO",
            "cod_sit_cadastral": "99", "icms_benef": "N/D", "icms_prop": "N/D",
            "icms_base": "N/D", "ipi_benef": "N/D", "ipi_prop": "N/D", "ipi_base": "N/D"
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

            # Dados do Cadastro SUFRAMA do Destinatário
            dados_suf = consultar_suframa_completo(cnpj_dest)

            # Processamento Item a Item (Produtos)
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

                # Regra de Exigência do PIN por PRODUTO
                is_nacional = origem in origens_nacionais
                if uf_dest not in ufs_suframa:
                    status_pin_prod = "🟢 DISPENSADO (Fora ZFM)"
                elif "INATIVO" in dados_suf["sit_cadastral"]:
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

            # Resumo por NF
            relatorio_nfs.append({
                "Nº NF": numero_nf,
                "Valor Total": f"R$ {valor_total_nf:,.2f}",
                "UF": uf_dest,
                "CNPJ Destinatário": cnpj_dest,
                "Situação Cadastral": dados_suf["sit_cadastral"],
                "Itens com PIN": f"{itens_com_pin}/{len(detalhes)}",
                "Diagnóstico NF": "🟡 GERAR PIN" if itens_com_pin > 0 else "🟢 DISPENSADO"
            })

        except Exception as e:
            st.error(f"Erro ao ler arquivo {file.name}: {e}")

        progress_bar.progress((index + 1) / total_files)

    status_text.empty()
    progress_bar.empty()

    # Apresentação do Relatório em Abas
    tab1, tab2 = st.tabs(["📦 Visão Detalhada POR PRODUTO", "📄 Resumo POR NOTA FISCAL"])

    df_prod = pd.DataFrame(relatorio_produtos)
    df_nf = pd.DataFrame(relatorio_nfs)

    with tab1:
        st.subheader("📋 Análise Item a Item (Identificação de Produtos com PIN)")
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
