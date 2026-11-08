import unittest,sys,copy,tempfile,json
from pathlib import Path
R=Path(__file__).resolve().parents[1];sys.path.insert(0,str(R/'motor'))
from buscador_formas import buscar
from luces_por_datos import compilar
from eventos import valor,validar_eventos
from objetos_star import verificar
from arquitectura_datos import paneles
from seguridad import guardar
class Tests(unittest.TestCase):
 def setUp(self):
  self.root=Path(tempfile.mkdtemp(prefix='t307_',dir=R/'evidencia'));self.off=self.root/'argon.off';self.off.write_text('apagado')
  self.policy={'minimum_score':.75,'weights':{'shape':.3,'dimensions':.2,'use':.2,'words':.3},'synonyms':{'meson':'escritorio','desk':'escritorio','laborar':'trabajar'},'stop_words':['de','para','un'],'primitive_shapes':['BOX','ELLIPSOID','CYLINDER']}
  self.recipe={'id':'escritorio_patas','formula':'escritorio_patas','words':['escritorio'],'shapes':['rectangular'],'uses':['trabajar'],'scale_policy':'independent_axes','features':['support'],'source':'biblioteca verificada'};self.catalog={'recipes':[self.recipe]};self.query={'id':'objeto_totalmente_nuevo_omega','shape':'rectangular','words':['meson'],'text':'','use':'laborar','dimensions_m':[2,.8,1],'required_features':['support'],'source':'ADN fixture'}
 def test_presencia_no_convierte_booleano_en_float(self):
  keys=[{'t':0,'value':True,'curve':'CONSTANT'},{'t':1,'value':False,'curve':'CONSTANT'}];self.assertIs(valor(keys,.5),True);self.assertIs(valor(keys,1),False)
 def test_aparicion_nombres_nuevos_01_no_inventa_trayectoria(self):
  from narrativa_estructurada import compilar_presencia
  d={'environment':{},'actions':[{'id':'aparicion_nueva','actor':'ser_nuevo','objeto':'','accion':'aparecer','t':[2,3]}]};rec=compilar_presencia(d);e=d['environment']['events'][0];self.assertEqual(e['object'],'ser_nuevo');self.assertIs(valor(e['keys'],1),True);self.assertIs(valor(e['keys'],2),False);self.assertEqual(rec[0]['kind'],'presence_only');self.assertNotIn('location',str(e))
 def test_presencia_reaparicion_un_solo_escritor(self):
  from narrativa_estructurada import compilar_presencia
  d={'environment':{},'actions':[{'id':'uno','actor':'ser_nuevo','accion':'aparecer','t':[1,2]},{'id':'dos','actor':'ser_nuevo','accion':'desaparecer','t':[3,4]},{'id':'tres','actor':'ser_nuevo','accion':'aparecer','t':[5,6]}]};compilar_presencia(d);e=d['environment']['events'];self.assertEqual(len(e),1);self.assertEqual(validar_eventos(e,7),[]);self.assertIs(valor(e[0]['keys'],4),True);self.assertEqual(e[0]['action_ids'],['uno','dos','tres']);self.assertEqual(compilar_presencia(d),[]);self.assertEqual(e[0]['action_ids'],['uno','dos','tres'])
 def test_guardar_receta_declarativa_archiva_y_rechaza_codigo(self):
  from buscador_formas import guardar_receta
  path=self.root/'biblioteca_nueva.json';guardar(path,{'recipes':[]});recipe={'id':'forma_nueva','source':'fixture sin Argon ni costo','parts':[{'id':'p','shape':'ELLIPSOID','dimensions_m':[1,2,3],'position_m':[0,0,0],'rotation_deg':[0,0,0],'material':{'rgba':[1,0,0,1],'roughness':.5,'metallic':0},'source':'fixture'}]};receipt=guardar_receta(recipe,path);self.assertTrue(receipt['sha256']);self.assertTrue(list((self.root/'archivo').glob('*/biblioteca_nueva.json')))
  with self.assertRaises(ValueError):guardar_receta(recipe,path)
  with self.assertRaises(ValueError):guardar_receta({'id':'mal','source':'fixture','code':'código no autorizado'},path)
 def test_nombre_nuevo_receta_similar_y_escala(self):
  r=buscar(self.query,self.catalog,self.policy,switch=self.off);self.assertEqual(r['step'],2);self.assertEqual(r['score'],1);self.assertEqual(r['dimensions_m'],self.query['dimensions_m'])
 def test_receta_exacta_primero(self):
  self.query['formula']='escritorio_patas';self.assertEqual(buscar(self.query,self.catalog,self.policy,switch=self.off)['step'],1)
 def test_sinonimo_ingles_otro_nombre(self):
  self.query.update(id='nebula_991',words=['desk']);self.assertEqual(buscar(self.query,self.catalog,self.policy,switch=self.off)['step'],2)
 def test_umbral_rechaza_menos_malo(self):
  self.query.update(words=['nube'],use='dormir',shape='esferica',required_features=[]);self.assertEqual(buscar(self.query,self.catalog,self.policy,switch=self.off)['state'],'FALTA')
 def test_incompatibilidad_funcional_no_basta_color(self):
  self.query['required_features']=['flight'];self.assertEqual(buscar(self.query,self.catalog,self.policy,switch=self.off)['state'],'FALTA')
 def test_composicion_ejecutable(self):
  self.catalog={'recipes':[]};self.query['parts']=[{'id':'pieza_canonica','shape':'BOX','dimensions_m':[1,1,1],'position_m':[0,0,0],'rotation_deg':[0,0,0],'material':{},'source':'fixture'}];self.assertEqual(buscar(self.query,self.catalog,self.policy,switch=self.off)['step'],3)
 def test_composicion_sin_medidas_no_inventa(self):
  self.catalog={'recipes':[]};self.query['parts']=[{'id':'incompleta'}];self.assertEqual(buscar(self.query,self.catalog,self.policy,switch=self.off)['state'],'FALTA')
 def test_off_argon_impide_llamada_y_ledger(self):
  self.catalog={'recipes':[]};called=[];f=lambda *a:called.append(a);d=buscar(self.query,self.catalog,self.policy,switch=self.off,paid_ok=True,argon_provider=f,ledger_before=f,recipe_library_path=self.root/'recetas_no_creadas.json');self.assertEqual(called,[]);self.assertEqual(d['spent_usd'],0)
 def test_sin_ok_no_gasta_aunque_no_off(self):
  self.catalog={'recipes':[]};d=buscar(self.query,self.catalog,self.policy,switch=self.root/'no_existe',argon_provider=lambda *a:self.fail('pago'));self.assertEqual(d['spent_usd'],0)
 def test_bbox_exacto_no_se_publica(self):
  self.catalog['recipes']=[dict(self.recipe,id='bbox',bbox_only=True)];self.query['formula']='bbox';self.assertEqual(buscar(self.query,self.catalog,self.policy,switch=self.off)['state'],'FALTA')
 def light(self):
  shots=[{'id':'plano_alpha','t0':0,'t1':1},{'id':'plano_beta','t0':1,'t1':2}];p={'source':'fixture','emitters':[{'id':'emisor_independiente','targets':[{'object':'lampara_sin_alias','property':'energy','base_value':57}],'states_by_shot':{'plano_alpha':{'factor':1,'curve':'LINEAR'},'plano_beta':{'factor':0,'curve':'CONSTANT','intentional_blackout':True}}}]};return p,shots
 def test_apagon_intencional_es_constant_y_cero_real(self):
  p,s=self.light();events,e=compilar(p,s);self.assertEqual(e,[]);self.assertEqual(valor(events[0]['keys'],.999),57);self.assertEqual(valor(events[0]['keys'],1),0)
 def test_formato_tres_canales_por_mapa_no_alias(self):
  p,s=self.light();p['emitters'][0].pop('states_by_shot');p.update(legacy_states={'por_toma':{'101':{'canal_arbitrario':1},'202':{'canal_arbitrario':0}}},legacy_channels={'canal_arbitrario':['emisor_independiente']},legacy_shot_ids={'101':'plano_alpha','202':'plano_beta'});events,e=compilar(p,s);self.assertEqual(e,[]);self.assertEqual(valor(events[0]['keys'],1),0)
 def test_canal_sin_mapa_es_falta(self):
  p,s=self.light();p.update(legacy_states={'por_toma':{'101':{'desconocido':1}}},legacy_shot_ids={'101':'plano_alpha'});self.assertTrue(compilar(p,s)[1])
 def test_estado_faltante_no_usa_default(self):
  p,s=self.light();del p['emitters'][0]['states_by_shot']['plano_beta'];self.assertTrue(compilar(p,s)[1])
 def test_lamparas_sin_dependencias(self):
  p,s=self.light();q=copy.deepcopy(p['emitters'][0]);q['id']='otro';q['targets'][0]['object']='otro_objeto';q['states_by_shot']['plano_beta']['factor']=1;q['states_by_shot']['plano_beta']['intentional_blackout']=False;p['emitters'].append(q);events,e=compilar(p,s);self.assertEqual(e,[]);self.assertEqual(valor(events[0]['keys'],1),0);self.assertEqual(valor(events[1]['keys'],1),57)
 def test_grafo_global_escritor_unico(self):
  p,s=self.light();events,_=compilar(p,s);self.assertTrue(validar_eventos(events+events,2))
 def test_varios_huecos_sin_pared_prefijada(self):
  spec={'width_m':4,'height_m':3,'thickness_m':.1,'openings':[{'rect_m':[.5,.5,1.5,2]},{'rect_m':[2,.2,3,1]}]};panels=paneles(spec);area=sum(x['dimensions_m'][0]*x['dimensions_m'][2] for x in panels);self.assertAlmostEqual(area,12-1.5-.8)
 def test_huecos_solapados_union(self):
  spec={'width_m':4,'height_m':3,'thickness_m':.1,'openings':[{'rect_m':[1,1,3,2]},{'rect_m':[2,1,4,2]}]};self.assertAlmostEqual(sum(x['dimensions_m'][0]*x['dimensions_m'][2] for x in paneles(spec)),9)
 def test_hueco_fuera_es_falta_no_recorte_inventado(self):
  with self.assertRaises(ValueError):paneles({'width_m':1,'height_m':1,'thickness_m':.1,'openings':[{'rect_m':[-1,0,2,1]}]})
 def test_pieza_movil_y_marco_faltantes_identificados(self):
  d=json.loads((R/'pruebas/datos/star_unificado_t307.json').read_text())['object'];del d['points'][0]['pieza_movil'];del d['points'][0]['frame'];f=verificar(d);self.assertTrue(any('pieza_movil' in x[0] for x in f));self.assertTrue(any('frame' in x[0] for x in f))
 def test_bug_AttributeError_tipo_desconocido_descartado(self):
  d=json.loads((R/'pruebas/datos/star_unificado_t307.json').read_text())['object'];d['formula']=None;self.assertTrue(verificar(d))
 def test_catalogo_real_busca_nombre_ajeno_por_forma_uso_medidas(self):
  catalog=json.loads((R/'bibliotecas/formulas_star_estrictas.json').read_text());policy=json.loads((R/'bibliotecas/politica_busqueda_formas_cpu.json').read_text());query={'id':'artefacto_nebular_729','shape':'rectangular','use':'laborar','words':['meson','dibujar'],'dimensions_m':[1.37,.72,.81],'required_features':['support'],'source':'ADN fixture nuevo'};result=buscar(query,catalog,policy,switch=self.off);self.assertEqual(result['step'],2);self.assertEqual(result['recipe']['formula'],'escritorio_patas');self.assertGreaterEqual(result['score'],policy['minimum_score']);self.assertEqual(result['dimensions_m'],query['dimensions_m'])
 def test_off_star_sin_prueba_cpu_bloquea(self):
  import os
  from seguridad import exigir_desarrollo
  previous=os.environ.pop('MOTOR_UNICO_CPU_PRUEBA',None)
  try:
   with self.assertRaises(ValueError):exigir_desarrollo('star_unificado')
  finally:
   if previous is not None:os.environ['MOTOR_UNICO_CPU_PRUEBA']=previous
 def test_catalogo_real_44_42(self):
  d=json.loads((R/'bibliotecas/formulas_star_estrictas.json').read_text());self.assertEqual(len(d['recipes']),44);self.assertEqual(len({x['builder'] for x in d['recipes']}),42)
if __name__=='__main__':
 result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(Tests));guardar(R/'evidencia/pruebas_t307.json',{'tests':result.testsRun,'passed':result.wasSuccessful(),'errors':len(result.errors),'failures':len(result.failures),'spend_usd':0});sys.exit(not result.wasSuccessful())
