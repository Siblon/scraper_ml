"""Funções auxiliares para buscar links no Mercado Livre com logs detalhados.

Este módulo centraliza a lógica de scraping e inclui recursos de logging,
tratamento de erros e exportação de resultados.  Ele é utilizado pelo script
``scraper_ml.py`` para processar uma lista de produtos e gerar um arquivo
``.xlsx`` com os links encontrados.
"""

from __future__ import annotations

import random
import time

import pandas as pd
import requests
from bs4 import BeautifulSoup

from colunas_utils import encontrar_colunas_necessarias

try:  # tqdm é opcional; se não estiver instalado, seguimos sem a barra de progresso
    from tqdm import tqdm
    tqdm_write = tqdm.write
except Exception:  # pragma: no cover - fallback simples
    def tqdm(iterable, *_, **__):
        return iterable

    def tqdm_write(msg):  # type: ignore[unused-arg]
        print(msg)


NOME_ARQUIVO = "66.xlsx"
RESULTADO_ARQUIVO = "resultado_scraping.xlsx"


def buscar_links_mercado_livre(
    consulta: str,
    limite: int = 1,
    salvar_html: bool = False,
    caminho_html: str = "pagina_debug.html",
) -> list[str]:
    """Retorna os primeiros ``limite`` links de uma busca no Mercado Livre.

    A requisição utiliza headers semelhantes aos de um navegador real para
    reduzir bloqueios e registra o status HTTP retornado. Caso ``salvar_html``
    seja ``True``, o HTML obtido é gravado em ``caminho_html`` para depuração.
    """

    termo = consulta.replace(" ", "-")
    url = f"https://lista.mercadolivre.com.br/{termo}"
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 "
            "Safari/537.36"
        ),
        "Accept": (
            "text/html,application/xhtml+xml,application/xml;q=0.9," "image/avif,image/webp,image/apng,*/*;q=0.8"
        ),
        "Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7",
        "Cache-Control": "no-cache",
        "Connection": "keep-alive",
        "Pragma": "no-cache",
        "Upgrade-Insecure-Requests": "1",
    }

    session = requests.Session()
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

    if salvar_html:
        try:
            with open(caminho_html, "w", encoding="utf-8") as f:
                f.write(response.text)
        except OSError as exc:
            tqdm_write(f"⚠️ Erro ao salvar HTML: {exc}")

    soup = BeautifulSoup(response.text, "html.parser")
    cards = soup.select("li.ui-search-layout__item")
    if not cards:
        tqdm_write(
            "⚠️ Nenhum card de produto encontrado; a estrutura da página pode ter mudado ou o acesso foi bloqueado."
        )
        return []

    links: list[str] = []
    for card in cards:
        if card.select_one(".ui-search-item__ad-label"):
            continue  # ignora anúncios patrocinados
        link_tag = card.select_one("a.ui-search-link") or card.select_one(
            "a.ui-search-item__group__element"
        )
        href = link_tag.get("href") if link_tag else None
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


def buscar_links_para_itens(
    df: pd.DataFrame, delay_range: tuple[float, float] = (5, 12)
) -> pd.DataFrame:
    """Busca o primeiro link para cada item com logs e resumo final.

    Parameters
    ----------
    df : pd.DataFrame
        ``DataFrame`` contendo a coluna ``Descrição do Item`` com os termos
        a serem pesquisados.
    delay_range : tuple[float, float], optional
        Intervalo de espera aleatório, em segundos, entre as requisições
        para evitar bloqueios (padrão ``(5, 12)``).

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
        tqdm_write(f"🔎 [{indice}/{total}] Buscando: \"{termo_busca}\"")
        inicio = time.time()
        link = ""
        status = "Erro"
        msg_erro = ""
        try:
            link = buscar_link(termo_busca)
            if link:
                tqdm_write(f"✅ Link encontrado: {link}")
                status = "Sucesso"
            else:
                msg_erro = "Nenhum link encontrado"
                falhas.append(termo_busca)
                tqdm_write("⚠️ Nenhum link encontrado")
        except Exception as exc:  # pragma: no cover - interação com rede
            msg_erro = str(exc)
            falhas.append(termo_busca)
            tqdm_write(
                f"❌ Erro ao buscar: \"{termo_busca}\" - {type(exc).__name__}"
            )
        duracao = time.time() - inicio
        tqdm_write(f"⏱️ Tempo: {duracao:.2f}s")
        tqdm_write("---")

        resultados.append(
            {
                "Produto": termo_busca,
                "Link encontrado": link,
                "Status": status,
                "Mensagem de erro": msg_erro,
            }
        )
        espera = random.uniform(*delay_range)
        time.sleep(espera)

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
