"""Compara etapa 11 sintética: modo busqueda (sin .off) vs directa SB (.off). Solo CPU, sin VPS.

  blender -b --factory-startup -t 2 --python-exit-code 17 -P probar_directa_vs_busqueda.py -- \
      MOTOR_DIR SALIDA CUADROS TOMAS

Escribe comparativa.json con tiempos, frame_set, BVH y busqueda_matematica por toma.
No afirma escena real avance13 resuelta.
"""
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

AQUI = Path(__file__).resolve().parent
MOTOR_SRC = Path(sys.argv[sys.argv.index('--') + 1]).resolve()
OUT = Path(sys.argv[sys.argv.index('--') + 2]).resolve()
N = int(sys.argv[sys.argv.index('--') + 3])
TOMAS = int(sys.argv[sys.argv.index('--') + 4])
OUT.mkdir(parents=True, exist_ok=True)

BLENDER = os.environ.get('BLENDER', 'blender')


def _run(motor: Path, sub: str):
    d = OUT / sub
    d.mkdir(parents=True, exist_ok=True)
    cmd = [BLENDER, '-b', '--factory-startup', '-t', '2', '--python-exit-code', '17',
           '-P', str(AQUI / 'correr_etapa11_sintetica.py'), '--',
           str(motor), str(d), str(N), str(TOMAS), '3', '0']
    p = subprocess.run(cmd, capture_output=True, text=True)
    med = d / 'medidas.json'
    rep = {}
    if med.is_file():
        rep = json.loads(med.read_text(encoding='utf-8'))
    return {'codigo': p.returncode, 'stderr_tail': (p.stderr or '')[-1200:], 'medidas': rep, 'dir': str(d)}


def _prep(clase: str, con_directa: bool):
    dest = OUT / f'motor_{clase}'
    if dest.exists():
        shutil.rmtree(dest)
    shutil.copytree(MOTOR_SRC, dest, ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
    off = dest / 'motor' / 'camara_busqueda_reparacion.off'
    if con_directa and not off.is_file():
        off.write_text('# modo directa experimental\n', encoding='utf-8')
    elif not con_directa and off.is_file():
        off.unlink()
    return dest


motor_busq = _prep('busqueda', False)
motor_dir = _prep('directa', True)
r_busq = _run(motor_busq, 'corrida_busqueda')
r_dir = _run(motor_dir, 'corrida_directa')

lim = {
    'ambito': 'escena_sintetica_cpu',
    'cuadros': N,
    'tomas': TOMAS,
    'no_escena_real': True,
    'production_approved_siempre_false': True,
}


def _extra(r):
    m = r.get('medidas') or {}
    rep = (m.get('reporte') or {})
    tomas = rep.get('tomas') or []
    return {
        'segundos': m.get('segundos'),
        'frame_set': m.get('frame_set'),
        'bvh_construidos': m.get('bvh_construidos'),
        'estado': m.get('estado'),
        'tomas': [{k: t.get(k) for k in ('toma', 'estado', 'motivos', 'busqueda', 'resuelto', 'reparacion', 'intentos')} for t in tomas],
        'codigo_blender': r['codigo'],
    }

salida = {'limitaciones': lim, 'busqueda': _extra(r_busq), 'directa_sb': _extra(r_dir)}
tmp = OUT / 'comparativa.json.tmp'
tmp.write_text(json.dumps(salida, ensure_ascii=False, indent=1), encoding='utf-8')
os.replace(tmp, OUT / 'comparativa.json')
print(json.dumps({'comparativa': str(OUT / 'comparativa.json'), 'directa_frame_set': salida['directa_sb'].get('frame_set'), 'busqueda_frame_set': salida['busqueda'].get('frame_set')}))
sys.exit(0 if r_busq['codigo'] in (0, 17) and r_dir['codigo'] in (0, 17) else 1)
