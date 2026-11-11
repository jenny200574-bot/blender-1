# -*- coding: utf-8 -*-
"""[t1066u, 10-nov-2026 · OK Ricardo: «si envia a argon hacer que escoje el debe aplicar tomas angulos y movimientos de camara para
contar la historia correctamete»] Storyboard DESPUÉS del 3D: UNA llamada a Argon por escena.
Entrada: corrida/sb3d/paquete.json (medidas reales, grafo de soporte, eje 180°, niveles N0–N3, 4–6 candidatas por viñeta) +
hojas de contacto Workbench + planta + guion/SB de la corrida + catálogo de cámara de Star (motor/sb3d/catalogo).
Salida: corrida/sb3d/sb_argon.json (JSON estricto, largo acotado) que lee `sb3d.py --modo aplicar`.
Reglas: puerta de fábricas (/opt/myia-fabricas/app/argon_fabrica.py): ledger ANTES, tope ≤ US$0,75 por llamada, tope del lote,
20 s entre llamadas (candado), SIN reintento, 429 = pausa. La credencial NO se abre aquí (argon_llamar_imagenes.py usa el cliente
existente por RUTA). Universal: nada de canal/capítulo/escena/personaje fijo en el código.
Uso: python3 sb3d_argon.py --corrida DIR --autorizacion TXT [--max_out 22000] [--solo_prompt]"""
from __future__ import annotations
import argparse, fcntl, json, os, re, subprocess, sys, time
from pathlib import Path
sys.path.insert(0, '/opt/myia-fabricas/app')
import argon_fabrica as AF

AQUI = Path(__file__).resolve().parent
CFG_FAB = Path('/opt/myia-fabricas/config/config.json')
TOK_IMAGEN = 2600          # reserva por imagen (peor caso; Argon cobra las imágenes como tokens de entrada)

TOK_VIDEO_S = 300         # reserva por segundo de video (Argon muestrea ~1 cuadro/s)
def tokens_medios(paths):
    t = 0
    for p in paths:
        if p.lower().endswith('.mp4'):
            try: d = float(json.loads((Path(p).parent / 'revision_argon.json').read_text()).get('cuadros', 60)) / max(0.1, float(json.loads((Path(p).parent / 'revision_argon.json').read_text()).get('fps_video', 1)))
            except Exception: d = 120.0
            t += int(TOK_VIDEO_S * d) + 500
        else: t += TOK_IMAGEN
    return t

def _corto(x, n):
    s = x if isinstance(x, str) else json.dumps(x, ensure_ascii=False)
    return s if len(s) <= n else s[:n] + '…'

FORMA = """{"vinetas":[{"id":"v1","objetivo":"<id de personaje protagonista>","plano":"PG|PE|PA|PM|PMC|PP|PPP|GPG",
"angulo":"NORM|PIC|CPIC|CEN|NAD|DUTCH","lente_mm":24,
"camara":{"pos":[x,y,z],"mira":"<id de personaje> o [x,y,z]","punto":"ojos|pecho|centro|pies"},"seguir_sujeto":false,
"movimiento":{"tipo":"STATIC|LOCK|DOLLYIN|DOLLYOUT|PAN|TILT|TRACK|ORBIT|CRANE|PEDESTAL|ZOOMIN|ZOOMOUT|STEADICAM|HANDHELD|WHIPPAN|CRASHZOOM",
"intensidad":0.6,"velocidad":"lenta|media|rapida","direccion":"izquierda|derecha|arriba|abajo|adentro|afuera|null","espera_s":0},
"nunca_ocultar":["<ids del censo>"],"motivo":"<=160 caracteres"}],"notas":"<=300 caracteres"}"""

def _catalogo():
    return "\n".join(f"### {f.name}\n{_corto(f.read_text(encoding='utf-8'), 9000)}" for f in sorted((AQUI / 'catalogo').glob('*')))

def _escena_texto(P, E):
    censo = {}
    for e, d in P['censo'].items():
        if d['nivel'] == 'N3': continue
        x = {k: d[k] for k in ('nivel', 'tipo', 'caja_min', 'caja_max', 'portador', 'por_vineta') if k in d}
        if d.get('por_que'): x['por_que'] = d['por_que'][:1]
        censo[e] = x
    vin = [{k: v.get(k) for k in ('id', 't', 'cuadros', 'objetivo', 'en_cuadro', 'objetos_sb', 'intencion', 'accion', 'dialogo', 'emocion', 'ritmo_s', 'sb_original', 'eje_180')}
           for v in P['vinetas']]
    esc = {"interior_m": P.get('interior'), "aspecto": P.get('aspecto'), "fps": P.get('fps'), "cuadros": P.get('N'), "sensor_mm": P.get('sensor_mm'),
           "censo": censo, "grafo_soporte": P.get('grafo_soporte'), "nunca_ocultar_N0": P['niveles'].get('N0'), "muros_N2": P['niveles'].get('N2')}
    guion = {"acciones": E.get('acciones_01'), "segmentos": E.get('segmentos_01'), "hechos": E.get('hechos')}
    return esc, vin, guion

REGLAS = """NIVELES: N0 = historia (personajes, piso, mueble que sostiene/toca a alguien, props del guion): NUNCA se ocultan; si un N0
tapa, la cámara se MUEVE (otra posición/altura), nunca se esconde nada. N1 = obstáculo: la cámara lo rodea. N2 = muros exteriores:
solo se recortan si la cámara queda FUERA del cuarto. N3 = decoración que nadie toca ni nombra: lo único ocultable.
VALIDACIÓN 3D del motor (bloquea): la cámara no puede quedar dentro de muros/muebles/personajes en NINGÚN cuadro del movimiento
(holgura 8 cm); el protagonista ('objetivo') debe verse ≥90 % en promedio (≥60 % en cada cuadro) y su cara/ojos dentro del cuadro;
ningún N0 oculto. Avisa (no bloquea): regla 180°, regla 30°, movimiento que casi no se nota.
COORDENADAS: metros, z hacia arriba; la PLANTA del video tiene x→derecha, y↑arriba y marcas rojas (x,y) en el piso; la VISTA AMPLIA
mira desde el frente (y pequeña) hacia el fondo. Usa las alturas REALES del censo: un PM queda a ~1–1,6 m del
sujeto con lente 35; un PP a ~0,6–1 m con 50; un PG a 2,5–4 m con 18–24. 'seguir_sujeto': la cámara acompaña si el sujeto camina."""

def construir_prompt(C: Path, fase: str = 'principal', fallas: list | None = None) -> tuple[str, list[str]]:
    S = C / 'sb3d'; P = json.loads((S / 'paquete.json').read_text())
    E = json.loads((C / 'entrada_motor.json').read_text())
    esc, vin, guion = _escena_texto(P, E); ids = [v['id'] for v in P['vinetas']]
    if fase == 'principal':
        med = [str(S / 'revision_argon.mp4')] if (S / 'revision_argon.mp4').is_file() else []
        prompt = f"""Eres el DIRECTOR DE FOTOGRAFÍA de esta escena. La escena YA está armada y ANIMADA en 3D. Te mando un
VIDEO DE REVISIÓN de toda la escena (izquierda: PLANTA cenital; derecha: VISTA AMPLIA; nombre de cada personaje sobre su cabeza;
arriba: cuadro, segundo y viñeta) y las medidas REALES de Blender. TÚ ESCOGES LIBREMENTE, por cada viñeta, dónde va la cámara
(posición xyz), a qué mira, el plano, el ángulo, el lente y el MOVIMIENTO de cámara (tipo del DSL, cantidad=intensidad 0–1 y
velocidad), para CONTAR LA HISTORIA CORRECTAMENTE: qué debe entender el niño, quién habla, qué se revela, qué emoción. Mira el
video: dónde está cada uno en cada viñeta, quién tapa a quién, qué muebles estorban.

{REGLAS}

CATÁLOGO DE CÁMARA (Star):
{_catalogo()}

GUION (cadena):
{_corto(guion, 12000)}

ESCENA 3D (medidas reales; posiciones por viñeta en censo.<personaje>.por_vineta):
{_corto(esc, 30000)}

VIÑETAS (cuadros [inicio, fin] a {P.get('fps')} fps; SB original solo como referencia, NO es obligatorio):
{_corto(vin, 30000)}

RESPONDE SOLO JSON (sin texto fuera), con TODAS las viñetas {ids}, exactamente esta forma:
{FORMA}
No agregues campos. 'motivo' ≤160 caracteres."""
    else:
        med = [str(S / 'planta_rev.jpg')] if (S / 'planta_rev.jpg').is_file() else []
        prev = json.loads((S / 'sb_argon.json').read_text()).get('decision', {}) if (S / 'sb_argon.json').is_file() else {}
        tuyas = [x for x in prev.get('vinetas', []) if x.get('id') in {f['vineta'] for f in (fallas or [])}]
        vf = [v for v in vin if v['id'] in {f['vineta'] for f in (fallas or [])}]
        prompt = f"""Eres el DIRECTOR DE FOTOGRAFÍA. El motor aplicó en 3D tus cámaras y estas viñetas NO pasaron la validación. Corrige SOLO
estas viñetas: mueve la cámara (posición/altura/distancia/lente/movimiento) para que pase, sin perder la intención narrativa.
Nunca se oculta un N0: si algo de historia tapa, cambia la posición. Imagen: PLANTA del cuarto (x→derecha, y↑arriba, marcas (x,y)).

{REGLAS}

TU DECISIÓN ANTERIOR (estas viñetas):
{_corto(tuyas, 8000)}

FALLAS MEDIDAS EN 3D (por viñeta; vis = fracción visible del protagonista; pos = tu cámara):
{_corto(fallas, 6000)}

VIÑETAS (SB + intención):
{_corto(vf, 8000)}

ESCENA 3D (medidas reales):
{_corto({k: esc[k] for k in ('interior_m', 'censo', 'nunca_ocultar_N0')}, 16000)}

RESPONDE SOLO JSON con SOLO las viñetas {[f['vineta'] for f in (fallas or [])]}, misma forma:
{FORMA}"""
    return prompt, [m for m in med if os.path.isfile(m)]

def validar(txt: str, ids: list[str], cands: dict) -> tuple[dict | None, list]:
    av = []
    t = txt.strip()
    t = re.sub(r'^```(json)?', '', t).rstrip('`').strip()
    try: d = json.loads(t)
    except Exception as e: return None, [f'JSON inválido: {e}']
    if isinstance(d, list): d = {"vinetas": d}
    vs = [x for x in d.get('vinetas', []) if isinstance(x, dict) and x.get('id') in ids]
    for x in vs:
        if not isinstance((x.get('camara') or {}).get('pos'), list): av.append(f"{x['id']}: sin camara.pos")
        if isinstance(x.get('motivo'), str) and len(x['motivo']) > 240: x['motivo'] = x['motivo'][:240]
    falt = [i for i in ids if i not in {x['id'] for x in vs}]
    if falt: av.append(f'faltan viñetas: {falt}')
    d['vinetas'] = vs
    return d, av

def llamar_con_imagenes(cfg, prompt, imgs, etiqueta, salida: Path, autorizacion, max_out, log=print, nivel=None):
    """Misma puerta que argon_fabrica.llamar (ledger antes, topes, separación, sin reintento, 429=pausa) + imágenes en la reserva."""
    a = AF._cfg(cfg)
    if not cfg.get('argon_enabled'): raise AF.ArgonParado('Argon APAGADO en config (argon_enabled=false)')
    if Path(a['pausa']).exists(): raise AF.ArgonParado(f'Argon en PAUSA por 429 ({a["pausa"]}); no se llama')
    reserva = AF.peor_caso(a, len(prompt) + tokens_medios(imgs) * a['chars_por_token'], max_out)
    tope_llamada = min(float(a['tope_por_llamada_usd']), 0.75)
    if reserva > tope_llamada: raise AF.ArgonParado(f'peor caso US${reserva} > tope por llamada US${tope_llamada}')
    total = AF.gastado(a); lote_desde = a.get('lote_desde') or None; tope_lote = float(a.get('tope_lote_usd') or 0)
    lote = AF.gastado(a, lote_desde) if lote_desde and tope_lote else 0.0
    if lote_desde and tope_lote:
        if lote + reserva > tope_lote + 1e-9: raise AF.ArgonParado(f'tope del lote Argon: gastado {lote} + reserva {reserva} > {tope_lote}')
    else:
        tt = float(cfg.get('tope_usd_argon') or 0)
        if tt and total + reserva > tt: raise AF.ArgonParado(f'tope total Argon: {total} + {reserva} > {tt}')
    py = a['python']; scr = str(AQUI / 'argon_llamar_imagenes.py')
    ch = subprocess.run([py, scr, '--chequear'], capture_output=True, text=True, timeout=120)
    if ch.returncode != 0: raise AF.ArgonParado(f'cliente Argon no disponible (sin costo, sin ledger): {(ch.stdout or ch.stderr)[-300:]}')
    pf = salida.with_suffix('.prompt.md'); pf.write_text(prompt, encoding='utf-8')
    lk = open(a['candado'], 'a+'); fcntl.flock(lk, fcntl.LOCK_EX)
    try:
        d = AF._ledger(a)
        ult = max([e.get('fin_epoch') or e.get('inicio_epoch') or 0 for e in d['entradas']] or [0])
        espera = a['separacion_s'] - (time.time() - ult)
        if espera > 0: log(f'argon: espera {espera:.0f} s (separación)'); time.sleep(espera)
        n = len(d['entradas']) + 1
        e = {'n': n, 'etiqueta': etiqueta, 'estado': 'en_curso', 'inicio': AF.ahora(), 'inicio_epoch': time.time(), 'modelo': a['modelo'],
             'caracteres_prompt': len(prompt), 'imagenes': [os.path.basename(i) for i in imgs], 'max_out': max_out, 'reserva_usd': reserva,
             'autorizacion': autorizacion, 'prompt': str(pf), 'salida': str(salida), 'gastado_antes_usd': lote if (lote_desde and tope_lote) else total,
             'gastado_historico_usd': total, 'lote_desde': lote_desde, 'tope_lote_usd': tope_lote or None, 'reintento': False}
        d['entradas'].append(e); AF._guardar_ledger(a, d)
        log(f'argon: ledger #{n} abierto ANTES (reserva peor caso US${reserva}) → {etiqueta}')
        r = subprocess.run([py, scr, '--prompt', str(pf), '--salida', str(salida), '--imagenes', ','.join(imgs), '--modelo', a['modelo'],
                            '--max-out', str(max_out), '--nivel', str(nivel or a.get('nivel', 'HIGH'))], capture_output=True, text=True, timeout=2000)
        res = json.loads((r.stdout.strip().splitlines() or ['{}'])[-1]) if r.stdout.strip() else {}
        res.setdefault('rc', r.returncode)
        if r.returncode != 0 and not res.get('error'): res['error'] = r.stderr[-600:]
        tin, tout = res.get('tokens_entrada'), res.get('tokens_salida'); pin, pout = a['precio_usd_por_millon']
        real = round((tin * pin + tout * pout) / 1e6, 6) if tin is not None and tout is not None else None
        d = AF._ledger(a); e = d['entradas'][n - 1]
        if res.get('codigo') == 429: e.update(estado='no_cobrado_429', costo_real_usd=0.0); Path(a['pausa']).write_text(f'429 en ledger #{n} {AF.ahora()}\n')
        elif res.get('ok'): e.update(estado='ok', costo_real_usd=real)
        else: e.update(estado='error_posible_cobro', costo_real_usd=real)
        e.update(fin=AF.ahora(), fin_epoch=time.time(), tokens_entrada=tin, tokens_salida=tout, error=(res.get('error') or None) and str(res['error'])[:400], finish=res.get('finish'))
        AF._guardar_ledger(a, d); res.update(ledger_n=n, costo_real_usd=real, reserva_usd=reserva)
        log(f"argon: #{n} {e['estado']} US${real if real is not None else reserva} tokens {tin}/{tout}")
        if res.get('codigo') == 429: raise AF.ArgonParado('429: Argon PAUSADO (sin reintento)')
        return res
    finally:
        fcntl.flock(lk, fcntl.LOCK_UN); lk.close()

def main():
    ap = argparse.ArgumentParser(); ap.add_argument('--corrida', required=True); ap.add_argument('--autorizacion', default='')
    ap.add_argument('--fase', default='principal', choices=['principal', 'correccion']); ap.add_argument('--validacion', default='')
    ap.add_argument('--max_out', type=int, default=16000); ap.add_argument('--solo_prompt', action='store_true'); ap.add_argument('--etiqueta', default='')
    ap.add_argument('--nivel', default='LOW')   # t1093u: con HIGH el pensamiento se comió los 16000 de salida (respuesta vacía)
    a = ap.parse_args(); C = Path(a.corrida); S = C / 'sb3d'
    fallas = None
    if a.fase == 'correccion':
        VJ = json.loads(Path(a.validacion).read_text())
        fallas = [{k: r.get(k) for k in ('vineta', 'fallas', 'vis_media', 'vis_min', 'oclusores_n0', 'pos', 'objetivo', 'avisos_decision')} for r in VJ['vinetas'] if not r.get('ok')]
    prompt, med = construir_prompt(C, a.fase, fallas)
    suf = '' if a.fase == 'principal' else '_correccion'
    (S / f'argon_prompt{suf}.md').write_text(prompt, encoding='utf-8')
    P = json.loads((S / 'paquete.json').read_text())
    ids = [v['id'] for v in P['vinetas']] if a.fase == 'principal' else [f['vineta'] for f in fallas]
    cfg = json.loads(CFG_FAB.read_text()); ac = AF._cfg(cfg)
    reserva = AF.peor_caso(ac, len(prompt) + tokens_medios(med) * ac['chars_por_token'], a.max_out)
    info = {"fase": a.fase, "caracteres_prompt": len(prompt), "medios": med, "reserva_usd": reserva, "max_out": a.max_out, "vinetas_pedidas": ids}
    if a.solo_prompt: print('RESULT_SB3D_ARGON', json.dumps(dict(info, ok=True, solo_prompt=True), ensure_ascii=False)); return
    out = S / f'argon_respuesta{suf}.txt'; est = dict(info)
    try:
        res = llamar_con_imagenes(cfg, prompt, med, (a.etiqueta or f"sb3d_{a.fase}_{C.name}")[:80], out, a.autorizacion, a.max_out, nivel=a.nivel)
        est['argon'] = {k: res.get(k) for k in ('ok', 'ledger_n', 'costo_real_usd', 'reserva_usd', 'tokens_entrada', 'tokens_salida', 'finish', 'error', 'codigo')}
    except AF.ArgonParado as ex:
        est['argon'] = {"ok": False, "parado": str(ex)}
    dec = None
    if out.is_file() and est['argon'].get('ok'):
        dec, av = validar(out.read_text(encoding='utf-8'), ids, {}); est['avisos_validacion'] = av
    if dec and dec.get('vinetas'):
        json.dump({"contrato": "sb_argon_v2", "fase": a.fase, "corrida": str(C), "decision": dec, "argon": est['argon'], "avisos_validacion": est.get('avisos_validacion')},
                  open(S / f'sb_argon{suf}.json', 'w'), indent=1, ensure_ascii=False)
        est['ok'] = True; est['vinetas'] = len(dec['vinetas'])
    else:
        est['ok'] = False; est['fallback'] = 'sin decisión válida de Argon en esta fase'
    json.dump(est, open(S / f'sb3d_argon_estado{suf}.json', 'w'), indent=1, ensure_ascii=False)
    print('RESULT_SB3D_ARGON', json.dumps(est, ensure_ascii=False)[:2000])

if __name__ == '__main__': main()
