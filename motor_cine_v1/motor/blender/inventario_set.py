"""inventario_set (Blender 5.2.3) — motor unificado v1 [9/10-nov-2026].
Lee el MOLDE DE ESCENARIO publicado por la fábrica (no crea nada) y mide:
  - caminables (piso/tapete) con su altura z, paredes, techo y obstáculos (huella xy + alto) para el planificador A*+RVO2;
  - piezas_vivas declaradas por la fábrica (custom property 'vivo' o meta.json del escenario) — solo se listan.
Uso: blender -b escenario.blend -P inventario_set.py -- --salida inv.json"""
import bpy, json, sys, math
from mathutils import Vector

CAMINABLE = ('piso', 'suelo', 'floor', 'tapete', 'alfombra', 'rug', 'carpet', 'cesped', 'pasto', 'grass', 'terreno', 'ground')
PARED = ('pared', 'muro', 'wall', 'zocalo', 'rodapie')
TECHO = ('techo', 'ceiling', 'cielo_raso', 'plafon')
IGNORAR = ('luz', 'light', 'cam_', 'camara', 'camera', 'cielo_', 'sky', 'fondo_lejano', 'vidrio', 'glass', 'cortina', 'interruptor', 'flecha_', 'marca_')

def bbox_mundo(o):
    pts = [o.matrix_world @ Vector(c) for c in o.bound_box]
    xs = [p.x for p in pts]; ys = [p.y for p in pts]; zs = [p.z for p in pts]
    return [min(xs), min(ys), min(zs)], [max(xs), max(ys), max(zs)]

def clasificar(o, lo, hi):
    n = o.name.lower()
    alto = hi[2] - lo[2]; ax = hi[0] - lo[0]; ay = hi[1] - lo[1]
    if any(k in n for k in IGNORAR): return 'ignorar'
    if any(k in n for k in TECHO) or (lo[2] > 2.2 and alto < 0.4 and ax * ay > 4): return 'techo'
    if any(k in n for k in CAMINABLE) and hi[2] < 0.12: return 'caminable'
    if hi[2] < 0.035 and ax * ay > 0.2: return 'caminable'
    if any(k in n for k in PARED) or (alto > 1.6 and min(ax, ay) < 0.35 and max(ax, ay) > 1.0): return 'pared'
    return 'obstaculo'

def main():
    argv = sys.argv[sys.argv.index('--') + 1:]
    salida = argv[argv.index('--salida') + 1]
    R = {"contrato": "inventario_set_v1", "blender": bpy.app.version_string, "archivo": bpy.data.filepath,
         "caminables": [], "paredes": [], "techos": [], "obstaculos": [], "ignorados": [], "piezas_vivas": [], "camaras_molde": []}
    lo_all = [1e9, 1e9, 1e9]; hi_all = [-1e9, -1e9, -1e9]
    for o in bpy.data.objects:
        if o.type == 'CAMERA': R["camaras_molde"].append(o.name); continue
        if o.type != 'MESH': continue
        if o.get('vivo'):
            try: R["piezas_vivas"].append(dict({"objeto": o.name}, **json.loads(o['vivo'])))
            except Exception: R["piezas_vivas"].append({"objeto": o.name, "raw": str(o['vivo'])})
        lo, hi = bbox_mundo(o)
        c = clasificar(o, lo, hi)
        item = {"id": o.name, "min": [round(x, 4) for x in lo], "max": [round(x, 4) for x in hi], "bbox_xy": [[round(lo[0], 4), round(lo[1], 4)], [round(hi[0], 4), round(hi[1], 4)]]}
        {'caminable': R["caminables"], 'pared': R["paredes"], 'techo': R["techos"], 'obstaculo': R["obstaculos"], 'ignorar': R["ignorados"]}[c].append(item)
        if c == 'caminable':
            for i in range(3): lo_all[i] = min(lo_all[i], lo[i]); hi_all[i] = max(hi_all[i], hi[i])
    if lo_all[0] > 1e8:                                    # sin piso con nombre: límites = interior de las paredes
        for x in R["paredes"]:
            for i in range(3): lo_all[i] = min(lo_all[i], x["min"][i]); hi_all[i] = max(hi_all[i], x["max"][i])
    # los obstáculos que flotan alto (repisas >1.5 m, lámparas de techo) no estorban al caminar
    R["obstaculos_piso"] = [x for x in R["obstaculos"] + R["paredes"] if x["min"][2] < 1.3]
    R["limites_xy"] = [[round(lo_all[0], 3), round(lo_all[1], 3)], [round(hi_all[0], 3), round(hi_all[1], 3)]]
    R["piso_z_mediana"] = sorted([x["max"][2] for x in R["caminables"]])[len(R["caminables"]) // 2] if R["caminables"] else None
    json.dump(R, open(salida, 'w'), indent=1, ensure_ascii=False)
    print("RESULT_INV", json.dumps({k: (len(v) if isinstance(v, list) else v) for k, v in R.items()}, ensure_ascii=False))

if __name__ == "__main__":
    main()
