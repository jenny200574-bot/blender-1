# -*- coding: utf-8 -*-
"""[constructores_v1_20261109 · 10-nov-2026] Saca UN objeto (obj-…) de un escenario YA ensamblado (ensamblado_<modo>.json:
forma Star o receta Argon vía B aprobada) y lo deja solo, centrado en x/y y apoyado en z = 0, para construir su molde
propio. Sin IA, US$0. Uso: python3 extraer_objeto.py --ensamblado E.json --objeto obj-x --salida piezas.json"""
import argparse, json
ap = argparse.ArgumentParser(); ap.add_argument('--ensamblado'); ap.add_argument('--objeto', required=True); ap.add_argument('--salida', required=True)
ap.add_argument('--receta', help='recetas_validas.json (Argon vía B aprobada): se arma desde la receta, sin escenario')
a = ap.parse_args()
if a.receta:
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'escenario' / 'codigo'))
    import formas_detalle as FD
    rec = json.load(open(a.receta, encoding='utf-8'))[a.objeto]
    T = FD.transformador([0, 0], 0, 0); pz = []
    for q in rec['partes']: pz += FD.parte_a_piezas(q, T)
    for q in pz:
        c = q.get('color') or q.get('color_guia_rgb')
        if isinstance(c, str) and c.startswith('#'): c = [int(c[i:i + 2], 16) / 255 for i in (1, 3, 5)]
        q['color'] = c or [0.7, 0.7, 0.7]
    it = {'id': a.objeto, 'forma': 'receta Argon vía B (aprobada)', 'receta': a.receta, 'piezas': pz}
else:
    E = json.load(open(a.ensamblado, encoding='utf-8'))
    its = [o for o in E['objetos'] if o['id'].split('#')[0] == a.objeto]
    if not its: raise SystemExit(f'FALTA: {a.objeto} no está en {a.ensamblado}')
    it = its[0]; pz = it['piezas']
def pts(p):
    out = []
    for k in ('c', 'a', 'b'):
        if k in p: out.append(p[k])
    out += p.get('v') or []
    return out
P = [q for p in pz for q in pts(p)]
mn = [min(q[i] for q in P) for i in range(3)]; mx = [max(q[i] for q in P) for i in range(3)]
cx, cy = (mn[0] + mx[0]) / 2, (mn[1] + mx[1]) / 2
# z mínimo real: centro − medio tamaño (cajas) o − radio (cil/esf) — aproximado; Blender mide después y se re-apoya
zmin = min([p['c'][2] - max(p['s']) / 2 for p in pz if p['t'] == 'caja'] + [min(p['a'][2], p['b'][2]) - p.get('r', 0) for p in pz if p['t'] == 'cil']
           + [p['c'][2] - p['r'] for p in pz if p['t'] == 'esf'] + [q[2] for p in pz if p['t'] == 'pol' for q in p['v']] + [mn[2]])
def mover(v): return [v[0] - cx, v[1] - cy, v[2] - zmin]
for p in pz:
    for k in ('c', 'a', 'b'):
        if k in p: p[k] = mover(p[k])
    if 'v' in p: p['v'] = [mover(q) for q in p['v']]
falta = any(p.get('falta') for p in pz)
r = {'objeto': a.objeto, 'instancia': it['id'], 'origen_ensamblado': a.ensamblado, 'info': {k: v for k, v in it.items() if k != 'piezas'},
     'n_piezas': len(pz), 'falta': falta, 'piezas': pz}
json.dump(r, open(a.salida, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print(json.dumps({'objeto': a.objeto, 'n_piezas': len(pz), 'falta': falta}))
