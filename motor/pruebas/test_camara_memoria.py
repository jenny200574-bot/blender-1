"""Regresión memoria cámara (sin bpy): compactación, purga lógica de cachés BVH."""
import sys
import unittest
from pathlib import Path

R = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(R / 'motor'))
from camara_memoria import compactar_puntos, descartar_bvh, purgar_caches_bvh


class _BV:
    def __init__(self):
        self.t = object()


class Tests(unittest.TestCase):
    def test_compactar_puntos_no_crece_lista(self):
        pts = [(float(i), 0, 0) for i in range(1000)]
        out = compactar_puntos(pts, 64)
        self.assertLessEqual(len(out), 64)
        self.assertGreater(len(out), 0)

    def test_purgar_caches_bvh_libera_entradas(self):
        entorno = {1: _BV(), 2: _BV()}
        otros = {3: _BV()}
        estatico = [None, None]
        purgar_caches_bvh(entorno, otros, estatico)
        self.assertEqual(len(entorno), 0)
        self.assertEqual(len(otros), 0)

    def test_simulacion_tomas_no_acumula_bvh_en_dict(self):
        """N tomas: mismo patrón que _vaciar_caches_toma no deja crecer mapas."""
        entorno = {}
        for n in range(12):
            entorno[n] = _BV()
            purgar_caches_bvh(entorno, {}, [None, None])
        self.assertEqual(len(entorno), 0)

    def test_descartar_bvh_sin_error(self):
        descartar_bvh(None)
        b = _BV()
        descartar_bvh(b)


if __name__ == '__main__':
    unittest.main(verbosity=2)
