import sys, unittest
from pathlib import Path
R = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(R / 'motor'))
from curvas_accion import curvas_de_accion, fijar_constante

class Punto:
    def __init__(self):
        self.interpolation = 'BEZIER'

class Curva:
    def __init__(self, n=2):
        self.keyframe_points = [Punto() for _ in range(n)]

class Bolsa:
    def __init__(self):
        self.fcurves = [Curva()]

class Tira:
    def __init__(self, bolsa):
        self._bolsa = bolsa
    def channelbag(self, slot):
        return self._bolsa if slot == 'slot' else None

class Capa:
    def __init__(self, bolsa):
        self.strips = [Tira(bolsa)]

class Accion44:
    def __init__(self):
        self.slots = ['slot']
        self.layers = [Capa(Bolsa())]
        self.fcurves = [Curva(1)]

class Accion42:
    def __init__(self):
        self.fcurves = [Curva(3)]

class Tests(unittest.TestCase):
    def test_42_usa_fcurves_si_no_hay_layers(self):
        accion = Accion42()
        self.assertEqual(len(curvas_de_accion(accion)), 1)
        self.assertEqual(fijar_constante(accion), 3)
        self.assertTrue(all(p.interpolation == 'CONSTANT' for c in accion.fcurves for p in c.keyframe_points))

    def test_44_usa_layers_aunque_exista_fcurves(self):
        accion = Accion44()
        curvas = curvas_de_accion(accion)
        self.assertEqual(curvas, accion.layers[0].strips[0]._bolsa.fcurves)
        self.assertNotEqual(curvas, accion.fcurves)
        self.assertEqual(fijar_constante(accion), 2)
        self.assertEqual(accion.fcurves[0].keyframe_points[0].interpolation, 'BEZIER')

    def test_sin_api_no_inventa(self):
        with self.assertRaises(ValueError) as ctx:
            curvas_de_accion(object())
        self.assertIn('fcurves', str(ctx.exception))

if __name__ == '__main__':
    unittest.main(verbosity=2)
