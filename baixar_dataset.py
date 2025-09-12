from roboflow import Roboflow

# sua nova Private API Key
rf = Roboflow(api_key="enETAH3MO2Vk47OAQu4G")

# substitua pelos valores EXATOS que aparecem no seu Roboflow
project = rf.workspace("dailva-souza-araujo").project("my-first-project-2b8n6")

# versão do dataset (ajuste o número se necessário)
version = project.version(3)

# baixar no formato YOLOv8
dataset = version.download("yolov8")
