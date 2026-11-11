#!/bin/bash
set -euo pipefail
# run as root on 213
mkdir -p /opt/myia-fabricas /opt/myia-biblioteca /opt/myia-fabricas/jobs
# never touch /opt/video-studio
rsync -a --delete /tmp/myia-fabricas-deploy/ /opt/myia-fabricas/
# fix imports: server runs from app/ with local modules
cd /opt/myia-fabricas/app
# seed comun
python3 - <<'PY'
import json,sys
sys.path.insert(0,'.')
from biblioteca import Biblioteca
from pathlib import Path
b=Biblioteca(Path('/opt/myia-biblioteca'))
n=b.importar_recetas_comun(Path('/opt/myia-fabricas/assets/recetas_aprendidas'))
print('recetas_comun', n)
PY
cp /opt/myia-fabricas/scripts/myia-fabricas.service /etc/systemd/system/myia-fabricas.service
systemctl daemon-reload
systemctl enable myia-fabricas.service
systemctl restart myia-fabricas.service
sleep 1
systemctl is-active myia-fabricas.service
curl -sS http://127.0.0.1:18750/v1/health
echo
