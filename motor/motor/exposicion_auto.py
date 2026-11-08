"""Histograma de salida sRGB, exposición global, no curva distinta por toma."""
import json,sys,subprocess,tempfile
from pathlib import Path

def histograma(paths,threshold=250):
 from PIL import Image
 rows=[]
 for file in paths:
  im=Image.open(file).convert('RGB');pixels=list(im.getdata());n=len(pixels);rows.append({'image':str(file),'pixels':n,'saturated_any':sum(max(p)>=threshold for p in pixels),'white_all':sum(min(p)>=threshold for p in pixels)})
 for r in rows:r['saturated_pct']=100*r['saturated_any']/r['pixels'];r['white_pct']=100*r['white_all']/r['pixels']
 n=sum(r['pixels'] for r in rows);return {'threshold':threshold,'metric':'any_RGB_channel_ge_threshold','images':rows,'saturated_pct':100*sum(r['saturated_any'] for r in rows)/n,'worst_shot_pct':max(r['saturated_pct'] for r in rows)}

def medir(paths,cfg):
 cmd=['python3',str(Path(__file__).resolve()),str(cfg['saturation_channel_threshold']),*[str(p) for p in paths]]
 return json.loads(subprocess.run(cmd,check=True,capture_output=True,text=True,timeout=60).stdout)

def gate(stats,cfg):
 if stats['worst_shot_pct']>cfg['max_saturated_pct']:raise ValueError('EXPOSICION_SATURADA: %s > %s %% por toma'%(stats['worst_shot_pct'],cfg['max_saturated_pct']))
 return True

def preparar(scene,cfg,preset):
 import bpy
 from seguridad import exigir
 exigir('exposicion_auto')
 if not cfg.get('enabled'):return
 for owner in [scene]+([scene.world] if scene.world else []):
  ad=owner.animation_data
  if ad and ad.action and any('exposure' in f.data_path for f in getattr(ad.action,'fcurves',[])):raise ValueError('Conflicto: exposición artística animada frente a exposición automática global')
 scene.view_settings.view_transform=cfg['view_transform'];scene.view_settings.look=cfg['look'];scene.view_settings.exposure=cfg['exposure_start_ev']
 if scene.world and scene.world.use_nodes:
  for n in scene.world.node_tree.nodes:
   if n.type=='BACKGROUND':n.inputs['Strength'].default_value*=cfg['world_strength_factor']
 # Roles explícitos de entrada, nunca alias por nombre. Por defecto reduce los emisores técnicos como conjunto.
 ids={l['id'] for l in preset.get('technical_lights',[]) if l.get('role') in [None,'fill']}
 for o in scene.objects:
  if o.type=='LIGHT':
   o.data.use_shadow=True
   if o.name in ids:o.data.energy*=cfg['technical_fill_factor']
 for m in bpy.data.materials:
  if not m.use_nodes:continue
  for n in m.node_tree.nodes:
   if n.type=='EMISSION':n.inputs['Strength'].default_value=min(n.inputs['Strength'].default_value,cfg['emission_strength_max'])
   if n.type=='BSDF_PRINCIPLED' and n.inputs.get('Emission Strength'):n.inputs['Emission Strength'].default_value=min(n.inputs['Emission Strength'].default_value,cfg['emission_strength_max'])

def calibrar(scene,views,cfg):
 import bpy
 old=(scene.render.resolution_x,scene.render.resolution_y,scene.render.resolution_percentage,scene.render.filepath);samples=scene.eevee.taa_render_samples if scene.render.engine=='BLENDER_EEVEE' else None;history=[]
 try:
  scene.render.resolution_x,scene.render.resolution_y=cfg.get('probe_resolution',[80,45]);scene.render.resolution_percentage=100
  if samples is not None:scene.eevee.taa_render_samples=cfg.get('probe_samples',4)
  with tempfile.TemporaryDirectory(prefix='motor_exposure_probe_') as folder:
   while True:
    paths=[]
    for i,v in enumerate(views):
     scene.camera=bpy.data.objects[v['camera']];scene.frame_set(v['frame']);p=Path(folder)/(str(i)+'.png');scene.render.filepath=str(p);bpy.ops.render.render(write_still=True);paths.append(p)
    stat=medir(paths,cfg);history.append({'exposure_ev':scene.view_settings.exposure,'stats':stat})
    if stat['worst_shot_pct']<=cfg['max_saturated_pct']*cfg.get('probe_safety_factor',.5):break
    if scene.view_settings.exposure-cfg['exposure_step_ev']<cfg['exposure_min_ev']:raise ValueError('EXPOSICION_SATURADA incluso al mínimo permitido')
    scene.view_settings.exposure-=cfg['exposure_step_ev']
  return {'global_exposure_ev':scene.view_settings.exposure,'history':history,'max_saturated_pct':cfg['max_saturated_pct'],'temporary_probe_files_removed':True}
 finally:
  scene.render.resolution_x,scene.render.resolution_y,scene.render.resolution_percentage,scene.render.filepath=old
  if samples is not None:scene.eevee.taa_render_samples=samples

if __name__=='__main__':print(json.dumps(histograma(sys.argv[2:],int(sys.argv[1]))))
