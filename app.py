import streamlit as st
import xmltodict
import requests
import pandas as pd
import os
import time
import json

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
st.sidebar.info("Módulo de Consulta Automatizada da SUFRAMA via CNPJá e Validação do PIN-e.")

# TOKEN CONFIGURADO DA VIRBAC
TOKEN_CONFIGURADO = "6990e991-24ae-4dff-99ae-ede83c192f80-9445ff19-2f86-4d58-92ba-dfa2143724df"

# Cabeçalho do Topo
st.markdown("""
    <div class="main-header">
        <div class="main-title">VIRBAC | Validador Fiscal ZFM & SUFRAMA</div>
        <div class="main-subtitle">Análise por Produto, Diagnóstico PIN-e e Visualizador de Dados CNPJá</div>
    </div>
""", unsafe_allow_html=True)

# Função para extrair dados da SUFRAMA diretamente da estrutura JSON enviada pela CNPJá
def extrair_detalhes_cnpja(json_data, cnpj_alvo):
    cnpj_limpo = ''.join(filter(str.isdigit, str(cnpj_alvo)))
    itens = json_data if isinstance(json_data, list) else [json_data]
    
    for item in itens:
        if isinstance(item, dict):
            tax_id = ''.join(filter(str.isdigit, str(item.get('taxId', ''))))
            
            if not cnpj_limpo or tax_id == cnpj_limpo or len(itens) == 1:
                company = item.get('company', {})
                razao_social = company.get('name', item.get('alias', 'N/D'))
                status_empresa = item.get('status', {}).get('text', 'Ativa')
                
                list_suframa = item.get('suframa', [])
                
                if list_suframa and len(list_suframa) > 0:
                    suf = list_suframa[0]
                    number = suf.get('number', '')
                    since = suf.get('since', 'N/D')
                    status_obj = suf.get('status', {})
                    status_txt = status_obj.get('text', 'Ativa') if isinstance(status_obj, dict) else str(status_obj)
                    
                    icms_benef, icms_prop, icms_base = "NÃO", "N/D", "N/D"
                    ipi_benef, ipi_prop, ipi_base = "NÃO", "N/D", "N/D"
                    
                    incentivos = suf.get('incentives', [])
                    for inc in incentivos:
                        tributo = str(inc.get('tribute', '')).upper()
                        if tributo == 'ICMS':
                            icms_benef = "SIM"
                            icms_prop = inc.get('purpose', 'N/D')
                            icms_base = inc.get('basis', 'N/D')
                        elif tributo == 'IPI':
                            ipi_benef = "SIM"
                            ipi_prop = inc.get('purpose', 'N/D')
                            ipi_base = inc.get('basis', 'N/D')

                    return {
                        "cnpj": tax_id,
                        "razao_social": razao_social,
                        "status_empresa": status_empresa,
                        "isuf": str(number) if number else "",
                        "situacao_suframa": status_txt.upper(),
                        "dt_cad": since[:10] if since != 'N/D' else 'N/D',
                        "icms_benef": icms_benef, "icms_prop": icms_prop, "icms_base": icms_base,
                        "ipi_benef": ipi_benef, "ipi_prop": ipi_prop, "ipi_base": ipi_base,
                        "json_bruto": item,
                        "sucesso": True if number else False
                    }
                else:
                    return {
                        "cnpj": tax_id,
                        "razao_social": razao_social,
                        "status_empresa": status_empresa,
                        "isuf": "",
                        "situacao_suframa": "SEM REGISTRO SUFRAMA",
                        "dt_cad": "N/D",
                        "icms_benef": "NÃO", "icms_prop": "N/D", "icms_base": "N/D",
                        "ipi_benef": "NÃO", "ipi_prop": "N/D", "ipi_base": "N/D",
                        "json_bruto": item,
                        "sucesso": False
                    }

    return {
        "cnpj": cnpj_limpo, "razao_social": "N/D", "status_empresa": "N/D",
        "isuf": "", "situacao_suframa": "NÃO LOCALIZADO", "dt_cad": "N/D",
        "icms_benef": "NÃO", "icms_prop": "N/D", "icms_base": "N/D",
        "ipi_benef": "NÃO", "ipi_prop": "N/D", "ipi_base": "N/D",
        "json_bruto": {}, "sucesso": False
    }

# Consulta na API CNPJá com Polling de até 40s (8 ciclos x 5s)
@st.cache_data(ttl=3600)
def consultar_suframa_cnpja_api(cnpj):
    cnpj_limpo = ''.join(filter(str.isdigit, str(cnpj)))
    if not cnpj_limpo or len(cnpj_limpo) != 14:
        return extrair_detalhes_cnpja({}, cnpj)
    
    url = f"https://api.cnpja.com/office/{cnpj_limpo}?strategy=cache&maxAge=45&sources=suframa"
    headers = {"Authorization": TOKEN_CONFIGURADO}

    max_tentativas = 8
    delay = 5

    for tentativa in range(max_tentativas):
        try:
            response = requests.get(url, headers=headers, timeout=12)
            
            if response.status_code in [400, 404]:
                url_fallback = f"https://api.cnpja.com/office/{cnpj_limpo}"
                response = requests.get(url_fallback, headers=headers, timeout=12)

            if response.status_code == 200:
                dados = response.json()
                resultado = extrair_detalhes_cnpja(dados, cnpj_limpo)
                
                if resultado["sucesso"]:
                    return resultado
                
                if tentativa < max_tentativas - 1:
                    time.sleep(delay)
                    continue

            elif response.status_code == 202:
                time.sleep(delay)
                continue
            else:
                break
        except Exception:
            time.sleep(delay)
            continue

    return extrair_detalhes_cnpja({}, cnpj)

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
    relatorio_cnpja = []
    
    origens_nacionais = ['0', '3', '4', '5', '8']
    ufs_suframa = ['AM', 'AC', 'RO', 'RR', 'AP']

    progress_bar = st.progress(0)
    status_text = st.empty()
    total_files = len(uploaded_files)

    for index, file in enumerate(uploaded_files):
        status_text.text(f"Consultando fonte SUFRAMA na CNPJá API [{index + 1}/{total_files}]: {file.name}")
        
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

            # 1. CONSULTA NA API CNPJÁ
            dados_cnpja = consultar_suframa_cnpja_api(cnpj_dest)
            isuf_api = dados_cnpja["isuf"]

            # Guarda para a nova aba de Dados Brutos
            relatorio_cnpja.append({
                "Nº NF": numero_nf,
                "CNPJ Destinatário": cnpj_dest,
                "Razão Social": dados_cnpja["razao_social"],
                "ISUF Retornado (API)": isuf_api if isuf_api else "NÃO CADASTRADO / VAZIO",
                "Situação SUFRAMA": dados_cnpja["situacao_suframa"],
                "Data Cadastro SUFRAMA": dados_cnpja["dt_cad"],
                "ICMS Isenção": dados_cnpja["icms_benef"],
                "ICMS Base Legal": dados_cnpja["icms_base"],
                "IPI Isenção": dados_cnpja["ipi_benef"],
                "IPI Base Legal": dados_cnpja["ipi_base"],
                "Estrutura JSON Bruta": json.dumps(dados_cnpja["json_bruto"], ensure_ascii=False, indent=2)
            })

            # LÓGICA DE VALIDAÇÃO (XML x CNPJá API)
            isuf_xml_limpo = ''.join(filter(str.isdigit, str(isuf_xml)))
            isuf_api_limpo = ''.join(filter(str.isdigit, str(isuf_api)))

            if isuf_xml not in ['Não informado', '', None]:
                isuf_exibicao = isuf_xml
                if isuf_api_limpo != "":
                    if isuf_xml_limpo == isuf_api_limpo:
                        status_valida_isuf = "🟢 VÁLIDO (XML coincide com o CNPJá)"
                    else:
                        status_valida_isuf = f"🔴 DIVERGENTE (XML: {isuf_xml} | CNPJá: {isuf_api})"
                else:
                    status_valida_isuf = "🟢 INFORMADO NO XML"
            else:
                if isuf_api_limpo != "":
                    isuf_exibicao = isuf_api
                    status_valida_isuf = "🟡 BUSCADO NO CNPJÁ (Ausente no XML)"
                else:
                    isuf_exibicao = "NÃO INFORMADO NO XML"
                    status_valida_isuf = "🔴 AUSENTE NO XML (Não localizado no CNPJá)"

            # 2. ANÁLISE INTERNA DO PIN ITEM A ITEM
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

                is_nacional = origem in origens_nacionais
                if uf_dest not in ufs_suframa:
                    status_pin_prod = "🟢 DISPENSADO (Fora ZFM)"
                elif "INATIVO" in dados_cnpja["situacao_suframa"] or "IRREGULAR" in dados_cnpja["situacao_suframa"]:
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
                    "Inscrição SUFRAMA Final": isuf_exibicao,
                    "Status Validação ISUF": status_valida_isuf,
                    "Data de Cadastro": dados_cnpja["dt_cad"],
                    "Situação Cadastral": dados_cnpja["situacao_suframa"],
                    "Código Situação Cadastral": "01" if "ATIV" in dados_cnpja["situacao_suframa"] or "HABILIT" in dados_cnpja["situacao_suframa"] else "02",
                    "ICMS Benefício": dados_cnpja["icms_benef"],
                    "ICMS Propósito": dados_cnpja["icms_prop"],
                    "ICMS Base Legal": dados_cnpja["icms_base"],
                    "IPI Benefício": dados_cnpja["ipi_benef"],
                    "IPI Propósito": dados_cnpja["ipi_prop"],
                    "IPI Base Legal": dados_cnpja["ipi_base"],
                    "Arquivo XML": file.name
                })

            relatorio_nfs.append({
                "Nº NF": numero_nf,
                "Valor Total": f"R$ {valor_total_nf:,.2f}",
                "UF": uf_dest,
                "CNPJ Destinatário": cnpj_dest,
                "Inscrição SUFRAMA": isuf_exibicao,
                "Validação Inscrição": status_valida_isuf,
                "Situação Cadastral": dados_cnpja["situacao_suframa"],
                "Itens com PIN": f"{itens_com_pin}/{len(detalhes)}",
                "Diagnóstico NF": "🟡 GERAR PIN" if itens_com_pin > 0 else "🟢 DISPENSADO"
            })

        except Exception as e:
            st.error(f"Erro ao ler arquivo {file.name}: {e}")

        progress_bar.progress((index + 1) / total_files)

    status_text.empty()
    progress_bar.empty()

    # ABAS DA INTERFACE (PRODUTO, NOTA FISCAL E CNPJÁ SUFRAMA)
    tab1, tab2, tab3 = st.tabs([
        "📦 Visão Detalhada POR PRODUTO", 
        "📄 Resumo POR NOTA FISCAL", 
        "🔍 Dados Brutos CNPJá (SUFRAMA)"
    ])

    df_prod = pd.DataFrame(relatorio_produtos)
    df_nf = pd.DataFrame(relatorio_nfs)
    df_cnpja = pd.DataFrame(relatorio_cnpja)

    with tab1:
        st.subheader("📋 Análise Item a Item (Validação SUFRAMA CNPJá & PIN)")
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

    with tab3:
        st.subheader("🔍 Retorno Oficial da API CNPJá (Módulo SUFRAMA)")
        st.info("Esta aba exibe exatamente o que a API do CNPJá entregou para cada CNPJ pesquisado.")
        
        # Exibe a tabela formatada dos dados recebidos
        st.dataframe(df_cnpja.drop(columns=["Estrutura JSON Bruta"]), use_container_width=True)
        
        # Expander para inspecionar a árvore do JSON recebido por nota
        st.markdown("---")
        st.subheader("🌳 Inspeção do JSON Recebido por CNPJ")
        for item in relatorio_cnpja:
            with st.expander(f"CNPJ: {item['CNPJ Destinatário']} | NF: {item['Nº NF']} - {item['Razão Social']}"):
                st.code(item["Estrutura JSON Bruta"], language="json")
