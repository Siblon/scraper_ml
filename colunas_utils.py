import pandas as pd
import unicodedata
import re
from difflib import SequenceMatcher
from typing import Optional


def preprocessar_planilha(df: pd.DataFrame) -> pd.DataFrame:
    """Limpa valores com múltiplas entradas separadas por ``|``.

    Para cada célula do DataFrame, mantém apenas o primeiro segmento
    antes do caractere ``|`` e remove espaços extras nas extremidades.

    Examples
    --------
    >>> preprocessar_planilha(pd.DataFrame({"col": ["38|40|42", "Tênis | Adidas"]}))
        col
    0    38
    1  Tênis

    Parameters
    ----------
    df : pd.DataFrame
        DataFrame lido da planilha original.

    Returns
    -------
    pd.DataFrame
        Novo DataFrame com os valores sanitizados.
    """

    def limpar(valor):
        if isinstance(valor, str):
            return valor.split("|")[0].strip()
        return valor

    return df.applymap(limpar)


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


def detectar_linha_cabecalho(df: pd.DataFrame, sinonimos) -> int:
    """Detecta automaticamente a linha que contém os nomes das colunas.

    A heurística procura pela primeira linha que contenha pelo menos um
    dos termos esperados nos cabeçalhos, considerando os sinônimos
    informados. Caso nenhuma linha seja encontrada, assume-se a primeira
    linha como cabeçalho.

    Parameters
    ----------
    df : pd.DataFrame
        DataFrame lido da planilha sem cabeçalho.
    sinonimos : dict
        Dicionário de sinônimos das colunas esperadas.

    Returns
    -------
    int
        Índice da linha detectada como cabeçalho.
    """

    termos = {normalizar(chave) for chave in sinonimos.keys()}
    for nomes in sinonimos.values():
        termos.update(normalizar(n) for n in nomes)

    for idx, row in df.iterrows():
        normalizados = [normalizar(str(c)) for c in row]
        if any(c in termos for c in normalizados):
            return idx
    return 0


def inferir_coluna_por_conteudo(serie, n=5) -> Optional[str]:
    """Tenta inferir o tipo da coluna analisando as primeiras N linhas.

    As heurísticas levam em consideração:

    - ``produto``: presença de marcas conhecidas em texto;
    - ``tamanho``: inteiros entre 15 e 50;
    - ``quantidade``: inteiros entre 1 e 100;
    - ``preco_unitario/preco_total``: valores contendo ``","`` ou ``".``.
    """

    amostra = serie.dropna().astype(str).head(n).str.lower()
    if amostra.empty:
        return None

    texto = " ".join(amostra)
    produto_keywords = [
        "nike",
        "adidas",
        "tenis",
        "tênis",
        "sapato",
        "camisa",
        "calca",
        "calça",
    ]
    if any(k in texto for k in produto_keywords):
        return "produto"

    numeros = (
        amostra.str.replace(",", ".", regex=False)
        .str.extract(r"(-?\d+\.?\d*)")[0]
    )
    numeros = pd.to_numeric(numeros, errors="coerce")
    if numeros.notna().all():
        if (numeros % 1 == 0).all() and numeros.between(15, 50).all():
            return "tamanho"
        if (numeros % 1 == 0).all() and numeros.between(0, 99).all():
            return "quantidade"

    if amostra.str.contains(r"[,.]").all():
        return "preco_unitario"

    return None


def encontrar_colunas_necessarias(caminho_arquivo, sinonimos, linhas_amostra=5):
    """Lê a planilha e identifica dinamicamente as colunas necessárias.

    A função detecta automaticamente a linha que contém os nomes das
    colunas, remove as linhas acima dela e aplica a sanitização dos
    valores que possuam múltiplas entradas separadas por ``|``. Em
    seguida, tenta utilizar os cabeçalhos e seus sinônimos e, caso não
    seja possível, infere o tipo da coluna pelos primeiros valores.
    Colunas detectadas são renomeadas para os nomes padrão e o DataFrame
    retornado já possui essas colunas padronizadas.

    Retorna o DataFrame da aba encontrada, o nome da aba e um dicionário
    com as colunas mapeadas para produto, modelo, tamanho, quantidade,
    preço unitário e total.
    """
    xls = pd.ExcelFile(caminho_arquivo)
    for aba in xls.sheet_names:
        df_raw = pd.read_excel(xls, sheet_name=aba, header=None)
        linha_cabecalho = detectar_linha_cabecalho(df_raw, sinonimos)
        df = df_raw.iloc[linha_cabecalho + 1 :].copy()
        df.columns = df_raw.iloc[linha_cabecalho].fillna("").astype(str)
        df = preprocessar_planilha(df)
        colunas_normalizadas = [normalizar(c) for c in df.columns]

        colunas_encontradas = {}
        colunas_originais = {}
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
                    df.rename(columns={melhor_coluna: chave}, inplace=True)
                    colunas_encontradas[chave] = chave
                    colunas_originais[chave] = melhor_coluna
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
                    df.rename(columns={coluna: destino}, inplace=True)
                    colunas_encontradas[destino] = destino
                    colunas_originais[destino] = coluna

        print(f"\n📄 Analisando aba '{aba}':")
        for chave in sinonimos.keys():
            coluna = colunas_encontradas.get(chave)
            if coluna:
                original = colunas_originais.get(chave, coluna)
                print(f"  ✅ Coluna '{chave}' detectada: '{original}'")
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
