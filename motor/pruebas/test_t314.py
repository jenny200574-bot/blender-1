import unittest,tempfile,json,sys,copy,math
from pathlib import Path
R=Path(__file__).resolve().parents[1];sys.path.insert(0,str(R/'motor'))
from recetas_proveedor import Runtime,Ledger,validar,huella
from catalogos_crecimiento import registrar,reusar,bvh_info,conectar,buscar_bvh,configuracion_job
from apariencia_base_cpu import construir
from seguridad import leer,sha,guardar
class Pruebas(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name);self.q={'id':'figura_nueva_91','dimensions_m':[.6,.4,.8],'source':'ADN de prueba','text':'escultura ovoide'};self.recipe={'id':'receta_nueva','source':'mock documental','parts':[{'id':'cuerpo','shape':'ELLIPSOID','dimensions_m':[.6,.4,.8],'position_m':[0,0,0],'rotation_deg':[0,0,0],'resolution':24,'material':{'rgba':[.2,.4,.6,1],'metallic':0,'roughness':.5},'source':'mock'}]}
 def tearDown(self):self.tmp.cleanup()
 def runtime(self,provider=None):return Runtime(self.root/'recipes.json',self.root/'ledger.json',self.root/'provider.off',provider or (lambda q,r:self.recipe),0,True)
 def test_01_default_activo_ledger_previo_y_cache(self):
  calls=[]
  def provider(q,r):
   ledger=leer(self.root/'ledger.json');self.assertEqual(ledger['entries'][-1]['state'],'RESERVED_BEFORE_CALL');calls.append(q);return self.recipe
  rt=self.runtime(provider);rec,status=rt.generate(self.q);self.assertEqual(status['state'],'CREATED');self.assertTrue(rec['recipe_sha256']);self.assertTrue(rec['created_at']);self.assertEqual(rt.generate(self.q)[1]['state'],'CACHE');self.assertEqual(len(calls),1);self.assertEqual(leer(self.root/'ledger.json')['spent_usd'],0)
 def test_02_off_no_llamada(self):
  rt=self.runtime(lambda q,r:self.fail('Llamada apagada'));rt.switch.touch();self.assertEqual(rt.generate(self.q)[1]['state'],'OFF');self.assertFalse((self.root/'ledger.json').exists())
 def test_03_caja_no_guardada(self):
  self.recipe['parts'][0]['shape']='BOX';rec,state=self.runtime().generate(self.q);self.assertIsNone(rec);self.assertEqual(state['state'],'FALTA');self.assertFalse((self.root/'recipes.json').exists())
 def test_04_medidas_adn(self):
  self.recipe['parts'][0]['dimensions_m'][0]=1;self.assertIsNone(self.runtime().generate(self.q)[0])
 def test_05_no_fiar_validated(self):
  self.recipe['validated']=True;self.recipe['parts'][0]['dimensions_m'][0]=-1;self.assertIsNone(self.runtime().generate(self.q)[0])
 def test_06_cache_tamper(self):
  rt=self.runtime();rt.generate(self.q);d=leer(rt.library);d['recipes'][0]['parts'][0]['dimensions_m'][0]=77;guardar(rt.library,d);self.assertEqual(rt.generate(self.q)[1]['state'],'FALTA')
 def test_07_cap_total_y_reservas(self):
  l=Ledger(self.root/'ledger.json');a=l.before(2,'test');self.assertRaises(ValueError,l.before,1.01,'test');l.settle(a,2);b=l.before(1,'test');l.settle(b,1);self.assertRaises(ValueError,l.before,.01,'test');self.assertEqual(leer(l.path)['spent_usd'],3)
 def test_08_cargo_no_supera_reserva(self):
  l=Ledger(self.root/'ledger.json');a=l.before(.2,'test');self.assertRaises(ValueError,l.settle,a,.3);self.assertEqual(leer(l.path)['spent_usd'],0)
 def test_09_error_provider_falta(self):
  def f(q,r):raise RuntimeError('mock averiado')
  self.assertEqual(self.runtime(f).generate(self.q)[1]['state'],'FALTA')
 def test_10_malla_abierta(self):
  p=self.recipe['parts'][0];p.update(shape='MESH',vertices_m=[[0,0,0],[1,0,0],[0,1,0]],faces=[[0,1,2]]);self.assertRaises(ValueError,validar,self.recipe,self.q)
 def entity(self):return {'id':'habitante_nuevo_707','type':'CHARACTER','anatomy':'humanoid','dna_record':{'source':'ADN sintético','source_data':{'height_m':1.7,'heads':6,'text':'1. Ficha Antropométrica:\nAltura 1.7 m\n2. Fisonomía Facial y Cabello:\nRostro triangular de piel morena.\nCabello gris plateado largo.\nOjos almendrados marrones.\nGafas cian translúcidas.\n4. Vestuario por Capas:\nPrenda exterior: chaqueta roja.\nPrenda inferior: pantalón azul.\nCalzado negro.'}}}
 def test_11_base_real_y_procedencia(self):
  g,r,e=construir(self.entity());self.assertFalse(e);self.assertGreater(len(g['parts']),20);self.assertTrue(all(p['library_dimensions']['status']=='de biblioteca' for p in g['parts']));self.assertTrue(any(p['role']=='clothes' and p['shape']=='MESH' for p in g['parts']));self.assertTrue(any(p['id'].endswith('hair_long') for p in g['parts']))
 def test_12_colores_texto_y_cabello_no_encabezado(self):
  g,_,_=construir(self.entity());self.assertEqual(next(p for p in g['parts'] if p['id'].endswith('hair'))['material']['rgba'],[.55,.55,.58,1]);self.assertEqual(next(p for p in g['parts'] if p['id'].endswith('jacket'))['material']['rgba'],[.8,.035,.025,1])
 def test_13_nombres_nuevos_no_cambian_formas(self):
  a=self.entity();b=copy.deepcopy(a);b['id']='otro_ser_800';g,_,_=construir(a);h,_,_=construir(b);self.assertEqual([p.get('vertices_m') for p in g['parts']],[p.get('vertices_m') for p in h['parts']])
 def test_14_gafas_negadas(self):
  a=self.entity();a['dna_record']['source_data']['text']=a['dna_record']['source_data']['text'].replace('Gafas cian translúcidas.','Sin gafas.');g,_,_=construir(a);self.assertFalse(any('glasses' in p['id'] for p in g['parts']))
 def test_15_gpu_slot_off(self):self.assertFalse(construir(self.entity())[0]['final_appearance_ref']['gpu_adapter_slot']['enabled'])
 def test_16_altura_ausente_no_inventada(self):
  a=self.entity();del a['dna_record']['source_data']['height_m'];g,r,e=construir(a);self.assertIsNone(g);self.assertTrue(e)
 def bvh(self):return R/'evidencia/pulida_real/pulido.bvh'
 def register(self,origin='kimodo',metrics=None):
  info=bvh_info(self.bvh());return registrar(self.root/'motions',self.bvh(),origin=origin,source={'source':'BVH existente de prueba','input_sha256':info['sha256']},skeleton={'bones':info['joint_names']},profile={'test_only':True},metrics=metrics or {'all_passed':True,'errors':[],'frames_measured':info['frames']},request={'action':'andar','anatomy':'humanoid','emotion':'neutral','load':None,'support':'floor','context':'prueba técnica'},prompt='andar',tracks=[])
 def test_17_registro_bvh_campos_y_reuso(self):
  result=self.register();rec=result['record'];self.assertEqual(result['state'],'ADDED');self.assertEqual(self.register()['state'],'REUSED');self.assertGreater(rec['duration_s'],0);self.assertTrue(rec['metrics']);self.assertTrue(rec['sha256']);self.assertTrue(reusar(self.root/'motions',rec['request'],rec['skeleton'],rec['profile']))
 def test_18_origenes_comunes(self):
  for origin in ['cmu','retarget','video','mixamo']:self.assertEqual(self.register(origin)['state'],'ADDED' if origin=='cmu' else 'REUSED')
 def test_19_fallo_tecnico_no_se_guarda(self):self.assertRaises(ValueError,self.register,metrics={'all_passed':False,'errors':['slip'],'frames_measured':48})
 def test_20_sin_metricas_no_sello(self):self.assertRaises(ValueError,self.register,metrics={'all_passed':True,'errors':[]})
 def test_21_cache_movimiento_alterado(self):
  rec=self.register()['record'];p=self.root/'motions'/rec['path'];p.write_text('alterado');self.assertIsNone(reusar(self.root/'motions',rec['request']))
 def test_22_perfil_diferente_no_reusa(self):
  rec=self.register()['record'];self.assertIsNone(reusar(self.root/'motions',rec['request'],rec['skeleton'],{'other':True}))
 def test_26_orden_entorno_luces_sin_alias(self):
  from eventos import separar_por_dependencias
  events=[{'object':'mueble_nuevo','property':'location'},{'object':'luz_nueva','property':'location'},{'object':'cielo_nuevo','property':'world.background_color'},{'object':'otra_luz','property':'energy'}];before,after=separar_por_dependencias(events,['luz_nueva']);self.assertEqual(before,events[:1]);self.assertEqual(after,events[1:]);self.assertEqual(len(before)+len(after),len(events))
 def test_25_enterizo_cubre_brazos_piernas(self):
  e=self.entity();e['dna_record']['source_data']['text']+='\nPrenda exterior: enterizo azul.';g,_,_=construir(e);covered={p['bind_role'] for p in g['parts'] if p['role']=='clothes'};self.assertTrue({'forearm_left','shin_right','hand_left'}<=covered);self.assertTrue(any(p.get('hidden_under_garment') for p in g['parts']));self.assertTrue(all(p['library_dimensions'].get('generator_sha256') for p in g['parts']))
 def test_24_broadphase_no_falso_positivo(self):
  from fisica_final import aabb_separados
  self.assertTrue(aabb_separados([[0,0,0],[.5,.5,.5]],[[.8,0,0],[1.4,.5,.5]]));self.assertFalse(aabb_separados([[0,0,0],[1,1,1]],[[.8,.8,.8],[1.8,1.8,1.8]]))
 def test_23_perfiles_genericos(self):
  for p in (R/'bibliotecas/star/catalogos').glob('humanoide_adulto_*.json'):
   d=leer(p);self.assertEqual(d['schema'],'anatomical_profile_v1');self.assertNotIn('personaje',d);self.assertTrue(d['examples']);self.assertTrue(d['source']['original_sha256'])
if __name__=='__main__':unittest.main(verbosity=2)
