#!/usr/bin/env python3
"""PISTA INMI (2026-10-30): orden 114 — igual que o113 pero usa poses_o114 (escala propia de cada hueso, sin deriva) y la GUARDIA DEL CUERPO cuadro a cuadro: si falla, la escena queda RECHAZADA (nombra hueso y cuadro). Orden 113 — igual que o112 y además crea las cámaras «auto_o113_*» del filtro del 01 (cubos/01/camaras_o113). Orden 112 (t305u) — cubo 02v «video gris 3D de la escena» (GRATIS, sin red). Genérico (cualquier canal/historia).
Lee cubos/01/esc_N.json con eventos de ARGON validados (version_eventos o112; sin eso se PARA: no hay borrador ni posiciones de prueba)
y el molde.blend del escenario. Personajes: cuerpos de molde_o109_blender.py; poses: la biblioteca MONTADA del 02c (cajas/poses_o110).
Saca: un MP4 por cámara del molde usada + vista general + corte_tomas.mp4 (montaje del plan de tomas) + chequeos automáticos
(pies hundidos/flotando, atravesar objetos, lado de la pantalla vs palabras, oclusión). Escribe SOLO en <capítulo>/cubos/02/video_o112/esc_N/."""
import json, os, subprocess, sys, time
from pathlib import Path
AQUI = Path(__file__).resolve().parent; POSES = AQUI / 'poses_o114'


def cortar(S, tomas):
    partes = []
    for i, t in enumerate(tomas):
        v = S / f"{t['camara_molde']}.mp4"
        if not v.exists(): continue
        o = S / f'_t{i}.mp4'
        subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-ss', str(t['t'][0]), '-to', str(t['t'][1]), '-i', str(v), '-vf',
                        f"drawtext=text='{t['id']} {t['camara_molde']}':x=6:y=6:fontsize=14:fontcolor=yellow", '-c:v', 'libx264', '-an', str(o)]); partes.append(o)
    if not partes: return None
    lst = S / '_corte.txt'; lst.write_text(''.join(f"file '{x}'\n" for x in partes))
    subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-f', 'concat', '-safe', '0', '-i', str(lst), '-c', 'copy', str(S / 'corte_tomas.mp4')])
    for x in partes: x.unlink()
    lst.unlink(); return str(S / 'corte_tomas.mp4')


def resumen_chequeos(R):
    C = R.get('chequeos') or {}; L = C.get('lado') or []
    return {'pies_fuera_de_piso': {k: len(v) for k, v in (C.get('pies') or {}).items()}, 'atraviesa_objetos': {k: sorted(v) for k, v in (C.get('choques') or {}).items()},
            'lado_igual': f"{sum(1 for x in L if x['igual'])}/{len(L)}", 'lado_cruzado': [x for x in L if not x['sin_cruce']][:10],
            'tapados': [x for x in C.get('oclusion') or [] if x['tapado'] >= .5], 'faltas_pose': R.get('faltas_pose'), 'avisos': R.get('avisos')}


def cubo02v(K, D, a):
    import cubo02_molde_o109 as M2
    filas, faltan = [], []
    b = K.blender()
    if not b: return K.r_base('02', D, {'ok': False, 'version': 'o112', 'error': 'no hay Blender en este equipo'})
    for e in K.escenas(D, a.solo):
        n = e['numero']; C = K.leer(D / 'cubos' / '01' / f'esc_{n}.json')
        ev = (C or {}).get('eventos') if isinstance(C, dict) else None
        if not (isinstance(ev, dict) and C.get('version_eventos') == 'o112' and ev.get('origen') == 'argon' and ev.get('beats')):
            faltan.append(f'escena {n}: el 01 no trae eventos o112 de Argon validados (no se inventa nada)'); continue
        blend = D / 'ramas' / 'moldes' / str(C.get('escenario_id') or e['escenario_id']) / 'molde.blend'
        if not blend.is_file(): faltan.append(f'escena {n}: el escenario no tiene molde.blend'); continue
        S = D / 'cubos' / '02' / 'video_o112' / f'esc_{n}'; S.mkdir(parents=True, exist_ok=True)
        asp = C.get('aspecto') or [16, 9]
        tomas = [{'id': t['id'], 't': t['t'], 'camara_molde': t['camara_molde'], 'palabras': t.get('palabras')} for t in C.get('tomas_plan') or [] if t.get('camara_molde') and t.get('t')]
        ent = {'personajes': [{'id': p['id'], 'altura': p.get('altura'), 'segmentos': p.get('segmentos'),
                               'controles': ((C.get('parametros_3d') or {}).get(p['id']) or {}).get('controles') or {}} for p in C['personajes']],
               'puntos': C.get('puntos'), 'eventos': ev, 'tomas': tomas, 'fps': C.get('fps') or 8, 'duracion_s': C.get('duracion_s'),
               'res': [480, 270] if asp[0] >= asp[1] else [270, 480], 'salida_dir': str(S), 'vrm_base': M2.VRM_BASE, 'addons_dir': M2.ADDONS,
               'addon': 'VRM_Addon_for_Blender-release', 'o110_dir': str(POSES), 'poses_lib': str(POSES / 'poses_basicas.json'),
               'molde_o109_blender': str(AQUI / 'molde_o109_blender.py'),
               'camaras_auto': (K.leer(D / 'cubos' / '01' / 'camaras_o113' / f"{C.get('escenario_id') or e['escenario_id']}.json") or {}).get('auto') or []}
        fe, fs = S / 'entrada.json', S / 'resultado.json'; fe.write_text(json.dumps(ent, ensure_ascii=False, indent=1), encoding='utf-8')
        if fs.exists(): fs.rename(S / f"resultado.antes_{time.strftime('%Y%m%d-%H%M%S')}.json")
        cmd = ['nice', '-n', '15', b, '-b', str(blend), '--factory-startup', '--python', str(AQUI / 'video_o114_blender.py'), '--', str(fe), str(fs)]
        try: p = subprocess.run(cmd, capture_output=True, text=True, timeout=int(a.timeout))
        except subprocess.TimeoutExpired: faltan.append(f'escena {n}: Blender tardó demasiado'); continue
        (S / 'blender.log').write_text((p.stdout or '')[-30000:] + '\n--- stderr ---\n' + (p.stderr or '')[-8000:], encoding='utf-8')
        if not fs.is_file(): faltan.append(f'escena {n}: Blender no devolvió resultado: ' + (p.stderr or p.stdout or '')[-300:]); continue
        R = json.loads(fs.read_text(encoding='utf-8')); R['videos']['corte_tomas'] = cortar(S, tomas); fs.write_text(json.dumps(R, ensure_ascii=False, indent=1), encoding='utf-8')
        G_ = R.get('guardia') or {}
        if not G_.get('ok'): faltan.append(f"escena {n}: RECHAZADA por la guardia del cuerpo ({G_.get('n_fallas')} fallas); primera: {(G_.get('primeras') or [{}])[0]}")
        filas.append({'escena': n, 'ok': bool(G_.get('ok')), 'guardia': G_, 'carpeta': str(S), 'videos': R['videos'], 'chequeos': resumen_chequeos(R), 'efectos': R.get('efectos'), 'cuerpos': R.get('cuerpos')})
    return K.r_base('02', D, {'version': 'o114', 'cubo': '02v', 'escenas': filas, 'faltan': faltan,
                              'resumen': f'02v o114 · video gris 3D (con guardia): {len(filas)} escenas' + (f' · {len(faltan)} paradas' if faltan else '')})


def main(argv):
    import argparse
    import paso01_cubos as K
    ap = argparse.ArgumentParser(prog='ver o109 cubo02video')
    ap.add_argument('--canal', required=True); ap.add_argument('--capitulo', required=True); ap.add_argument('--escena', default='')
    ap.add_argument('--timeout', default=5400)
    a = ap.parse_args(argv); a.solo = {x for x in a.escena.split(',') if x}
    D = K.carpeta(a.canal, a.capitulo)
    if not D: return {'ok': False, 'caja': 'cubo', 'cubo': '02v', 'error': f'no hay carpeta del capítulo {a.capitulo} del canal {a.canal}'}
    t0 = time.time(); r = cubo02v(K, D, a); r['segundos'] = round(time.time() - t0, 1); return r
