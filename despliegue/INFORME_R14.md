# INFORME R14 — oclusión universal por storyboard (9-nov-2026)

## Objetivo

- Eliminar regla «no cambiar plan / solo informe» y prohibición de ocultar `ch-*` / `obj-*`.
- Ocultar con `visible_camera` (fcurve **CONSTANT**, solo rango de toma) cualquier obstáculo entre cámara y **sujeto(s) del SB**, sin tocar `hide_render`.
- Protegidos: sujetos SB + hombro OTS (composición); no ocultar lo que forma parte del encuadre pedido.
- Reparaciones: retroceso holgura/encuadre, espejo eje 180° (salvo `CROSSAXIS`), oclusión por rayos BVH.

## Cambios en código

| Archivo | Cambio |
|---------|--------|
| `motor/motor/camara_oclusion_sb.py` | Lógica pura: sujetos protegidos, rayos, malos, espejo eje |
| `motor/motor/camara_despeje_render.py` | `filtrar_objetos_ocultar`; etapa 13: `DESPEJE_SUJETO` |
| `motor/motor/camara_v2_blender.py` | `_tras_validacion_directa` → `reparacion_toma` R14 |
| `motor/motor/camara_directa_exp.py` | Informe y opciones Ricardo actualizados |

## Compuerta etapa 13

- Siguen: `DESPEJE_SIN_FCURVE`, `DESPEJE_FALSO_PASE`.
- Nuevo: **`DESPEJE_SUJETO`** si se registró `visible_camera` en malla de sujeto protegido.

## Reporte por toma

En `experimental_directa.reparacion_toma`:

- `sujetos_protegidos`, `ocultados`, `movimientos` (retroceso / espejo eje), `pasos` (detalle y motivo).

## Interruptores (.off en `motor/motor/`)

- `camara_escenario_despeje_por_toma.off` — oclusión `visible_camera`.
- `camara_retroceso_holgura_directa.off` — retroceso tras validación directa.
- `camara_busqueda_reparacion.off` — modo directa SB (sin buscador).

## Prueba en VPS (copia `_r9`, sin gasto on-demand)

```bash
# 1) Descomprimir overlay sobre el candidato BVH08 (no tocar instalado avance13)
export REPO=/ruta/repo/cursor/camara-directa-sb-exp-43f7
export CAND=/opt/myia-motor-v9/avance14_20261108_buscador/MOTOR_BVH08_CANDIDATO_r14
# o crear r14 copiando MOTOR_BVH08_CANDIDATO → MOTOR_BVH08_CANDIDATO_r14

sudo mkdir -p "$CAND"
sudo tar -xzf avance14_camara_directa_sb_exp_<GIT>.tar.gz -C /tmp
sudo rsync -a --delete /tmp/avance14_camara_directa_sb_exp/motor/ "$CAND/"

# 2) Escena de prueba _r9 (misma que R13, copia aislada)
export STAGE=/opt/myia-motor-v9/copia_escena_r9
export B=${BLENDER:-/opt/blender/blender-4.2.3/blender}
export M="$CAND"

# 3) Constructor etapas 11+13 (CPU, sin RunPod)
"$B" -b "$STAGE/escena.blend" -P "$M/motor/constructor_final.py" -- \
  "$PAQUETE" "$SALIDA" ...

# 4) Revisar JSON cámara: reparacion_toma por viñeta; etapa 13 sin DESPEJE_SUJETO
jq '.tomas[] | {vineta, motor_aplicado, reparacion: .experimental_directa.reparacion_toma}' "$SALIDA/camara_*.json"
```

**Tomas de referencia (escena prueba):** v9 (Eco no sujeto), v2/v5/v6/v7 (cabeza + pared), v4 (cama), v4/v11/v12 (180°).

## Tests locales

```bash
cd motor && for t in pruebas/test_*.py; do python3 -B "$t"; done
```

(Nuevos: `test_camara_oclusion_sb.py`, tests `DESPEJE_SUJETO` en `test_camara_despeje_render.py`.)

## Rendimiento

Reparación acotada: ≤6 cuadros muestreados para rayos, ≤3 pasos de ocultación, sin bucle extra de búsqueda. Objetivo: etapa 11 **≤ ~419 s** en VPS (medir tras despliegue).

## Regresión oro Blender

No ejecutada en este entorno. Si las fcurves `visible_camera` o trayectoria espejada afectan renders, correr regresión 23/23 en VPS.
