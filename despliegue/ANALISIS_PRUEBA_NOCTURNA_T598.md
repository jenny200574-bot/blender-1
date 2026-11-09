# Análisis t598 (evidencia VPS, modo directa PR7)

## Mediciones

- **Velocidad:** etapa 11 ≈ 211 s / 12 tomas (antes >2 h + timeout toma06) → modo directa SB cumple objetivo de tiempo.
- **Resultado:** pasan 1,2,3,10; bloqueadas 4–9,11,12.
- **Aborto constructor:** `FaltaDatos` por `faltantes` — `ch-pintor-bce0` cabeza solo hueso (`valida_visual: false`). El `escena.blend` sí se guardó.

## Causas por motivo (demostrables)

| Motivo | Causa probable | Tipo |
|--------|----------------|------|
| **sujeto fuera de cuadro (cabeza)** | Mezcla: (1) pose directa SB sin reparación de distancia; (2) si `origen_cabeza=hueso`, región facial es minúscula (3 puntos) vs malla real → `fraccion_en_cuadro` subestimada o encuadre realmente insuficiente. Ver `experimental_directa.diagnostico_encuadre` en `camara_v2.json`. | geometría SB + medición |
| **cabeza solo hueso** | Malla `face`/`head` en ADN pero no visible en evaluación (`hide_render`, sin parent correcto, o no bajo ACT). Arreglo: `bind_role` en objeto Blender + `malla_es_cabeza` unificado (sonda + medir). Si sigue hueso → **entrada/4a2** debe entregar malla visible. | motor / entrada |
| **pegada / dentro escenario** | Holgura: candidato (0°,×1) demasiado cerca de `muro_*`, cortinas, etc. Opcional: `camara_escenario_despeje_por_toma.off` (solo BVH muros) + `camara_retroceso_holgura_directa.off`. **No** despeja `obj-*` (props). | geometría SB |
| **sujeto tapado (obj-cama…)** | Conflicto real escena; no ocultación automática de props. | conflicto escena |
| **cruza eje 180°** | Regla eje bloque + pose directa; sin buscador no hay lado alternativo. `conflicto_sb_probable: true`. | conflicto SB |
| **inclinación / roll** | SB pide 12° etc.; rig directo no cumple. | conflicto SB |

## Próxima prueba VPS

1. Sonda cabeza pintor (frames tomas 4–6):  
   `blender -b SAL/escena.blend -P motor/sonda_inspeccion_camara.py -- --actor ch-pintor-bce0 --frames … --config motor/camara_v2_config.json`
2. Opcional activar en copia: `camara_escenario_despeje_por_toma.off`, `camara_retroceso_holgura_directa.off`
3. Revisar por toma `experimental_directa` y `faltantes` en `camara_v2.json`
