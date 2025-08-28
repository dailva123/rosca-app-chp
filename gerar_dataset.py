import cv2
import numpy as np
import os
import random

# Configurações
IMG_SIZE = 640
NUM_IMAGENS = 200  # você pode aumentar para 500, 1000 etc
OUTPUT_DIR = "synthetic_dataset"

CLASSES = ["cartao", "rosca_externa", "rosca_interna"]

# Criar pastas
os.makedirs(f"{OUTPUT_DIR}/images", exist_ok=True)
os.makedirs(f"{OUTPUT_DIR}/labels", exist_ok=True)

def yolo_format(x, y, w, h, img_w, img_h):
    """Converte para formato YOLO (x_center, y_center, w, h) normalizado"""
    return f"{x/img_w} {y/img_h} {w/img_w} {h/img_h}"

for i in range(NUM_IMAGENS):
    img = np.ones((IMG_SIZE, IMG_SIZE, 3), dtype=np.uint8) * 255  # fundo branco
    label_lines = []

    # --- Gerar cartão (retângulo azul)
    card_x = random.randint(50, 200)
    card_y = random.randint(50, 400)
    card_w = 200
    card_h = 120
    cv2.rectangle(img, (card_x, card_y), (card_x+card_w, card_y+card_h), (255,0,0), -1)

    # YOLO label do cartão
    xc = card_x + card_w/2
    yc = card_y + card_h/2
    label_lines.append(f"0 {yolo_format(xc, yc, card_w, card_h, IMG_SIZE, IMG_SIZE)}")

    # --- Gerar rosca externa (círculo verde)
    rx = random.randint(150, 500)
    ry = random.randint(150, 500)
    rr = random.randint(40, 70)
    cv2.circle(img, (rx, ry), rr, (0,255,0), -1)
    label_lines.append(f"1 {yolo_format(rx, ry, rr*2, rr*2, IMG_SIZE, IMG_SIZE)}")

    # --- Gerar rosca interna (círculo vermelho)
    rx2 = random.randint(100, 500)
    ry2 = random.randint(100, 500)
    rr2 = random.randint(30, 60)
    cv2.circle(img, (rx2, ry2), rr2, (0,0,255), -1)
    label_lines.append(f"2 {yolo_format(rx2, ry2, rr2*2, rr2*2, IMG_SIZE, IMG_SIZE)}")

    # --- Salvar imagem
    img_path = f"{OUTPUT_DIR}/images/img_{i}.jpg"
    cv2.imwrite(img_path, img)

    # --- Salvar labels
    with open(f"{OUTPUT_DIR}/labels/img_{i}.txt", "w") as f:
        f.write("\n".join(label_lines))

print("✅ Dataset sintético gerado!")
