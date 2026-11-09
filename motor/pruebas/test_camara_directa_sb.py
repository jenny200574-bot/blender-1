"""Contrato modo directa SB: camara_busqueda_reparacion.off omite rejilla, mantiene validación."""
import ast
from pathlib import Path

MOTOR = Path(__file__).resolve().parents[1] / 'motor'
CV2 = (MOTOR / 'camara_v2_blender.py').read_text(encoding='utf-8')


def test_flag_directo_en_fuente():
    assert "DIRECTO = OFF('camara_busqueda_reparacion')" in CV2
    assert "SW['directa_sb'] = DIRECTO" in CV2
    assert 'rama_directa_sb' in CV2
    assert 'busqueda_omitida' in CV2


def test_off_experimental_presente_en_rama():
    off = MOTOR / 'camara_busqueda_reparacion.off'
    assert off.is_file(), 'copia experimental debe incluir el .off (sin búsqueda/reparación)'
    txt = off.read_text(encoding='utf-8')
    assert 'directa' in txt.lower() or 'rejilla' in txt.lower()


def test_modo_directo_no_usa_rejilla_completa_en_ast():
    tree = ast.parse(CV2)
    encontrado = False
    for node in ast.walk(tree):
        if isinstance(node, ast.If) and isinstance(node.test, ast.Name) and node.test.id == 'DIRECTO':
            encontrado = True
    assert encontrado, 'falta rama condicional DIRECTO en camara_v2_blender.py'


if __name__ == '__main__':
    test_flag_directo_en_fuente()
    test_off_experimental_presente_en_rama()
    test_modo_directo_no_usa_rejilla_completa_en_ast()
    print('OK test_camara_directa_sb')
