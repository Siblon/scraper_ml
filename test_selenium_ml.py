import argparse
import os
import sys
import time

from selenium import webdriver
from selenium.common.exceptions import TimeoutException, WebDriverException
from selenium.webdriver.common.by import By


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

    start = time.time()
    options = webdriver.ChromeOptions()
    if args.headless:
        options.add_argument("--headless=new")

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
    # Novo seletor mais robusto que contempla diferentes estruturas de card
    selector = "[data-testid='item'] a.ui-search-link, li.ui-search-layout__item a.ui-search-link"
    try:
        print(f"Acessando URL: {url}")
        driver = webdriver.Chrome(options=options)
        print("Navegador iniciado, carregando página...")
        driver.get(url)
        if args.pause_login:
            input("Faça login manualmente e pressione Enter para continuar...")
        print("Página carregada, iniciando espera pelos produtos...")

        elements = []
        for i in range(20):
            elements = driver.find_elements(By.CSS_SELECTOR, selector)
            print(f"Tentativa {i + 1}/20: {len(elements)} elementos encontrados")
            if elements:
                break
            time.sleep(1)

        if not elements:
            raise TimeoutException("Nenhum produto encontrado dentro do tempo limite")

        print(f"Elementos encontrados: {len(elements)}")
        link = elements[0].get_attribute("href")
        print(f"Primeiro link encontrado: {link}")
        try:
            screenshot = "produtos.png"
            driver.save_screenshot(screenshot)
            print(f"Screenshot salva em {screenshot}")
        except WebDriverException as err:
            print(f"Falha ao salvar screenshot: {err}")
    except TimeoutException as exc:
        print(f"Erro: {exc}")
        if driver:
            try:
                screenshot = "timeout.png"
                driver.save_screenshot(screenshot)
                print(f"Screenshot salva em {screenshot}")
            except WebDriverException as err:
                print(f"Falha ao salvar screenshot: {err}")
    except WebDriverException as exc:
        print(f"Erro ao iniciar o ChromeDriver ou acessar a página: {exc}")
    finally:
        if driver:
            print("Fechando o driver")
            driver.quit()
        total = time.time() - start
        print(f"Tempo total de execução: {total:.2f} segundos")


if __name__ == "__main__":
    main()
