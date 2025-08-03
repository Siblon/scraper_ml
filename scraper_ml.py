"""Scraper de preços do Mercado Livre.

Este script automatiza a busca de determinados modelos de produtos no
Mercado Livre, extraindo o preço dos primeiros resultados encontrados e
gerando um arquivo CSV com o preço médio por modelo.

As bibliotecas :mod:`selenium` e :mod:`pandas` são necessárias para a
execução. Caso não estejam instaladas, o script exibirá uma mensagem de
erro clara instruindo a instalação via ``pip install -r requirements.txt``.
"""

try:
    from selenium import webdriver
    from selenium.webdriver.chrome.service import Service
    from selenium.webdriver.common.by import By
    from selenium.webdriver.chrome.options import Options
    from time import sleep
    import pandas as pd
except ModuleNotFoundError as exc:  # pragma: no cover - executed at import time
    raise SystemExit(
        "Dependências ausentes. Instale-as com 'pip install -r requirements.txt'"
    ) from exc

import urllib.parse

# Caminho do seu chromedriver
CAMINHO_CHROMEDRIVER = r"C:\Users\Win10\Downloads\chromedriver-win64\chromedriver-win64\chromedriver.exe"

# Lista de modelos para buscar
modelos = [
    "VS PPACE 2.0 CFI IE8888",
    "ADVANTAGE SMILEY CFI JI0501",
    "TENSAUR SPORT 2.0 CF I GW6456",
    "VL COURT 3.0 CFI ID9157",
    "VL COURT 3.0 CFI"
]

# Configurar navegador invisível (modo headless se quiser)
options = Options()
# options.add_argument('--headless')  # descomente essa linha se quiser rodar em segundo plano
options.add_argument('--start-maximized')

def main() -> None:
    """Executa a busca e salva o CSV com os preços encontrados."""
    service = Service(CAMINHO_CHROMEDRIVER)
    driver = webdriver.Chrome(service=service, options=options)

    resultados = []

    for modelo in modelos:
        print(f"\n🔍 Buscando: {modelo}")
        query = urllib.parse.quote(modelo)
        url = f"https://lista.mercadolivre.com.br/{query}"
        driver.get(url)
        sleep(2)

        precos = []
        links = []
        nomes = []

        cards = driver.find_elements(By.CSS_SELECTOR, "li.ui-search-layout__item")[:10]

        for card in cards:
            try:
                nome = card.find_element(By.CSS_SELECTOR, "h2.ui-search-item__title").text
                preco_text = card.find_element(By.CSS_SELECTOR, "span.andes-money-amount__fraction").text
                preco = float(preco_text.replace(".", "").replace(",", "."))
                link = card.find_element(By.TAG_NAME, "a").get_attribute("href")

                precos.append(preco)
                nomes.append(nome)
                links.append(link)
            except Exception:  # pylint: disable=broad-except
                continue

        media = round(sum(precos) / len(precos), 2) if precos else 0
        print(f"📊 Preço médio: R${media:.2f} com {len(precos)} resultados")

        for i in range(len(precos)):
            resultados.append(
                {
                    "Modelo buscado": modelo,
                    "Produto": nomes[i],
                    "Preço": precos[i],
                    "Link": links[i],
                }
            )

    # Fechar navegador
    driver.quit()

    # Mostrar resultados
    df = pd.DataFrame(resultados)
    print("\n🧾 Preços capturados:")
    print(df[["Modelo buscado", "Preço"]].groupby("Modelo buscado").mean().round(2))

    # Salvar CSV (opcional)
    output = "precos_mercado_livre.csv"
    df.to_csv(output, index=False, encoding="utf-8-sig")
    print(f"\n💾 Arquivo salvo como: {output}")


if __name__ == "__main__":  # pragma: no cover - direct execution
    main()
