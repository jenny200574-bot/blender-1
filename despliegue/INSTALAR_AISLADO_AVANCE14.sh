#!/bin/bash
# Instala el tarball experimental en directorio aislado. No modifica /opt/myia-motor-v9 instalado.
set -euo pipefail
VPS_EXP="${VPS_EXP:-/opt/myia-motor-v9-experimental-avance14}"
TGZ="${1:?uso: VPS_EXP=/opt/... $0 avance14_camara_directa_sb_exp_<git>.tar.gz}"
mkdir -p "$VPS_EXP"
tar -xzf "$TGZ" -C "$VPS_EXP"
PKG="$VPS_EXP/avance14_camara_directa_sb_exp"
test -f "$PKG/motor/motor/camara_busqueda_reparacion.off" || { echo "FALTA .off directa SB"; exit 2; }
python3 -B "$PKG/motor/pruebas/test_camara_directa_sb.py"
echo "Instalado en $PKG"
echo "Leer $PKG/../README_DESPLIEGUE.md o $PKG/README_DESPLIEGUE.md tras empaquetado"
