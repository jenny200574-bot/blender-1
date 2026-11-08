import hashlib
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'motor'))
from compatibilidad_artefacto import (
    ESQUEMA,
    exigir_nucleo,
    exigir_paquete,
    huella_obj,
    sellar_nucleo,
    sellar_paquete,
)


def _sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _entrada_valida():
    return {
        'props': [{'id': 'libro', 'axis_ids': ['eje-libro']}],
        '_eje_objetos': {'esquema': ESQUEMA, 'ejes': ['eje-libro']},
        '_cabeza_compilada': {'esquema': ESQUEMA, 'entidades': ['persona']},
        'legacy': {'scene': 'x', 'fps': 24},
    }


class Tests(unittest.TestCase):
    def setUp(self):
        self.root = ROOT
        self.tmp = Path(tempfile.mkdtemp(prefix='compatibilidad_'))
        self.paquete = self.tmp / 'paquete_normalizado'
        self.paquete.mkdir(parents=True)
        self.entrada = _entrada_valida()
        (self.paquete / 'entrada_escena.json').write_text(
            json.dumps(self.entrada, ensure_ascii=False, indent=2) + '\n', encoding='utf-8'
        )

    def tearDown(self):
        if self.tmp.exists():
            shutil.rmtree(self.tmp)

    def test_sin_recibo_no_reutiliza_paquete_ni_nucleo(self):
        self.assertEqual(exigir_paquete(self.root, self.paquete)[0]['codigo'], 'FALTA_RECIBO_PAQUETE')
        blend = self.tmp / 'nucleo' / 'escena.blend'
        blend.parent.mkdir()
        blend.write_bytes(b'blend')
        self.assertEqual(exigir_nucleo(self.root, blend, self.entrada['legacy'])[0]['codigo'], 'FALTA_RECIBO_NUCLEO')

    def test_paquete_sellado_solo_si_las_marcas_y_el_codigo_coinciden(self):
        self.assertTrue(sellar_paquete(self.root, self.paquete))
        self.assertEqual(exigir_paquete(self.root, self.paquete), [])
        recibo = json.loads((self.paquete / 'compatibilidad_paquete.json').read_text(encoding='utf-8'))
        self.assertFalse(recibo['produccion_aprobada'])
        recibo['codigo']['motor/malla_cabeza.py'] = '0' * 64
        (self.paquete / 'compatibilidad_paquete.json').write_text(json.dumps(recibo), encoding='utf-8')
        codigos = {m['codigo'] for m in exigir_paquete(self.root, self.paquete)}
        self.assertIn('CODIGO_DISTINTO', codigos)

    def test_entrada_distinta_o_sin_marca_no_se_sella(self):
        crudo = json.loads((self.paquete / 'entrada_escena.json').read_text(encoding='utf-8'))
        del crudo['_eje_objetos']
        (self.paquete / 'entrada_escena.json').write_text(json.dumps(crudo), encoding='utf-8')
        self.assertFalse(sellar_paquete(self.root, self.paquete))
        (self.paquete / 'compatibilidad_paquete.json').write_text('{"esquema":"otro"}', encoding='utf-8')
        codigos = {m['codigo'] for m in exigir_paquete(self.root, self.paquete)}
        self.assertIn('FALTA_MARCA_EJES', codigos)

    def test_nucleo_exige_el_mismo_legacy_y_el_mismo_codigo(self):
        legacy = {'fps': 24, 'scene': 'x'}
        entrada = self.tmp / 'nucleo_seed' / 'entrada.json'
        entrada.parent.mkdir()
        entrada.write_text(json.dumps(legacy), encoding='utf-8')
        blend = self.tmp / 'nucleo' / 'escena.blend'
        blend.parent.mkdir()
        blend.write_bytes(b'blend')
        sellar_nucleo(self.root, blend, entrada)
        self.assertEqual(exigir_nucleo(self.root, blend, legacy), [])
        self.assertEqual(huella_obj(legacy), json.loads((blend.parent / 'compatibilidad_nucleo.json').read_text())['entrada_huella'])
        otros = exigir_nucleo(self.root, blend, {'fps': 12, 'scene': 'x'})
        self.assertEqual(otros[0]['codigo'], 'LEGACY_DISTINTO')
        self.assertTrue(_sha(self.root / 'motor' / 'heredado' / 'rig.py'))


if __name__ == '__main__':
    unittest.main(verbosity=2)
