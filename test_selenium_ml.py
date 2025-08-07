import argparse
import logging
import os
import sys
import time
from datetime import datetime

from selenium import webdriver
from selenium.common.exceptions import TimeoutException, WebDriverException
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait


def main() -> None:
    parser = argparse.ArgumentParser(description="Teste simples de scraping no Mercado Livre")
    parser.add_argument("search_term", nargs="?", default="notebook", help="Termo de busca")
    parser.add_argument(
        "--use-profile",
        action="store_true",
        help="Usa o perfil padrão do Chrome do sistema (apenas Windows)",
    )
    parser.add_argument(
        "--pause-login",
        action="store_true",
        help="Pausa a execução para login manual antes de procurar os produtos",
    )
    parser.add_argument(
        "--headless",
        action="store_true",
        help="Executa o Chrome em modo headless",
    )
    args = parser.parse_args()

    url = f"https://lista.mercadolivre.com.br/{args.search_term}"
    start_time = datetime.now()
    print(f"Scraping iniciado em: {start_time:%Y-%m-%d %H:%M:%S}")

    start = time.time()
    options = webdriver.ChromeOptions()
    if args.headless:
        options.add_argument("--headless=new")
    options.add_argument("--incognito")

    logging.basicConfig(
        filename="scraping.log",
        level=logging.ERROR,
        format="%(asctime)s %(levelname)s: %(message)s",
    )

    if args.use_profile and os.name == "nt":
        user_data_dir = os.path.join(
            os.environ.get("LOCALAPPDATA", ""), "Google", "Chrome", "User Data"
        )
        if os.path.exists(user_data_dir):
            options.add_argument(f"user-data-dir={user_data_dir}")
            options.add_argument("profile-directory=Default")
            print(f"Usando perfil padrão em: {user_data_dir}")
        else:
            print("Perfil padrão do Chrome não encontrado, prosseguindo sem perfil.")

    driver = None
    product_selector = "li.ui-search-layout__item"
    try:
        print(f"Acessando URL: {url}")
        driver = webdriver.Chrome(options=options)
        print("Navegador iniciado, carregando página...")
        driver.get(url)
        if "#" in driver.current_url:
            clean_url = driver.current_url.split("#")[0]
            if clean_url != driver.current_url:
                print("URL contém hash, recarregando sem o hash...")
                driver.get(clean_url)
        if args.pause_login:
            input("Faça login manualmente e pressione Enter para continuar...")
        print("Página carregada, iniciando espera pelos produtos...")

        # Tenta fechar pop-ups de cookies ou login
        for css in [
            "button.cookie-consent-banner-opt-out__action--key-accept",
            "button[data-testid='action:understood-button']",
            "button[data-testid='action:accept']",
            "button[data-testid='action:close']",
            "button#user_id",
        ]:
            try:
                WebDriverWait(driver, 5).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, css))
                ).click()
            except TimeoutException:
                pass

        container_selector = "ol.ui-search-layout__items"
        WebDriverWait(driver, 20).until(
            EC.visibility_of_element_located((By.CSS_SELECTOR, container_selector))
        )
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(2)

        produtos = WebDriverWait(driver, 20).until(
            EC.presence_of_all_elements_located((By.CSS_SELECTOR, product_selector))
        )

        print(f"Produtos encontrados: {len(produtos)}")
        link = produtos[0].find_element(By.CSS_SELECTOR, "a.ui-search-link").get_attribute("href")
        print(f"Primeiro link encontrado: {link}")
        try:
            screenshot = "produtos.png"
            driver.save_screenshot(screenshot)
            print(f"Screenshot salva em {screenshot}")
        except WebDriverException as err:
            print(f"Falha ao salvar screenshot: {err}")
    except TimeoutException as exc:
        print(f"Erro: {exc}")
        logging.exception("Timeout ao buscar produtos")
        if driver:
            try:
                screenshot = f"timeout_{int(time.time())}.png"
                driver.save_screenshot(screenshot)
                print(f"Screenshot salva em {screenshot}")
            except WebDriverException as err:
                print(f"Falha ao salvar screenshot: {err}")
    except WebDriverException as exc:
        print(f"Erro ao iniciar o ChromeDriver ou acessar a página: {exc}")
        logging.exception("Erro do WebDriver")
        if driver:
            try:
                screenshot = f"webdriver_{int(time.time())}.png"
                driver.save_screenshot(screenshot)
                print(f"Screenshot salva em {screenshot}")
            except WebDriverException as err:
                print(f"Falha ao salvar screenshot: {err}")
    except Exception as exc:
        print(f"Erro inesperado: {exc}")
        logging.exception("Erro inesperado durante o scraping")
        if driver:
            try:
                screenshot = f"error_{int(time.time())}.png"
                driver.save_screenshot(screenshot)
                print(f"Screenshot salva em {screenshot}")
            except WebDriverException as err:
                print(f"Falha ao salvar screenshot: {err}")
    finally:
        if driver:
            print("Fechando o driver")
            driver.quit()
        total = time.time() - start
        print(f"Tempo total de execução: {total:.2f} segundos")
        end_time = datetime.now()
        print(f"Scraping finalizado em: {end_time:%Y-%m-%d %H:%M:%S}")


if __name__ == "__main__":
    main()
