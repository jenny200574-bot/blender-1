# blender-1 — Motor único de Blender de MYIA Estudio

Código fuente limpio del motor de animación 3D en Blender (T317 + cambios de AVANCE_04 a AVANCE_08, 7-nov-2026). **Lee primero `AGENTS.md` y `docs/TRASPASO_INMI.md`.**

## Estructura
| Carpeta | Qué hay |
|---|---|
| `motor/` | Motor único vigente (copia de `avance08_20261107/MOTOR_UNICO_20261107` en el VPS): `motor_unico.py`, `motor/` (módulos: física, cámara, luces, ADN, Argon, revisor…), `bibliotecas/`, `config/` (incluye banderas `.off` = función apagada), `pruebas/` (tests), `paquetes/` (fixtures de entrada), `evidencia/oro_t317_definitivo/` (métricas oro de referencia). Contratos: `CONTRATO_MOTOR_UNICO.md`, `CONTRATO_ENTRADA.schema.json`. |
| `entrada/` | Puente de entrada desde n8n (`entrada_motor.py/.sh`), `activar_y_probar.py`, `INSTRUCCIONES_MOTOR_UNICO.md`. |
| `avances/avance04..08/` | Código, configuración, esquemas/prompts de Argon, evidencias JSON (validaciones, ledger de costos) de cada fase. Generador nuevo: `avances/avance0X/codigo/generar_schema.py`; traductor 02T: `avances/avance04/codigo/traductor_02t.py`; puente JSON: `avances/avance06/codigo/puente_json.py`. |
| `escenas/guardianes_esc1_candidata/` | Datos actuales de la escena 1 de Guardianes (candidata, sin aprobar). |
| `escenas/fuente_capitulo1/` | Texto del capítulo 1 (T01) y biblias de la serie, fuente de la 2B. |
| `n8n/` | Código JS de los nodos Code de 02T, 02, SELLO (sello_pago) y MOTOR exportados del workflow `debwaH9svFMoTnOf`, más parámetros de los nodos SSH/IF (sin credenciales). |
| `docs/` | Traspaso, informes AVANCE, bloqueos, costos. |

## Cómo correr las pruebas (en seco, sin red ni gasto)
Requisitos probados: Python 3.11+ (3.13 en el box), numpy, jsonschema, Pillow, SciPy; Blender 5.2.3 LTS CPU y ffmpeg solo para pruebas con Blender.
```bash
cd motor
for t in pruebas/test_*.py; do python3 -B "$t"; done
```
`test_dev2` da 2 `FileExistsError` a propósito si ya existen las carpetas de evidencia (ver `entrada/INSTRUCCIONES_MOTOR_UNICO.md`). Las pruebas `pruebas/probar_*_blender.py` y `verificar_*` necesitan Blender.

## Regresión oro (23 métricas exactas, tolerancias sin cambiar)
```bash
cd motor
python3 motor_unico.py <entrada_escena.json> --salida /ruta/nueva --regresion --blender /ruta/blender \
  --referencia evidencia/oro_t317_definitivo/metricas_oro.json
```
Código 0 = completo; 2 = BLOQUEADO (faltan datos, el motor dice cuáles).

## Objetivos
1. Escenarios 3D reales (no planos ni sustitutos).
2. Sistema de puntos de Star (anclas/contactos ejecutables por punto).
3. Movimiento natural validado por física.
4. Automatización completa con Argon (Vertex `gemini-3-flash-preview`) desde n8n, sin pasos manuales.

## Estado actual (7-nov-2026, 23:00 Bogotá)
- Oro 23/23 exacto; unit tests OK (`test_t317` 17, `test_traductor_adn` 16 verificados al empaquetar).
- Escena 1 de Guardianes **BLOQUEADA, sin video**. AVANCE_07 dejó 7 bloqueos (`docs/avance07_7_BLOQUEOS_ESC1.csv`). AVANCE_08 (en curso) completó la 2B con el capítulo 1 (52 filas, citas literales), Argon propuso la física y pasó la prueba de sensatez, preflight de datos = 0 faltantes; falta preview CPU completa, aprobación de física/movimientos y render GPU.
- Configuración con valores redactados: define `VERTEX_SA_FILE`, `GCP_PROJECT_ID`, `VPS_HOST` en el entorno.
