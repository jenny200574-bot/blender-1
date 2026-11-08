import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HEREDADO = ROOT / 'motor' / 'heredado'
sys.path.insert(0, str(HEREDADO))
from cargar_modulo_motor import cargar


class Tests(unittest.TestCase):
    def test_carga_el_modulo_unico_aunque_sys_path_sea_solo_heredado(self):
        self.assertEqual(Path(sys.path[0]).resolve(), HEREDADO.resolve())
        modulo = cargar('malla_cabeza')
        self.assertEqual(Path(modulo.__file__).resolve(), (ROOT / 'motor' / 'malla_cabeza.py').resolve())
        self.assertEqual(modulo.desplazar_cabeza([(0, 0, 0)], 2), [(0, 1.0, 0)])

    def test_no_acepta_una_copia_bajo_heredado(self):
        copia = HEREDADO / 'malla_cabeza.py'
        self.assertFalse(copia.exists())
        with self.assertRaises(ModuleNotFoundError) as ctx:
            cargar('modulo_que_no_esta')
        self.assertIn(str((ROOT / 'motor' / 'modulo_que_no_esta.py').resolve()), str(ctx.exception))
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
