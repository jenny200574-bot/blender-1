# constructores_v1_20261109 — fábricas 3D conectadas (OK Ricardo pt993u/pt994u, 9-nov-2026)
Copia versionada y generalizada de los constructores prototipo del 9-nov (restaurado/prototipo_esqueletos y fabricas/escenario).
Sin rutas del box, sin habitación fija: canal, id y escenario van por argumento. Lo usa /opt/myia-fabricas/app/workers_v2_3d.py.
- prototipo_esqueletos/: constructor_blender.py (+ --blend), validador.py, esquema/, medir_altura.py (nuevo), hacer_hoja.py (genérico).
- personajes/generar_ficha_humana.py (nuevo): ficha bipedo_humano desde el ADN sellado (altura m, cabezas, colores, ropa, pelo).
  Con el ADN de Valentina reproduce la ficha manual del 9-nov: 20 huesos, 24 piezas, 8 colores (geometría idéntica).
- escenario/codigo/: plan_escenario.py (--escenario --inv --e4a2 --datos [--mapa]), ensamblar.py (--datos --escenario),
  construir_render.py (-- modo --datos --escenario --salida), formas_detalle.py, biblioteca_formas/ (283 formas Star), hoja_escenario.py.
  escenario/mapas/esc-habitacion.json = decisiones por objeto que antes estaban en el código (datos revisados).
  Con la habitación, plan y ensamblado salen idénticos al prototipo. _legado_habitacion/ = hojas viejas, no se usan.
- escenario/via_b/revisor_recetas.py + verificador_citas.py + esquemas/; objetos/escalar.py.
- pod/run_personaje_pod.sh y pod/run_escenario_pod.sh: corren EN el pod RunPod (los sube el servicio). Nadie los corre a mano.
