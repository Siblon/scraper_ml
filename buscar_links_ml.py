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


def buscar_links_para_itens(df: pd.DataFrame) -> pd.DataFrame:
    """Busca os três primeiros links para cada item em um ``DataFrame``.

    Parameters
    ----------
    df : pd.DataFrame
        ``DataFrame`` contendo a coluna ``Descrição do Item`` com os termos
        a serem pesquisados.

    Returns
    -------
    pd.DataFrame
        ``DataFrame`` com as colunas ``Descrição do Item`` e ``Link 1`` a
        ``Link 3`` contendo os primeiros resultados encontrados.
    """

    if "Descrição do Item" not in df.columns:
        raise KeyError("DataFrame must contain 'Descrição do Item' column")

    resultados: list[dict[str, str]] = []
    for descricao in df["Descrição do Item"].dropna():
        termo_busca = str(descricao).strip()
        links = buscar_links(termo_busca)
        resultado = {"Descrição do Item": termo_busca}
        for i in range(3):
            resultado[f"Link {i+1}"] = links[i] if i < len(links) else ""
        resultados.append(resultado)

    return pd.DataFrame(resultados, columns=["Descrição do Item", "Link 1", "Link 2", "Link 3"])


def main():
    df, _, info_colunas = encontrar_colunas_necessarias(NOME_ARQUIVO)
    coluna_descricao = info_colunas["principal"]

    df_itens = df[[coluna_descricao]].rename(columns={coluna_descricao: "Descrição do Item"})
    resultado_df = buscar_links_para_itens(df_itens)
    resultado_df.to_excel(RESULTADO_ARQUIVO, index=False)
    print(f"✅ Resultados salvos em: {RESULTADO_ARQUIVO}")


if __name__ == "__main__":
    main()
