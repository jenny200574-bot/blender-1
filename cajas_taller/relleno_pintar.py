#!/usr/bin/env python3
"""PISTA INMI (2026-10-29): orden 89 — pintar referencias de los personajes de RELLENO de un capítulo (frente y espalda).

Los personajes cargados del canal NUNCA se generan (solo sus imágenes subidas/aprobadas). El RELLENO del capítulo (orden 88:
figuras secundarias nuevas, sin hoja, con descripción genérica del guion) puede tener una referencia pintada para que todas sus
tomas se parezcan. Esto la hace:
  relleno-cotizar  (GRATIS)  textos EXACTOS (<capítulo>/relleno/pedidos/) + precio peor caso por imagen.
  relleno-pintar   (PAGO)    Nano Banana (modelo y talla DEL CANAL): frente (sin refs, desde la descripción + estilo del canal)
                             y espalda (ref 1 = el frente recién pintado). Guarda <capítulo>/relleno/<id>/frente.png|espalda.png
                             y anota en personajes_relleno.json «imagenes» con estado pendiente_revision. NO aprueba nada.
Solo voz → nunca se pinta. Un relleno ya aprobado o con imágenes → no se repinta (salvo --forzar con su id).
Reglas de pago (las de siempre): CERRADO sin cajas/HABILITAR_PAGO_RELLENO (con el monto), --ok USD y --aprobado QUIEN;
ledger ANTES de cada intento (id propio), tope de tiempo + reintento (llamada_segura), 429 → no_cobrado, timeout = peor caso,
se para al llegar a --ok. Genérico: sin nombres de canales ni de personajes."""
import json, os, re, time
from pathlib import Path

AQUI = Path(__file__).resolve().parent
import personajes as PJ
import personajes_hoja as PH
import llamada_segura as LS

GUARDA = 'HABILITAR_PAGO_RELLENO'
VISTAS = ('frente', 'espalda')

def estilo_texto(canal):
    import estilo_taller as ET
    e = ET.resolver(ET.canal_datos(canal))
    if not e: raise ValueError('el canal no tiene estilo fijo aprobado: no se pinta')
    return f"{e['nombre']}\n{e['descripcion_en']}" + (f"\nAvoid: {e['negativo']}" if e.get('negativo') else '')

def prompt(vista, x, estilo):
    E = PH.HV()['encuadre']
    return (PH.texto(f'relleno_{vista}.txt').replace('{PERSONAJE}', x['nombre']).replace('{DESCRIPCION}', (x.get('descripcion') or '-').strip())
            .replace('{ENCUADRE}', E['texto']).replace('{FONDO}', E['fondo']).replace('{ESTILO}', estilo))

def plan(canal, D, solo=None, forzar=()):
    rel = PJ.relleno_capitulo(canal, D); out = []
    for pid, x in rel.items():
        if solo and pid not in solo and not any(PJ.igual(s, x['nombre']) for s in solo): continue
        if x.get('tipo') != 'relleno': out.append({'id': pid, 'nombre': x['nombre'], 'pintar': False, 'motivo': 'solo voz: no se ve en cuadro'}); continue
        ya = x.get('imagenes') or {}
        if x.get('estado') == 'aprobado' and pid not in forzar: out.append({'id': pid, 'nombre': x['nombre'], 'pintar': False, 'motivo': 'ya aprobado'}); continue
        falta = [v for v in VISTAS if pid in forzar or not (ya.get(v) and (Path(D) / ya[v]).is_file())]
        out.append({'id': pid, 'nombre': x['nombre'], 'pintar': bool(falta), 'vistas': falta, 'x': x, 'motivo': None if falta else 'ya tiene frente y espalda'})
    return out

def cotizar(canal, D, solo=None, forzar=()):
    P = PH.precios(canal); est = estilo_texto(canal); d = Path(D) / 'relleno' / 'pedidos'; d.mkdir(parents=True, exist_ok=True)
    pl = plan(canal, D, solo, forzar); n = 0; usd = 0.0
    for q in pl:
        for v in q.get('vistas') or []:
            (d / f"{q['id']}__{v}.txt").write_text(prompt(v, q['x'], est), encoding='utf-8')
            n += 1; usd += PH.est_imagen(P, 0 if v == 'frente' else 1)
    return {'ok': True, 'accion': 'personajes relleno-cotizar', 'capitulo': Path(D).name, 'imagenes': n, 'usd_peor_caso': round(usd, 4),
            'modelo': P['imagen']['modelo'], 'talla': P['imagen']['talla'], 'pedidos': str(d),
            'personajes': [{k: q.get(k) for k in ('id', 'nombre', 'pintar', 'vistas', 'motivo')} for q in pl], 'llamadas_hechas': 0, 'usd': 0}

def revisar_guarda(a):
    G = PH.GUARDA_DIR / GUARDA
    if not G.is_file(): return f'pintar relleno cerrado: falta {G.name} (pago no aprobado). No se llamó a nada.'
    if a.ok is None or not a.aprobado: return 'falta --ok USD y --aprobado QUIEN'
    mm = re.search(r'\d+(?:\.\d+)?', G.read_text(errors='replace'))
    if not mm: return f'{G.name} no trae el monto aprobado: no se llama'
    if a.ok > float(mm.group()) + 1e-9: return f'--ok {a.ok} pasa el monto habilitado en {G.name} ({mm.group()})'
    return None

def guardar(canal, D, pid, vista, data, lid, texto, refs):
    D = Path(D); o = D / 'relleno' / pid / f'{vista}.png'; o.parent.mkdir(parents=True, exist_ok=True)
    if o.is_file() and PJ.sha(o.read_bytes()) != PJ.sha(data): o.rename(o.with_name(f'{vista}_{PJ.sha(o.read_bytes())[:16]}.png'))
    o.write_bytes(data); rel = str(o.relative_to(D))
    PJ.escribir_json(o.with_suffix('.json'), {'origen': 'relleno_ia', 'vista': vista, 'ledger': lid, 'fecha': PJ.ahora(), 'refs_entrada': refs, 'texto': texto, 'aprobada': False})
    with PJ.Candado(canal):
        f = PJ.relleno_f(D); doc = PJ.leer_json(f) or {}; x = (doc.get('personajes') or {})[pid]
        x.setdefault('imagenes', {})[vista] = rel; x['imagen'] = x['imagenes'].get('frente') or rel
        x['imagenes_estado'] = 'pendiente_revision'; x.setdefault('imagenes_ledger', {})[vista] = lid
        doc['actualizado'] = PJ.ahora(); PJ.escribir_json(f, doc)
    return rel

def pintar(canal, D, a, solo=None, forzar=(), X=None):
    err = revisar_guarda(a)
    if err: return {'ok': False, 'error': err, 'llamadas_hechas': 0}
    P = (X or {}).get('precios') or PH.precios(canal); est = estilo_texto(canal); pl = plan(canal, D, solo, set(forzar or ()))
    X = X or PH._app(); AR, T = X['AR'], X['types']; cli = X.get('cli') or AR._cliente()
    I = P['imagen']; m, talla = I['modelo'], I['talla']; tope = PH.H()['tope_por_llamada_usd']
    ritmo = LS.Ritmo(X['ritmo_dir'], m, LS.num_env('TALLER_PAUSA_IMAGEN_S', PH.H()['separar']['pausa_s']), dormir=X.get('dormir', time.sleep))
    bolsa = {'gastado': 0.0}; corrida = time.strftime('%Y%m%d-%H%M%S'); res = []
    for q in pl:
        if not q['pintar']: res.append({'personaje': q['nombre'], 'saltado': q['motivo']}); continue
        frente = None
        for vista in q['vistas']:
            refs = []
            if vista == 'espalda':
                fx = frente or (str(Path(D) / q['x']['imagenes']['frente']) if (q['x'].get('imagenes') or {}).get('frente') else None)
                if not fx or not Path(fx).is_file(): res.append({'personaje': q['nombre'], 'vista': vista, 'saltado': 'falta el frente (hazlo primero)'}); continue
                refs = [fx]
            texto = prompt(vista, q['x'], est); e_ = PH.est_imagen(P, len(refs))
            partes = [T.Part.from_bytes(data=Path(r).read_bytes(), mime_type='image/png') for r in refs] + [T.Part.from_text(text=texto)]
            cfg_ = T.GenerateContentConfig(response_modalities=['IMAGE', 'TEXT'], image_config=T.ImageConfig(aspect_ratio=PH.HV()['encuadre']['aspecto'], image_size=talla),
                                           http_options=T.HttpOptions(timeout=LS.timeout_ms('imagen')))
            def hacer(lid, k, e_=e_, partes=partes, cfg_=cfg_, vista=vista, q=q):
                ritmo.esperar()
                try: AR.registrar(lid, f'{m} {talla}', e_, f"relleno {Path(D).name} {q['id']} {vista} intento {k} (aprobado {a.aprobado})", tipo='imagen', ok_usd=e_, tope_usd=tope)
                except Exception as ex: PH._no_llamado_si_no_anotado(AR, lid, ex); raise
                try: return cli.models.generate_content(model=m, contents=[T.Content(role='user', parts=partes)], config=cfg_)
                except Exception as ex: AR.marcar(lid, LS.estado_fallo(ex), e_, ''); raise
            try: (lid, r), ints = PH._intentar(X, a, e_, bolsa, f"taller-relleno-{q['id'][:40]}-{vista}-{corrida}", hacer)
            except LS.IntentosAgotados as ex:
                if isinstance(ex.ultimo, LS.SinPresupuesto) and len(ex.intentos) == 1: res.append({'personaje': q['nombre'], 'vista': vista, 'saltado': str(ex.ultimo)}); continue
                res.append({'personaje': q['nombre'], 'vista': vista, 'ok': False, 'error': str(ex)[:300], 'intentos': ex.intentos}); continue
            except LS.NoLlamado as ex: res.append({'personaje': q['nombre'], 'vista': vista, 'ok': False, 'error': str(ex)}); continue
            data = next((pt.inline_data.data for c in (r.candidates or []) for pt in ((c.content.parts or []) if c.content else []) if pt.inline_data and pt.inline_data.data), None)
            AR.marcar(lid, 'ok' if data else 'sin_imagen', e_, ''); bolsa['gastado'] += e_
            if not data: res.append({'personaje': q['nombre'], 'vista': vista, 'ok': False, 'error': 'el modelo no devolvió imagen', 'ledger': lid}); continue
            rel = guardar(canal, D, q['id'], vista, data, lid, texto, refs)
            if vista == 'frente': frente = str(Path(D) / rel)
            res.append({'personaje': q['nombre'], 'vista': vista, 'ok': True, 'ledger': lid, 'usd': e_, 'imagen': rel, 'intentos': len(ints)})
    hechas = [x for x in res if 'saltado' not in x]
    return {'ok': all(x.get('ok') for x in hechas), 'accion': 'personajes relleno-pintar', 'capitulo': Path(D).name, 'resultados': res,
            'llamadas_hechas': len(hechas), 'usd': round(bolsa['gastado'], 4),
            'nota': 'imágenes de RELLENO pendientes de revisión: siguen siendo relleno de este capítulo; no se adjuntan a los cubos hasta que una persona apruebe el relleno'}
