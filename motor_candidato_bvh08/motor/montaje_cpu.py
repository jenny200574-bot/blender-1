"""Montaje FFmpeg por reloj global, sin acortar para ocultar fallos.
Los cambios entre tomas tienen duración explícita y utilizan márgenes rendereados.
"""
from pathlib import Path
import subprocess,json
from seguridad import guardar,archivar,cuadro,sha,exigir
TRANS={'FUNDIDO':'fade','ENCADENADO':'fade','BARRIDO_IZQUIERDA':'wipeleft','BARRIDO_DERECHA':'wiperight','FUNDIDO_NEGRO':'fadeblack','FUNDIDO_BLANCO':'fadewhite'}
CUT={'CORTE','CORTE_SECO','CUT','FIN_ESCENA'}
def planificar(shots,fps,duration,convention="outgoing"):
    exigir("montaje")
    if convention not in {"incoming","outgoing"}:raise ValueError("Convención de transición desconocida")
    n=cuadro(duration,fps);out=[];last=0;ids=set()
    for i,s in enumerate(shots):
        a,b=cuadro(s['t0'],fps),cuadro(s['t1'],fps)
        if s['id'] in ids or a!=last or b<=a or b>n or s['t1']-s['t0']>10:raise ValueError('Tomas repetidas/vacías/hueco o >10s')
        tr=(shots[i-1]['transition'] if i else 'CORTE') if convention=='outgoing' else s['transition'];kind=tr['type'] if isinstance(tr,dict) else tr
        overlap=0
        if kind not in CUT and kind not in {'J_CUT','L_CUT'}:
            if kind not in TRANS and kind not in {'J_CUT','L_CUT'}:raise ValueError('Transición no soportada '+kind)
            if not isinstance(tr,dict) or 'duration_s' not in tr:raise ValueError('SB: duración de transición ausente')
            overlap=cuadro(tr['duration_s'],fps)
            if not 0<overlap<=b-a or i==0:raise ValueError('Margen de transición inválido')
        out.append({'id':s['id'],'start':a,'end':b,'render_start':a-overlap if kind in TRANS else a,'frames':b-a+(overlap if kind in TRANS else 0),'transition':kind,'overlap':overlap,'audio_handoff_omni':tr if kind in {'J_CUT','L_CUT'} else None,'transition_convention':convention});last=b;ids.add(s['id'])
    if last!=n:raise ValueError('Cobertura no completa')
    if convention=='outgoing':
        terminal=shots[-1]['transition'];kind=terminal['type'] if isinstance(terminal,dict) else terminal
        if kind in {'FUNDIDO_NEGRO','FUNDIDO_BLANCO'}:
            if not isinstance(terminal,dict) or 'duration_s' not in terminal:raise ValueError('SB: duración de fundido terminal ausente')
            frames=cuadro(terminal['duration_s'],fps)
            if not 0<frames<=out[-1]['end']-out[-1]['start']:raise ValueError('Fundido terminal fuera de toma')
            out[-1]['terminal_transition']={'type':kind,'frames':frames}
        elif kind in {'J_CUT','L_CUT'}:out[-1]['terminal_audio_handoff_omni']=terminal
        elif kind not in CUT:raise ValueError('Transición final sin destino/implementación; no se omite: '+kind)
    return out

def ejecutar(clips,plan,fps,size,duration,tracks,root,dest):
    exigir("montaje")
    dest=Path(dest);dest.mkdir(parents=True,exist_ok=True);target=dest/'video_final.mp4'
    if target.exists():archivar(target)
    cmd=['ffmpeg','-hide_banner','-loglevel','error','-nostdin'];filters=[]
    for clip in clips:cmd+=['-i',str(clip)]
    for i,p in enumerate(plan):filters.append(f'[{i}:v]settb=AVTB,setpts=PTS-STARTPTS,fps={fps},format=yuv420p[v{i}]')
    current='v0'
    for i,p in enumerate(plan[1:],1):
        name='mix'+str(i);offset=p['start']/fps
        if p['transition'] in TRANS:
            filters.append(f'[{current}][v{i}]xfade=transition={TRANS[p["transition"]]}:duration={p["overlap"]/fps:.9f}:offset={(p["start"]-p["overlap"])/fps:.9f}[{name}]')
        else:filters.append(f'[{current}][v{i}]concat=n=2:v=1:a=0[{name}]')
        current=name
    if plan[-1].get('terminal_transition'):
        tr=plan[-1]['terminal_transition'];color='black' if tr['type']=='FUNDIDO_NEGRO' else 'white';length=tr['frames']/fps;filters.append(f'[{current}]fade=t=out:st={duration-length}:d={length}:color={color}[terminal]');current='terminal'
    # J/L son desplazamientos de AUDIO explícitos; vídeo conserva corte exacto.
    audio_inputs=[]
    for i,t in enumerate(tracks):
        idx=len(clips)+i;cmd+=['-i',str(Path(root)/t['path'])]
        start=t['t0']+t.get('offset_s',0)
        if start<0:raise ValueError('Audio J/L empieza antes de escena')
        delay=round(start*1000);audio_inputs.append('aud'+str(i));filters.append(f'[{idx}:a]adelay={delay}:all=1,volume={t["gain"]}[aud{i}]')
    if audio_inputs:filters.append(''.join(f'[{x}]' for x in audio_inputs)+f'amix=inputs={len(audio_inputs)}:normalize=0,apad,atrim=duration={duration}[audio]')
    cmd+=['-filter_complex_threads','1','-filter_complex',';'.join(filters),'-map','['+current+']']
    if audio_inputs:cmd+=['-map','[audio]','-c:a','aac']
    cmd+=['-c:v','libx264','-preset','veryfast','-pix_fmt','yuv420p','-frames:v',str(cuadro(duration,fps)),'-t',str(duration),str(target)]
    r=subprocess.run(cmd,capture_output=True,text=True,timeout=600);(dest/'ffmpeg.log').write_text(r.stderr)
    if r.returncode:raise RuntimeError('Montaje falló; ver ffmpeg.log')
    probe=subprocess.run(['ffprobe','-v','error','-count_frames','-show_streams','-of','json',str(target)],capture_output=True,text=True,check=True);info=json.loads(probe.stdout);v=next(s for s in info['streams'] if s['codec_type']=='video')
    if int(v['nb_read_frames'])!=cuadro(duration,fps) or [int(v['width']),int(v['height'])]!=size:raise RuntimeError('Conteo/resolución final incorrectos')
    receipt={'path':str(target),'sha256':sha(target),'frames':int(v['nb_read_frames']),'audio':any(s['codec_type']=='audio' for s in info['streams']),'transition_plan':plan}
    guardar(dest/'montaje.json',receipt);return receipt
