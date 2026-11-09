"""R3: fcurves hide_render anulan publicación; informe_conflicto siempre en bloqueadas."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'motor'))
from cabeza_visible_constructor import quitar_fcurves_visibilidad_objeto, publicar_mallas_cabeza_adn
from camara_directa_exp import informe_conflicto_toma
from malla_cabeza import malla_es_cabeza


class _FCurve:
    def __init__(self, data_path):
        self.data_path = data_path
        self.keyframe_points = []


class _Action:
    def __init__(self, curvas):
        self.fcurves = curvas

    def remove(self, curva):
        self.fcurves.remove(curva)


class _Anim:
    def __init__(self, action):
        self.action = action


class _Mesh:
    def __init__(self, name, **props):
        self.name = name
        self.type = 'MESH'
        self.hide_render = props.get('hide_render', True)
        self.hide_viewport = props.get('hide_viewport', True)
        self.parent_type = props.get('parent_type', 'BONE')
        self.parent_bone = props.get('parent_bone', 'cabeza')
        self._props = dict(props)
        self.animation_data = props.get('animation_data')

    def get(self, k, default=None):
        return self._props.get(k, default)

    def __setitem__(self, k, v):
        self._props[k] = v


def test_quitar_fcurves_hide():
    curvas = [_FCurve('hide_render'), _FCurve('location.x')]
    act = _Action(curvas)
    m = _Mesh('face', animation_data=_Anim(act))
    n = quitar_fcurves_visibilidad_objeto(m)
    assert n == 1
    assert len(act.fcurves) == 1
    assert act.fcurves[0].data_path == 'location.x'


def test_publicar_quita_fcurves_y_fija():
    act = _Action([_FCurve('hide_render')])
    entity = {'id': 'ch-pintor-bce0', 'appearance': {'geometry': {'parts': [{'id': 'ch-pintor-bce0.base.face', 'bind_role': 'head', 'role': 'face'}]}}}
    mesh = _Mesh('ch-pintor-bce0.base.face', bind_role='head', semantic_role='face', animation_data=_Anim(act))
    cap = _Mesh('ch-pintor-bce0_malla_cabeza', hide_render=True, motor_preserve_hidden=True)
    class Rig:
        children_recursive = [cap, mesh]
    pub = publicar_mallas_cabeza_adn(entity, Rig(), ['cabeza'])
    assert 'ch-pintor-bce0.base.face' in pub
    assert len(act.fcurves) == 0
    assert mesh.hide_render is False
    assert mesh.get('motor_visibilidad_cabeza_fija') is True


def test_informe_conflicto_siempre_dict():
    rep = informe_conflicto_toma('toma05', {'plano0': 'CU', 'elev': 12, 'orient': 0, 'lens': 35, 'roll_deg': 0}, ['malla de cabeza no visible'], {'encuadre': 2}, {})
    assert rep['vineta'] == 'toma05'
    assert 'opciones_sin_cambiar_storyboard' in rep
    assert rep['motivos_revision']


if __name__ == '__main__':
    test_quitar_fcurves_hide()
    test_publicar_quita_fcurves_y_fija()
    test_informe_conflicto_siempre_dict()
    print('OK test_visibilidad_cabeza_fcurves')
