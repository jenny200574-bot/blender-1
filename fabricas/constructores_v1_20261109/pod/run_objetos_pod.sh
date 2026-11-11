#!/bin/bash
# [constructores_v1_20261109] Corre EN EL POD (lo lanza el servicio): varios objetos en UN pod. /root/job/objetos/<id>/piezas.json (+ alto_ref.txt)
set -uo pipefail
JOB=/root/job; OUT=/root/out; mkdir -p $OUT
export __EGL_VENDOR_LIBRARY_FILENAMES=/usr/share/glvnd/egl_vendor.d/10_nvidia.json __GLX_VENDOR_LIBRARY_NAME=nvidia EGL_PLATFORM=device MYIA_GPU=1
. /root/myia_env.sh; cd $JOB/constructores/objetos
for d in $JOB/objetos/*/; do ID=$(basename $d); O=$OUT/$ID; mkdir -p $O
  echo "T_OBJ_INI_$ID $(date +%s.%N)"
  $BLENDER --gpu-backend opengl -b --factory-startup -P construir_objeto.py -- --piezas $d/piezas.json --salida $O --id $ID > $O/blender.log 2>&1; echo "OBJ_RC $ID $?"
  python3 hoja_objeto.py --dir $O --id $ID --alto-ref "$(cat $d/alto_ref.txt 2>/dev/null)" --fuente "$(cat $d/fuente.txt 2>/dev/null)" > $O/hoja.log 2>&1
  echo "T_OBJ_FIN_$ID $(date +%s.%N)"
done
cd /root && tar czf /root/out.tgz out && echo PAQUETE_OK
