"""Fluxo completo de busca de links no Mercado Livre.

Este script lê uma planilha Excel, identifica automaticamente a coluna
principal que descreve o item e utiliza essa informação para buscar os
primeiros links no Mercado Livre através da função
``buscar_links_para_itens``.

Caso a planilha possua uma coluna ``Modelo``, ela é adicionada ao termo de
busca para tornar a consulta mais específica. Os resultados são exibidos no
console e também exportados para ``resultados_busca.xlsx``.
"""

from __future__ import annotations

import sys
from typing import Optional

import pandas as pd

from buscar_links_ml import buscar_links_para_itens
from colunas_utils import encontrar_colunas_necessarias, montar_frase_busca


# Nome padrão da planilha; pode ser sobrescrito via argumento de linha de
# comando para tornar o script reutilizável com arquivos semelhantes.
NOME_ARQUIVO = sys.argv[1] if len(sys.argv) > 1 else "66.xlsx"

# Nome do arquivo de saída contendo os links encontrados.
ARQUIVO_RESULTADO = "resultados_busca.xlsx"


def montar_dataframe_buscas(
    df: pd.DataFrame, coluna_principal: str, coluna_modelo: Optional[str]
) -> pd.DataFrame:
    """Cria um ``DataFrame`` com os termos de busca.

    Cada linha da planilha original é transformada em um termo de busca
    combinando a coluna principal e, se disponível, a coluna ``Modelo``.
    Linhas vazias são ignoradas.
    """

    colunas_extras = [coluna_modelo] if coluna_modelo else []

    termos: list[str] = []
    for _, row in df.iterrows():
        termo = montar_frase_busca(row, coluna_principal, colunas_extras)
        if termo:
            termos.append(termo)

    return pd.DataFrame({"Descrição do Item": termos})


def main() -> None:
    """Executa o fluxo de leitura, busca e exportação dos resultados."""

    print("🔍 Lendo planilha...")
    df, _, info_colunas = encontrar_colunas_necessarias(NOME_ARQUIVO)
    coluna_principal = info_colunas["principal"]

    # Verifica se existe uma coluna "Modelo" entre as colunas extras
    coluna_modelo = next(
        (c for c in info_colunas["extras"] if c.lower() == "modelo"), None
    )

    df_busca = montar_dataframe_buscas(df, coluna_principal, coluna_modelo)

    print("🔗 Buscando links no Mercado Livre...")
    resultado_df = buscar_links_para_itens(df_busca)

    print("\n📄 Primeiros resultados:")
    print(resultado_df.head())

    resultado_df.to_excel(ARQUIVO_RESULTADO, index=False)
    print(f"\n✅ Resultados salvos em: {ARQUIVO_RESULTADO}")


if __name__ == "__main__":  # pragma: no cover - ponto de entrada do script
    main()

