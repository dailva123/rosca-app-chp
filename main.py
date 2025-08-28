import os
import cv2
import numpy as np
import tempfile
from fastapi import FastAPI, UploadFile, Form, File
from fastapi.responses import JSONResponse, FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from ultralytics import YOLO

# ================================
# Inicialização do FastAPI
# ================================
app = FastAPI()

# Servir arquivos estáticos
app.mount("/static", StaticFiles(directory="static"), name="static")

# ================================
# Modelo YOLOv8 (Lazy Load)
# ================================
model = None  # só será carregado na 1ª requisição

# Dimensão real do cartão ISO/IEC 7810 ID-1
CARTAO_LARGURA_MM = 85.6

# ================================
# Tabelas oficiais simuladas (mm)
# ================================
TABELA_ROSCAS = {
    "BSP": {
        "externa": {"1/8": 9.7, "1/4": 13.2, "3/8": 16.7, "1/2": 20.9, "3/4": 26.4, "1": 33.2},
        "interna": {"1/8": 8.5, "1/4": 11.8, "3/8": 15.3, "1/2": 19.0, "3/4": 24.5, "1": 30.3}
    },
    "NPT": {
        "externa": {"1/8": 10.2, "1/4": 13.7, "3/8": 17.1, "1/2": 21.3, "3/4": 26.7, "1": 33.5},
        "interna": {"1/8": 8.7, "1/4": 11.9, "3/8": 15.5, "1/2": 19.3, "3/4": 24.9, "1": 30.8}
    },
    "UNF": {
        "externa": {"1/4": 6.35, "3/8": 9.53, "1/2": 12.7, "3/4": 19.05, "1": 25.4},
        "interna": {"1/4": 5.8, "3/8": 8.8, "1/2": 12.0, "3/4": 18.3, "1": 24.5}
    }
}

# ================================
# Função de decisão
# ================================
def fator_decisao(diametro_medido: float, interna: bool):
    tipo = "interna" if interna else "externa"
    candidatos = []
    for norma, dados in TABELA_ROSCAS.items():
        for bitola, diametro_ref in dados[tipo].items():
            if abs(diametro_medido - diametro_ref) <= 0.5:  # tolerância
                candidatos.append((norma, bitola, diametro_ref))
    if not candidatos:
        return None, None, None, 0.0, tipo
    norma, bitola, diametro_ref = candidatos[0]
    return norma, bitola, diametro_ref, 95.0, tipo

# ================================
# Função principal: medir com YOLO
# ================================
def medir_diametro_yolo(imagem_path, interna: bool):
    global model
    if model is None:
        model = YOLO("yolov8n.pt")  # carrega apenas na 1ª vez

    img = cv2.imread(imagem_path)
    if img is None:
        return -1, None

    # Redimensionar para acelerar
    scale_factor = 800 / max(img.shape[:2])
    img = cv2.resize(img, (int(img.shape[1] * scale_factor), int(img.shape[0] * scale_factor)))

    # Rodar YOLO
    results = model(img, verbose=False)[0]

    cartao_px = None
    rosca_px = None

    for box in results.boxes:
        cls_id = int(box.cls[0])
        x1, y1, x2, y2 = box.xyxy[0].tolist()
        largura = x2 - x1
        altura = y2 - y1

        # ⚠️ IMPORTANTE: ajuste IDs conforme seu dataset custom
        if cls_id == 0:  # supomos "cartao"
            cartao_px = max(largura, altura)
            cv2.rectangle(img, (int(x1), int(y1)), (int(x2), int(y2)), (255, 0, 0), 2)
        elif cls_id == 1:  # supomos "rosca"
            rosca_px = max(largura, altura)
            cv2.rectangle(img, (int(x1), int(y1)), (int(x2), int(y2)), (0, 255, 0), 2)

    # Salvar imagem debug
    debug_path = os.path.join("static", "debug_output.png")
    cv2.imwrite(debug_path, img)

    if not cartao_px or not rosca_px:
        return -1, debug_path

    escala = CARTAO_LARGURA_MM / cartao_px
    diametro_mm = rosca_px * escala
    return diametro_mm, debug_path

# ================================
# Endpoint: Home (HTML principal)
# ================================
@app.get("/", response_class=HTMLResponse)
def home():
    return FileResponse("static/index.html")

@app.get("/termos", response_class=HTMLResponse)
def termos():
    return FileResponse("static/termos.html")

@app.get("/privacidade", response_class=HTMLResponse)
def privacidade():
    return FileResponse("static/privacidade.html")

# ================================
# Endpoint de análise
# ================================
@app.post("/analisar")
async def analisar(file: UploadFile = File(None), interna: str = Form(None)):
    try:
        if file is None:
            return JSONResponse(content={"erro": "📷 Por favor, selecione uma foto."}, status_code=400)
        if interna is None:
            return JSONResponse(content={"erro": "🔧 Informe se a rosca é interna ou externa."}, status_code=400)

        ext = os.path.splitext(file.filename)[1].lower()
        if ext not in [".png", ".jpg", ".jpeg"]:
            ext = ".png"

        with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as tmp:
            tmp.write(await file.read())
            temp_path = tmp.name

        diametro_medido, debug_path = medir_diametro_yolo(temp_path, interna.lower() == "true")

        if diametro_medido <= 0:
            return JSONResponse(content={
                "erro": "❌ Não foi possível identificar a rosca/cartão.",
                "debug": "/static/debug_output.png"
            }, status_code=400)

        norma, bitola, diametro_ref, confianca, tipo = fator_decisao(diametro_medido, interna.lower() == "true")

        if not norma:
            return JSONResponse(content={
                "erro": "⚠️ Medida não corresponde a norma conhecida.",
                "diametro_medido_mm": f"{diametro_medido:.2f}",
                "debug": "/static/debug_output.png"
            }, status_code=400)

        return JSONResponse(content={
            "status": "ok",
            "tipo_rosca": "Rosca interna (fêmea)" if interna.lower() == "true" else "Rosca externa (macho)",
            "diametro_medido_mm": f"{diametro_medido:.2f}",
            "bitola": bitola,
            "norma": norma,
            "confianca": f"{confianca:.1f}%",
            "observacao": "ℹ️ Detecção feita por IA (YOLOv8).",
            "debug": "/static/debug_output.png"
        })

    except Exception as e:
        return JSONResponse(content={"erro": f"💥 Erro inesperado: {str(e)}"}, status_code=500)
