# -*- coding: utf-8 -*-
"""Blender: renderiza cada receta válida SOLA (vista 3/4 desde el frente −y), 512×512, para la hoja de recetas.
Uso: blender -b --factory-startup -P render_recetas.py"""
import bpy, json, math, sys
from mathutils import Vector
from pathlib import Path
B = Path(__file__).resolve().parents[1]; sys.path[:0] = [str(B / 'codigo')]
import formas_detalle as FD
REC = json.loads((B / 'datos/recetas_validas.json').read_text(encoding='utf-8'))
OUT = B / 'renders/recetas'; OUT.mkdir(parents=True, exist_ok=True)
exec(open(B / 'codigo/construir_render.py', encoding='utf-8').read().split('# ---------------- cuarto ----------------')[0]
     .replace("ENS = json.loads((BASE / f'datos/ensamblado_{MODO}.json').read_text(encoding='utf-8'))", "ENS = None"))
for oid, r in REC.items():
    bpy.ops.wm.read_factory_settings(use_empty=True); sc = bpy.context.scene; MATS.clear()
    globals()['sc'] = sc
    T = FD.transformador([0, 0], 0, 0); pz = []
    for p in r['partes']: pz += FD.parte_a_piezas(p, T)
    for k, p in enumerate(pz): pieza(p, f'p{k}')
    w, d, h = r['caja_m']['ancho'], r['caja_m']['fondo'], r['caja_m']['alto']; L = max(w, d, h)
    pintar(caja('suelo', (0, 0, -0.005), (L * 6, L * 6, 0.01)), [0.85, 0.85, 0.83])
    for n, e, loc in [('k', 220 * L * L, (-1.5 * L, -2 * L, 2.5 * L)), ('f', 90 * L * L, (2 * L, -1 * L, 1.5 * L))]:
        Ld = bpy.data.lights.new(n, 'AREA'); Ld.energy = max(e, 5); Ld.size = L * 1.5
        o = bpy.data.objects.new(n, Ld); sc.collection.objects.link(o); o.location = loc
        o.rotation_euler = (Vector((0, 0, h / 2)) - Vector(loc)).to_track_quat('-Z', 'Y').to_euler()
    wd = bpy.data.worlds.new('w'); sc.world = wd; wd.use_nodes = True; wd.node_tree.nodes['Background'].inputs[1].default_value = 0.25
    c = bpy.data.cameras.new('c'); c.lens = 50; o = bpy.data.objects.new('c', c); sc.collection.objects.link(o)
    dist = L * 2.3; o.location = (dist * 0.55, -dist * 0.8, h / 2 + dist * 0.45)
    o.rotation_euler = (Vector((0, 0, h / 2)) - o.location).to_track_quat('-Z', 'Y').to_euler(); c.clip_start = L * 0.01
    sc.camera = o; eng = [i.identifier for i in sc.render.bl_rna.properties['engine'].enum_items]
    sc.render.engine = 'BLENDER_EEVEE_NEXT' if 'BLENDER_EEVEE_NEXT' in eng else 'BLENDER_EEVEE'
    sc.render.resolution_x = sc.render.resolution_y = 512; sc.view_settings.view_transform = 'AgX'; sc.view_settings.exposure = -0.3
    sc.render.filepath = str(OUT / f'{oid}.png'); bpy.ops.render.render(write_still=True); print('RECETA', oid, flush=True)
