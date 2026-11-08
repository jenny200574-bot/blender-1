import sys, unittest
from pathlib import Path
R = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(R / 'motor'))
from medir_objetivo_camara import SENSOR_ANCHO_MM_APROBADO, puntos_de_objetivo, sensor_ancho_mm

HIJO = [(0.0, 0.0, 0.0), (0.2, 0.0, 1.4), (0.0, 0.1, 0.7)]
CAJA = [(1.0, 2.0, 0.0), (1.4, 2.0, 0.0), (1.0, 2.3, 0.0), (1.4, 2.3, 0.0), (1.0, 2.0, 1.6), (1.4, 2.0, 1.6), (1.0, 2.3, 1.6), (1.4, 2.3, 1.6)]

class Tests(unittest.TestCase):
    def test_malla_propia_no_mezcla_hijos_ni_caja(self):
        propios = [(0.0, 0.0, 0.1), (0.0, 0.0, 1.0)]
        pts = puntos_de_objetivo('ch-eco', 'toma01', propios, [HIJO], CAJA)
        self.assertEqual(pts, [(0.0, 0.0, 0.1), (0.0, 0.0, 1.0)])

    def test_sin_vertices_propios_usa_hijos(self):
        pts = puntos_de_objetivo('ch-eco', 'toma01', [], [HIJO], CAJA)
        self.assertEqual(pts, HIJO)
        self.assertEqual(min(p[2] for p in pts), 0.0)
        self.assertEqual(max(p[2] for p in pts), 1.4)

    def test_sin_mallas_usa_bounding_box_del_mundo(self):
        pts = puntos_de_objetivo('vacio-armature', 'toma03', [], [[], []], CAJA)
        self.assertEqual(pts, CAJA)

    def test_vacio_total_nombra_objeto_y_toma(self):
        with self.assertRaises(ValueError) as ctx:
            puntos_de_objetivo('marca_vacia', 'toma02', [], [], [])
        msg = str(ctx.exception)
        self.assertIn('marca_vacia', msg)
        self.assertIn('toma02', msg)
        self.assertIn('No se inventa', msg)

    def test_bbox_degenerada_no_inventa_posicion(self):
        mismo = [(3.0, 4.0, 5.0)] * 8
        with self.assertRaises(ValueError) as ctx:
            puntos_de_objetivo('Empty.objetivo', 'toma04', [], None, mismo)
        self.assertIn('Empty.objetivo', str(ctx.exception))
        self.assertIn('toma04', str(ctx.exception))

    def test_nan_no_cuenta_como_vertice(self):
        with self.assertRaises(ValueError):
            puntos_de_objetivo('roto', 'toma05', [(float('nan'), 0.0, 0.0)], [], [(0.0, 0.0, 0.0)] * 8)

    def test_sensor_aprobado_36(self):
        self.assertEqual(SENSOR_ANCHO_MM_APROBADO, 36)
        self.assertEqual(sensor_ancho_mm({'sensor_width_mm': 36}), 36.0)
        self.assertEqual(sensor_ancho_mm({'shots': [{'sensor_width_mm': 36}]}), 36.0)

    def test_sensor_ausente_o_distinto_no_se_inventa(self):
        with self.assertRaises(ValueError):
            sensor_ancho_mm({})
        with self.assertRaises(ValueError):
            sensor_ancho_mm(None)
        with self.assertRaises(ValueError) as ctx:
            sensor_ancho_mm({'sensor_width_mm': 24})
        self.assertIn('36', str(ctx.exception))

if __name__ == '__main__':
    unittest.main(verbosity=2)
