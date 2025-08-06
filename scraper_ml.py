from __future__ import annotations
import sys
import os
import signal
from typing import Optional
from datetime import datetime

import pandas as pd

from buscar_links_ml import buscar_links_para_itens
from colunas_utils import encontrar_colunas_necessarias, montar_frase_busca


NOME_ARQUIVO = sys.argv[1] if len(sys.argv) > 1 else "66.xlsx"
NOME_BASE_SAIDA = "resultado_scraping"

# Lista global de resultados para salvar parcialmente
resultados_parciais: list[dict] = []


def salvar_resultado_parcial_em_excel() -> Optional[str]:
    if not resultados_parciais:
        print("⚠️ Nenhum resultado parcial para salvar.")
        return None

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    nome_saida = f"{NOME_BASE_SAIDA}_parcial_{timestamp}.xlsx"
    pasta_planilhas = "planilhas"
    os.makedirs(pasta_planilhas, exist_ok=True)
    caminho_saida = os.path.join(pasta_planilhas, nome_saida)

    try:
        df_parcial = pd.DataFrame(resultados_parciais)
        df_parcial.to_excel(caminho_saida, index=False)
        print(f"💾 Salvamento parcial realizado em: {caminho_saida}")
        return caminho_saida
    except Exception as e:
        print(f"❌ Erro ao salvar parcial: {e}")
        return None


def montar_dataframe_buscas(
    df: pd.DataFrame, coluna_principal: str, coluna_modelo: Optional[str]
) -> pd.DataFrame:
    colunas_extras = [coluna_modelo] if coluna_modelo else []
    termos: list[str] = []
    for _, row in df.iterrows():
        termo = montar_frase_busca(row, coluna_principal, colunas_extras)
        if termo:
            termos.append(termo)
    return pd.DataFrame({"Descrição do Item": termos})


def main() -> None:
    print("🔍 Lendo planilha...")
    df, _, info_colunas = encontrar_colunas_necessarias(NOME_ARQUIVO)
    coluna_principal = info_colunas["principal"]
    coluna_modelo = next((c for c in info_colunas["extras"] if c.lower() == "modelo"), None)

    df_busca = montar_dataframe_buscas(df, coluna_principal, coluna_modelo)

    print(f"🔎 {len(df_busca)} itens encontrados para busca.\n")
    print("🔗 Iniciando buscas no Mercado Livre...\n")

    caminho_planilha: Optional[str] = None

    try:
        for i, linha in df_busca.iterrows():
            termo = linha["Descrição do Item"]
            print(f"🔍 ({i+1}/{len(df_busca)}) Buscando: {termo}")

            resultado_linha = buscar_links_para_itens(pd.DataFrame([linha]))
            if not resultado_linha.empty:
                resultados_parciais.append(resultado_linha.iloc[0].to_dict())

    except KeyboardInterrupt:
        print("\n🛑 Interrupção manual detectada (Ctrl+C).")

    finally:
        if resultados_parciais:
            caminho_planilha = salvar_resultado_parcial_em_excel()
            if caminho_planilha:
                try:
                    resposta = input("Deseja salvar a planilha gerada? (s/n): ").strip().lower()
                except (KeyboardInterrupt, EOFError):
                    resposta = "n"
                if resposta != "s":
                    os.remove(caminho_planilha)
                    print("🗑️ Planilha temporária descartada.")
                else:
                    print(f"📁 Planilha mantida em: {caminho_planilha}")
        else:
            print("⚠️ Nenhum dado coletado. Nada para salvar.")

        print("\n⏹️ Execução finalizada.")


if __name__ == "__main__":
    main()
