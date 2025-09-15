from roboflow import Roboflow

# Sua chave privada do Roboflow
rf = Roboflow(api_key="enETAH3MO2Vk47OAQu4G")

# Workspace e projeto
project = rf.workspace("dailva-souza-araujo").project("my-first-project-2b8n6")

# Agora usamos a versão 4 (com augmentations aplicados)
version = project.version(4)

# Baixar no formato YOLOv8
dataset = version.download("yolov8")
