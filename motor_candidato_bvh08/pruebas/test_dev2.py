import sys,unittest,json,copy,shutil,subprocess
from pathlib import Path
from PIL import Image
R=Path(__file__).resolve().parents[1];sys.path.insert(0,str(R/'motor'))
from seguridad import *
from dialogos import compilar
from eventos import validar_eventos
from fisica_final import outside_distance
from montaje_cpu import planificar,ejecutar
from orquestador import ejecutar as escena
BL='/home/box/apps/blender-5.2.3-linux-x64/blender'
class Tests(unittest.TestCase):
 def test_dialogos_reales_11_y_cortes(self):
  d=leer(R/'evidencia/guardianes_dev2/tiempos_dialogo.json');self.assertEqual(d['estado'],'COMPLETO');self.assertEqual(len(d['dialogos']),11);self.assertEqual(sum(len(l['tomas'])>1 for l in d['dialogos']),4);self.assertFalse(d['genera_voz']);self.assertFalse(d['genera_lipsync'])
 def test_falta_texto_es_dato_01(self):
  d=compilar([{'id':'a','accion':'hablar','actor':'e','t':[0,1]}],[{'id':'v','t0':0,'t1':1}],24,1,['e'],'fixture');self.assertEqual(d['estado'],'BLOQUEADO');self.assertEqual(d['errores'][0]['modulo'],'guion/01')
 def test_dialogo_no_se_repite_si_cruza_corte(self):
  d=compilar([{'id':'a','accion':'hablar','actor':'e','cita':'Texto único.','t':[.5,1.5]}],[{'id':'v1','t0':0,'t1':1},{'id':'v2','t0':1,'t1':2}],24,2,['e'],'fixture');self.assertEqual(len(d['dialogos']),1);self.assertEqual(d['dialogos'][0]['tomas'],['v1','v2']);self.assertEqual(sum(p['fin_cuadro']-p['inicio_cuadro']+1 for p in d['dialogos'][0]['por_toma']),24)
 def test_equilibrio_fuera_y_dentro(self):
  self.assertEqual(outside_distance((.5,.5),[(0,0),(1,0),(1,1),(0,1)]),0);self.assertAlmostEqual(outside_distance((2,.5),[(0,0),(1,0),(1,1),(0,1)]),1)
 def test_material_dos_escritores_bloquea(self):
  e={'object':'a','property':'material.base_color','material':'m','source':'fixture','keys':[{'t':0,'value':[0,0,0,1],'curve':'LINEAR'}]};self.assertTrue(validar_eventos([e,dict(e,object='b')],2))
 def test_fixture_unica_16_etapas(self):
  d=leer(R/'evidencia/fixture_aviar_integracion_v6/resultado.json');self.assertEqual(d['estado'],'COMPLETO');self.assertEqual(len(d['etapas']),16);self.assertEqual(d['coverage']['frames_built'],16);self.assertNotIn('audio', [x['campo'] for x in d['errores']]);rv=leer(R/'evidencia/fixture_aviar_integracion_v6/revision_final.json');self.assertTrue(rv['all_passed']);self.assertGreater(rv['camera']['extent_vertices_checked'],100);self.assertEqual(rv['physics']['frames'],16)
 def test_salida_omni_jl_sin_audio_no_bloquea(self):
  plan=planificar([{'id':'a','t0':0,'t1':1,'transition':'J_CUT'},{'id':'b','t0':1,'t1':2,'transition':'FIN_ESCENA'}],8,2);self.assertEqual(sum(p['frames'] for p in plan),16);self.assertEqual(plan[1]['audio_handoff_omni'],'J_CUT')
 def test_transicion_saliente_no_se_adelanta(self):
  p=planificar([{'id':'a','t0':0,'t1':1,'transition':{'type':'FUNDIDO','duration_s':.25}},{'id':'b','t0':1,'t1':2,'transition':'FIN_ESCENA'}],8,2);self.assertEqual(p[0]['overlap'],0);self.assertEqual(p[1]['overlap'],2)
 def test_off_montaje_no_se_ignora(self):
  p=R/'config/montaje.off'
  if p.exists():self.fail('No pisar interruptor existente')
  p.write_text('prueba negativa dev2')
  try:
   with self.assertRaises(ValueError):planificar([],8,2)
  finally:archivar(p)
 def test_oclusor_no_genera_video_parcial(self):
  original=R/'paquetes/fixture_aviar_integracion';pk=R/'paquetes/fixture_negativa_oclusor';pk.mkdir(exist_ok=False);d=leer(original/'entrada_escena.json')
  for asset in d['assets']:
   target=ruta(pk,asset['path']);target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(ruta(original,asset['path']),target)
  d['environment']['geometry'].append({'id':'oclusor','shape':'BOX','position_m':[0,-2,.9],'dimensions_m':[2,.1,1.8],'rotation_deg':[0,0,0],'resolution':8,'material':{'rgba':[.1,.1,.1,1],'metallic':0,'roughness':1},'source':'fixture_negativo_explicito'})
  guardar(pk/'entrada_escena.json',d);out=R/'evidencia/fixture_negativa_oclusor';result=escena(pk/'entrada_escena.json',out,True,BL);self.assertEqual(result['estado'],'BLOQUEADO');self.assertIsNone(result['master']);self.assertFalse(list(out.glob('*.mp4')));self.assertTrue(any(e['type']=='OCLUSION' for e in leer(out/'revision_final.json')['errors']))
 def test_montaje_fundido_cuenta_y_no_es_corte(self):
  out=R/'evidencia/montaje_colores_dev2';out.mkdir(exist_ok=False);clips=[]
  for name,color,frames in [('rojo','red',8),('azul','blue',10)]:
   p=out/(name+'.mp4');subprocess.run(['ffmpeg','-nostdin','-loglevel','error','-f','lavfi','-i',f'color=c={color}:s=64x64:r=8','-frames:v',str(frames),'-c:v','libx264','-pix_fmt','yuv420p',str(p)],check=True);clips.append(p)
  p=planificar([{'id':'a','t0':0,'t1':1,'transition':{'type':'FUNDIDO','duration_s':.25}},{'id':'b','t0':1,'t1':2,'transition':'FIN_ESCENA'}],8,2);result=ejecutar(clips,p,8,[64,64],2,[],out,out/'master');self.assertEqual(result['frames'],16)
  img=out/'intermedio.png';subprocess.run(['ffmpeg','-nostdin','-loglevel','error','-i',result['path'],'-vf','select=eq(n\\,7)','-frames:v','1',str(img)],check=True);pixel=Image.open(img).getpixel((32,32));self.assertGreater(pixel[0],30);self.assertGreater(pixel[2],30);guardar(out/'prueba_pixel.json',{'pixel_frame8':pixel,'frames':result['frames'],'fade_not_cut':True})
if __name__=='__main__':
 runner=unittest.TextTestRunner(verbosity=2);result=runner.run(unittest.defaultTestLoader.loadTestsFromTestCase(Tests));guardar(R/'evidencia/pruebas_dev2.json',{'tests':result.testsRun,'passed':result.wasSuccessful(),'failures':len(result.failures),'errors':len(result.errors)});sys.exit(not result.wasSuccessful())
