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

# Estilização CSS personalizada (Cores Virbac)
st.markdown("""
    <style>
    .main-header {
        background-color: #003B80;
        padding: 20px;
        border-radius: 8px;
        color: white;
        margin-bottom: 25px;
        border-bottom: 4px solid #E30613;
    }
    .main-title {
        font-size: 28px;
        font-weight: bold;
        margin: 0;
        color: #FFFFFF;
    }
    .main-subtitle {
        font-size: 14px;
        color: #D1E0FF;
        margin-top: 5px;
    }
    </style>
""", unsafe_allow_html=True)

# Cabeçalho da Aplicação
st.markdown("""
    <div class="main-header">
        <div class="main-title">VIRBAC | Validador Fiscal ZFM</div>
        <div class="main-subtitle">Consulta de Cadastro SUFRAMA & Obrigatoriedade do PIN-e em Lote</div>
    </div>
""", unsafe_allow_html=True)

# Barra Lateral
st.sidebar.markdown("### **VIRBAC**")
st.sidebar.subheader("Painel de Controle")
st.sidebar.info("Módulo de Consulta Automatizada da SUFRAMA e Validação do PIN para NFs de Entrada/Saída.")

# Função para consultar situação cadastral do CNPJ
@st.cache_data(ttl=3600)
def consultar_suframa_cnpj(cnpj):
    cnpj_limpo = ''.join(filter(str.isdigit, cnpj))
    if not cnpj_limpo or len(cnpj_limpo) != 14:
        return {"status": "CNPJ INVÁLIDO", "detalhe": "Tamanho incorreto"}
        
    url = f"https://publica.cnpj.ws/cnpj/{cnpj_limpo}"
    try:
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            dados = response.json()
            situacao = dados.get('estabelecimento', {}).get('situacao_cadastral', 'Ativa')
            return {
                "status": "HABILITADO" if situacao.upper() == "ATIVA" else "INATIVO/IRREGULAR",
                "detalhe": f"Situação: {situacao}"
            }
        else:
            return {"status": "CONSULTA INDISPONÍVEL", "detalhe": "Erro na API externa"}
    except Exception:
        return {"status": "TIMEOUT", "detalhe": "Erro de conexão"}

# Área de Upload
st.subheader("📤 Upload de Arquivos XML")
uploaded_files = st.file_uploader(
    "Arraste ou selecione até 50 arquivos XML para processamento simultâneo:", 
    type=["xml"], 
    accept_multiple_files=True
)

if uploaded_files:
    if len(uploaded_files) > 50:
        st.warning("⚠️ Limite do lote: processando apenas os primeiros 50 XMLs.")
        uploaded_files = uploaded_files[:50]

    relatorio_lote = []
    origens_nacionais = ['0', '3', '4', '5', '8']
    ufs_suframa = ['AM', 'AC', 'RO', 'RR', 'AP']

    progress_bar = st.progress(0)
    status_text = st.empty()

    total_nfs = len(uploaded_files)
    qtd_gerar_pin = 0
    valor_total_lote = 0.0

    for index, file in enumerate(uploaded_files):
        status_text.text(f"Analisando arquivo {index + 1} de {total_nfs}: {file.name}")
        
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
            valor_total_lote += valor_total_nf
            
            cnpj_dest = destinatario.get('CNPJ', destinatario.get('CPF', 'Não identificado'))
            isuf_xml = destinatario.get('ISUF', 'Não informado')
            cidade_dest = ender_dest.get('xMun', 'N/D')
            uf_dest = ender_dest.get('UF', 'N/D')

            # Consulta Situação do CNPJ
            consulta_suframa = consultar_suframa_cnpj(cnpj_dest)
            status_cadastro = consulta_suframa["status"]

            # Análise das Origens dos Itens
            detalhes = infNFe.get('det', [])
            if not isinstance(detalhes, list):
                detalhes = [detalhes]

            qtd_itens_nacionais = 0
            for det in detalhes:
                imposto = det.get('imposto', {})
                icms = imposto.get('ICMS', {})
                origem = "N/D"
                
                for k, v in icms.items():
                    if isinstance(v, dict) and 'orig' in v:
                        origem = str(v.get('orig', 'N/D'))
                        break
                
                if origem in origens_nacionais:
                    qtd_itens_nacionais += 1

            # Aplicação das Regras do PIN
            if uf_dest not in ufs_suframa:
                parecer_pin = "🟢 DISPENSADO (Fora ZFM)"
            elif "INATIVO" in status_cadastro:
                parecer_pin = "🔴 BLOQUEADO (Inativo)"
            elif qtd_itens_nacionais > 0:
                parecer_pin = "🟡 GERAR PIN (Obrigatório)"
                qtd_gerar_pin += 1
            else:
                parecer_pin = "🟢 DISPENSADO (Estrangeiro)"

            relatorio_lote.append({
                "Nº NF": numero_nf,
                "Valor Total": f"R$ {valor_total_nf:,.2f}",
                "Cidade": cidade_dest,
                "UF": uf_dest,
                "CNPJ Destinatário": cnpj_dest,
                "ISUF (XML)": isuf_xml,
                "Situação Cadastral": status_cadastro,
                "Origem Nacional": f"{qtd_itens_nacionais}/{len(detalhes)}",
                "Diagnóstico PIN": parecer_pin,
                "Nome Arquivo": file.name
            })

        except Exception as e:
            relatorio_lote.append({
                "Nº NF": "ERRO",
                "Valor Total": "R$ 0,00",
                "Cidade": "N/D",
                "UF": "N/D",
                "CNPJ Destinatário": "N/D",
                "ISUF (XML)": "N/D",
                "Situação Cadastral": "Erro no XML",
                "Origem Nacional": "0",
                "Diagnóstico PIN": "🔴 ERRO LEITURA",
                "Nome Arquivo": file.name
            })

        progress_bar.progress((index + 1) / total_nfs)

    status_text.empty()
    progress_bar.empty()

    # Dashboard de Resumo
    st.subheader("📈 Resumo do Lote Processado")
    m1, m2, m3 = st.columns(3)
    m1.metric("Total de NFs Analisadas", total_nfs)
    m2.metric("NFs com PIN Obrigatório", qtd_gerar_pin)
    m3.metric("Valor Total do Lote", f"R$ {valor_total_lote:,.2f}")

    # Tabela Consolidada
    df_relatorio = pd.DataFrame(relatorio_lote)
    st.subheader("📊 Relatório Detalhado")
    st.dataframe(df_relatorio, use_container_width=True)

    # Exportação em CSV
    csv_data = df_relatorio.to_csv(index=False).encode('utf-8')
    st.download_button(
        label="📥 Baixar Relatório em CSV / Excel",
        data=csv_data,
        file_name="relatorio_virbac_suframa_pin.csv",
        mime="text/csv",
        type="primary"
    )
