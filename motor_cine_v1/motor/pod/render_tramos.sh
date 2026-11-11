#!/bin/bash
# [argon_v2u 10-nov-2026 · Ricardo: render MEDIO, la GPU solo mientras trabaja] Render FINAL solo (sin vistas de revisión ni
# composición), UN proceso de Blender en segundo plano y entrega POR TRAMOS: cada tramo se codifica a mp4 apenas sus cuadros están
# listos, y el 213 lo baja entre fases (si el pod se corta por tope, lo ya bajado no se pierde). General: rango de cuadros y
# calidad por variables; nada de escena/canal.
#   render_tramos.sh iniciar            -> extrae motor/corrida, lanza Blender (EEVEE, MUESTRAS, RES_FINAL) en segundo plano
#   render_tramos.sh tramo F0 F1 K      -> espera los cuadros F0..F1, codifica /root/out/tramo_K.mp4
set -uo pipefail
JOB=/root/job; OUT=/root/out; R=$JOB/r_final; mkdir -p $OUT $R
export __EGL_VENDOR_LIBRARY_FILENAMES=/usr/share/glvnd/egl_vendor.d/10_nvidia.json
export __GLX_VENDOR_LIBRARY_NAME=nvidia EGL_PLATFORM=device VK_ICD_FILENAMES=/usr/share/vulkan/icd.d/nvidia_icd.json
. /root/myia_env.sh; BASE=${MYIA_GPU_BASE:-/root/myia_gpu}
MV=$BASE/motor/${MOTOR_VOL:?falta MOTOR_VOL}; COR=$JOB/corrida
if [ "$1" = "iniciar" ]; then
  mkdir -p $MV && tar xzf $JOB/motor.tgz -C $MV --strip-components=1
  mkdir -p $COR && tar xzf $JOB/corrida.tgz -C $COR --strip-components=1
  [ -f $JOB/corrida_sb3d.tgz ] && tar xzf $JOB/corrida_sb3d.tgz -C $COR
  if [ ! -f $BASE/ffmpeg/.ok ]; then mkdir -p $BASE/ffmpeg && timeout 240 pip install -q --target $BASE/ffmpeg imageio-ffmpeg && touch $BASE/ffmpeg/.ok; fi
  [ -s $COR/escena_motor.blend ] || { echo FALTA_BLEND; exit 2; }
  nvidia-smi --query-gpu=name,memory.total --format=csv,noheader
  setsid nohup bash -c "$BLENDER -b $COR/escena_motor.blend --gpu-backend opengl -P $MV/blender/render_motor.py -- --out $R --modo final --res ${RES_FINAL:-1280x720} --muestras ${MUESTRAS:-16} --animacion 1 > $OUT/render_final.log 2>&1; echo \$? > $OUT/render_rc.txt" > /dev/null 2>&1 < /dev/null &
  echo $! > $OUT/render.pid; sleep 2; echo "RENDER_INICIADO $(date +%s)"; exit 0
fi
if [ "$1" = "tramo" ]; then
  F0=$2; F1=$3; K=$4; T=$(date +%s)
  FF=$(PYTHONPATH=$BASE/ffmpeg python3 -c "import imageio_ffmpeg;print(imageio_ffmpeg.get_ffmpeg_exe())")
  FPS=$(python3 -c "import json;print(json.load(open('$COR/entrada_motor.json'))['fps'])")
  SIG=$(printf "%05d" $((F1 + 1)))
  while true; do   # el cuadro F1 está completo cuando existe el siguiente o Blender terminó
    if [ -f $OUT/render_rc.txt ]; then break; fi
    if [ -f $R/f$SIG.png ]; then break; fi
    sleep 3
  done
  if [ -f $OUT/render_rc.txt ] && [ "$(cat $OUT/render_rc.txt)" != "0" ]; then echo "RENDER_FALLO rc=$(cat $OUT/render_rc.txt)"; tail -20 $OUT/render_final.log; exit 3; fi
  N=$((F1 - F0 + 1)); ls $R/f*.png | wc -l
  $FF -y -loglevel error -framerate $FPS -start_number $F0 -i $R/f%05d.png -frames:v $N -c:v libx264 -pix_fmt yuv420p -crf 18 $OUT/tramo_$K.mp4 || exit 4
  cp $R/f$(printf "%05d" $(( (F0 + F1) / 2 ))).png $OUT/muestra_tramo_$K.png 2>/dev/null
  echo "TRAMO_OK $K $F0-$F1 espera+codif $(( $(date +%s) - T ))s $(stat -c %s $OUT/tramo_$K.mp4) bytes"
  [ -f $OUT/render_rc.txt ] && grep RESULT_RENDER $OUT/render_final.log | tail -1
  exit 0
fi
echo "uso: iniciar | tramo F0 F1 K"; exit 1
