import requests
import os

# ================================
# Configuração
# ================================
file_path = r"C:\backend\uploads\fototeste.png"

# URL base da API (Render ou local)
# 🔹 Se a variável API_URL estiver definida no ambiente, usa ela
# 🔹 Senão, usa o localhost padrão
BASE_URL = os.getenv("API_URL", "http://127.0.0.1:8000")
url = f"{BASE_URL}/analisar"

# ================================
# Envio da requisição
# ================================
try:
    with open(file_path, "rb") as f:
        files = {"file": f}
        data = {"interna": "false"}  # "true" para rosca interna
        response = requests.post(url, files=files, data=data)

    print("Status:", response.status_code)

    try:
        resp_json = response.json()
        print("Resposta JSON:", resp_json)

        if "debug" in resp_json:
            debug_url = f"{BASE_URL}{resp_json['debug']}"
            print("👉 Veja a imagem de análise (debug):", debug_url)

    except Exception:
        print("Resposta bruta:", response.text)

except FileNotFoundError:
    print(f"❌ Arquivo não encontrado: {file_path}")
except requests.exceptions.ConnectionError:
    print(f"❌ Não foi possível conectar em {url}. O servidor está rodando?")
except Exception as e:
    print("❌ Erro inesperado:", str(e))
