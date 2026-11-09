"""El buscador por cuadro devuelve el mismo informe que el recorrido por candidato.

No abre Blender. El obstáculo es una caja analítica; cuenta cuántas veces cambia
de cuadro, que en Blender es reconstruir o buscar el BVH del escenario.
"""
import copy
import math
import random
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'motor'))
import buscador_posicion_camara as BUS

AZ = [0, 15, -15, 30, -30, 45, -45, 60, -60, 75, -75]
FAC = [1.0, 0.85, 1.2, 0.7, 1.45]


class Caja:
    def __init__(self, lo, hi):
        self.lo, self.hi = lo, hi
        self.cambios = 0
        self.ultimo = None
        self.llamadas = 0

    def para(self, f):
        def obs(loc):
            self.llamadas += 1
            if self.ultimo != f:
                self.cambios += 1
                self.ultimo = f
            dentro = all(self.lo[i] <= loc[i] <= self.hi[i] for i in range(3))
            d = math.sqrt(sum(max(self.lo[i] - loc[i], 0, loc[i] - self.hi[i]) ** 2 for i in range(3)))
            return (dentro, 0.0 if dentro else d, 'caja')
        return obs


def pedido(n, caja, lado=None, eje=False, semilla=0, libres=False, yaw=0.0):
    rnd = random.Random(semilla)
    muestras = []
    for f in range(n):
        giro = math.radians(20.0 * f / max(1, n - 1)) + rnd.uniform(-0.01, 0.01)
        frente = (math.sin(giro), math.cos(giro), 0.0)
        x = 0.4 * f / max(1, n - 1)
        pts = [(x + rnd.uniform(-0.15, 0.15), rnd.uniform(-0.1, 0.1), rnd.uniform(1.2, 1.75)) for _ in range(24)]
        muestras.append({'frente': frente, 'mira': (x, 0.0, 1.5), 'hf': 0.96, 'puntos': pts, 'centro': (x, 0.0, 0.9),
                         'cabeza': (x, 0.0, 1.6), 'frente_cara': frente, 'altura': 1.75,
                         'eje': ((x, 0.0, 0.0), (-1.6, 0.6, 0.0)) if eje else None, 'yaw': yaw, 'roll': 0.0,
                         'altura_extra': 0.0, 'dist_mul': 1.0, 'libre_encuadre': libres and f % 7 == 0,
                         'libre_inclin': False, 'modelado': True, 'obstaculo': caja.para(f)})
    return {'sensor_mm': 36.0, 'lens_mm': 35.0, 'aspecto': 16 / 9, 'elev_deg': 0.0, 'orient_deg': 0.0, 'aire': 0.06,
            'xlado': 0.5, 'region_min': 0.9, 'max_cara_deg': 110, 'inclinacion_tol_deg': 5, 'roll_tol_deg': 3,
            'holgura_max_m': 0.15, 'holgura_frac_distancia': 0.3, 'holgura_frac_altura': 0.25, 'lado': lado,
            'cara_exigida': True, 'azimuts_deg': AZ, 'factores': FAC, 'muestras': muestras}


ESCENARIOS = {
    'directo_pasa': ((5, 5, 5), (6, 6, 6), {}),
    'caja_delante': ((-1.6, 1.0, 0.0), (1.6, 3.6, 2.4), {}),
    'caja_delante_eje': ((-1.6, 1.0, 0.0), (1.6, 3.6, 2.4), {'eje': True}),
    'caja_delante_lado': ((-1.6, 1.0, 0.0), (1.6, 3.6, 2.4), {'eje': True, 'lado': -1.0}),
    'caja_ancha_sin_solucion': ((-9, 0.3, -1), (9, 9, 9), {}),
    'pared_cercana': ((-9, 2.0, -1), (9, 2.4, 9), {'libres': True}),
}


class BuscadorPorCuadro(unittest.TestCase):
    def _par(self, nombre, n=9):
        lo, hi, k = ESCENARIOS[nombre]
        a, b = Caja(lo, hi), Caja(lo, hi)
        pa = pedido(n, a, **k)
        pb = pedido(n, b, **k)
        avisos = []
        pb['por_cuadro'] = True
        pb['aviso'] = lambda fase, i, total, cand: avisos.append((fase, i, total, cand))
        return BUS.buscar(pa), BUS.buscar(pb), a, b, avisos

    def test_mismo_informe_en_todos_los_escenarios(self):
        for nombre in ESCENARIOS:
            with self.subTest(nombre):
                sec, lot, a, b, _ = self._par(nombre)
                extra = lot.pop('por_cuadro', None)
                self.assertEqual(sec, lot)
                if extra is not None:
                    self.assertEqual(extra['fuera_de_lote'], 0, nombre)

    def test_hay_escenario_que_refina_y_el_obstaculo_va_por_cuadro(self):
        sec, lot, a, b, avisos = self._par('caja_delante', n=12)
        self.assertEqual(lot['por_cuadro']['fuera_de_lote'], 0)
        self.assertGreater(lot['examinados'], 682)
        self.assertTrue(any(f == 'refinar' for f, *_ in avisos))
        # Por candidato: un cambio de cuadro por cada (candidato, cuadro). Por cuadro: por lote.
        self.assertGreater(a.cambios, 682 * 12 - 1)
        self.assertLessEqual(b.cambios, lot['por_cuadro']['lotes'] * 12)
        self.assertLessEqual(lot['por_cuadro']['lotes'], 2 + BUS.PASOS_REFINAR)

    def test_evaluar_por_cuadro_igual_a_fallos_de(self):
        lo, hi, k = ESCENARIOS['caja_delante_eje']
        ped = pedido(10, Caja(lo, hi), **k)
        pares = [(d, f) for d in (-75.0, -20.0, 0.0, 33.3, 75.0) for f in (0.7, 1.0, 1.333, 1.45)]
        lote = BUS.evaluar_por_cuadro(pares, ped)
        for d, f in pares:
            self.assertEqual(lote[(d, f)], BUS.fallos_de(d, f, ped))

    def test_aviso_puede_cortar_la_busqueda(self):
        lo, hi, k = ESCENARIOS['caja_delante']
        ped = pedido(8, Caja(lo, hi), **k)
        ped['por_cuadro'] = True

        class Corte(Exception):
            pass

        def aviso(fase, i, total, cand):
            if fase == 'rejilla' and i == 3:
                raise Corte()
        ped['aviso'] = aviso
        with self.assertRaises(Corte):
            BUS.buscar(ped)

    def test_no_cambia_listas_tolerancias_ni_sensor(self):
        lo, hi, k = ESCENARIOS['caja_delante']
        ped = pedido(6, Caja(lo, hi), **k)
        ped['por_cuadro'] = True
        ped['sensor_mm'] = 35.0
        with self.assertRaises(ValueError):
            BUS.buscar(ped)
        ped['sensor_mm'] = 36.0
        antes = copy.deepcopy({k2: v for k2, v in ped.items() if k2 not in ('muestras', 'aviso')})
        BUS.buscar(ped)
        self.assertEqual(antes, {k2: v for k2, v in ped.items() if k2 not in ('muestras', 'aviso')})


if __name__ == '__main__':
    unittest.main(verbosity=2)
