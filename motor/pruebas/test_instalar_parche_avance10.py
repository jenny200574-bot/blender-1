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
import instalar_parche_avance10 as inst

MANIFIESTO = ROOT / 'despliegue' / 'manifiesto_13.json'
PIN_13 = '99a3acc9cd8f9841608184eb26a56d9ce807f811'
FISICA_SHA = inst.FISICA_SHA


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


class Tests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix='instalar_'))
        self.dest = self.tmp / 'MOTOR_BVH08_CANDIDATO'
        self.dest.mkdir()
        data = json.loads(MANIFIESTO.read_text(encoding='utf-8'))
        self.data = data
        fisica = subprocess.check_output(['git', 'show', '4a8165fc90bd0ab893a4a473a808a29aead3c481:motor_candidato_bvh08/motor/fisica_final.py'])
        self.assertEqual(hashlib.sha256(fisica).hexdigest(), FISICA_SHA)
        out = self.dest / 'motor' / 'fisica_final.py'
        out.parent.mkdir(parents=True)
        out.write_bytes(fisica)
        self.origen = self.tmp / 'origen13'
        for item in data['archivos']:
            nuevo = subprocess.check_output(['git', 'show', PIN_13 + ':motor/' + item['ruta']])
            self.assertEqual(hashlib.sha256(nuevo).hexdigest(), item['despues'], item['ruta'])
            path = self.origen / item['ruta']
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(nuevo)
            if item['antes'] is None:
                continue
            previo = subprocess.check_output(['git', 'show', '5e65c123288901682a8305ed18ddb9dfb77b9721:motor/' + item['ruta']])
            self.assertEqual(hashlib.sha256(previo).hexdigest(), item['antes'], item['ruta'])
            dst = self.dest / item['ruta']
            dst.parent.mkdir(parents=True, exist_ok=True)
            dst.write_bytes(previo)

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def test_seco_no_escribe_y_deja_la_fisica(self):
        antes = sha(self.dest / 'motor' / 'fisica_final.py')
        rig = sha(self.dest / 'motor' / 'heredado' / 'rig.py')
        self.assertEqual(inst.main(['--destino', str(self.dest), '--origen', str(self.origen), '--manifiesto', str(MANIFIESTO)]), 0)
        self.assertEqual(sha(self.dest / 'motor' / 'fisica_final.py'), antes)
        self.assertEqual(sha(self.dest / 'motor' / 'heredado' / 'rig.py'), rig)
        self.assertFalse((self.dest / 'motor' / 'compatibilidad_artefacto.py').exists())

    def test_aplicar_solo_cambia_los_13_y_no_la_fisica(self):
        self.assertEqual(inst.main(['--destino', str(self.dest), '--origen', str(self.origen), '--manifiesto', str(MANIFIESTO), '--aplicar']), 0)
        self.assertEqual(sha(self.dest / 'motor' / 'fisica_final.py'), FISICA_SHA)
        for item in self.data['archivos']:
            self.assertEqual(sha(self.dest / item['ruta']), item['despues'], item['ruta'])
        self.assertEqual(inst.main(['--destino', str(self.dest), '--origen', str(self.origen), '--manifiesto', str(MANIFIESTO), '--aplicar']), 2)

    def test_hash_previo_distinto_no_escribe(self):
        rig = self.dest / 'motor' / 'heredado' / 'rig.py'
        rig.write_bytes(rig.read_bytes() + b'\n')
        malo = sha(rig)
        self.assertEqual(inst.main(['--destino', str(self.dest), '--origen', str(self.origen), '--manifiesto', str(MANIFIESTO), '--aplicar']), 2)
        self.assertEqual(sha(rig), malo)
        self.assertEqual(sha(self.dest / 'motor' / 'fisica_final.py'), FISICA_SHA)
        self.assertFalse((self.dest / 'motor' / 'compatibilidad_artefacto.py').exists())

    def test_archivo_nuevo_ya_presente_y_fisica_cambiada_rechazan(self):
        nuevo = self.dest / 'motor' / 'compatibilidad_artefacto.py'
        nuevo.write_text('distinto\n', encoding='utf-8')
        self.assertEqual(inst.main(['--destino', str(self.dest), '--origen', str(self.origen), '--manifiesto', str(MANIFIESTO)]), 2)
        self.assertEqual(nuevo.read_text(encoding='utf-8'), 'distinto\n')
        nuevo.unlink()
        fisica = self.dest / 'motor' / 'fisica_final.py'
        fisica.write_bytes(b'otra fisica\n')
        self.assertEqual(inst.main(['--destino', str(self.dest), '--origen', str(self.origen), '--manifiesto', str(MANIFIESTO), '--aplicar']), 2)
        self.assertEqual(fisica.read_bytes(), b'otra fisica\n')

    def test_manifiesto_con_fisica_no_se_acepta(self):
        malo = self.tmp / 'malo.json'
        data = json.loads(MANIFIESTO.read_text(encoding='utf-8'))
        data['archivos'][0]['ruta'] = 'motor/fisica_final.py'
        malo.write_text(json.dumps(data), encoding='utf-8')
        with self.assertRaises(SystemExit):
            inst.cargar(malo)


if __name__ == '__main__':
    unittest.main(verbosity=2)
