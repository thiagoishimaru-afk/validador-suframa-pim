import streamlit as st
import xmltodict
import pandas as pd
from playwright.sync_api import sync_playwright
import os

# Configuração da Página Streamlit
st.set_page_config(page_title="Validador SUFRAMA & PIN - Virbac", layout="wide")

# Função que abre o navegador real do CADSUF em segundo plano e extrai os dados oficiais
@st.cache_data(ttl=3600)
def consultar_cadsuf_oficial_playwright(cnpj):
    cnpj_limpo = ''.join(filter(str.isdigit, str(cnpj)))
    if not cnpj_limpo or len(cnpj_limpo) != 14:
        return {"isuf": "N/D", "situacao": "CNPJ INVÁLIDO", "dt_cad": "N/D"}

    try:
        with sync_playwright() as p:
            # Inicializa o navegador sem interface gráfica
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            
            # Acesse a URL oficial do CADSUF
            page.goto("https://www4.suframa.gov.br/cadsuf/#/situacao-cadastral", timeout=15000)
            page.wait_for_selector("input", timeout=10000)
            
            # Insere o CNPJ no campo da tela
            page.fill("input", cnpj_limpo)
            page.click("button:has-text('Consultar')")
            
            # Aguarda o resultado carregar na tela
            page.wait_for_selector(".resultado-consulta, .card", timeout=8000)
            
            # Extrai os textos do Comprovante
            conteudo = page.content()
            
            # Exemplo de extração dos dados reais exibidos na página
            isuf = "NÃO LOCALIZADO"
            if "Inscrição" in conteudo or "200" in conteudo:
                # Captura o texto que contém o número da Inscrição de 9 dígitos
                import re
                match = re.search(r'\b(20\d{7})\b', conteudo)
                if match:
                    isuf = match.group(1)
            
            situacao = "HABILITADO" if "HABILITADO" in conteudo.upper() or "ATIVA" in conteudo.upper() else "INATIVO"
            
            browser.close()
            return {"isuf": isuf, "situacao": situacao, "dt_cad": "Consultado via CADSUF"}
            
    except Exception as e:
        return {"isuf": "ERRO NA CONSULTA", "situacao": "FALHA NO PORTAL", "dt_cad": "N/D"}
