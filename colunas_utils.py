import pandas as pd
import unicodedata
import re
from difflib import SequenceMatcher


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


def encontrar_colunas_necessarias(caminho_arquivo, sinonimos):
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
        for chave, nomes in sinonimos.items():
            # Calcula similaridade de cada coluna com os sinônimos
            scores = []
            for coluna_original, coluna_norm in zip(df.columns, colunas_normalizadas):
                score = max(
                    SequenceMatcher(None, coluna_norm, normalizar(nome)).ratio()
                    for nome in nomes
                )
                scores.append((coluna_original, score))

            # Melhor correspondência para a chave
            melhor_coluna, melhor_score = max(scores, key=lambda x: x[1])
            if melhor_score >= 0.8:
                colunas_encontradas[chave] = melhor_coluna
            else:
                colunas_encontradas[chave] = None
                # Guarda as melhores sugestões (top 3)
                colunas_sugeridas[chave] = sorted(
                    scores, key=lambda x: x[1], reverse=True
                )[:3]

        print(f"\n📄 Analisando aba '{aba}':")
        for chave, nomes in sinonimos.items():
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

