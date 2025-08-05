import requests
from bs4 import BeautifulSoup
import pandas as pd
import time

from colunas_utils import encontrar_colunas_necessarias

NOME_ARQUIVO = "66.xlsx"
RESULTADO_ARQUIVO = "resultado_links.xlsx"


def buscar_links_mercado_livre(consulta: str, limite: int = 3) -> list[str]:
    """Retorna os primeiros ``limite`` links de uma busca no Mercado Livre."""

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
    itens = df["Descrição do Item"].dropna().unique()
    total = len(itens)
    falhas: list[str] = []

    for indice, descricao in enumerate(itens, start=1):
        termo_busca = str(descricao).strip()
        print(f"🔍 Buscando item {indice} de {total}: \"{termo_busca}\"")
        inicio = time.time()
        try:
            links = buscar_links_mercado_livre(termo_busca)
            if links:
                print(f"✅ Link encontrado: {links[0]}")
            else:
                print("⚠️ Nenhum link encontrado")
        except Exception as exc:  # pragma: no cover - interação com rede
            print(
                f"❌ Erro ao buscar: \"{termo_busca}\" - {type(exc).__name__}"
            )
            falhas.append(termo_busca)
            links = []
        duracao = time.time() - inicio
        print(f"⏱️ Tempo de busca: {duracao:.2f} segundos")
        print("---")

        resultado = {"Descrição do Item": termo_busca}
        for i in range(3):
            resultado[f"Link {i + 1}"] = links[i] if i < len(links) else ""
        resultados.append(resultado)

    sucesso = total - len(falhas)
    print(
        f"\nResumo: {sucesso} produtos processados com sucesso e {len(falhas)} falharam."
    )
    if falhas:
        print("Itens com falha:")
        for item in falhas:
            print(f"- {item}")

    return pd.DataFrame(
        resultados, columns=["Descrição do Item", "Link 1", "Link 2", "Link 3"]
    )


def main():
    df, _, info_colunas = encontrar_colunas_necessarias(NOME_ARQUIVO)
    coluna_descricao = info_colunas["principal"]

    df_itens = df[[coluna_descricao]].rename(columns={coluna_descricao: "Descrição do Item"})
    resultado_df = buscar_links_para_itens(df_itens)
    resultado_df.to_excel(RESULTADO_ARQUIVO, index=False)
    print(f"✅ Resultados salvos em: {RESULTADO_ARQUIVO}")


if __name__ == "__main__":
    main()
