"""Regresión R10: _validar_cuadro no debe sombrear la función region() antes de llamarla."""
import ast
import math
import unittest
from pathlib import Path

CAMARA = Path(__file__).resolve().parents[1] / 'motor' / 'camara_v2_blender.py'


def _compilar(nombres):
    arbol = ast.parse(CAMARA.read_text(encoding='utf-8'))
    cuerpo = [n for n in arbol.body if isinstance(n, ast.FunctionDef) and n.name in nombres]
    if {n.name for n in cuerpo} != set(nombres):
        raise AssertionError('Faltan: ' + ', '.join(sorted(set(nombres) - {n.name for n in cuerpo})))
    modulo = ast.Module(body=cuerpo, type_ignores=[])
    ast.fix_missing_locations(modulo)
    g = {'math': math}
    exec(compile(modulo, str(CAMARA), 'exec'), g)
    return g


class _V:
    __slots__ = ('x', 'y', 'z')

    def __init__(self, x=0.0, y=0.0, z=1.0):
        if isinstance(x, (tuple, list)) and y == 0.0 and z == 1.0 and len(x) == 3:
            self.x, self.y, self.z = float(x[0]), float(x[1]), float(x[2])
        else:
            self.x, self.y, self.z = float(x), float(y), float(z)

    def __sub__(self, other):
        return _V(self.x - other.x, self.y - other.y, self.z - other.z)

    @property
    def length(self):
        return math.sqrt(self.x ** 2 + self.y ** 2 + self.z ** 2)


class _M:
    def __matmul__(self, v):
        if isinstance(v, _V):
            return _V(v.x, v.y, v.z)
        return v


class Tests(unittest.TestCase):
    def test_encuadre_cabeza_llama_region_sin_unbound(self):
        g = _compilar({'region', '_validar_cuadro'})
        llamadas = []

        def region(m, plano):
            llamadas.append(plano)
            return {'cuerpo_entero': False, 'Hf': 0.08, 'bot': 0.0, 'top': 0.5}

        g.update(
            region=region,
            env_bvh=lambda *a, **k: None,
            otros_bvh=lambda *a, **k: None,
            dentro_de_malla=lambda *a, **k: None,
            proyectar=lambda p, *a: (1.5, 1.5),
            CFG={
                'puntos_region': 8,
                'region_en_cuadro_min': 0.6,
                'visibilidad_min': 0.0,
                'holgura_max_m': 0.15,
                'holgura_frac_distancia': 0.1,
                'holgura_frac_altura': 0.25,
                'max_angulo_cara_deg': 90,
                'inclinacion_tolerancia_deg': 15,
                'roll_tolerancia_deg': 15,
            },
            SW={'despeje_escenario': False},
            RIG=type('R', (), {'mirada_relativa': staticmethod(lambda *a: (0.0, 0.0))})(),
            Vector=_V,
            medir=lambda *a, **k: None,
        )
        cabeza = {'puntos_cara': [_V()], 'alto': 0.25, 'centro': _V()}
        spec = {
            'medir': lambda f: {
                'puntos': [_V()],
                'cabeza': cabeza,
                'H': 1.6,
                'tipo': 'personaje',
                'centro': _V(0, 0, 1),
            },
            'plano_de': lambda f: 'CU',
            'revisar_encuadre': True,
            'excluir_oclusion': set(),
            'roll_pedido_deg': 0,
        }
        malos = []
        x = {'loc': _V(0, -2, 1), 'quat': type('Q', (), {'to_matrix': lambda self: _M()})(), 'lente': 35.0}
        g['_validar_cuadro'](x, spec, 10, [], [], malos)
        self.assertGreater(len(llamadas), 0, 'region() debe invocarse')
        self.assertTrue(any('fuera de cuadro' in m[1] for m in malos))
        diag = spec.get('_diag_encuadre') or []
        self.assertEqual(diag[0].get('region_revision'), 'cabeza_cara')

    def test_no_asigna_nombre_region_en_validar_cuadro(self):
        arbol = ast.parse(CAMARA.read_text(encoding='utf-8'))
        for nodo in ast.walk(arbol):
            if isinstance(nodo, ast.FunctionDef) and nodo.name == '_validar_cuadro':
                for sub in ast.walk(nodo):
                    if isinstance(sub, ast.Assign):
                        for t in sub.targets:
                            if isinstance(t, ast.Name) and t.id == 'region':
                                self.fail('asignación a "region" dentro de _validar_cuadro (sombrea la función global)')
                return
        self.fail('no se encontró _validar_cuadro')


if __name__ == '__main__':
    unittest.main(verbosity=2)
