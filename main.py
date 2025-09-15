import os
import cv2
import tempfile
import logging
from fastapi import FastAPI, UploadFile, File
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

    # 3️⃣ Se nada bater, pega o mais próximo
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

def detectar_multiplos_angulos(img, conf=0.4):
    for angle in [0, 90, 180, 270]:
        if angle != 0:
            M = cv2.getRotationMatrix2D((img.shape[1]//2, img.shape[0]//2), angle, 1)
            rot = cv2.warpAffine(img, M, (img.shape[1], img.shape[0]))
        else:
            rot = img

        res = model.predict(rot, conf=conf, verbose=False)[0]
        if len(res.boxes) > 0:
            logger.info(f"✅ Detecção feita com rotação {angle}°")
            return res
    return None

# ================================
# Função principal de análise robusta
# ================================
def analisar_imagem(path_img: str):
    img = cv2.imread(path_img)
    if img is None:
        return None, "❌ Erro ao abrir imagem."

    # 1) Testa original + variações
    variacoes = [
        img,
        cv2.convertScaleAbs(img, alpha=1.2, beta=30),
        cv2.convertScaleAbs(img, alpha=0.8, beta=-30),
        cv2.equalizeHist(cv2.cvtColor(img, cv2.COLOR_BGR2GRAY))
    ]

    resultados = None
    for var in variacoes:
        if len(var.shape) == 2:
            var = cv2.cvtColor(var, cv2.COLOR_GRAY2BGR)
        res = model.predict(var, conf=0.4, verbose=False)[0]
        if len(res.boxes) > 0:
            resultados = res
            break

    # 2) Se não achou, tenta ângulos
    if resultados is None:
        resultados = detectar_multiplos_angulos(img, conf=0.4)

    # 3) Fallback confiança baixa
    if resultados is None:
        resultados = model.predict(img, conf=0.2, verbose=False)[0]
        if len(resultados.boxes) == 0:
            return None, "❌ Nenhum objeto detectado."

    # ================================
    # Processar detecções
    # ================================
    cartao_px = None
    roscas = []
    debug = img.copy()

    for box in resultados.boxes:
        cls_id = int(box.cls[0])
        conf = float(box.conf[0])
        x1, y1, x2, y2 = map(int, box.xyxy[0].tolist())
        largura, altura = x2 - x1, y2 - y1
        label = NAMES.get(cls_id, str(cls_id))

        cv2.rectangle(debug, (x1, y1), (x2, y2), (0, 255, 0), 2)
        cv2.putText(debug, f"{label} {conf:.2f}", (x1, y1 - 5),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)

        if label == "cartao":
            cartao_px = max(largura, altura)

        if label in ["rosca_externa", "rosca_interna"]:
            roscas.append({
                "tipo": label,
                "px": max(largura, altura),
                "conf": conf
            })

    debug_filename = f"debug_{next(tempfile._get_candidate_names())}.png"
    debug_path = os.path.join("static", debug_filename)
    cv2.imwrite(debug_path, debug)

    if not cartao_px:
        return None, "❌ Nenhum cartão detectado."
    if not roscas:
        return None, "❌ Nenhuma rosca detectada."

    escala = CARTAO_LARGURA_MM / cartao_px
    resultados_final = []
    for r in roscas:
        diametro_mm = r["px"] * escala
        norma, bitola, diam_ref, confianca = fator_decisao(diametro_mm, interna=(r["tipo"]=="rosca_interna"))

        resultados_final.append({
            "tipo_rosca": r["tipo"],
            "diametro_medido_mm": round(diametro_mm, 2),
            "bitola": bitola if bitola else "indefinida",
            "norma": norma if norma else "desconhecida",
            "confianca": confianca,
            "conf_yolo": round(r["conf"]*100, 1)
        })

    return {"resultados": resultados_final, "debug": f"/{debug_path}"}, None

# ================================
# Rotas FastAPI
# ================================
@app.get("/", response_class=HTMLResponse)
def home():
    return FileResponse("static/index.html")

@app.post("/analisar")
async def analisar(file: UploadFile = File(...)):
    try:
        if not file:
            return JSONResponse({"status": "erro", "msg": "📷 Nenhum arquivo enviado."}, status_code=400)

        ext = os.path.splitext(file.filename or "")[1].lower()
        if ext not in [".png", ".jpg", ".jpeg"]:
            ext = ".png"

        with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as tmp:
            tmp.write(await file.read())
            temp_path = tmp.name

        resp, erro = analisar_imagem(temp_path)

        if erro:
            return JSONResponse({
                "status": "falha",
                "msg": erro,
                "resultados": [],
                "debug": resp["debug"] if resp else None
            })

        return JSONResponse({
            "status": "ok",
            "msg": "✅ Detecção concluída.",
            **resp
        })

    except Exception as e:
        logger.exception("💥 Erro no /analisar")
        return JSONResponse({
            "status": "erro",
            "msg": f"💥 Erro inesperado: {str(e)}",
            "resultados": [],
            "debug": None
        }, status_code=500)

@app.get("/healthz")
def health_check():
    return {"status": "ok"}
