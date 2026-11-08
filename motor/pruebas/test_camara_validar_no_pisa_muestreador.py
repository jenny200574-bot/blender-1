"""El constructor real reventó en validar porque el bucle de tomas pisó la función muestras.

Esta prueba no abre Blender. Compila las funciones reales de camara_v2_blender.py,
les pone encima la lista que el bucle guardaba con el mismo nombre, y llama a validar
como lo hace el resolutor después de construir una trayectoria.
"""
import ast
import unittest
from pathlib import Path

CAMARA = Path(__file__).resolve().parents[1] / 'motor' / 'camara_v2_blender.py'


def _compilar(nombres):
    arbol = ast.parse(CAMARA.read_text(encoding='utf-8'))
    cuerpo = [nodo for nodo in arbol.body if isinstance(nodo, ast.FunctionDef) and nodo.name in nombres]
    if {nodo.name for nodo in cuerpo} != set(nombres):
        faltan = set(nombres) - {nodo.name for nodo in cuerpo}
        raise AssertionError('Faltan funciones en camara_v2_blender.py: ' + ', '.join(sorted(faltan)))
    modulo = ast.Module(body=cuerpo, type_ignores=[])
    ast.fix_missing_locations(modulo)
    espacio = {}
    exec(compile(modulo, str(CAMARA), 'exec'), espacio)
    return espacio


class ValidarNoPisaMuestreador(unittest.TestCase):
    def test_la_lista_de_busqueda_no_vuelve_inllamable_a_validar(self):
        espacio = _compilar({'cuadros_muestra', 'validar'})
        # El bucle de avance12 hacía `muestras = muestras_busqueda(...)` en el mismo módulo.
        espacio['muestras'] = [{'frente': (1, 0, 0), 'mira': (0, 0, 1)}]
        malos = espacio['validar'](
            [],
            {'medir': lambda f: None, 'excluir_oclusion': set(), 'excluir_env': frozenset()},
            1,
            3,
        )
        self.assertEqual(malos, [])
        self.assertEqual(espacio['cuadros_muestra'](1, 3), [1, 2, 3])

    def test_el_bucle_de_tomas_no_reasigna_el_muestreador(self):
        arbol = ast.parse(CAMARA.read_text(encoding='utf-8'))
        asignados = set()
        for nodo in arbol.body:
            if isinstance(nodo, ast.Assign):
                for destino in nodo.targets:
                    if isinstance(destino, ast.Name):
                        asignados.add(destino.id)
            elif isinstance(nodo, ast.AnnAssign) and isinstance(nodo.target, ast.Name):
                asignados.add(nodo.target.id)
        self.assertNotIn('cuadros_muestra', asignados)
        self.assertNotIn('validar', asignados)
        texto = CAMARA.read_text(encoding='utf-8')
        self.assertIn('def cuadros_muestra(f0, f1):', texto)
        self.assertIn('for f in cuadros_muestra(f0, f1):', texto)
        self.assertNotIn('def muestras(f0, f1):', texto)


if __name__ == '__main__':
    unittest.main()
