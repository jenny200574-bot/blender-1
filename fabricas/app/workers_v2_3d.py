# -*- coding: utf-8 -*-
"""workers_v2_3d.py — [fábricas v2 3D, 9-nov-2026, OK Ricardo pt993u/pt994u] La fábrica CONSTRUYE de verdad en 3D y publica.
Regla permanente de Ricardo: la fábrica construye real y queda encendida; todo lo construido sube a /opt/myia-biblioteca;
no está amarrada a ningún canal (canal e id son parámetros); las pruebas nunca a mano y siempre en GPU (RunPod), con tope.
Orden por trabajo:
  1. lo de v1 (workers.py, intacto): biblioteca primero (reusar aprobado) → vía B Wikipedia gratis → copias del pedido.
  2. personaje humano: generar_ficha_humana.py desde el ADN sellado (altura en metros, cabezas, colores, ropa, pelo) → STOP si
     falta o choca la altura. No humano → «esperando_pago_argon» (Argon sigue apagado; se aprueba aparte).
  3. GPU (gpu_pod.py): constructor_blender + medir_altura + hoja en un pod RunPod con Blender 5.2.3 EGL; el pod se termina siempre.
  4. altura: cubo_fijo_v2 comparar_altura (misma función, ±2 %): ADN manda; si no cuadra → STOP, no se publica hoja.
  5. publicar en <bib>/<canal>/<tipo>/<id>/: blend/vNNN, ficha_esqueleto/vNNN, renders/vNNN (HOJA), recibos/vNNN; meta.json.
     Estado de la pieza: «hoja_lista» (espera aprobación de Ricardo → «aprobado»). Estado del trabajo: «listo».
  escenario: plan_escenario → ensamblar (213, Python) → construir_render + hoja en GPU → publicar. objeto: v1 (receta) por ahora.
"""
from __future__ import annotations
import ast, json, shutil, subprocess, tarfile, traceback
from pathlib import Path
from biblioteca import Biblioteca, now_iso
import workers as v1
from gpu_pod import Pod, limpiar_huerfanos

ROOT = Path(__file__).resolve().parents[1]
try:
    _CFG0 = json.loads((ROOT / 'config' / 'config.json').read_text(encoding='utf-8'))
    _H = limpiar_huerfanos(_CFG0)
    if _H: print('workers_v2_3d: pods huérfanos terminados', _H, flush=True)
except Exception as _e:
    print('workers_v2_3d: limpiar_huerfanos', _e, flush=True)

TIPO = {'personaje': 'personajes', 'escenario': 'escenarios', 'objeto': 'objetos', 'objeto_usuario': 'objetos_usuario'}

def _comparar_altura_cubo_v2(cfg):
    """Toma comparar_altura y TOL_ALTURA tal cual de cubo_fijo_v2 (fase 2), sin ejecutar ese script."""
    src = Path(cfg['constructores']['cubo_fijo_v2']).read_text(encoding='utf-8')
    mod = ast.parse(src); keep = []
    for n in mod.body:
        if isinstance(n, ast.FunctionDef) and n.name == 'comparar_altura': keep.append(n)
        if isinstance(n, ast.Assign) and any(getattr(t, 'id', '') == 'TOL_ALTURA' for t in n.targets): keep.append(n)
    ns = {}; exec(compile(ast.Module(body=keep, type_ignores=[]), 'cubo_fijo_v2:comparar_altura', 'exec'), ns)
    return ns['comparar_altura'], ns['TOL_ALTURA']

def _version(d: Path) -> str:
    vs = [int(p.name[1:]) for sub in ('blend', 'renders', 'ficha_esqueleto', 'recibos') for p in (d / sub).glob('v[0-9][0-9][0-9]') if p.is_dir()]
    return f'v{(max(vs) + 1) if vs else 1:03d}'

def _log(job, msg):
    job['log'].append(f'{now_iso()} {msg}')

def _guardar(job, cfg):
    p = Path(cfg['jobs_root']) / f"{job['id']}.json"; tmp = p.with_suffix('.parcial')
    tmp.write_text(json.dumps(job, ensure_ascii=False, indent=1), encoding='utf-8'); tmp.replace(p)

def _meta(bib, canal, tipo, pid, **kw):
    d = bib.pieza_dir(canal, tipo, pid); m = bib.leer_meta(canal, tipo, pid); m.update(kw); m['updated_at'] = now_iso()
    bib._save(d / 'meta.json', m)
    idx_p = bib.canal_dir(canal) / 'indice.json'; idx = json.loads(idx_p.read_text(encoding='utf-8'))
    key =[REDACTED]
    e.append({'key': key, 'tipo': tipo, 'id': pid, 'estado': m.get('estado'), 'updated_at': m['updated_at']}); idx['entries'] = e
    idx['updated_at'] = now_iso(); bib._save(idx_p, idx)
    return m

def run_job(job: dict, cfg: dict, bib: Biblioteca) -> dict:
    if job['kind'] in ('objeto', 'objeto_usuario') and (cfg.get('construir_3d') or {}).get('objeto'):
        # [t1027u] un solo «id» de n8n → ids=[id] por el MISMO lote (antes, lo gratis de v1: biblioteca/corpus); objeto_usuario → objetos_usuario/
        if not job['payload'].get('ids'):
            if not job['payload'].get('id'): job['estado'] = 'stop_falta_dato'; _log(job, 'objeto sin id ni ids'); return job
            job = v1.run_job(job, cfg, bib)
            if job.get('estado') == 'reusado': return job
            job['payload']['ids'] = [job['payload']['id']]; job['payload']['_id_unico'] = True
        job['worker'] = 'workers_v2_3d'
        try: return _objetos_lote(job, cfg, bib)
        except Exception as e:
            job['estado'] = 'error'; job['error'] = f'{type(e).__name__}: {e}'; job['trace'] = traceback.format_exc()[-2000:]; return job
    job = v1.run_job(job, cfg, bib)                 # 1) lo de siempre (gratis)
    if job.get('estado') == 'reusado': return job
    job['worker'] = 'workers_v2_3d'
    job['estado_v1'] = job.get('estado'); job['estado'] = 'construyendo'   # [20261110] no mostrar «listo_parcial» de v1 mientras v2 construye
    try:
        if job['kind'] == 'personaje': return _personaje(job, cfg, bib)
        if job['kind'] == 'escenario' and (cfg.get('construir_3d') or {}).get('escenario'): return _escenario(job, cfg, bib)
        _log(job, f"{job['kind']}: construcción 3D v2 aún no conectada para este tipo; queda lo de v1 ({job.get('estado')})")
        return job
    except Exception as e:
        job['estado'] = 'error'; job['error'] = f'{type(e).__name__}: {e}'; job['trace'] = traceback.format_exc()[-2000:]
        return job

# ------------------------------------------------------------------ objetos (lote: varios moldes en UN pod)
def _objetos_lote(job, cfg, bib):
    """Cada objeto (sello cubo_fijo/objetos_pj/<id>.json → ids_canal) se saca del escenario YA construido y publicado donde
    aparece (ensamblado star_recetas > star; con forma Star o receta Argon aprobada), se arma solo en Blender en el pod, se mide
    (alto vs caja 4a2 ±2 %) y se publica en objetos/<id>/. Si en ningún escenario tiene forma/receta → FALTA (no se inventa)."""
    C = cfg['constructores']; p = job['payload']; canal = p['canal']; ids = p['ids']; cubo = Path(C['cubo_fijo_raiz'])
    esc_root = Path(cfg['biblioteca_root']) / canal / 'escenarios'
    tipo_pub = TIPO.get(job['kind'], 'objetos')   # [t1027u] objeto → objetos/, objeto_usuario → objetos_usuario/
    pre = v1.prefijo_canal(bib, canal, cfg)   # [t1027u] prefijo de ids del canal (workers.prefijo_canal: desde los datos)
    ens = []
    for e in sorted(esc_root.glob('*')):
        for modo in ('star_recetas', 'star'):
            c = sorted(e.glob(f'datos/v*/ensamblado_{modo}.json'))
            if c: ens.append((e.name, modo, c[-1])); break
    tmp = ROOT / 'tmp' / f"objetos_{job['id']}"; (tmp / 'objetos').mkdir(parents=True, exist_ok=True)
    plan, job['objetos'] = {}, {}
    if p.get('recetas_sueltas'):   # [20261110] objetos sin forma en ningún escenario → receta Argon vía B propia (misma puerta)
        _recetas_sueltas(job, cfg, bib, p['recetas_sueltas'])
    obj_root = Path(cfg['biblioteca_root']) / canal / tipo_pub
    for oid in ids:
        sp = cubo / 'objetos_pj' / f'{oid}.json'
        if p.get('_id_unico') and p.get('sello_path') and Path(p['sello_path']).is_file(): sp = Path(p['sello_path'])   # sello que trae n8n
        if not sp.is_file(): job['objetos'][oid] = {'estado': 'stop_falta_dato', 'motivo': f'sin sello {sp}'}; continue
        s_ = json.loads(sp.read_text(encoding='utf-8')); claves = [x for x in (s_.get('ids_canal') or []) if x.startswith('obj-')]
        corto = oid[len(pre):] if pre and oid.startswith(pre) else oid
        claves =[REDACTED]
        mejor = None
        # 1.º receta Argon vía B aprobada (aunque el objeto vaya en la mano y no se dibuje en el set)
        for rv in (sorted(obj_root.glob(f'{oid}/receta/v*/recetas_validas.json'), reverse=True) + sorted(esc_root.glob('*/receta/v*/recetas_validas.json'), reverse=True)):
            R_ = json.loads(rv.read_text(encoding='utf-8'))
            k_ = next((k for k in R_ if any(k == c or k.startswith(c + '-') for c in claves)), None)
            if k_:
                mejor = (0, rv.parts[-4], 'receta', rv, k_, {'id': k_, 'forma': 'receta Argon vía B (aprobada)', 'caja': R_[k_].get('caja_m')}); break
        for esc, modo, f in (ens if mejor is None else []):
            E = json.loads(f.read_text(encoding='utf-8'))
            for it in E['objetos']:
                base = it['id'].split('#')[0]
                if _coincide_pieza(base, claves, corto, esc):
                    falta = any(q.get('falta') for q in it['piezas'])
                    cand = (0 if not falta else 1, esc, modo, f, base, it)
                    if mejor is None or cand[0] < mejor[0]: mejor = cand
        if mejor is None: job['objetos'][oid] = {'estado': 'stop_falta_dato', 'motivo': f'{claves} no aparece en ningún escenario construido ({[e[0] for e in ens]})'}; continue
        falta, esc, modo, f, base, it = mejor
        od = tmp / 'objetos' / oid; od.mkdir(exist_ok=True)
        src = ['--receta', str(f)] if modo == 'receta' else ['--ensamblado', str(f)]
        r = subprocess.run(['/usr/bin/python3', str(Path(C['raiz']) / 'objetos' / 'extraer_objeto.py'), *src, '--objeto', base, '--salida', str(od / 'piezas.json')],
                           capture_output=True, text=True, timeout=120)
        if r.returncode != 0: job['objetos'][oid] = {'estado': 'error', 'motivo': r.stderr[-300:]}; continue
        alto = (it.get('caja') or {}).get('alto') if modo == 'receta' else None
        if alto is None:   # alto de referencia = caja del objeto en el plan del escenario (4a1/4a2), no lo que mide Blender
            pf = sorted((esc_root / esc / 'datos').glob(f'v*/plan_{esc}.json'))
            if pf:
                pi = next((q for q in json.loads(pf[-1].read_text(encoding='utf-8'))['objetos'] if (q.get('oid') or q['id']).split('#')[0] == base or q['id'] == it['id']), None)
                if pi: alto = pi.get('h')
        (od / 'alto_ref.txt').write_text(str(alto or '')); forma = it.get('forma') or (f"Star {it.get('fid')}" if it.get('fid') else '')
        (od / 'fuente.txt').write_text(f'{esc} · {modo} · {base} · {forma}'[:140])
        plan[oid] = {'escenario': esc, 'modo': modo, 'ensamblado': str(f), 'instancia': it['id'], 'falta': bool(falta), 'alto_ref_m': alto, 'forma': forma}
        job['objetos'][oid] = {'estado': 'preparado', **plan[oid]}
    _log(job, f"objetos preparados {len(plan)}/{len(ids)}; sin escenario/forma: {[k for k, v in job['objetos'].items() if v['estado'] != 'preparado']}"); _guardar(job, cfg)
    if not plan: job['estado'] = 'stop_falta_dato'; return job
    tgz_cons = ROOT / 'tmp' / f"constructores_{job['id']}.tgz"
    with tarfile.open(tgz_cons, 'w:gz') as t: t.add(C['raiz'], arcname='constructores', filter=lambda ti: None if '__pycache__' in ti.name else ti)
    tgz_o = ROOT / 'tmp' / f"objetos_{job['id']}.tgz"
    with tarfile.open(tgz_o, 'w:gz') as t: t.add(tmp / 'objetos', arcname='objetos')
    rec = ROOT / 'recibos_lotes' / job['id']; rec.mkdir(parents=True, exist_ok=True)
    job['estado'] = 'construyendo'; _guardar(job, cfg)
    est = Pod(cfg).correr(etiqueta=f"obj-lote-{len(plan)}", autorizacion=cfg['gpu'].get('autorizacion'),
                          subir=[(tgz_cons, '/root/job/constructores.tgz'), (tgz_o, '/root/job/objetos.tgz')],
                          comando='cd /root/job && tar xzf constructores.tgz && tar xzf objetos.tgz && bash constructores/pod/run_objetos_pod.sh',
                          traer='/root/out.tgz', destino=rec / 'out.tgz', log=lambda m: (_log(job, 'gpu: ' + m), _guardar(job, cfg)),
                          setup_cmd='cd /root/job && tar xzf constructores.tgz && bash constructores/pod/setup_pod_rapido.sh')
    (rec / 'gpu_estado.json').write_text(json.dumps(est, ensure_ascii=False, indent=1), encoding='utf-8')
    gasto = max(est.get('costo_real_usd') or 0, est.get('costo_tiempo_usd') or 0); job['gasto_usd'] = round(gasto, 6)
    job['gpu'] = {k: est.get(k) for k in ('pod_id', 'gpu', 'cloud', 'costo_hora', 'segundos_pod', 'costo_tiempo_usd', 'costo_real_usd', 'balance_runpod_despues', 'pod_terminado', 'ledger_n', 'error', 'tiempos_s', 'volumen_listo')}
    if not (rec / 'out.tgz').is_file(): job['estado'] = 'error_gpu'; return job
    with tarfile.open(rec / 'out.tgz') as t: t.extractall(rec)
    import re as _re
    tt = {m.group(1): float(m.group(2)) for m in _re.finditer(r'T_OBJ_(?:INI|FIN)_(\S+) ([0-9.]+)', est.get('comando_tail') or '')}
    comparar, tol = _comparar_altura_cubo_v2(cfg); por_obj = round(gasto / max(1, len(plan)), 6)
    for oid, info in plan.items():
        o = rec / 'out' / oid; tipo = tipo_pub; d = bib.pieza_dir(canal, tipo, oid); ver = _version(d)
        med = json.loads((o / 'medida.json').read_text()) if (o / 'medida.json').is_file() else {}
        blend = o / 'blend' / f'{oid}.blend'; hoja = o / 'renders' / f'HOJA_{oid}.png'
        if not blend.is_file(): job['objetos'][oid].update(estado='error_construccion'); continue
        alt = comparar({'id': oid, 'altura_m': info['alto_ref_m'], 'altura_blender_m': med.get('alto_m')}) if info['alto_ref_m'] else {'estado': 'SIN_REFERENCIA', 'diferencia_pct': None}
        bdir, rdir, rcd = d / 'blend' / ver, d / 'renders' / ver, d / 'recibos' / ver
        for x in (bdir, rdir, rcd): x.mkdir(parents=True, exist_ok=True)
        shutil.copy2(blend, bdir / blend.name)
        for f in (o / 'renders').glob('*'): shutil.copy2(f, rdir / f.name)
        for f in ('medida.json', 'blender.log'):
            if (o / f).is_file(): shutil.copy2(o / f, rcd / f)
        shutil.copy2(tmp / 'objetos' / oid / 'piezas.json', rcd / 'piezas.json')
        bib.registrar_version(canal, tipo, oid, 'blend', bdir / blend.name, {'version': ver, 'gasto_usd': por_obj, 'origen': info})
        estado = 'hoja_lista' if not info['falta'] and alt['estado'] in ('OK', 'SIN_REFERENCIA') else ('falta_receta' if info['falta'] else 'stop_altura')
        m = bib.leer_meta(canal, tipo, oid)
        _meta(bib, canal, tipo, oid, estado=estado, gasto_usd_acum=round((m.get('gasto_usd_acum') or 0) + por_obj, 6),
              v2_3d={'version': ver, 'blend': f'blend/{ver}/{blend.name}', 'hoja': f'renders/{ver}/{hoja.name}', 'alto_m_medido': med.get('alto_m'),
                     'alto_m_ref_4a2': info['alto_ref_m'], 'altura': alt, 'origen': info, 'gpu': est.get('gpu'), 'gasto_usd': por_obj, 'construido': now_iso()})
        seg = round(tt.get(f'{oid}_FIN', 0) - tt.get(f'{oid}_INI', 0), 1) if f'{oid}_INI' in tt else None
        job['objetos'][oid].update(estado=estado, version=ver, alto_medido_m=med.get('alto_m'), altura=alt, hoja=str(rdir / hoja.name), blender_s=seg, gasto_usd=por_obj)
    job['estado'] = 'listo'; return job


# ------------------------------------------------------------------ personaje
def _personaje(job, cfg, bib):
    C = cfg['constructores']; p = job['payload']; canal, pid = p['canal'], p['id']; tipo = 'personajes'
    d = bib.pieza_dir(canal, tipo, pid); ver = _version(d)
    cubo = Path(C['cubo_fijo_raiz'])
    adn = Path(p.get('adn_path') or '')
    sellado = cubo / 'adn' / f'{pid}_ako.json'
    if sellado.is_file(): adn = sellado                                  # manda el ADN sellado del cubo
    sello = Path(p.get('sello_path') or cubo / 'personajes' / f'{pid}.json')
    tabla = Path(C['tablas_personajes'].format(canal=canal))
    if not adn.is_file() or not sello.is_file():
        job['estado'] = 'stop_falta_dato'; _log(job, f'falta ADN ({adn}) o sello ({sello})'); return job
    fdir = d / 'ficha_esqueleto' / ver
    if p.get('ficha_path'):
        # ficha de esqueleto ya hecha (no humana / investigada): se valida igual; la altura la manda el sello del cubo
        src = Path(p['ficha_path']); fdir.mkdir(parents=True, exist_ok=True)
        if not src.is_file(): job['estado'] = 'stop_falta_dato'; _log(job, f'falta ficha_path {src}'); return job
        fj = json.loads(src.read_text(encoding='utf-8')); s_json = json.loads(sello.read_text(encoding='utf-8'))
        h_s = s_json.get('altura_m')
        if h_s is None: job['estado'] = 'stop_falta_dato'; _log(job, 'sello sin altura_m'); return job
        fj.setdefault('calibracion', {})['altura_ficha_original_m'] = fj.get('altura_m'); fj['altura_m'] = float(h_s)
        if fj.get('id') != pid: fj.setdefault('calibracion', {})['id_ficha_original'] = fj.get('id'); fj['id'] = pid   # nombres de mallas/renders = id real
        (fdir / 'ficha_esqueleto.json').write_text(json.dumps(fj, ensure_ascii=False, indent=1), encoding='utf-8')
        shutil.copy2(src, fdir / ('ORIGINAL_' + src.name))
        fr = {'estado': 'FICHA_DADA', 'altura_m': float(h_s), 'fuente': str(src)}; r = None
        job['ficha'] = fr; _log(job, f"ficha dada {src} → altura del sello {h_s} m")
    else:
      r = subprocess.run(['/usr/bin/python3', str(Path(C['raiz']) / 'personajes' / 'generar_ficha_humana.py'), '--adn', str(adn), '--sello', str(sello),
                        '--tabla', str(tabla), '--canal', canal, '--id', pid, '--salida', str(fdir)], capture_output=True, text=True, timeout=120)
      fr = json.loads((r.stdout.strip().splitlines() or ['{}'])[-1])
      job['ficha'] = fr; _log(job, f"ficha: {fr.get('estado')} rc={r.returncode}")
    if r is None: pass
    elif r.returncode == 4:
        job['estado'] = 'esperando_pago_argon'; _meta(bib, canal, tipo, pid, estado='esperando_pago_argon', nota_v2=fr.get('motivo')); return job
    elif r.returncode != 0:
        job['estado'] = 'stop_altura' if 'ALTURA' in str(fr) or 'CONFLICTO' in fr.get('estado', '') or 'FALTA' in fr.get('estado', '') else 'error'
        job['motivo'] = fr.get('motivo'); _meta(bib, canal, tipo, pid, estado=job['estado'], motivo_v2=fr.get('motivo')); return job
    ficha = fdir / 'ficha_esqueleto.json'; altura_adn = fr['altura_m']
    # validar la ficha en el 213 (Python, US$0) ANTES de pagar un pod
    rv = subprocess.run(['/usr/bin/python3', '-c', 'import sys,json; sys.path.insert(0, sys.argv[1]); import validador as V; '
                         'v = V.validar(json.load(open(sys.argv[2]))); print(json.dumps({"apta": v.apta, "errores": v.errores}, ensure_ascii=False))',
                         str(Path(C['raiz']) / 'prototipo_esqueletos'), str(ficha)], capture_output=True, text=True, timeout=60)
    val = json.loads((rv.stdout.strip().splitlines() or ['{"apta": false}'])[-1]); job['validacion_ficha'] = val
    if not val.get('apta'):
        job['estado'] = 'ficha_rechazada'; _log(job, f"ficha RECHAZADA por validador (sin pod, US$0): {val.get('errores')}")
        _meta(bib, canal, tipo, pid, estado='ficha_rechazada'); return job
    bib.registrar_version(canal, tipo, pid, 'ficha_esqueleto', ficha, {'version': ver, 'origen': 'plantilla', 'gasto_usd': 0})
    _meta(bib, canal, tipo, pid, estado='construyendo'); job['estado'] = 'construyendo'; _guardar(job, cfg)
    # ---- GPU ----
    tgz_cons = ROOT / 'tmp' / f"constructores_{job['id']}.tgz"; tgz_cons.parent.mkdir(exist_ok=True)
    with tarfile.open(tgz_cons, 'w:gz') as t: t.add(C['raiz'], arcname='constructores', filter=lambda ti: None if '__pycache__' in ti.name else ti)
    rec = d / 'recibos' / ver; rec.mkdir(parents=True, exist_ok=True)
    pod = Pod(cfg)
    est = pod.correr(etiqueta=f'pj-{pid}', autorizacion=job['payload'].get('autorizacion') or cfg['gpu'].get('autorizacion'),
                     subir=[(tgz_cons, '/root/job/constructores.tgz'), (ficha, '/root/job/ficha_esqueleto.json')],
                     comando=f'cd /root/job && tar xzf constructores.tgz && bash constructores/pod/run_personaje_pod.sh {pid} {altura_adn}',
                     traer='/root/out.tgz', destino=rec / 'out.tgz', log=lambda m: (_log(job, 'gpu: ' + m), _guardar(job, cfg)),
                     setup_cmd='cd /root/job && tar xzf constructores.tgz && bash constructores/pod/setup_pod_rapido.sh')
    t_pub = __import__('time').time()
    (rec / 'gpu_estado.json').write_text(json.dumps(est, ensure_ascii=False, indent=1), encoding='utf-8')
    job['gpu'] = {k: est.get(k) for k in ('pod_id', 'gpu', 'cloud', 'costo_hora', 'segundos_pod', 'costo_tiempo_usd', 'costo_real_usd',
                                           'balance_runpod_despues', 'pod_terminado', 'ledger_n', 'error', 'star_32soe7oh2f1gtf', 'comando_rc',
                                           'tiempos_s', 'volumen_listo')}
    import re as _re
    _t = {m.group(1): float(m.group(2)) for m in _re.finditer(r'T_(\w+) ([0-9.]+)', est.get('comando_tail') or '')}
    _ts = job['gpu'].setdefault('tiempos_s', {}) if isinstance(job['gpu'].get('tiempos_s'), dict) else job['gpu'].update(tiempos_s={}) or job['gpu']['tiempos_s']
    if 'CONSTRUIR_INI' in _t and 'CONSTRUIR_FIN' in _t: _ts['blender_construir_y_renders'] = round(_t['CONSTRUIR_FIN'] - _t['CONSTRUIR_INI'], 1)
    if 'MEDIR_INI' in _t and 'HOJA_INI' in _t: _ts['medir_altura'] = round(_t['HOJA_INI'] - _t['MEDIR_INI'], 1)
    if 'HOJA_INI' in _t and 'HOJA_FIN' in _t: _ts['hoja_png'] = round(_t['HOJA_FIN'] - _t['HOJA_INI'], 1)
    if 'CALIBRAR_INI' in _t and 'CALIBRAR_FIN' in _t: _ts['calibrar_altura_reconstruir'] = round(_t['CALIBRAR_FIN'] - _t['CALIBRAR_INI'], 1)
    gasto = max(est.get('costo_real_usd') or 0, est.get('costo_tiempo_usd') or 0); job['gasto_usd'] = round(gasto, 6)
    if not (rec / 'out.tgz').is_file():
        job['estado'] = 'error_gpu'; _meta(bib, canal, tipo, pid, estado='error_gpu'); return job
    with tarfile.open(rec / 'out.tgz') as t: t.extractall(rec)
    out = rec / 'out'
    medida = json.loads((out / 'medida.json').read_text()) if (out / 'medida.json').is_file() else {}
    informe = json.loads((out / 'renders' / f'{pid}_informe.json').read_text()) if (out / 'renders' / f'{pid}_informe.json').is_file() else {}
    # ---- altura: cubo_fijo_v2 ----
    comparar, tol = _comparar_altura_cubo_v2(cfg)
    alt = comparar({'id': pid, 'altura_m': altura_adn, 'altura_blender_m': medida.get('altura_medida_m')})
    job['altura'] = alt; _log(job, f"altura ADN {altura_adn} m vs Blender {medida.get('altura_medida_m')} m → {alt['estado']} ({alt['diferencia_pct']} %)")
    blend_src = out / 'blend' / f'{pid}.blend'; hoja_src = out / 'renders' / f'HOJA_{pid}.png'
    if alt['estado'] != 'OK' or not blend_src.is_file():
        job['estado'] = 'stop_altura' if blend_src.is_file() else 'error_construccion'
        _meta(bib, canal, tipo, pid, estado=job['estado'], altura_v2=alt, gasto_usd_acum=round((bib.leer_meta(canal, tipo, pid).get('gasto_usd_acum') or 0) + gasto, 6))
        return job
    # ---- publicar ----
    bdir = d / 'blend' / ver; rdir = d / 'renders' / ver; bdir.mkdir(parents=True, exist_ok=True); rdir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(blend_src, bdir / blend_src.name)
    for f in (out / 'renders').glob('*'): shutil.copy2(f, rdir / f.name)
    for f in ('medida.json', 'gpu.txt', 'gpu_uso.csv', 'constructor.log', 'medir.log'):
        if (out / f).is_file(): shutil.copy2(out / f, rdir / f)
    bib.registrar_version(canal, tipo, pid, 'blend', bdir / blend_src.name, {'version': ver, 'gpu': est.get('gpu'), 'gasto_usd': gasto})
    if hoja_src.is_file(): bib.registrar_version(canal, tipo, pid, 'hoja', rdir / hoja_src.name, {'version': ver})
    m = bib.leer_meta(canal, tipo, pid)
    meta = _meta(bib, canal, tipo, pid, estado='hoja_lista' if hoja_src.is_file() else 'parcial_sin_hoja', approval_ref=None,
                 gasto_usd_acum=round((m.get('gasto_usd_acum') or 0) + gasto, 6),
                 v2_3d={'version': ver, 'fabrica': 'workers_v2_3d + constructores_v1_20261109', 'plantilla': 'bipedo_humano',
                        'altura_m_adn': altura_adn, 'altura_m_medida': medida.get('altura_medida_m'), 'altura_diferencia_pct': alt['diferencia_pct'],
                        'altura_estado': alt['estado'], 'tolerancia': tol, 'n_huesos': informe.get('n_huesos'), 'n_piezas_ficha': fr.get('n_piezas'),
                        'n_objetos_blend': informe.get('n_objetos'), 'n_colores': medida.get('n_materiales'), 'prueba_pose': informe.get('resultado'),
                        'blender': informe.get('blender'), 'gpu': est.get('gpu'), 'pod_id': est.get('pod_id'), 'gasto_usd': gasto,
                        'blend': f'blend/{ver}/{blend_src.name}', 'hoja': f'renders/{ver}/{hoja_src.name}' if hoja_src.is_file() else None,
                        'ficha': f'ficha_esqueleto/{ver}/ficha_esqueleto.json', 'construido': now_iso(),
                        'siguiente': 'Ricardo aprueba la HOJA → approval_ref + estado aprobado (el motor solo carga aprobados)'})
    job['estado'] = 'listo' if hoja_src.is_file() else 'parcial'; job['resultado'] = {'dir': str(d), 'version': ver, 'meta_estado': meta['estado'], 'gasto_usd': gasto,
                                                 'blend': str(bdir / blend_src.name), 'hoja': str(rdir / hoja_src.name)}
    _ts['publicar_213'] = round(__import__('time').time() - t_pub, 1)
    _ts['renders_dentro_de_blender'] = informe.get('tiempo_render_s')
    _log(job, f'publicado {ver} en {d}')
    return job


def _coincide_pieza(base, claves, corto, escenario=None):
    """Emparejado UNIVERSAL de una instancia con la pieza pedida: id exacto o slug completo `amb-<escenario>-<id>`.
    Nunca un sufijo suelto (…-madera-rio no es rio). Misma regla que datos_via_b.coincide_en_escena."""
    base = (base or '').split('#')[0]
    claves =[REDACTED]
    if any(base == k or base.startswith(k + '-') for k in claves):
        return True
    if escenario and base.startswith(f'amb-{escenario}-'):
        slug = base[len(f'amb-{escenario}-'):]
        if corto and slug == corto:
            return True
        if any(slug == k or (k.startswith('obj-') and slug == k[4:]) for k in claves):
            return True
    return False

# ------------------------------------------------------------------ recetas Argon (vía B + Argon, como Piquito / habitación)
def _recetas_sueltas(job, cfg, bib, pedido):
    """Pedido {'grupo', 'objetos': [{gdc, objeto_id, nombre, caja_m, apoyo, fuente_caja}]} → fichas (sello+ADN+caja con fuente) →
    corpus gratis → Argon (puerta argon_fabrica) → revisor → objetos/<gdc>/receta/vNNN/recetas_validas.json (solo APTAS)."""
    import argon_fabrica as AF
    C = cfg['constructores']; vb = Path(C['raiz']) / 'escenario' / 'via_b'; canal = job['payload']['canal']
    S = ROOT / 'tmp' / f"sueltas_{job['id']}"; S.mkdir(parents=True, exist_ok=True); (S / 'pedido.json').write_text(json.dumps(pedido, ensure_ascii=False, indent=1))
    r = subprocess.run(['/usr/bin/python3', str(vb / 'recetas_sueltas.py'), 'preparar', '--pedido', str(S / 'pedido.json'), '--salida', str(S),
                        '--adn-dir', str(Path(C['cubo_fijo_raiz']) / 'adn'), '--cubo', str(C['cubo_fijo_raiz'])], capture_output=True, text=True, timeout=1500)
    _log(job, f'vía B sueltas preparar: rc={r.returncode} {r.stdout[-300:]} {r.stderr[-300:] if r.returncode else ""}'); _guardar(job, cfg)
    if r.returncode != 0: return
    G = json.loads((S / 'grupos.json').read_text(encoding='utf-8')); job['argon'] = []
    for g in G['grupos']:
        try:
            res = AF.llamar(cfg, (S / 'prompts' / f'PROMPT_RECETA_{g}.md').read_text(encoding='utf-8'), f'receta-sueltos-{g}', S / 'respuestas' / f'{g}.json',
                            (cfg.get('argon') or {}).get('autorizacion', ''), log=lambda m: (_log(job, m), _guardar(job, cfg)))
        except AF.ArgonParado as e:
            _log(job, f'Argon NO llamado/parado: {e}'); job['argon'].append({'grupo': g, 'parado': str(e)}); break
        job['argon'].append({'grupo': g, 'ledger_n': res.get('ledger_n'), 'ok': res.get('ok'), 'usd': res.get('costo_real_usd'), 'error': res.get('error')})
    r = subprocess.run(['/usr/bin/python3', str(vb / 'recetas_sueltas.py'), 'revisar', '--salida', str(S)], capture_output=True, text=True, timeout=600)
    _log(job, f'revisor recetas sueltas: rc={r.returncode} {r.stdout[-300:]}')
    rv = S / 'recetas_validas.json'; V = json.loads(rv.read_text(encoding='utf-8')) if rv.is_file() else {}
    job['recetas_sueltas'] = {'aptas': list(V), 'revision': str(S / 'REVISION.json')}
    for o in pedido['objetos']:
        if o['objeto_id'] not in V: continue
        pid = o.get('id') or o.get('pieza_id') or o.get('gdc')
        if not pid: continue
        d = bib.pieza_dir(canal, 'objetos', pid); ver = _version(d); rd = d / 'receta' / ver; rd.mkdir(parents=True, exist_ok=True)
        (rd / 'recetas_validas.json').write_text(json.dumps({o['objeto_id']: V[o['objeto_id']]}, ensure_ascii=False, indent=1), encoding='utf-8')
        for x in ('REVISION.json', 'grupos.json', 'pedido.json'): shutil.copy2(S / x, rd / x)
        shutil.copytree(S / 'respuestas', rd / 'respuestas', dirs_exist_ok=True); shutil.copytree(S / 'prompts', rd / 'prompts', dirs_exist_ok=True)
        bib.registrar_version(canal, 'objetos', o['gdc'], 'receta', rd / 'recetas_validas.json', {'version': ver, 'origen': 'Argon vía B sueltos (servicio)', 'fuente_caja': o.get('fuente_caja')})


def _recetas_argon(job, cfg, bib, d, ver, datos, eid):
    """Objetos FALTA del escenario → fichas + corpus gratis → Argon (puerta argon_fabrica: ledger antes, topes, 20 s, sin reintento,
    429 = pausa) → revisor_recetas → receta/vNNN/recetas_validas.json. Devuelve la ruta o None."""
    import argon_fabrica as AF
    C = cfg['constructores']; vb = Path(C['raiz']) / 'escenario' / 'via_b'; S = d / 'receta' / ver; S.mkdir(parents=True, exist_ok=True)
    r = subprocess.run(['/usr/bin/python3', str(vb / 'recetas_argon.py'), 'preparar', '--datos', str(datos), '--escenario', eid, '--salida', str(S),
                        '--adn-dir', str(Path(C['cubo_fijo_raiz']) / 'adn')],
                       capture_output=True, text=True, timeout=1500)
    _log(job, f'vía B preparar: rc={r.returncode} {r.stdout[-300:]}'); _guardar(job, cfg)
    if r.returncode != 0: job['error_via_b'] = r.stderr[-600:]; return None
    G = json.loads((S / 'grupos.json').read_text(encoding='utf-8')); gasto = 0.0; job['argon'] = []
    for g in G['grupos']:
        out = S / 'respuestas' / f'{g}.json'
        if out.is_file(): continue
        try:
            res = AF.llamar(cfg, (S / 'prompts' / f'PROMPT_RECETA_{g}.md').read_text(encoding='utf-8'), f'receta-{eid}-{g}', out,
                            (cfg.get('argon') or {}).get('autorizacion', ''), log=lambda m: (_log(job, m), _guardar(job, cfg)))
        except AF.ArgonParado as e:
            _log(job, f'Argon NO llamado/parado: {e}'); job['argon'].append({'grupo': g, 'parado': str(e)}); break
        c = res.get('costo_real_usd'); gasto += c if c is not None else res.get('reserva_usd') or 0
        job['argon'].append({'grupo': g, 'ledger_n': res.get('ledger_n'), 'ok': res.get('ok'), 'usd': c, 'error': res.get('error')})
    job['gasto_argon_usd'] = round(gasto, 6)
    r = subprocess.run(['/usr/bin/python3', str(vb / 'recetas_argon.py'), 'revisar', '--salida', str(S)], capture_output=True, text=True, timeout=600)
    _log(job, f'revisor recetas: rc={r.returncode} {r.stdout[-300:]}')
    rv = S / 'recetas_validas.json'
    if rv.is_file() and json.loads(rv.read_text(encoding='utf-8')):
        bib.registrar_version(job['payload']['canal'], 'escenarios', eid, 'receta', rv, {'version': ver, 'gasto_usd': round(gasto, 6), 'origen': 'Argon vía B (servicio)'})
        return rv
    return None


# ------------------------------------------------------------------ escenario (código listo; primera prueba GPU pendiente)
def _escenario(job, cfg, bib):
    C = cfg['constructores']; p = job['payload']; canal, eid = p['canal'], p['id']; tipo = 'escenarios'
    d = bib.pieza_dir(canal, tipo, eid); ver = _version(d)
    inv = Path(p.get('inventario_parcial_path') or p.get('inventario_path') or '')
    e4a2 = Path(p.get('e4a2_path') or (Path(p.get('carpeta') or '/nonexist') / 'ramas' / '4a2_entrada_blender.json'))
    if not inv.is_file() or not e4a2.is_file():
        job['estado'] = 'stop_falta_dato'; _log(job, f'falta inventario 4a1 ({inv}) o 4a2 ({e4a2})'); return job
    datos = d / 'datos' / ver; datos.mkdir(parents=True, exist_ok=True)
    cod = Path(C['raiz']) / 'escenario' / 'codigo'
    def correr(cmd, t=600):
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=t); _log(job, f'{Path(cmd[1]).name}: rc={r.returncode} {r.stdout[-200:]}')
        if r.returncode != 0: job['estado'] = 'error_construccion'; job['error'] = r.stderr[-800:]
        return r.returncode == 0
    if not correr(['/usr/bin/python3', str(cod / 'plan_escenario.py'), '--escenario', eid, '--inv', str(inv), '--e4a2', str(e4a2), '--datos', str(datos)]): return job
    if not correr(['/usr/bin/python3', str(cod / 'ensamblar.py'), '--datos', str(datos), '--escenario', eid, 'star']): return job
    modo = 'star'
    rp = Path(p.get('recetas_path') or '')
    if not rp.is_file():   # recetas vía B ya aprobadas y publicadas en la biblioteca (receta/vNNN/recetas_validas.json, la más nueva)
        cands = [c for c in sorted((d / 'receta').glob('v*/recetas_validas.json')) if json.loads(c.read_text(encoding='utf-8') or '{}')]   # solo si trae recetas
        if cands: rp = cands[-1]
    if not rp.is_file() and cfg.get('argon_enabled') and not p.get('sin_argon'):
        rp = _recetas_argon(job, cfg, bib, d, ver, datos, eid) or rp
    if rp.is_file():
        shutil.copy2(rp, datos / 'recetas_validas.json'); modo = 'star_recetas'; _log(job, f'recetas vía B aprobadas: {rp} → modo star_recetas')
        if not correr(['/usr/bin/python3', str(cod / 'ensamblar.py'), '--datos', str(datos), '--escenario', eid, 'star_recetas']): return job
    tgz_cons = ROOT / 'tmp' / f"constructores_{job['id']}.tgz"; tgz_cons.parent.mkdir(exist_ok=True)
    with tarfile.open(tgz_cons, 'w:gz') as t: t.add(C['raiz'], arcname='constructores', filter=lambda ti: None if '__pycache__' in ti.name else ti)
    tgz_d = ROOT / 'tmp' / f"datos_{job['id']}.tgz"
    with tarfile.open(tgz_d, 'w:gz') as t: t.add(datos, arcname='datos')
    rec = d / 'recibos' / ver; rec.mkdir(parents=True, exist_ok=True)
    _meta(bib, canal, tipo, eid, estado='construyendo'); job['estado'] = 'construyendo'; _guardar(job, cfg)
    est = Pod(cfg).correr(etiqueta=f'esc-{eid}', autorizacion=cfg['gpu'].get('autorizacion'),
                          subir=[(tgz_cons, '/root/job/constructores.tgz'), (tgz_d, '/root/job/datos.tgz')],
                          comando=f'cd /root/job && tar xzf constructores.tgz && tar xzf datos.tgz && bash constructores/pod/run_escenario_pod.sh {eid} {modo}',
                          traer='/root/out.tgz', destino=rec / 'out.tgz', log=lambda m: (_log(job, 'gpu: ' + m), _guardar(job, cfg)),
                     setup_cmd='cd /root/job && tar xzf constructores.tgz && bash constructores/pod/setup_pod_rapido.sh')
    (rec / 'gpu_estado.json').write_text(json.dumps(est, ensure_ascii=False, indent=1), encoding='utf-8')
    gasto = max(est.get('costo_real_usd') or 0, est.get('costo_tiempo_usd') or 0); job['gasto_usd'] = round(gasto, 6); job['gpu'] = est
    if not (rec / 'out.tgz').is_file(): job['estado'] = 'error_gpu'; return job
    with tarfile.open(rec / 'out.tgz') as t: t.extractall(rec)
    out = rec / 'out'; blend = out / f'{eid}_{modo}.blend'
    if not blend.is_file(): job['estado'] = 'error_construccion'; return job
    bdir = d / 'blend' / ver; rdir = d / 'renders' / ver; bdir.mkdir(parents=True, exist_ok=True); rdir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(blend, bdir / blend.name)
    for f in list((out / 'renders').glob('*.png')) + list(out.glob('HOJA_*.png')): shutil.copy2(f, rdir / f.name)
    bib.registrar_version(canal, tipo, eid, 'blend', bdir / blend.name, {'version': ver, 'gasto_usd': gasto})
    m = bib.leer_meta(canal, tipo, eid)
    vfile = datos / f'validacion_{modo}.json'
    n_falta = 0
    try:
        ensj = json.loads((datos / f'ensamblado_{modo}.json').read_text(encoding='utf-8'))
        n_falta = sum(1 for o in ensj['objetos'] if any(q.get('falta') for q in o['piezas']))
    except Exception: pass
    job['objetos_falta'] = n_falta
    _meta(bib, canal, tipo, eid, estado='hoja_lista' if n_falta == 0 else 'hoja_lista_con_faltas', objetos_falta=n_falta, modo=modo, gasto_usd_acum=round((m.get('gasto_usd_acum') or 0) + gasto, 6),
          v2_3d={'version': ver, 'blend': f'blend/{ver}/{blend.name}', 'gpu': est.get('gpu'), 'gasto_usd': gasto, 'construido': now_iso()})
    job['estado'] = 'listo'; job['resultado'] = {'dir': str(d), 'version': ver, 'gasto_usd': gasto}
    return job
