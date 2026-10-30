# Equipo de la tienda (CPU). Para GPU NVIDIA: partir de una imagen CUDA y usar onnxruntime-gpu.
FROM python:3.12-slim
RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg libgl1 libglib2.0-0 && rm -rf /var/lib/apt/lists/*
WORKDIR /edge
COPY requirements.txt requirements-modelo.txt ./
RUN pip install --no-cache-dir -r requirements.txt -r requirements-modelo.txt
COPY vigilado_edge ./vigilado_edge
ENTRYPOINT ["python", "-m", "vigilado_edge"]
CMD ["ejecutar", "--config", "/config/config.yaml"]
