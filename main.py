import os
import cv2
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

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory="static"), name="static")

# ================================
# Modelo YOLO
# ================================
MODEL_PATH = "runs/detect/train12/weights/best.pt"
CARTAO_LARGURA_MM = 85.6

model = YOLO(MODEL_PATH)
NAMES = model.names
logger.info(f"✅ Modelo carregado: {MODEL_PATH} com classes {NAMES}")

# ================================
# Tabelas oficiais (mm)
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
def fator_decisao(diametro_medido: float, interna: bool):
    tipo = "interna" if interna else "externa"

    # 1️⃣ Alta precisão (±0.2 mm)
    for norma, dados in TABELA_ROSCAS.items():
        for bitola, diametro_ref in dados[tipo].items():
            if abs(diametro_medido - diametro_ref) <= 0.2:
                return norma, bitola, diametro_ref, 99.0

    # 2️⃣ Média precisão (±0.5 mm)
    for norma, dados in TABELA_ROSCAS.items():
        for bitola, diametro_ref in dados[tipo].items():
            if abs(diametro_medido - diametro_ref) <= 0.5:
                return norma, bitola, diametro_ref, 90.0

    # 3️⃣ Mais próximo
    menor_dif = float("inf")
    melhor = (None, None, None)
    for norma, dados in TABELA_ROSCAS.items():
        for bitola, diametro_ref in dados[tipo].items():
            diff = abs(diametro_medido - diametro_ref)
            if diff < menor_dif:
                menor_dif = diff
                melhor = (norma, bitola, diametro_ref)

    if melhor[0]:
        return melhor[0], melhor[1], melhor[2], 70.0

    return None, None, None, 0.0


# ================================
# Função principal
# ================================
def analisar_imagem(path_img: str, interna: bool):
    img = cv2.imread(path_img)
    if img is None:
        return None, "❌ Erro ao abrir imagem."

    debug = img.copy()

    # === Tenta primeiro com conf=0.4 ===
    resultados = model.predict(img, conf=0.4, verbose=False)[0]

    # === Se não achou nada, tenta com conf=0.2 ===
    if len(resultados.boxes) == 0:
        logger.warning("⚠️ Nenhuma detecção em conf=0.4, tentando com conf=0.2")
        resultados = model.predict(img, conf=0.2, verbose=False)[0]
        if len(resultados.boxes) == 0:
            return None, "❌ Nenhum objeto detectado."

    # ================================
    # Processar detecções
    # ================================
    cartao_px = None
    rosca_px = None

    for box in resultados.boxes:
        cls_id = int(box.cls[0])
        conf = float(box.conf[0])
        x1, y1, x2, y2 = map(int, box.xyxy[0].tolist())
        largura, altura = x2 - x1, y2 - y1
        label = NAMES.get(cls_id, str(cls_id))

        if label == "cartao":
            cartao_px = max(largura, altura)
        if (interna and label == "rosca_interna") or (not interna and label == "rosca_externa"):
            rosca_px = max(largura, altura)

        cv2.rectangle(debug, (x1, y1), (x2, y2), (0, 255, 0), 2)
        cv2.putText(debug, f"{label} {conf:.2f}", (x1, y1 - 5),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)

    debug_filename = f"debug_{next(tempfile._get_candidate_names())}.png"
    debug_path = os.path.join("static", debug_filename)
    cv2.imwrite(debug_path, debug)

    if not cartao_px:
        return None, "❌ Nenhum cartão detectado."
    if not rosca_px:
        return None, "❌ Nenhuma rosca detectada."

    escala = CARTAO_LARGURA_MM / cartao_px
    diametro_mm = rosca_px * escala

    norma, bitola, diam_ref, confianca = fator_decisao(diametro_mm, interna)

    return {
        "tipo_rosca": "Rosca interna (fêmea)" if interna else "Rosca externa (macho)",
        "diametro_medido_mm": round(diametro_mm, 2),
        "bitola": bitola if bitola else "indefinida",
        "norma": norma if norma else "desconhecida",
        "confianca": confianca,
        "observacao": "ℹ️ Detecção feita por IA (YOLOv8).",
        "debug": f"/{debug_path}"
    }, None


# ================================
# Rotas FastAPI
# ================================
@app.get("/", response_class=HTMLResponse)
def home():
    return FileResponse("static/index.html")

@app.post("/analisar")
async def analisar(file: UploadFile = File(...), interna: str = Form("false")):
    try:
        is_interna = interna.strip().lower() in ["true", "1", "yes"]

        ext = os.path.splitext(file.filename or "")[1].lower()
        if ext not in [".png", ".jpg", ".jpeg"]:
            ext = ".png"

        with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as tmp:
            tmp.write(await file.read())
            temp_path = tmp.name

        resp, erro = analisar_imagem(temp_path, is_interna)

        if erro:
            return JSONResponse({
                "status": "falha",
                "msg": erro,
                "tipo_rosca": "Rosca interna (fêmea)" if is_interna else "Rosca externa (macho)",
                "diametro_medido_mm": "0.00",
                "bitola": "-",
                "norma": "-",
                "confianca": "0.0",
                "observacao": erro,
                "debug": resp["debug"] if resp else None
            })

        return JSONResponse({
            "status": "ok",
            **resp
        })

    except Exception as e:
        logger.exception("💥 Erro no /analisar")
        return JSONResponse({
            "status": "erro",
            "msg": f"💥 Erro inesperado: {str(e)}",
            "tipo_rosca": "indefinida",
            "diametro_medido_mm": "0.00",
            "bitola": "-",
            "norma": "-",
            "confianca": "0.0",
            "observacao": "Erro inesperado.",
            "debug": None
        }, status_code=500)

@app.get("/healthz")
def health_check():
    return {"status": "ok"}
