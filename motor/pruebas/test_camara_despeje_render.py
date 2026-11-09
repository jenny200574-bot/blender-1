"""Despeje R12: visible_camera, prohibidos, fcurve stub."""
import json
import sys
import unittest
from pathlib import Path

R = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(R / 'motor'))

from camara_despeje_render import (
    aplicar_visible_camera_toma,
    comprobar_fcurve_despeje,
    filtrar_objetos_despeje,
    objeto_permitido_despeje,
    revisar_despeje_etapa13,
    valor_visible_camera_en_cuadro,
)
from camara_directa_exp import tapadores_escenario_desde_malos


class _KP:
    def __init__(self, x, y, interp='CONSTANT'):
        self.co = (float(x), float(y))
        self.interpolation = interp


class _FC:
    def __init__(self, path, points):
        self.data_path = path
        self.keyframe_points = points

    def find(self, _path):
        return self if self.data_path == _path else None


class _Action:
    def __init__(self, fcurves):
        self.fcurves = fcurves


class _Anim:
    def __init__(self, action):
        self.action = action


class _Ob:
    def __init__(self, name, inserts=None):
        self.name = name
        self.type = 'MESH'
        self.visible_camera = True
        self.animation_data = None
        self._inserts = inserts or []
        self.meta = {}

    def keyframe_insert(self, data_path, frame):
        self._inserts.append((data_path, int(frame), bool(self.visible_camera)))

    def __setitem__(self, k, v):
        self.meta[k] = v


class _BpyData:
    def __init__(self, objs):
        self.objects = objs

    def get(self, name):
        return self.objects.get(name)


class _Bpy:
    def __init__(self, objs):
        self.data = _BpyData(objs)


class Tests(unittest.TestCase):
    def test_prohibe_personaje_y_prop(self):
        self.assertFalse(objeto_permitido_despeje('ch-eco-eff3'))
        self.assertFalse(objeto_permitido_despeje('obj-cama.cabecero'))
        self.assertTrue(objeto_permitido_despeje('muro_frente_2'))

    def test_filtrar_rechaza_prop(self):
        with self.assertRaises(ValueError):
            filtrar_objetos_despeje(['muro_fondo_1', 'obj-cama.estructura'])

    def test_tapadores_no_obj_cama(self):
        malos = [(10, 'cámara pegada a geometría del escenario (obj-cama.cabecero)', 0)]
        t = tapadores_escenario_desde_malos(malos, act_ids=('ch-x',))
        self.assertNotIn('obj-cama.cabecero', t)

    def test_aplicar_inserta_keyframes_rango(self):
        ob = _Ob('muro_frente_2')
        bpy = _Bpy({'muro_frente_2': ob})
        out = aplicar_visible_camera_toma(bpy, ['muro_frente_2'], 720, 792, 'v8')
        self.assertEqual(out, ['muro_frente_2'])
        frames = {f: v for _, f, v in ob._inserts}
        self.assertFalse(frames[720])
        self.assertTrue(frames[793])
        self.assertIn('motor_despeje_camara', ob.meta)

    def test_comprobar_fcurve_stub(self):
        ob = _Ob('muro_frente_2')
        ob.animation_data = _Anim(_Action([
            _FC('visible_camera', [_KP(719, 1), _KP(720, 0), _KP(793, 1)]),
        ]))
        self.assertIsNone(comprobar_fcurve_despeje(ob, 720, 792))
        self.assertEqual(
            comprobar_fcurve_despeje(_Ob('x'), 1, 10),
            'despeje_registrado_sin_fcurve_visible_camera',
        )

    def test_valor_en_cuadro(self):
        act = _Action([_FC('visible_camera', [_KP(720, 0), _KP(793, 1)])])
        self.assertFalse(valor_visible_camera_en_cuadro(act, 750))
        self.assertTrue(valor_visible_camera_en_cuadro(act, 800))

    def test_anti_falso_pase_bvh_legacy(self):
        tomas = [{
            'vineta': 'v8',
            'frame_ini': 720,
            'frame_fin': 792,
            'experimental_directa': {
                'despeje_escenario': {
                    'objetos_excluidos_bvh': ['muro_frente_2'],
                    'nota': 'Solo exclusión en BVH de validación; personajes no cambian.',
                },
            },
        }]
        err = revisar_despeje_etapa13(None, tomas)
        self.assertTrue(any(e['type'] == 'DESPEJE_FALSO_PASE' for e in err))


if __name__ == '__main__':
    unittest.main(verbosity=2)
