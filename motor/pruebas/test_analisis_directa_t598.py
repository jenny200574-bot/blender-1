"""Pruebas reproducibles t598: cabeza, tapadores escenario, clasificación de motivos."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'motor'))
from malla_cabeza import clasificar_medida_cabeza, marcar_malla_cabeza_visible, malla_es_cabeza


class _Mesh:
    def __init__(self, **k):
        self.__dict__.update(k)
    parent_type = 'BONE'
    parent_bone = 'cabeza'
    def get(self, k, d=None):
        return self.__dict__.get(k, d)


def test_malla_es_cabeza_bind_role_en_objeto():
    m = _Mesh(bind_role='head', semantic_role='geometry', parent_bone='pecho')
    assert malla_es_cabeza(m, {'cabeza'})
    m2 = _Mesh(bind_role='body', semantic_role='geometry', parent_bone='pecho')
    assert not malla_es_cabeza(m2, {'cabeza'})


def test_hueso_vs_malla_encuadre_diagnostico():
    hueso = clasificar_medida_cabeza({'origen': 'hueso', 'malla_visible': False})
    assert hueso['medicion'] == 'respaldo_hueso'
    malla = clasificar_medida_cabeza(marcar_malla_cabeza_visible({'centro': (0, 0, 1)}))
    assert malla['valida_visual']


def test_tapadores_escenario_regex():
    from camara_directa_exp import tapadores_escenario_desde_malos, clasificar_motivos_directa

    malos = [
        (10, 'cámara pegada a geometría del escenario (muro_frente_2)', 0.02),
        (11, 'sujeto tapado (escenario: obj-cama.cabecero)', 0.4),
        (12, 'sujeto fuera de cuadro (cabeza)', 0.3),
    ]
    t = tapadores_escenario_desde_malos(malos, act_ids=('ch-pintor-bce0',))
    assert 'muro_frente_2' in t
    assert 'obj-cama.cabecero' not in t  # props de historia: no despeje automático
    cats = clasificar_motivos_directa(malos)
    assert cats['encuadre'] == 1
    assert cats['holgura_escenario'] >= 1


if __name__ == '__main__':
    test_malla_es_cabeza_bind_role_en_objeto()
    test_hueso_vs_malla_encuadre_diagnostico()
    test_tapadores_escenario_regex()
    print('OK test_analisis_directa_t598')
