from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.common.exceptions import WebDriverException
import pandas as pd
import time
import random
import unicodedata

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

# ============ FUNÇÕES ============

def normalizar(texto):
    if not isinstance(texto, str):
        return ""
    return unicodedata.normalize('NFKD', texto).encode('ASCII', 'ignore').decode('utf-8').strip().lower()

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
print(f"✅ Colunas detectadas: {colunas}")

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

