import copy, json, sys, unittest
from pathlib import Path
R = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(R / 'motor'))
from malla_cabeza import desplazar_cabeza, error_hueso_cabeza, error_malla_vacia, region_desde_hueso, validar_cabeza, clasificar_medida_cabeza, estado_visual, marcar_malla_cabeza_visible
from traductor_adn import compilar

ESC = Path(__file__).resolve().parents[2] / 'escenas' / 'guardianes_esc1_candidata'
IDS = ['ch-pintor-bce0', 'ch-spark-468e', 'ch-valentina-a9be', 'ch-eco-eff3']

class Tests(unittest.TestCase):
    def test_malla_vacia_no_se_construye(self):
        self.assertIsNone(error_malla_vacia({'id': 'cara', 'shape': 'MESH', 'vertices_m': [[0, 0, 0]], 'faces': [[0]]}))
        msg = error_malla_vacia({'id': 'ch-eco-eff3.base.face', 'shape': 'MESH', 'vertices_m': [], 'faces': []})
        self.assertIn('ch-eco-eff3.base.face', msg)
        self.assertIn('No se construye', msg)

    def test_hueso_ausente_nombra_al_personaje(self):
        self.assertIsNone(error_hueso_cabeza('ch-pintor-bce0', 'head', 'cabeza', ['cabeza', 'pecho']))
        msg = error_hueso_cabeza('ch-pintor-bce0', 'head', 'cabeza', ['pecho'])
        self.assertIn('ch-pintor-bce0', msg)
        self.assertIn('cabeza', msg)
        self.assertIn('No se inventa', msg)

    def test_desplazamiento_de_cabeza_usa_el_largo_del_hueso(self):
        self.assertEqual(desplazar_cabeza([(0, 0, 0), (1, 0, 0)], 2), [(0, 1.0, 0), (1, 1.0, 0)])
        with self.assertRaises(ValueError):
            desplazar_cabeza([(0, 0, 0)], None)

    def test_cuatro_humanoides_salen_con_malla_de_cabeza(self):
        d = json.loads((ESC / 'entrada_escena.json').read_text())
        d['entities'] = [e for e in d['entities'] if e['id'] in IDS]
        recibos, errores = compilar(d, True)
        self.assertEqual(errores, [])
        self.assertEqual({r['entity'] for r in recibos}, set(IDS))
        for ent in d['entities']:
            self.assertIsNone(validar_cabeza(ent))
            caras = [p for p in ent['appearance']['geometry']['parts'] if p.get('bind_role') == 'head' and p.get('role') == 'face']
            self.assertTrue(caras)
            self.assertGreater(len(caras[0]['vertices_m']), 0)

    def test_region_de_hueso_no_inventa_largo(self):
        region = region_desde_hueso((0, 0, 1), (0, 0, 1.4))
        self.assertEqual(region['origen'], 'hueso')
        self.assertEqual(region['centro'], (0, 0, 1.2))
        self.assertAlmostEqual(region['alto'], 0.4)
        self.assertIsNone(region_desde_hueso((0, 0, 1), (0, 0, 1)))
        self.assertIsNone(region_desde_hueso(None, (0, 0, 1)))
        self.assertIsNone(region_desde_hueso((0, 0, float('nan')), (0, 0, 1)))

    def test_respaldo_de_hueso_no_aprueba_la_malla_ausente(self):
        region = region_desde_hueso((0, 0, 1), (0, 0.2, 1.3))
        clase = clasificar_medida_cabeza(region)
        self.assertEqual(clase['medicion'], 'respaldo_hueso')
        self.assertFalse(clase['malla_visible'])
        self.assertFalse(clase['valida_visual'])
        self.assertFalse(clase['production_approved'])
        self.assertIn('no visible', clase['mensaje'])
        self.assertEqual(estado_visual('pasa', clase), 'bloqueada')
        ausente = clasificar_medida_cabeza(None)
        self.assertEqual(ausente['medicion'], 'ausente')
        self.assertFalse(ausente['production_approved'])
        self.assertEqual(estado_visual('pasa', ausente), 'bloqueada')
        visible = clasificar_medida_cabeza(marcar_malla_cabeza_visible({'centro': (0, 0, 1)}))
        self.assertEqual(visible['medicion'], 'malla_visible')
        self.assertTrue(visible['valida_visual'])
        self.assertFalse(visible['production_approved'])
        self.assertEqual(estado_visual('pasa', visible), 'pasa')
        self.assertEqual(estado_visual('bloqueada', visible), 'bloqueada')

    def test_cabeza_vacia_bloquea_sin_inventar(self):
        ent = {'id': 'ch-valentina-a9be', 'type': 'CHARACTER', 'appearance': {'geometry': {'parts': [{'id': 'ch-valentina-a9be.base.face', 'shape': 'MESH', 'role': 'face', 'bind_role': 'head', 'vertices_m': [], 'faces': []}]}, 'rig': {'bones': []}}}
        msg = validar_cabeza(ent)
        self.assertIn('ch-valentina-a9be', msg)
        self.assertIn('sin vértices', msg)
        ent2 = copy.deepcopy(ent)
        ent2['appearance']['geometry']['parts'] = []
        ent2['rig'] = {'bones': [{'id': 'pecho', 'role': 'torso'}]}
        msg2 = validar_cabeza(ent2)
        self.assertIn('ch-valentina-a9be', msg2)
        self.assertIn('no tiene hueso ni malla de cabeza', msg2)

if __name__ == '__main__':
    unittest.main(verbosity=2)
