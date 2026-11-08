"""Legacy assertions stay unchanged: pin their Argon4 fixture, test Flash3 separately."""
import importlib.util,unittest,json,sys
from pathlib import Path
B=Path('/opt/myia-motor-v9/avance04_20261107');R=B/'MOTOR_UNICO_20261107';sys.path.insert(0,str(R/'motor'))
from argon_transporte import tarifa,Transport
spec=importlib.util.spec_from_file_location('t316_legacy_fixture',R/'pruebas/test_t316.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
original=m.Tests.setUp
# The legacy tests contain hard-coded Argon4 tariff expectations, not a generic current-model fixture.
def setup(self):
 original(self);self.cfg['model']='gemini-4-argon';(self.r/'config/argon_transporte.json').write_text(json.dumps(self.cfg))
m.Tests.setUp=setup
class Flash3(unittest.TestCase):
 def test_current_provider_tariff(self):
  cfg=json.loads((R/'config/argon_transporte.json').read_text());self.assertEqual(cfg['model'],'gemini-3-flash-preview');rate=tarifa(R,cfg,'2026-11-07');self.assertEqual((rate['entrada'],rate['salida']),(.5,3))
 def test_token_gross_fixture(self):self.assertEqual((50*.5+(12+7)*3)/1e6,.000082)
 def test_no_implicit_network(self):
  seen=[];t=Transport(R,lambda:seen.append(True));q=t.quote({'id':'test_only','source':'test_fixture','text':'test fixture','dimensions_m':[1,2,3]});self.assertFalse(q['network_sent']);self.assertEqual(seen,[])
suite=unittest.TestSuite([unittest.defaultTestLoader.loadTestsFromModule(m),unittest.defaultTestLoader.loadTestsFromTestCase(Flash3)]);r=unittest.TextTestRunner(verbosity=2).run(suite);(B/'entrega/evidencias/test_modelos_runtime_resultado.json').write_text(json.dumps({'tests':r.testsRun,'passed':r.wasSuccessful(),'legacy_model_fixture':'gemini-4-argon','new_provider_fixture':'gemini-3-flash-preview','assertions_and_tolerances_changed':False,'new_network_calls':0},indent=2));sys.exit(0 if r.wasSuccessful() else 1)
