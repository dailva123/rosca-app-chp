import os
import cv2
import numpy as np
import tempfile
import logging
from fastapi import FastAPI, UploadFile, Form, File
from fastapi.responses import JSONResponse, FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from ultralytics import YOLO

# ================================
# Configuração de logging
# ================================
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ================================
# Inicialização do FastAPI
# ================================
app = FastAPI()

# 🚀 CORS liberado para o front funcionar no Render
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # pode restringir depois se quiser
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Servir arquivos estáticos
app.mount("/static", StaticFiles(directory="static"), name="static")

# ================================
# Modelo YOLOv8 (Lazy Load)
# ================================
MODEL_PATH = os.getenv("YOLO_MODEL_PATH", "best.pt")  # Arquivo deve estar no repositório raiz
model = None
NAMES = {}

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
# Funções utilitárias
# ================================
def load_model():
    global model, NAMES
    if model is None:
        if not os.path.exists(MODEL_PATH):
            logger.error(f"❌ Modelo não encontrado em {MODEL_PATH}")
        logger.info(f"🔄 Carregando modelo YOLOv8: {MODEL_PATH}")
        model = YOLO(MODEL_PATH)
        NAMES = model.names
        logger.info(f"✅ Modelo carregado com {len(NAMES)} classes: {NAMES}")
    return model

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
    mdl = load_model()
    img = cv2.imread(imagem_path)
    if img is None:
        logger.error("❌ Falha ao carregar imagem.")
        return -1, None

    # Redimensionar (max 800px)
    scale_factor = 800 / max(img.shape[:2])
    img = cv2.resize(img, (int(img.shape[1] * scale_factor), int(img.shape[0] * scale_factor)))

    results = mdl(img, verbose=False)[0]

    cartao_px = None
    rosca_px = None

    for box in results.boxes:
        cls_id = int(box.cls[0])
        x1, y1, x2, y2 = map(int, box.xyxy[0].tolist())
        largura, altura = x2 - x1, y2 - y1
        label = NAMES.get(cls_id, str(cls_id)).lower()

        logger.info(f"📦 Detectado: {label} ({cls_id}) - {largura:.1f}x{altura:.1f}px")

        # 🔑 Aceita diferentes nomes para as classes
        if label in ["cartao", "card"]:
            cartao_px = max(largura, altura)
            cv2.rectangle(img, (x1, y1), (x2, y2), (255, 0, 0), 2)
            cv2.putText(img, "Cartão", (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 0, 0), 2)

        elif label in ["rosca", "thread", "screw"]:
            rosca_px = max(largura, altura)
            cv2.rectangle(img, (x1, y1), (x2, y2), (0, 255, 0), 2)
            cv2.putText(img, "Rosca", (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)

    # Nome único para debug
    debug_filename = f"debug_{next(tempfile._get_candidate_names())}.png"
    debug_path = os.path.join("static", debug_filename)
    cv2.imwrite(debug_path, img)

    if not cartao_px or not rosca_px:
        logger.warning("⚠️ Não encontrou cartao ou rosca na imagem.")
        return -1, debug_path

    escala = CARTAO_LARGURA_MM / cartao_px
    diametro_mm = rosca_px * escala
    logger.info(f"📏 Diametro calculado: {diametro_mm:.2f} mm")
    return diametro_mm, debug_path

# ================================
# Rotas FastAPI
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

@app.post("/analisar")
async def analisar(file: UploadFile = File(...), interna: str = Form("false")):
    try:
        if not file:
            return JSONResponse(content={"erro": "📷 Nenhum arquivo recebido."}, status_code=400)

        is_interna = interna.strip().lower() in ["true", "1", "yes"]

        ext = os.path.splitext(file.filename or "")[1].lower()
        if ext not in [".png", ".jpg", ".jpeg"]:
            ext = ".png"

        with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as tmp:
            tmp.write(await file.read())
            temp_path = tmp.name

        diametro_medido, debug_path = medir_diametro_yolo(temp_path, is_interna)

        if diametro_medido <= 0:
            return JSONResponse(content={
                "erro": "❌ Não foi possível identificar a rosca/cartão.",
                "debug": f"/{debug_path}"
            }, status_code=400)

        norma, bitola, diametro_ref, confianca, tipo = fator_decisao(diametro_medido, is_interna)

        if not norma:
            return JSONResponse(content={
                "erro": "⚠️ Medida não corresponde a norma conhecida.",
                "diametro_medido_mm": f"{diametro_medido:.2f}",
                "debug": f"/{debug_path}"
            }, status_code=400)

        return JSONResponse(content={
            "status": "ok",
            "tipo_rosca": "Rosca interna (fêmea)" if is_interna else "Rosca externa (macho)",
            "diametro_medido_mm": f"{diametro_medido:.2f}",
            "bitola": bitola,
            "norma": norma,
            "confianca": f"{confianca:.1f}%",
            "observacao": "ℹ️ Detecção feita por IA (YOLOv8).",
            "debug": f"/{debug_path}"
        })

    except Exception as e:
        logger.exception("💥 Erro inesperado no endpoint /analisar")
        return JSONResponse(content={"erro": f"💥 Erro inesperado: {str(e)}"}, status_code=500)

# ================================
# Health Check para Render
# ================================
@app.get("/healthz")
def health_check():
    return {"status": "ok"}
