import unittest,tempfile,json,sys,copy
from pathlib import Path
from types import SimpleNamespace as NS
R=Path(__file__).resolve().parents[1];sys.path.insert(0,str(R/'motor'))
from argon_transporte import Transport,tarifa,pedido
from recetas_proveedor import Ledger
class Tests(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory();self.r=Path(self.temp.name);(self.r/'config').mkdir();self.cfg=json.loads((R/'config/argon_transporte.json').read_text());(self.r/'config/argon_transporte.json').write_text(json.dumps(self.cfg));(self.r/'config/tarifas_argon.json').write_bytes((R/'config/tarifas_argon.json').read_bytes());self.q={'id':'objeto_inesperado','dimensions_m':[1,2,3],'text':'mueble medido','source':'fixture'}
 def tearDown(self):self.temp.cleanup()
 def test_01_tarifa_existente(self):
  t=tarifa(self.r,self.cfg,'2026-11-07');self.assertEqual((t['entrada'],t['salida']),(2,10));t=tarifa(self.r,self.cfg,'2026-12-01');self.assertEqual((t['entrada'],t['salida']),(4,20))
 def test_02_sin_tramo_bloquea(self):self.assertRaises(ValueError,tarifa,self.r,self.cfg,'2026-01-01')
 def test_03_stream_1800_y_limite_real(self):
  p=pedido(self.q,self.cfg);self.assertTrue(p['stream']);self.assertEqual(p['timeout_s'],1800);self.assertEqual(p['max_output_tokens'],65536)
 def test_04_seco_reserva_antes_y_libera(self):
  called=[];t=Transport(self.r,lambda:called.append(1));r=t.prepare(self.q);d=json.loads((self.r/'evidencia/ledger.json').read_text());self.assertEqual(called,[]);self.assertEqual(d['spent_usd'],0);self.assertEqual(d['reserved_usd'],0);self.assertEqual(d['entries'][0]['state'],'SETTLED');self.assertGreater(r['reserve_usd'],r['estimated_usd'])
 def test_05_seco_bloquea_antes_de_cliente(self):
  called=[];t=Transport(self.r,lambda:called.append(1));self.assertRaises(ValueError,t,self.q,{'authorized':True,'reserved_usd':3});self.assertEqual(called,[])
 def test_06_off_bloquea_aun_habilitado(self):
  self.cfg['dry_run']=False;(self.r/'config/argon_transporte.json').write_text(json.dumps(self.cfg));(self.r/'config/argon_envio.off').touch();called=[];t=Transport(self.r,lambda:called.append(1));self.assertRaises(ValueError,t,self.q,{'authorized':True,'reserved_usd':3});self.assertEqual(called,[])
 def test_07_reserva_insuficiente_antes_cliente(self):
  self.cfg['dry_run']=False;(self.r/'config/argon_transporte.json').write_text(json.dumps(self.cfg));called=[];t=Transport(self.r,lambda:called.append(1));self.assertRaises(ValueError,t,self.q,{'authorized':True,'reserved_usd':0});self.assertEqual(called,[])
 def test_08_stream_mock_descarta_thought_cobra_tokens(self):
  self.cfg['dry_run']=False;(self.r/'config/argon_transporte.json').write_text(json.dumps(self.cfg));seen=[]
  def stream(**kwargs):
   seen.append(kwargs['config'].max_output_tokens);return iter([NS(candidates=[NS(content=NS(parts=[NS(thought=True,text='NO MOSTRAR'),NS(thought=False,text=json.dumps({'source':'fixture','parts':[{'id':'piece','shape':'ELLIPSOID','position_m':[0,0,0],'rotation_deg':[0,0,0],'dimensions_m':[1,2,3],'resolution':16,'material':{'rgba':[.4,.2,.1,1],'roughness':.5,'metallic':0},'source':'fixture'}]}))]),finish_reason='STOP')],usage_metadata=NS(prompt_token_count=50,candidates_token_count=12,thoughts_token_count=7))])
  t=Transport(self.r,lambda:NS(models=NS(generate_content_stream=stream)));q=t.quote(self.q);ref=Ledger(self.r/'evidencia/ledger.json').before(q['reserve_usd'],'test',mock=True);out=t(self.q,ref);self.assertEqual(out['source'],'fixture');self.assertAlmostEqual(out['_usage_usd'],.00029);self.assertEqual(seen,[65536])
 def test_09_tope_total_3(self):
  l=Ledger(self.r/'evidencia/ledger.json');l.before(2.5,'test',mock=True);self.assertRaises(ValueError,l.before,.51,'test',True)
 def test_10_anatomia_no_certifica_datos_inferidos(self):
  q=dict(self.q,task='anatomy_review');p=pedido(q,self.cfg);self.assertIn('no certificación inventada',p['prompt']);self.assertEqual(p['task'],'anatomy_review')
if __name__=='__main__':unittest.main(verbosity=2)
