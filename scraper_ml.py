from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.common.exceptions import WebDriverException
import pandas as pd
import time
import random
import unicodedata

# ============ CONFIGURAÇÕES ============

NOME_ARQUIVO = "LISTA ADIDAS 31 07 2025.xlsx"
COLUNA_PRODUTO = "descricao do item"
COLUNA_TAMANHO = "tam"
LIMITE_PRODUTOS = 50
DELAY_MIN = 5
DELAY_MAX = 10

# ============ FUNÇÕES ============

def normalizar(texto):
    if not isinstance(texto, str):
        return ""
    return unicodedata.normalize('NFKD', texto).encode('ASCII', 'ignore').decode('utf-8').strip().lower()

def encontrar_colunas_necessarias(caminho_arquivo, col_produto_nome, col_tam_nome):
    xls = pd.ExcelFile(caminho_arquivo)
    for aba in xls.sheet_names:
        df = pd.read_excel(xls, sheet_name=aba)
        colunas_normalizadas = [normalizar(c) for c in df.columns]
        col_produto_norm = normalizar(col_produto_nome)
        col_tam_norm = normalizar(col_tam_nome)

        if col_produto_norm in colunas_normalizadas:
            idx_prod = colunas_normalizadas.index(col_produto_norm)
            col_produto = df.columns[idx_prod]
            col_modelo = df.columns[idx_prod + 1] if idx_prod + 1 < len(df.columns) else None

            if col_tam_norm in colunas_normalizadas:
                idx_tam = colunas_normalizadas.index(col_tam_norm)
                col_tam = df.columns[idx_tam]
            else:
                raise ValueError("❌ Coluna de tamanho não encontrada!")

            return df, aba, col_produto, col_modelo, col_tam
    raise ValueError("❌ Colunas obrigatórias não encontradas!")

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
df, aba, col_produto, col_modelo, col_tam = encontrar_colunas_necessarias(NOME_ARQUIVO, COLUNA_PRODUTO, COLUNA_TAMANHO)

resultados = []
total_processados = 0

try:
    for index, row in df.iterrows():
        if total_processados >= LIMITE_PRODUTOS:
            break

        nome_produto = str(row[col_produto])
        modelo_produto = str(row[col_modelo]) if col_modelo else ""
        tamanho = row[col_tam]
        tipo = classificar_tipo(tamanho)

        termo_busca = f"{nome_produto} {modelo_produto} {tipo}"
        print(f"🔎 Buscando: {termo_busca}")

        try:
            precos = buscar_preco(termo_busca)
            media = round(sum(precos)/len(precos), 2) if precos else None
            qtd_resultados = len(precos)
        except Exception as e:
            print(f"❌ Erro ao buscar: {e}")
            media = None
            qtd_resultados = "Erro"

        resultados.append({
            "Nome do Produto": nome_produto,
            "Modelo": modelo_produto,
            "Tamanho": tamanho,
            "Tipo": tipo,
            "Preço Médio": media,
            "Qtd Resultados": qtd_resultados
        })

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
