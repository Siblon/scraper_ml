import time
import re
import random
import requests
import pandas as pd
from bs4 import BeautifulSoup
from typing import Optional, List

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# Cabeçalho falso para requests
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36"
}

# Regex para validar links de produto
REGEX_LINK_PRODUTO = re.compile(r"^https://(produto|item|articulo|www)\.mercadolivre\.com\.br/.+")


def extrair_com_bs4(html: str) -> Optional[str]:
    soup = BeautifulSoup(html, "html.parser")
    links = soup.select("li.ui-search-layout__item a.ui-search-link")

    for a in links:
        href = a.get("href", "")
        if REGEX_LINK_PRODUTO.match(href):
            return href
    return None


def extrair_com_selenium(termo: str) -> Optional[str]:
    termo_formatado = termo.replace(" ", "-")
    url = f"https://lista.mercadolivre.com.br/{termo_formatado}"

    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("--window-size=1920,1080")

    try:
        driver = webdriver.Chrome(options=options)
        driver.get(url)

        wait = WebDriverWait(driver, 10)
        wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "li.ui-search-layout__item a.ui-search-link")))

        elementos = driver.find_elements(By.CSS_SELECTOR, "li.ui-search-layout__item a.ui-search-link")
        for el in elementos:
            href = el.get_attribute("href")
            if REGEX_LINK_PRODUTO.match(href):
                return href

    except Exception as e:
        print(f"❌ Erro Selenium: {e}")
    finally:
        driver.quit()

    return None


def buscar_links_para_itens(df_busca: pd.DataFrame) -> pd.DataFrame:
    resultados: List[dict] = []

    for idx, row in df_busca.iterrows():
        termo = row["Descrição do Item"]
        print(f"\n🔎 ({idx+1}/{len(df_busca)}) Buscando: \"{termo}\"")
        inicio = time.time()

        url = f"https://lista.mercadolivre.com.br/{termo.replace(' ', '-')}"
        try:
            resposta = requests.get(url, headers=HEADERS, timeout=10)
            html = resposta.text
            link = extrair_com_bs4(html)

            if link:
                tempo = round(time.time() - inicio, 2)
                print(f"✅ Link encontrado (BS4): {link}")
                status = "Sucesso (rápido)"
            else:
                print("⚠️ Nada com BeautifulSoup. Ativando Selenium...")
                link = extrair_com_selenium(termo)
                tempo = round(time.time() - inicio, 2)

                if link:
                    print(f"✅ Link encontrado (Selenium): {link}")
                    status = "Sucesso (via Selenium)"
                else:
                    print(f"❌ Nenhum produto encontrado. HTML salvo.")
                    nome_html = f"debug_{termo[:40].replace(' ', '_')}.html"
                    with open(nome_html, "w", encoding="utf-8") as f:
                        f.write(html)
                    link = "NÃO ENCONTRADO"
                    status = "Falha"

        except Exception as e:
            tempo = round(time.time() - inicio, 2)
            link = "ERRO"
            status = f"Erro: {str(e)}"
            print(f"❌ Erro na busca: {e}")

        resultados.append({
            "Descrição do Item": termo,
            "Link encontrado": link,
            "Status": status,
            "Tempo (s)": tempo
        })

        time.sleep(random.uniform(2.5, 5.5))  # Delay entre buscas

    return pd.DataFrame(resultados)
