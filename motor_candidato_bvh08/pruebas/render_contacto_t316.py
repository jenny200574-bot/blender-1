import bpy,sys,json,os
from pathlib import Path
os.environ['MOTOR_UNICO_CPU_PRUEBA']='1'
R=Path(__file__).resolve().parents[1];sys.path.insert(0,str(R/'motor'));from seguridad import leer,guardar,sha
from detalle_entorno import aplicar
from render_estilo import configurar
args=sys.argv[sys.argv.index('--')+1:];pk=Path(args[0]);out=Path(args[1]);out.mkdir(exist_ok=False,parents=True);d=leer(pk/'entrada_escena.json');old=R/'evidencia/contacto_guardianes_t314_definitivo';bpy.ops.wm.open_mainfile(filepath=str(old/'diagnostico.blend'));sc=bpy.context.scene;objects={o.name:o for o in sc.objects};rec=leer(old/'recibo.json');receipt=aplicar(d['environment']['catalog_jobs'],objects)
# Preserve all artistic missing-data blocks. This is a technical test preset only.
settings=configurar(sc,d['environment']['visual_preset']);sc.render.image_settings.file_format='PNG'
for ob in sc.objects:
 if ob.type=='MESH' and not ob.parent and not ob.get('motor_preserve_hidden') and not ob.hide_render:
  if not any(m.type=='BEVEL' for m in ob.modifiers):
   m=ob.modifiers.new('bevel_tecnico_por_preset','BEVEL');m.width=d['environment']['visual_preset']['bevel_width_m'];m.segments=d['environment']['visual_preset']['bevel_segments']
images=[]
for image in rec['images']:
 sc.frame_set(image['frame']);sc.render.filepath=str(out/image['image']);bpy.ops.render.render(write_still=True);i=dict(image);i['sha256']=sha(out/image['image']);images.append(i)
import gpu
backend={'renderer':gpu.platform.renderer_get(),'vendor':gpu.platform.vendor_get(),'version':gpu.platform.version_get(),'LIBGL_ALWAYS_SOFTWARE':os.environ.get('LIBGL_ALWAYS_SOFTWARE'),'GALLIUM_DRIVER':os.environ.get('GALLIUM_DRIVER')}
assert 'llvmpipe' in backend['renderer'].lower() or 'softpipe' in backend['renderer'].lower(),backend
bpy.ops.wm.save_as_mainfile(filepath=str(out/'diagnostico.blend'));rec.update(images=images,source_previous_sheet_sha256=sha(old/'hoja_contacto_REAL_DIAGNOSTICO_BLOQUEADO.png'),render=settings,backend=backend,detail_jobs=receipt,warning='Diagnóstico técnico t316, 5/6 sujetos; B intactas; no aceptación de escena. Cámaras heredadas del diagnóstico, no revalidadas con props nuevos.');guardar(out/'recibo.json',rec);guardar(out/'detalle_entorno.json',receipt);print('CPU_SOFTWARE_BACKEND',backend['renderer'])
