from ultralytics import YOLO
import os

# carregar o modelo treinado
model = YOLO("runs/detect/train12/weights/best.pt")

# dicionário com os conjuntos de dados e suas pastas
datasets = {
    "train": "My-First-Project-3/train/images",
    "valid": "My-First-Project-3/valid/images",
    "test": "My-First-Project-3/test/images"
}

# criar uma pasta base para salvar resultados
output_base = "runs/detect/resultados"
os.makedirs(output_base, exist_ok=True)

# rodar em cada conjunto de imagens
for name, path in datasets.items():
    print(f"\n🔎 Rodando predições em {name}...")
    results = model.predict(source=path, save=True, project=output_base, name=name)
    print(f"✅ Resultados de {name} salvos em: {os.path.join(output_base, name)}")

print("\n🚀 Finalizado! Confira as pastas dentro de 'runs/detect/resultados/'")
