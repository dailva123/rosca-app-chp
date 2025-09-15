# ================================
# Patch para garantir compatibilidade com polars
# ================================
import sys, importlib

try:
    import polars
except ImportError:
    try:
        polars = importlib.import_module("polars_lts_cpu")
        sys.modules["polars"] = polars
        print("⚡ Usando polars-lts-cpu como polars")
    except ImportError:
        print("❌ Nenhuma versão de polars encontrada. Instale com: pip install polars-lts-cpu")

# ================================
# Treinamento com Ultralytics YOLOv8
# ================================
from ultralytics import YOLO

# carregar o modelo base (pode trocar por yolov8s.pt, yolov8m.pt, etc.)
model = YOLO("yolov8n.pt")

# treinar usando o dataset baixado do Roboflow
results = model.train(
    data="My-First-Project-3/data.yaml",  # caminho para o dataset
    epochs=50,                           # número de épocas de treino
    imgsz=640                            # tamanho das imagens
)

print("✅ Treinamento finalizado! Modelo salvo em runs/detect/train/weights/best.pt")
