"""Progreso/tope/cancelación de la cámara y validación de la salida del constructor. Sin Blender."""
import hashlib
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'motor'))
import progreso_camara as PC  # noqa: E402
import validar_salida_constructor as VS  # noqa: E402


class Reloj:
    def __init__(self):
        self.t = 0.0

    def __call__(self):
        return self.t


class Progreso(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix='prog_'))
        self.lineas = []
        self.reloj = Reloj()

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def nuevo(self, **k):
        return PC.Progreso(self.tmp, reloj=self.reloj, pared=lambda: 0.0, imprimir=lambda s, flush=False: self.lineas.append(s), **k)

    def test_escribe_json_atomico_y_linea(self):
        p = self.nuevo()
        p.marcar(forzar=True, fase='toma', toma='toma01')
        d = json.loads((self.tmp / 'progreso_camara.json').read_text(encoding='utf-8'))
        self.assertEqual((d['fase'], d['toma'], d['estado']), ('toma', 'toma01', 'EN_CURSO'))
        self.assertTrue(self.lineas[-1].startswith('CAMARA_PROGRESO '))
        self.assertFalse(list(self.tmp.glob('*.parcial')))

    def test_limita_frecuencia_y_limpia_contadores_de_fase(self):
        p = self.nuevo(cada_s=5)
        p.marcar(forzar=True, fase='validacion', candidato=3)
        self.assertFalse(p.marcar(fase='validacion', candidato=4))
        self.reloj.t = 6
        self.assertTrue(p.marcar(fase='hornear'))
        self.assertNotIn('candidato', p.estado)

    def test_tope_y_cancelacion_cortan_sin_ser_exception(self):
        p = self.nuevo(limite_s=10)
        self.reloj.t = 11
        with self.assertRaises(PC.CamaraInterrumpida) as ctx:
            p.marcar(fase='x')
        self.assertEqual(ctx.exception.codigo, 'CAMARA_TIEMPO_AGOTADO')
        self.assertFalse(isinstance(ctx.exception, Exception))
        marca = self.tmp / 'CANCELAR'
        marca.write_text('')
        q = self.nuevo(cancelar=marca)
        with self.assertRaises(PC.CamaraInterrumpida) as ctx:
            q.marcar(fase='x')
        self.assertEqual(ctx.exception.codigo, 'CANCELADO')

    def test_limite_desde_entorno(self):
        self.assertIsNone(PC.limite_desde_entorno({}))
        self.assertEqual(PC.limite_desde_entorno({PC.ENV_LIMITE: '90'}), 90.0)
        for malo in ('0', '-1', 'nan', 'diez'):
            with self.assertRaises(ValueError):
                PC.limite_desde_entorno({PC.ENV_LIMITE: malo})


class SalidaConstructor(unittest.TestCase):
    def setUp(self):
        self.out = Path(tempfile.mkdtemp(prefix='salida_'))
        blend = self.out / 'escena.blend'
        blend.write_bytes(b'BLENDER-v402' + b'\0' * 64)
        sha = hashlib.sha256(blend.read_bytes()).hexdigest()
        self.escribir('worker_resultado.json', {'estado': 'CONSTRUIDO_REVISADO', 'blend_sha256': sha})
        self.escribir('revision_final.json', {'all_passed': True, 'errors': []})
        self.escribir('etapas_worker.json', {k: {} for k in VS.ETAPAS})
        self.escribir('progreso_worker.json', {'estado': 'TERMINADO', 'etapa': '14'})
        (self.out / 'auditoria_4g').mkdir()
        self.escribir('auditoria_4g/camara_v2.json', {'resumen': {'pasa': [1], 'bloqueada': []}, 'faltantes': [], 'production_approved': False})

    def tearDown(self):
        shutil.rmtree(self.out)

    def escribir(self, rel, data):
        (self.out / rel).write_text(json.dumps(data), encoding='utf-8')

    def test_salida_completa_es_ok(self):
        self.assertTrue(VS.validar(self.out)['ok'], VS.validar(self.out)['motivos'])

    def test_cada_hueco_es_rechazo(self):
        casos = {
            'etapa 11 sin recibo': lambda: self.escribir('etapas_worker.json', {k: {} for k in VS.ETAPAS if k != '11'}),
            'blend alterado': lambda: (self.out / 'escena.blend').write_bytes(b'BLENDER-otro'),
            'blend no es blender': lambda: (self.out / 'escena.blend').write_bytes(b'hola'),
            'guardado a medias': lambda: (self.out / 'escena_parcial_guardando.blend').write_bytes(b'x'),
            'revision con errores': lambda: self.escribir('revision_final.json', {'all_passed': False, 'errors': [{}]}),
            'toma bloqueada': lambda: self.escribir('auditoria_4g/camara_v2.json', {'resumen': {'bloqueada': [2]}, 'faltantes': [], 'production_approved': False}),
            'worker bloqueado': lambda: self.escribir('worker_resultado.json', {'estado': 'BLOQUEADO', 'codigo': 'CANCELADO'}),
            'progreso en curso': lambda: self.escribir('progreso_worker.json', {'estado': 'EN_CURSO', 'etapa': '11'}),
        }
        for nombre, romper in casos.items():
            with self.subTest(nombre):
                self.setUp()
                romper()
                self.assertFalse(VS.validar(self.out)['ok'], nombre)


if __name__ == '__main__':
    unittest.main(verbosity=2)
