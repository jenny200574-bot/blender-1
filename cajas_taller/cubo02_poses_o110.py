#!/usr/bin/env python3
"""PISTA INMI (2026-10-30): orden 110 (t298u) — cubo 02c «molde 3D por toma CON POSE» (GRATIS, sin red). Igual que el 02b (o109) y además
pone a cada personaje en la pose que el 01 escribió en palabras.por_personaje[].pose (+ espejo); sin pose = de_pie. Usa la biblioteca
o110 (cajas/poses_o110: aplicar_pose.py humanoides, universal.py otros cuerpos). Palabra que falte = FALTA en el informe (nunca se inventa).
NO modifica los programas del 02b: reusa cubo02_molde_o109 (lectura del 01, cruce de palabras) y molde_o109_blender.py (cuerpos y cámara).
Escribe SOLO en <capítulo>/cubos/02/poses_o110/esc_N/."""
import json, os, subprocess, sys, time
from pathlib import Path
AQUI = Path(__file__).resolve().parent
POSES = AQUI / 'poses_o110'
sys.path.insert(0, str(POSES))


def cubo02c(K, D, a):
    import cubo01_o109 as C1, cubo02_molde_o109 as M2, palabras_pose as PP
    filas, faltan = [], []
    b = K.blender()
    if not b: return K.r_base('02', D, {'ok': False, 'version': 'o110', 'error': 'no hay Blender en este equipo'})
    for e in K.escenas(D, a.solo):
        n = e['numero']; C = K.leer(D / 'cubos' / '01' / f'esc_{n}.json')
        if not (isinstance(C, dict) and C.get('version_01') == 'o109'): faltan.append(f'escena {n}: sin dirección o109 del cubo 01 (no se inventa nada)'); continue
        blend = D / 'ramas' / 'moldes' / str(C.get('escenario_id') or e['escenario_id']) / 'molde.blend'
        if not blend.is_file(): faltan.append(f'escena {n}: el escenario no tiene molde.blend'); continue
        pers = [{'id': p['id'], 'altura': p.get('altura'), 'controles': ((C.get('parametros_3d') or {}).get(p['id']) or {}).get('controles') or {}} for p in C['personajes']]
        tomas, err_pal = [], []
        for t in C.get('tomas_plan') or []:
            if not t.get('camara_molde') or not t.get('t') or None in t['t']: continue
            tm = (float(t['t'][0]) + float(t['t'][1])) / 2; est = {}
            for p in C['personajes']:
                pos, rot = C1.estado_en(K, C, p, tm)
                if pos is not None: est[p['id']] = {'pos': pos, 'rot': rot or 0}
            pw = {x.get('id'): x for x in ((t.get('palabras') or {}).get('por_personaje') or []) if isinstance(x, dict)}
            for cid, x in pw.items(): err_pal += PP.validar_toma(t['id'], cid, x)
            poses = {cid: {'pose': x.get('pose'), 'espejo': bool(x.get('espejo'))} for cid, x in pw.items()}
            tomas.append({'id': t['id'], 'camara_molde': t['camara_molde'], 'segundo': tm, 'estados': est, 'en_cuadro': (t.get('palabras') or {}).get('en_cuadro') or [], 'poses': poses})
        if a.tomas: tomas = tomas[:a.tomas]
        S = D / 'cubos' / '02' / 'poses_o110' / f'esc_{n}'; S.mkdir(parents=True, exist_ok=True)
        ent = {'personajes': pers, 'tomas': tomas, 'salida_dir': str(S), 'vrm_base': M2.VRM_BASE, 'addons_dir': M2.ADDONS, 'poses_dir': str(POSES),
               'molde_o109_blender': str(AQUI / 'molde_o109_blender.py'),
               'res': [960, 540] if (C.get('aspecto') or [16, 9])[0] >= (C.get('aspecto') or [16, 9])[1] else [540, 960]}
        fe, fs = S / 'entrada.json', S / 'medidas.json'; fe.write_text(json.dumps(ent, ensure_ascii=False, indent=1), encoding='utf-8')
        if fs.exists(): fs.unlink()
        cmd = ['nice', '-n', '15', b, '-b', str(blend), '--factory-startup', '--python', str(AQUI / 'molde_poses_o110_blender.py'), '--', str(fe), str(fs)]
        try: p = subprocess.run(cmd, capture_output=True, text=True, timeout=int(a.timeout))
        except subprocess.TimeoutExpired: faltan.append(f'escena {n}: Blender tardó demasiado'); continue
        (S / 'blender.log').write_text((p.stdout or '')[-20000:] + '\n--- stderr ---\n' + (p.stderr or '')[-5000:], encoding='utf-8')
        if not fs.is_file(): faltan.append(f'escena {n}: Blender no devolvió medidas: ' + (p.stderr or p.stdout or '')[-300:]); continue
        M = json.loads(fs.read_text(encoding='utf-8')); res = []
        for t in C['tomas_plan']:
            m = (M.get('tomas') or {}).get(t['id'])
            if not m: continue
            ps = (M.get('poses') or {}).get(t['id']) or {}
            dif = ['error: ' + m['error']] if m.get('error') else M2.cruzar(t, m)
            acost = [pid for pid, r in ps.items() if str(r.get('aplicada', '')).startswith('acostado')]
            avisos = [f'{pid}: acostado — el cruce frente/espalda del 02b no aplica a un cuerpo acostado' for pid in acost]
            dif = [d for d in dif if not any(d.startswith(f'{pid}: palabras «') and ('lo ve de espalda' in d or 'lo ve de frente' in d) for pid in acost)]
            dif += [f"{pid}: {r['falta']}" for pid, r in ps.items() if r.get('falta')]
            dif += [f"{pid}: se hunde o flota ({r.get('zmin_menos_piso')} m)" for pid, r in ps.items() if r.get('piso_ok') is False]
            res.append({'toma': t['id'], 'camara_molde': t.get('camara_molde'), 'coincide': not dif, 'diferencias': dif, 'imagenes': m.get('imagenes'), 'poses': ps, 'avisos': avisos, 'medidas': m.get('personajes')})
        K.guardar(S / 'informe.json', {'escena': n, 'cuerpos': M.get('cuerpos'), 'errores_palabras_pose': err_pal, 'tomas': res})
        filas.append({'escena': n, 'tomas': len(res), 'coinciden': sum(1 for r in res if r['coincide']), 'cuerpos': M.get('cuerpos'), 'carpeta': str(S),
                      'errores_palabras_pose': err_pal[:12], 'diferencias': [f"{r['toma']}: {d}" for r in res for d in r['diferencias']][:12]})
    tot = sum(f['tomas'] for f in filas); ok = sum(f['coinciden'] for f in filas)
    return K.r_base('02', D, {'version': 'o110', 'escenas': filas, 'faltan': faltan, 'poses_validas': PP.lista(),
                              'resumen': f'02c o110 · molde con poses: {len(filas)} escenas, {ok}/{tot} tomas coinciden' + (f' · {len(faltan)} paradas' if faltan else '')})


def main(argv):
    import argparse
    import paso01_cubos as K
    ap = argparse.ArgumentParser(prog='ver o109 cubo02poses')
    ap.add_argument('--canal', required=True); ap.add_argument('--capitulo', required=True); ap.add_argument('--escena', default='')
    ap.add_argument('--tomas', type=int, default=0); ap.add_argument('--timeout', default=1500)
    a = ap.parse_args(argv); a.solo = {x for x in a.escena.split(',') if x}
    D = K.carpeta(a.canal, a.capitulo)
    if not D: return {'ok': False, 'caja': 'cubo', 'cubo': '02', 'error': f'no hay carpeta del capítulo {a.capitulo} del canal {a.canal}'}
    t0 = time.time(); r = cubo02c(K, D, a); r['segundos'] = round(time.time() - t0, 1); return r
