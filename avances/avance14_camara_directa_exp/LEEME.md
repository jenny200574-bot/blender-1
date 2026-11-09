# Avance 14 experimental — cámara directa SB (t588/t589)

Copia **separada** de la etapa 11: no sustituye el buscador instalado en VPS avance13.

## Activación

- Archivo `motor/motor/camara_busqueda_reparacion.off` presente → **modo directa SB**.
- Sin el `.off` → comportamiento previo (rejilla + reparaciones hasta `reparaciones_max`).

## Semántica

- Para cada toma con modelo de elevación: **un solo candidato** `(acimut extra 0°, factor distancia 1.0)` derivado del storyboard (plano, lente, movimiento, objetivo).
- **No** se llama a `BUS.buscar` ni se recorre la rejilla de alternativas.
- **Sí** se ejecuta `construir` + `validar` completo (encuadre, holgura, oclusión, eje, cara…).
- Si la validación falla → toma `bloqueada` con `motivos` / `muestras_malas`; **sin** `mejor_intento` ni reconstrucción con otra pose.
- `production_approved` permanece **false** en el motor.

## Prueba sintética (repo, CPU)

```bash
cd motor/pruebas/blender_camara
blender -b --factory-startup -t 2 -P probar_directa_vs_busqueda.py -- \
  ../../.. MOTOR/pruebas/blender_camara/salida_directa_exp 24 2
```

Salida: `comparativa.json` (tiempos, `frame_set`, BVH, `busqueda_matematica` por toma). **No** equivale a escena real avance13.

## VPS — paquete listo (sin clonar repo)

- Empaquetado: `despliegue/empaquetar_avance14_directa_sb.py` → `avance14_camara_directa_sb_exp_<git>.tar.gz` + manifiesto SHA-256.
- Instrucciones operador: `despliegue/README_AVANCE14_DESPLIEGUE.md` (incluido en el tarball como `README_DESPLIEGUE.md`).
- Directorio aislado sugerido: `/opt/myia-motor-v9-experimental-avance14`.
- **PR #7** = **PR #6** (`97a7a89`) + commit `4f439fc`. No tocar instalación original.
