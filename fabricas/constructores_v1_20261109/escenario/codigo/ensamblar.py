# -*- coding: utf-8 -*-
"""[constructores_v1_20261109 · genérico] Uso: python3 ensamblar.py --datos DIR --escenario ID [star|cajas|star_recetas ...]
(antes fijo a esc-habitacion y a ../datos). Lógica de ensamblado y validación SIN cambios.
Ensambla un escenario SIN Blender (Python puro, US$0): piezas absolutas por objeto en dos modos
('star' = biblioteca de 283 formas; 'cajas' = molde de cajas, como hoy 4a2) + validación de apoyo y colisiones.
Salida: datos/ensamblado_<modo>.json  (lo dibuja construir_render.py)  y datos/validacion_<modo>.json."""
import json, math, sys
from pathlib import Path
AQUI = Path(__file__).resolve().parent
sys.path[:0] = [str(AQUI), str(AQUI / 'biblioteca_formas')]
import formas_detalle as FD
import formas_biblioteca as FB

def _arg(k, d=None):
    return sys.argv[sys.argv.index(k) + 1] if k in sys.argv else d
DATOS = Path(_arg('--datos', str(AQUI.parent / 'datos')))
ESC = _arg('--escenario')
if not ESC: raise SystemExit('falta --escenario <id>')
MODOS = [a for i, a in enumerate(sys.argv[1:], 1) if not a.startswith('--') and sys.argv[i - 1] not in ('--datos', '--escenario')]
PLAN = json.loads((DATOS / f'plan_{ESC}.json').read_text(encoding='utf-8'))
W, D, H = PLAN['medidas']['ancho_m'], PLAN['medidas']['fondo_m'], PLAN['medidas']['alto_m']
TOL_APOYO = 0.08     # hasta 8 cm de diferencia se corrige al apoyo real (y se informa)
TOL_CHOQUE = 0.015   # penetración mínima para contar choque (1,5 cm por eje)

def rgb(hx):
    hx = hx.lstrip('#'); return [int(hx[i:i + 2], 16) / 255 for i in (0, 2, 4)]

def piezas_de(fid, w, d, h, vueltas=8):
    """Igual que construir_biblioteca: ajusta la forma a la caja pedida (error ≤ 2 mm) y la apoya en z=0."""
    def crudo(a0, a1, a2):
        T = FD.transformador([0, 0], 0, 0); out = []
        for p in FB.G[fid](a0, a1, a2):
            out += [p['pieza']] if p.get('tipo') == '_pieza_interna' else FD.parte_a_piezas(p, T)
        return out
    a = [w, d, h]; mejor = None
    for _ in range(vueltas):
        pz = crudo(*a); mn, mx = FD.bbox(pz); bb = [mx[i] - mn[i] for i in range(3)]
        err = max(abs(bb[0] - w), abs(bb[1] - d), abs(bb[2] - h))
        if mejor is None or err < mejor[0]: mejor = (err, pz)
        if err <= 0.002: break
        a = [max(1e-3, a[i] * (t / bb[i] if bb[i] > 1e-6 else 1.0)) for i, t in enumerate((w, d, h))]
    mn, _ = FD.bbox(mejor[1])
    return FD.desplazar(mejor[1], [0, 0, -mn[2]]), round(mejor[0], 4)

def caja_local(w, d, h, nombre='caja'):
    return [dict(t='caja', nombre=nombre, c=[0, 0, h / 2], s=[w, d, h], R=[[1, 0, 0], [0, 1, 0], [0, 0, 1]], color=None)]

def a_mundo(pz, x, y, z, rot):
    R = FD.rz(math.radians(rot)); out = []
    for p in pz:
        q = FD.mover_pieza(p, R, [0, 0, 0], [x, y, z]); out.append(q)
    return out

def dims_locales(it):
    """Utilería y elementos 4a1: ancho/fondo en ejes del CUARTO (x, y). Objetos de historia (4a2 objetos_tamano): del objeto."""
    if it['fuente'].startswith('4a1.objetos'):
        return it['w'], it['d'], it['h']
    s = abs(math.sin(math.radians(it['rot_star'])))
    return (it['d'], it['w'], it['h']) if s > 0.7071 else (it['w'], it['d'], it['h'])

def pintar(pz, colores):
    for p in pz:
        n = (p.get('nombre') or '').lower()
        hx = next((v for k, v in colores.items() if k != '*' and k in n), colores['*'])
        p['color'] = rgb(hx)
    return pz

RECETAS_ARCHIVO = DATOS / 'recetas_validas.json'   # recetas de Argon que pasaron revisor_recetas.py (vía B)
def _recetas():
    return json.loads(RECETAS_ARCHIVO.read_text(encoding='utf-8')) if RECETAS_ARCHIVO.exists() else {}

def construir_objeto(it, modo):
    w, d, h = dims_locales(it)
    rec = _recetas().get(it.get('oid') or it['id']) if modo == 'star_recetas' and not it.get('fid') else None
    if rec is not None:
        T = FD.transformador([0, 0], 0, 0); pz = []
        for p in rec['partes']:
            pz += FD.parte_a_piezas(p, T)
        info = {'id': it['id'], 'fid': None, 'aprox': False, 'dims_local_m': [w, d, h], 'forma': 'receta Argon (vía B)', 'receta': True}
        return a_mundo(pz, it['x'], it['y'], it['z'], it['rot_star']), info
    w, d, h = max(w, 0.01), max(d, 0.003), max(h, 0.003)
    info = {'id': it['id'], 'fid': it.get('fid'), 'aprox': bool(it.get('aprox')), 'dims_local_m': [w, d, h]}
    if modo == 'cajas' or not it.get('fid'):
        pz = caja_local(w, d, h, 'caja'); info['forma'] = 'caja' + ('' if modo == 'cajas' else ' (FALTA en Star)')
        pintar(pz, {'*': it['colores']['*']})
        if modo in ('star', 'star_recetas'):
            for p in pz: p['falta'] = True
    elif it.get('pila'):
        pz = []; n = it['pila']; hx = [v for k, v in sorted(it['colores'].items())] or ['#888888']
        cols = [c for c in (it.get('color_hex_lista') or [])] or None
        from plan_escenario import hexes
        hl = hexes(it.get('color_txt')) or [it['colores']['*']]
        for k in range(n):
            b, err = piezas_de(it['fid'], w * (1 - 0.08 * k), d * (1 - 0.06 * k), h / n)
            pintar(b, {'*': hl[k % len(hl)], 'hojas': '#F5E6D3'})
            pz += FD.desplazar(b, [0.0, 0.0, k * h / n])
        info['forma'] = f'pila de {n} × {it["fid"]}'
    elif it.get('par'):
        pz = []
        for k, dx in enumerate((-w / 4 - 0.02, w / 4 + 0.02)):
            b, err = piezas_de(it['fid'], w / 2 - 0.04, d, h)
            pintar(b, it['colores']); pz += FD.desplazar(b, [dx, 0.0, 0.0])
        info['forma'] = f'par de {it["fid"]}'
    else:
        pz, err = piezas_de(it['fid'], w, d, h); info['error_ajuste_m'] = err
        quitar = set(it.get('quitar_piezas') or [])
        pz = [p for p in pz if (p.get('nombre') or '') not in quitar]
        pintar(pz, it['colores']); info['forma'] = it['fid'] + (' (aprox)' if it.get('aprox') else '')
    return a_mundo(pz, it['x'], it['y'], it['z'], it['rot_star']), info

def bb(pz):
    return FD.bbox(pz)

def solapa_xy(c, mn, mx, m=0.0):
    return mn[0] - m <= c[0] <= mx[0] + m and mn[1] - m <= c[1] <= mx[1] + m

def ensamblar(modo):
    objs, avisos, problemas, correcciones, sostenidos = [], [], [], [], []
    orden = sorted(PLAN['objetos'], key=lambda i: (i['z'] > 0.03, i['z']))
    hechos = []
    for it in orden:
        if it.get('estructura'):
            continue
        if it['apoyo'] == 'sostenido':
            sostenidos.append({'id': it['id'], 'z_m': it['z'], 'escenas': it.get('escenas'),
                               'motivo': 'lo lleva un personaje o vuela por magia (4a1 junto_a): no es mueble del set',
                               'junto_a_4a1': it.get('junto_a')})
            continue
        pz, info = construir_objeto(it, modo)
        if info.get('error_ajuste_m', 0) > 0.01:
            problemas.append({'tipo': 'forma_no_ajusta', 'id': it['id'], 'error_m': info['error_ajuste_m']})
        mn, mx = bb(pz)
        if it['apoyo'] == 'sobre_otro' and modo == 'cajas':
            # molde: se dibuja tal cual; solo se informa si flota o queda enterrado en la caja de abajo
            c = [(mn[0] + mx[0]) / 2, (mn[1] + mx[1]) / 2]
            dentro = [o['id'] for o in hechos if solapa_xy(c, *bb(o['piezas'])) and bb(o['piezas'])[0][2] < mn[2] < bb(o['piezas'])[1][2] - 0.01]
            tops = [bb(o['piezas'])[1][2] for o in hechos if solapa_xy(c, *bb(o['piezas'])) and bb(o['piezas'])[1][2] <= mn[2] + 0.01]
            if dentro: problemas.append({'tipo': 'enterrado_en_caja', 'id': it['id'], 'dentro_de': dentro})
            elif not tops or mn[2] - max(tops) > 0.01: problemas.append({'tipo': 'flota', 'id': it['id'], 'z_m': round(mn[2], 3)})
            info['apoya_en'] = 'molde (sin corregir)'
        elif it['apoyo'] == 'montado_frente':
            c = [(mn[0] + mx[0]) / 2, mx[1]]
            ok = [o['id'] for o in hechos if solapa_xy(c, *bb(o['piezas']), m=0.03) and bb(o['piezas'])[0][2] <= mn[2] <= bb(o['piezas'])[1][2]]
            if not ok: problemas.append({'tipo': 'montaje_sin_soporte', 'id': it['id']})
            info['apoya_en'] = 'frente de ' + (ok[0] if ok else '?')
        elif it['apoyo'] == 'sobre_otro':
            c = [(mn[0] + mx[0]) / 2, (mn[1] + mx[1]) / 2]
            tops = []
            for o in hechos:
                for p in o['piezas']:
                    pmn, pmx = FD.bbox_pieza(p)
                    if solapa_xy(c, pmn, pmx) and pmx[2] <= mn[2] + TOL_APOYO + 1e-6:
                        tops.append((pmx[2], o['id'], p.get('nombre')))
            # alfombra (suelo de la sala) también es apoyo
            if (c[0] - W / 2) ** 2 + (c[1] - D / 2) ** 2 <= 1.1 ** 2:
                tops.append((0.02, 'alfombra', 'alfombra'))
            tops.append((0.0, 'piso', 'piso'))
            top = max(tops) if tops else None
            if top is not None and abs(top[0] - mn[2]) <= TOL_APOYO:
                dz = top[0] - mn[2]
                if abs(dz) > 0.002:
                    pz = FD.desplazar(pz, [0, 0, dz]); mn, mx = bb(pz)
                    correcciones.append({'id': it['id'], 'dz_m': round(dz, 3), 'apoya_en': f'{top[1]}:{top[2]}'})
                info['apoya_en'] = f'{top[1]}:{top[2]}'
            else:
                problemas.append({'tipo': 'sin_apoyo', 'id': it['id'], 'z_m': round(mn[2], 3), 'apoyo_cercano': top})
        elif it['apoyo'] == 'piso':
            if abs(mn[2]) > 0.01 and not (abs(mn[2] - 0.02) < 0.01):
                problemas.append({'tipo': 'no_toca_piso', 'id': it['id'], 'zmin': round(mn[2], 3)})
            info['apoya_en'] = 'piso'
        elif it['apoyo'] == 'pared':
            dist = min(abs(mn[0]), abs(W - mx[0]), abs(mn[1]), abs(D - mx[1]))
            if dist > 0.05:
                problemas.append({'tipo': 'lejos_de_pared', 'id': it['id'], 'distancia_m': round(dist, 3)})
            info['apoya_en'] = 'pared'
        elif it['apoyo'] == 'techo':
            if abs(mx[2] - H) > 0.02:
                problemas.append({'tipo': 'no_cuelga_del_techo', 'id': it['id'], 'zmax': round(mx[2], 3)})
            info['apoya_en'] = 'techo'
        # dentro del cuarto (aberturas pueden meterse en el muro)
        if not it['id'].startswith(('Ventana', 'Puerta')):
            fuera = [round(v, 3) for v in (-mn[0], mx[0] - W, -mn[1], mx[1] - D, mx[2] - H) if v > 0.01]
            if fuera:
                problemas.append({'tipo': 'atraviesa_muro_o_techo', 'id': it['id'], 'exceso_m': max(fuera)})
        info.update(bbox_min=[round(v, 3) for v in mn], bbox_max=[round(v, 3) for v in mx], piezas=len(pz), apoyo=it['apoyo'])
        o = {'id': it['id'], 'piezas': pz, 'info': info, 'apoyo': it['apoyo'], 'escenas': it.get('escenas')}
        objs.append(o); hechos.append(o)
    # colisiones entre objetos (cajas límite de pieza; apoyo-padre e hijos sobre él se permiten en contacto)
    choques = []
    for i in range(len(objs)):
        for j in range(i + 1, len(objs)):
            a, b = objs[i], objs[j]
            amn, amx = bb(a['piezas']); bmn, bmx = bb(b['piezas'])
            if any(amx[k] < bmn[k] + TOL_CHOQUE or bmx[k] < amn[k] + TOL_CHOQUE for k in range(3)):
                continue
            peor = 0.0; par = None
            for p in a['piezas']:
                pmn, pmx = FD.bbox_pieza(p)
                for q in b['piezas']:
                    qmn, qmx = FD.bbox_pieza(q)
                    pen = min(min(pmx[k], qmx[k]) - max(pmn[k], qmn[k]) for k in range(3))
                    if pen > peor: peor, par = pen, (p.get('nombre'), q.get('nombre'))
            ea, eb = set(a.get('escenas') or []), set(b.get('escenas') or [])
            if ea and eb and not (ea & eb):
                continue  # nunca están a la vez en cámara
            if peor > TOL_CHOQUE:
                apoyo = (a['info'].get('apoya_en', '').startswith(b['id'] + ':') or b['info'].get('apoya_en', '').startswith(a['id'] + ':'))
                choques.append({'a': a['id'], 'b': b['id'], 'penetracion_m': round(peor, 3), 'piezas': par, 'es_apoyo': apoyo})
    reales = [c for c in choques if not c['es_apoyo']]
    for c in reales:
        problemas.append(dict(tipo='choque', **c))
    res = {'modo': modo, 'objetos': len(objs), 'sostenidos_no_dibujados': sostenidos, 'correcciones_apoyo': correcciones,
           'problemas': problemas, 'choques_de_apoyo_permitidos': [c for c in choques if c['es_apoyo']],
           'info': [o['info'] for o in objs]}
    (DATOS / f'ensamblado_{modo}.json').write_text(json.dumps({'objetos': [{'id': o['id'], 'piezas': o['piezas']} for o in objs]}), encoding='utf-8')
    (DATOS / f'validacion_{modo}.json').write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding='utf-8')
    return res

if __name__ == '__main__':
    for m in (MODOS or ['star', 'cajas']):
        r = ensamblar(m)
        print(m, 'objetos', r['objetos'], 'sostenidos', len(r['sostenidos_no_dibujados']), 'correcciones', len(r['correcciones_apoyo']),
              'problemas', len(r['problemas']))
        for p in r['problemas']: print('   ', p)
        for c in r['correcciones_apoyo']: print('   corr', c)
        for s in r['sostenidos_no_dibujados']: print('   sost', s['id'], s['z_m'])
