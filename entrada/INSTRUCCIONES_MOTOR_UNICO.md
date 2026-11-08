# Motor único MYIA — instrucciones de la copia de respaldo

Foto del motor tomada el **7-nov-2026 a las 11:32 (hora de Bogotá, UTC−5)** desde el box `/workspace/MOTOR_UNICO_20261107/`.
Es la **versión t317 final sellada** (`MANIFIESTO_VERSION.json` → `20261107-dev6-cpu+t317-definitivo`, sellada a las 11:32 hora de Bogotá): 197/197 pruebas, Argon automático en paralelo (en seco) y luces corregidas. El `SHA256SUMS.txt` interno del motor se verificó completo antes de empaquetar. Si después aparece una versión más nueva, vale la más nueva.

No tiene claves: se sacaron `.secrets`, `*.env` y tokens, y se revisó con búsqueda de patrones y de valores reales. La credencial de Argon se lee desde una ruta que hay que poner a mano en cada máquina (`config/argon_credencial_ruta.json`). No copies claves aquí.

## 1. Qué hay en esta carpeta

| Ruta | Qué es |
|---|---|
| `MOTOR_UNICO_20261107/` | El motor completo: código (`motor/`), entrada pública (`motor_unico.py`), `config/` con interruptores `.off`, `bibliotecas/`, `pruebas/`, `paquetes/` (entradas de prueba y Guardianes), `evidencia/` (hojas de contacto, logs, ledger), `respaldos/` y `archivo/` (versiones anteriores, nada borrado). |
| `dependencias_externas/workspace/...` | Los 39 archivos sueltos de carpetas viejas del box que el motor lee por ruta absoluta `/workspace/...`. Están copiados con la misma ruta para que el paquete se sostenga solo. |
| `requisitos_target_blender.txt` | Lista de librerías Python (scipy, casadi, pinocchio, crocoddyl...) que vivían en `/workspace/LIBRERIAS_MOTOR_20261104/target_blender` (1,3 GB). No se copiaron: se reinstalan con pip. |
| `INSTRUCCIONES_MOTOR_UNICO.md` | Este archivo. |
| `MANIFIESTO_PAQUETE.json` | Lista de archivos externos incluidos y lo que no se incluyó. |

Documentos dentro del motor que conviene leer en este orden:
1. `MOTOR_UNICO_20261107/README.md` y `LEEME.md`: estado corto.
2. `MOTOR_UNICO_20261107/INFORME_T317_ARGON_Y_EXPOSICION.md`: cierre t317 (Argon automático y luces). Luego `RESULTADO_FASES_0a6.md`, que es el informe t314 + t316.
3. `MOTOR_UNICO_20261107/CONTRATO_MOTOR_UNICO.md`: reglas del motor.
4. `MOTOR_UNICO_20261107/motor/GUIA_BIBLIOTECAS_Y_PUENTES.md`: dónde están las bibliotecas, cómo se alimentan y cómo hacer puentes nuevos.
5. `MOTOR_UNICO_20261107/MEJORAS_ACTIVAS_T314.md`, `DIAGNOSTICO_VISUAL_T316.md`, `FALTANTES_GRUPO_B.md`.

## 2. Cómo funciona: una entrada y 16 etapas

Hay una sola entrada pública: `entrada_escena.json` más los archivos que nombra, cada uno con ruta relativa, bytes y SHA-256. El motor no depende de ningún canal, escena ni personaje. Todo sale de la entrada y de las bibliotecas.

Las 16 etapas, todas en `motor/orquestador.py` y en el constructor común:
1. Fuentes y control de gasto (ledger antes de cada gasto).
2. Argon con caché (recetas nuevas).
3. Preparar y puentes (datos que llegan en otros formatos).
4. Validación del contrato.
5. ADN → apariencia (caras y ropa con la base CPU).
6. Blend base y escenario vivo (arquitectura por datos).
7. Objetos: buscador de formas (receta exacta → parecida → composición → receta nueva de Argon → FALTA), recetas y constructores de Star, puntos world→local, bisagras, controles c + IK.
8. Esqueletos, incluido el de ave.
9. Escalera de movimiento: Argon → catálogo → Kimodo → CMU.
10. Retarget, pulida y contactos.
11. Cámara del SB + 4g.
12. Luz por emisor, por datos, con reloj global.
13. Revisión.
14. Empaquetado.
15. Render.
16. Montaje, con tomas de 10 s como máximo y sin partir.

Salida: animación con caras y ropa más `tiempos_dialogo.json`. La voz y los labios los hace Omni después (t295).
Si falta un dato, el motor responde BLOQUEADO y dice qué falta y qué módulo lo produce. No inventa datos ni entrega videos parciales.

## 3. Cómo correrlo

Requisitos que ya se probaron en el box: Python 3.13, Blender 5.2.3 LTS (CPU), numpy, jsonschema, Pillow, ffmpeg 7.1 y SciPy.

```bash
cd MOTOR_UNICO_20261107
# prueba CPU explícita (producción sigue apagada con motor_unico.off)
python3 motor_unico.py paquetes/<paquete>/entrada_escena.json --salida /ruta/salida_nueva --prueba-cpu --blender /ruta/a/blender
# regresión oro
python3 motor_unico.py <entrada_escena.json> --salida /ruta/nueva --regresion --blender /ruta/blender --referencia <metricas_ref.json>
```
Salida esperada: `{"estado":..., "faltantes":N, "gasto_usd":0}`. Código 0 = completo; 2 = faltan datos (BLOQUEADO).

### Pruebas unitarias (en seco, sin red ni gasto)
```bash
cd MOTOR_UNICO_20261107
for t in pruebas/test_*.py; do python3 -B "$t"; done
```
Resultado en el box sobre esta misma copia: test_cpu 40 OK, test_no_facial_v5 35 OK, test_puentes_fisicos 14 OK, test_t307 28 OK, test_t314 26 OK, test_t316 10 OK, test_t317 17 OK, test_traductor_adn 16 OK (186 OK en total, más test_dev2 9/11). La suite sellada t317 da **197/197** (`evidencia/suite_t317_definitiva.log`) y la de paralelo 16/16 (`evidencia/t317_paralelo_regresiones.log`).
`test_dev2` da 2 errores `FileExistsError` **a propósito**: no deja sobrescribir carpetas de evidencia que ya existen (`evidencia/montaje_colores_dev2` y `paquetes/fixture_negativa_oclusor`). No es una falla del motor. Para volver a correrla hay que usar una copia sin esas carpetas.
Las pruebas con Blender (`pruebas/probar_*_blender.py`, `verificar_*`) necesitan Blender instalado.

## 4. Interruptores .off (en `config/` y en la raíz)

- `motor_unico.off` (raíz): producción APAGADA. Solo se corre con `--prueba-cpu` explícito.
- `argon_automatico.off` / `argon_recetas.off` (si se crean): detienen la generación automática de recetas.
- `argon_envio.off`: mientras exista, NO se envía nada real a Argon (solo cotización en seco, con `dry_run:true` en `config/argon_transporte.json`). Para la primera corrida real hay que borrarlo con el visto bueno de Ricardo, mostrando antes cuántas llamadas son y cuánto cuestan. El dinero lo controla un solo parámetro de presupuesto total. Hasta ahora el tope total es US$3 y no hay límite por llamada.
- `audio.off`: voz y labios fuera del motor (los hace Omni).
- `t314_desarrollo.off`, `t316_desarrollo.off`, `t317_desarrollo.off`, `integracion_final.off`, `compiladores_reales.off`, `star_unificado.off`, `catalogo_star_completo.off`, `no_facial.off`, `puentes_fisicos.off`, `traductor_adn.off`: cada fase nueva queda apagada para producción y prendida solo en pruebas CPU explícitas.
- Para apagar una capacidad se crea su `.off`. Antes de reemplazar algo, `seguridad.guardar()` / `archivar()` guardan la versión anterior en `respaldos/` o `archivo/`.

## 5. Bibliotecas y cómo alimentarlas (resumen; el detalle está en la GUÍA)

| Biblioteca | Ruta (dentro de MOTOR_UNICO_20261107) |
|---|---|
| Fórmulas Star (44 fórmulas / 42 constructores) | `bibliotecas/formulas_star_estrictas.json` |
| Buscador de formas (umbral, sinónimos) | `bibliotecas/politica_busqueda_formas_cpu.json` |
| Recetas nuevas aprobadas (incluye las de Argon) | `bibliotecas/recetas_aprobadas.json` |
| Apariencia base CPU (caras/ropa) | `bibliotecas/apariencia_base_cpu.json` |
| Poses y movimientos (Kimodo) | `bibliotecas/kimodo/catalogo_poses/`, `catalogo_perfiles_movimiento/`, `mocap/` |
| Movimientos nuevos aprobados (Kimodo devuelve aquí) | `bibliotecas/movimientos_aprobados/catalogo.json` + `bvh/<sha>.bvh` |
| Perfiles anatómicos genéricos (antes "Kael") | `bibliotecas/star/catalogos/humanoide_adulto_*.json` |
| Motor de puntos Star | `bibliotecas/star/motor_puntos/` |
| Registro | `bibliotecas/registro.json` |

Para alimentar: crear un directorio con los archivos y un `lote.json` (kind: recipe, pose, movement, cmu, mixamo, video, profile o material; con sha256 y bytes calculados, nunca escritos a mano) e importarlo con `motor/importar_lote.py`. Lo importado entra en cuarentena (`PENDIENTE_REVISION_TECNICA`) y solo se activa después de la revisión técnica. Los pasos están en la sección 5 de la GUÍA. Para puentes nuevos, sección 6.

## 6. Carpetas viejas de las que depende

El código guarda rutas absolutas del box `/workspace/...`. Los archivos que lee de ahí vienen copiados en `dependencias_externas/workspace/`, con la misma ruta:

- `MOTOR_v9_desde_PC/v9_universal_calidad_20261106/`: reglas de validación y 24 fichas de objetos (`biblioteca_objetos_lectura_213`). El `entorno_cpu` (venv de 151 MB con SciPy) NO se copió porque un venv no se puede mover; en otra máquina se reinstala con `pip install scipy numpy` y se pone su ruta en `config/runtime_cpu.json` (`numeric_python`).
- `REVISION_TRASPASO_20261104/entradas_SB_t896/...`: hojas del cubo fijo de personajes y una imagen de objeto, que son entradas de Guardianes.
- `STAR_MOTOR_UNIVERSAL_v2_20261030/src/cajas/`: cliente Argon `myia_argon.py` y `precios_myia.json` (tarifas).
- `STAR_MOTOR_UNIVERSAL_v6_20261031/src/encuadre_cams_v4.py`: encuadre de cámaras de Star.
- `STAR_MOTOR_ESCENAS_v5_20261031/.../esc_6_v5.json`: escena 6 de Star (fixture del convertidor).
- `PRUEBA_ESC6_20261031/05_moldes_motor_puntos/`: animación de puntos y `HairSample_Male.vrm`.
- `videos_star/ENTREGA_AKO_MOTOR_FONDOS_20261107/salida/esc6/hoja_fondos_v2.png`: referencia de motor_fondos v2.
- `LIBRERIAS_MOTOR_20261104/target_blender`: solo librerías pip; se reinstalan con `requisitos_target_blender.txt`:
  `pip install --target <carpeta> -r requisitos_target_blender.txt`. Después se pone esa carpeta en `bibliotecas/kimodo/mocap` (clave `target_blender`).

Para correr fuera del box hay dos formas:
(a) Crear un enlace `/workspace` que apunte a `dependencias_externas/workspace`. Así no se cambia el código, pero toca la raíz del servidor y en el 213 hace falta el sí de Ricardo.
(b) Cambiar el prefijo `/workspace/` por la ruta nueva en `config/` y en los archivos que lo nombran. Esto se hace con respaldo y `.off`, igual que cualquier cambio.
Las pruebas unitarias de la sección 3 no necesitan ninguna de las dos.

## 7. Estado A/B (al momento de la foto)

- **A (lo que le toca al motor): 0 pendientes** dentro del alcance BASE_CPU (caras/ropa con la biblioteca base de CPU; la GPU queda para después).
- **B (datos de la escena que faltan): 24 filas / 17 causas** en Guardianes: 2B truncado y contactos, reglas de colisión, anatomía del ave, asociación objeto↔ADN, recetas de cama y cofre, 22 decoraciones sin receta, escenario vivo, calidad técnica de 15 movimientos, ejes y unidades, luz artística, y cámaras PAN/CRANE sin amplitud. Los campos exactos y quién produce cada uno están en `FALTANTES_GRUPO_B.md` y `resultado.json`.
- Guardianes: **BLOQUEADO**. Hay hoja de contacto solo diagnóstica; no hay video final.
- Gasto real: **US$0**. Argon real nunca enviado; GPU no usada.
- Luz t317: los píxeles saturados bajaron de 20,66% a 0%, con exposición automática global y gate antes de los clips. Lo que no se corrigió es la fidelidad de la geometría.
- Argon t317: detecta 29 entradas; 25 se pueden preparar y 4 necesitan asociación o tipo de referencia de origen.
- Pruebas selladas: suite t317 197/197; oro 23 exactas (`evidencia/oro_t317_definitivo/`).

## 8. Qué falta

1. Completar los datos B con sus productores (SB, 4a2, 4a4, 01/Star, ADN OBJ, 2B).
2. Primera corrida real de Argon, en paralelo y automática: mostrar a Ricardo el número de llamadas y el costo, y quitar `argon_envio.off` solo con su sí.
3. Luz artística por toma (4a2/4a4). El brillo técnico ya quedó corregido en t317.
4. GPU: imagen→3D para caras y ropa de alta fidelidad, y prueba completa de Guardianes y luego otra escena de otro canal.
5. Conectar al flujo n8n (fase 9, promoción) solo con aprobación.

## 9. Reglas que no se rompen

Nunca imprimir claves. No tocar 217.76.52.53 ni el pod de Star 32soe7oh2f1gtf. En el 213 solo se trabaja en carpetas NUEVAS de `/opt/myia-motor-v9/` y en el flujo n8n autorizado, con respaldo. No sobrescribir `v9_universal_calidad_20261106`. No cambiar producción. Respaldo y `.off` antes de cada cambio. No inventar datos. El ADN manda la apariencia, el SB manda la cámara y las tomas duran 10 s como máximo, sin partirlas.
