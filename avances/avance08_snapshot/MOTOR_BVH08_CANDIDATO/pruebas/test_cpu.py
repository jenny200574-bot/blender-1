import sys,unittest,copy,tempfile,json,socket
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'motor'))
from contrato import validar,cargar,desenvolver
from seguridad import *
from movimientos import seleccionar
from eventos import valor,validar_eventos
from cinematica_camara import trayectoria
from montaje import planificar
from pulida_estricta import pulir

class CPU(unittest.TestCase):
 def setUp(self):
  # No cleanup: conservar artefactos de cada prueba como exige la regla de archivo.
  self.root=Path(tempfile.mkdtemp(prefix='cpu_',dir=ROOT/'evidencia'))
  p=self.root/'programa.json';p.write_text('{}')
  self.d={'schema_version':'1.0','scene':'fixture_datos','clock':{'fps':24,'duration_s':2,'rounding':'half_up'},'coordinates':{'unit':'m','up':'Z','forward':'Y','origin':[0,0,0],'source':'fixture'},'sources':[{'module':'fixture','path':p.name,'sha256':sha(p)}],'assets':[{'path':p.name,'sha256':sha(p),'bytes':p.stat().st_size}],'entities':[{'id':'actor_A','type':'CHARACTER','anatomy':'humanoid','appearance':{k:{'asset':p.name,'source':'fixture'} for k in ['rostros_finales','ropa_final']}}],'requirements':{'entity_ids':['actor_A']},'environment':{'live_data':{'status':'complete'}},'motion':{'status':'complete','catalog':p.name,'assignments':p.name},'camera':{'shots':[{'id':'t1','t0':0,'t1':1,'transition':'CORTE'},{'id':'t2','t0':1,'t1':2,'transition':'CORTE'}]},'lighting':{'exposure':0,'base':[],'events':[],'source':'fixture'},'audio':{'tracks':['fixture'],'voices':['fixture'],'alignment':['fixture'],'facial_map':['fixture']},'libraries':[],'required_capabilities':['voz_final','labios_sincronizados','rostros_finales','ropa_final']}
 def codes(self,d):return [e['codigo'] for e in validar(d,self.root)]
 def test_estructura_positiva(self):self.assertEqual(validar(self.d,self.root),[])
 def test_audio_ausente_no_bloquea(self):
  del self.d['audio'];self.d['required_capabilities']=['rostros_finales','ropa_final'];self.assertEqual(validar(self.d,self.root),[])
 def test_campo_ausente(self):del self.d['lighting'];self.assertTrue(validar(self.d,self.root))
 def test_json_truncado(self):(self.root/'entrada_escena.json').write_text('{"x":');self.assertEqual(cargar(self.root)[1][0]['codigo'],'JSON_INVALIDO')
 def test_actor_omitido(self):self.d['requirements']['entity_ids'].append('actor_B');self.assertIn('ENTIDAD_OMITIDA',self.codes(self.d))
 def test_prop_no_humano(self):self.d['entities'][0].update(type='PROP',spec={'cabezas':5});self.assertIn('PROP_MAL_CLASIFICADO',self.codes(self.d))
 def test_ids_duplicados(self):self.d['entities']*=2;self.assertIn('ID_DUPLICADO',self.codes(self.d))
 def test_hash_distinto(self):self.d['assets'][0]['sha256']='0'*64;self.assertIn('HASH_DISTINTO',self.codes(self.d))
 def test_anatomia_no_soportada(self):self.d['entities'][0]['anatomy']='unknown';self.assertIn('ANATOMIA_NO_SOPORTADA',self.codes(self.d))
 def test_camara_ausente(self):self.d['camera']={};self.assertTrue(validar(self.d,self.root))
 def test_tiempo_ausente(self):del self.d['clock']['fps'];self.assertTrue(validar(self.d,self.root))
 def test_fuera_paquete(self):self.d['assets'][0]['path']='../externo';self.assertIn('RUTA_INVALIDA',self.codes(self.d))
 def test_cero_es_valido(self):self.assertEqual(self.d['lighting']['exposure'],0);self.assertFalse(validar(self.d,self.root))
 def test_no_claves_repetidas(self):
  p=self.root/'repetidas.json';p.write_text('{"x":1,"x":2}')
  with self.assertRaises(ValueError):leer(p)
 def test_envoltorio_n8n(self):self.assertEqual(desenvolver([{'json':{'stdout':'{"x":0}','exitCode':0}}]),{'x':0})
 def test_apariencia_no_opcional(self):self.d['required_capabilities']=[];self.assertTrue(validar(self.d,self.root))
 def test_10s_no_divide(self):self.d['clock']['duration_s']=11;self.d['camera']['shots']=[{'id':'t','t0':0,'t1':11,'transition':'CORTE'}];self.assertIn('TOMA_LARGA',self.codes(self.d))
 def test_cobertura1320_sin_duplicar(self):
  edges=[0,3,9,11,18,21,25,30,33,40,44,47.4,55]
  shots=[{'id':str(i),'t0':a,'t1':b,'transition':'CORTE','state':'APROBADA'} for i,(a,b) in enumerate(zip(edges,edges[1:]))]
  out=planificar(shots,24,55);self.assertEqual(sum(x['frames'] for x in out),1320);self.assertEqual(len(out),12)
 def test_no_montaje_parcial(self):
  with self.assertRaises(ValueError):planificar([{'id':'t','t0':0,'t1':2,'state':'BLOQUEADA'}],24,2)
 def test_no_fundido_silencioso(self):
  with self.assertRaises(ValueError):planificar([{'id':'t','t0':0,'t1':2,'state':'APROBADA','transition':'FUNDIDO'}],24,2)
 def test_pan_posicion_fija(self):
  spec={'mode':'PAN','position':[0,0,2],'target':[0,2,2],'degrees':90,'t0':0,'t1':1,'lens_mm':35};out=trayectoria(spec,24);self.assertEqual(len(out),24);self.assertTrue(all(x['position']==[0,0,2] for x in out));self.assertAlmostEqual(out[-1]['target'][0],-2)
 def test_crane_altura_medida(self):
  spec={'mode':'CRANE','position':[1,0,2],'target':[0,2,2],'height_m':1.5,'t0':0,'t1':1,'lens_mm':35};out=trayectoria(spec,24);self.assertAlmostEqual(out[-1]['position'][2],3.5)
 def test_pan_sin_datos_bloquea(self):
  with self.assertRaises(ValueError):trayectoria({'mode':'PAN','position':[0,0,0],'target':[0,1,0]},24)
 def test_crane_sin_datos_bloquea(self):
  with self.assertRaises(ValueError):trayectoria({'mode':'CRANE','position':[0,0,0],'target':[0,1,0]},24)
 def test_luz_reloj_global(self):
  keys=[{'t':0,'value':100,'curve':'LINEAR'},{'t':2,'value':0,'curve':'LINEAR'}];self.assertEqual(valor(keys,1),50);self.assertAlmostEqual(valor(keys,1-1e-8),valor(keys,1+1e-8),places=5)
 def test_apagon_no_suavizar(self):
  keys=[{'t':0,'value':100,'curve':'CONSTANT'},{'t':1,'value':0,'curve':'CONSTANT'}];self.assertEqual(valor(keys,.99),100);self.assertEqual(valor(keys,1),0)
 def test_dos_escritores_luz(self):
  e={'object':'l','property':'energy','source':'fixture','keys':[{'t':0,'value':0,'curve':'LINEAR'}]};self.assertTrue(validar_eventos([e,e],1))
 def test_semantica_no_levantarse_para_caminar(self):
  r={'action':'walk','anatomy':'humanoid','emotion':'neutral','load':'none','support':'feet','context':'flat'};c=dict(r,id='c',provider='kimodo',action='stand_up',license_ref='fixture',approval_ref='fixture');chosen,log=seleccionar(r,[c],lambda _:self.fail('No debe retargetear candidato incompatible'),lambda *_:self.fail('No debe revisar'));self.assertIsNone(chosen);self.assertEqual(log[0]['estado'],'INCOMPATIBLE')
 def test_escalera_orden_y_revisor(self):
  r={'action':'walk','anatomy':'humanoid','emotion':'neutral','load':'none','support':'feet','context':'flat'};c=[dict(r,id=x,provider=x,license_ref='fixture',approval_ref='fixture') for x in ['cmu','kimodo','catalogo','argon']];chosen,log=seleccionar(r,c,lambda c:(c['id'],{}),lambda track,r:{'passed':track=='kimodo'});self.assertEqual(chosen['candidate']['id'],'kimodo');self.assertEqual([x['provider'] for x in log],['argon','catalogo','kimodo'])
 def test_pulida_firma_real(self):
  class Backend:
   def polish_bvh(inner,src,dst,*,do_smooth,do_footlock,npz,unit_scale):self.assertTrue(do_smooth);self.assertFalse(do_footlock);self.assertEqual(unit_scale,.01);return {'footlock_applied':False}
  self.assertIn('footlock_applied',pulir('in.bvh',self.root/'out.bvh',unit_scale=.01,footlock=False,backend=Backend()))
 def test_pulida_off_no_se_ignora(self):
  p=self.root/'pulida.off';p.write_text('')
  with self.assertRaises(ValueError):pulir('in',self.root/'out',unit_scale=1,footlock=False,switch=p,backend=object())
 def test_footlock_sin_fk_bloquea(self):
  with self.assertRaises(ValueError):pulir('in',self.root/'out',unit_scale=1,footlock=True)
 def test_no_silencia_excepcion_pulida(self):
  class Backend:
   def polish_bvh(*args,**kw):raise RuntimeError('fallo real')
  with self.assertRaises(RuntimeError):pulir('in',self.root/'out',unit_scale=1,footlock=False,backend=Backend())
 def test_formato_incorrecto_bloquea(self):
  self.d['entities']='texto';self.assertIn('TIPO_INVALIDO',self.codes(self.d))
 def test_objeto_requerido_sin_binding(self):
  self.d['requirements']['object_refs']=['obj_A'];self.assertIn('OBJETO_SIN_BINDING',self.codes(self.d))
 def test_alias_ambiguo_no_adivina(self):
  from bibliotecas import resolver_id
  with self.assertRaises(ValueError):resolver_id('libro',[{'id':'a','exact_aliases':['libro']},{'id':'b','exact_aliases':['libro']}])
 def test_biblioteca_restringida_no_se_activa(self):
  from bibliotecas import cargar as cargar_biblioteca
  p=self.root/'programa.json'
  with self.assertRaises(ValueError):cargar_biblioteca(self.root,{'path':p.name,'sha256':sha(p),'restricted':True,'technical_restricted':True})
 def test_corte_seco_es_corte_exacto(self):
  self.assertEqual(len(planificar([{'id':'a','t0':0,'t1':1,'state':'APROBADA','transition':'CORTE_SECO'},{'id':'b','t0':1,'t1':2,'state':'APROBADA','transition':'FIN_ESCENA'}],24,2)),2)
 def test_fin_escena_no_anticipado(self):
  with self.assertRaises(ValueError):planificar([{'id':'a','t0':0,'t1':1,'state':'APROBADA','transition':'FIN_ESCENA'},{'id':'b','t0':1,'t1':2,'state':'APROBADA','transition':'CORTE'}],24,2)
 def test_presupuesto0_sin_red(self):
  import importlib.util
  spec=importlib.util.spec_from_file_location('runner',ROOT/'motor_unico.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
  guardar(self.root/'entrada_escena.json',self.d);old=socket.socket
  socket.socket=lambda *a,**kw:(_ for _ in ()).throw(AssertionError('Red prohibida'))
  try:r=m.ejecutar(self.root/'entrada_escena.json',self.root/'salida',True)
  finally:socket.socket=old
  self.assertEqual(r['gasto_usd'],0);self.assertFalse(r['execution_policy']['gpu_enabled']);self.assertEqual(r['estado'],'BLOQUEADO')

if __name__=='__main__':
 suite=unittest.defaultTestLoader.loadTestsFromTestCase(CPU);result=unittest.TextTestRunner(verbosity=2).run(suite)
 guardar(ROOT/'evidencia/pruebas_cpu.json',{'run':result.testsRun,'failures':len(result.failures),'errors':len(result.errors),'passed':result.wasSuccessful(),'synthetic_fixtures':True});sys.exit(not result.wasSuccessful())
