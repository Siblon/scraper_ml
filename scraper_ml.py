from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.common.exceptions import WebDriverException
import pandas as pd
import time
import random
import sys

from colunas_utils import encontrar_colunas_necessarias, preprocessar_planilha

# ============ CONFIGURAÇÕES ============

NOME_ARQUIVO = "66.xlsx"
COLUNAS_SINONIMOS = {
    "produto": ["descricao do item", "nome", "produto", "descricao"],
    "modelo": ["modelo", "cod", "codigo", "referencia"],
    "tamanho": ["tamanho", "tam", "numero"],
    "quantidade": ["quantidade", "qtd", "qtde"],
    "preco_unitario": ["preco unitario", "valor unitario", "preco"],
    "preco_total": ["preco total", "valor total", "total"]
}
LIMITE_PRODUTOS = 50
DELAY_MIN = 5
DELAY_MAX = 10
DEBUG = True

# ============ FUNÇÕES ============

def configurar_driver():
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("--disable-gpu")
    options.add_argument("user-agent=Mozilla/5.0")
    return webdriver.Chrome(options=options)

def buscar_preco(consulta):
    driver = configurar_driver()
    try:
        url = f"https://lista.mercadolivre.com.br/{consulta}"
        driver.get(url)
        time.sleep(random.uniform(3, 5))

        precos_elementos = driver.find_elements(By.CSS_SELECTOR, "span.andes-money-amount__fraction")
        precos = []
        for p in precos_elementos:
            try:
                preco = float(p.text.replace(".", "").replace(",", "."))
                precos.append(preco)
            except:
                continue
        return precos
    except WebDriverException as e:
        print(f"❌ Erro ao buscar {consulta}: {e}")
        return []
    finally:
        driver.quit()

def classificar_tipo(tamanho):
    try:
        tam = int(tamanho)
        return "infantil" if tam <= 28 else "adulto"
    except:
        return "adulto"

# ============ EXECUÇÃO ============

print("🔍 Lendo planilha...")
df, aba, colunas = encontrar_colunas_necessarias(NOME_ARQUIVO, COLUNAS_SINONIMOS)
df = preprocessar_planilha(df)
print(f"✅ Colunas detectadas: {colunas}")

if DEBUG:
    print("🧪 Modo DEBUG ativo. Primeiros 3 itens:")
    print(df.head(3))
    sys.exit()

resultados = []
total_processados = 0

try:
    for index, row in df.iterrows():
        if total_processados >= LIMITE_PRODUTOS:
            break

        faltando = []
        for chave in ("produto", "tamanho"):
            coluna = colunas.get(chave)
            valor = row.get(coluna) if coluna else None
            if coluna is None or pd.isna(valor) or str(valor).strip() == "":
                faltando.append(chave)
        if faltando:
            print(f"⚠️ Linha {index} ignorada: dados ausentes em {', '.join(faltando)}.")
            continue

        nome_produto = str(row[colunas["produto"]])
        modelo_col = colunas.get("modelo")
        modelo_produto = (
            str(row[modelo_col])
            if modelo_col and not pd.isna(row.get(modelo_col))
            else ""
        )
        tamanho = row[colunas["tamanho"]]
        tipo = classificar_tipo(tamanho)

        termo_busca = f"{nome_produto} {modelo_produto} {tipo}"
        print(f"🔎 Buscando: {termo_busca}")

        try:
            precos = buscar_preco(termo_busca)
            media = round(sum(precos) / len(precos), 2) if precos else None
            qtd_resultados = len(precos)
        except Exception as e:
            print(f"❌ Erro ao buscar: {e}")
            media = None
            qtd_resultados = "Erro"

        resultados.append(
            {
                "Nome do Produto": nome_produto,
                "Modelo": modelo_produto,
                "Tamanho": tamanho,
                "Tipo": tipo,
                "Preço Médio": media,
                "Qtd Resultados": qtd_resultados,
            }
        )

        total_processados += 1
        delay = random.uniform(DELAY_MIN, DELAY_MAX)
        print(f"✅ Processados: {total_processados} de {LIMITE_PRODUTOS}")
        print(f"⏱️ Aguardando {round(delay, 2)} segundos...\n")
        time.sleep(delay)

except KeyboardInterrupt:
    print("🚨 Interrupção manual detectada. Salvando resultados parciais...")

finally:
    resultado_df = pd.DataFrame(resultados)
    arquivo_saida = f"resultado_precos_{int(time.time())}.xlsx"
    resultado_df.to_excel(arquivo_saida, index=False)
    print(f"✅ Resultados salvos em: {arquivo_saida}")
    print(f"🏁 Extração finalizada! Total processado: {total_processados}")

