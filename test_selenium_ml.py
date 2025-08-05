import time
import traceback

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException


SEARCH_TERM = "notebook"
URL = f"https://lista.mercadolivre.com.br/{SEARCH_TERM}"


def main() -> None:
    start = time.time()
    options = webdriver.ChromeOptions()
    options.add_argument("--headless=new")
    driver = None

    try:
        driver = webdriver.Chrome(options=options)
        driver.get(URL)

        wait = WebDriverWait(driver, 10)
        try:
            element = wait.until(
                EC.presence_of_element_located(
                    (By.CSS_SELECTOR, "li.ui-search-layout__item a.ui-search-link")
                )
            )
            link = element.get_attribute("href")
            print(f"Primeiro link encontrado: {link}")
        except TimeoutException:
            print("Erro: nenhum produto encontrado dentro do tempo limite.")
            traceback.print_exc()
        except Exception:
            print("Erro inesperado ao buscar produto:")
            traceback.print_exc()
    except Exception:
        print("Erro ao iniciar o ChromeDriver ou acessar a página:")
        traceback.print_exc()
    finally:
        if driver:
            driver.quit()
        total = time.time() - start
        print(f"Tempo total de execução: {total:.2f} segundos")


if __name__ == "__main__":
    main()
