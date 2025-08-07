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
from selenium.common.exceptions import TimeoutException
from datetime import datetime

# Cabeçalho falso para requests
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/115.0.0.0 Safari/537.36"
    )
}

# Regex para validar links de produto
REGEX_LINK_PRODUTO = re.compile(r"^https://(produto|item|articulo|www)\.mercadolivre\.com\.br/.+")


def log(msg: str) -> None:
    """Imprime mensagens com timestamp."""
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")


def extrair_com_bs4(html: str) -> Optional[str]:
    soup = BeautifulSoup(html, "html.parser")
    links = soup.select("li.ui-search-layout__item a.ui-search-link")

    for a in links:
        href = a.get("href", "")
        if REGEX_LINK_PRODUTO.match(href):
            return href
    return None


def abrir_navegador_anonimo() -> webdriver.Chrome:
    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--incognito")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument(f"user-agent={HEADERS['User-Agent']}")
    options.add_argument("--window-size=1920,1080")
    return webdriver.Chrome(options=options)


def extrair_com_selenium(termo: str) -> Optional[str]:
    termo_formatado = termo.replace(" ", "-")
    url = f"https://lista.mercadolivre.com.br/{termo_formatado}"
    for tentativa in range(1, 4):
        driver: Optional[webdriver.Chrome] = None
        try:
            log(f"Tentativa Selenium {tentativa} para '{termo}'")
            driver = abrir_navegador_anonimo()
            driver.get(url)

            wait = WebDriverWait(driver, 10)
            wait.until(
                EC.presence_of_all_elements_located(
                    (By.CSS_SELECTOR, "li.ui-search-layout__item")
                )
            )

            itens = driver.find_elements(By.CSS_SELECTOR, "li.ui-search-layout__item")
            for item in itens:
                try:
                    link_el = item.find_element(By.CSS_SELECTOR, "a.ui-search-link")
                    href = link_el.get_attribute("href")
                    if REGEX_LINK_PRODUTO.match(href):
                        return href
                except Exception:
                    continue

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            screenshot = f"timeout_{timestamp}.png"
            driver.save_screenshot(screenshot)
            log(f"🖼️ Screenshot salva em {screenshot}")
        except Exception as e:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            if driver:
                screenshot = f"selenium_error_{timestamp}.png"
                try:
                    driver.save_screenshot(screenshot)
                    log(f"🖼️ Screenshot salva em {screenshot}")
                except Exception:
                    pass
            if isinstance(e, TimeoutException):
                log("⏰ Timeout ao buscar produtos.")
            else:
                log(f"❌ Erro Selenium: {e}")
        finally:
            if driver:
                driver.quit()
        time.sleep(random.uniform(1.5, 4.0))

    return None


def buscar_links_para_itens(df_busca: pd.DataFrame) -> pd.DataFrame:
    resultados: List[dict] = []

    for idx, row in df_busca.iterrows():
        termo = row["Descrição do Item"]
        log(f"\n🔎 ({idx+1}/{len(df_busca)}) Buscando: \"{termo}\"")
        inicio = time.time()
        link: Optional[str] = None
        status = "nenhum resultado"
        html_ultimo = ""

        for tentativa in range(1, 4):
            log(f"Tentativa {tentativa} para \"{termo}\"")
            try:
                url = f"https://lista.mercadolivre.com.br/{termo.replace(' ', '-')}"
                resposta = requests.get(url, headers=HEADERS, timeout=10)
                html = resposta.text
                html_ultimo = html
                url_final = resposta.url

                bloqueado = "account-verification" in url_final
                sem_cards = "ui-search-layout__item" not in html

                if bloqueado or sem_cards:
                    log("⚠️ Nada com BeautifulSoup. Ativando Selenium...")
                    link = extrair_com_selenium(termo)
                else:
                    link = extrair_com_bs4(html)
                    if not link:
                        log("⚠️ Nada com BeautifulSoup. Ativando Selenium...")
                        link = extrair_com_selenium(termo)
            except Exception as e:
                log(f"❌ Erro na tentativa {tentativa}: {e}")
                status = "erro"
                break

            if link:
                status = "ok"
                break
            time.sleep(random.uniform(1.5, 4.0))

        tempo = round(time.time() - inicio, 2)

        if not link and html_ultimo:
            nome_html = f"debug_{termo[:40].replace(' ', '_')}.html"
            with open(nome_html, "w", encoding="utf-8") as f:
                f.write(html_ultimo)
            log(f"❌ Nenhum produto encontrado. HTML salvo em {nome_html}.")

        link_valor = link if link else ("ERRO" if status == "erro" else "NÃO ENCONTRADO")

        resultados.append({
            "Descrição do Item": termo,
            "Link Mercado Livre encontrado": link_valor,
            "Status da busca": status,
            "Tempo gasto (s)": tempo,
            "Timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        })

        time.sleep(random.uniform(1.5, 4.0))

    return pd.DataFrame(resultados)
