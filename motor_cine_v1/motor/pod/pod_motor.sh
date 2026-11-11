#!/bin/bash
# [motor unificado v1, 10-nov-2026] Corre EN EL POD RunPod (GPU). Datos: /root/job/motor.tgz, /root/job/corrida.tgz.
# 1) motor al volumen persistente (/workspace/myia_gpu/motor/v1_20261110, respaldo del anterior), 2) motor_blender (Mwni, foot-lock,
# cámara, ocultar_estorbos), 3) render final EEVEE GPU + vistas de revisión, 4) video de revisión grande (Pillow + FFmpeg).
set -uo pipefail
ID="${1:-corrida}"; JOB=/root/job; OUT=/root/out; mkdir -p $OUT
export __EGL_VENDOR_LIBRARY_FILENAMES=/usr/share/glvnd/egl_vendor.d/10_nvidia.json
export __GLX_VENDOR_LIBRARY_NAME=nvidia EGL_PLATFORM=device VK_ICD_FILENAMES=/usr/share/vulkan/icd.d/nvidia_icd.json
nvidia-smi --query-gpu=name,driver_version,memory.total --format=csv,noheader > $OUT/gpu.txt 2>&1
. /root/myia_env.sh; BASE=${MYIA_GPU_BASE:-/root/myia_gpu}
MV=$BASE/motor/${MOTOR_VOL:?falta MOTOR_VOL}   # [argon_v2] carpeta del volumen = nombre de la copia del motor (lo manda correr_escena); nunca la del motor vivo
mkdir -p $MV && tar xzf $JOB/motor.tgz -C $MV --strip-components=1 && echo "MOTOR_EN_VOLUMEN $MV"
mkdir -p $JOB/corrida && tar xzf $JOB/corrida.tgz -C $JOB/corrida --strip-components=1
COR=$JOB/corrida
if [ ! -f $BASE/ffmpeg/.ok ]; then mkdir -p $BASE/ffmpeg && timeout 240 pip install -q --target $BASE/ffmpeg imageio-ffmpeg && touch $BASE/ffmpeg/.ok; fi
FF=$(PYTHONPATH=$BASE/ffmpeg python3 -c "import imageio_ffmpeg;print(imageio_ffmpeg.get_ffmpeg_exe())")
echo "FFMPEG $FF"
# [t1066u] FASES: FASE=todo (por defecto, como antes) | construir (Kimodo + motor_blender y entrega /root/out_fase1.tgz para el
# storyboard después del 3D en 213) | render (aplica /root/job/corrida_sb3d.tgz si existe y solo renderiza). SALTAR_CONSTRUIR=1 =
# no corre Kimodo ni motor_blender (escena ya armada: reusar corrida).
FASE=${FASE:-todo}
if [ -f $JOB/corrida_sb3d.tgz ] && [ "$FASE" != "construir" ]; then
  tar xzf $JOB/corrida_sb3d.tgz -C $COR && echo "SB3D_APLICADO_EN_COR $(ls $COR/sb3d 2>/dev/null | wc -l) archivos"
fi
if [ "$FASE" = "render" ]; then SALTAR_CONSTRUIR=1; fi
RC=0
if [ "${SALTAR_CONSTRUIR:-0}" != "1" ]; then
# ---- Kimodo ON (Ricardo t983u/t995u): genera los tramos de movimiento en GPU antes del motor
if [ -f $COR/kimodo/pedidos.json ]; then
  TK=$(date +%s); bash $MV/pod/setup_kimodo.sh > $OUT/kimodo_setup.log 2>&1; KRC=$?
  echo "KIMODO_SETUP_RC $KRC $(( $(date +%s)-TK ))s"; tail -3 $OUT/kimodo_setup.log
  if [ $KRC -eq 0 ]; then
    TK=$(date +%s)
    HF_HOME=$BASE/kimodo/hf TEXT_ENCODER_DEVICE=cpu PYTHONUNBUFFERED=1 $BASE/kimodo/venv/bin/python $MV/pod/kimodo_gen.py --corrida $COR > $OUT/kimodo_gen.log 2>&1
    echo "KIMODO_GEN_RC $? $(( $(date +%s)-TK ))s"; grep -E "^KIMODO |RESULT_KIMODO_GEN" $OUT/kimodo_gen.log | tail -12
  fi
  mkdir -p $OUT/kimodo && cp $COR/kimodo/* $OUT/kimodo/ 2>/dev/null
  nvidia-smi --query-gpu=memory.used --format=csv,noheader >> $OUT/gpu.txt 2>&1; free -g | head -2 >> $OUT/gpu.txt
fi
T0=$(date +%s)
$BLENDER --gpu-backend opengl -b --factory-startup -P $MV/blender/motor_blender.py -- --corrida $COR --motor $MV ${MOTOR_ARGS:-} > $OUT/motor.log 2>&1
RC=$?; echo "MOTOR_RC $RC $(( $(date +%s)-T0 ))s"; grep -E "RESULT_MOTOR|Traceback|Error|FALLO|MOTOR_SALIDA" $OUT/motor.log | tail -8
cp $COR/reporte_motor.json $OUT/ 2>/dev/null
else
  echo "SALTAR_CONSTRUIR escena ya armada (reusar corrida / fase render)"
fi
if [ "$FASE" = "construir" ]; then
  cp $OUT/motor.log $COR/motor_fase1.log 2>/dev/null; cp $OUT/kimodo_gen.log $COR/kimodo_gen_fase1.log 2>/dev/null   # [prueba t528] traer logs y kimodo para medir
  cd $COR && tar czf /root/out_fase1.tgz escena_motor.blend reporte_motor.json $(ls *.json | grep -v reporte_motor.json) $(ls -d kimodo motor_fase1.log kimodo_gen_fase1.log 2>/dev/null) 2>/dev/null
  cp $OUT/motor.log /root/out_fase1_motor.log 2>/dev/null
  echo "FASE1_RC $RC"; [ -s /root/out_fase1.tgz ] && echo "PAQUETE_FASE1_OK"; exit $RC
fi
if [ $RC -eq 0 ] && [ ! -s $COR/escena_motor.blend ]; then
  echo "FALLO_SIN_BLEND no existe escena_motor.blend (blender pudo salir 0 tras una excepción Python)"
  RC=1
fi
if [ $RC -eq 0 ]; then
  # [t1066u] vistas de revisión (Workbench) EN PARALELO con el render final EEVEE
  T1=$(date +%s)
  ( $BLENDER -b $COR/escena_motor.blend --gpu-backend opengl -P $MV/blender/render_motor.py -- --out $JOB/r_amplia --modo amplia --res 1280x720 > $OUT/render_amplia.log 2>&1; echo "RENDER_AMPLIA_RC $? $(( $(date +%s)-T1 ))s" > $OUT/rc_amplia.txt ) &
  ( $BLENDER -b $COR/escena_motor.blend --gpu-backend opengl -P $MV/blender/render_motor.py -- --out $JOB/r_planta --modo planta --res 960x540 > $OUT/render_planta.log 2>&1; echo "RENDER_PLANTA_RC $? $(( $(date +%s)-T1 ))s" > $OUT/rc_planta.txt ) &
  ( $BLENDER -b $COR/escena_motor.blend --gpu-backend opengl -P $MV/blender/render_motor.py -- --out $JOB/r_lateral --modo lateral --res 960x540 > $OUT/render_lateral.log 2>&1; echo "RENDER_LATERAL_RC $? $(( $(date +%s)-T1 ))s" > $OUT/rc_lateral.txt ) &
  $BLENDER -b $COR/escena_motor.blend --gpu-backend opengl -P $MV/blender/render_motor.py -- --out $JOB/r_final --modo final --res ${RES_FINAL:-1280x720} --muestras ${MUESTRAS:-16} > $OUT/render_final.log 2>&1
  echo "RENDER_FINAL_RC $? $(( $(date +%s)-T1 ))s"; grep RESULT_RENDER $OUT/render_final.log | tail -1
  wait; cat $OUT/rc_amplia.txt $OUT/rc_planta.txt $OUT/rc_lateral.txt 2>/dev/null
  cp $JOB/r_final/render.json $OUT/render_final.json 2>/dev/null; cp $JOB/r_amplia/render.json $OUT/render_amplia.json 2>/dev/null; cp $JOB/r_lateral/render.json $OUT/render_lateral.json 2>/dev/null
  LAT=""; [ -f $JOB/r_lateral/f00001.png ] && LAT="--lateral $JOB/r_lateral"
  PYTHONPATH=$BASE/pillow python3 $MV/componer_revision.py --corrida $COR --final $JOB/r_final --amplia $JOB/r_amplia --planta $JOB/r_planta $LAT --out $JOB/r_rev > $OUT/componer.log 2>&1
  echo "COMPONER_RC $?"
  FPS=$(python3 -c "import json;print(json.load(open('$COR/entrada_motor.json'))['fps'])")
  $FF -y -loglevel error -framerate $FPS -i $JOB/r_final/f%05d.png -c:v libx264 -pix_fmt yuv420p -crf 18 $OUT/final_camara_sb.mp4
  $FF -y -loglevel error -framerate $FPS -i $JOB/r_amplia/f%05d.png -c:v libx264 -pix_fmt yuv420p -crf 20 $OUT/revision_vista_amplia.mp4
  $FF -y -loglevel error -framerate $FPS -i $JOB/r_planta/f%05d.png -c:v libx264 -pix_fmt yuv420p -crf 22 $OUT/revision_planta.mp4
  [ -n "$LAT" ] && $FF -y -loglevel error -framerate $FPS -i $JOB/r_lateral/f%05d.png -c:v libx264 -pix_fmt yuv420p -crf 22 $OUT/revision_lateral.mp4
  $FF -y -loglevel error -framerate $FPS -i $JOB/r_rev/f%05d.png -c:v libx264 -pix_fmt yuv420p -crf 18 $OUT/REVISION_GRANDE_1920x1080.mp4
  ls -la $OUT/*.mp4
  mkdir -p $OUT/cuadros && python3 - <<PY
import json, shutil
R = json.load(open('$COR/reporte_motor.json'))
for t in R['pasos']['5_camara']['tomas']:
    m = (t['frame_ini'] + t['frame_fin']) // 2
    for d in ('r_rev', 'r_final'):
        try: shutil.copy(f'$JOB/{d}/f{m:05d}.png', f'$OUT/cuadros/{t["vineta"]}_f{m:05d}' + ('' if d == 'r_rev' else '_final') + '.png')
        except Exception as e: print(e)
PY
  cp $COR/escena_motor.blend $OUT/ 2>/dev/null
  FALTAN=()
  for f in final_camara_sb.mp4 revision_vista_amplia.mp4 revision_planta.mp4 REVISION_GRANDE_1920x1080.mp4 escena_motor.blend; do
    if [ ! -s "$OUT/$f" ]; then FALTAN+=("$f"); fi
  done
  if [ ${#FALTAN[@]} -gt 0 ]; then
    echo "FALLO_SIN_SALIDAS faltan o están vacíos: ${FALTAN[*]}"
    RC=1
  fi
  DEST=$BASE/motor/corridas/$ID; mkdir -p $DEST && cp -a $OUT/*.mp4 $OUT/*.json $OUT/escena_motor.blend $DEST/ 2>/dev/null && echo "CORRIDA_EN_VOLUMEN $DEST"
fi
cp $COR/*.json $OUT/ 2>/dev/null
[ -d $COR/sb3d ] && mkdir -p $OUT/sb3d && cp $COR/sb3d/*.json $COR/sb3d/*.jpg $OUT/sb3d/ 2>/dev/null
cd /root && tar czf /root/out.tgz out && echo "PAQUETE_OK"
echo "FIN $RC"
exit $RC
