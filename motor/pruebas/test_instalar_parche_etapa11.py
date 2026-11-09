"""Instalador del parche de etapa 11: seco, aplicar con respaldo, rechazo por hash y reversión sin borrar.

Arma un destino falso con los previos exactos de 3d1653a (git) y la física del candidato.
Sin git no puede reconstruir los previos y lo dice en vez de pasar.
"""
import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / 'despliegue'))
import instalar_parche_etapa11 as inst  # noqa: E402

ORIGEN = REPO / 'motor'
MANIFIESTO = REPO / 'despliegue' / 'manifiesto_etapa11.json'


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def git_show(ref):
    return subprocess.run(['git', '-C', str(REPO), 'show', ref], capture_output=True, check=True).stdout


class Instalador(unittest.TestCase):
    def setUp(self):
        try:
            git_show('3d1653a:motor/motor/camara_v2_blender.py')
        except (OSError, subprocess.CalledProcessError):
            self.skipTest('sin git no se reconstruyen los previos de 3d1653a')
        self.tmp = Path(tempfile.mkdtemp(prefix='etapa11_'))
        self.dest = self.tmp / 'MOTOR_BVH08_CANDIDATO'
        fis = git_show('4a8165fc90bd0ab893a4a473a808a29aead3c481:motor_candidato_bvh08/motor/fisica_final.py')
        self.assertEqual(hashlib.sha256(fis).hexdigest(), inst.FISICA_SHA)
        (self.dest / 'motor').mkdir(parents=True)
        (self.dest / 'motor' / 'fisica_final.py').write_bytes(fis)
        for ruta in inst.PREVIOS:
            (self.dest / ruta).write_bytes(git_show('3d1653a:motor/' + ruta))
        (self.dest / 'pruebas').mkdir()
        (self.dest / 'pruebas' / 'test_buscador_posicion_camara.py').write_bytes(git_show('1611c56:motor/pruebas/test_buscador_posicion_camara.py'))
        self.args = ['--destino', str(self.dest), '--origen', str(ORIGEN), '--manifiesto', str(MANIFIESTO)]

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def test_manifiesto_coincide_con_el_repo_y_los_previos_instalados(self):
        data = json.loads(MANIFIESTO.read_text(encoding='utf-8'))
        self.assertEqual(data, inst.generar(ORIGEN))
        for ruta, antes in inst.PREVIOS.items():
            self.assertEqual(sha(self.dest / ruta), antes, ruta)
        self.assertNotIn('pruebas/test_buscador_posicion_camara.py', [x['ruta'] for x in data['archivos']])

    def test_seco_aplicar_revertir(self):
        test_local = sha(self.dest / 'pruebas' / 'test_buscador_posicion_camara.py')
        self.assertEqual(inst.main(self.args), 0)
        self.assertEqual(sha(self.dest / 'motor' / 'camara_v2_blender.py'), inst.PREVIOS['motor/camara_v2_blender.py'])
        respaldo = self.tmp / 'respaldo'
        self.assertEqual(inst.main(self.args + ['--aplicar', '--respaldo', str(respaldo)]), 0)
        data = json.loads(MANIFIESTO.read_text(encoding='utf-8'))
        for x in data['archivos']:
            self.assertEqual(sha(self.dest / x['ruta']), x['despues'], x['ruta'])
        self.assertTrue((self.dest / 'motor' / 'camara_lotes_por_cuadro.off').is_file())
        self.assertEqual(sha(self.dest / 'pruebas' / 'test_buscador_posicion_camara.py'), test_local)
        self.assertEqual(sha(self.dest / 'motor' / 'fisica_final.py'), inst.FISICA_SHA)
        self.assertEqual(inst.main(self.args), 2)
        self.assertEqual(inst.main(['--destino', str(self.dest), '--manifiesto', str(MANIFIESTO), '--revertir', '--respaldo', str(respaldo)]), 0)
        for ruta, antes in inst.PREVIOS.items():
            self.assertEqual(sha(self.dest / ruta), antes)
        self.assertFalse((self.dest / 'motor' / 'progreso_camara.py').exists())
        self.assertTrue((respaldo / 'retirados' / 'motor' / 'progreso_camara.py').is_file())

    def test_hash_previo_ajeno_rechaza_sin_escribir(self):
        (self.dest / 'motor' / 'constructor_final.py').write_text('# otro\n', encoding='utf-8')
        self.assertEqual(inst.main(self.args + ['--aplicar', '--respaldo', str(self.tmp / 'r')]), 2)
        self.assertFalse((self.dest / 'motor' / 'progreso_camara.py').exists())
        self.assertFalse((self.tmp / 'r').exists())

    def test_no_acepta_manifiesto_que_toca_protegidos(self):
        data = json.loads(MANIFIESTO.read_text(encoding='utf-8'))
        for ruta in ('motor/heredado/rig.py', 'motor/malla_cabeza.py', 'motor/fisica_final.py'):
            otro = dict(data, archivos=data['archivos'] + [{'ruta': ruta, 'antes': None, 'despues': '0' * 64, 'bytes': 1}])
            m = self.tmp / 'm.json'
            m.write_text(json.dumps(otro), encoding='utf-8')
            with self.assertRaises(SystemExit):
                inst.cargar(m)


if __name__ == '__main__':
    unittest.main(verbosity=2)
