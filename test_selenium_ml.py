import sys
import time

from selenium import webdriver
from selenium.common.exceptions import TimeoutException, WebDriverException
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait


def main() -> None:
    search_term = sys.argv[1] if len(sys.argv) > 1 else "notebook"
    url = f"https://lista.mercadolivre.com.br/{search_term}"

    start = time.time()
    options = webdriver.ChromeOptions()
    options.add_argument("--headless=new")

    driver = None
    try:
        driver = webdriver.Chrome(options=options)
        driver.get(url)

        wait = WebDriverWait(driver, 10)
        element = wait.until(
            EC.presence_of_element_located(
                (By.CSS_SELECTOR, "li.ui-search-layout__item a.ui-search-link")
            )
        )
        link = element.get_attribute("href")
        print(f"Primeiro link encontrado: {link}")
    except TimeoutException:
        print("Erro: nenhum produto encontrado dentro do tempo limite.")
    except WebDriverException as exc:
        print(f"Erro ao iniciar o ChromeDriver ou acessar a página: {exc}")
    finally:
        if driver:
            driver.quit()
        total = time.time() - start
        print(f"Tempo total de execução: {total:.2f} segundos")


if __name__ == "__main__":
    main()
