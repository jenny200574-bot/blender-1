#!/bin/bash
# Motor unificado v1 (10-nov-2026): puerta para n8n (sudo -n desde entrada_ssh.sh del usuario restringido n8ntaller).
set -u
V=/opt/myia-motor-unificado/v1_20261110
if [ -f $V/entrada_n8n.off ]; then echo '{"ok": false, "error": "motor unificado apagado (entrada_n8n.off)"}'; exit 0; fi
exec /usr/bin/python3 $V/motor/entrada_n8n.py "$@"
