import pandas as pd
import unicodedata
import re
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


def normalizar_string(texto: str) -> str:
    """Normaliza strings para comparações resilientes.

    A função remove acentos, converte para minúsculas e elimina
    caracteres não alfanuméricos. É um wrapper amigável em torno da
    função :func:`normalizar` existente.

    Parameters
    ----------
    texto : str
        Texto de entrada que pode conter acentos ou pontuação.

    Returns
    -------
    str
        Versão sanitizada do texto.
    """

    return normalizar(texto)


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


def inferir_coluna_por_conteudo(
    serie, n=5, nome_coluna: Optional[str] = None
) -> Optional[str]:
    """Tenta inferir o tipo da coluna analisando as primeiras N linhas.

    Parameters
    ----------
    serie : pd.Series ou DataFrame
        Coluna a ser analisada. DataFrames devem possuir apenas uma
        coluna, caso contrário um ``TypeError`` será levantado.
    n : int, optional
        Número de linhas utilizadas para a inferência.

    As heurísticas levam em consideração:

    - ``produto``: presença de marcas conhecidas em texto;
    - ``tamanho``: inteiros entre 15 e 50;
    - ``quantidade``: inteiros entre 1 e 100;
    - ``preco_unitario/preco_total``: valores contendo ``","`` ou ``".``.
    - Detecção por nome da coluna para colunas principais, opcionais e
      irrelevantes.
    """

    if isinstance(serie, pd.DataFrame):
        if serie.shape[1] != 1:
            raise TypeError("'serie' deve ser uma Series ou DataFrame de uma única coluna")
        serie = serie.iloc[:, 0]
    if not isinstance(serie, pd.Series):
        raise TypeError("'serie' deve ser uma Series")

    nome_normalizado = normalizar_string(nome_coluna) if nome_coluna else ""
    principais = {"descricao", "nome", "item", "produto"}
    opcionais = {"modelo", "tamanho", "categoria", "subcategoria"}
    irrelevantes = {
        "codigoml",
        "sku",
        "quantidade",
        "endereco",
        "grade",
        "seller",
        "valor",
        "total",
        "vertical",
        "typeseller",
    }

    if any(chave in nome_normalizado for chave in irrelevantes):
        return None
    for chave in principais:
        if chave in nome_normalizado:
            return "produto"
    for chave in opcionais:
        if chave in nome_normalizado:
            return chave

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


def inferir_seguro(df: pd.DataFrame, coluna, n=5) -> Optional[str]:
    """Obtém coluna de forma resiliente e delega para ``inferir_coluna_por_conteudo``.

    Garante que ``coluna`` seja um nome válido do ``DataFrame`` e lida com
    casos de nomes duplicados ou colunas não encontradas. Nomes iniciados
    por ``Unnamed`` são ignorados.
    """
    nome = str(coluna).strip()
    if nome.lower().startswith("unnamed"):
        return None

    serie = df.get(nome)
    if serie is None:
        return None
    if isinstance(serie, pd.DataFrame):
        if serie.shape[1] == 0:
            return None
        serie = serie.iloc[:, 0]

    return inferir_coluna_por_conteudo(serie, n=n, nome_coluna=nome)


def encontrar_colunas_necessarias(caminho_arquivo: str):
    """Carrega a planilha e detecta as colunas relevantes.

    A função procura por uma coluna de descrição do produto aceitando
    variações como ``produto``, ``item`` ou ``descrição``. Colunas
    opcionais (``modelo``, ``tamanho``, ``categoria`` e ``subcategoria``)
    são utilizadas se estiverem presentes, enquanto colunas irrelevantes
    como ``sku`` ou ``quantidade`` são ignoradas. Todas as análises são
    realizadas de maneira case-insensitive e sem acentuação para garantir
    robustez contra planilhas com nomes diferentes.

    Parameters
    ----------
    caminho_arquivo : str
        Caminho para o arquivo Excel a ser analisado.

    Returns
    -------
    tuple
        ``(df, aba, info)`` onde ``df`` é o DataFrame sanitizado da aba
        analisada, ``aba`` é o nome da aba utilizada e ``info`` é um
        dicionário contendo:

        ``principal`` : nome da coluna de descrição do produto
        ``extras`` : lista de colunas opcionais aproveitadas
        ``ignoradas`` : lista de colunas irrelevantes identificadas

    Raises
    ------
    ValueError
        Se nenhuma coluna de descrição do produto for encontrada em
        nenhuma aba do arquivo.
    """

    obrigatorias = [
        "produto",
        "item",
        "nome",
        "descrição",
        "descrição do item",
    ]
    opcionais = ["modelo", "tamanho", "categoria", "subcategoria"]
    irrelevantes = [
        "quantidade",
        "qtd",
        "qtde",
        "código ml",
        "codigo ml",
        "sku",
        "valor unit",
        "valor unitario",
        "preço unitario",
        "preco unitario",
        "valor total",
        "preço total",
        "preco total",
        "valor",
        "total",
        "vertical",
        "type seller",
        "endereço",
        "grade",
    ]

    # sinônimos mínimos para detecção da linha de cabeçalho
    sinonimos_cabecalho = {"produto": obrigatorias}
    for opc in opcionais:
        sinonimos_cabecalho[opc] = [opc]

    xls = pd.ExcelFile(caminho_arquivo)
    for aba in xls.sheet_names:
        df_raw = pd.read_excel(xls, sheet_name=aba, header=None)
        linha_cabecalho = detectar_linha_cabecalho(df_raw, sinonimos_cabecalho)
        df = df_raw.iloc[linha_cabecalho + 1 :].copy()
        df.columns = df_raw.iloc[linha_cabecalho].fillna("").astype(str).str.strip()
        df = preprocessar_planilha(df)

        colunas_norm = {col: normalizar_string(col) for col in df.columns}

        # coluna principal
        obrig_norm = [normalizar_string(c) for c in obrigatorias]
        principal = None
        for original, norm in colunas_norm.items():
            if any(chave in norm for chave in obrig_norm):
                principal = original
                break
        if principal is None:
            continue

        # opcionais
        opcionais_norm = [normalizar_string(c) for c in opcionais]
        extras = []
        for original, norm in colunas_norm.items():
            if original == principal:
                continue
            if any(chave in norm for chave in opcionais_norm):
                extras.append(original)

        # irrelevantes
        irrelevantes_norm = [normalizar_string(c) for c in irrelevantes]
        ignoradas = []
        for original, norm in colunas_norm.items():
            if any(chave in norm for chave in irrelevantes_norm):
                ignoradas.append(original)

        extras_msg = ", ".join(extras) if extras else "nenhuma"
        ignoradas_msg = ", ".join(ignoradas) if ignoradas else "nenhuma"
        print(f"✔ Coluna principal identificada: {principal}")
        print(f"➕ Colunas extras incluídas: {extras_msg}")
        print(f"🚫 Colunas ignoradas: {ignoradas_msg}")

        info = {"principal": principal, "extras": extras, "ignoradas": ignoradas}
        return df, aba, info

    raise ValueError("Nenhuma coluna de descrição do produto foi encontrada.")


def identificar_colunas_busca(df: pd.DataFrame):
    """Identifica colunas relevantes para montagem da frase de busca.

    A função aceita diferentes nomes para a coluna principal de
    descrição (``produto``, ``item``, ``nome``, ``descrição`` ou
    ``descrição do item``). Outras colunas como ``modelo``, ``tamanho``,
    ``categoria`` e ``subcategoria`` são utilizadas apenas se estiverem
    presentes. Colunas consideradas irrelevantes, como ``quantidade`` ou
    ``sku``, são listadas e ignoradas automaticamente. Os nomes das
    colunas são comparados de forma case-insensitive e sem acentuação.

    Parameters
    ----------
    df : pd.DataFrame
        DataFrame com os dados da planilha original.

    Returns
    -------
    tuple
        (coluna_principal, colunas_opcionais, colunas_ignoradas)
    """

    # sinônimos aceitos para a coluna principal de descrição
    obrigatorias = [
        "produto",
        "item",
        "nome",
        "descrição",
        "descrição do item",
    ]

    # colunas que enriquecem a busca quando disponíveis
    opcionais = ["modelo", "tamanho", "categoria", "subcategoria"]

    # colunas que não devem ser consideradas durante a busca
    irrelevantes = [
        "quantidade",
        "código ml",
        "sku",
        "endereço",
        "grade",
        "valor unit",
        "preco unitario",
        "valor total",
        "preco total",
        "vertical",
        "type seller",
    ]

    # Normaliza nomes das colunas
    colunas_norm = {col: normalizar_string(col) for col in df.columns}

    # Identifica coluna principal
    obrigatorias_norm = [normalizar_string(k) for k in obrigatorias]
    coluna_principal = None
    for original, norm in colunas_norm.items():
        if any(chave in norm for chave in obrigatorias_norm):
            coluna_principal = original
            break
    if coluna_principal is None:
        raise ValueError("Nenhuma coluna de descrição do produto foi encontrada.")

    # Colunas opcionais
    opcionais_norm = [normalizar_string(k) for k in opcionais]
    colunas_opcionais = []
    for original, norm in colunas_norm.items():
        if original == coluna_principal:
            continue
        if any(chave in norm for chave in opcionais_norm):
            colunas_opcionais.append(original)

    # Colunas irrelevantes
    irrelevantes_norm = [normalizar_string(k) for k in irrelevantes]
    colunas_ignoradas = []
    for original, norm in colunas_norm.items():
        if any(chave in norm for chave in irrelevantes_norm):
            colunas_ignoradas.append(original)

    extras_msg = ", ".join(colunas_opcionais) if colunas_opcionais else "nenhuma"
    ignoradas_msg = ", ".join(colunas_ignoradas) if colunas_ignoradas else "nenhuma"
    print(f"✔ Coluna principal identificada: {coluna_principal}")
    print(f"➕ Colunas extras incluídas: {extras_msg}")
    print(f"🚫 Colunas ignoradas: {ignoradas_msg}")

    return coluna_principal, colunas_opcionais, colunas_ignoradas


def montar_frase_busca(row: pd.Series, coluna_principal: str, colunas_opcionais):
    """Constrói a frase de busca a partir das colunas relevantes.

    Parameters
    ----------
    row : pd.Series
        Linha da planilha com os dados do produto.
    coluna_principal : str
        Nome da coluna de descrição do item.
    colunas_opcionais : list
        Lista de colunas adicionais a serem consideradas.

    Returns
    -------
    str
        Frase pronta para a busca.
    """

    partes = [str(row.get(coluna_principal, "")).strip()]
    for coluna in colunas_opcionais:
        valor = row.get(coluna)
        if pd.notna(valor) and str(valor).strip():
            partes.append(str(valor).strip())
    return " ".join(partes).strip()
