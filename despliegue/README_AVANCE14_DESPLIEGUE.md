# Paquete experimental avance14 — cámara directa SB (PR #7)

**Uso:** copiar al VPS en un **directorio aislado**. **No** sustituye `/opt/myia-motor-v9/` ni el motor instalado avance13.

## Relación con PR #6 (etapa 11)

| Pieza | Valor |
|-------|--------|
| Base | Rama `cursor/camara-etapa11-construccion-43f7`, commit `97a7a89` (contenido PR #6) |
| Delta PR #7 | **Un solo commit** `4f439fc`: modo `directa_sb` + `.off` + pruebas comparación |
| Original instalado | **No tocar** — hashes preimages del manifiesto etapa11 en repo siguen siendo la referencia de producción |

## Modo búsqueda OFF (solo esta copia)

- Archivo presente: `motor/motor/camara_busqueda_reparacion.off` → **no** `BUS.buscar`, **no** rejilla ni `mejor_intento`.
- **Revisión intacta:** `construir` + `validar` cuadro a cuadro; oclusiones/fallos → toma `bloqueada`; `production_approved` **false**.
- Para recuperar buscador estándar en la copia experimental: **borrar** ese `.off` (no hacerlo en producción sin decisión explícita).

## Runtime (VPS)

- **Blender:** `4.2.3 LTS` CPU (`bpy`), ruta típica `${BLENDER}` — ver `COMANDOS.env.example`.
- **Python preflight:** `python3` del sistema con `jsonschema` (como avance13).
- **No** GPU, APIs de pago ni credenciales en este paquete.

Dependencias declaradas en `motor/DEPENDENCIAS.json` (referencia; el constructor corre **dentro** de Blender).

## Instalación aislada

```bash
# Elegir raíz nueva, p. ej.:
export VPS_EXP=/opt/myia-motor-v9-experimental-avance14
sudo mkdir -p "$VPS_EXP"
sudo tar -xzf avance14_camara_directa_sb_exp_<GIT>.tar.gz -C "$VPS_EXP"
# → $VPS_EXP/avance14_camara_directa_sb_exp/
```

O ejecutar `INSTALAR_AISLADO.sh` (edita `VPS_EXP` dentro del script).

Verificar integridad:

```bash
sha256sum -c avance14_camara_directa_sb_exp_<GIT>.tar.gz.sha256
python3 - <<'PY'
import json, pathlib
m=json.loads(pathlib.Path("avance14_camara_directa_sb_exp/manifiesto_paquete.json").read_text())
assert m["camara_busqueda_reparacion_off"] is True
print("OK manifiesto", m["git_commit"], "archivos", len(m["archivos"]))
PY
```

## Entrada externa (preflight + construcción)

Variables (ajustar rutas reales; **sin** datos de cliente en el paquete):

```bash
export M=$VPS_EXP/avance14_camara_directa_sb_exp/motor
export B=${BLENDER:-/opt/blender/blender-4.2.3/blender}
export PAQUETE=$RUTA_PAQUETE_NORMALIZADO   # carpeta con entrada del orquestador
export NUCLEO=$RUTA_NUCLEO                 # carpeta con escena.blend del núcleo reutilizable
export SAL=$VPS_EXP/ejecuciones/run_$(date +%Y%m%d_%H%M%S)
mkdir -p "$SAL"
```

**1. Preflight sin Blender**

```bash
python3 -B "$M/motor/preflight_constructor.py" "$PAQUETE" \
  --nucleo "$NUCLEO/escena.blend" \
  --salida "$SAL/preflight_constructor.json"
```

Código 0 = sin BLOQUEO; 2 = BLOQUEO (corregir entrada).

**2. Preflight geometría (Blender, no guarda)**

```bash
"$B" -b --factory-startup --disable-autoexec "$NUCLEO/escena.blend" \
  -P "$M/motor/preflight_blend.py" -- \
  "$PAQUETE" --salida "$SAL/preflight_blend.json"
```

**3. Constructor completo (etapas 6…11 con cámara directa SB)**

```bash
"$B" -b --disable-autoexec -t 2 --python-exit-code 17 \
  -P "$M/motor/constructor_final.py" -- \
  "$PAQUETE" "$SAL" "$NUCLEO/escena.blend" \
  > "$SAL/constructor.log" 2>&1
echo "rc=$?"
```

**4. Validar salida**

```bash
python3 -B "$M/motor/validar_salida_constructor.py" "$SAL" --paquete "$PAQUETE"
```

Artefactos: `$SAL/escena.blend`, `$SAL/auditoria_4g/camara_v2.json` (`interruptores.directa_sb`, `busqueda_matematica.modo` por toma).

## Solo etapa 11 sintética (smoke CPU, sin escena real)

Fixture incluido: `motor/paquetes/fixture_4g_v5` (ave, **no** cliente).

```bash
python3 -B "$M/pruebas/test_camara_directa_sb.py"

"$B" -b --factory-startup -t 2 --python-exit-code 17 \
  -P "$M/pruebas/blender_camara/probar_directa_vs_busqueda.py" -- \
  "$M" "$SAL/smoke_directa" 24 2
# → comparativa.json (tiempos, frame_set, BVH; no certifica avance13 real)
```

## Comparación busqueda vs directa

Script: `motor/pruebas/blender_camara/probar_directa_vs_busqueda.py`

- Copia temporal del motor **sin** `.off` → corrida con buscador.
- Copia **con** `.off` (como este paquete) → corrida directa SB.
- Salida: `comparativa.json`.

## Limitaciones

- Pruebas del agente cloud **no** ejecutan escena real avance13.
- Oro 23/23 en VPS **no** reemplazado por este paquete.
- Si preflight devuelve BLOQUEO, **no** forzar `production_approved`.
