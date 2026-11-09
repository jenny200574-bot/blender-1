"""Corre camara_v2_blender.py (etapa 11, ruta SB_4G) sobre la escena sintética, en Blender real CPU.

  blender -b --factory-startup -t 2 --python-exit-code 17 -P correr_etapa11_sintetica.py -- \
      MOTOR_DIR SALIDA CUADROS TOMAS [CORTES_ENTORNO] [ANIMADO 0|1]

MOTOR_DIR es la carpeta motor/ que se quiere medir (instalada o parchada).
Cuenta cambios de cuadro (handler frame_change_pre) y construcciones de BVHTree,
y deja medidas.json con el tiempo; si el proceso muere por timeout, medidas_parcial.json
conserva el último conteo. No guarda nada fuera de SALIDA.
"""
import json
import os
import runpy
import sys
import time
import types
from pathlib import Path

import bpy
import mathutils.bvhtree as _bvh_real

AQUI = Path(__file__).resolve().parent
sys.path.insert(0, str(AQUI))
import escena_sintetica as ES

a = sys.argv[sys.argv.index('--') + 1:]
MOTOR = Path(a[0]).resolve()
OUT = Path(a[1]).resolve()
N = int(a[2])
TOMAS = int(a[3])
CORTES = int(a[4]) if len(a) > 4 else 3
ANIMADO = len(a) > 5 and a[5] == '1'
OUT.mkdir(parents=True, exist_ok=True)
CONT = {'frame_set': 0, 'bvh_construidos': 0, 'inicio': time.time()}


def _volcar(nombre='medidas_parcial.json', extra=None):
    d = dict(CONT, segundos=round(time.time() - CONT['inicio'], 3))
    if extra:
        d.update(extra)
    tmp = OUT / (nombre + '.tmp')
    tmp.write_text(json.dumps(d, ensure_ascii=False, indent=1), encoding='utf-8')
    os.replace(tmp, OUT / nombre)


def _contar_cuadro(scene, *_):
    CONT['frame_set'] += 1
    if CONT['frame_set'] % 200 == 0:
        _volcar()


class _BVHContado:
    @staticmethod
    def FromPolygons(*q, **k):
        CONT['bvh_construidos'] += 1
        return _bvh_real.BVHTree.FromPolygons(*q, **k)

    def __getattr__(self, n):
        return getattr(_bvh_real.BVHTree, n)


proxy = types.ModuleType('mathutils.bvhtree')
proxy.BVHTree = _BVHContado
sys.modules['mathutils.bvhtree'] = proxy

sc = ES.construir(N, cortes_entorno=CORTES, entorno_animado=ANIMADO)
ES.insumos(OUT / 'insumos', N, tomas=TOMAS)
cfg = json.loads((MOTOR / 'motor' / 'camara_v2_config.json').read_text(encoding='utf-8'))
(OUT / 'insumos' / 'config.json').write_text(json.dumps(cfg, ensure_ascii=False), encoding='utf-8')
caras_entorno = 0
dg = bpy.context.evaluated_depsgraph_get()
for o in sc.objects:
    if o.type == 'MESH' and not o.name.startswith('actor_'):
        e = o.evaluated_get(dg)
        m = e.to_mesh()
        caras_entorno += len(m.polygons)
        e.to_mesh_clear()
bpy.app.handlers.frame_change_pre.append(_contar_cuadro)
I = OUT / 'insumos'
audit = OUT / 'auditoria_4g'
argv = [str(I / 'entrada.json'), str(I / 'sb_camara.json'), str(I / 'sb_escena.json'), str(I / 'config.json'),
        str(I / 'ajustes.json'), str(audit), str(I / 'comandos.json'), str(I / 'elevaciones.json'), str(I / 'tipos_plano.json')]
viejo = sys.argv
estado = 'ERROR'
try:
    sys.argv = ['resolver_4g', '--'] + argv
    runpy.run_path(str(MOTOR / 'motor' / 'camara_v2_blender.py'), run_name='__motor_sb4g__')
    estado = 'TERMINADO'
finally:
    sys.argv = viejo
    claves = {}
    for blk, pref in ((sc.camera, 'obj'), (sc.camera.data, 'data')):
        act = blk.animation_data.action if blk.animation_data else None
        if act is None:
            continue
        curvas = act.fcurves if hasattr(act, 'fcurves') else []
        for c in curvas:
            claves['%s:%s[%d]' % (pref, c.data_path, c.array_index)] = [[p.co[0], p.co[1], p.interpolation] for p in c.keyframe_points]
    (OUT / 'camara_claves.json').write_text(json.dumps(claves, sort_keys=True), encoding='utf-8')
    rep = {}
    js = audit / 'camara_v2.json'
    if js.is_file():
        r = json.loads(js.read_text(encoding='utf-8'))
        rep = {'resumen': r.get('resumen'), 'tomas': [{'toma': t['toma'], 'estado': t['estado'], 'motivos': t.get('motivos'),
                                                        'busqueda': (t.get('busqueda_matematica') or {}).get('examinados'),
                                                        'resuelto': (t.get('busqueda_matematica') or {}).get('resuelto_geometrico'),
                                                        'reparacion': t.get('reparacion'), 'intentos': t.get('intentos'),
                                                        'camara': t.get('camara'), 'recorrido': t.get('recorrido')} for t in r['tomas']]}
    _volcar('medidas.json', {'estado': estado, 'cuadros': N, 'tomas': TOMAS, 'caras_entorno': caras_entorno,
                             'blender': bpy.app.version_string, 'entorno_animado': ANIMADO, 'cortes': CORTES, 'motor': str(MOTOR), 'reporte': rep})
