"""Funções auxiliares para buscar links no Mercado Livre com logs detalhados."""

from __future__ import annotations
import random
import re
import time
import pandas as pd
import requests
from bs4 import BeautifulSoup
from colunas_utils import encontrar_colunas_necessarias

try:
    from tqdm import tqdm
    tqdm_write = tqdm.write
except Exception:
    def tqdm(iterable, *_, **__):
        return iterable
    def tqdm_write(msg):
        print(msg)

NOME_ARQUIVO = "66.xlsx"
RESULTADO_ARQUIVO = "resultado_scraping.xlsx"

def buscar_links_mercado_livre(consulta: str, limite: int = 1, salvar_html: bool = False, caminho_html: str = "pagina_debug.html") -> list[str]:
    termo = consulta.replace(" ", "-")
    url = f"https://lista.mercadolivre.com.br/{termo}"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
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
            tqdm_write("ℹ️ Redirecionamentos: " + " -> ".join(str(r.status_code) for r in response.history))
        tqdm_write(f"🌐 GET {response.url} -> {response.status_code}")
        response.raise_for_status()
    except requests.RequestException as exc:
        tqdm_write(f"⚠️ Falha na requisição: {exc}")
        return []

    soup = BeautifulSoup(response.text, "html.parser")

    # Novo seletor adaptado para layout atual
    cards = soup.select("a[href*='mercadolivre.com.br']")
    if not cards:
        tqdm_write("⚠️ Nenhum card encontrado com os seletores atualizados.")
        if salvar_html:
            try:
                with open(caminho_html, "w", encoding="utf-8") as f:
                    f.write(response.text)
                tqdm_write(f"📝 HTML salvo em: {caminho_html}")
            except OSError as exc:
                tqdm_write(f"⚠️ Erro ao salvar HTML: {exc}")
        return []

    links: list[str] = []
    for card in cards:
        href = card.get("href")
        if href and "anuncio" not in href.lower():  # ignora anúncios
            links.append(href.split("#")[0])
        if len(links) >= limite:
            break

    if not links and salvar_html:
        try:
            with open(caminho_html, "w", encoding="utf-8") as f:
                f.write(response.text)
            tqdm_write(f"📝 HTML salvo em: {caminho_html}")
        except OSError as exc:
            tqdm_write(f"⚠️ Erro ao salvar HTML: {exc}")

    return links

def buscar_link(produto: str) -> str:
    slug = re.sub(r"[^a-z0-9-]+", "-", produto.lower()).strip("-")
    caminho = f"debug_{slug}.html"
    links = buscar_links_mercado_livre(produto, limite=1, salvar_html=True, caminho_html=caminho)
    return links[0] if links else ""

def buscar_links_para_itens(df: pd.DataFrame, delay_range: tuple[float, float] = (5, 12)) -> pd.DataFrame:
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
        except Exception as exc:
            msg_erro = str(exc)
            falhas.append(termo_busca)
            tqdm_write(f"❌ Erro ao buscar: \"{termo_busca}\" - {type(exc).__name__}")
        duracao = time.time() - inicio
        tqdm_write(f"⏱️ Tempo: {duracao:.2f}s")
        tqdm_write("---")

        resultados.append({
            "Produto": termo_busca,
            "Link encontrado": link,
            "Status": status,
            "Mensagem de erro": msg_erro,
        })
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
