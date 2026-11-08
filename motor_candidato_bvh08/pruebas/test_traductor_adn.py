import sys,json,copy,unittest
from pathlib import Path
from collections import Counter
R=Path(__file__).resolve().parents[1];sys.path.insert(0,str(R/'motor'))
from superficies_adn import loft
from traductor_adn import traducir,compilar,hechos
from seguridad import guardar
class Tests(unittest.TestCase):
 def setUp(self):self.entry=json.loads((R/'paquetes/fixture_traductor_adn/entrada_escena.json').read_text());self.entity=self.entry['entities'][0];self.model=self.entity['dna_record']['source_data']['construction_3d']
 def manifold(self,faces):
  edges=Counter(tuple(sorted((a,b))) for face in faces for a,b in zip(face,face[1:]+face[:1]));return all(v==2 for v in edges.values())
 def test_cota_malformada_B_no_crash_A(self):
  self.model['face_surfaces'][0]['surface'].pop('sections_m');g,r,e=traducir(self.entity);self.assertIsNone(g);self.assertTrue(e);self.assertTrue(all(x['tipo']=='completar dato' for x in e))
 def test_material_ausente_B_no_crash(self):
  self.model['face_surfaces'][0]['material'].pop('roughness');g,r,e=traducir(self.entity);self.assertIsNone(g);self.assertTrue(e);self.assertTrue(all(x['tipo']=='completar dato' for x in e))
 def test_no_omitir_expresiones_ni_reglas_de_giro(self):
  f=hechos('1. Antropometría:\n- Cinco cabezas.\n2. Rostro:\n- Oval.\n3. Expresiones:\n- Nervioso: cejas altas.\n4. Vestuario:\n- Capa.\n5. Giro:\n- De espaldas: dos parches.');self.assertEqual({x['section'] for x in f},{'anthropometry','face','expressions','clothes','rotation_rules'})
 def test_cobertura_animal_no_exige_ropa_humana(self):
  self.model['garments'][0]['role']='plumage';g,r,e=traducir(self.entity);self.assertFalse(e);self.assertEqual(g['parts'][1]['role'],'plumage')
 def test_vinculos_o_color_malformados_son_B_no_crash(self):
  for field,value in [('fact_bindings',[]),('required_roles','cara')]:
   old=self.model[field];self.model[field]=value;g,r,e=traducir(self.entity);self.assertIsNone(g);self.assertTrue(all(x['tipo']=='completar dato' for x in e));self.model[field]=old
  self.model['face_surfaces'][0]['material']['rgba']='rojo';g,r,e=traducir(self.entity);self.assertIsNone(g);self.assertTrue(e)
 def test_cara_malla_cerrada_no_capsula(self):
  v,f=loft(self.model['face_surfaces'][0]['surface']);self.assertTrue(self.manifold(f));self.assertGreater(len(v),300);self.assertAlmostEqual(max(p[2] for p in v)-min(p[2] for p in v),.35)
 def test_ropa_grosor_aberturas_manifold(self):
  s=self.model['garments'][0]['surface'];v,f=loft(s);self.assertTrue(self.manifold(f));self.assertEqual(len(v),len(s['sections_m'])*s['radial_segments']*2)
 def test_radio_menor_que_grosor_bloquea(self):
  s=copy.deepcopy(self.model['garments'][0]['surface']);s['thickness_m']=1
  with self.assertRaises(ValueError):loft(s)
 def test_perfil_desordenado_bloquea(self):
  s=copy.deepcopy(self.model['garments'][0]['surface']);s['sections_m'].reverse()
  with self.assertRaises(ValueError):loft(s)
 def test_cada_hecho_tiene_geometria_citada(self):
  g,r,e=traducir(self.entity);self.assertEqual(e,[]);self.assertEqual(len(r['facts']),len(r['applied']));self.assertTrue(any(p['shape']=='MESH' and p['role']=='clothes' for p in g['parts']))
 def test_no_marcar_final_si_falta_un_rasgo(self):
  self.entity['dna_record']['source_data']['text']+='\n4. Vestuario por Capas:\n- Detalle adicional todavía sin construir.\n';g,r,e=traducir(self.entity);self.assertIsNone(g);self.assertTrue(any(x['tipo']=='crear capacidad' for x in e))
 def test_cotas_ausentes_son_B_no_adn_inexistente(self):
  del self.entity['dna_record']['source_data']['construction_3d'];g,r,e=traducir(self.entity);self.assertIsNone(g);self.assertEqual(len(e),2);self.assertTrue(all(x['tipo']=='completar dato' for x in e));self.assertTrue(r['facts'])
 def test_entrada_unica_inyecta_malla_y_material_no_se_saltea(self):
  rec,e=compilar(self.entry,prueba_cpu=True);self.assertEqual(e,[]);app=self.entry['entities'][0]['appearance'];self.assertTrue(app['geometry']['parts']);self.assertTrue(app['rostros_finales']['source']);self.assertTrue(app['ropa_final']['source'])
 def test_off_traductor_produccion_bloquea(self):
  with self.assertRaises(ValueError):compilar(self.entry,prueba_cpu=False)
 def test_nombres_nuevos_mismas_cotas_misma_malla(self):
  g,_,_=traducir(self.entity);self.entity['id']='ser_diferente_901';h,_,_=traducir(self.entity);self.assertEqual(g['parts'],h['parts'])
 def test_cotas_cm_y_hex_se_conservan(self):
  f=hechos('2. Fisonomía:\n- Marca #ABCDEF de 1,2 cm.\n4. Vestuario:\n- Cuello de 2 cm.');self.assertEqual(f[0]['explicit_cm'],[1.2]);self.assertEqual(f[0]['hex_colors'],['#ABCDEF'])
if __name__=='__main__':
 result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(Tests));guardar(R/'evidencia/pruebas_traductor_adn.json',{'tests':result.testsRun,'passed':result.wasSuccessful(),'failures':len(result.failures),'errors':len(result.errors),'spend_usd':0});sys.exit(not result.wasSuccessful())
