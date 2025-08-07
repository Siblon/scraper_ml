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
DEBUG_SINGLE_ITEM = False

# Lista global de resultados coletados
resultados_parciais: list[dict] = []


def log(msg: str) -> None:
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")


def salvar_resultado_dataframe(df: pd.DataFrame, prefix: str = NOME_BASE_SAIDA) -> Optional[str]:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    nome_saida = f"{prefix}_{timestamp}.xlsx"
    pasta_planilhas = "planilhas"
    os.makedirs(pasta_planilhas, exist_ok=True)
    caminho_saida = os.path.join(pasta_planilhas, nome_saida)

    try:
        df.to_excel(caminho_saida, index=False)
        log(f"💾 Resultados salvos em: {caminho_saida}")
        return caminho_saida
    except Exception as e:
        log(f"❌ Erro ao salvar planilha: {e}")
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
    log("🚀 Iniciando scraping...")
    log("🔍 Lendo planilha...")
    df, _, info_colunas = encontrar_colunas_necessarias(NOME_ARQUIVO)
    coluna_principal = info_colunas["principal"]
    coluna_modelo = next((c for c in info_colunas["extras"] if c.lower() == "modelo"), None)

    df_busca = montar_dataframe_buscas(df, coluna_principal, coluna_modelo)
    if DEBUG_SINGLE_ITEM:
        df_busca = df_busca.head(1)

    log(f"🔎 {len(df_busca)} itens encontrados para busca.\n")
    log("🔗 Iniciando buscas no Mercado Livre...\n")

    try:
        for i, linha in df_busca.iterrows():
            termo = linha["Descrição do Item"]
            log(f"🔍 ({i+1}/{len(df_busca)}) Buscando: {termo}")

            resultado_linha = buscar_links_para_itens(pd.DataFrame([linha]))
            if not resultado_linha.empty:
                resultados_parciais.append(resultado_linha.iloc[0].to_dict())

    except KeyboardInterrupt:
        log("\n🛑 Interrupção manual detectada (Ctrl+C).")

    finally:
        if resultados_parciais:
            df_final = pd.DataFrame(resultados_parciais)
            try:
                resposta = input("Deseja salvar a planilha agora? (s/n) ").strip().lower()
            except (KeyboardInterrupt, EOFError):
                resposta = "n"

            if resposta == "s":
                caminho_planilha = salvar_resultado_dataframe(df_final)
                if caminho_planilha:
                    log(f"📁 Planilha criada em: {caminho_planilha}")
            else:
                caminho_temp = salvar_resultado_dataframe(df_final, prefix="resultado_temp")
                if caminho_temp:
                    log(f"💾 Backup temporário salvo em: {caminho_temp}")
        else:
            log("⚠️ Nenhum dado coletado.")

        tempo_total = round(time.time() - inicio_total, 2)
        log(f"⏱️ Tempo total de execução: {tempo_total}s")
        log("✅ Scraping finalizado.")


if __name__ == "__main__":
    main()
