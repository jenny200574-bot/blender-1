import sys
import tempfile
import unittest
import importlib.util
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _heredado_dir():
    for p in (ROOT / 'motor' / 'motor' / 'heredado', ROOT / 'motor' / 'heredado'):
        if (p / 'cargar_modulo_motor.py').is_file():
            return p
    raise FileNotFoundError('No está cargar_modulo_motor.py en motor/motor/heredado ni motor/heredado')


def _modulo_malla():
    for p in (ROOT / 'motor' / 'motor' / 'malla_cabeza.py', ROOT / 'motor' / 'malla_cabeza.py'):
        if p.is_file():
            return p
    raise FileNotFoundError('malla_cabeza.py')


HEREDADO = _heredado_dir()
sys.path.insert(0, str(HEREDADO))
from cargar_modulo_motor import cargar


class Tests(unittest.TestCase):
    def test_carga_el_modulo_unico_aunque_sys_path_sea_solo_heredado(self):
        self.assertEqual(Path(sys.path[0]).resolve(), HEREDADO.resolve())
        modulo = cargar('malla_cabeza')
        cargado = Path(modulo.__file__).resolve()
        esperados = {(ROOT / 'motor' / 'malla_cabeza.py').resolve(), (ROOT / 'motor' / 'motor' / 'malla_cabeza.py').resolve()}
        self.assertIn(cargado, esperados)
        self.assertEqual(modulo.desplazar_cabeza([(0, 0, 0)], 2), [(0, 1.0, 0)])

    def test_encuentra_modulo_cuando_heredado_y_modulos_comparten_padre(self):
        base = Path(tempfile.mkdtemp(prefix='cargar_layout_'))
        pkg = base / 'motor'
        (pkg / 'heredado').mkdir(parents=True)
        shutil.copy2(_modulo_malla(), pkg / 'malla_cabeza.py')
        shutil.copy2(HEREDADO / 'cargar_modulo_motor.py', pkg / 'heredado' / 'cargar_modulo_motor.py')
        spec = importlib.util.spec_from_file_location('cargar_modulo_aislado', pkg / 'heredado' / 'cargar_modulo_motor.py')
        cm = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cm)
        modulo = cm.cargar('malla_cabeza')
        self.assertEqual(Path(modulo.__file__).resolve(), (pkg / 'malla_cabeza.py').resolve())

    def test_no_usa_decoy_en_heredado(self):
        """Aunque exista malla_cabeza.py bajo heredado/, cargar() debe usar el módulo canónico vecino."""
        base = Path(tempfile.mkdtemp(prefix='cargar_decoy_'))
        pkg = base / 'motor'
        (pkg / 'heredado').mkdir(parents=True)
        (pkg / 'heredado' / 'malla_cabeza.py').write_text('raise RuntimeError("decoy")\n', encoding='utf-8')
        shutil.copy2(_modulo_malla(), pkg / 'malla_cabeza.py')
        shutil.copy2(HEREDADO / 'cargar_modulo_motor.py', pkg / 'heredado' / 'cargar_modulo_motor.py')
        spec = importlib.util.spec_from_file_location('cargar_modulo_decoy', pkg / 'heredado' / 'cargar_modulo_motor.py')
        cm = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cm)
        modulo = cm.cargar('malla_cabeza')
        self.assertEqual(Path(modulo.__file__).resolve(), (pkg / 'malla_cabeza.py').resolve())

    def test_no_acepta_modulo_inexistente(self):
        with self.assertRaises(ModuleNotFoundError) as ctx:
            cargar('modulo_que_no_esta')
        esperado = (ROOT / 'motor' / 'malla_cabeza.py').parent / 'modulo_que_no_esta.py'
        if not esperado.is_file():
            esperado = (ROOT / 'motor' / 'motor' / 'modulo_que_no_esta.py')
        self.assertIn('modulo_que_no_esta', str(ctx.exception))
        self.assertIn('No se usa una copia', str(ctx.exception))

    def test_el_rig_no_importa_malla_cabeza_por_nombre(self):
        texto = (HEREDADO / 'rig.py').read_text(encoding='utf-8')
        self.assertNotIn('from malla_cabeza import', texto)
        self.assertIn("cargar_modulo_motor('malla_cabeza')", texto)

    def test_el_constructor_rechaza_el_reuso_antes_de_abrir_el_blend(self):
        texto = (ROOT / 'motor' / 'constructor_final.py').read_text(encoding='utf-8')
        self.assertLess(texto.index('exigir_paquete'), texto.index('open_mainfile'))
        self.assertLess(texto.index('exigir_nucleo'), texto.index('open_mainfile'))


if __name__ == '__main__':
    unittest.main(verbosity=2)
