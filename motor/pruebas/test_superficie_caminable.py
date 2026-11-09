"""Alfombra sobre piso: elección de Z de apoyo."""
import sys
import unittest
from pathlib import Path

R = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(R / 'motor'))
from superficie_caminable import elegir_apoyo_xy, es_superficie_caminable


class Tests(unittest.TestCase):
    def test_detecta_alfombra(self):
        self.assertTrue(es_superficie_caminable('av07.rug.main'))
        self.assertFalse(es_superficie_caminable('muro_fondo_1'))

    def test_preferir_z_mas_alta(self):
        cands = [
            {'nombre': 'piso', 'z_top': 0.0, 'caminable': False},
            {'nombre': 'av07.rug.main', 'z_top': 0.03, 'caminable': True},
        ]
        mejor = elegir_apoyo_xy((0.5, 0.5), cands)
        self.assertEqual(mejor['nombre'], 'av07.rug.main')


if __name__ == '__main__':
    unittest.main(verbosity=2)
