import sys,json,copy,unittest
from pathlib import Path
R=Path(__file__).resolve().parents[1];sys.path.insert(0,str(R/'motor'))
from puentes_fisicos import reglas,contactos,compilar,MAP
from seguridad import guardar
class Tests(unittest.TestCase):
 def setUp(self):self.d=json.loads((R/'paquetes/fixture_aviar_integracion/entrada_escena.json').read_text())
 def test_reglas_canonicas_no_cambian_un_numero(self):
  result,e=reglas(self.d['rules']);self.assertEqual(e,[])
  for k,v in result.items():self.assertEqual(v,self.d['rules'][k])
 def test_reglas_espanol_conversion_cm_por_cuadro(self):
  back={v:k for k,v in MAP.items()};source={back.get(k,k):v for k,v in self.d['rules'].items()};source['resbale_max_cm_cuadro']=source.pop('slip_max_m_per_frame')*100;result,e=reglas(source);self.assertEqual(e,[]);self.assertEqual(result['slip_max_m_per_frame'],self.d['rules']['slip_max_m_per_frame'])
 def test_no_inventar_umbral_ausente(self):
  result,e=reglas({});self.assertIsNone(result);self.assertTrue(e);self.assertTrue(all(x['tipo']=='completar dato' for x in e))
 def test_limites_alias_contradictorios_bloquean(self):
  source=copy.deepcopy(self.d['rules']);source['penetracion_max_m']=source['penetration_tolerance_m']+1;self.assertTrue(any(x['codigo']=='CONFLICTO' for x in reglas(source)[1]))
 def test_resbale_texto_no_crashea(self):
  source=copy.deepcopy(self.d['rules']);source['resbale_max_cm_cuadro']='cinco';self.assertTrue(reglas(source)[1])
 def test_intervalo_espanol_malformado_no_crashea(self):
  for t in [4,[],[1],None]:
   c={'actor':'nuevo','hueso':'efector','objetivo_punto':'punto','cadena':2,'iteraciones':4,'t':t,'tolerancia_m':.001};result,e=contactos([c],3);self.assertIsNone(result);self.assertTrue(e)
 def test_manifest_no_diccionario_o_pieza_no_objeto_no_crashea(self):
  source=copy.deepcopy(self.d['rules']);source.pop('colliders')
  for m in [[],{'complete':True,'objects':[None]},{'complete':True}]:self.assertTrue(reglas(source,m)[1])
 def test_programa_suelto_sin_hash_no_se_consume(self):
  import uuid
  root=R/'evidencia'/('negativo_programa_sin_hash_'+uuid.uuid4().hex);root.mkdir();guardar(root/'programa_2b.json',{'status':'complete','contacts':[]});d=copy.deepcopy(self.d);d.pop('contacts');d['assets']=[];receipt,e=compilar(d,root,True);self.assertNotIn('contacts',d);self.assertTrue(any(x['codigo']=='FUENTE_NO_VERIFICADA' for x in e))
 def test_contacto_espanol_conserva_actor_y_punto(self):
  result,e=contactos([{'actor':'actor_nuevo','hueso':'efector_dato','objetivo_punto':'mueble_nuevo.pin','cadena':2,'iteraciones':128,'t':[1,2],'tolerancia_m':.001}],3);self.assertEqual(e,[]);self.assertEqual(result[0]['entity'],'actor_nuevo');self.assertEqual(result[0]['target_point'],'mueble_nuevo.pin')
 def test_contacto_tiempo_texto_no_crashea(self):
  c=copy.deepcopy(self.d['contacts'][0]);c['t0']='uno';result,e=contactos([c],2);self.assertIsNone(result);self.assertTrue(e)
 def test_no_convertir_contactos_ausentes_en_lista_vacia(self):
  result,e=contactos(None,2);self.assertIsNone(result);self.assertEqual(e[0]['modulo'],'01/2B + Star')
 def test_collider_sin_rol_no_se_adivina_por_nombre(self):
  source=copy.deepcopy(self.d['rules']);source.pop('colliders');result,e=reglas(source,{'complete':True,'objects':[{'id':'piso_del_canal_que_no_se_debe_inferir'}]});self.assertIsNone(result);self.assertTrue(e)
 def test_collider_explicito_si_marcadores_no(self):
  source=copy.deepcopy(self.d['rules']);source.pop('colliders');result,e=reglas(source,{'complete':True,'objects':[{'id':'malla_nueva','collider':True},{'id':'marcador_nuevo','collider':False}]});self.assertEqual(e,[]);self.assertEqual(result['colliders'],['malla_nueva'])
 def test_fuente_guardianes_incompleta_sigue_bloqueada_sin_defaults(self):
  d=json.loads((R/'paquetes/guardianes/entrada_escena.json').read_text());receipt,e=compilar(d,R/'paquetes/guardianes',True);self.assertTrue(e);self.assertNotIn('contacts',d);self.assertEqual(d['_physical_bridge_status']['rules'],'WAITING_PRODUCER')
if __name__=='__main__':
 result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(Tests));guardar(R/'evidencia/pruebas_puentes_fisicos.json',{'tests':result.testsRun,'passed':result.wasSuccessful(),'errors':len(result.errors),'failures':len(result.failures),'spend_usd':0});sys.exit(not result.wasSuccessful())
