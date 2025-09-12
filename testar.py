from ultralytics import YOLO

# carregar o modelo treinado
model = YOLO("runs/detect/train12/weights/best.pt")

# rodar em todas as imagens da pasta de teste
results = model.predict(source="My-First-Project-3/test/images", save=True)

print("✅ Predição concluída! Veja os resultados em 'runs/detect/predict/'")
