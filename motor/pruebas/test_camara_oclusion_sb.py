"""R14: oclusión universal por storyboard (sin bpy)."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'motor'))
from camara_oclusion_sb import (
    elegir_a_ocultar,
    puede_ocultar_obstaculo,
    sujetos_protegidos,
    nombres_obstaculo_en_malos,
    reflejar_xy_sobre_eje,
)


class Tests(unittest.TestCase):
    def test_sujetos_protegidos_ots(self):
        S = {'sujetos': ['ch-pintor'], 'ots': ['ch-eco']}
        prot = sujetos_protegidos(S, 'ch-pintor', ('ch-pintor', 'ch-eco', 'obj-cama'))
        self.assertIn('ch-pintor', prot)
        self.assertIn('ch-eco', prot)
        self.assertFalse(puede_ocultar_obstaculo('ch-eco.cuerpo', prot, ('ch-pintor', 'ch-eco')))
        self.assertTrue(puede_ocultar_obstaculo('obj-cama.estructura', prot, ('ch-pintor', 'ch-eco')))

    def test_elegir_excluye_sujeto(self):
        prot = {'ch-pintor'}
        counts = {'muro_frente': 5, 'ch-pintor.mesh': 3, 'obj-cama': 2}
        out = elegir_a_ocultar(counts, prot, ('ch-pintor',))
        self.assertIn('muro_frente', out)
        self.assertNotIn('ch-pintor.mesh', out)

    def test_malos_parse_obj_cama(self):
        mal = [(10, 'sujeto tapado (escenario: obj-cama.cabecero)', 0.4)]
        d = nombres_obstaculo_en_malos(mal)
        self.assertIn('obj-cama.cabecero', d)

    def test_reflejo_xy(self):
        class V:
            def __init__(self, x, y, z=0):
                self.x, self.y, self.z = x, y, z

        class A:
            def __init__(self, x, y):
                self.x, self.y = x, y

        p = reflejar_xy_sobre_eje(V(2, 1), A(0, 0), A(1, 0))
        self.assertAlmostEqual(p.x, 2)
        self.assertAlmostEqual(p.y, -1, places=5)


if __name__ == '__main__':
    unittest.main(verbosity=2)
