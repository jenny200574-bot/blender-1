"""Prueba de preflight_blend.py en Blender real con escena sintética (sin material de cliente).

  blender -b --factory-startup -P probar_preflight_blend.py -- SALIDA

Construye la escena, le mete una malla con NaN, la guarda en SALIDA/escena.blend, arma un
paquete mínimo y lanza el preflight en otro Blender. Exige: código 2, los bloqueos esperados y
el .blend intacto (mismo hash). Sale 0 si todo se cumple.
"""
import hashlib
import json
import subprocess
import sys
from pathlib import Path

import bpy

AQUI = Path(__file__).resolve().parent
sys.path.insert(0, str(AQUI))
import escena_sintetica as ES

OUT = Path(sys.argv[sys.argv.index('--') + 1:][0]).resolve()
OUT.mkdir(parents=True, exist_ok=False)
ES.construir(12, cortes_entorno=1)
roto = bpy.data.meshes.new('malla_rota')
roto.from_pydata([(0, 0, 0), (1, 0, 0), (float('nan'), 1, 0)], [], [(0, 1, 2)])
ob = bpy.data.objects.new('malla_rota', roto)
bpy.context.scene.collection.objects.link(ob)
blend = OUT / 'escena.blend'
bpy.ops.wm.save_as_mainfile(filepath=str(blend))
antes = hashlib.sha256(blend.read_bytes()).hexdigest()
pk = OUT / 'paquete'
pk.mkdir()
sb = {'vinetas': [{'vineta': 'v01', 't_abs': [0, 0.5], 'objetivo': 'actor_a'}, {'vineta': 'v02', 't_abs': [0.5, 0.5], 'objetivo': 'objeto_fantasma'}]}
(pk / 'sb.json').write_text(json.dumps(sb), encoding='utf-8')
entrada = {'clock': {'fps': 24, 'duration_s': 0.5},
           'entities': [{'id': 'actor_a', 'type': 'CHARACTER', 'legacy': {'spec': {}}, 'points': [{'id': 'mano'}]}],
           'bindings': {'mesa_ref': {'scene_object_id': 'mesa'}, 'roto_ref': {'scene_object_id': 'no_existe'}},
           'rules': {'colliders': ['piso', 'collider_fantasma']},
           'contacts': [{'target_point': 'actor_a.mano'}, {'target_point': 'punto_fantasma'}],
           'camera': {'source': 'sb.json'}}
(pk / 'entrada_escena.json').write_text(json.dumps(entrada), encoding='utf-8')
cmd = [bpy.app.binary_path, '-b', '--factory-startup', '--disable-autoexec', str(blend), '--python-exit-code', '17',
       '-P', str(AQUI.parents[1] / 'motor' / 'preflight_blend.py'), '--', str(pk), '--salida', str(OUT / 'informe.json')]
r = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
inf = json.loads((OUT / 'informe.json').read_text(encoding='utf-8'))
codigos = sorted({f['codigo'] for f in inf['filas'] if f['severidad'] == 'BLOQUEO'})
esperados = ['BINDING_SIN_OBJETO', 'COLLIDER_SIN_OBJETO', 'OBJETIVO_SIN_OBJETO', 'PUNTO_SIN_OBJETO', 'VERTICES_NO_FINITOS']
despues = hashlib.sha256(blend.read_bytes()).hexdigest()
ok = r.returncode == 2 and codigos == esperados and antes == despues and inf['entorno_visible']['poligonos'] > 0
print('PRUEBA_PREFLIGHT_BLEND ' + json.dumps({'ok': ok, 'rc': r.returncode, 'bloqueos': codigos, 'blend_intacto': antes == despues,
                                             'entorno': inf['entorno_visible'], 'blender': bpy.app.version_string}), flush=True)
sys.exit(0 if ok else 1)
