#!/bin/bash
set -euo pipefail
umask 077
exec /opt/myia-motor-v9/respaldo_plan_20261107_193319/herramientas/venv_cpu/bin/python -B /opt/myia-motor-v9/v9_motor_unico_20261107/entrada_motor.py "$@"
