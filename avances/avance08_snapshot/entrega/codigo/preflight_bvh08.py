import sys,json
from pathlib import Path
R=Path('/opt/myia-motor-v9/avance08_20261107');M=R/'MOTOR_BVH08_CANDIDATO';sys.path.insert(0,str(M/'motor'))
from orquestador import ejecutar
x=ejecutar(R/'esc1_bvh08/entrada_escena.json',R/'preflight_bvh08',prueba_cpu=True,blender='/opt/blender/actual/blender',solo_validar=True)
y={'estado':x['estado'],'faltantes':len(x['errores']),'errores':x['errores'],'source':'Native orquestador.ejecutar solo_validar=True; no CLI flag invented','full_scene_review_passed':False}
(R/'entrega/evidencias/preflight_bvh08.json').write_text(json.dumps(y,ensure_ascii=False,indent=2));print(json.dumps(y,ensure_ascii=False));assert not x['errores']
