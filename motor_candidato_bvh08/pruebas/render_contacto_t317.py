import bpy,sys,os
from pathlib import Path
os.environ['MOTOR_UNICO_CPU_PRUEBA']='1'
R=Path(__file__).resolve().parents[1];sys.path.insert(0,str(R/'motor'))
from seguridad import leer,guardar,sha
from exposicion_auto import preparar,calibrar,medir,gate
old,out,package=map(Path,sys.argv[sys.argv.index('--')+1:]);out.mkdir(parents=True,exist_ok=False);d=leer(package/'entrada_escena.json');cfg=leer(R/'config/exposicion_auto.json');bpy.ops.wm.open_mainfile(filepath=str(old/'diagnostico.blend'));sc=bpy.context.scene;rec=leer(old/'recibo.json');sc.render.image_settings.file_format='PNG'
views=[{'camera':x.get('camera',sc.camera.name),'frame':x['frame']} for x in rec['images']]
before=medir([old/x['image'] for x in rec['images']],cfg);preparar(sc,cfg,d['environment']['visual_preset']);sc.eevee.taa_render_samples=cfg['samples'];sc.render.resolution_x,sc.render.resolution_y=cfg['resolution'];cal=calibrar(sc,views,cfg);images=[]
for v,x in zip(views,rec['images']):
 sc.camera=bpy.data.objects[v['camera']];sc.frame_set(v['frame']);sc.render.filepath=str(out/x['image']);bpy.ops.render.render(write_still=True);images.append(dict(x,sha256=sha(out/x['image'])))
after=medir([out/x['image'] for x in rec['images']],cfg);passed=gate(after,cfg)
import gpu
backend=gpu.platform.renderer_get();assert 'llvmpipe' in backend.lower() or 'softpipe' in backend.lower()
rec.update(images=images,source_previous_sheet_sha256=sha(old/'hoja_contacto_REAL_DIAGNOSTICO_BLOQUEADO.png'),exposure_calibration=cal,backend={'renderer':backend},warning='Sólo diagnóstico real CPU: 5/6 sujetos, escena BLOQUEADA; no se inventaron recetas/anatomía; no se creó otro blend.')
guardar(out/'recibo.json',rec);guardar(out/'histogramas_antes_despues.json',{'before':before,'after':after,'gate_passed':passed,'threshold_pct':cfg['max_saturated_pct'],'configuration':cfg,'calibration':cal,'spend_usd':0});print('EXPOSICION_CPU_OK',before['saturated_pct'],after['saturated_pct'],cal['global_exposure_ev'])
