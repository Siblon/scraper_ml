import requests
from bs4 import BeautifulSoup
import pandas as pd

from colunas_utils import encontrar_colunas_necessarias

NOME_ARQUIVO = "66.xlsx"
RESULTADO_ARQUIVO = "resultado_links.xlsx"


def buscar_links(consulta: str, limite: int = 3) -> list[str]:
    """Busca os primeiros links de resultados no Mercado Livre.

    Parameters
    ----------
    consulta : str
        Termo utilizado na busca.
    limite : int, optional
        Número máximo de links retornados, por padrão 3.

    Returns
    -------
    list[str]
        Lista com os links dos resultados encontrados.
    """
    url = f"https://lista.mercadolivre.com.br/{consulta}"
    headers = {"User-Agent": "Mozilla/5.0"}
    response = requests.get(url, headers=headers, timeout=10)
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")
    links: list[str] = []
    for tag in soup.select("a.ui-search-result__content-wrapper"):
        href = tag.get("href")
        if href:
            links.append(href.split("#")[0])
        if len(links) >= limite:
            break
    return links


def main():
    df, _, info_colunas = encontrar_colunas_necessarias(NOME_ARQUIVO)
    coluna_descricao = info_colunas["principal"]

    resultados: list[dict[str, str]] = []
    for descricao in df[coluna_descricao].dropna():
        termo_busca = str(descricao).strip()
        links = buscar_links(termo_busca)
        resultado = {"Descrição do Item": termo_busca}
        for i in range(3):
            resultado[f"Link {i+1}"] = links[i] if i < len(links) else ""
        resultados.append(resultado)

    pd.DataFrame(resultados).to_excel(RESULTADO_ARQUIVO, index=False)
    print(f"✅ Resultados salvos em: {RESULTADO_ARQUIVO}")


if __name__ == "__main__":
    main()
