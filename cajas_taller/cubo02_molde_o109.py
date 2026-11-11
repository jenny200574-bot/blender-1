#!/usr/bin/env python3
"""PISTA INMI (2026-10-30): orden 109 — cubo 02 «molde 3D por toma» (GRATIS, sin red, sin ledger). Genérico: cualquier canal, historia y personaje.
Lee la salida del cubo 01 o109 (cubos/01/esc_N.json: posiciones para Blender, cámara del molde y «palabras» por toma, parametros_3d) y arma,
DENTRO del molde.blend del escenario, cada toma: personajes VRM armados por parámetros (o105–o108; sin parámetros → figura gris a su
altura), posados en su posición y giro del segundo medio de la toma, vistos SOLO por la cámara del molde elegida.
Saca por toma: <toma>_gris.png, <toma>_color.png y medidas (lado de la pantalla, frente/espalda, alto en pantalla, lado del accesorio)
y las CRUZA con las palabras del 01 → «coincide» o la lista de diferencias. Sin salida o109 del 01 se PARA (nunca inventa posiciones).
Escribe SOLO en <capítulo>/cubos/02/molde_o109/esc_N/."""
import json, os, subprocess, sys, tempfile, time
from pathlib import Path

AQUI = Path(__file__).resolve().parent
VRM_BASE = os.environ.get('MYIA_VRM_BASE') or str(AQUI / 'biblioteca_vrm' / 'HairSample_Male.vrm')
ADDONS = os.environ.get('MYIA_BLENDER_ADDONS') or '/opt/myia-herramientas/blender_addons'


def cruzar(t, med):
    """Palabras del 01 vs lo que mide Blender. Devuelve lista de diferencias (vacía = coincide)."""
    dif = []; w = t.get('palabras') or {}; pp = {x.get('id'): x for x in w.get('por_personaje') or []}
    for pid, x in pp.items():
        m = (med.get('personajes') or {}).get(pid)
        if not m: dif.append(f'{pid}: el 01 dice que se ve, Blender no lo puso en cuadro'); continue
        if not m.get('en_cuadro'): dif.append(f'{pid}: fuera del cuadro de la cámara del molde')
        if m.get('cuerpo') == 'espalda' and x.get('cuerpo') in ('frente', 'tres_cuartos_frente'): dif.append(f"{pid}: palabras «{x.get('cuerpo')}», Blender lo ve de espalda")
        if m.get('cuerpo') == 'frente' and x.get('cuerpo') in ('espalda', 'tres_cuartos_espalda'): dif.append(f"{pid}: palabras «{x.get('cuerpo')}», Blender lo ve de frente")
        if {m.get('lado_pantalla'), x.get('lado_pantalla')} == {'izquierda', 'derecha'}: dif.append(f"{pid}: palabras lado «{x.get('lado_pantalla')}», Blender lo ve a la {m.get('lado_pantalla')}")
    return dif


def cubo02(K, D, a):
    import cubo01_o109 as C1
    filas, faltan = [], []
    b = K.blender()
    if not b: return K.r_base('02', D, {'ok': False, 'version': 'o109', 'error': 'no hay Blender en este equipo'})
    for e in K.escenas(D, a.solo):
        n = e['numero']; C = K.leer(D / 'cubos' / '01' / f'esc_{n}.json')
        if not (isinstance(C, dict) and C.get('version_01') == 'o109'):
            faltan.append(f'escena {n}: sin dirección o109 del cubo 01 (no se inventa nada)'); continue
        blend = D / 'ramas' / 'moldes' / str(C.get('escenario_id') or e['escenario_id']) / 'molde.blend'
        if not blend.is_file(): faltan.append(f'escena {n}: el escenario no tiene molde.blend'); continue
        pers = [{'id': p['id'], 'altura': p.get('altura'), 'controles': ((C.get('parametros_3d') or {}).get(p['id']) or {}).get('controles') or {}} for p in C['personajes']]
        tomas = []
        for t in C.get('tomas_plan') or []:
            if not t.get('camara_molde') or not t.get('t') or None in t['t']: continue
            tm = (float(t['t'][0]) + float(t['t'][1])) / 2; est = {}
            for p in C['personajes']:
                pos, rot = C1.estado_en(K, C, p, tm)
                if pos is not None: est[p['id']] = {'pos': pos, 'rot': rot or 0}
            tomas.append({'id': t['id'], 'camara_molde': t['camara_molde'], 'segundo': tm, 'estados': est, 'en_cuadro': (t.get('palabras') or {}).get('en_cuadro') or []})
        if a.tomas: tomas = tomas[:a.tomas]
        S = D / 'cubos' / '02' / 'molde_o109' / f'esc_{n}'; S.mkdir(parents=True, exist_ok=True)
        ent = {'personajes': pers, 'tomas': tomas, 'salida_dir': str(S), 'vrm_base': VRM_BASE, 'addons_dir': ADDONS,
               'res': [960, 540] if (C.get('aspecto') or [16, 9])[0] >= (C.get('aspecto') or [16, 9])[1] else [540, 960]}
        fe, fs = S / 'entrada.json', S / 'medidas.json'; fe.write_text(json.dumps(ent, ensure_ascii=False, indent=1), encoding='utf-8')
        if fs.exists(): fs.unlink()
        cmd = ['nice', '-n', '15', b, '-b', str(blend), '--factory-startup', '--python', str(AQUI / 'molde_o109_blender.py'), '--', str(fe), str(fs)]
        try: p = subprocess.run(cmd, capture_output=True, text=True, timeout=int(a.timeout))
        except subprocess.TimeoutExpired: faltan.append(f'escena {n}: Blender tardó demasiado'); continue
        (S / 'blender.log').write_text((p.stdout or '')[-20000:] + '\n--- stderr ---\n' + (p.stderr or '')[-5000:], encoding='utf-8')
        if not fs.is_file(): faltan.append(f'escena {n}: Blender no devolvió medidas: ' + (p.stderr or p.stdout or '')[-300:]); continue
        M = json.loads(fs.read_text(encoding='utf-8')); res = []
        for t in C['tomas_plan']:
            m = (M.get('tomas') or {}).get(t['id'])
            if not m: continue
            dif = ['error: ' + m['error']] if m.get('error') else cruzar(t, m)
            res.append({'toma': t['id'], 'camara_molde': t.get('camara_molde'), 'coincide': not dif, 'diferencias': dif, 'imagenes': m.get('imagenes'),
                        'medidas': m.get('personajes')})
        K.guardar(S / 'informe.json', {'escena': n, 'cuerpos': M.get('cuerpos'), 'vrm_addon': M.get('vrm_addon'), 'tomas': res})
        filas.append({'escena': n, 'tomas': len(res), 'coinciden': sum(1 for r in res if r['coincide']), 'cuerpos': M.get('cuerpos'), 'carpeta': str(S),
                      'diferencias': [f"{r['toma']}: {d}" for r in res for d in r['diferencias']][:12]})
    tot = sum(f['tomas'] for f in filas); ok = sum(f['coinciden'] for f in filas)
    return K.r_base('02', D, {'version': 'o109', 'escenas': filas, 'faltan': faltan,
                              'resumen': f'02 o109 · molde 3D: {len(filas)} escenas, {ok}/{tot} tomas coinciden con las palabras del 01' + (f' · {len(faltan)} paradas' if faltan else '')})


def main(argv):
    import argparse
    import paso01_cubos as K
    ap = argparse.ArgumentParser(prog='ver o109 cubo02')
    ap.add_argument('--canal', required=True); ap.add_argument('--capitulo', required=True); ap.add_argument('--escena', default='')
    ap.add_argument('--tomas', type=int, default=0, help='máximo de tomas por escena (0 = todas)'); ap.add_argument('--timeout', default=1500)
    a = ap.parse_args(argv); a.solo = {x for x in a.escena.split(',') if x}
    D = K.carpeta(a.canal, a.capitulo)
    if not D: return {'ok': False, 'caja': 'cubo', 'cubo': '02', 'error': f'no hay carpeta del capítulo {a.capitulo} del canal {a.canal}'}
    t0 = time.time(); r = cubo02(K, D, a); r['segundos'] = round(time.time() - t0, 1); return r
