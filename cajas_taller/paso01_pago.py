#!/usr/bin/env python3
"""PISTA INMI (2026-10-29): órdenes 82/83 — piezas comunes de los caminos PAGOS de los cubos 01 (Argon dirige la escena) y
03 (Argon revisa coherencia). Por defecto NADA paga: los cubos solo cotizan. Para pagar hacen falta TODAS estas cosas:
  1. la guarda cajas/HABILITAR_PAGO_<cubo> (con el monto aprobado escrito adentro),
  2. --ok USD (<= el monto de la guarda) y --aprobado QUIEN,
  3. una cotización FRESCA (justo antes de llamar) que no pase --ok,
  4. cada pedido <= tope por llamada (paso01_datos/argon_pago.json, US$0,75; o el tope del canal si es menor),
  5. línea de ledger ANTES de cada intento (myia_argon.llamar la escribe; id propio por intento),
  6. intentos acotados (llamada_segura.intentar): 429 = no_cobrado; otros errores = posible cobro y cuentan en la bolsa,
  7. se para al llegar al monto aprobado: lo que falta queda «no llamado» y se dice por qué.
Genérico (regla 6): aquí no hay canales, capítulos ni personajes."""
import json, os, re, time
from pathlib import Path

AQUI = Path(__file__).resolve().parent
GUARDA_DIR = Path(os.environ.get('MYIA_GUARDA_DIR', str(AQUI)))
import llamada_segura as LS


def ajustes(): return json.loads((AQUI / 'paso01_datos' / 'argon_pago.json').read_text(encoding='utf-8'))


def texto(rel): return (AQUI / rel).read_text(encoding='utf-8')


def archivos_que_faltan(cubo):
    """PISTA INMI (orden 82): el «programa viejo» paraba con «le falta un archivo» sin decir cuál. Aquí se dice CUÁL."""
    c = ajustes()[cubo]
    return [rel for rel in (c['prompt'], c['esquema']) if not (AQUI / rel).is_file()]


def revisar_guarda(cubo, ok, aprobado):
    G = GUARDA_DIR / ajustes()[cubo]['guarda']
    if not G.is_file(): return f'pago del cubo {cubo} cerrado: falta cajas/{G.name} (pago no aprobado). No se llamó a nada.'
    if ok is None or not aprobado: return 'falta --ok USD y --aprobado QUIEN'
    mm = re.search(r'\d+(?:[.,]\d+)?', G.read_text(errors='replace'))
    if not mm: return f'{G.name} no trae el monto aprobado: no se llama'
    monto = float(mm.group().replace(',', '.'))
    if float(ok) > monto + 1e-9: return f'--ok {ok} pasa el monto habilitado en {G.name} ({monto})'
    return None


def tope(AR, cd):
    base = float(ajustes()['tope_por_llamada_usd'])
    try: tc = AR.tope_de_canal(cd)
    except Exception: tc = None
    return base if tc is None else min(base, float(tc))


def app():
    """App del staging (ledger, Argon, Vertex). Red SOLO a *.googleapis.com. La credencial va por RUTA (no se abre aquí)."""
    import paso00_cadena as C
    C.bloquear_red(True)
    _A, _P, _PB, AR, FP, F = C.cargar_app(C.copiar_datos(), C.ruta_credencial())
    # orden 89: con TOPE DE TIEMPO (llamadas_config.json, texto) como las demás llamadas pagas; un vencido queda «timeout» (peor caso) y se reintenta
    return {'C': C, 'AR': AR, 'FP': FP, 'F': F, 'transporte': LS.transporte_texto(AR), 'dormir': time.sleep}


def fijo(cubo, texto_fijo, esquema_txt, modelo, nivel, max_out, FP=None):
    """Parte fija (myia_fijo_prompt): texto del prompt + esquema + modelo/nivel/salida. El nombre lleva el sha: si cambia, es otro registro."""
    if FP is None: import myia_fijo_prompt as FP
    partes = {'texto': texto_fijo, 'esquema': esquema_txt, 'modelo': modelo, 'nivel': nivel, 'max_out': int(max_out), 'max_rondas': 1, 'json_out': True}
    return {'paso': f"{ajustes()[cubo]['paso_fijo']}_{FP.sha_total(partes)[:10]}", 'partes': partes, 'fragmentos': [texto_fijo]}


def _no_llamado_si_no_anotado(AR, lid, exc):
    try: est = next((r.get('estado') for r in AR._leer() if r.get('id') == lid), None)
    except Exception: est = 'desconocido'
    if est is None: raise LS.NoLlamado(f'{type(exc).__name__}: {str(exc)[:300]}') from exc


def correr(pedidos, a, X, cd, cubo):
    """pedidos = [{clave, prompt, salida, est, adjuntos, esquema, fijo, modelo, nivel, max_out, nota}] YA cotizados en fresco.
    Devuelve (resultados, bolsa). Cada resultado: {clave, ok, ledger, usd, texto, fin, intentos, error, no_llamado}."""
    AR = X['AR']; tp = tope(AR, cd); bolsa = {'gastado': 0.0}; res = []
    # Ricardo t339u: espera propia del cubo (argon_pago.json[cubo].timeout_texto_s); sin ella, la de llamadas_config.json
    _seg = (ajustes().get(cubo) or {}).get('timeout_texto_s') if isinstance(ajustes().get(cubo), dict) else None
    _cc = ajustes().get(cubo) if isinstance(ajustes().get(cubo), dict) else {}   # Fase 4: avances en streaming SOLO si el cubo lo pide
    _kw = {'pensamientos': True, 'silencio_s': _cc.get('silencio_max_s')} if _cc.get('pensamientos_stream') else {}
    transp = LS.transporte_texto(AR, segundos=float(_seg), **_kw) if _seg and X.get('transporte') is not None else X.get('transporte')
    mx = max(1, min(6, int(getattr(a, 'max_intentos', None) or ajustes()['max_intentos'])))
    for q in pedidos:
        est = float(q['est'])
        if est > tp + 1e-9: res.append({'clave': q['clave'], 'ok': False, 'no_llamado': True, 'error': f'peor caso US${est} > tope por llamada US${tp}'}); continue
        if bolsa['gastado'] + est > float(a.ok) + 1e-9:
            res.append({'clave': q['clave'], 'ok': False, 'no_llamado': True,
                        'error': f"se llegó al monto aprobado: gastado {round(bolsa['gastado'], 4)} + {est} > --ok {a.ok}"}); continue
        X['C'].registrar_taller(q['fijo'], X['FP'] or __import__('myia_fijo_prompt'), X['F'])
        base = f"taller-{cubo}-{q['clave']}-{time.strftime('%Y%m%d-%H%M%S')}"

        def uno(n, q=q, est=est, base=base):
            lid = base + ('' if n == 1 else f'-i{n}')
            if bolsa['gastado'] + est > float(a.ok) + 1e-9: raise LS.SinPresupuesto(f"gastado {round(bolsa['gastado'], 4)} + {est} > --ok {a.ok}")
            try:
                r = AR.llamar(lid, q['prompt'], str(q['salida']), est, f"{q['nota']} intento {n} (aprobado: {a.aprobado})", transporte=transp,
                              modelo=q['modelo'], nivel=q['nivel'], max_out=int(q['max_out']), json_out=True, adjuntos=q.get('adjuntos') or None, fijo=q['fijo'],
                              cotizacion=AR.cotizacion(est, modelo=q['modelo']), ok_usd=est, tope_usd=tp, esquema=q['esquema'])
            except Exception as e:
                _no_llamado_si_no_anotado(AR, lid, e)
                if LS.es_timeout(e): AR.marcar(lid, 'timeout', est, '')   # orden 89: igual que orden 81 (peor caso; se reintenta)
                if LS.clasificar_error(e)['cobro'] == 'error_posible_cobro': bolsa['gastado'] += est
                raise
            bolsa['gastado'] += float(r.get('usd') or 0); return lid, r
        try:
            (lid, r), ints = LS.intentar(uno, max_intentos=mx, max_transitorios=1, dormir=X.get('dormir', time.sleep),
                                         puede_otro=lambda n, c, est=est: bolsa['gastado'] + est <= float(a.ok) + 1e-9)
        except LS.IntentosAgotados as e:
            nl = isinstance(e.ultimo, (LS.NoLlamado, LS.SinPresupuesto)) and len(e.intentos) == 1
            res.append({'clave': q['clave'], 'ok': False, 'no_llamado': nl, 'error': str(e)[:300], 'intentos': e.intentos,
                        'anotados': sum(1 for i in e.intentos if i.get('cobro'))}); continue
        res.append({'clave': q['clave'], 'ok': True, 'ledger': lid, 'usd': r.get('usd'), 'texto': r.get('texto') or '', 'fin': r.get('fin'), 'intentos': ints, 'anotados': len(ints)})
    return res, bolsa
