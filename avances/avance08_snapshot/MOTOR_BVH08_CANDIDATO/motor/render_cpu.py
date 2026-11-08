"""Render CPU sólo después de revisión completa. N tomas, archivos nuevos, sin recorte."""
import bpy,sys,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'motor'))
from seguridad import *
from montaje_cpu import planificar
exigir('render')
args=sys.argv[sys.argv.index('--')+1:];pk=Path(args[0]);out=Path(args[1]);d=leer(pk/'entrada_escena.json');rv=leer(out/'revision_final.json')
if rv['all_passed'] is not True:raise RuntimeError('Revisión no aprobada')
sc=bpy.context.scene;r=d['render'];
if r['engine'] not in ['CYCLES','BLENDER_EEVEE']:raise ValueError('Motor de render CPU no soportado')
if r['engine']=='BLENDER_EEVEE':
 from render_estilo import configurar
 configurar(sc,d['environment']['visual_preset'],base_lighting=False)
sc.render.engine=r['engine'];sc.render.resolution_x,sc.render.resolution_y=r['resolution'];sc.render.resolution_percentage=100;sc.render.image_settings.file_format='PNG';fps=d['clock']['fps'];sc.render.fps=fps
if sc.render.engine=='CYCLES':sc.cycles.device='CPU';sc.cycles.samples=r['samples'];sc.cycles.seed=r['seed']
plan=planificar(d['camera']['shots'],fps,d['clock']['duration_s'],d['camera'].get('transition_semantics','outgoing'));clips=[]
auto=leer(ROOT/'config/exposicion_auto.json')
if auto.get('enabled'):
 from exposicion_auto import preparar,calibrar,medir,gate
 preparar(sc,auto,d.get('environment',{}).get('visual_preset',{}))
 views=[{'camera':p['id']+'_camera','frame':p['render_start']+1} for p in plan]
 guardar(out/'exposicion_auto.json',calibrar(sc,views,auto))
rendered=[]
for i,p in enumerate(plan):
    folder=out/'cuadros'/('toma_'+str(i+1));folder.mkdir(parents=True,exist_ok=False);sc.camera=bpy.data.objects[p['id']+'_camera']
    for j,f0 in enumerate(range(p['render_start'],p['end'])):
        sc.frame_set(f0+1);sc.render.filepath=str(folder/(str(j+1).zfill(6)+'.png'));bpy.ops.render.render(write_still=True)
    if auto.get('enabled'):
        histogram=medir(sorted(folder.glob('*.png')),auto);guardar(folder/'histograma.json',histogram);gate(histogram,auto)
    rendered.append((i,p,folder))
# Ningún clip se codifica hasta superar el histograma de TODAS las tomas.
for i,p,folder in rendered:
    video=out/('toma_'+str(i+1)+'.mp4')
    if video.exists():archivar(video)
    subprocess.run(['ffmpeg','-hide_banner','-loglevel','error','-nostdin','-framerate',str(fps),'-i',str(folder/'%06d.png'),'-c:v','libx264','-pix_fmt','yuv420p','-frames:v',str(p['frames']),str(video)],check=True,timeout=600);clips.append({'id':p['id'],'file':video.name,'sha256':sha(video),'frames':p['frames']})
guardar(out/'clips.json',clips)
