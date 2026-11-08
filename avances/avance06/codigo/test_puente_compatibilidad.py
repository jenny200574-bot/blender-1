import importlib.util,json,re,unittest,sys,subprocess
from pathlib import Path
B=Path('/opt/myia-motor-v9/avance06_20261107');E=B/'entrega';spec=importlib.util.spec_from_file_location('bridge',E/'codigo/puente_json.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
class Tests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.K=m.legacy()['_cubo']();r=json.loads((E/'config/bird2_sources.json').read_text())['record'];cls.text=r['source_data']['text'];blocks=re.split(r'(?m)(?=^[1-5]\. )',cls.text);blocks=[x.strip() for x in blocks if x.strip()];assert len(blocks)==5;cls.obj={'schema':'ako_json/v1','id':r['id'],'clase':'personaje',**{f'bloque_{i}':b for i,b in enumerate(blocks,1)}}
 def test_old_text_unchanged(self):self.assertEqual(m.ako_text(self.text,'personaje',self.obj['id']),self.text)
 def test_json_converts_to_same_document(self):self.assertEqual(m.ako_text(self.obj,'personaje',self.obj['id']),self.text)
 def test_actual_parse_ako_accepts_both(self):
  for v in [self.text,self.obj]:self.assertEqual(self.K['parse_ako'](m.ako_text(v,'personaje',self.obj['id']),'personaje')['status'],'PASS_SELLABLE')
 def test_identity_rejected(self):
  with self.assertRaises(ValueError):m.ako_text(self.obj,'personaje','wrong-id')
 def test_missing_block_rejected(self):
  obj=self.obj.copy();obj.pop('bloque_3')
  with self.assertRaises(ValueError):m.ako_text(obj,'personaje',self.obj['id'])
 def test_gates_exist_and_cap(self):
  self.assertTrue((B/'pago_adn_json.off').exists());d=json.loads((E/'evidencias/ledger.json').read_text());self.assertEqual(d['step_cap_usd'],10);self.assertLessEqual(d['step_gross_usd']+d['reserved_usd'],10)
 def test_root_owned_wrapper(self):
  for p in [E/'codigo/puente_json.sh',E/'codigo/puente_json.py',E/'config/registry.json']:self.assertEqual(p.stat().st_uid,0);self.assertFalse(p.stat().st_mode&0o022)
if __name__=='__main__':unittest.main(verbosity=2)
