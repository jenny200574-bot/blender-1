# -*- coding: utf-8 -*-
"""[constructores_v1_20261109 · genérico] Plan de un escenario (sin Blender, sin IA, US$0): lee los datos REALES de n8n (4a1 + 4a2)
y decide, por objeto, qué forma de la biblioteca de Star usa (o si FALTA), su caja, posición, giro, apoyo y colores.
Antes: fijo a esc-habitacion y a /workspace/fabricas/datos_n8n. Ahora:
  python3 plan_escenario.py --escenario <id> --inv <inv_4a1.json> --e4a2 <4a2_entrada_blender.json> --datos <DIR> [--mapa mapas/<id>.json]
Decisión por objeto: 1) mapa del escenario si existe (datos revisados); 2) si no, forma Star por nombre (token exacto en las 283 formas);
3) si no hay forma → FALTA (va a receta). Nunca se detiene por un objeto sin decisión: lo marca FALTA y lo informa.
Salida: <DIR>/plan_<id>.json."""
import json, re, hashlib, sys, argparse, unicodedata
from pathlib import Path
AQUI = Path(__file__).resolve().parent
sys.path[:0] = [str(AQUI / 'biblioteca_formas')]
ap = argparse.ArgumentParser(); ap.add_argument('--escenario', required=True); ap.add_argument('--inv', required=True)
ap.add_argument('--e4a2', required=True); ap.add_argument('--datos', required=True); ap.add_argument('--mapa')
if __name__ == '__main__':
    ARGS = ap.parse_args()
else:   # importado (ensamblar.py usa hexes): sin argumentos
    ARGS = argparse.Namespace(escenario='_', inv='', e4a2='', datos='.', mapa=None)
INV = Path(ARGS.inv)
E4A2 = Path(ARGS.e4a2)
OUT = Path(ARGS.datos) / f'plan_{ARGS.escenario}.json'
_MP = Path(ARGS.mapa) if ARGS.mapa else AQUI.parent / 'mapas' / f'{ARGS.escenario}.json'
_M = json.loads(_MP.read_text(encoding='utf-8')) if _MP.is_file() else {'MAPA': {}, 'COLORES_ADN': {}}
HEX = re.compile(r'#([0-9A-Fa-f]{6})')

def hexes(s):
    return ['#' + h.upper() for h in HEX.findall(str(s or ''))]

def rot_star(theta_n8n):
    """n8n: rotacion_grados = hacia dónde mira el FRENTE, 0 = +y, horario (pared izquierda 90 → mira +x).
    Star: frente local −y, giro antihorario rz.  R_ccw(rz)(0,−1) = R_cw(θ)(0,1)  ⇒  rz = 180 − θ."""
    return (180.0 - float(theta_n8n or 0)) % 360.0

MAPA = _M.get('MAPA') or {}
COLORES_ADN = {k: (v['colores'], v['fuente']) for k, v in (_M.get('COLORES_ADN') or {}).items()}
try:
    import formas_biblioteca as _FB
    FORMAS = set(_FB.G)
except Exception:
    FORMAS = set()
def _tok(s):
    s = unicodedata.normalize('NFD', str(s).lower()); s = ''.join(c for c in s if unicodedata.category(c) != 'Mn')
    return [t for t in re.split(r'[^a-z0-9]+', s) if t]
def decidir(key, it):
    """Mapa revisado → forma Star por nombre → FALTA. Devuelve dict de decisión (como el MAPA)."""
    if key in MAPA: return dict(MAPA[key], decision='mapa')
    nombre = ' '.join(str(x) for x in (key, it.get('nombre') or '') if x)
    if re.search(r'z[oó]calo', nombre, re.I): return dict(estructura=True, decision='auto_estructura')
    tk = _tok(nombre)
    for n in (3, 2, 1):
        for i in range(len(tk) - n + 1):
            f = '_'.join(tk[i:i + n])
            if f in FORMAS: return dict(fid=f, aprox=False, decision=f'auto_nombre:{f}')
    for t in tk:
        for f in sorted(FORMAS):
            if f.split('_')[0] == t and len(t) > 3: return dict(fid=f, aprox=True, decision=f'auto_raiz:{f}')
    return dict(fid=None, decision='auto_falta')

def colores_de(oid, color_txt):
    if oid in COLORES_ADN:
        return COLORES_ADN[oid]
    h = hexes(color_txt)
    if not h:
        return ({'*': '#B0B0B0'}, 'sin color en datos')
    c = {'*': h[0]}
    if len(h) > 1:
        for k in ('cobija', 'asiento', 'tablero', 'cajon', 'puerta', 'interior', 'fondo', 'lienzo', 'follaje', 'ala', 'guarda', 'tapa'):
            c[k] = h[1]
    return (c, f'4a1 color: {color_txt}')

def main():
    inv = json.loads(INV.read_text(encoding='utf-8'))
    e4 = json.loads(E4A2.read_text(encoding='utf-8'))
    # datos REALES de n8n tal cual: inv_escenarios[__id].json trae {'escenarios': [...]} y 4a2 es una lista → se elige este escenario
    if isinstance(inv, dict) and 'escenarios' in inv and 'elementos_blender' not in inv:
        inv = next((e for e in inv['escenarios'] if (e.get('escenario_id') or e.get('id')) == ARGS.escenario), None)
        if inv is None: raise SystemExit(f'FALTA: {ARGS.escenario} no está en {INV}')
    if isinstance(e4, list):
        e4 = next((e for e in e4 if e.get('id') == ARGS.escenario), None)
        if e4 is None: raise SystemExit(f'FALTA: {ARGS.escenario} no está en {E4A2}')
    tam = e4['objetos_tamano']
    items = []
    for e in inv['elementos_blender']:
        n = e['nombre']
        if re.match(r'^(Piso|Centro|Suelo)\b', n):
            continue
        apoyo = 'pared' if re.match(r'^(Ventana|Puerta|Cuadro|Repisa)', n) else 'piso'
        items.append(dict(id=n, fuente='4a1.elementos_blender', x=e['x_m'], y=e['y_m'], z=e['z_m'], w=e['ancho_m'], d=e['fondo_m'],
                          h=e['alto_m'], rot_n8n=e['rotacion_grados'], apoyo=apoyo, material=e.get('material'), color_txt=e.get('material')))
    cuenta = {}
    for o in inv['objetos_del_lugar_posicion']:
        oid = o['objeto_id']; cuenta[oid] = cuenta.get(oid, 0) + 1
        t = (tam.get(oid) or {}).get('tamano')
        if not t:
            print(f'AVISO sin tamaño 4a2 para {oid}: se omite (no se inventa medida)'); continue
        items.append(dict(id=f'{oid}#{cuenta[oid]}', oid=oid, fuente='4a1.objetos_del_lugar_posicion + 4a2.objetos_tamano (4b1/4c1)',
                          escenas=o.get('escenas'), junto_a=o.get('junto_a'), x=o['x_m'], y=o['y_m'], z=o['z_m'],
                          w=t['ancho_cm'] / 100, d=t['fondo_cm'] / 100, h=t['alto_cm'] / 100, rot_n8n=o['rotacion_grados'],
                          apoyo=None, color_txt=None, justificacion=o.get('justificacion')))
    for u in (inv.get('ambiente_vivo') or {}).get('utileria_ambiente') or []:
        items.append(dict(id=u['ambiente_id'], fuente='4a1.ambiente_vivo.utileria_ambiente', nombre=u['nombre'], x=u['x_m'], y=u['y_m'],
                          z=u['z_m'], w=u['ancho_m'], d=u['fondo_m'], h=u['alto_m'], rot_n8n=u['rotacion_grados'], apoyo=u['apoyo'],
                          pared=u.get('pared'), material=u.get('material'), color_txt=u.get('color')))
    for it in items:
        key =[REDACTED]
        m = decidir(key, it)
        it.update({k: v for k, v in m.items()})
        it['rot_star'] = rot_star(it['rot_n8n'])
        it['colores'], it['colores_fuente'] = colores_de(key, it.get('color_txt'))
        # apoyo de objetos de historia (4a1 no lo trae): por altura
        if it.get('apoyo') is None:
            j = (it.get('justificacion') or '') + ' ' + (it.get('junto_a') or '')
            if re.search(r'\b(Sostenid|Llevad|Levantad|Volando)', j): it['apoyo'] = 'sostenido'
            elif 'en el frente de' in j: it['apoyo'] = 'montado_frente'
            elif it['z'] <= 0.03: it['apoyo'] = 'piso'
            elif re.search(r'l[aá]mpara|colgante|candelabro', key + ' ' + str(it.get('nombre') or ''), re.I) and it['z'] > 1.5: it['apoyo'] = 'techo'
            else: it['apoyo'] = 'sobre_otro'
    plan = {'escenario_id': inv['escenario_id'], 'int_ext': e4.get('int_ext') or inv.get('int_ext'), 'tipo_lugar': inv.get('tipo_lugar'), 'medidas': inv['medidas'], 'aberturas': inv['aberturas'],
            'materiales': inv['materiales_texturas'], 'luz_escena1': (inv.get('luz_por_escena') or [None])[0],
            'fuentes_sha256': {str(INV): hashlib.sha256(INV.read_bytes()).hexdigest(), str(E4A2): hashlib.sha256(E4A2.read_bytes()).hexdigest()},
            'objetos': items, 'mapa': str(_MP) if _MP.is_file() else None,
            'decisiones': {d: sum(1 for i in items if (i.get('decision') or '').startswith(d)) for d in ('mapa', 'auto_nombre', 'auto_raiz', 'auto_falta', 'auto_estructura')}}
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(plan, ensure_ascii=False, indent=1), encoding='utf-8')
    star = [i for i in items if i.get('fid')]; falt = [i for i in items if not i.get('fid') and not i.get('estructura')]
    print(f'objetos {len(items)}: Star {len(star)} (aprox {sum(1 for i in star if i.get("aprox"))}), faltan {len(falt)}, estructura {sum(1 for i in items if i.get("estructura"))}')

if __name__ == '__main__':
    main()
