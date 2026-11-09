"""Reproduce R2: cápsula legacy oculta vs piezas ADN publicadas."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'motor'))
from cabeza_visible_constructor import es_capsula_legacy_auditoria
from malla_cabeza import malla_es_cabeza, clasificar_medida_cabeza, marcar_malla_cabeza_visible


class _Mesh:
    def __init__(self, name, **props):
        self.name = name
        self.type = 'MESH'
        self.hide_render = props.get('hide_render', False)
        self.hide_viewport = props.get('hide_viewport', False)
        self.parent_type = props.get('parent_type')
        self.parent_bone = props.get('parent_bone')
        self._props = props
    def get(self, k, default=None):
        return self._props.get(k, default)
    def __setitem__(self, k, v):
        self._props[k] = v


def test_capsula_legacy_no_se_publica():
    assert es_capsula_legacy_auditoria('ch-pintor-bce0_malla_cabeza', 'ch-pintor-bce0', True)
    assert es_capsula_legacy_auditoria('ch-pintor-bce0_malla_cabeza', 'ch-pintor-bce0', False)
    assert not es_capsula_legacy_auditoria('ch-pintor-bce0.base.face', 'ch-pintor-bce0', False)


def test_publicar_simulado():
    entity = {
        'id': 'ch-pintor-bce0',
        'appearance': {'geometry': {'parts': [{'id': 'ch-pintor-bce0.base.face', 'bind_role': 'head', 'role': 'face', 'shape': 'MESH', 'vertices_m': [[0, 0, 0]], 'faces': [[0]]}]}},
    }
    rig_children = [
        _Mesh('ch-pintor-bce0_malla_cabeza', hide_render=True, motor_preserve_hidden=True, bind_role='head'),
        _Mesh('ch-pintor-bce0.base.face', hide_render=True, bind_role='head', semantic_role='face'),
    ]
    class Rig:
        children_recursive = rig_children
    from cabeza_visible_constructor import publicar_mallas_cabeza_adn
    pub = publicar_mallas_cabeza_adn(entity, Rig(), ['cabeza'])
    assert 'ch-pintor-bce0.base.face' in pub
    assert rig_children[0].hide_render is True
    assert rig_children[1].hide_render is False
    assert rig_children[1].get('motor_cabeza_canonica') is True
    cl = clasificar_medida_cabeza(marcar_malla_cabeza_visible({'centro': (0, 0, 1)}))
    assert cl['valida_visual']


if __name__ == '__main__':
    test_capsula_legacy_no_se_publica()
    test_publicar_simulado()
    print('OK test_cabeza_visible_legacy')
