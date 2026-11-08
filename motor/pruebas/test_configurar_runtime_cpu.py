import json
import stat
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'despliegue'))
import configurar_runtime_cpu as cfg


def sha(path):
    return __import__('hashlib').sha256(Path(path).read_bytes()).hexdigest()


class Tests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix='rtcpu_'))
        self.stage = self.tmp / 'avance11_20261108_pr4' / 'runtime_1145' / 'MOTOR_BVH08_CANDIDATO' / 'config'
        self.stage.mkdir(parents=True)
        self.config = self.stage / 'runtime_cpu.json'
        self.original = {
            'numeric_python': cfg.RUTA_MUERTA,
            'source': 'Entorno SciPy ya instalado; dependencia técnica, no ruta de escena',
            'gpu': False,
            'semilla': 1,
        }
        self.config.write_text(json.dumps(self.original, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
        self.bueno = self.tmp / 'python_bueno'
        self.bueno.write_text('#!/usr/bin/env python3\nimport json\nprint(json.dumps({"numpy":"1.26.0","scipy":"1.11.0","sparse":True,"splu":True}))\n', encoding='utf-8')
        self.malo = self.tmp / 'python_malo'
        self.malo.write_text('#!/usr/bin/env python3\nimport json\nprint(json.dumps({"numpy":None,"scipy":None,"sparse":False,"splu":False,"numpy_error":"ModuleNotFoundError: numpy"}))\n', encoding='utf-8')
        for path in (self.bueno, self.malo):
            path.chmod(path.stat().st_mode | stat.S_IEXEC)

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmp)

    def test_seco_no_escribe_y_el_malo_no_gana(self):
        antes = self.config.read_bytes()
        codigo = cfg.main(['--config', str(self.config), '--candidato', str(self.malo), '--candidato', str(self.bueno)])
        self.assertEqual(codigo, 0)
        self.assertEqual(self.config.read_bytes(), antes)

    def test_aplicar_solo_cambia_el_python(self):
        codigo = cfg.main(['--config', str(self.config), '--candidato', str(self.bueno), '--aplicar'])
        self.assertEqual(codigo, 0)
        data = json.loads(self.config.read_text(encoding='utf-8'))
        self.assertEqual(data['numeric_python'], str(self.bueno))
        self.assertEqual(data['source'], self.original['source'])
        self.assertIs(data['gpu'], False)
        self.assertEqual(data['semilla'], 1)
        respaldo = next(self.stage.glob('runtime_cpu.json.bak.*'))
        self.assertEqual(json.loads(respaldo.read_text(encoding='utf-8'))['numeric_python'], cfg.RUTA_MUERTA)
        recibo = json.loads((self.stage / 'runtime_cpu_recibo.json').read_text(encoding='utf-8'))
        self.assertEqual(recibo['sha256_antes'], sha(respaldo))
        self.assertEqual(recibo['sha256_despues'], sha(self.config))
        self.assertFalse(recibo['production_approved'])
        self.assertFalse(self.config.is_symlink())

    def test_symlink_y_ruta_muerta_no_se_eligen(self):
        enlace = self.tmp / 'enlace'
        enlace.symlink_to(self.bueno)
        self.assertFalse(cfg.evaluar(enlace)['ok'])
        self.assertFalse(cfg.evaluar(cfg.RUTA_MUERTA)['ok'])
        self.assertEqual(cfg.main(['--config', str(self.config), '--candidato', str(enlace), '--aplicar']), 2)
        self.assertEqual(json.loads(self.config.read_text(encoding='utf-8'))['numeric_python'], cfg.RUTA_MUERTA)

    def test_avance10_se_rechaza(self):
        malo = self.tmp / 'avance10_20261108' / 'MOTOR' / 'config'
        malo.mkdir(parents=True)
        destino = malo / 'runtime_cpu.json'
        destino.write_text(self.config.read_text(encoding='utf-8'), encoding='utf-8')
        with self.assertRaises(SystemExit):
            cfg.exigir_config(destino)

    def test_oro_no_lee_runtime_cpu(self):
        texto = (ROOT / 'motor' / 'motor_unico.py').read_text(encoding='utf-8')
        self.assertNotIn('runtime_cpu', texto)
        orq = (ROOT / 'motor' / 'motor' / 'orquestador.py').read_text(encoding='utf-8')
        pulida = orq.split('def pulida():', 1)[1].split('def camara():', 1)[0]
        self.assertLess(pulida.index('if solo_validar:'), pulida.index('runtime_cpu.json'))
        self.assertLess(pulida.index('runtime_cpu.json'), pulida.index('for i,job in enumerate'))


if __name__ == '__main__':
    unittest.main(verbosity=2)
