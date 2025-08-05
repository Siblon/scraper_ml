import pandas as pd
import unicodedata
import re
from difflib import SequenceMatcher
from typing import Optional


def normalizar(texto):
    """Remove acentos, espaços e pontuação de um texto."""
    if not isinstance(texto, str):
        return ""
    texto = (
        unicodedata.normalize("NFKD", texto)
        .encode("ASCII", "ignore")
        .decode("utf-8")
        .lower()
    )
    # Remove caracteres não alfanuméricos (espaços, pontuações, etc.)
    texto = re.sub(r"[\W_]+", "", texto)
    return texto


def inferir_coluna_por_conteudo(serie, n=5) -> Optional[str]:
    """Tenta inferir o tipo da coluna analisando as primeiras N linhas."""
    amostra = serie.dropna().astype(str).head(n).str.lower()
    if amostra.empty:
        return None

    texto = " ".join(amostra)
    produto_keywords = ["nike", "adidas", "tenis", "tênis", "sapato"]
    if any(k in texto for k in produto_keywords):
        return "produto"

    numeros = (
        amostra.str.replace(",", ".", regex=False)
        .str.extract(r"(-?\d+\.?\d*)")[0]
    )
    numeros = pd.to_numeric(numeros, errors="coerce")
    if numeros.notna().all():
        if numeros.max() <= 60:
            return "tamanho"
        if (numeros % 1 == 0).all():
            return "quantidade"
        return "preco_unitario"

    return None


def encontrar_colunas_necessarias(caminho_arquivo, sinonimos, linhas_amostra=5):
    """Lê a planilha e identifica dinamicamente as colunas necessárias.

    Retorna o DataFrame da aba encontrada, o nome da aba e um dicionário
    com as colunas mapeadas para produto, modelo, tamanho, quantidade,
    preço unitário e total.
    """
    xls = pd.ExcelFile(caminho_arquivo)
    for aba in xls.sheet_names:
        df = pd.read_excel(xls, sheet_name=aba)
        colunas_normalizadas = [normalizar(c) for c in df.columns]

        colunas_encontradas = {}
        colunas_sugeridas = {}
        colunas_restantes = set(df.columns)

        for chave, nomes in sinonimos.items():
            scores = []
            for coluna_original, coluna_norm in zip(df.columns, colunas_normalizadas):
                if coluna_original.lower().startswith("unnamed"):
                    continue
                score = max(
                    SequenceMatcher(None, coluna_norm, normalizar(nome)).ratio()
                    for nome in nomes
                )
                scores.append((coluna_original, score))

            if scores:
                melhor_coluna, melhor_score = max(scores, key=lambda x: x[1])
                if melhor_score >= 0.8:
                    colunas_encontradas[chave] = melhor_coluna
                    colunas_restantes.discard(melhor_coluna)
                else:
                    colunas_encontradas[chave] = None
                    colunas_sugeridas[chave] = sorted(
                        scores, key=lambda x: x[1], reverse=True
                    )[:3]
            else:
                colunas_encontradas[chave] = None

        for coluna in list(colunas_restantes):
            guess = inferir_coluna_por_conteudo(df[coluna], n=linhas_amostra)
            if guess:
                destino = guess
                if (
                    guess == "preco_unitario"
                    and colunas_encontradas.get("preco_unitario") is not None
                    and colunas_encontradas.get("preco_total") is None
                ):
                    destino = "preco_total"
                if colunas_encontradas.get(destino) is None:
                    colunas_encontradas[destino] = coluna
                    if coluna.lower().startswith("unnamed"):
                        df.rename(columns={coluna: destino}, inplace=True)
                        colunas_encontradas[destino] = destino

        print(f"\n📄 Analisando aba '{aba}':")
        for chave in sinonimos.keys():
            coluna = colunas_encontradas.get(chave)
            if coluna:
                print(f"  ✅ Coluna '{chave}' detectada: '{coluna}'")
            else:
                sugestoes = colunas_sugeridas.get(chave, [])
                if sugestoes:
                    sugestoes_str = ", ".join(
                        f"{col} ({score:.2f})" for col, score in sugestoes
                    )
                    print(
                        f"  ⚠️ Coluna '{chave}' não encontrada. Sugestões: {sugestoes_str}"
                    )
                else:
                    print(f"  ⚠️ Coluna '{chave}' não encontrada.")

        if colunas_encontradas.get("produto") and colunas_encontradas.get("tamanho"):
            return df, aba, colunas_encontradas

        print(
            "  ⚠️ Colunas obrigatórias 'produto' e 'tamanho' não encontradas nesta aba."
        )

    raise ValueError("❌ Colunas obrigatórias não encontradas!")
