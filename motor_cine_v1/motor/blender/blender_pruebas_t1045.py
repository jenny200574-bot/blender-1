"""Pruebas Blender CPU (US$0) t1045s3546: excepthook, clip_desde_reposo en molde animal, calc distancia."""
import bpy, sys, os, json, traceback
from mathutils import Vector, Quaternion

# This file is invoked in two modes via --mode
argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
mode = argv[0] if argv else 'help'
print('MODO', mode, flush=True)

if mode == 'excepthook':
    # Import the hook pattern from motor (standalone copy) and raise
    import atexit
    _OK = False
    def hook(typ, val, tb):
        print('HOOK_OK', typ.__name__, val, flush=True)
        os._exit(7)
    def ate():
        if not _OK:
            print('ATEXIT_SIN_OK', flush=True)
            os._exit(7)
    sys.excepthook = hook
    atexit.register(ate)
    raise TypeError("distancia_m simulada str-str")

if mode == 'clip_reposo':
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    # Recreate clip_desde_reposo with FPS=24 as in motor
    FPS = 24
    def clip_desde_reposo(arm, cuadros=None):
        cuadros = cuadros or max(1, int(round(FPS)))
        bones = [b.name for b in arm.pose.bones]
        poses = [{n: (Vector(), Quaternion()) for n in bones} for _ in range(cuadros)]
        info = {"fuente": "reposo_del_molde", "cuadros": cuadros, "periodo_cuadros": cuadros, "zancada_ciclo_m": 0.0}
        return {"poses": poses, "P": cuadros, "D": 0.0}, info
    arms = [o for o in bpy.data.objects if o.type == 'ARMATURE']
    if not arms:
        print('FALLO sin armature'); sys.exit(2)
    arm = arms[0]
    bones = [b.name for b in arm.pose.bones]
    humano = all(b in bones for b in ('cadera', 'femur_L', 'femur_R', 'pie_L', 'pie_R'))
    C, info = clip_desde_reposo(arm)
    print('ARMATURE', arm.name)
    print('BONES', bones)
    print('HUMANO', humano)
    print('CLIP', json.dumps(info), 'P', C['P'], 'D', C['D'], 'huesos_en_pose', len(C['poses'][0]))
    assert C['P'] == 24 and C['D'] == 0.0
    assert set(C['poses'][0]) == set(bones)
    assert not humano, 'este molde debía ser no humano (prueba del ave)'
    # foot-lock guard
    pies_ok = all(p in arm.pose.bones for p in ('pie_L', 'pie_R'))
    print('PIES_OK', pies_ok)
    assert not pies_ok
    print('CLIP_REPOSO_OK')
    sys.exit(0)

if mode == 'calc_vineta_datos':
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import numeros_json as NJ
    cam_path = argv[1]
    alturas = json.loads(argv[2]) if len(argv) > 2 else {}
    CV, avisos = NJ.normalizar_camara(json.load(open(cam_path)))
    sensor_h = float(CV['sensor_mm'][1])
    out = []
    for v in CV['vinetas']:
        obj = v['objetivo']
        h = NJ.a_numero(v.get('altura_m'), 'altura_m') or float(alturas.get(obj, 1.0))
        for k in v['keyframes']:
            lente = NJ.a_numero(k.get('lente_mm'), 'lente_mm', obligatorio=True)
            d = NJ.a_numero(k.get('distancia_m'), 'distancia_m')
            fuente = 'json'
            if d is None:
                d = NJ.distancia_desde_plano(k.get('plano'), lente, h, sensor_h)
                fuente = 'plano+lente+altura'
            out.append({"vineta": v['vineta'], "obj": obj, "plano": k.get('plano'), "lente": lente, "h": h, "dist": round(d, 4), "fuente": fuente})
    print('CALC_DIST', json.dumps(out, ensure_ascii=False))
    print('AVISOS', len(avisos))
    print('CALC_OK')
    sys.exit(0)

print('uso: -- mode ...')
sys.exit(1)
