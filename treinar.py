from ultralytics import YOLO

# carregar o modelo base (pode ser yolov8n.pt, yolov8s.pt, etc.)
model = YOLO("yolov8n.pt")

# treinar usando o dataset baixado do Roboflow
results = model.train(
    data="My-First-Project-3/data.yaml",  # caminho para o dataset
    epochs=50,                           # número de épocas de treino
    imgsz=640                            # tamanho das imagens
)

print("✅ Treinamento finalizado! Modelo salvo em runs/detect/train/weights/best.pt")
