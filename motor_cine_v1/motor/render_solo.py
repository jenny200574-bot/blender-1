# -*- coding: utf-8 -*-
"""[argon_v2u 10-nov-2026 · Ricardo t543: terminar el render de una escena YA armada, calidad MEDIA] UN pod solo de render final
(sin reconstruir, sin Argon). Blender en segundo plano en el pod; el 213 baja cada tramo mp4 apenas está listo (si el vigilante
corta por tope, lo bajado queda); al final se unen los tramos en el mp4 final. El pod se TERMINA siempre (finally de Pod.correr).
General: cualquier corrida con escena_motor.blend + entrada_motor.json.
Uso: python3 render_solo.py --corrida DIR --tope_usd 0.20 --muestras 16 [--res 1280x720] [--tramos 4] --autorizacion TXT"""
import argparse, json, subprocess, sys, tarfile, time
from pathlib import Path
from datetime import datetime
V = Path(__file__).resolve().parents[1]; MOT = V / 'motor'; sys.path.insert(0, str(MOT / 'gpu'))
import gpu_pod_copia_fabrica as GP
CFG = json.load(open(V / 'config_motor.json'))
ap = argparse.ArgumentParser(); ap.add_argument('--corrida', required=True); ap.add_argument('--tope_usd', type=float, required=True)
ap.add_argument('--muestras', type=int, default=16); ap.add_argument('--res', default=CFG.get('res_final', '1280x720')); ap.add_argument('--tramos', type=int, default=4)
ap.add_argument('--autorizacion', required=True); ap.add_argument('--tope_dia_usd', type=float, default=0.0); ap.add_argument('--gastado_dia_usd', type=float, default=0.0)
a = ap.parse_args(); C = Path(a.corrida); E = json.load(open(C / 'entrada_motor.json')); N = int(E['N'])
S = C / 'render_solo'; S.mkdir(exist_ok=True); log = open(S / 'render_solo.log', 'a')
def lg(m): log.write(f"[{datetime.now().astimezone():%H:%M:%S}] {m}\n"); log.flush(); print(m, flush=True)
if a.tope_dia_usd and a.gastado_dia_usd + a.tope_usd > a.tope_dia_usd + 1e-9:
    lg(f'STOP: gastado del día {a.gastado_dia_usd} + tope del pod {a.tope_usd} > tope del día {a.tope_dia_usd}'); sys.exit(7)
tmp = V / 'tmp' / f'render_solo_{C.name}'; tmp.mkdir(parents=True, exist_ok=True)
with tarfile.open(tmp / 'motor.tgz', 'w:gz') as t: t.add(MOT, arcname='motor', filter=lambda x: None if '__pycache__' in x.name or x.name.endswith('.pyc') else x)
with tarfile.open(tmp / 'corrida.tgz', 'w:gz') as t:
    t.add(C / 'entrada_motor.json', arcname='corrida/entrada_motor.json')
    if (C / 'moldes').is_dir(): t.add(C / 'moldes', arcname='corrida/moldes')
with tarfile.open(tmp / 'corrida_sb3d.tgz', 'w:gz') as t:
    for n in ('escena_motor.blend', 'reporte_motor.json'): t.add(C / n, arcname=n)
subir = [(tmp / 'motor.tgz', '/root/job/motor.tgz'), (tmp / 'corrida.tgz', '/root/job/corrida.tgz'), (tmp / 'corrida_sb3d.tgz', '/root/job/corrida_sb3d.tgz'),
         (MOT / 'pod' / 'render_tramos.sh', '/root/job/render_tramos.sh'), (MOT / 'pod' / 'setup_pod_rapido_fabrica_copia.sh', '/root/job/setup_pod_rapido.sh')]
envs = f"MOTOR_VOL='{CFG.get('motor_en_volumen') or V.name}' RES_FINAL='{a.res}' MUESTRAS='{a.muestras}'"
lim = [round(i * N / a.tramos) for i in range(a.tramos + 1)]
rangos = [(lim[i] + 1, lim[i + 1]) for i in range(a.tramos)]
cmds = [f"{envs} bash /root/job/render_tramos.sh iniciar && {envs} bash /root/job/render_tramos.sh tramo {rangos[0][0]} {rangos[0][1]} 1"]
cmds += [f"{envs} bash /root/job/render_tramos.sh tramo {f0} {f1} {k + 1}" for k, (f0, f1) in enumerate(rangos) if k > 0]
bajados = []
def entre(i, ctx):   # tras la fase i: bajar el tramo i+1 ya codificado
    d = S / f'tramo_{i + 1}.mp4'; ctx['traer'](f'/root/out/tramo_{i + 1}.mp4', d); bajados.append(str(d)); lg(f'tramo {i + 1} bajado ({d.stat().st_size} bytes)'); return True
g = dict(CFG['gpu']); g['tope_por_trabajo_usd'] = a.tope_usd
P = GP.Pod({'gpu': g})
if P.gastado() + a.tope_usd > float(CFG['gpu'].get('tope_motor_total_usd') or 0) + 1e-9: lg(f'STOP_tope_motor: gastado {P.gastado():.4f} + tope {a.tope_usd}'); sys.exit(7)
lg(f'render solo: {N} cuadros en {a.tramos} tramos {rangos}, {a.res}, {a.muestras} muestras, tope US${a.tope_usd}')
R = P.correr(f"motor-render-{C.name}"[:40], subir, cmds, f'/root/out/tramo_{a.tramos}.mp4', S / f'tramo_{a.tramos}.mp4', a.autorizacion, log=lg,
             setup_cmd='bash /root/job/setup_pod_rapido.sh', entre=entre)
if (S / f'tramo_{a.tramos}.mp4').is_file(): bajados.append(str(S / f'tramo_{a.tramos}.mp4'))
res = {k: R.get(k) for k in ('ok', 'pod_id', 'gpu', 'cloud', 'costo_hora', 'segundos_pod', 'costo_tiempo_usd', 'costo_real_usd', 'pod_terminado', 'tope_alcanzado', 'error', 'tiempos_s', 'ledger_n', 'fases')}
res['tramos_bajados'] = bajados
json.dump(res, open(S / 'render_solo_estado.json', 'w'), indent=1, ensure_ascii=False, default=str)   # antes de unir: el estado del pod nunca se pierde
FF = None
try:
    import imageio_ffmpeg; FF = imageio_ffmpeg.get_ffmpeg_exe()
except Exception:
    import shutil; FF = shutil.which('ffmpeg')
if len(bajados) == a.tramos and not FF:
    res['final'] = None; res['concat_pendiente'] = 'sin ffmpeg en esta máquina: unir los tramos con lista.txt (ffmpeg -f concat -c copy)'
    (S / 'lista.txt').write_text(''.join(f"file '{Path(b).name}'\n" for b in bajados))
if len(bajados) == a.tramos and FF:
    (S / 'lista.txt').write_text(''.join(f"file '{b}'\n" for b in bajados))
    fin = C / 'final_camara_sb.mp4'
    r = subprocess.run([FF, '-y', '-loglevel', 'error', '-f', 'concat', '-safe', '0', '-i', str(S / 'lista.txt'), '-c', 'copy', str(fin)], capture_output=True, text=True)
    res['final'] = str(fin) if r.returncode == 0 and fin.is_file() else None; res['concat_error'] = r.stderr[-300:] or None
json.dump(res, open(S / 'render_solo_estado.json', 'w'), indent=1, ensure_ascii=False, default=str)
print('RESULT_RENDER_SOLO', json.dumps({k: res.get(k) for k in ('ok', 'pod_id', 'segundos_pod', 'costo_real_usd', 'costo_tiempo_usd', 'pod_terminado', 'tope_alcanzado', 'final', 'error')}, default=str))
