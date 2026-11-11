# -*- coding: utf-8 -*-
"""[fábricas v2 · 10-nov-2026, OK Ricardo t1004u] Puerta ÚNICA de Argon (pagado) para el servicio de fábricas.
Reglas (no se saltan): ledger ANTES de cada llamada (/opt/myia-fabricas/ledger_argon.json, peor caso reservado);
tope por llamada (config argon.tope_por_llamada_usd, ≤ US$0,75), tope de la noche y tope duro total (= lo que queda de la bolsa
de US$50); 20 s entre llamadas (candado de archivo, entre procesos); SIN reintento automático; un 429 PAUSA Argon
(archivo argon_pausa_429) hasta que alguien lo quite. La credencial NO se lee aquí: el cliente existente del motor
(myia_argon._cliente) autentica con la ruta que ya tiene configurada el motor v9 (config/argon_transporte.json existing_file).
La llamada corre en el venv con google-genai (subproceso argon_llamar.py)."""
from __future__ import annotations
import fcntl, json, math, subprocess, time
from datetime import datetime
from pathlib import Path

ROOT = Path('/opt/myia-fabricas')
APP = Path(__file__).resolve().parent

class ArgonParado(RuntimeError):
    pass

def ahora(): return datetime.now().astimezone().isoformat(timespec='seconds')

def _cfg(cfg):
    a = dict(cfg.get('argon') or {})
    a.setdefault('ledger', str(ROOT / 'ledger_argon.json')); a.setdefault('pausa', str(ROOT / 'argon_pausa_429'))
    a.setdefault('candado', str(ROOT / 'argon.lock')); a.setdefault('separacion_s', 20); a.setdefault('tope_por_llamada_usd', 0.75)
    a.setdefault('modelo', 'gemini-4-argon'); a.setdefault('precio_usd_por_millon', [2.0, 10.0]); a.setdefault('chars_por_token', 3)
    a.setdefault('max_out', 32768); a.setdefault('python', '/opt/myia-argon-blender/venv/bin/python')
    return a

def _ledger(a):
    p = Path(a['ledger'])
    return json.loads(p.read_text(encoding='utf-8')) if p.is_file() else {'schema': 'ledger_argon_fabricas/v1', 'entradas': []}

def _guardar_ledger(a, d):
    p = Path(a['ledger']); t = p.with_suffix('.tmp'); t.write_text(json.dumps(d, ensure_ascii=False, indent=1), encoding='utf-8'); t.replace(p)

def gastado(a, desde=None):
    """Gasto contado (real si se liquidó; peor caso si quedó abierta o dudosa)."""
    s = 0.0
    for e in _ledger(a)['entradas']:
        if desde and e.get('inicio', '') < desde: continue
        if e.get('estado') == 'no_cobrado_429' or e.get('estado') == 'rechazada_antes': continue
        s += float(e['costo_real_usd'] if e.get('costo_real_usd') is not None else e.get('reserva_usd') or 0)
    return round(s, 6)

def peor_caso(a, caracteres, max_out):
    pin, pout = a['precio_usd_por_millon']
    return round((math.ceil(caracteres / a['chars_por_token']) * pin + max_out * pout) / 1e6, 6)

def llamar(cfg, prompt: str, etiqueta: str, salida: Path, autorizacion: str, max_out: int | None = None, log=print) -> dict:
    a = _cfg(cfg)
    if not cfg.get('argon_enabled'): raise ArgonParado('Argon APAGADO en config (argon_enabled=false)')
    if Path(a['pausa']).exists(): raise ArgonParado(f'Argon en PAUSA por 429 ({a["pausa"]}); no se llama')
    max_out = int(max_out or a['max_out'])
    reserva = peor_caso(a, len(prompt), max_out)
    tope_llamada = min(float(a['tope_por_llamada_usd']), 0.75)
    if reserva > tope_llamada: raise ArgonParado(f'peor caso US${reserva} > tope por llamada US${tope_llamada}')
    total = gastado(a); noche = gastado(a, a.get('noche_desde'))
    tope_total = float(cfg.get('tope_usd_argon') or 0); tope_noche = float(a.get('tope_noche_usd') or 0)
    lote_desde = a.get('lote_desde') or None
    tope_lote = float(a.get('tope_lote_usd') or 0)
    lote = gastado(a, lote_desde) if lote_desde and tope_lote else 0.0
    # Lote abierto: tope propio contado desde cero a partir de lote_desde. El tope del lote anterior queda cerrado y no se reabre.
    if lote_desde and tope_lote:
        if lote + reserva > tope_lote + 1e-9:
            raise ArgonParado(f'tope del lote Argon: gastado {lote} + reserva {reserva} > {tope_lote}')
    else:
        if tope_total and total + reserva > tope_total: raise ArgonParado(f'tope total Argon: gastado {total} + {reserva} > {tope_total}')
        if tope_noche and noche + reserva > tope_noche: raise ArgonParado(f'tope de la noche: {noche} + {reserva} > {tope_noche}')
    salida = Path(salida); salida.parent.mkdir(parents=True, exist_ok=True)
    ch = subprocess.run([a['python'], str(APP / 'argon_llamar.py'), '--chequear'], capture_output=True, text=True, timeout=120)
    if ch.returncode != 0: raise ArgonParado(f'cliente Argon no disponible (sin costo, sin ledger): {(ch.stdout or ch.stderr)[-300:]}')
    pf = salida.with_suffix('.prompt.md'); pf.write_text(prompt, encoding='utf-8')
    lk = open(a['candado'], 'a+'); fcntl.flock(lk, fcntl.LOCK_EX)
    try:
        d = _ledger(a)
        ult = max([e.get('fin_epoch') or e.get('inicio_epoch') or 0 for e in d['entradas']] or [0])
        espera = a['separacion_s'] - (time.time() - ult)
        if espera > 0: log(f'argon: espera {espera:.0f} s (separación {a["separacion_s"]} s)'); time.sleep(espera)
        n = len(d['entradas']) + 1
        e = {'n': n, 'etiqueta': etiqueta, 'estado': 'en_curso', 'inicio': ahora(), 'inicio_epoch': time.time(), 'modelo': a['modelo'],
             'caracteres_prompt': len(prompt), 'max_out': max_out, 'reserva_usd': reserva, 'autorizacion': autorizacion,
             'prompt': str(pf), 'salida': str(salida),
             'gastado_antes_usd': lote if (lote_desde and tope_lote) else total,
             'gastado_historico_usd': total,
             'tope_total_usd': tope_total, 'tope_noche_usd': tope_noche,
             'lote_desde': lote_desde, 'tope_lote_usd': tope_lote or None,
             'reintento': False}
        d['entradas'].append(e); _guardar_ledger(a, d)          # LEDGER ANTES DE LLAMAR
        log(f'argon: ledger #{n} abierto ANTES (reserva peor caso US${reserva}) → {etiqueta}')
        r = subprocess.run([a['python'], str(APP / 'argon_llamar.py'), '--prompt', str(pf), '--salida', str(salida), '--modelo', a['modelo'],
                            '--max-out', str(max_out), '--nivel', str(a.get('nivel', 'HIGH'))], capture_output=True, text=True, timeout=2000)
        res = json.loads((r.stdout.strip().splitlines() or ['{}'])[-1]) if r.stdout.strip() else {}
        res.setdefault('rc', r.returncode)
        if r.returncode != 0 and not res.get('error'): res['error'] = r.stderr[-600:]
        tin, tout = res.get('tokens_entrada'), res.get('tokens_salida')
        pin, pout = a['precio_usd_por_millon']
        real = round((tin * pin + tout * pout) / 1e6, 6) if tin is not None and tout is not None else None
        d = _ledger(a); e = d['entradas'][n - 1]
        if res.get('codigo') == 429:
            e.update(estado='no_cobrado_429', costo_real_usd=0.0); Path(a['pausa']).write_text(f'429 en ledger #{n} {ahora()}\n')
        elif res.get('ok'):
            e.update(estado='ok', costo_real_usd=real)
        else:
            e.update(estado='error_posible_cobro', costo_real_usd=real)   # sin uso → cuenta la reserva (peor caso)
        e.update(fin=ahora(), fin_epoch=time.time(), tokens_entrada=tin, tokens_salida=tout, error=(res.get('error') or None) and str(res['error'])[:400],
                 finish=res.get('finish'))
        _guardar_ledger(a, d); res['ledger_n'] = n; res['costo_real_usd'] = real; res['reserva_usd'] = reserva
        log(f"argon: #{n} {e['estado']} US${real if real is not None else reserva} tokens {tin}/{tout}")
        if res.get('codigo') == 429: raise ArgonParado('429: Argon PAUSADO (sin reintento)')
        return res
    finally:
        fcntl.flock(lk, fcntl.LOCK_UN); lk.close()
