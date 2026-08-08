MODEL_PATH = "runs/detect/train12/weights/best.pt"
CARTAO_LARGURA_MM = 85.6
MAX_DIMENSAO_PX = 1280  # reduz fotos grandes antes de processar, para economizar memória/CPU

model = YOLO(MODEL_PATH)
NAMES = model.names
logger.info(f"✅ Modelo carregado: {MODEL_PATH} com classes {NAMES}")

# ================================
# Tabelas oficiais (mm) - ver tabelas.py (BSPP, BSPT, NPT, UNC, UNF)
# ================================

# ================================
# Função principal
# ================================
def analisar_imagem(path_img: str, interna: bool):
    img = cv2.imread(path_img)
    if img is None:
        return None, "❌ Erro ao abrir imagem."

    altura, largura = img.shape[:2]
    maior_lado = max(altura, largura)
    if maior_lado > MAX_DIMENSAO_PX:
        fator_resize = MAX_DIMENSAO_PX / maior_lado
        img = cv2.resize(img, (int(largura * fator_resize), int(altura * fator_resize)), interpolation=cv2.INTER_AREA)

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

    candidatos = tabelas.encontrar_candidatos(diametro_mm, interna, top_n=3)
    melhor = candidatos[0] if candidatos else None

    observacao = "ℹ️ Detecção feita por IA (YOLOv8). Diâmetro estimado por comparação com um cartão de referência."
    if melhor and len(candidatos) > 1 and candidatos[1]["diferenca_mm"] <= 0.3 and candidatos[1]["bitola_pol"] == melhor["bitola_pol"]:
        observacao += (
            f" Atenção: o diâmetro medido é compatível tanto com rosca {melhor['forma']} quanto com "
            f"{candidatos[1]['forma']}. Verifique visualmente se a rosca afunila (cônica) ou é reta (paralela) "
            "para confirmar entre elas."
        )
    observacao += " Recomenda-se confirmar a bitola com um gabarito/pente de rosca antes de fazer o pedido."

    return {
        "tipo_rosca": "Rosca interna (fêmea)" if interna else "Rosca externa (macho)",
        "diametro_medido_mm": round(diametro_mm, 2),
        "diametro_medido_pol": tabelas.mm_para_polegada(diametro_mm),
        "bitola": melhor["bitola_pol"] if melhor else "indefinida",
        "norma": melhor["norma"] if melhor else "desconhecida",
        "confianca": melhor["confianca"] if melhor else 0.0,
        "candidatos": candidatos,
        "observacao": observacao,
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

@app.get("/termos", response_class=HTMLResponse)
def termos_de_uso():
    return (
        "<html><head><meta charset='utf-8'><title>Termos de Uso</title></head><body>"
        "<h2>Termos de Uso</h2>"
        "<p>Este aplicativo estima o diâmetro e a possível norma de uma rosca (BSPP, BSPT, NPT, "
        "UNC, UNF) a partir de uma foto, usando um cartão de referência para calcular a escala. "
        "O resultado é uma estimativa gerada por processamento de imagem e inteligência artificial "
        "e pode conter erros de medição decorrentes de ângulo de foto, iluminação, distância ou "
        "qualidade da imagem.</p>"
        "<p>Antes de comprar, fabricar ou instalar qualquer peça, confirme sempre a bitola com um "
        "gabarito/pente de rosca físico ou com um profissional qualificado. O uso deste aplicativo "
        "não substitui a verificação técnica da peça.</p>"
        "</body></html>"
    )

@app.get("/privacidade", response_class=HTMLResponse)
def politica_de_privacidade():
    return (
        "<html><head><meta charset='utf-8'><title>Política de Privacidade</title></head><body>"
        "<h2>Política de Privacidade</h2>"
        "<p>As fotos enviadas são usadas apenas para detectar e medir a rosca e o cartão de "
        "referência na imagem, e para gerar a imagem de depuração exibida no resultado. Não "
        "coletamos dados pessoais, não compartilhamos as imagens com terceiros e não as usamos "
        "para nenhuma outra finalidade além de responder à sua solicitação de análise.</p>"
        "</body></html>"
    )
# ================================
# Rotas FastAPI
# ================================
@app.get("/", response_class=HTMLResponse)
def home():
    return FileResponse("static/index.html")

@app.post("/analisar")
async def analisar(file: UploadFile = File(...), interna: str = Form("false"), formato: str = Form("")):
    try:
        is_interna = interna.strip().lower() in ["true", "1", "yes"]
        formato_normalizado = formato.strip().lower() if formato.strip().lower() in ("reta", "conica") else None

        ext = os.path.splitext(file.filename or "")[1].lower()
        if ext not in [".png", ".jpg", ".jpeg"]:
            ext = ".png"

        with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as tmp:
            tmp.write(await file.read())
            temp_path = tmp.name

        resp, erro = analisar_imagem(temp_path, is_interna, formato_normalizado)

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

@app.get("/termos", response_class=HTMLResponse)
def termos_de_uso():
    return (
        "<html><head><meta charset='utf-8'><title>Termos de Uso</title></head><body>"
        "<h2>Termos de Uso</h2>"
        "<p>Este aplicativo estima o diâmetro e a possível norma de uma rosca de tubo (BSPP, BSPT ou "
        "NPT) a partir de uma foto, usando um cartão de referência para calcular a escala. "
        "O resultado é uma estimativa gerada por processamento de imagem e inteligência artificial "
        "e pode conter erros de medição decorrentes de ângulo de foto, iluminação, distância ou "
        "qualidade da imagem.</p>"
        "<p>Antes de comprar, fabricar ou instalar qualquer peça, confirme sempre a bitola com um "
        "gabarito/pente de rosca físico ou com um profissional qualificado. O uso deste aplicativo "
        "não substitui a verificação técnica da peça.</p>"
        "</body></html>"
    )

@app.get("/privacidade", response_class=HTMLResponse)
def politica_de_privacidade():
    return (
        "<html><head><meta charset='utf-8'><title>Política de Privacidade</title></head><body>"
        "<h2>Política de Privacidade</h2>"
        "<p>As fotos enviadas são usadas apenas para detectar e medir a rosca e o cartão de "
        "referência na imagem, e para gerar a imagem de depuração exibida no resultado. Não "
        "coletamos dados pessoais, não compartilhamos as imagens com terceiros e não as usamos "
        "para nenhuma outra finalidade além de responder à sua solicitação de análise.</p>"
        "</body></html>"
    )
