import json
import tempfile
import unittest
from pathlib import Path

import sys
R = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(R / 'motor'))
from progreso_fisica import Progreso


class Tests(unittest.TestCase):
    def test_escribe_json_atomico(self):
        with tempfile.TemporaryDirectory() as tmp:
            sal = Path(tmp)
            p = Progreso(sal, cada_s=0.0)
            p.marcar(forzar=True, fase='prueba', cuadro=1)
            data = json.loads((sal / 'progreso_fisica.json').read_text(encoding='utf-8'))
            self.assertEqual(data['fase'], 'prueba')
            self.assertEqual(data['cuadro'], 1)


if __name__ == '__main__':
    unittest.main(verbosity=2)
