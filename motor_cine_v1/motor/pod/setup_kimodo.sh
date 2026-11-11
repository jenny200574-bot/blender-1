#!/bin/bash
# [motor unificado v1, Kimodo ON 10-nov-2026] Instala Kimodo UNA vez en el volumen persistente ($BASE/kimodo): librerías, código y pesos
# (Llama-3-8B NousResearch + LLM2Vec + nvidia/Kimodo-SOMA-RP-v1.2). Mismos pasos que el lab aprobado (remote_run3.sh, Ricardo t995u).
# Los pods siguientes arrancan listos (no se vuelve a descargar nada).
set -uo pipefail
BASE=${MYIA_GPU_BASE:-/root/myia_gpu}; K=$BASE/kimodo; mkdir -p $K/hf $K/src
export HF_HOME=$K/hf HF_HUB_ENABLE_HF_TRANSFER=1 PYTHONUNBUFFERED=1 PIP_DISABLE_PIP_VERSION_CHECK=1
# venv en el volumen que VE el torch de la imagen del pod (no se baja otro torch)
[ -x $K/venv/bin/python ] || python3 -m venv --system-site-packages $K/venv || { echo KIMODO_VENV_FALLO; exit 20; }
PY=$K/venv/bin/python
df -h $BASE | tail -1
if [ ! -f $K/venv/.ok ]; then
  $PY -m pip install -q huggingface_hub hf_transfer accelerate peft einops hydra-core omegaconf \
    'numpy>=1.23,<2.3' 'scipy>=1.10' tqdm pydantic filelock bvhio packaging boto3 'urllib3>=2.0' 'transformers>=4.44,<5.2' || { echo KIMODO_PIP_FALLO; exit 21; }
  touch $K/venv/.ok
fi
if [ ! -f $K/src/.ok ]; then
  TS=$(date +%Y%m%d_%H%M%S); [ -d $K/src/kimodo_tmp ] && mv $K/src/kimodo_tmp $K/src/_prev_tmp_$TS; git clone -q --depth 1 https://github.com/nv-tlabs/kimodo.git $K/src/kimodo_tmp || { echo KIMODO_CLONE_FALLO; exit 22; }
  (cd $K/src/kimodo_tmp && git rev-parse HEAD > $K/src/COMMIT) ; [ -d $K/src/kimodo ] && mv $K/src/kimodo $K/src/_prev_$TS; mv $K/src/kimodo_tmp $K/src/kimodo
  (cd $K/src/kimodo && SKIP_MOTION_CORRECTION_IN_SETUP=1 $PY -m pip install -q -e . --no-deps) || { echo KIMODO_INSTALL_FALLO; exit 24; }
  touch $K/src/.ok
fi
if [ ! -f $K/hf/.ok ]; then
  $PY - <<'PY' || { echo KIMODO_PESOS_FALLO; exit 23; }
from huggingface_hub import snapshot_download
for r in ['NousResearch/Meta-Llama-3-8B-Instruct','McGill-NLP/LLM2Vec-Meta-Llama-3-8B-Instruct-mntp','McGill-NLP/LLM2Vec-Meta-Llama-3-8B-Instruct-mntp-supervised','nvidia/Kimodo-SOMA-RP-v1.2']:
    print('DL', r, flush=True); snapshot_download(r, ignore_patterns=(['original/*'] if 'Llama' in r else None)); print('OK', r, flush=True)
PY
  $PY - <<'PY'
import json, os
from pathlib import Path
hf = Path(os.environ['HF_HOME']) / 'hub'
for name in ['models--McGill-NLP--LLM2Vec-Meta-Llama-3-8B-Instruct-mntp', 'models--McGill-NLP--LLM2Vec-Meta-Llama-3-8B-Instruct-mntp-supervised']:
    for cfg in (hf / name).rglob('adapter_config.json'):
        d = json.loads(cfg.read_text())
        if d.get('base_model_name_or_path') == 'meta-llama/Meta-Llama-3-8B-Instruct':
            d['base_model_name_or_path'] = 'NousResearch/Meta-Llama-3-8B-Instruct'; cfg.write_text(json.dumps(d, indent=2)); print('patched', cfg)
PY
  touch $K/hf/.ok
fi
CHK='import torch,transformers,kimodo.scripts.generate;print("torch",torch.__version__,"transformers",transformers.__version__,"cuda",torch.cuda.is_available())'
if ! $PY -c "$CHK"; then
  echo "KIMODO: el torch de la imagen no sirve -> torch nuevo en el venv del volumen (una sola vez)"
  $PY -m pip install -q 'torch>=2.6' || { echo KIMODO_TORCH_FALLO; exit 26; }
  $PY -c "$CHK" || { echo KIMODO_IMPORT_FALLO; exit 25; }
fi
du -sh $K/venv $K/hf $K/src 2>/dev/null; df -h $BASE | tail -1
echo KIMODO_LISTO
