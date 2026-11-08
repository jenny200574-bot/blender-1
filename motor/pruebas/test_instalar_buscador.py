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

MANIFIESTO = ROOT / 'despliegue' / 'manifiesto_buscador.json'
ORIGEN = ROOT / 'motor'
PIN_13 = '99a3acc9cd8f9841608184eb26a56d9ce807f811'
FISICA_SHA = inst.FISICA_SHA


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


class Tests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix='buscador_'))
        self.dest = self.tmp / 'MOTOR_BVH08_CANDIDATO'
        self.dest.mkdir()
        data = json.loads(MANIFIESTO.read_text(encoding='utf-8'))
        self.data = data
        fisica = subprocess.check_output(['git', 'show', '4a8165fc90bd0ab893a4a473a808a29aead3c481:motor_candidato_bvh08/motor/fisica_final.py'])
        self.assertEqual(hashlib.sha256(fisica).hexdigest(), FISICA_SHA)
        out = self.dest / 'motor' / 'fisica_final.py'
        out.parent.mkdir(parents=True)
        out.write_bytes(fisica)
        for item in data['archivos']:
            self.assertEqual(sha(ORIGEN / item['ruta']), item['despues'], item['ruta'])
            if item['antes'] is None:
                self.assertFalse((self.dest / item['ruta']).exists())
                continue
            blob = subprocess.check_output(['git', 'show', PIN_13 + ':motor/' + item['ruta']])
            self.assertEqual(hashlib.sha256(blob).hexdigest(), item['antes'], item['ruta'])
            path = self.dest / item['ruta']
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(blob)

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def test_seco_no_escribe(self):
        antes = sha(self.dest / 'motor' / 'fisica_final.py')
        camara = sha(self.dest / 'motor' / 'camara_v2_blender.py')
        self.assertEqual(inst.main(['--destino', str(self.dest), '--origen', str(ORIGEN), '--manifiesto', str(MANIFIESTO)]), 0)
        self.assertEqual(sha(self.dest / 'motor' / 'fisica_final.py'), antes)
        self.assertEqual(sha(self.dest / 'motor' / 'camara_v2_blender.py'), camara)
        self.assertFalse((self.dest / 'motor' / 'buscador_posicion_camara.py').exists())

    def test_aplicar_y_un_segundo_intento_se_rechaza(self):
        self.assertEqual(inst.main(['--destino', str(self.dest), '--origen', str(ORIGEN), '--manifiesto', str(MANIFIESTO), '--aplicar']), 0)
        self.assertEqual(sha(self.dest / 'motor' / 'fisica_final.py'), FISICA_SHA)
        for item in self.data['archivos']:
            self.assertEqual(sha(self.dest / item['ruta']), item['despues'], item['ruta'])
        self.assertEqual(inst.main(['--destino', str(self.dest), '--origen', str(ORIGEN), '--manifiesto', str(MANIFIESTO), '--aplicar']), 2)
        self.assertEqual(sha(self.dest / 'motor' / 'fisica_final.py'), FISICA_SHA)

    def test_hash_previo_o_fisica_distinta_no_escribe(self):
        camara = self.dest / 'motor' / 'camara_v2_blender.py'
        camara.write_bytes(camara.read_bytes() + b'\n')
        malo = sha(camara)
        self.assertEqual(inst.main(['--destino', str(self.dest), '--origen', str(ORIGEN), '--manifiesto', str(MANIFIESTO), '--aplicar']), 2)
        self.assertEqual(sha(camara), malo)
        camara.write_bytes(subprocess.check_output(['git', 'show', PIN_13 + ':motor/motor/camara_v2_blender.py']))
        fisica = self.dest / 'motor' / 'fisica_final.py'
        fisica.write_bytes(b'otra fisica\n')
        self.assertEqual(inst.main(['--destino', str(self.dest), '--origen', str(ORIGEN), '--manifiesto', str(MANIFIESTO), '--aplicar']), 2)
        self.assertEqual(fisica.read_bytes(), b'otra fisica\n')
        self.assertFalse((self.dest / 'motor' / 'buscador_posicion_camara.py').exists())


if __name__ == '__main__':
    unittest.main(verbosity=2)
