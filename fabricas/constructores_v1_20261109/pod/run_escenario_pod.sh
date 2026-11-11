#!/bin/bash
# [constructores_v1_20261109] Corre EN EL POD RunPod (GPU): construir_render (EEVEE) + hoja de un escenario ya ensamblado en el 213.
# Uso: bash run_escenario_pod.sh <ESC_ID> <MODO>   (datos en /root/job/datos: plan_<ESC>.json, ensamblado_<MODO>.json, validacion_<MODO>.json)
set -uo pipefail
ESC="$1"; MODO="${2:-star}"; JOB=/root/job; OUT=/root/out
mkdir -p $OUT
export __EGL_VENDOR_LIBRARY_FILENAMES=/usr/share/glvnd/egl_vendor.d/10_nvidia.json
export __GLX_VENDOR_LIBRARY_NAME=nvidia EGL_PLATFORM=device VK_ICD_FILENAMES=/usr/share/vulkan/icd.d/nvidia_icd.json
export MYIA_GPU=1
nvidia-smi --query-gpu=name,driver_version,memory.total --format=csv,noheader > $OUT/gpu.txt 2>&1
cd $JOB/constructores/escenario/codigo
. /root/myia_env.sh; $BLENDER --gpu-backend opengl -b --factory-startup -P construir_render.py -- $MODO --datos $JOB/datos --escenario $ESC --salida $OUT > $OUT/construir.log 2>&1
RC=$?; echo "CONSTRUIR_RC $RC"; tail -3 $OUT/construir.log
[ $RC -eq 0 ] && python3 hoja_escenario.py --escenario $ESC --modo $MODO --datos $JOB/datos --renders $OUT/renders --salida $OUT/HOJA_${ESC}_${MODO}.png > $OUT/hoja.log 2>&1
cp $JOB/datos/*.json $OUT/ 2>/dev/null
cd /root && tar czf /root/out.tgz out && echo "PAQUETE_OK"
echo "FIN $RC"
