"""Funções auxiliares para buscar links no Mercado Livre com logs detalhados.

Este módulo centraliza a lógica de scraping e inclui recursos de logging,
tratamento de erros e exportação de resultados.  Ele é utilizado pelo script
``scraper_ml.py`` para processar uma lista de produtos e gerar um arquivo
``.xlsx`` com os links encontrados.
"""

from __future__ import annotations

import time

import pandas as pd
import requests
from bs4 import BeautifulSoup

from colunas_utils import encontrar_colunas_necessarias

try:  # tqdm é opcional; se não estiver instalado, seguimos sem a barra de progresso
    from tqdm import tqdm
except Exception:  # pragma: no cover - fallback simples
    def tqdm(iterable, *_, **__):
        return iterable


NOME_ARQUIVO = "66.xlsx"
RESULTADO_ARQUIVO = "resultados_scraping.xlsx"


def buscar_links_mercado_livre(consulta: str, limite: int = 1) -> list[str]:
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


def buscar_link(produto: str) -> str:
    """Retorna o primeiro link encontrado para ``produto``.

    Parameters
    ----------
    produto : str
        Termo a ser pesquisado no Mercado Livre.

    Returns
    -------
    str
        Primeiro link encontrado ou ``""`` se nenhum resultado for obtido.
    """

    links = buscar_links_mercado_livre(produto, limite=1)
    return links[0] if links else ""


def buscar_links_para_itens(df: pd.DataFrame, delay: float = 1.0) -> pd.DataFrame:
    """Busca o primeiro link para cada item com logs e resumo final.

    Parameters
    ----------
    df : pd.DataFrame
        ``DataFrame`` contendo a coluna ``Descrição do Item`` com os termos
        a serem pesquisados.
    delay : float, optional
        Pausa em segundos entre uma busca e outra para evitar bloqueios.

    Returns
    -------
    pd.DataFrame
        DataFrame com as colunas ``Produto``, ``Link encontrado``, ``Status`` e
        ``Mensagem de erro``.
    """

    if "Descrição do Item" not in df.columns:
        raise KeyError("DataFrame must contain 'Descrição do Item' column")

    resultados: list[dict[str, str]] = []
    itens = df["Descrição do Item"].dropna().unique()
    total = len(itens)
    falhas: list[str] = []

    for indice, descricao in enumerate(tqdm(itens, total=total, desc="Progresso"), start=1):
        termo_busca = str(descricao).strip()
        tqdm.write(f"Buscando item {indice} de {total}: \"{termo_busca}\"")
        inicio = time.time()
        link = ""
        status = "Erro"
        msg_erro = ""
        try:
            link = buscar_link(termo_busca)
            if link:
                tqdm.write(f"✅ Link encontrado: {link}")
                status = "Sucesso"
            else:
                msg_erro = "Nenhum link encontrado"
                falhas.append(termo_busca)
                tqdm.write("⚠️ Nenhum link encontrado")
        except Exception as exc:  # pragma: no cover - interação com rede
            msg_erro = str(exc)
            falhas.append(termo_busca)
            tqdm.write(
                f"❌ Erro ao buscar: \"{termo_busca}\" - {type(exc).__name__}"
            )
        duracao = time.time() - inicio
        tqdm.write(f"⏱️ Tempo: {duracao:.2f}s")
        tqdm.write("---")

        resultados.append(
            {
                "Produto": termo_busca,
                "Link encontrado": link,
                "Status": status,
                "Mensagem de erro": msg_erro,
            }
        )
        time.sleep(delay)

    sucesso = total - len(falhas)
    print("\nResumo:")
    print(f"- Sucessos: {sucesso}")
    print(f"- Falhas: {len(falhas)}")
    if falhas:
        print("Itens com falha:")
        for item in falhas:
            print(f"- {item}")

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
