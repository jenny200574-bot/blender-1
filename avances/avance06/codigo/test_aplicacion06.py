import unittest,json,hashlib,math
from pathlib import Path
B=Path('/opt/myia-motor-v9/avance06_20261107');E=B/'entrega';P=B/'esc1_candidata';OLD=B/'esc1_antes'
def read(p):return json.loads(p.read_text())
class Tests(unittest.TestCase):
 def test_manifest_assets_sources(self):
  d=read(P/'entrada_escena.json')
  for a in d['assets']:self.assertEqual(hashlib.sha256((P/a['path']).read_bytes()).hexdigest(),a['sha256']);self.assertEqual((P/a['path']).stat().st_size,a['bytes'])
  for s in d['sources']:self.assertEqual(hashlib.sha256((P/s['path']).read_bytes()).hexdigest(),s['sha256'])
 def test_no_2b_fabrication(self):
  for n in ['respuesta_2b.json','programa_2b.json','catalogo_poses_escena.json','asignacion_para_motor.json']:self.assertEqual((OLD/n).read_bytes(),(P/n).read_bytes())
 def test_no_physics_or_coordinates_invention(self):
  a=read(OLD/'entrada_escena.json');b=read(P/'entrada_escena.json')
  for k in ['coordinates','rules','rules_source','locked_source_rules_not_yet_fully_integrated']:self.assertEqual(a.get(k),b.get(k))
 def test_bone_numbers_unchanged(self):
  raw=read(E/'evidencias/av06_bird02/respuesta.json');canonical=read(P/'argon_piquito06_rig.json')
  self.assertEqual(len(canonical['rig']['bones']),19)
  for r,c in zip(raw['bones'],canonical['rig']['bones']):
   self.assertEqual(c['head'],[r['h'+k] for k in 'xyz']);self.assertEqual(c['tail'],[r['t'+k] for k in 'xyz']);self.assertEqual(c['limits_deg'],[[r['lim_'+k+'_min'],r['lim_'+k+'_max']] for k in 'xyz'])
 def test_all_appearance_numbers_from_model(self):
  raw=read(E/'evidencias/av06_bird_appearance02/respuesta.json');patch=read(E/'evidencias/av06_crest03/respuesta.json');a=read(P/'argon_piquito06_apariencia.json');self.assertEqual(len(a['parts']),40)
  for r,c in zip(raw['parts'],a['parts']):
   expected=[r['p'+k] for k in 'xyz']
   if r['feature'] in ['crest.1','crest.2']:expected[2]=patch['crest1_pz' if r['feature']=='crest.1' else 'crest2_pz']
   self.assertEqual(c['position_m'],expected);self.assertEqual(c['rotation_deg'],[r['r'+k] for k in 'xyz']);self.assertEqual(c['dimensions_m'],[r['d'+k] for k in 'xyz']);self.assertEqual(c['material']['rgba'],[r[k] for k in ['r','g','b','a']]);self.assertEqual(c['role'],r['feature'])
 def test_light_numbers_from_model(self):
  raw=read(E/'evidencias/av06_light02/respuesta.json');patch=read(E/'evidencias/av06_lightworld03/respuesta.json');a=read(P/'argon_luces06.json')
  for i,c in enumerate(a['base'],1):
   self.assertEqual(c['size'],raw[f'l{i}_size']);self.assertEqual(c['energy'],raw[f'l{i}_energy']);self.assertEqual(c['position_m'],[raw[f'l{i}_p{k}'] for k in 'xyz']);self.assertEqual(c['rotation_deg'],[math.degrees(raw[f'l{i}_r{k}']) for k in 'xyz'])
  self.assertEqual(a['world']['color_rgba'],[raw['world_'+k] for k in 'rgb']+[patch['world_a']])
 def test_cpu_blocks_and_blender_build_passed(self):
  d=read(E/'evidencias/preview_cpu_final_resultado.json');self.assertEqual(d['estado'],'BLOQUEADO');self.assertIsNone(d['master']);self.assertFalse(d['gpu_used']);self.assertEqual(d['paid_network_calls_in_preview'],0);self.assertTrue(read(E/'evidencias/blender_diseno_world_resultado.json')['passed'])
 def test_ledger_and_switches(self):
  d=read(E/'evidencias/ledger.json');self.assertEqual(d['reserved_usd'],0);self.assertLess(d['step_gross_usd'],10);self.assertTrue((B/'generador.off').exists());self.assertTrue((B/'pago_adn_json.off').exists())
 def test_gold_23_unchanged_core(self):
  d=read(B/'oro_av06/metricas_oro.json');self.assertTrue(d['all_equal']);self.assertEqual(d['count'],23)
  rel='MOTOR_UNICO_20261107/motor/nucleo_bueno_cpu.py';self.assertEqual((B/rel).read_bytes(),(Path('/opt/myia-motor-v9/avance05_20261107')/rel).read_bytes())
if __name__=='__main__':unittest.main(verbosity=2)
