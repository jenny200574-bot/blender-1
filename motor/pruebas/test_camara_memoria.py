"""Regresión memoria cámara (sin bpy): compactación, purga lógica de cachés BVH."""
import sys
import unittest
from pathlib import Path

R = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(R / 'motor'))
from camara_memoria import (
    compactar_puntos,
    descartar_bvh,
    es_bvh_compartido_estatico,
    evictar_entrada_bvh,
    purgar_caches_bvh,
)


class _BV:
    def __init__(self, nombre=''):
        self.t = f'arbol-{nombre}'
        self.own = []

    def ray_cast(self, *q):
        if self.t is None:
            raise AttributeError('_BV sin arbol')
        return ('hit', 0, 0, 0)


class Tests(unittest.TestCase):
    def test_compactar_puntos_no_crece_lista(self):
        pts = [(float(i), 0, 0) for i in range(1000)]
        out = compactar_puntos(pts, 64)
        self.assertLessEqual(len(out), 64)
        self.assertGreater(len(out), 0)

    def test_purgar_caches_bvh_libera_entradas_sin_mutar_wrapper(self):
        est = _BV('est')
        estatico = [est, 10, frozenset()]
        entorno = {1: est, 2: _BV('dyn')}
        otros = {3: _BV('oth')}
        purgar_caches_bvh(entorno, otros, estatico)
        self.assertEqual(len(entorno), 0)
        self.assertEqual(len(otros), 0)
        self.assertIsNone(estatico[0])

    def test_eviccion_no_rompe_bvh_estatico_compartido(self):
        """Reproduce R7: ENVC guarda el mismo _BV que _BVH_ESCENA_EST; evictar una clave no debe borrar .t."""
        estatico = [_BV('compartido'), 1, frozenset()]
        est = estatico[0]
        entorno = {'f10': est, 'f20': est, 'f30': _BV('otro')}
        self.assertTrue(es_bvh_compartido_estatico(est, estatico))
        evictar_entrada_bvh(entorno, 'f10', estatico)
        self.assertIn('f20', entorno)
        self.assertEqual(est.t, 'arbol-compartido')
        est.ray_cast(0, 0, 0)
        evictar_entrada_bvh(entorno, 'f20', estatico)
        entorno['f40'] = estatico[0]
        estatico[0].ray_cast(1, 1, 1)

    def test_doce_tomas_sin_mutar_bvh_entre_tomas(self):
        estatico = [None, None, None]
        for n in range(12):
            est = _BV(f'est{n}')
            estatico[0] = est
            entorno = {f't{n}-{i}': est if i % 2 == 0 else _BV(f'd{n}-{i}') for i in range(6)}
            while len(entorno) > 3:
                evictar_entrada_bvh(entorno, next(iter(entorno)), estatico)
            purgar_caches_bvh(entorno, {}, estatico)
            self.assertIsNone(estatico[0])
            est = _BV(f'rebuild{n}')
            est.ray_cast(0, 0, 0)

    def test_descartar_bvh_es_noop(self):
        descartar_bvh(None)
        b = _BV()
        descartar_bvh(b)
        self.assertIsNotNone(b.t)
        b.ray_cast()


if __name__ == '__main__':
    unittest.main(verbosity=2)
