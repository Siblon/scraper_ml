from __future__ import annotations
import sys
import os
import time
from typing import Optional
from datetime import datetime

import pandas as pd

from buscar_links_ml import buscar_links_para_itens
from colunas_utils import encontrar_colunas_necessarias, montar_frase_busca


NOME_ARQUIVO = sys.argv[1] if len(sys.argv) > 1 else "66.xlsx"
NOME_BASE_SAIDA = "resultado_scraping"

# Lista global de resultados coletados
resultados_parciais: list[dict] = []


def salvar_resultado_dataframe(df: pd.DataFrame) -> Optional[str]:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    nome_saida = f"{NOME_BASE_SAIDA}_{timestamp}.xlsx"
    pasta_planilhas = "planilhas"
    os.makedirs(pasta_planilhas, exist_ok=True)
    caminho_saida = os.path.join(pasta_planilhas, nome_saida)

    try:
        df.to_excel(caminho_saida, index=False)
        print(f"💾 Resultados salvos em: {caminho_saida}")
        return caminho_saida
    except Exception as e:
        print(f"❌ Erro ao salvar planilha: {e}")
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
    inicio_total = time.time()
    print("🚀 Iniciando scraping...")
    print("🔍 Lendo planilha...")
    df, _, info_colunas = encontrar_colunas_necessarias(NOME_ARQUIVO)
    coluna_principal = info_colunas["principal"]
    coluna_modelo = next((c for c in info_colunas["extras"] if c.lower() == "modelo"), None)

    df_busca = montar_dataframe_buscas(df, coluna_principal, coluna_modelo)

    print(f"🔎 {len(df_busca)} itens encontrados para busca.\n")
    print("🔗 Iniciando buscas no Mercado Livre...\n")

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
            try:
                resposta = input("Deseja salvar os resultados encontrados? (s/n) ").strip().lower()
            except (KeyboardInterrupt, EOFError):
                resposta = "n"

            if resposta == "s":
                df_final = pd.DataFrame(resultados_parciais)
                caminho_planilha = salvar_resultado_dataframe(df_final)
                if caminho_planilha:
                    print(f"📁 Planilha criada em: {caminho_planilha}")
            else:
                print("🗑️ Resultados descartados.")
        else:
            print("⚠️ Nenhum dado coletado.")

        tempo_total = round(time.time() - inicio_total, 2)
        print(f"⏱️ Tempo total de execução: {tempo_total}s")
        print("✅ Scraping finalizado.")


if __name__ == "__main__":
    main()
