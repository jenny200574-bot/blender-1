#!/bin/bash
# [constructores_v1_20261109] Corre EN EL POD RunPod (GPU). Lo sube y lanza el servicio de fábricas (workers_v2_3d → gpu_pod.py); nadie lo corre a mano.
# Uso: bash run_personaje_pod.sh <ID> <ALTURA_ADN_M>
# Blender 5.2.3 con EGL NVIDIA + --gpu-backend opengl (receta pack blender523_egl_ready de Ako, 4-nov). US$ lo cobra el pod, no este script.
set -uo pipefail
ID="$1"; ALT="$2"; JOB=/root/job; OUT=/root/out
mkdir -p $OUT/renders $OUT/blend
export __EGL_VENDOR_LIBRARY_FILENAMES=/usr/share/glvnd/egl_vendor.d/10_nvidia.json
export __GLX_VENDOR_LIBRARY_NAME=nvidia EGL_PLATFORM=device VK_ICD_FILENAMES=/usr/share/vulkan/icd.d/nvidia_icd.json
export MYIA_GPU=1 MYIA_GPU_BACKEND=opengl-egl
nvidia-smi --query-gpu=name,driver_version,memory.total --format=csv,noheader > $OUT/gpu.txt 2>&1
nvidia-smi --query-gpu=timestamp,utilization.gpu,memory.used --format=csv -lms 500 > $OUT/gpu_uso.csv 2>&1 &
MON=$!
. /root/myia_env.sh
B=$BLENDER
T(){ echo "T_$1 $(date +%s.%N)"; }
cd $JOB/constructores/prototipo_esqueletos
T CONSTRUIR_INI
$B --gpu-backend opengl -b --factory-startup --python constructor_blender.py -- --ficha $JOB/ficha_esqueleto.json --salida $OUT/renders --blend $OUT/blend/$ID.blend > $OUT/constructor.log 2>&1
RC=$?; T CONSTRUIR_FIN; echo "CONSTRUIR_RC $RC"; tail -3 $OUT/constructor.log
if [ $RC -eq 0 ]; then
  T MEDIR_INI
  $B --gpu-backend opengl -b $OUT/blend/$ID.blend --python medir_altura.py -- --salida $OUT/medida.json > $OUT/medir.log 2>&1
  echo "MEDIR_RC $?"; grep MEDIDA $OUT/medir.log | tail -1
  # Calibración (cubo_fijo_v2: el ADN manda, Blender solo mide): las mallas sobresalen de los huesos (cráneo/suela),
  # así que si la medida se aparta >0,5 % del ADN se reconstruye UNA vez con altura_m × (ADN/medida). Sin IA, US$0.
  F=$(python3 -c "import json;m=json.load(open('$OUT/medida.json'));print(round($ALT/m['altura_medida_m'],6))")
  if python3 -c "import sys;sys.exit(0 if abs(1-$F)>0.005 else 1)"; then
    T CALIBRAR_INI
    python3 -c "import json;f=json.load(open('$JOB/ficha_esqueleto.json'));a=f['altura_m'];f['altura_m']=round(a*$F,5);f.setdefault('calibracion',{}).update({'altura_hueso_original_m':a,'factor':$F,'motivo':'mallas sobresalen del esqueleto; escalar molde al ADN (cubo_fijo_v2)'});json.dump(f,open('$JOB/ficha_calibrada.json','w'),ensure_ascii=False,indent=1)"
    cp $OUT/medida.json $OUT/medida_antes_calibrar.json; rm -rf $OUT/renders/*
    $B --gpu-backend opengl -b --factory-startup --python constructor_blender.py -- --ficha $JOB/ficha_calibrada.json --salida $OUT/renders --blend $OUT/blend/$ID.blend > $OUT/constructor.log 2>&1
    echo "CALIBRAR_RC $? factor=$F"; cp $JOB/ficha_calibrada.json $OUT/ficha_calibrada.json
    $B --gpu-backend opengl -b $OUT/blend/$ID.blend --python medir_altura.py -- --salida $OUT/medida.json > $OUT/medir.log 2>&1
    grep MEDIDA $OUT/medir.log | tail -1; T CALIBRAR_FIN
  fi
  T HOJA_INI
  python3 hacer_hoja.py --informe $OUT/renders/${ID}_informe.json --medida $OUT/medida.json --salida $OUT/renders/HOJA_${ID}.png --altura-adn "$ALT" > $OUT/hoja.log 2>&1
  echo "HOJA_RC $?"; T HOJA_FIN
fi
kill $MON 2>/dev/null || true
grep -i -m3 "gpu\|opengl\|egl\|nvidia" $OUT/constructor.log > $OUT/blender_gpu_lineas.txt 2>/dev/null || true
T EMPAQUE_INI; cd /root && tar czf /root/out.tgz out && echo "PAQUETE_OK $(du -k /root/out.tgz | cut -f1)KB"
echo "FIN $RC"
