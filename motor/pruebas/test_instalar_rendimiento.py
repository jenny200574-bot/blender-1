import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'despliegue'))
import instalar_parche_buscador as inst

MANIFIESTO = ROOT / 'despliegue' / 'manifiesto_buscador_rendimiento.json'
ORIGEN = ROOT / 'motor'
PIN = '3d1653a'
FISICA_SHA = inst.FISICA_SHA


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


class Tests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix='rendimiento_'))
        self.dest = self.tmp / 'MOTOR_BVH08_CANDIDATO'
        self.dest.mkdir()
        self.data = json.loads(MANIFIESTO.read_text(encoding='utf-8'))
        fisica = subprocess.check_output(['git', 'show', '4a8165fc90bd0ab893a4a473a808a29aead3c481:motor_candidato_bvh08/motor/fisica_final.py'])
        self.assertEqual(hashlib.sha256(fisica).hexdigest(), FISICA_SHA)
        out = self.dest / 'motor' / 'fisica_final.py'
        out.parent.mkdir(parents=True)
        out.write_bytes(fisica)
        for item in self.data['archivos']:
            self.assertEqual(sha(ORIGEN / item['ruta']), item['despues'], item['ruta'])
            blob = subprocess.check_output(['git', 'show', PIN + ':motor/' + item['ruta']])
            self.assertEqual(hashlib.sha256(blob).hexdigest(), item['antes'], item['ruta'])
            path = self.dest / item['ruta']
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(blob)

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def test_seco_no_toca_el_proceso_y_aplicar_deja_la_fisica(self):
        antes = sha(self.dest / 'motor' / 'fisica_final.py')
        self.assertEqual(inst.main(['--destino', str(self.dest), '--origen', str(ORIGEN), '--manifiesto', str(MANIFIESTO)]), 0)
        self.assertEqual(sha(self.dest / 'motor' / 'buscador_posicion_camara.py'), self.data['archivos'][0]['antes'])
        self.assertEqual(inst.main(['--destino', str(self.dest), '--origen', str(ORIGEN), '--manifiesto', str(MANIFIESTO), '--aplicar']), 0)
        self.assertEqual(sha(self.dest / 'motor' / 'fisica_final.py'), antes)
        for item in self.data['archivos']:
            self.assertEqual(sha(self.dest / item['ruta']), item['despues'], item['ruta'])
        self.assertEqual(inst.main(['--destino', str(self.dest), '--origen', str(ORIGEN), '--manifiesto', str(MANIFIESTO), '--aplicar']), 2)


if __name__ == '__main__':
    unittest.main(verbosity=2)
