import copy, json, sys, tempfile, unittest
from pathlib import Path
R = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(R / 'motor'))
from revisor_propuesta_fisica import FIJAS, aplicar, revisar
from puentes_fisicos import compilar, reglas
from seguridad import guardar, sha

def inventario():
    return {'meshes': ['suelo_estudio', 'muro_norte', 'cuerpo', 'marca_suelo'], 'markers': ['marca_suelo'], 'character_primary': {'actor': ['cuerpo']}, 'duration_s': 2}

def propuesta():
    return {
        'scene_id': 'escena_prueba',
        'proposal_status': 'PROPOSED_FOR_DETERMINISTIC_VALIDATION',
        'physics': {
            'bone_length_error_m': 1e-5,
            'root_speed_max_m_s': 1.5,
            'root_accel_max_m_s2': 8,
            'com_accel_max_m_s2': 20,
            'joint_speed_max_deg_s': 600,
            'slip_max_m_per_frame': 0.05,
            'penetration_tolerance_m': 0.001,
            'reject_surface_intersections': True,
            'colliders': ['suelo_estudio', 'muro_norte', 'cuerpo'],
            'allowed_collision_pairs': [['cuerpo', 'suelo_estudio']],
        },
        'contacts': [],
    }

class Tests(unittest.TestCase):
    def test_dentro_de_limite_no_aprueba(self):
        r = revisar(propuesta(), inventario())
        self.assertEqual(r['estado'], 'PROPUESTA_EN_LIMITE')
        self.assertIs(r['approved'], False)
        self.assertIs(r['production_approved'], False)
        self.assertIs(r['scene_physics_approved'], False)
        self.assertIs(r['physics_validated'], False)
        for k, v in FIJAS.items():
            self.assertEqual(r['reglas'][k], v)
        canon, err = reglas(r['reglas'])
        self.assertEqual(err, [])
        self.assertEqual(canon['joint_speed_max_deg_s'], 600)
        self.assertEqual(canon['slip_max_m_per_frame'], 0.05)

    def test_approved_true_en_raiz_se_rechaza(self):
        p = propuesta(); p['approved'] = True
        r = revisar(p, inventario())
        self.assertEqual(r['estado'], 'RECHAZADO')
        self.assertIsNone(r['reglas'])
        self.assertIs(r['approved'], False)
        self.assertTrue(any(e['codigo'] == 'MODELO_NO_APRUEBA' for e in r['errores']))

    def test_approved_true_anidado_se_rechaza(self):
        p = propuesta(); p['physics']['approved'] = True
        r = revisar(p, inventario())
        self.assertEqual(r['estado'], 'RECHAZADO')
        self.assertIs(r['approved'], False)
        self.assertIn('physics.approved', r['errores'][0]['mensaje'])

    def test_approved_false_si_pasa(self):
        p = propuesta(); p['approved'] = False; p['physics_validated'] = False
        r = revisar(p, inventario())
        self.assertEqual(r['estado'], 'PROPUESTA_EN_LIMITE')
        self.assertIs(r['approved'], False)

    def test_proposal_status_approved_se_rechaza(self):
        p = propuesta(); p['proposal_status'] = 'APPROVED'
        r = revisar(p, inventario())
        self.assertEqual(r['estado'], 'RECHAZADO')
        self.assertTrue(any(e['codigo'] == 'MODELO_NO_APRUEBA' for e in r['errores']))

    def test_reglas_fijas_y_valor_t317_900(self):
        for key, malo in [('com_accel_max_m_s2', 21), ('joint_speed_max_deg_s', 900), ('slip_max_m_per_frame', 0.06)]:
            p = propuesta(); p['physics'][key] = malo
            r = revisar(p, inventario())
            self.assertEqual(r['estado'], 'RECHAZADO', key)
            self.assertIsNone(r['reglas'])
            e = next(x for x in r['errores'] if x['codigo'] == 'REGLA_FIJA_ALTERADA')
            self.assertEqual(e['dato_encontrado'], malo)
            self.assertEqual(e['dato_esperado'], FIJAS[key])

    def test_enteros_equivalentes_de_las_fijas(self):
        p = propuesta(); p['physics']['com_accel_max_m_s2'] = 20.0; p['physics']['joint_speed_max_deg_s'] = 600.0
        r = revisar(json.loads(json.dumps(p)), inventario())
        self.assertEqual(r['estado'], 'PROPUESTA_EN_LIMITE')
        self.assertEqual(r['reglas']['slip_max_m_per_frame'], 0.05)

    def test_bool_y_nan_no_cuelan(self):
        p = propuesta(); p['physics']['joint_speed_max_deg_s'] = True
        self.assertEqual(revisar(p, inventario())['estado'], 'RECHAZADO')
        p = propuesta(); p['physics']['com_accel_max_m_s2'] = float('nan')
        self.assertEqual(revisar(p, inventario())['estado'], 'RECHAZADO')

    def test_regla_fija_ausente_bloquea(self):
        p = propuesta(); del p['physics']['slip_max_m_per_frame']
        r = revisar(p, inventario())
        self.assertEqual(r['estado'], 'BLOQUEADO')
        self.assertIn('physics/slip_max_m_per_frame', r['faltantes'])
        self.assertIsNone(r['reglas'])

    def test_fuera_de_sensatez(self):
        p = propuesta(); p['physics']['root_speed_max_m_s'] = 1e9
        r = revisar(p, inventario())
        self.assertEqual(r['estado'], 'RECHAZADO')
        self.assertTrue(any(e['codigo'] == 'FUERA_DE_SENSATEZ' for e in r['errores']))

    def test_interseccion_apagada_se_rechaza(self):
        p = propuesta(); p['physics']['reject_surface_intersections'] = False
        self.assertEqual(revisar(p, inventario())['estado'], 'RECHAZADO')

    def test_limite_desconocido_no_se_copia(self):
        p = propuesta(); p['physics']['joint_speed_max_deg_s_t317'] = 900
        r = revisar(p, inventario())
        self.assertEqual(r['estado'], 'RECHAZADO')
        self.assertTrue(any(e['codigo'] == 'LIMITE_NO_RECONOCIDO' for e in r['errores']))

    def test_collider_ajeno_marcador_y_prefijo_no_adivinado(self):
        p = propuesta(); p['physics']['colliders'] = ['suelo_estudio', 'muro_norte', 'cuerpo', 'fantasma']
        self.assertEqual(revisar(p, inventario())['estado'], 'RECHAZADO')
        p = propuesta(); p['physics']['colliders'] = ['suelo_estudio', 'muro_norte', 'marca_suelo']
        self.assertTrue(any(e['codigo'] == 'NOT_ACTUAL_PHYSICAL_MESH' for e in revisar(p, inventario())['errores']))
        inv = inventario(); inv['markers'] = []
        p = propuesta(); p['physics']['colliders'] = ['suelo_estudio', 'muro_norte', 'cuerpo', 'marca_suelo']
        self.assertEqual(revisar(p, inv)['estado'], 'PROPUESTA_EN_LIMITE')

    def test_colliders_vacios_o_sin_inventario(self):
        p = propuesta(); p['physics']['colliders'] = []
        self.assertEqual(revisar(p, inventario())['estado'], 'RECHAZADO')
        r = revisar(propuesta(), None)
        self.assertEqual(r['estado'], 'BLOQUEADO')
        self.assertIn('inventario_fisico.meshes', r['faltantes'])

    def test_personaje_sin_collider_declarado(self):
        p = propuesta(); p['physics']['colliders'] = ['suelo_estudio', 'muro_norte']
        p['physics']['allowed_collision_pairs'] = []
        self.assertTrue(any(e['codigo'] == 'CHARACTER_COLLISION_OMITTED' for e in revisar(p, inventario())['errores']))

    def test_par_invalido(self):
        p = propuesta(); p['physics']['allowed_collision_pairs'] = [['cuerpo', 'cuerpo']]
        self.assertEqual(revisar(p, inventario())['estado'], 'RECHAZADO')

    def test_no_exige_piso_por_nombre(self):
        self.assertNotIn('piso', propuesta()['physics']['colliders'])
        self.assertEqual(revisar(propuesta(), inventario())['estado'], 'PROPUESTA_EN_LIMITE')

    def test_avian_absurdo_y_escena_sin_ave(self):
        self.assertEqual(revisar(propuesta(), inventario())['estado'], 'PROPUESTA_EN_LIMITE')
        p = propuesta(); p['avian'] = {'balance_margin_m': 1, 'shoulder_offset_m': [0, 0, 0], 'support_polygon_offsets_m': [[0, 0, 0], [.01, 0, 0], [0, .01, 0], [.01, .01, 0]]}
        self.assertTrue(any(e['codigo'] == 'AVIAN_MARGIN' for e in revisar(p, inventario())['errores']))

    def test_intervalos_solo_si_la_fuente_los_trae(self):
        p = propuesta()
        p['avian'] = {'balance_margin_m': .005, 'shoulder_offset_m': [0, 0, 0], 'support_polygon_offsets_m': [[0, 0, 0], [.01, 0, 0], [0, .01, 0], [.01, .01, 0]], 'support_intervals': [{'t0': 0, 't1': 1, 'mode': 'supported'}], 'attachment': {'target_point': 'hombro_medido'}}
        inv = inventario(); inv['intervalos_apoyo_fuente'] = [(0, 1)]; inv['punto_hombro'] = 'hombro_medido'
        self.assertEqual(revisar(p, inv)['estado'], 'PROPUESTA_EN_LIMITE')
        inv['punto_hombro'] = 'otro'
        self.assertTrue(any(e['codigo'] == 'HOMBRO_NO_COINCIDE' for e in revisar(p, inv)['errores']))

    def test_contactos_ausentes_no_se_inventan_vacios(self):
        p = propuesta(); del p['contacts']
        r = revisar(p, inventario())
        self.assertEqual(r['estado'], 'BLOQUEADO')
        self.assertIn('contacts', r['faltantes'])

    def test_aplicar_cpu_escribe_reglas_sin_aprobar(self):
        d = {'contacts': [], 'clock': {'duration_s': 2, 'fps': 24}, 'argon_physics_proposal': propuesta(), 'inventario_fisico': inventario()}
        receipt, errors = compilar(d, Path(tempfile.mkdtemp()), True)
        self.assertEqual(errors, [])
        self.assertEqual(d['rules']['com_accel_max_m_s2'], 20)
        self.assertEqual(d['rules']['joint_speed_max_deg_s'], 600)
        self.assertEqual(d['rules']['slip_max_m_per_frame'], 0.05)
        self.assertNotIn('approved', d)
        self.assertIs(receipt['revisor_propuesta_fisica']['approved'], False)
        self.assertIs(receipt['revisor_propuesta_fisica']['scene_physics_approved'], False)
        self.assertEqual(receipt['revisor_propuesta_fisica']['estado'], 'PROPUESTA_EN_LIMITE')

    def test_aplicar_apagado_no_escribe_reglas(self):
        d = {'contacts': [], 'rules': {'com_accel_max_m_s2': 20, 'joint_speed_max_deg_s': 600, 'slip_max_m_per_frame': 0.05}, 'argon_physics_proposal': propuesta(), 'inventario_fisico': inventario()}
        before = copy.deepcopy(d['rules'])
        receipt, errors = compilar(d, Path(tempfile.mkdtemp()), False)
        self.assertEqual(d['rules'], before)
        self.assertEqual(receipt['revisor_propuesta_fisica']['estado'], 'OFF')
        self.assertIs(receipt['revisor_propuesta_fisica']['approved'], False)
        self.assertTrue(any(e['codigo'] == 'CAPACIDAD_APAGADA' for e in errors))

    def test_approved_en_escena_no_deja_reglas(self):
        d = {'contacts': [], 'approved': True, 'clock': {'fps': 24, 'duration_s': 2}, 'argon_physics_proposal': propuesta(), 'inventario_fisico': inventario()}
        _receipt, errors = compilar(d, Path(tempfile.mkdtemp()), True)
        self.assertNotIn('rules', d)
        self.assertIs(d['approved'], False)
        self.assertTrue(any(e['codigo'] == 'MODELO_NO_APRUEBA' for e in errors))

    def test_physics_validated_true_no_abre_anclas(self):
        root = Path(tempfile.mkdtemp())
        program = {'status': 'complete', 'physics_validated': True, 'anclas': [{'actor': 'a', 'hueso': 'h', 'objetivo_punto': 'p', 'cadena': 2, 'iteraciones': 4, 't': [0, 1], 'tolerancia_m': .001}]}
        guardar(root / 'programa_2b.json', program)
        d = {'clock': {'duration_s': 2, 'fps': 24}, 'assets': [{'path': 'programa_2b.json', 'sha256': sha(root / 'programa_2b.json')}], 'motion': {'program': 'programa_2b.json'}, 'rules': {'com_accel_max_m_s2': 20}}
        _receipt, errors = compilar(d, root, True)
        self.assertNotIn('contacts', d)
        self.assertTrue(any(e['codigo'] == 'MODELO_NO_APRUEBA' for e in errors))

    def test_no_pisa_reglas_previas(self):
        previas = {'com_accel_max_m_s2': 20, 'joint_speed_max_deg_s': 600, 'slip_max_m_per_frame': 0.05, 'colliders': ['ya_medido']}
        d = {'rules': previas, 'contacts': [], 'argon_physics_proposal': propuesta(), 'inventario_fisico': inventario()}
        aplicar(d, d['argon_physics_proposal'], d['inventario_fisico'], prueba_cpu=True)
        self.assertEqual(d['rules']['colliders'], ['ya_medido'])

if __name__ == '__main__':
    unittest.main(verbosity=2)
