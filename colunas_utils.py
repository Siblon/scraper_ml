import pandas as pd
import unicodedata


def normalizar(texto):
    if not isinstance(texto, str):
        return ""
    return (
        unicodedata.normalize("NFKD", texto)
        .encode("ASCII", "ignore")
        .decode("utf-8")
        .strip()
        .lower()
    )


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
        for chave, nomes in sinonimos.items():
            encontrado = None
            for nome in nomes:
                nome_norm = normalizar(nome)
                if nome_norm in colunas_normalizadas:
                    idx = colunas_normalizadas.index(nome_norm)
                    encontrado = df.columns[idx]
                    break
            colunas_encontradas[chave] = encontrado

        if colunas_encontradas.get("produto") and colunas_encontradas.get("tamanho"):
            return df, aba, colunas_encontradas

    raise ValueError("❌ Colunas obrigatórias não encontradas!")

