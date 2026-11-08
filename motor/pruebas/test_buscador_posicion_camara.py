import ast
import json
import math
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'motor'))
import buscador_posicion_camara as B

CFG = json.loads((ROOT / 'motor' / 'camara_v2_config.json').read_text(encoding='utf-8'))
AZ = CFG['busqueda_acimut_deg']
FAC = CFG['busqueda_factor_distancia']


def base(**extra):
    ped = {
        'sensor_mm': 36,
        'lens_mm': 35,
        'aspecto': 16 / 9,
        'elev_deg': 0,
        'orient_deg': 0,
        'aire': 0.06,
        'xlado': 0.5,
        'region_min': CFG['region_en_cuadro_min'],
        'max_cara_deg': CFG['max_angulo_cara_deg'],
        'inclinacion_tol_deg': CFG['inclinacion_tolerancia_deg'],
        'roll_tol_deg': CFG['roll_tolerancia_deg'],
        'holgura_max_m': CFG['holgura_max_m'],
        'holgura_frac_distancia': CFG['holgura_frac_distancia'],
        'holgura_frac_altura': CFG['holgura_frac_altura'],
        'lado': None,
        'cara_exigida': True,
        'azimuts_deg': AZ,
        'factores': FAC,
    }
    ped.update(extra)
    return ped


def muestra(frente=(1, 0, 0), mira=(0, 0, 1), hf=0.55, puntos=None, obstaculo=None, **extra):
    if puntos is None:
        puntos = [(0, 0, 1.05), (0, 0.05, 1.05), (0, -0.05, 1.05), (0, 0, 1.15), (0, 0, 0.95)]
    fila = {
        'modelado': True,
        'frente': frente,
        'mira': mira,
        'hf': hf,
        'puntos': puntos,
        'centro': (0, 0, 1),
        'cabeza': (0, 0, 1.05),
        'frente_cara': frente,
        'altura': 1.0,
        'eje': None,
        'yaw': 0.0,
        'roll': 0.0,
        'altura_extra': 0.0,
        'dist_mul': 1.0,
        'libre_encuadre': False,
        'libre_inclin': False,
        'obstaculo': obstaculo or (lambda loc: (False, None, None)),
    }
    fila.update(extra)
    return fila


class Buscador(unittest.TestCase):
    def test_la_posicion_pedida_pasa_y_no_aprueba_produccion(self):
        info = B.buscar(base(muestras=[muestra()]))
        self.assertTrue(info['resuelto_geometrico'])
        self.assertEqual(info['candidato'], {'az_extra_deg': 0.0, 'factor_distancia': 1.0})
        self.assertFalse(info['production_approved'])
        self.assertNotIn('import numpy', Path(B.__file__).read_text(encoding='utf-8'))
        self.assertNotIn('import scipy', Path(B.__file__).read_text(encoding='utf-8'))

    def test_sensor_distinto_de_36_se_rechaza(self):
        with self.assertRaises(ValueError):
            B.buscar(base(sensor_mm=35, muestras=[muestra()]))

    def test_la_rejilla_se_salta_el_unico_factor_que_cabe(self):
        pts = [(0, -0.36, 1.1), (0, 0.36, 1.1), (0, 0, 1.22), (0, 0, 0.88)]

        def obs(loc):
            if loc[0] >= 0.95 or abs(loc[1]) >= 0.20:
                return True, 0.0, 'muro'
            return False, min(0.95 - loc[0], 0.20 - abs(loc[1])), 'muro'

        info = B.buscar(base(muestras=[muestra(puntos=pts, obstaculo=obs)]))
        self.assertFalse(info['rejilla_discreta_resuelve'])
        self.assertTrue(info['resuelto_geometrico'])
        factor = info['candidato']['factor_distancia']
        self.assertGreater(factor, 0.7)
        self.assertLess(factor, 0.85)
        self.assertEqual(info['candidato']['az_extra_deg'], 0.0)
        self.assertFalse(info['production_approved'])

    def test_encuadre_y_holgura_no_se_cumplen_a_la_vez(self):
        pts = [(0, -0.40, 1.1), (0, 0.40, 1.1), (0, 0, 1.22), (0, 0, 0.88)]

        def obs(loc):
            if loc[0] >= 0.85 or abs(loc[1]) >= 0.20:
                return True, 0.0, 'muro'
            return False, min(0.85 - loc[0], 0.20 - abs(loc[1])), 'muro'

        info = B.buscar(base(muestras=[muestra(puntos=pts, obstaculo=obs)]))
        self.assertFalse(info['resuelto_geometrico'])
        self.assertFalse(info['rejilla_discreta_resuelve'])
        self.assertIn(['encuadre', 'holgura'], info['incompatibles'])
        self.assertFalse(info['production_approved'])

    def test_el_lado_del_eje_fuera_de_la_ventana_es_imposible(self):
        eje = ((5, -1, 0), (5, 1, 0))
        # El sujeto está en el origen y la ventana ±75° no alcanza el otro lado de la recta x=5.
        info = B.buscar(base(lado=-1.0, muestras=[muestra(eje=eje)]))
        self.assertFalse(info['resuelto_geometrico'])
        estados = {fila['nombre']: fila['estado'] for fila in info['restricciones']}
        self.assertEqual(estados['eje_180'], 'sin_solucion')
        self.assertFalse(info['production_approved'])

    def test_la_grua_pedida_que_rompe_la_inclinacion_no_se_anula(self):
        info = B.buscar(base(muestras=[muestra(altura_extra=-0.8)]))
        self.assertFalse(info['resuelto_geometrico'])
        estados = {fila['nombre']: fila['estado'] for fila in info['restricciones']}
        self.assertEqual(estados['inclinacion'], 'sin_solucion')
        pequena = B.buscar(base(muestras=[muestra(altura_extra=-0.05)]))
        self.assertTrue(pequena['resuelto_geometrico'])
        self.assertEqual(pequena['candidato']['factor_distancia'], 1.0)

    def test_el_roll_pedido_se_conserva(self):
        self.assertEqual(B.fallos_de(0, 1, base(muestras=[muestra(roll=math.radians(8))]))['roll'], 0)
        self.assertEqual(B.fallos_de(0, 1, base(muestras=[muestra(roll=0.0)]))['roll'], 0)
        info = B.buscar(base(elev_deg=-12, muestras=[muestra(frente=(0, 1, 0), mira=(0, 0, 1))]))
        self.assertTrue(info['resuelto_geometrico'])
        self.assertEqual(info['candidato']['factor_distancia'], 1.0)

    def test_pitch_pedido_es_el_negativo_de_la_elevacion(self):
        frente = (0, 1, 0)
        mira = (0, 0, 1)
        hf = 0.55
        ped = base(elev_deg=-12)
        dh, _ = B.direccion(frente, ped['orient_deg'], ped['elev_deg'])
        distancia = hf * ped['lens_mm'] / (ped['sensor_mm'] / ped['aspecto'])
        _look, loc, ejes = B._ajustar(mira, dh, ped['elev_deg'], distancia, 0, [(0, 0, 1.05)], ped, 0, 0)
        pitch, roll = B._pitch_roll(ejes)
        self.assertAlmostEqual(pitch, 12.0, places=4)
        self.assertAlmostEqual(roll, 0.0, places=4)
        self.assertAlmostEqual(B._yaw_cara(frente, (0, 0, 1.05), loc), 0.0, places=4)

    def test_track_mantiene_el_frente_y_static_no_puede_inventar_orbita(self):
        efectos, completo = B.efectos_de_segmentos(
            [
                {'t0': 11.0, 't1': 15.5, 'movimiento': 'STATIC', 'args': {}},
                {'t0': 15.5, 't1': 18.0, 'movimiento': 'TRACK', 'args': {'screen': 'L2R'}},
            ],
            265, 432, 24, {'MS': 0.55},
        )
        self.assertTrue(completo)
        self.assertFalse(efectos[372]['seguir_frente'])
        self.assertTrue(efectos[373]['seguir_frente'])
        giro = B.acimut_mundo((0, 1, 0), 40) 
        otro = B.acimut_mundo((-1, 0, 0), 40)
        self.assertAlmostEqual(abs(B._wrap_diff(otro, giro)), math.pi / 2, places=4)

    def test_orbita_sin_modelo_no_se_declara_imposible(self):
        efectos, completo = B.efectos_de_segmentos(
            [{'t0': 0.0, 't1': 1.0, 'movimiento': 'ORBIT', 'args': {'degrees': 30}}],
            1, 24, 24, {},
        )
        self.assertFalse(completo)
        self.assertFalse(efectos[1]['modelado'])
        info = B.buscar(base(muestras=[muestra(modelado=False)]))
        self.assertFalse(info['resuelto_geometrico'])
        self.assertFalse(info['modelo_completo'])
        self.assertEqual(len(info['propuestas']), len(AZ) * len(FAC))
        self.assertNotIn('sin_solucion', info['motivo'])

    def test_el_rig_consulta_el_acimut_por_cuadro(self):
        texto = (ROOT / 'motor' / 'rig_camara_coords.py').read_text(encoding='utf-8')
        self.assertIn("tr.get('az_fn')", texto)
        arbol = ast.parse((ROOT / 'motor' / 'camara_v2_blender.py').read_text(encoding='utf-8'))
        self.assertIsNotNone(arbol)
        camara = (ROOT / 'motor' / 'camara_v2_blender.py').read_text(encoding='utf-8')
        self.assertIn('buscador_posicion_camara', camara)
        self.assertIn('TRACK', camara)


def _wrap_diff(a, b):
    return (a - b + math.pi) % (2 * math.pi) - math.pi


# el módulo no exporta el wrap; el test usa el suyo
B._wrap_diff = _wrap_diff


class Sonda(unittest.TestCase):
    def test_la_sonda_no_guarda_el_blend(self):
        ruta = ROOT / 'motor' / 'sonda_inspeccion_camara.py'
        texto = ruta.read_text(encoding='utf-8')
        self.assertNotIn('save_as_mainfile', texto)
        self.assertNotIn('ops.wm.save', texto)
        ast.parse(texto)
        self.assertIn('hide_render', texto)
        self.assertIn('motor_preserve_hidden', texto)
        self.assertIn('claves_hide_render', texto)
        self.assertIn('evaluated_get', texto)


if __name__ == '__main__':
    unittest.main()
