#!/bin/bash
# [constructores_v1_20261109] Setup RÁPIDO del pod (sin apt): Blender 5.2.3 + libs EGL/X del pack extraídas con dpkg-deb -x
# (sin resolver dependencias) → LD_LIBRARY_PATH. Si hay volumen de red montado en /workspace, todo queda ahí instalado
# (myia_gpu/) y los pods siguientes arrancan listos. Escribe /root/myia_env.sh (BLENDER, LD_LIBRARY_PATH).
set -uo pipefail
JOB=/root/job
BASE=/root/myia_gpu
if mountpoint -q /workspace 2>/dev/null; then BASE=/workspace/myia_gpu; fi
mkdir -p $BASE /root/out
if [ ! -x $BASE/blender/blender ]; then
  [ -f $JOB/blender-5.2.3-linux-x64.tar.xz ] || { echo FALTA_TAR_BLENDER; exit 2; }
  mkdir -p $BASE/blender && tar -xJf $JOB/blender-5.2.3-linux-x64.tar.xz -C $BASE/blender --strip-components=1 || exit 2
fi
if [ ! -f $BASE/libs/.ok ]; then
  [ -f $JOB/blender523_egl_libs_scripts.tar ] || { echo FALTA_TAR_LIBS; exit 2; }
  tar -xf $JOB/blender523_egl_libs_scripts.tar -C $JOB debs
  mkdir -p $BASE/libs && for d in $JOB/debs/*.deb; do dpkg-deb -x "$d" $BASE/libs; done && touch $BASE/libs/.ok
fi
if [ ! -f $BASE/pillow/.ok ]; then
  mkdir -p $BASE/pillow && (python3 -c "import PIL" 2>/dev/null || timeout 180 pip install -q --target $BASE/pillow pillow) && touch $BASE/pillow/.ok
fi
# constructores versionados también quedan en el volumen (referencia; cada trabajo igual sube su copia del 213)
[ -d $JOB/constructores ] && V=$(python3 -c "import json;print(json.load(open('$JOB/constructores/VERSION.json')).get('version','v1'))" 2>/dev/null || echo v1) && mkdir -p $BASE/constructores/$V && cp -a $JOB/constructores/. $BASE/constructores/$V/ 2>/dev/null
cat > /root/myia_env.sh <<E
export BLENDER=$BASE/blender/blender
export LD_LIBRARY_PATH=$BASE/libs/usr/lib/x86_64-linux-gnu:$BASE/libs/lib/x86_64-linux-gnu:\${LD_LIBRARY_PATH:-}
export PYTHONPATH=$BASE/pillow:\${PYTHONPATH:-}
export MYIA_GPU_BASE=$BASE
E
. /root/myia_env.sh
$BLENDER --version | head -1 || { echo BLENDER_NO_ARRANCA; exit 3; }
echo "BASE $BASE"
echo SETUP_OK
