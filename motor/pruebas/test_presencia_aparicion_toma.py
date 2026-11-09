"""Presencia aparecer: visible en toda la toma SB si el guion pide el personaje (onset t[0], no t[1])."""
import sys
import unittest
from pathlib import Path

R = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(R / 'motor'))
from seguridad import cuadro
from narrativa_estructurada import compilar_presencia, _inicio_accion
from eventos import hide_render_en_cuadro, validar_eventos

# Misma ventana que acción a9 (ch-pintor-bce0) en guardianes: aparecer [18, 21] s @ 24 fps.
T0, T1, FPS = 18.0, 21.0, 24.0


class Tests(unittest.TestCase):
    def test_aparecer_visible_en_toda_la_toma_sb(self):
        d = {
            'environment': {'events': []},
            'actions': [
                {
                    'id': 'aparecer_toma',
                    'actor': 'ch-pintor-bce0',
                    'accion': 'aparecer',
                    't': [T0, T1],
                }
            ],
            'clock': {'duration_s': 120, 'fps': FPS},
        }
        self.assertEqual(_inicio_accion(d['actions'][0]), T0)
        compilar_presencia(d)
        ev = next(
            e
            for e in d['environment']['events']
            if e.get('object') == 'ch-pintor-bce0' and e.get('property') == 'hide_render'
        )
        self.assertEqual(validar_eventos([ev], d['clock']['duration_s']), [])
        onset = next(k for k in ev['keys'] if k['t'] == T0)
        self.assertIs(onset['value'], False)
        self.assertNotIn(T1, [k['t'] for k in ev['keys'] if k['value'] is False])
        f_ini = 1 + cuadro(T0, FPS)
        f_fin = cuadro(T1, FPS)
        self.assertEqual(f_ini, 433)
        self.assertEqual(f_fin, 504)
        for frame in range(f_ini, f_fin + 1):
            self.assertIs(
                hide_render_en_cuadro(ev['keys'], frame, FPS),
                False,
                f'frame {frame} debería ser visible en toma05',
            )
        self.assertIs(hide_render_en_cuadro(ev['keys'], f_ini - 1, FPS), True)
        self.assertIs(hide_render_en_cuadro(ev['keys'], f_fin + 1, FPS), False)

    def test_argon_t21_y_action_a9_un_solo_escritor(self):
        d = {
            'environment': {
                'events': [
                    {
                        'object': 'ch-pintor-bce0',
                        'property': 'hide_render',
                        'recursive': True,
                        'action_id': 'a9',
                        'keys': [
                            {'t': 0, 'value': True, 'curve': 'CONSTANT'},
                            {'t': 21.0, 'value': False, 'curve': 'CONSTANT'},
                        ],
                        'source': {'module': 'argon', 'plantilla': 'hero_visibility'},
                    }
                ]
            },
            'actions': [
                {
                    'id': 'a9',
                    'actor': 'ch-pintor-bce0',
                    'accion': 'aparecer',
                    't': [T0, T1],
                }
            ],
            'clock': {'duration_s': 120, 'fps': FPS},
        }
        compilar_presencia(d)
        hrs = [
            e
            for e in d['environment']['events']
            if e.get('object') == 'ch-pintor-bce0' and e.get('property') == 'hide_render'
        ]
        self.assertEqual(len(hrs), 1)
        self.assertEqual(validar_eventos(hrs, d['clock']['duration_s']), [])
        for frame in range(433, 505):
            self.assertIs(hide_render_en_cuadro(hrs[0]['keys'], frame, FPS), False)
        self.assertIn('presence_superseded', d['environment'])

    def test_cofre_argon_t33_sustituido_por_aparecer_t30(self):
        d = {
            'environment': {
                'events': [
                    {
                        'object': 'obj-cofre-dorado',
                        'property': 'hide_render',
                        'recursive': True,
                        'action_id': 'a13',
                        'keys': [
                            {'t': 0, 'value': True, 'curve': 'CONSTANT'},
                            {'t': 33.0, 'value': False, 'curve': 'CONSTANT'},
                        ],
                        'source': {'module': 'argon', 'plantilla': 'cofre_visibility'},
                    }
                ]
            },
            'actions': [
                {
                    'id': 'a13',
                    'objeto': 'obj-cofre-dorado',
                    'accion': 'aparecer',
                    't': [30.0, 33.0],
                }
            ],
            'clock': {'duration_s': 120, 'fps': FPS},
        }
        compilar_presencia(d)
        ev = d['environment']['events'][0]
        self.assertEqual(ev['action_ids'], ['a13'])
        onset = next(k for k in ev['keys'] if k['value'] is False)
        self.assertEqual(onset['t'], 30.0)
        f_ini = 1 + cuadro(30.0, FPS)
        f_fin = cuadro(33.0, FPS)
        self.assertIs(hide_render_en_cuadro(ev['keys'], f_ini, FPS), False)
        self.assertIs(hide_render_en_cuadro(ev['keys'], f_fin, FPS), False)
        self.assertEqual(validar_eventos([ev], d['clock']['duration_s']), [])

    def test_recompilar_borra_presencia_obsoleta_con_onset_fin(self):
        d = {
            'environment': {
                'events': [
                    {
                        'object': 'actor_x',
                        'property': 'hide_render',
                        'recursive': True,
                        'compiled_presence': True,
                        'action_id': 'viejo',
                        'action_ids': ['viejo'],
                        'keys': [
                            {'t': 0, 'value': True, 'curve': 'CONSTANT'},
                            {'t': 3.0, 'value': False, 'curve': 'CONSTANT'},
                        ],
                        'source': {},
                    }
                ]
            },
            'actions': [
                {'id': 'nuevo', 'actor': 'actor_x', 'accion': 'aparecer', 't': [2, 3]},
            ],
            'clock': {'duration_s': 10, 'fps': 24},
        }
        compilar_presencia(d)
        ev = d['environment']['events'][0]
        self.assertEqual(ev['action_ids'], ['nuevo'])
        onset = next(k for k in ev['keys'] if k['value'] is False)
        self.assertEqual(onset['t'], 2.0)
        self.assertIs(hide_render_en_cuadro(ev['keys'], 1 + cuadro(2.0, 24), 24), False)
        self.assertIs(hide_render_en_cuadro(ev['keys'], 1 + cuadro(3.0, 24), 24), False)


if __name__ == '__main__':
    unittest.main(verbosity=2)
