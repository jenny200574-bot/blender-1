import json, sys, unittest
from pathlib import Path
R = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(R / 'motor'))
from eje_objetos import alias_vacio, enlazar, par_eje
from objetos_adn import compilar

ESC = Path(__file__).resolve().parents[2] / 'escenas' / 'guardianes_esc1_candidata'

class Tests(unittest.TestCase):
    def test_par_entre_personajes_y_alias_construido(self):
        brazos = {'ch-don-caos-7adf', 'ch-spark-468e', 'ch-pintor-bce0'}
        self.assertEqual(par_eje('ch-spark-468e-ch-pintor-bce0', brazos, set()), ('ch-spark-468e', 'ch-pintor-bce0'))
        objetos = {'ch-don-caos-7adf-libro'}
        self.assertEqual(par_eje('ch-don-caos-7adf-libro', brazos, objetos), ('ch-don-caos-7adf', 'ch-don-caos-7adf-libro'))
        self.assertEqual(par_eje('ch-don-caos-7adf-libro', brazos, set())[0], 'ambiguo')

    def test_escena1_enlaza_libro_y_ventana_sin_inventar(self):
        sb = json.loads((ESC / 'camara_4g' / 'sb_scene.json').read_text())
        props = ['obj-libro-cuentos__e1-8', 'Ventana con vista al arcoíris', 'obj-cama', 'obj-cofre-dorado']
        personas = ['ch-don-caos-7adf', 'ch-spark-468e', 'ch-pintor-bce0', 'ch-valentina-a9be', 'ch-eco-eff3']
        aliases, errores = enlazar(sb['vinetas'], props, personas)
        self.assertEqual(errores, [])
        self.assertEqual(aliases['ch-don-caos-7adf-libro'], 'obj-libro-cuentos__e1-8')
        self.assertEqual(aliases['ch-don-caos-7adf-ventana'], 'Ventana con vista al arcoíris')
        self.assertNotIn('ch-spark-468e-ch-pintor-bce0', aliases)

    def test_eje_sin_cita_no_inventa_vinculo(self):
        vinetas = [{'continuidad': {'eje': 'ch-don-caos-7adf-libro', 'cambios_declarados': [{'antes': 'algo que no es un id', 'despues': 'tampoco'}]}}]
        aliases, errores = enlazar(vinetas, ['obj-libro-cuentos__e1-8'], ['ch-don-caos-7adf'])
        self.assertEqual(aliases, {})
        self.assertEqual(errores[0]['codigo'], 'EJE_SIN_OBJETO')
        self.assertIn('ch-don-caos-7adf-libro', errores[0]['mensaje'])

    def test_alias_copia_la_posicion_medida(self):
        prop = {'id': 'obj-libro-cuentos__e1-8', 'position_m': [1.2, 2.6, 0.54], 'rotation_deg': [0, 0, 15]}
        alias = alias_vacio(prop, 'ch-don-caos-7adf-libro')
        self.assertEqual(alias['position_m'], [1.2, 2.6, 0.54])
        self.assertEqual(alias['of'], prop['id'])
        with self.assertRaises(ValueError):
            alias_vacio({'id': 'x'}, 'ch-don-caos-7adf-libro')

    def test_compilador_de_escena1_marca_los_ejes(self):
        d = json.loads((ESC / 'entrada_escena.json').read_text())
        cat = json.loads((R / 'bibliotecas' / 'formulas_star_estrictas.json').read_text())
        pol = json.loads((R / 'bibliotecas' / 'politica_busqueda_formas_cpu.json').read_text())
        recibo, errores = compilar(d, ESC, cat, pol)
        self.assertEqual(recibo['state'], 'READY', errores)
        por_id = {p['id']: p for p in d['props']}
        self.assertEqual(por_id['obj-libro-cuentos__e1-8']['axis_ids'], ['ch-don-caos-7adf-libro'])
        self.assertEqual(por_id['Ventana con vista al arcoíris']['axis_ids'], ['ch-don-caos-7adf-ventana'])

if __name__ == '__main__':
    unittest.main(verbosity=2)
