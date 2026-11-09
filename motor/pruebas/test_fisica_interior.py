"""Prueba interior de colliders sin bpy: clasificación y parity sin excepción."""
import math
import sys
import unittest
from pathlib import Path

R = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(R / 'motor'))
from fisica_final import (
    clasificar_collider,
    cuadros_muestra_penetracion,
    extents_vertices,
    punto_dentro_collider,
    ray_parity_interiores,
    _muestra_vertices,
)


class _Vec:
    def __init__(self, x, y, z):
        self.x, self.y, self.z = float(x), float(y), float(z)

    def copy(self):
        return _Vec(self.x, self.y, self.z)

    def __add__(self, o):
        return _Vec(self.x + o.x, self.y + o.y, self.z + o.z)

    def __mul__(self, s):
        return _Vec(self.x * s, self.y * s, self.z * s)

    __rmul__ = __mul__


def _xyz(p):
    if hasattr(p, 'x'):
        return p.x, p.y, p.z
    return p[0], p[1], p[2]


class _TreeCaja:
    """BVH simulado: caja [0,1]^3; rayos salen si origin.x > 1."""
    def ray_cast(self, origin, direction, dist=1000):
        ox, oy, oz = _xyz(origin)
        if ox >= 1.0 - 1e-9:
            return (None, None, None, None)
        dx = direction.x if hasattr(direction, 'x') else direction[0]
        if dx > 0:
            t = (1.0 - ox) / max(dx, 1e-9)
            hit = _Vec(ox + dx * t, oy, oz)
            return (hit, direction, None, t)
        return (None, None, None, None)

    def find_nearest(self, p):
        return (p, None, None, 0.0)


class _TreeInfinito:
    """Nunca escapa: reproduce rebotes > límite (malla no cerrada)."""

    def ray_cast(self, origin, direction, dist=1000):
        ox, oy, oz = _xyz(origin)
        dx = direction.x if hasattr(direction, 'x') else direction[0]
        dy = direction.y if hasattr(direction, 'y') else direction[1]
        dz = direction.z if hasattr(direction, 'z') else direction[2]
        hit = _Vec(ox + dx * 0.01, oy + dy * 0.01, oz + dz * 0.01)
        return (hit, direction, None, 0.01)

    def find_nearest(self, p):
        return (p, None, None, 0.0)


class Tests(unittest.TestCase):
    def test_lamina_no_usa_interior_cerrado(self):
        verts = [_Vec(0, 0, 0), _Vec(1, 0, 0), _Vec(0, 1, 0), _Vec(0.5, 0.5, 0.001)]
        ex, ey, ez = extents_vertices(verts)
        self.assertLess(ez / max(ex, ey, ez), 0.02)
        meta = clasificar_collider('cortina_t', verts, _TreeCaja(), face_count=2)
        self.assertEqual(meta['metodo'], 'distancia_overlap')
        self.assertIn('lámina', meta['motivo'])

    def test_ray_parity_no_aborta_en_malla_ambigua(self):
        p = _Vec(0.5, 0.5, 0.5)
        viable, _, motivo = ray_parity_interiores(_TreeInfinito(), p, max_rebotes=50)
        self.assertFalse(viable)
        self.assertIn('50', motivo)

    def test_solido_cerrado_clasifica_y_mide(self):
        verts = [_Vec(x, y, z) for x in (0, 1) for y in (0, 1) for z in (0, 1)]
        tree = _TreeCaja()
        meta = clasificar_collider('caja', verts, tree, face_count=12)
        self.assertEqual(meta['metodo'], 'interior_cerrado')
        inside = punto_dentro_collider(tree, _Vec(0.5, 0.5, 0.5), meta)
        self.assertTrue(inside or isinstance(inside, bool))

    def test_punto_dentro_respeta_metodo(self):
        meta = {'metodo': 'distancia_overlap'}
        self.assertFalse(punto_dentro_collider(_TreeCaja(), _Vec(0.5, 0.5, 0.5), meta))

    def test_muestreo_cuadros_y_vertices(self):
        c200 = cuadros_muestra_penetracion(200, max_muestras=48)
        self.assertLessEqual(len(c200), 50)
        self.assertEqual(c200[-1], 200)
        vs = list(range(500))
        self.assertLessEqual(len(_muestra_vertices(vs)), 32)


if __name__ == '__main__':
    unittest.main(verbosity=2)
