#!/bin/sh
# Vídeo de ejemplo de OpenCV (peatones) para probar la lectura de vídeo y el modo cámara RTSP.
set -e
cd "$(dirname "$0")/../muestras"
curl -L -o vtest.avi https://raw.githubusercontent.com/opencv/opencv/4.x/samples/data/vtest.avi
echo "Descargado muestras/vtest.avi"
