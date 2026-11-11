#!/bin/bash
set -euo pipefail
export DEBIAN_FRONTEND=noninteractive
export TEXT_ENCODER_DEVICE=cpu
export HF_HOME=/workspace/hf-cache
export HF_HUB_ENABLE_HF_TRANSFER=1
export PYTHONUNBUFFERED=1
mkdir -p /workspace/out /workspace/hf-cache /workspace/src
cd /workspace
echo "=== START3 $(date -u) ===" | tee /workspace/out/status.txt
nvidia-smi -L | tee -a /workspace/out/status.txt
python -m pip install -q --upgrade pip
python -m pip install -q huggingface_hub hf_transfer accelerate peft einops hydra-core omegaconf \
  'numpy>=1.23' 'scipy>=1.10' tqdm pydantic filelock bvhio pillow packaging boto3 'urllib3>=2.0'
python -m pip install -q 'transformers>=4.44,<5.2' || python -m pip install -q transformers
if [ ! -d /workspace/src/kimodo/.git ]; then
  git clone --depth 1 https://github.com/nv-tlabs/kimodo.git /workspace/src/kimodo
fi
cd /workspace/src/kimodo
SKIP_MOTION_CORRECTION_IN_SETUP=1 python -m pip install -q -e . --no-deps
echo "=== Prefetch $(date -u) ===" | tee -a /workspace/out/status.txt
python - <<'PY'
from huggingface_hub import snapshot_download
import sys
repos=['NousResearch/Meta-Llama-3-8B-Instruct','McGill-NLP/LLM2Vec-Meta-Llama-3-8B-Instruct-mntp','McGill-NLP/LLM2Vec-Meta-Llama-3-8B-Instruct-mntp-supervised','nvidia/Kimodo-SOMA-RP-v1.2']
for r in repos:
  print('DL', r, flush=True)
  try:
    snapshot_download(r, ignore_patterns=(['original/*'] if 'Llama' in r else None))
    print('OK', r, flush=True)
  except Exception as e:
    open('/workspace/out/download_fail.txt','w').write(f'{r}\n{type(e).__name__}\n{e}'); print('FAIL_DL', r, e); sys.exit(42)
PY
python - <<'PY'
import json, os
from pathlib import Path
hf=Path(os.environ['HF_HOME'])/'hub'
for name in ['models--McGill-NLP--LLM2Vec-Meta-Llama-3-8B-Instruct-mntp','models--McGill-NLP--LLM2Vec-Meta-Llama-3-8B-Instruct-mntp-supervised']:
  for cfg in (hf/name).rglob('adapter_config.json'):
    d=json.loads(cfg.read_text())
    if d.get('base_model_name_or_path')=='meta-llama/Meta-Llama-3-8B-Instruct':
      d['base_model_name_or_path']='NousResearch/Meta-Llama-3-8B-Instruct'
      cfg.write_text(json.dumps(d, indent=2)); print('patched', cfg)
PY
echo "=== GEN3 all $(date -u) ===" | tee -a /workspace/out/status.txt
cd /workspace/src/kimodo
# three separate CLI calls with --no-postprocess (model reload cost accepted; avoids motion_correction)
for name in walk_to_point walk_sit turn90; do
  case $name in
    walk_to_point) PROMPT='A child walks forward to a point and stops';;
    walk_sit) PROMPT='A child walks forward then sits down on the ground';;
    turn90) PROMPT='A child walks, turns ninety degrees to the right, then continues walking';;
  esac
  DUR=$(python -c "import json;c=json.load(open('/workspace/constraints/$name.json'))[0];n=max(c['frame_indices'])+1;print(round((n-1)/30.0,2))")
  echo "=== GEN $name dur=$DUR $(date -u) ===" | tee -a /workspace/out/status.txt
  TEXT_ENCODER_DEVICE=cpu python -m kimodo.scripts.generate "$PROMPT" \
    --model soma --duration "$DUR" \
    --constraints /workspace/constraints/$name.json \
    --num_samples 1 --seed 7 \
    --output /workspace/out/$name --bvh --bvh_standard_tpose --no-postprocess \
    2>&1 | tee /workspace/out/gen_$name.log
done
find /workspace/out -type f | sort | tee /workspace/out/filelist.txt
du -sh /workspace/out /workspace/hf-cache | tee -a /workspace/out/status.txt
echo "DONE $(date -u)" | tee -a /workspace/out/status.txt
