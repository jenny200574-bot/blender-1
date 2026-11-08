import sys,unittest,copy,json,uuid
from pathlib import Path
R=Path(__file__).resolve().parents[1];sys.path.insert(0,str(R/'motor'))
from seguridad import leer,guardar,sha
from anatomia_perfiles import compilar as anatomia
from objetos_adn import compilar as objetos
from vivo_binding import compilar as vivo
from reglas_binding import compilar as reglas,revisar_limites
from puente_sb4g import preparar
from movimientos import seleccionar
from bibliotecas import cargar,indexar
from causas import consolidar
class T(unittest.TestCase):
 def setUp(self):
  self.pk=R/'paquetes/fixture_no_facial_v5';self.d=leer(self.pk/'entrada_escena.json');self.cat=leer(R/'bibliotecas/formulas_star_estrictas.json');self.policy=leer(R/'bibliotecas/politica_busqueda_formas_cpu.json')
 def select(self,**kw):
  r={'action':'walk','anatomy':'declarative','emotion':'neutral','load':None,'support':'feet','context':'flat'};c=dict(r,id='nuevo',provider='catalogo',approval_ref='calidad_fixture',**kw);return seleccionar(r,[c],lambda c:('track',{}),lambda t,r:{'passed':True})
 def test_licencia_ausente_es_aviso_y_no_filtro(self):
  chosen,log=self.select();self.assertIsNotNone(chosen);self.assertTrue(any(x.get('estado')=='AVISO' for x in log))
 def test_calidad_sigue_obligatoria(self):
  r={'action':'walk','anatomy':'avian','emotion':'neutral','load':None,'support':'feet','context':'flat'};c=dict(r,id='x',provider='catalogo',approval_ref='validacion');chosen,_=seleccionar(r,[c],lambda c:('track',{}),lambda t,r:{'passed':False});self.assertIsNone(chosen)
 def test_sin_aprobacion_tecnica_bloquea_aunque_licencia_si(self):
  r={'action':'walk','anatomy':'avian','emotion':'neutral','load':None,'support':'feet','context':'flat'};c=dict(r,id='x',provider='catalogo',license_ref='licencia');chosen,_=seleccionar(r,[c],lambda c:('track',{}),lambda t,r:{'passed':True});self.assertIsNone(chosen)
 def test_restriccion_legal_es_aviso_tecnica_no(self):
  p=self.pk/'entrada_escena.json';ref={'path':p.name,'sha256':sha(p),'restricted':True};self.assertTrue(cargar(self.pk,ref));self.assertTrue(ref['warnings']);ref['technical_restricted']=True
  with self.assertRaises(ValueError):cargar(self.pk,ref)
 def test_indexado_no_filtra_licencia(self):
  p=self.pk/'entrada_escena.json';x=indexar([{'path':str(p),'role':'motion','approval_status':'VERIFICADA'}],self.pk);self.assertTrue(x[0]['runtime_enabled'])
 def test_anatomia_conecta_19_huesos_y_ancla_fuente(self):
  before=copy.deepcopy(self.d['entities'][0]['anatomy_profile']);r,e=anatomia(self.d);self.assertFalse(e);ent=self.d['entities'][0];self.assertEqual(ent['rig'],before['rig']);self.assertEqual(len(ent['rig']['bones']),19);self.assertEqual(ent['attachment'],before['attachment'])
 def test_perfil_no_suministrado_es_B_no_rig_estimado(self):
  self.d['entities'][0].pop('anatomy_profile');r,e=anatomia(self.d);self.assertTrue(e);self.assertTrue(all(x['tipo']=='completar dato' for x in e));self.assertNotIn('rig',self.d['entities'][0])
 def test_anatomia_desconocida_sigue_A(self):
  self.d['entities'][0]['anatomy']='desconocida';r,e=anatomia(self.d);self.assertEqual(e[0]['tipo'],'crear capacidad')
 def test_falta_dedo_no_se_disimula(self):
  self.d['entities'][0]['anatomy_profile']['rig']['bones'].pop();r,e=anatomia(self.d);self.assertTrue(e);self.assertNotIn('rig',self.d['entities'][0])
 def test_ancla_sin_offset_B(self):
  self.d['entities'][0]['anatomy_profile']['attachment'].pop('offset_m');r,e=anatomia(self.d);self.assertTrue(e)
 def test_apoyos_con_hueco_B(self):
  self.d['entities'][0]['anatomy_profile']['physics']['support_intervals'][0]['t0']=.1;r,e=anatomia(self.d);self.assertTrue(e)
 def test_pesos_incompletos_B(self):
  self.d['entities'][0]['anatomy_profile']['physics']['bone_mass_kg'].pop('root');r,e=anatomia(self.d);self.assertTrue(e)
 def test_limits_malformados_B_sin_crash(self):
  self.d['entities'][0]['anatomy_profile']['rig']['bones'][0]['limits_deg']='no';r,e=anatomia(self.d);self.assertTrue(e)
 def test_objeto_compuesto_por_ADN_llega_a_puntos_y_bisagras(self):
  r,e=objetos(self.d,self.pk,self.cat,self.policy);self.assertFalse(e);p=next(p for p in self.d['props'] if p['id']=='prop_fixture');self.assertEqual(len(p['geometry']),2);self.assertEqual(len(p['hinges']),1);self.assertEqual(p['shape_provenance']['step'],3)
 def test_ADN_objeto_sin_hash_no_se_lee(self):
  self.d['assets']=[];r,e=objetos(self.d,self.pk,self.cat,self.policy);self.assertTrue(e)
 def test_objeto_nombre_nuevo_no_adivina_alias(self):
  self.d['props'][-1]['id']='objeto_otra_identidad';r,e=objetos(self.d,self.pk,self.cat,self.policy);self.assertTrue(e)
 def test_objeto_solo_mirada_con_binding_no_requiere_ADN(self):
  self.d.pop('props');self.d['requirements']['object_refs']=['punto_de_atencion_nuevo'];self.d['bindings']={'punto_de_atencion_nuevo':{'scene_object_id':'punto_de_atencion_nuevo','reference_kind':'POINT','position_m':[0,0,0],'source':'medido'}};self.d['actions']=[{'id':'mira_nuevo','mirada_id':'punto_de_atencion_nuevo'}];r,e=objetos(self.d,self.pk,self.cat,self.policy);self.assertFalse(e);self.assertEqual(r['objects'][0]['state'],'SPATIAL_TARGET')
 def test_no_convertir_mueble_en_punto_por_ser_objeto_de_mirada(self):
  self.d.pop('props');self.d['requirements']['object_refs']=['prop_fixture'];self.d['actions']=[{'id':'mirada','mirada_id':'prop_fixture'}];r,e=objetos(self.d,self.pk,self.cat,self.policy);self.assertFalse(e);self.assertTrue(any(p['id']=='prop_fixture' and p['geometry'] for p in self.d['props']))
 def test_vivo_propiedades_y_tiempos_salen_de_01(self):
  r,e=vivo(self.d);self.assertFalse(e);self.assertEqual(r['changes_compiled'],2);ev=next(x for x in self.d['environment']['events'] if x['property']=='location');self.assertEqual([k['t'] for k in ev['keys']],[0,2]);self.assertEqual(ev['action_id'],'cambio_escena_nuevo')
 def test_vivo_idempotente_un_solo_escritor(self):
  vivo(self.d);r,e=vivo(self.d);self.assertFalse(e);self.assertEqual(len(self.d['environment']['events']),2)
 def test_vivo_sin_tiempo_no_lo_inventa(self):
  self.d['environment']['live_data']['changes'][1].pop('action_id');r,e=vivo(self.d);self.assertTrue(e)
 def test_vivo_incompleto_es_dato_productor(self):
  self.d['environment']['live_data']['status']='incomplete';r,e=vivo(self.d);self.assertTrue(any(x['codigo']=='VIVO_DATOS_FALTANTES' for x in e))
 def test_estado_narrativo_sin_asercion_no_se_declara_completo(self):
  self.d['environment']['live_data']['state_for_scene']={'inicio':['Pieza encendida'],'fin':['Pieza apagada']};r,e=vivo(self.d);self.assertTrue(any(x['codigo']=='VIVO_DATOS_FALTANTES' for x in e));self.assertEqual(len(r['unbound_states']),2)
 def test_estado_narrativo_con_aserciones_trazables(self):
  live=self.d['environment']['live_data'];live['state_for_scene']={'inicio':['Color inicial'],'fin':['Color final']};live['state_bindings']={'Color inicial':['estado_material_nuevo'],'Color final':['estado_material_nuevo']};r,e=vivo(self.d);self.assertFalse(e)
 def test_vivo_propiedad_no_implementada_sigue_A(self):
  self.d['environment']['live_data']['changes'][0]['property']='propiedad_desconocida';r,e=vivo(self.d);self.assertTrue(any(x['tipo']=='crear capacidad' for x in e))
 def test_reglas_preservan_todos_los_topes(self):
  anatomia(self.d);before=copy.deepcopy(self.d['rules']);r,e=reglas(self.d);self.assertFalse(e)
  for k,v in before.items():self.assertEqual(v,self.d['rules'][k])
  self.assertEqual(self.d['rules']['locked_naturalness'],self.d['locked_source_rules_not_yet_fully_integrated'])
 def test_equilibrio_distancia_rechaza(self):
  e=revisar_limites({'nuevo':[{'outside_m':.061,'balance_margin_m':.04,'hop':False}]},{'equilibrio_max_fuera_m':.06});self.assertTrue(e)
 def test_equilibrio_duracion_rechaza(self):
  e=revisar_limites({'nuevo':[{'outside_m':.05,'balance_margin_m':.04,'hop':False}]*3},{'equilibrio_cuadros_fuera_max':2});self.assertTrue(e)
 def test_saltito_cero_rechaza_uno(self):
  self.assertTrue(revisar_limites({'nuevo':[{'outside_m':0,'balance_margin_m':.04,'hop':True}]},{'saltitos_max':0}))
 def test_limites_inclusivos_y_aire_sin_hop(self):
  self.assertFalse(revisar_limites({'nuevo':[{'outside_m':.06,'balance_margin_m':.04,'hop':False}]*2},{'equilibrio_max_fuera_m':.06,'equilibrio_cuadros_fuera_max':2,'saltitos_max':0}))
 def test_4g_tiempos_relativos_y_absolutos_son_el_mismo_comando(self):
  pk=R/'paquetes/guardianes_no_facial_v5';d=leer(pk/'entrada_escena.json');r,e=preparar(d,pk);self.assertFalse(e);self.assertEqual(r['state'],'READY')
 def test_4g_una_fuente_modificada_no_pasa_hash(self):
  pk=R/'paquetes/fixture_4g_v5';d=leer(pk/'entrada_escena.json');d['assets']=[a for a in d['assets'] if a['path']!=d['camera']['resolver_inputs']['commands']];r,e=preparar(d,pk);self.assertTrue(e)
 def test_consolidacion_12_cotas_son_6_causas_no_12(self):
  errors=[dict(campo='entities/'+i+'/dna/'+f,modulo='ADN',codigo='ADN_COTA_NO_DEFINIDA',grupo='B',mensaje='dato') for i in ['a','b','c','d','e','f'] for f in ['face','garment']];r=consolidar(errors);self.assertEqual(r['B_diagnostic_rows'],12);self.assertEqual(r['B_causes'],6)
 def test_consolidacion_truncado_contactos_misma_causa(self):
  errors=[dict(campo=f,modulo='fuente',codigo='JSON_TRUNCADO' if i==0 else 'DATO_FALTANTE',grupo='B',mensaje='dato') for i,f in enumerate(['motion/respuesta_2b.json','2B','motion/status','motion/contacts'])];r=consolidar(errors);self.assertEqual(r['B_causes'],1);self.assertEqual(r['B_diagnostic_rows'],4)
 def test_consolidacion_no_omite_A_no_faciales(self):
  r=consolidar([{'grupo':'A','campo':'entities/nuevo/rig'}]);self.assertEqual(r['A_other'],1)
if __name__=='__main__':
 result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(T));guardar(R/'evidencia/pruebas_no_facial_v5.json',{'tests':result.testsRun,'passed':result.wasSuccessful(),'errors':len(result.errors),'failures':len(result.failures),'spend_usd':0});sys.exit(not result.wasSuccessful())
