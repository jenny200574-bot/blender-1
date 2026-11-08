import unittest,json,sys,hashlib,math
from pathlib import Path
B=Path('/opt/myia-motor-v9/avance05_20261107');E=B/'entrega';P=B/'esc1_candidata';R=B/'MOTOR_UNICO_20261107'
def read(p):return json.loads(p.read_text())
class Tests(unittest.TestCase):
 def test_recipes_passed_without_tolerance_change(self):
  v=read(E/'evidencias/validacion_planos.json')
  for n in ['iteracion16_cofre_reparado2','iteracion17_cama_reparada2']:
   self.assertTrue(v['recipes'][n]['passed']);self.assertEqual(v['recipes'][n]['metrics']['tolerance_m'],.001)
 def test_flat_components_unchanged(self):
  v=read(E/'evidencias/validacion_planos.json')
  for n in ['iteracion16_cofre_reparado2','iteracion17_cama_reparada2']:
   flat=read(E/'evidencias'/n/'respuesta.json');parts=v['recipes'][n]['recipe']['parts']
   for i,p in enumerate(parts,1):
    for target,keys in [('position_m',['px','py','pz']),('rotation_deg',['rx','ry','rz']),('dimensions_m',['dx','dy','dz'])]:self.assertEqual(p[target],[flat[f'p{i}_{k}'] for k in keys])
    self.assertEqual(p['material']['rgba'],[flat[f'p{i}_{k}'] for k in ['r','g','b','a']]);self.assertEqual(p['material']['metallic'],flat[f'p{i}_metallic']);self.assertEqual(p['material']['roughness'],flat[f'p{i}_roughness'])
 def test_all_scene_assets_hashes(self):
  d=read(P/'entrada_escena.json')
  for a in d['assets']:
   p=P/a['path'];self.assertEqual(hashlib.sha256(p.read_bytes()).hexdigest(),a['sha256']);self.assertEqual(p.stat().st_size,a['bytes'])
 def test_camera_values_and_original_timing(self):
  orig=read(B/'esc1_antes/storyboard_camara.json');now=read(P/'storyboard_camara.json');raw=read(E/'evidencias/iteracion08_camara_escalar/respuesta.json');by={s['vineta']:s for s in now['vinetas']}
  self.assertEqual([(s['vineta'],s['t_abs']) for s in orig['vinetas']],[(s['vineta'],s['t_abs']) for s in now['vinetas']])
  for ident,key,arg in [('v3','pan_v3_degrees','degrees'),('v5','crane_v5_distance_m','distance'),('v7','pan_v7_degrees','degrees')]:self.assertEqual(by[ident]['segmentos'][0]['args'][arg],raw[key])
 def test_provisional_not_silently_removed(self):self.assertEqual(read(B/'esc1_antes/entrada_escena.json')['provisional'],read(P/'entrada_escena.json')['provisional'])
 def test_exact_object_identifiers_only(self):
  dna=read(P/'adn_entidades.json')
  for ident in ['obj-cama','obj-cofre-dorado']:
   records=[r for r in dna['records'] if ident==r['id'] or ident in r.get('exact_aliases',[])];self.assertEqual(len(records),1)
   for part in records[0]['source_data']['construction_3d']['parts']:self.assertTrue(part['id'].startswith(ident+'.'));self.assertNotEqual(part['shape'],'BOX')
 def test_automatic_paid_disabled(self):
  self.assertFalse(read(R/'config/politica_ejecucion.json')['argon_automatico']);self.assertTrue(read(R/'config/argon_transporte.json')['dry_run']);self.assertTrue((R/'config/argon_envio.off').exists())
 def test_cpu_guard_stays_blocked(self):
  d=read(E/'evidencias/preview_cpu_objetos_resultado.json');self.assertEqual(d['estado'],'BLOQUEADO');self.assertIsNone(d['master']);self.assertFalse(d['gpu_used']);self.assertEqual(d['paid_network_calls_in_preview'],0)
if __name__=='__main__':unittest.main(verbosity=2)
