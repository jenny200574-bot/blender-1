#!/bin/bash
# PISTA INMI (2026-10-29): orden 75 — + «personajes» (Cargar personajes, gratis).
# Paso 1 programa imágenes (31-oct-2026): + «estilo» (fijar/leer muestra oficial, gratis).
# Paso 2 programa imágenes (31-oct-2026): + «escena» (armar/leer ficha Nivel 2, gratis).
# Animatic gratis (31-oct-2026): + «animatic» (armar/leer MP4 de pinturas aprobadas, sin IA).
# Planeador storyboard (1-nov-2026): + «storyboard» (cotizar/validar/traducir gratis; correr solo con cajas/HABILITAR_PAGO_SB).
# Entrada ÚNICA del usuario restringido n8ntaller (forzada en authorized_keys). Solo deja correr paso00_cadena.py con argumentos simples.
# Fondo cubemap (2-nov-2026): + cubemap (cubo/cotizar/proyectar gratis; pintar solo con cajas/HABILITAR_PAGO_FC).
set -u
CMD="${SSH_ORIGINAL_COMMAND:-}"
# El nodo SSH de n8n antepone "cd / ; " (parámetro cwd). Solo se acepta exactamente ese prefijo.
CMD="${CMD#cd / ; }"
CMD="${CMD#cd '/' ; }"
# AVANCE06 Ricardo 2026-11-07 21:30 Bogota: sólo generador JSON acotado y sus argumentos.
if [[ "$CMD" =~ ^generador_json\ (estado|ejecutar\ [A-Za-z0-9][A-Za-z0-9_-]{0,79})$ ]] || [[ "$CMD" =~ ^generador_json\ adn\ b64\.[A-Za-z0-9_-]+\ --ok\ [0-9]+(\.[0-9]+)?\ --aprobado\ [A-Za-z0-9_-]+$ ]]; then
  read -r -a ARGS <<< "$CMD"
  exec sudo -n /opt/myia-motor-v9/avance06_20261107/entrega/codigo/puente_json.sh "${ARGS[@]:1}"
fi
# VER pre-gasto (inmi 2-nov-2026): + «ver_prepago MANIFIESTO.json» (SECO, nunca paga). Solo manifiestos en cajas/ver_prepago/manifiestos/. exit 1 si FAIL.
if [[ "$CMD" =~ ^ver_prepago\ ([A-Za-z0-9._-]+\.json)$ ]]; then
  MF="/opt/myia-taller-n8n/cajas/ver_prepago/manifiestos/${BASH_REMATCH[1]}"
  [[ -f "$MF" ]] || { echo '{"ok": false, "error": "manifiesto no existe"}'; exit 1; }
  exec /usr/bin/python3 /opt/myia-taller-n8n/cajas/ver_prepago/ver_prepago.py "$MF"
fi
# CUBO FIJO (inmi 2-nov-2026): + «cubo_fijo leer|ver|ensamblar|registrar_pj|extraer|sellar» (disco cajas/cubo_fijo/, gratis, nunca paga).
if [[ "$CMD" =~ ^cubo_fijo\ (leer|ver|ensamblar|registrar_pj|extraer|sellar)(\ [A-Za-z0-9._,_-]+)?$ ]]; then
  read -r -a ARGS <<< "$CMD"
  exec /usr/bin/python3 /opt/myia-taller-n8n/cajas/cubo_fijo/cubo_fijo.py "${ARGS[@]:1}"
fi
# SELLO PAGO (inmi 2-nov-2026 17:45 Bogotá): + «sello_pago estado|hoja|adn b64.X --ok USD --aprobado QUIEN». Paga SOLO si existe
# cajas/HABILITAR_PAGO_ADN (compuerta con monto) y cabe en --ok / tope por llamada; ledger «taller-sello-». Sin compuerta: no llama (US$0).
if [[ "$CMD" =~ ^sello_pago\ (estado|hoja|adn)(\ b64\.[A-Za-z0-9_-]+)?(\ --ok\ [0-9]+(\.[0-9]+)?\ --aprobado\ [A-Za-z0-9._-]+)?$ ]]; then
  read -r -a ARGS <<< "$CMD"
  exec sudo -n /opt/myia-staging-arreglos-20261026/venv/bin/python /opt/myia-taller-n8n/cajas/sello_pago.py "${ARGS[@]:1}"
fi
# MOTOR v9 universal calidad (fase 4, 6-nov-2026, Ricardo t246u–t248u): «motor_v9 preparar|armar --canal C --capitulo N --escena E [--paquete ID]».
# Gratis: sin Argon ni GPU. Retirado t912 (inmi): ver bak_20261106_* y /opt/myia-motor-v9/_archivo_inmi_20261106/. Interruptor: <motor>/entrada_n8n.off
# T317: puente aprobado por Ricardo 7-nov-2026 19:59 Bogotá; respaldo previo.
if [[ "$CMD" =~ ^motor_v9\ (preparar|traducir|armar)(\ --(canal|capitulo|escena|paquete)\ [A-Za-z0-9._-]+)*$ ]]; then
  read -r -a ARGS <<< "$CMD"
  exec sudo -n /opt/myia-motor-v9/v9_motor_unico_20261107/entrada_motor.sh "${ARGS[@]:1}"
fi
if [[ "$CMD" =~ ^motor_v9\ (preparar|armar)(\ --(canal|capitulo|escena|paquete)\ [A-Za-z0-9._-]+)*$ ]]; then
  read -r -a ARGS <<< "$CMD"
  exec sudo -n /opt/myia-motor-v9/v9_universal_calidad_20261106/entrada_motor.sh "${ARGS[@]:1}"
fi
if [[ ! "$CMD" =~ ^paso00_cadena\ (revisar_guardar01|cotizar|correr|juntos|estado|ramas|biblioteca|pintar|ver|resolver|personajes|estilo|escena|animatic|storyboard|cubemap|guion|dirigir)(\ [A-Za-z0-9._:=,+-]+)*$ ]]; then
  echo '{"ok": false, "error": "comando no permitido"}'; exit 0
fi
read -r -a ARGS <<< "$CMD"
exec sudo -n /opt/myia-staging-arreglos-20261026/venv/bin/python /opt/myia-taller-n8n/cajas/paso00_cadena.py "${ARGS[@]:1}"
