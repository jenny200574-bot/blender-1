"""correr_escena — ENTRADA ÚNICA del motor unificado v1 (la llama n8n COPIA FABRICAS por HTTP/SSH o a mano el script de pruebas).
Corre en 213: preparar (moldes de la biblioteca) -> traductor (01 + 2B) -> inventario del set (Blender CPU, solo medir) ->
planificador A*+RVO2 -> trabajo GPU en RunPod (motor_blender + render + videos de revisión) -> desempaqueta en corridas/<id>.
Reglas: ledger ANTES del pod, tope por trabajo, bolsa compartida US$50 (fábrica + motor), saldo RunPod ≥ US$5, pod propio
terminado siempre, nunca Star 32soe7oh2f1gtf, claves sin imprimir.
Uso: python3 correr_escena.py --cadena DIR --escena 1 [--id nombre] [--permitir_escenario_taller] [--solo_cpu] [--autorizacion txt]
[t1066u, 10-nov-2026] STORYBOARD DESPUÉS DEL 3D (config sb_despues_3d.encendido, por defecto ON), universal para cualquier escena:
  escena armada -> sb3d.py --modo paquete (medidas reales, soporte, eje 180°, N0–N3, 4–6 candidatas + hojas de contacto) ->
  UNA llamada a Argon por escena (sb3d_argon.py, puerta de fábricas) -> sb3d.py --modo aplicar (validación 3D + respaldo a la
  siguiente candidata) -> render. Corre en 213 (CPU) entre la fase construir y la fase render del MISMO pod (hook 'entre'), o
  antes del pod si se reusa una escena ya armada.
  --reusar_corrida CID : copia JSONs, moldes y escena_motor.blend de corridas/CID (no repite Kimodo ni motor_blender).
  --tope_usd X         : tope GPU de este trabajo (no cambia config). --sb_argon_existente F : reusar una decisión (sin llamar).
  --sin_sb3d           : apaga el paso solo en esta corrida."""
import json, argparse, subprocess, sys, os, tarfile, time, shutil, signal
from pathlib import Path
from datetime import datetime
V = Path(__file__).resolve().parents[1]; MOT = V / 'motor'   # [prueba t528] COPIA: la carpeta del propio script (nunca el motor vivo)
sys.path.insert(0, str(MOT / 'gpu'))
BLENDER = os.environ.get('MOTOR_BLENDER') or '/opt/blender/5.2.3/blender'   # [argon_v2] sobreescribible (prueba en seco en otra máquina)
CFG = json.load(open(V / 'config_motor.json'))

def sh(cmd, log, env=None, timeout=1800):
    r = subprocess.run(cmd, shell=True, capture_output=True, text=True, env=env, timeout=timeout)
    log.write(f"$ {cmd}\n{r.stdout[-3000:]}\n{r.stderr[-2000:]}\n"); log.flush(); return r

def gastado_fabrica():
    try:
        d = json.load(open('/opt/myia-fabricas/ledger_gpu.json'))
        return sum(max(e.get('costo_real_usd') or 0, e.get('costo_tiempo_usd') or 0) if e.get('estado') != 'en_curso' else (e.get('tope_usd') or 0) for e in d['entradas'])
    except Exception: return 0.0

SB3D = MOT / 'blender' / 'sb3d.py'

def paso_sb3d(C: Path, log, env, autorizacion: str, argon_existente: str = '', est=None, sin_argon: bool = False) -> dict:
    """[t1066u/t1077u] storyboard después del 3D sobre una corrida LOCAL ya armada (escena_motor.blend + reporte_motor.json):
    paquete (N0–N3, soporte, eje, respaldos) -> video de revisión (planta + amplia, ~1 fps) -> UNA llamada Argon (decide libre
    cámara/plano/ángulo/lente/movimiento) -> validación 3D -> si fallan viñetas, UNA llamada de corrección solo con esas ->
    aplicar (lo que siga fallando usa la mejor opción válida, reportado). Si algo falla ANTES de aplicar, la escena queda con las
    cámaras del SB de siempre (respaldo automático)."""
    sc = dict(CFG.get('sb_despues_3d') or {}); r0 = {"inicio": datetime.now().astimezone().isoformat(timespec='seconds'), "ok": False}
    S = C / 'sb3d'; S.mkdir(exist_ok=True)
    if sc.get('umbrales'): json.dump(sc['umbrales'], open(C / 'sb3d_config.json', 'w'), indent=1)
    blend = C / 'escena_motor.blend'
    if not blend.is_file(): return dict(r0, error='no hay escena_motor.blend', respaldo='cámaras del SB (sin cambios)')
    def bl(modo, extra='', tmax=3000):
        t = time.time()
        r = sh(f"cd {MOT}/blender && {BLENDER} -b {blend} -P {SB3D} -- --corrida {C} --modo {modo} {extra}", log, env, tmax)
        return {"rc": r.returncode, "s": round(time.time() - t), "result": next((l for l in r.stdout.splitlines() if 'RESULT_SB3D' in l), (r.stdout + r.stderr)[-300:])[:700]}
    v2 = int(sc.get('version', 1)) >= 2   # [argon_v2] Argon ESCOGE entre candidatas ya medidas (sb3d_argon_v2.py)
    sim = str(sc.get('argon_simulado') or os.environ.get('MOTOR_ARGON_SIMULADO') or '')   # prueba en seco: Argon simulado (US$0)
    def argon(fase, extra=''):
        t = time.time()
        if v2:
            si = f" --simulado auto {os.environ.get('MOTOR_ARGON_SIMULADO_ARGS', '')}" if sim else ''
            r = sh(f"cd {MOT}/sb3d && python3 sb3d_argon_v2.py --corrida {C} --fase {fase} --nivel {sc.get('argon_nivel', 'LOW')} --autorizacion {json.dumps(autorizacion)} {extra}{si}", log, env, 2400)
            x = {"rc": r.returncode, "s": round(time.time() - t)}
            try: x.update(json.load(open(S / ('sb3d_argon_estado.json' if fase == 'principal' else 'sb3d_argon_estado_correccion.json'))))
            except Exception as ex: x['error'] = str(ex)
            return x
        r = sh(f"cd {MOT}/sb3d && python3 sb3d_argon.py --corrida {C} --fase {fase} --nivel {sc.get('argon_nivel', 'LOW')} --autorizacion {json.dumps(autorizacion)} {extra}", log, env, 2400)
        x = {"rc": r.returncode, "s": round(time.time() - t)}
        try: x.update(json.load(open(S / ('sb3d_argon_estado.json' if fase == 'principal' else 'sb3d_argon_estado_correccion.json'))))
        except Exception as ex: x['error'] = str(ex)
        return x
    try:
        r0['paquete'] = bl('paquete', f"--miniaturas 0 --max_candidatas {int(sc.get('max_candidatas', 6))}" + (f" --v2 1 --stills 1 --res_still {sc.get('res_still', '640x360')}" if v2 else ''), int(sc.get('paquete_max_s', 3000)))
        if not (S / 'paquete.json').is_file(): return dict(r0, error='paquete sb3d no se generó', respaldo='cámaras del SB (sin cambios)')
        if argon_existente:
            shutil.copy(argon_existente, S / 'sb_argon.json'); r0['argon'] = {"reusado": argon_existente}
            _corr = Path(argon_existente).with_name('sb_argon_correccion.json')   # [prueba t528] reusar también la corrección ya pagada (US$0)
            if _corr.is_file(): shutil.copy(_corr, S / 'sb_argon_correccion.json'); r0['argon']['correccion_reusada'] = str(_corr)
        elif v2:   # sin video de revisión: Argon ve las fotos claras de cada candidata (hoja por viñeta)
            r0['argon'] = argon('principal', f"--max_out {int(sc.get('argon_max_out_v2', 6000))}") if (not sin_argon or sim) else {"omitido": "--sin_argon"}
        else:
            if (S / 'revision_argon.mp4').is_file() and (S / 'revision_argon.json').is_file():
                r0['video'] = {"reusado": str(S / 'revision_argon.mp4')}
            else:
              r0['video'] = bl('video', f"--fps_video {float(sc.get('fps_video', 1.0))} --res_video {sc.get('res_video', '560x316')}", int(sc.get('video_max_s', 3000)))
            r0['argon'] = {"omitido": "--sin_argon (prueba en seco, US$0)"} if sin_argon else argon('principal', f"--max_out {int(sc.get('argon_max_out', 16000))}")
        if not (S / 'sb_argon.json').is_file() and not v2:
            return dict(r0, error='Argon no dio decisión válida', respaldo='cámaras del SB (sin cambios)')
        if not (S / 'sb_argon.json').is_file():   # [argon_v2] sin decisión: aplicar estricto deja TODAS las viñetas en STOP (no se filma)
            r0['alerta'] = 'Argon no dio decisión válida: todas las viñetas quedan STOP_CAMARA_SIN_SUJETO'
        r0['validacion_1'] = bl('validar', '--etiqueta_val 1 --paso_val ' + str(int(sc.get('paso_validacion', 4))), int(sc.get('aplicar_max_s', 3000)))
        try: V1 = json.load(open(S / 'validacion_argon_1.json')); r0['fallan_1'] = V1.get('fallan')
        except Exception as ex: V1 = None; r0['fallan_1'] = f'sin validación: {ex}'
        if V1 and V1.get('fallan') and sc.get('correccion', True) and not argon_existente:
            r0['argon_correccion'] = argon('correccion', f"--validacion {S / 'validacion_argon_1.json'} --max_out {int(sc.get('correccion_max_out', 5000))}")
            if v2 and (S / 'sb_argon_correccion.json').is_file():   # [argon_v2] se re-mide la corrección (ronda 2) antes de aplicar
                r0['validacion_2'] = bl('validar', '--etiqueta_val 2 --paso_val ' + str(int(sc.get('paso_validacion', 4))), int(sc.get('aplicar_max_s', 3000)))
                try: r0['fallan_2'] = json.load(open(S / 'validacion_argon_2.json')).get('fallan')
                except Exception as ex: r0['fallan_2'] = f'sin validación 2: {ex}'
        rp = C / 'reporte_motor.json'; shutil.copy(rp, S / 'reporte_motor_antes_aplicar.json')
        r0['aplicar'] = bl('aplicar', f"--guardar 1 --paso_val {int(sc.get('paso_validacion', 4))}" + (' --v2 1' if v2 else ''), int(sc.get('aplicar_max_s', 3000)))
        if r0['aplicar']['rc'] != 0:
            shutil.copy(S / 'reporte_motor_antes_aplicar.json', rp)
            return dict(r0, error='aplicar falló', respaldo='cámaras del SB (reporte restaurado; el .blend solo se guarda al final de aplicar)')
        V = json.load(open(S / 'sb3d_validacion.json'))
        r0['tabla'] = [{k: x.get(k) for k in ('vineta', 'estado', 'origen', 'plano', 'angulo', 'movimiento', 'velocidad', 'lente_mm', 'camara_pos')} for x in V['tabla']]
        r0['n0_ocultos'] = V.get('n0_ocultos'); r0['ok'] = True
        if v2:
            stop = [x['vineta'] for x in V['tabla'] if x.get('estado') == 'STOP_CAMARA_SIN_SUJETO']
            if stop:
                r0['alerta'] = f"STOP_CAMARA_SIN_SUJETO en {stop}: esas viñetas no tienen cámara válida; no se filma la escena (decisión pendiente)"
                (C / 'ALERTA_CAMARA.txt').write_text(r0['alerta'] + '\n' + '\n'.join(f"- {x['vineta']}: {'; '.join(str(t) for t in ((x.get('validacion') or {}).get('fallas') or [x.get('origen')]))[:300]}"
                                                     for x in V['tabla'] if x.get('estado') == 'STOP_CAMARA_SIN_SUJETO') + '\n', encoding='utf-8')
    except Exception as ex:
        r0['error'] = f'{type(ex).__name__}: {ex}'; r0['respaldo'] = 'cámaras del SB (sin cambios)'
    return r0

def tar_sb3d(C: Path, destino: Path):
    with tarfile.open(destino, 'w:gz') as t:
        for n in ('escena_motor.blend', 'reporte_motor.json'):
            if (C / n).exists(): t.add(C / n, arcname=n)
        if (C / 'sb3d').is_dir():
            for f in (C / 'sb3d').iterdir():
                if f.suffix in ('.json', '.jpg', '.mp4', '.md', '.txt'): t.add(f, arcname=f'sb3d/{f.name}')

def main():
    ap = argparse.ArgumentParser(); ap.add_argument('--cadena', required=True); ap.add_argument('--escena', required=True)
    ap.add_argument('--id'); ap.add_argument('--permitir_escenario_taller', action='store_true'); ap.add_argument('--permitir_faltantes', action='store_true')
    ap.add_argument('--solo_cpu', action='store_true', help='solo prepara/planifica (sin GPU)'); ap.add_argument('--autorizacion', default=CFG['gpu'].get('autorizacion', ''))
    ap.add_argument('--motor_args', default='')
    ap.add_argument('--reusar_corrida', default=''); ap.add_argument('--tope_usd', type=float, default=0.0)
    ap.add_argument('--sb_argon_existente', default=''); ap.add_argument('--sin_sb3d', action='store_true'); ap.add_argument('--sin_argon', action='store_true')
    a = ap.parse_args()
    # [t518] SIGTERM/SIGHUP (n8n o systemd matan el proceso) -> SystemExit: así corre el finally de Pod.correr y el pod se termina
    for _sg in (signal.SIGTERM, signal.SIGHUP):
        try: signal.signal(_sg, lambda n, fr: sys.exit(128 + n))
        except Exception: pass
    sb_on = bool((CFG.get('sb_despues_3d') or {}).get('encendido', True)) and not a.sin_sb3d
    cid = a.id or f"esc{a.escena}_{datetime.now():%Y%m%d_%H%M%S}"; C = V / 'corridas' / cid; C.mkdir(parents=True, exist_ok=True)
    log = open(C / 'correr_escena.log', 'a'); est = {"id": cid, "corrida": str(C), "inicio": datetime.now().astimezone().isoformat(timespec='seconds'), "pasos": {}}
    def fin(code):
        est['fin'] = datetime.now().astimezone().isoformat(timespec='seconds'); json.dump(est, open(C / 'estado.json', 'w'), indent=1, ensure_ascii=False)
        print('RESULT_CORRER', json.dumps(est, ensure_ascii=False)[:4000]); sys.exit(code)
    env = dict(os.environ, PYTHONPATH=str(V / 'py213'))
    est['sb_despues_3d'] = {"encendido": sb_on}
    if a.reusar_corrida:   # [t1066u] escena ya armada: copiar (nunca mover) y saltar preparar..planificador y la construcción en el pod
        O = V / 'corridas' / a.reusar_corrida
        for f in O.iterdir():
            if f.is_file() and f.suffix == '.json' and f.name != 'estado.json': shutil.copy(f, C / f.name)
        for dd in ('moldes', 'kimodo'):
            if (O / dd).is_dir() and not (C / dd).exists(): shutil.copytree(O / dd, C / dd)
        for cand in (O / 'escena_motor.blend', O / 'salida' / 'out' / 'escena_motor.blend'):
            if cand.is_file(): shutil.copy(cand, C / 'escena_motor.blend'); break
        if (O / 'sb3d' / 'revision_argon.mp4').is_file() and not a.sin_sb3d:   # misma escena ya armada: se reusa su video de revisión
            (C / 'sb3d').mkdir(exist_ok=True)
            for n in ('revision_argon.mp4', 'revision_argon.json', 'planta_rev.jpg'):
                if (O / 'sb3d' / n).is_file(): shutil.copy(O / 'sb3d' / n, C / 'sb3d' / n)
        for rp in (O / 'salida' / 'out' / 'reporte_motor.json', O / 'reporte_motor.json'):
            if rp.is_file(): shutil.copy(rp, C / 'reporte_motor.json'); break
        est['reusa'] = str(O); est['pasos']['reusar'] = f"copiados JSON/moldes/escena_motor.blend de {O.name}"
        if not (C / 'escena_motor.blend').is_file() or not (C / 'reporte_motor.json').is_file(): est['estado'] = 'STOP_reusar_sin_blend'; fin(10)
    flags = (' --permitir_escenario_taller' if a.permitir_escenario_taller else '') + (' --permitir_faltantes' if a.permitir_faltantes else '')
    if not a.reusar_corrida:
      r = sh(f"cd {MOT} && python3 m1_preparar.py --cadena {a.cadena} --escena {a.escena} --biblioteca {CFG['biblioteca']}/{Path(a.cadena).parent.name} --corrida {C}{flags}", log, env)
      est['pasos']['preparar'] = r.stdout.strip().splitlines()[-1] if r.stdout.strip() else r.stderr[-300:]
      if r.returncode != 0: est['estado'] = 'STOP_preparar'; fin(3)
      if CFG.get('sb_camara', 1):   # [cine_v1 t559u] creador de SB, paso cámara: beat -> tabla_decision_camara.json -> plano + reglas de secuencia
          r = sh(f"cd {MOT} && python3 sb_camara.py --corrida {C}", log, env)
          est['pasos']['sb_camara'] = next((l for l in r.stdout.splitlines() if 'RESULT_SB_CAMARA' in l), r.stderr[-300:])
          if r.returncode != 0: est['estado'] = 'STOP_sb_camara'; fin(3)
      p2b = C / 'programa_2b.json'
      r = sh(f"cd {MOT} && python3 m3_traductor.py --entrada {C}/entrada_motor.json --salida {C}/movimiento.json" + (f" --programa_2b {p2b}" if p2b.exists() else '') + (' --kimodo' if CFG.get('kimodo_encendido') else ''), log, env)
      est['pasos']['traductor'] = r.stdout.strip().splitlines()[-1] if r.stdout.strip() else r.stderr[-300:]
      if r.returncode != 0: est['estado'] = 'STOP_traductor'; fin(4)
      E = json.load(open(C / 'entrada_motor.json'))
      r = sh(f"cd {MOT}/blender && {BLENDER} -b {C}/{E['escenario']['blend']} -P inventario_set.py -- --salida {C}/inventario.json", log, env, 600)
      est['pasos']['inventario'] = next((l for l in r.stdout.splitlines() if 'RESULT_INV' in l), 'sin RESULT_INV')[:300]
      if not (C / 'inventario.json').exists(): est['estado'] = 'STOP_inventario'; fin(5)
      r = sh(f"cd {MOT} && python3 planificador.py --entrada {C}/entrada_motor.json --movimiento {C}/movimiento.json --inventario {C}/inventario.json --salida {C}/plan.json --estricto", log, env)   # [t518] rc 12 = personaje en mueble -> STOP sin GPU
      est['pasos']['planificador'] = r.stdout.strip().splitlines()[-1] if r.stdout.strip() else r.stderr[-300:]
      if r.returncode != 0: est['estado'] = 'STOP_planificador'; fin(6)
      if CFG.get('kimodo_encendido'):   # Kimodo ON (Ricardo t983u): pedidos por tramo; se generan en el pod GPU antes del motor
          r = sh(f"cd {MOT}/kimodo && python3 kimodo_pedidos.py --corrida {C}", log, env)
          est['pasos']['kimodo_pedidos'] = r.stdout.strip().splitlines()[-1] if r.stdout.strip() else r.stderr[-300:]
          if r.returncode != 0: est['estado'] = 'STOP_kimodo_pedidos'; fin(9)
    if a.reusar_corrida and sb_on:   # escena ya armada en 213: el storyboard después del 3D corre ANTES del pod (CPU, US$0 de GPU)
        est['sb3d'] = paso_sb3d(C, log, env, a.autorizacion, a.sb_argon_existente, est, a.sin_argon)
        json.dump(est, open(C / 'estado.json', 'w'), indent=1, ensure_ascii=False)
        if not est['sb3d'].get('ok') and not a.sin_argon and not a.solo_cpu and not (CFG.get('sb_despues_3d') or {}).get('gpu_si_falla_al_reusar', False):
            est['estado'] = 'STOP_sb3d_sin_decision_argon (no se crea pod: re-filmar con cámaras viejas no prueba nada)'; fin(0)   # t1093u
    if a.solo_cpu: est['estado'] = 'OK_sin_gpu'; fin(0)
    # ---- GPU
    tmp = V / 'tmp' / cid; tmp.mkdir(parents=True, exist_ok=True)
    with tarfile.open(tmp / 'motor.tgz', 'w:gz') as t: t.add(MOT, arcname='motor', filter=lambda x: None if '__pycache__' in x.name or x.name.endswith('.pyc') else x)
    with tarfile.open(tmp / 'corrida.tgz', 'w:gz') as t: t.add(C, arcname='corrida', filter=lambda x: None if x.name.endswith(('.log', 'out.tgz')) or (x.name.endswith(('.blend', '.blend1')) and '/moldes/' not in x.name) or '/salida' in x.name or '/sb3d/miniaturas' in x.name or '/sb3d/stills' in x.name else x)   # [argon_v2] los moldes .blend SÍ viajan (fallo t528)
    import gpu_pod_copia_fabrica as GP
    g = dict(CFG['gpu'])
    if a.tope_usd > 0: g['tope_por_trabajo_usd'] = a.tope_usd; est['tope_gpu_usd'] = a.tope_usd
    g['gastado_previo_usd'] = round(float(CFG['gpu'].get('gastado_previo_usd', 0)) + gastado_fabrica(), 6)
    P = GP.Pod({'gpu': g})
    gastado_motor = P.gastado()
    if gastado_motor + float(g['tope_por_trabajo_usd']) > float(CFG['gpu']['tope_motor_total_usd']) + 1e-9:
        est['estado'] = f"STOP_tope_motor: gastado {gastado_motor:.4f} + tope {g['tope_por_trabajo_usd']} > {CFG['gpu']['tope_motor_total_usd']}"; fin(7)
    def lg(m): log.write(f"[gpu] {m}\n"); log.flush()
    # [t518] barrido de huérfanos ANTES de crear nada (solo si nadie está usando la GPU; nunca Star)
    est['huerfanos_inicio'] = GP.limpiar_huerfanos_motor({'gpu': g}, log=lg) if g.get('barrido_huerfanos', True) else {'omitido': 'config gpu.barrido_huerfanos=false'}
    subir = [(tmp / 'motor.tgz', '/root/job/motor.tgz'), (tmp / 'corrida.tgz', '/root/job/corrida.tgz'),
             (MOT / 'pod' / 'pod_motor.sh', '/root/job/pod_motor.sh'), (MOT / 'pod' / 'setup_pod_rapido_fabrica_copia.sh', '/root/job/setup_pod_rapido.sh')]
    envs = ' '.join(f"{k}='{v}'" for k, v in (('MOTOR_ARGS', a.motor_args), ('MOTOR_VOL', CFG.get('motor_en_volumen') or V.name), ('RES_FINAL', CFG.get('res_final', '1280x720')), ('MUESTRAS', CFG.get('muestras', 16))))
    entre = None
    if a.reusar_corrida:
        if sb_on and (C / 'sb3d' / 'sb3d_validacion.json').is_file():
            tar_sb3d(C, tmp / 'corrida_sb3d.tgz')
        else:
            with tarfile.open(tmp / 'corrida_sb3d.tgz', 'w:gz') as t:
                for n in ('escena_motor.blend', 'reporte_motor.json'): t.add(C / n, arcname=n)
        subir.append((tmp / 'corrida_sb3d.tgz', '/root/job/corrida_sb3d.tgz'))
        comando = f"{envs} FASE=render bash /root/job/pod_motor.sh {cid}"
    elif sb_on and not (CFG.get('sb_despues_3d') or {}).get('un_solo_pod', False):
        # [t518 10-nov-2026, Ricardo: «la GPU solo cuando hace la petición y luego se apague»] DOS pods cortos:
        #   pod 1 = construir (Kimodo + motor_blender) -> trae out_fase1.tgz -> SE TERMINA (finally de Pod.correr)
        #   sb3d + Argon en 213 con la GPU APAGADA (antes el pod esperaba cobrando ~800 s por escena)
        #   pod 2 = solo render (igual que «reusar corrida», ya probado en t1095) -> trae out.tgz -> SE TERMINA
        R1 = P.correr(f"motor-{cid}-c"[:40], subir, f"{envs} FASE=construir bash /root/job/pod_motor.sh {cid}", '/root/out_fase1.tgz',
                      tmp / 'out_fase1.tgz', a.autorizacion, log=lg, setup_cmd='bash /root/job/setup_pod_rapido.sh')
        est['gpu_construir'] = {k: R1.get(k) for k in ('ok', 'pod_id', 'gpu', 'segundos_pod', 'costo_tiempo_usd', 'costo_real_usd', 'pod_terminado', 'error', 'tiempos_s', 'ledger_n')}
        json.dump(est, open(C / 'estado.json', 'w'), indent=1, ensure_ascii=False)
        if not R1.get('ok') or not (tmp / 'out_fase1.tgz').is_file():
            est['estado'] = 'FALLO_GPU'; est['motivo'] = 'fase construir: ' + str(R1.get('error') or 'sin out_fase1.tgz'); fin(8)
        with tarfile.open(tmp / 'out_fase1.tgz') as t: t.extractall(C)
        est['sb3d'] = paso_sb3d(C, log, env, a.autorizacion, a.sb_argon_existente, est, a.sin_argon)
        tabla = (est['sb3d'] or {}).get('tabla') or []
        stop_cam = [x['vineta'] for x in tabla if x.get('estado') == 'STOP_CAMARA_SIN_SUJETO']
        if stop_cam and not (CFG.get('sb_despues_3d') or {}).get('render_con_camara_sin_sujeto', False):
            est['estado'] = f"STOP_CAMARA_SIN_SUJETO {stop_cam}: no se crea el pod de render (US$0 más)"; fin(0)
        if est['sb3d'].get('ok'): tar_sb3d(C, tmp / 'corrida_sb3d.tgz')
        else:
            lg('sb3d no OK: se renderiza con la cámara del motor (marcado en estado.json)')
            with tarfile.open(tmp / 'corrida_sb3d.tgz', 'w:gz') as t:
                for n in ('escena_motor.blend', 'reporte_motor.json'): t.add(C / n, arcname=n)
        gastado_motor = P.gastado()
        if gastado_motor + float(g['tope_por_trabajo_usd']) > float(CFG['gpu']['tope_motor_total_usd']) + 1e-9:
            est['estado'] = f"STOP_tope_motor antes del render: gastado {gastado_motor:.4f}"; fin(7)
        subir = subir + [(tmp / 'corrida_sb3d.tgz', '/root/job/corrida_sb3d.tgz')]
        comando = f"{envs} FASE=render bash /root/job/pod_motor.sh {cid}"
    elif sb_on:   # modo viejo (un solo pod esperando a sb3d): solo si config sb_despues_3d.un_solo_pod = true
        comando = [f"{envs} FASE=construir bash /root/job/pod_motor.sh {cid}", f"{envs} FASE=render bash /root/job/pod_motor.sh {cid}"]
        def entre(i, ctx):   # en 213, con el pod vivo: traer la escena armada, storyboard después del 3D, subir la decisión aplicada
            ctx['traer']('/root/out_fase1.tgz', tmp / 'out_fase1.tgz')
            with tarfile.open(tmp / 'out_fase1.tgz') as t: t.extractall(C)
            est['sb3d'] = paso_sb3d(C, log, env, a.autorizacion, a.sb_argon_existente, est, a.sin_argon)
            if est['sb3d'].get('ok'):
                tar_sb3d(C, tmp / 'corrida_sb3d.tgz'); ctx['subir'](tmp / 'corrida_sb3d.tgz', '/root/job/corrida_sb3d.tgz')
            else:
                lg('sb3d no OK: se renderiza con la cámara del motor (marcado en estado.json)')
            return True
    else:
        comando = f"{envs} bash /root/job/pod_motor.sh {cid}"
    try:
        R = P.correr(f"motor-{cid}"[:40], subir, comando, '/root/out.tgz', C / 'out.tgz', a.autorizacion, log=lg,
                     setup_cmd='bash /root/job/setup_pod_rapido.sh', entre=entre)
    finally:
        est['huerfanos_fin'] = GP.limpiar_huerfanos_motor({'gpu': g}, log=lg) if g.get('barrido_huerfanos', True) else {'omitido': 'config gpu.barrido_huerfanos=false'}   # [t518] barrido al terminar (pase lo que pase)
    est['gpu'] = {k: R.get(k) for k in ('ok', 'pod_id', 'gpu', 'cloud', 'costo_hora', 'segundos_pod', 'costo_tiempo_usd', 'costo_real_usd', 'balance_runpod_despues',
                                         'pod_terminado', 'volumen_listo', 'error', 'tiempos_s', 'star_32soe7oh2f1gtf', 'ledger_n', 'tope_alcanzado', 'fases', 'entre_error')}
    est['gpu']['comando_tail'] = (R.get('comando_tail') or '')[-1500:]
    if est.get('gpu_construir'):   # [t518] costo total = pod construir + pod render
        est['gpu']['costo_total_real_usd'] = round((est['gpu_construir'].get('costo_real_usd') or 0) + (R.get('costo_real_usd') or 0), 6)
        est['gpu']['costo_total_tiempo_usd'] = round((est['gpu_construir'].get('costo_tiempo_usd') or 0) + (R.get('costo_tiempo_usd') or 0), 6)
    sal = C / 'salida' / 'out'
    if (C / 'out.tgz').exists():
        with tarfile.open(C / 'out.tgz') as t: t.extractall(C / 'salida')
        est['salida'] = str(sal)
        try:
            RM = json.load(open(sal / 'reporte_motor.json')); est['revision_ok'] = RM['pasos']['6_revision']['ok']
            if RM.get('error'): est['error_motor'] = RM['error']
        except Exception as ex: est['revision_ok'] = f'sin reporte: {ex}'
    def _okfile(p, minimo=1024):
        return p.is_file() and p.stat().st_size >= minimo
    requeridos = ['escena_motor.blend', 'final_camara_sb.mp4', 'revision_vista_amplia.mp4',
                  'revision_planta.mp4', 'REVISION_GRANDE_1920x1080.mp4']
    faltan = [n for n in requeridos if not (_okfile(sal / n) or _okfile(C / n))]
    if faltan:
        est['falta_salidas'] = faltan
        motivo = ('el pod reportó ok pero faltan o están vacíos: ' if R.get('ok')
                  else 'faltan o están vacíos: ') + ', '.join(faltan)
        if est.get('error_motor'):
            motivo += f"; motor: {est['error_motor']}"
        est['motivo'] = motivo
        est['estado'] = 'FALLO_SIN_SALIDAS' if R.get('ok') else 'FALLO_GPU'
        fin(8)
    if not R.get('ok'):
        est['estado'] = 'FALLO_GPU'
        est['motivo'] = (R.get('error') or 'pod no ok')
        fin(8)
    est['estado'] = 'OK'
    fin(0)

if __name__ == '__main__': main()
