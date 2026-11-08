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
import preparar_stage_avance11 as st

FISICA = '3423c9a777eb0157d49eb90869f39227fb7cf834322e2705a605a37a66d418d2'
ORO = ROOT / 'motor' / 'paquetes' / 'regresion_orden_explicito' / 'entrada_escena.json'


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


class Tests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix='stage11_'))
        self.origen = self.tmp / 'avance10' / 'MOTOR_BVH08_CANDIDATO'
        self.origen.mkdir(parents=True)
        fisica = subprocess.check_output(['git', 'show', '4a8165fc90bd0ab893a4a473a808a29aead3c481:motor_candidato_bvh08/motor/fisica_final.py'])
        self.assertEqual(hashlib.sha256(fisica).hexdigest(), FISICA)
        (self.origen / 'motor').mkdir()
        (self.origen / 'motor' / 'fisica_final.py').write_bytes(fisica)
        manifiesto = json.loads((ROOT / 'despliegue' / 'manifiesto_13.json').read_text(encoding='utf-8'))
        for item in manifiesto['archivos']:
            if item['antes'] is None:
                continue
            blob = subprocess.check_output(['git', 'show', '5e65c123288901682a8305ed18ddb9dfb77b9721:motor/' + item['ruta']])
            self.assertEqual(hashlib.sha256(blob).hexdigest(), item['antes'], item['ruta'])
            path = self.origen / item['ruta']
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(blob)
        (self.origen / 'motor_unico.py').write_bytes((ROOT / 'motor' / 'motor_unico.py').read_bytes())
        (self.origen / 'config').mkdir()
        (self.origen / 'config' / 'politica_ejecucion.json').write_text('{"presupuesto_total_usd":3,"argon_automatico":false}\n', encoding='utf-8')
        (self.origen / 'evidencia').mkdir()
        (self.origen / 'archivo').mkdir()
        (self.origen / 'respaldos').mkdir()
        (self.origen / 'evidencia' / 'no_leer.bin').write_bytes(b'E' * 100000)
        (self.origen / 'archivo' / 'no_leer.bin').write_bytes(b'A' * 100000)
        self.marca = sha(self.origen / 'evidencia' / 'no_leer.bin')
        self.dest = self.tmp / 'avance11_20261108_pr4'

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def test_oro_no_copia_evidencia_ni_escribe_el_origen(self):
        antes = sha(self.origen / 'motor' / 'fisica_final.py')
        codigo = st.main(['--origen-motor', str(self.origen), '--destino', str(self.dest), '--entrada-oro', str(ORO), '--referencia-oro', str(ROOT / 'motor' / 'config' / 'politica_ejecucion.json'), '--copiar'])
        self.assertEqual(codigo, 0)
        self.assertEqual(sha(self.origen / 'motor' / 'fisica_final.py'), antes)
        self.assertEqual(sha(self.origen / 'evidencia' / 'no_leer.bin'), self.marca)
        self.assertFalse((self.dest / 'MOTOR_BVH08_CANDIDATO' / 'evidencia').exists())
        self.assertFalse((self.dest / 'MOTOR_BVH08_CANDIDATO' / 'archivo').exists())
        self.assertFalse((self.dest / 'MOTOR_BVH08_CANDIDATO' / 'respaldos').exists())
        self.assertFalse((self.dest / 'entradas' / 'oro' / 'archivo').exists())
        self.assertTrue((self.dest / 'entradas' / 'oro' / 'entrada.json').is_file())
        raiz = self.dest / 'entradas' / 'oro' / 'entrada_escena.json'
        self.assertTrue(raiz.is_file())
        self.assertEqual(sha(raiz), sha(ORO))
        self.assertTrue((self.dest / 'MOTOR_BVH08_CANDIDATO' / 'pruebas' / 'test_malla_cabeza.py').is_file())
        for path in (self.dest / 'MOTOR_BVH08_CANDIDATO').rglob('*'):
            if path.is_file():
                self.assertFalse(path.is_symlink())
                self.assertEqual(path.stat().st_nlink, 1)
        self.assertEqual(sha(self.dest / 'MOTOR_BVH08_CANDIDATO' / 'motor' / 'fisica_final.py'), FISICA)

    def test_escena_sin_set_blend_no_copia(self):
        escena = self.tmp / 'escena'
        escena.mkdir()
        data = json.loads((ROOT / 'escenas' / 'guardianes_esc1_candidata' / 'entrada_escena.json').read_text(encoding='utf-8'))
        data['assets'] = [a for a in data['assets'] if a['path'] in ('entrada.json', 'set.blend')]
        (escena / 'entrada_escena.json').write_text(json.dumps(data), encoding='utf-8')
        (escena / 'entrada.json').write_text('{}', encoding='utf-8')
        codigo = st.main(['--origen-motor', str(self.origen), '--destino', str(self.dest), '--entrada-escena', str(escena / 'entrada_escena.json'), '--copiar'])
        self.assertEqual(codigo, 2)
        self.assertFalse((self.dest / 'MOTOR_BVH08_CANDIDATO').exists())

    def test_destino_avance10_se_rechaza(self):
        malo = self.tmp / 'avance10_20261108' / 'nuevo'
        with self.assertRaises(SystemExit):
            st.exigir_separados(self.origen, malo)

    def test_asset_archivo_de_la_entrada_si_se_copia_y_el_de_la_raiz_no(self):
        escena = self.tmp / 'escena2'
        escena.mkdir()
        (escena / 'archivo').mkdir()
        (escena / 'archivo' / 'nota.json').write_text('{"ok":true}\n', encoding='utf-8')
        (escena / 'entrada_escena.json').write_text(json.dumps({'assets': [{'path': 'archivo/nota.json', 'sha256': sha(escena / 'archivo' / 'nota.json'), 'bytes': (escena / 'archivo' / 'nota.json').stat().st_size}]}), encoding='utf-8')
        codigo = st.main(['--origen-motor', str(self.origen), '--destino', str(self.dest), '--entrada-escena', str(escena / 'entrada_escena.json'), '--copiar'])
        self.assertEqual(codigo, 0)
        self.assertTrue((self.dest / 'entradas' / 'escena' / 'archivo' / 'nota.json').is_file())
        self.assertEqual(sha(self.dest / 'entradas' / 'escena' / 'entrada_escena.json'), sha(escena / 'entrada_escena.json'))
        self.assertFalse((self.dest / 'MOTOR_BVH08_CANDIDATO' / 'archivo').exists())

    def test_stage_completo_pasa_el_instalador_en_seco(self):
        import instalar_parche_avance10 as inst
        escena = self.tmp / 'escena_ok'
        escena.mkdir()
        (escena / 'entrada.json').write_text('{}\n', encoding='utf-8')
        (escena / 'entrada_escena.json').write_text(json.dumps({'assets': [{'path': 'entrada.json', 'sha256': sha(escena / 'entrada.json'), 'bytes': (escena / 'entrada.json').stat().st_size}]}), encoding='utf-8')
        otro = self.tmp / 'runtime_1145'
        codigo = st.main(['--origen-motor', str(self.origen), '--destino', str(otro), '--entrada-oro', str(ORO), '--entrada-escena', str(escena / 'entrada_escena.json'), '--referencia-oro', str(ROOT / 'motor' / 'config' / 'politica_ejecucion.json'), '--copiar'])
        self.assertEqual(codigo, 0)
        self.assertEqual(sha(otro / 'entradas' / 'oro' / 'entrada_escena.json'), sha(ORO))
        self.assertEqual(sha(otro / 'entradas' / 'escena' / 'entrada_escena.json'), sha(escena / 'entrada_escena.json'))
        motor = otro / 'MOTOR_BVH08_CANDIDATO'
        self.assertTrue((motor / 'pruebas' / 'test_malla_cabeza.py').is_file())
        self.assertFalse((motor / 'pruebas' / 'test_cargar_modulo_motor.py').exists())
        self.assertFalse((motor / 'motor' / 'compatibilidad_artefacto.py').exists())
        self.assertEqual(sha(motor / 'motor' / 'fisica_final.py'), FISICA)
        self.assertEqual(inst.main(['--destino', str(motor), '--origen', str(ROOT / 'motor'), '--manifiesto', str(ROOT / 'despliegue' / 'manifiesto_13.json')]), 0)
        # Segunda pasada: no pisa lo ya copiado y el origen sigue igual.
        marca = sha(self.origen / 'motor' / 'fisica_final.py')
        self.assertEqual(st.main(['--origen-motor', str(self.origen), '--destino', str(otro), '--entrada-oro', str(ORO), '--entrada-escena', str(escena / 'entrada_escena.json'), '--referencia-oro', str(ROOT / 'motor' / 'config' / 'politica_ejecucion.json'), '--copiar']), 0)
        self.assertEqual(sha(self.origen / 'motor' / 'fisica_final.py'), marca)
        self.assertTrue((otro / 'manifiesto_stage.json').is_file())
        self.assertTrue((otro / 'manifiesto_stage_completar.json').is_file())


if __name__ == '__main__':
    unittest.main(verbosity=2)
