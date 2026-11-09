"""Tomas ↔ cuadros y contrato de cinemática en cortes."""
import json
import sys
import unittest
from pathlib import Path

R = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(R / 'motor'))
from continuidad_tomas import cuadro_a_toma, cuadros_inicio_toma, exclusion_cinematica_contrato, indice_tomas
from seguridad import cuadro


class Tests(unittest.TestCase):
    def _mini(self):
        return {
            'clock': {'fps': 24, 'duration_s': 12},
            'camera': {
                'shots': [
                    {'id': 'v1', 't0': 0.0, 't1': 3.0, 'transition': 'CORTE'},
                    {'id': 'v2', 't0': 3.0, 't1': 6.0, 'transition': 'CORTE_SECO'},
                    {'id': 'v3', 't0': 6.0, 't1': 12.0, 'transition': 'CORTE'},
                ],
            },
            'rules': {},
        }

    def test_inicio_toma_y_cortes(self):
        d = self._mini()
        fps = 24
        f2 = cuadro(3.0, fps)
        self.assertIn(f2, cuadros_inicio_toma(d))
        t = cuadro_a_toma(d, f2, fps)
        self.assertEqual(t['id'], 'v2')
        self.assertTrue(t['frame_inicio'])
        t73 = cuadro_a_toma(d, f2 + 1, fps)
        self.assertEqual(t73['id'], 'v2')

    def test_sin_exclusion_por_defecto(self):
        ok, src = exclusion_cinematica_contrato({})
        self.assertFalse(ok)
        self.assertIsNone(src)

    def test_exclusion_solo_si_regla_explicita(self):
        ok, src = exclusion_cinematica_contrato({'cinematic_skip_shot_first_frame': True})
        self.assertTrue(ok)
        self.assertIn('cinematic_skip', src)

    def test_indice_ordenado(self):
        d = self._mini()
        idx = indice_tomas(d)
        self.assertEqual([x['id'] for x in idx], ['v1', 'v2', 'v3'])
        self.assertLessEqual(idx[0]['f1'], idx[1]['f0'])


if __name__ == '__main__':
    unittest.main(verbosity=2)
