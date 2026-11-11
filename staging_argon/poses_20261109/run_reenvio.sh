#!/bin/bash
cd /opt/myia-staging-arreglos-20261026/poses_20261109 || exit 1
set -a; . /opt/myia-staging-arreglos-20261026/staging.env; set +a
export MYIA_FIJOS_ARGON=/opt/myia-staging-arreglos-20261026/FIJOS_ARGON_real MYIA_ARGON_LEDGER=/opt/myia-staging-arreglos-20261026/ledger/ledger_argon.csv MYIA_FIJO_PROMPT=1 MYIA_ARGON_BITACORA=$PWD/bitacora_conteo.log PYTHONDONTWRITEBYTECODE=1
exec /opt/myia-staging-arreglos-20261026/venv/bin/python -B reenviar_L01.py
