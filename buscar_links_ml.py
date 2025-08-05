"""Funções auxiliares para buscar links no Mercado Livre com logs detalhados."""

from __future__ import annotations
import random
import re
import time
import unicodedata

import pandas as pd
import requests
from requests.adapters import HTTPAdapter, Retry
from bs4 import BeautifulSoup
from colunas_utils import encontrar_colunas_necessarias
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException

try:
    from tqdm import tqdm
    tqdm_write = tqdm.write
except Exception:
    def tqdm(iterable, *_, **__):
        return iterable
    def tqdm_write(msg):
        print(msg)

NOME_ARQUIVO = "66.xlsx"
RESULTADO_ARQUIVO = "resultado_scraping.xlsx"


USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.0 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64; rv:117.0) Gecko/20100101 Firefox/117.0",
]


def gerar_slug(texto: str) -> str:
    """Converte ``texto`` em um slug simples.

    Remove acentos e caracteres especiais, substitui espaços por hifens e
    converte o resultado para minúsculas.
    """

    texto_normalizado = unicodedata.normalize("NFKD", texto)
    texto_ascii = texto_normalizado.encode("ascii", "ignore").decode("ascii")
    texto_limpo = re.sub(r"[^a-zA-Z0-9\s-]", "", texto_ascii)
    texto_hifenizado = re.sub(r"\s+", "-", texto_limpo.strip())
    texto_hifenizado = re.sub(r"-+", "-", texto_hifenizado)
    return texto_hifenizado.lower()

def buscar_links_mercado_livre(
    consulta: str,
    limite: int = 1,
    salvar_html: bool = False,
    caminho_html: str = "pagina_debug.html",
) -> list[str]:
    termo = gerar_slug(consulta)
    url = f"https://lista.mercadolivre.com.br/{termo}"
    headers = {
        "User-Agent": random.choice(USER_AGENTS),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
        "Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7",
        "Cache-Control": "no-cache",
        "Connection": "keep-alive",
        "Pragma": "no-cache",
        "Upgrade-Insecure-Requests": "1",
    }

    session = requests.Session()
    retries = Retry(
        total=3,
        backoff_factor=0.5,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET"],
    )
    adapter = HTTPAdapter(max_retries=retries)
    session.mount("https://", adapter)
    session.mount("http://", adapter)

    time.sleep(random.uniform(1, 3))
    try:
        response = session.get(url, headers=headers, timeout=10, allow_redirects=True)
        if response.history:
            tqdm_write(
                "ℹ️ Redirecionamentos: "
                + " -> ".join(str(r.status_code) for r in response.history)
            )
        tqdm_write(f"🌐 GET {response.url} -> {response.status_code}")
        response.raise_for_status()
    except requests.RequestException as exc:
        tqdm_write(f"⚠️ Falha na requisição: {exc}")
        return []

    soup = BeautifulSoup(response.text, "html.parser")

    padrao_produto = re.compile(r"(\/p\/MLB\d+|MLB-\d+|\/item\/)", re.IGNORECASE)

    selectors = [
        "li.ui-search-layout__item a.ui-search-link",
        "a.ui-search-item__group__element.ui-search-link",
        "div.ui-search-result__content-wrapper a.ui-search-link",
    ]
    cards = []
    for sel in selectors:
        cards = soup.select(sel)
        if cards:
            break
    if not cards:
        cards = [a for a in soup.find_all("a", href=True) if padrao_produto.search(a["href"])]

    if not cards:
        tqdm_write("⚠️ Nenhum card de produto encontrado na página.")
        if salvar_html:
            try:
                with open(caminho_html, "w", encoding="utf-8") as f:
                    f.write(response.text)
                tqdm_write(f"📝 HTML salvo em: {caminho_html}")
            except OSError as exc:
                tqdm_write(f"⚠️ Erro ao salvar HTML: {exc}")
        return []

    links: list[str] = []
    links_invalidos = (
        "/acessibilidade",
        "/ajuda",
        "/ofertas",
        "/privacidade",
        "/seguranca",
    )

    vistos = set()
    for card in cards:
        href = card.get("href")
        if not href:
            continue
        href = href.split("#")[0]
        if href in vistos:
            continue
        vistos.add(href)
        if any(inv in href for inv in links_invalidos) or not padrao_produto.search(href):
            tqdm_write(f"🚫 Link ignorado: {href}")
            continue
        tqdm_write(f"✅ Produto encontrado: {href}")
        links.append(href)
        if len(links) >= limite:
            break

    if not links and salvar_html:
        try:
            with open(caminho_html, "w", encoding="utf-8") as f:
                f.write(response.text)
            tqdm_write(f"📝 HTML salvo em: {caminho_html}")
        except OSError as exc:
            tqdm_write(f"⚠️ Erro ao salvar HTML: {exc}")

    if not links:
        tqdm_write("⚠️ Nenhum produto real encontrado.")

    return links

def buscar_link(produto: str) -> str | None:
    """Retorna o primeiro link de produto encontrado ou ``None``."""

    slug = gerar_slug(produto)
    caminho = f"debug_{slug}.html"
    links = buscar_links_mercado_livre(
        produto, limite=1, salvar_html=True, caminho_html=caminho
    )
    return links[0] if links else None

def buscar_links_para_itens(
    df: pd.DataFrame, delay_range: tuple[float, float] = (3, 7)
) -> pd.DataFrame:
    """Busca links no Mercado Livre usando Selenium.

    Para cada descrição do ``DataFrame`` abre a página de busca em um navegador
    headless, aguarda o carregamento dos produtos e captura o primeiro link de
    item válido. Em caso de falha, salva o HTML de depuração.
    """

    if "Descrição do Item" not in df.columns:
        raise KeyError("DataFrame must contain 'Descrição do Item' column")

    resultados: list[dict[str, str]] = []
    itens = df["Descrição do Item"].dropna().unique()
    total = len(itens)

    options = Options()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument(f"--user-agent={random.choice(USER_AGENTS)}")

    driver = webdriver.Chrome(options=options)

    links_invalidos = (
        "/acessibilidade",
        "/ajuda",
        "/ofertas",
        "/privacidade",
        "/seguranca",
    )
    padrao_produto = re.compile(r"(?:/item/|/p/)", re.IGNORECASE)

    try:
        for indice, descricao in enumerate(
            tqdm(itens, total=total, desc="Progresso"), start=1
        ):
            termo_busca = str(descricao).strip()
            tqdm_write(f"🔎 [{indice}/{total}] Buscando: \"{termo_busca}\"")
            inicio = time.time()

            slug = gerar_slug(termo_busca)
            url = f"https://lista.mercadolivre.com.br/{slug}"
            status = "Não encontrado"
            link_saida = "NÃO ENCONTRADO"

            try:
                tqdm_write(f"🌐 Acessando: {url}")
                driver.get(url)
                wait = WebDriverWait(driver, 10)
                wait.until(
                    EC.presence_of_element_located(
                        (By.CSS_SELECTOR, "li.ui-search-layout__item a.ui-search-link")
                    )
                )
                elementos = driver.find_elements(
                    By.CSS_SELECTOR, "li.ui-search-layout__item a.ui-search-link"
                )
                for elem in elementos:
                    href = elem.get_attribute("href")
                    if not href:
                        continue
                    href = href.split("#")[0]
                    if any(inv in href for inv in links_invalidos):
                        tqdm_write(f"🚫 Link ignorado: {href}")
                        continue
                    if not padrao_produto.search(href):
                        tqdm_write(f"🚫 Link ignorado: {href}")
                        continue
                    link_saida = href
                    status = "Sucesso"
                    tqdm_write(f"✅ Link encontrado: {href}")
                    break
                if status != "Sucesso":
                    tqdm_write(
                        f"⚠️ Nenhum resultado encontrado para: \"{termo_busca}\""
                    )
                    nome_debug = f"debug_{slug}.html"
                    with open(nome_debug, "w", encoding="utf-8") as f:
                        f.write(driver.page_source)
                    tqdm_write(f"📝 HTML salvo em: {nome_debug}")
            except TimeoutException:
                status = "Timeout"
                tqdm_write("⌛ Timeout ao carregar resultados")
                nome_debug = f"debug_{slug}.html"
                with open(nome_debug, "w", encoding="utf-8") as f:
                    f.write(driver.page_source)
                tqdm_write(f"📝 HTML salvo em: {nome_debug}")
            except Exception as exc:
                status = f"Erro: {type(exc).__name__}"
                tqdm_write(
                    f"❌ Erro ao buscar: \"{termo_busca}\" - {exc}"
                )
                nome_debug = f"debug_{slug}.html"
                with open(nome_debug, "w", encoding="utf-8") as f:
                    f.write(driver.page_source)
                tqdm_write(f"📝 HTML salvo em: {nome_debug}")

            duracao = time.time() - inicio
            tqdm_write(f"⏱️ Tempo: {duracao:.2f}s")
            tqdm_write("---")

            resultados.append(
                {
                    "Descrição do Item": termo_busca,
                    "Link encontrado": link_saida,
                    "Status": status,
                    "Tempo (s)": f"{duracao:.2f}",
                }
            )
            espera = random.uniform(*delay_range)
            time.sleep(espera)
    finally:
        driver.quit()

    return pd.DataFrame(resultados)

def main():
    df, _, info_colunas = encontrar_colunas_necessarias(NOME_ARQUIVO)
    coluna_descricao = info_colunas["principal"]

    df_itens = df[[coluna_descricao]].rename(columns={coluna_descricao: "Descrição do Item"})
    resultado_df = buscar_links_para_itens(df_itens)
    resultado_df.to_excel(RESULTADO_ARQUIVO, index=False)
    print(f"✅ Resultados salvos em: {RESULTADO_ARQUIVO}")

if __name__ == "__main__":
    main()
