import unittest,tempfile,sys,json,threading,copy
from pathlib import Path
R=Path(__file__).resolve().parents[1];sys.path.insert(0,str(R/'motor'))
from seguridad import guardar,leer
from recetas_proveedor import Ledger
from argon_automatico import ejecutar,planificar,cache_get,agrupar,validate_one
from exposicion_auto import histograma,gate
class Tests(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory();self.r=Path(self.temp.name);(self.r/'config').mkdir()
  for f in ['argon_transporte.json','tarifas_argon.json','politica_ejecucion.json']:(self.r/'config'/f).write_bytes((R/'config'/f).read_bytes())
  self.items=[{'id':'nuevo_'+str(i),'dimensions_m':[1,2,3],'source':'fixture','text':'objeto nuevo'} for i in range(40)]
 def tearDown(self):self.temp.cleanup()
 def recipe(self,q):return {'source':'fixture','parts':[{'id':'pieza','shape':'ELLIPSOID','position_m':[0,0,0],'rotation_deg':[0,0,0],'dimensions_m':q['dimensions_m'],'resolution':16,'material':{'rgba':[.3,.2,.1,1],'roughness':.6,'metallic':0},'source':'fixture'}]}
 def provider(self,q,ref):
  self.assertTrue(ref['authorized']);self.assertTrue(any(x['id']==ref['id'] for x in leer(self.r/'evidencia/ledger.json')['entries']));return {'responses':[{'id':x['id'],'recipe':self.recipe(x)} for x in q['items']]}
 def test01_dry_no_provider(self):
  seen=[];r=ejecutar(self.r,self.items,'dry',lambda *a:seen.append(1));self.assertEqual(seen,[]);self.assertEqual(r['calls_count'],2);self.assertEqual(leer(self.r/'evidencia/ledger.json')['spent_usd'],0)
 def test02_parallel_and_cache(self):
  pol=leer(self.r/'config/politica_ejecucion.json');pol['tokens_salida_estimados_por_receta']=4000;guardar(self.r/'config/politica_ejecucion.json',pol);barrier=threading.Barrier(3);threads=set()
  def f(q,ref):threads.add(threading.get_ident());barrier.wait(timeout=5);return self.provider(q,ref)
  r=ejecutar(self.r,self.items,'mock',f,True);self.assertEqual(len(r['saved']),40);self.assertEqual(len(threads),3);self.assertEqual(ejecutar(self.r,self.items,'mock',self.provider,True)['calls_count'],0)
 def test03_repair_only_failed(self):
  seen=[]
  def f(q,ref):
   seen.append(len(q['items']));r=self.provider(q,ref)
   if not q['repair_errors']:r['responses'][0]['recipe']['parts'][0]['shape']='BOX'
   return r
  r=ejecutar(self.r,self.items[:3],'mock',f,True);self.assertEqual(seen,[3,1]);self.assertEqual(len(r['saved']),3)
 def test04_no_progress_falta(self):
  r=ejecutar(self.r,self.items[:1],'mock',lambda q,r:{'responses':[]},True);self.assertEqual(r['calls_count'],2);self.assertEqual(len(r['faltantes']),1)
 def test05_mock_real_root_rejected(self):self.assertRaises(ValueError,ejecutar,self.r,self.items,'mock',self.provider,False)
 def test06_single_budget_not_fixed_three(self):
  p=leer(self.r/'config/politica_ejecucion.json');p['presupuesto_total_usd']=4;guardar(self.r/'config/politica_ejecucion.json',p);l=Ledger(self.r/'evidencia/ledger.json');l.before(3.5,'fixture',True);self.assertRaises(ValueError,l.before,.51,'fixture',True)
 def test07_zero_budget_blocks(self):
  p=leer(self.r/'config/politica_ejecucion.json');p['presupuesto_total_usd']=0;guardar(self.r/'config/politica_ejecucion.json',p);r=ejecutar(self.r,self.items,'mock',self.provider,True);self.assertEqual(r['calls_count'],0);self.assertTrue(r['faltantes'])
 def test08_group_contracts(self):
  cfg=leer(self.r/'config/argon_transporte.json');p=leer(self.r/'config/politica_ejecucion.json');b=agrupar(self.items[:1]+[{'id':'otro','task':'anatomy_review','anatomy':'nocturna'}],cfg,p);self.assertEqual(len(b),2)
 def test09_recipe_dimensions_rejected(self):
  r=self.recipe(self.items[0]);r['parts'][0]['dimensions_m']=[9,9,9];self.assertRaises(ValueError,validate_one,r,self.items[0])
 def test10_unfounded_certification_rejected(self):self.assertRaises(ValueError,validate_one,{'status':'PROPOSAL','source':'fixture','profile':{'x':1},'certified':True},{'task':'anatomy_review'})
 def test11_unknown_ids_rejected(self):
  r=ejecutar(self.r,self.items[:1],'mock',lambda q,r:{'responses':[{'id':'ID-ajeno','recipe':self.recipe(self.items[0])}]},True);self.assertEqual(len(r['saved']),0)
 def test12_saturation_gate(self):
  from PIL import Image
  f=self.r/'a.png';Image.new('RGB',(10,10),(255,0,0)).save(f);s=histograma([f]);self.assertEqual(s['saturated_pct'],100);self.assertEqual(s['images'][0]['white_pct'],0);self.assertRaises(ValueError,gate,s,{'max_saturated_pct':.5});Image.new('RGB',(10,10),(128,128,128)).save(f);self.assertTrue(gate(histograma([f]),{'max_saturated_pct':.5}))
 def test13_quote_no_network(self):
  p=planificar(self.r,self.items);self.assertEqual(p['ungrouped']['calls'],40);self.assertEqual(p['grouped']['calls'],2);self.assertTrue(p['grouped']['within_budget']);self.assertFalse(p['ungrouped']['within_budget'])
 def test14_transport_failure_repaired(self):
  calls=[]
  def f(q,ref):
   calls.append(q)
   if len(calls)==1:raise ValueError('JSON mock inválido')
   return self.provider(q,ref)
  r=ejecutar(self.r,self.items[:1],'mock',f,True);self.assertEqual(len(r['saved']),1);self.assertEqual(r['calls_count'],2)
 def test15_off_preserved(self):
  (self.r/'config/argon_automatico.off').touch();r=ejecutar(self.r,self.items,'mock',self.provider,True);self.assertEqual(r['state'],'OFF');self.assertEqual(r['calls_count'],0)
 def test16_background_cache_bridge(self):
  from argon_automatico import aplicar_cache_entorno
  q=dict(self.items[0]);q['source']={'inventory':{'position_m':[1,2,3],'rotation_euler_rad':[0,0,1],'parent':None}}
  ejecutar(self.r,[q],'mock',self.provider,True);d={'fixture_only':True,'environment':{'unresolved_details':[{'id':q['id']}]}};r=aplicar_cache_entorno(self.r,d,[q]);self.assertEqual(len(r['applied']),1);self.assertEqual(d['props'][0]['position_m'],[1,2,3]);self.assertAlmostEqual(d['props'][0]['rotation_deg'][2],57.29577951308232)
  d={'environment':{'unresolved_details':[{'id':q['id']}]}};self.assertRaises(ValueError,aplicar_cache_entorno,self.r,d,[q])
 def test17_ledger_decimal_sin_residuo_negativo(self):
  l=Ledger(self.r/'evidencia/ledger.json');a=l.before(.696414,'fixture',True);b=l.before(.699652,'fixture',True);l.settle(a,0);l.settle(b,0);self.assertEqual(leer(l.path)['reserved_usd'],0)
if __name__=='__main__':unittest.main(verbosity=2)
