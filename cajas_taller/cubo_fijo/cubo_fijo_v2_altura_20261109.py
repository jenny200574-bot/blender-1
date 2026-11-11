#!/usr/bin/env python3
"""[v2 altura 9-nov-2026, fase 2 motor, OK Ricardo t987s3315 — copia versionada; cubo_fijo.py v1 NO se tocó]
REGLA DE ALTURA v2: manda la altura del ADN (altura_m, tabla personajes.json del canal). Blender SOLO mide, compara y reporta la diferencia
(altura_blender_m, altura_diferencia_pct); nunca reemplaza ni borra la altura del ADN. Maestro personaje = 02 v2 (estatura en metros obligatoria).
Nuevo: «cubo_fijo alturas» -> tabla ADN vs Blender (gratis, solo informa).
CUBO FIJO persistente en disco · v2 «Maestros Ako» (2-nov-2026). Gratis. NUNCA paga.
Programa OFICIAL de ADN = programa/maestros_ako/ (Ako 2-nov-2026, ledger #418-421). ADN guardado en
adn/<adn_id>_ako.json (5 bloques de Ako + párrafo de inyección). El ADN forense A–D (adn/<id>_v3.json) queda
como histórico/control: se informa, el director NO lo usa.
Uso (vía entrada_ssh.sh, usuario n8ntaller; un solo argumento):
  cubo_fijo leer                    -> catálogo + resumen ADN Ako (+ legado v3) + maestros + overrides
  cubo_fijo ver                     -> VER del cubo (exit 1 si FAIL)
  cubo_fijo ensamblar id1,id2       -> (legado) frases FIJAS por id
  cubo_fijo ensamblar b64.<b64url>  -> {canal,escena,toma_id,personajes[],objetos[],escenario,estilo,estilo_canal}
                                       -> ADN Ako por clase + plantilla director + overrides canal+escena
  cubo_fijo registrar_pj <b64url>   -> PUENTE crear PJ+voz -> CUBO (personajes/<id>.json) + plan extraer cotizado
  cubo_fijo extraer <id>|b64.<b64>  -> disk-first adn/<id>_ako.json; si falta: pedidos con el Maestro de su clase,
                                       cotizados, PAGO CERRADO (PJ: FASE 1 hoja = gasto imagen; FASE 2 ADN = Argon)
  cubo_fijo sellar <b64url>         -> {id,clase,adn_ako_texto,...}: valida formato Ako y escribe _ako.json solo si PASA
"""
import json, sys, os, base64, hashlib, datetime, glob, re, shutil
R = os.environ.get('CUBO_FIJO_RAIZ_PRUEBA') if os.geteuid() == 0 and os.environ.get('CUBO_FIJO_RAIZ_PRUEBA') else '/opt/myia-taller-n8n/cajas/cubo_fijo'
MA = f'{R}/programa/maestros_ako'
CLASES = {'personajes': 'personaje', 'objetos_escenario': 'escenario', 'objetos_pj': 'objeto', 'poderes': 'poder', 'estilo': 'estilo'}
DIR_DE = {'personaje': 'personajes', 'escenario': 'objetos_escenario', 'objeto': 'objetos_pj', 'poder': 'poderes', 'poder_energia': 'poderes', 'estilo': 'estilo'}
MAESTRO = {'personaje': '02_MAESTRO_PERSONAJE_HOJA_ADN_v2_altura_20261109.txt', 'objeto': '03_MAESTRO_OBJETOS.txt', 'poder': '03_MAESTRO_OBJETOS.txt',
           'escenario': '04_MAESTRO_ESCENARIOS.txt', 'estilo': '05_MAESTRO_ESTILO.txt', 'accion': '01_MAESTRO_ACCION_v2.txt'}
PLANTILLA = '00_PLANTILLA_DIRECTOR.txt'
# títulos de bloque que exige cada Maestro de Ako (palabra clave por bloque 1..5)
TITULOS = {'personaje': ['Antropom', 'Fisonom', 'Expresiones', 'Vestuario', 'Giro|Turnaround'],
           'objeto': ['Identificaci', 'Materiales', 'Detalles', 'Comportamiento', 'Inyecci'],
           'escenario': ['Composici', 'Arquitectura|Skyline', 'Auxiliares|Mobiliario', 'Iluminaci', 'Inyecci'],
           'estilo': ['L[ií]nea|Lineart', 'Color|Sombreado|Rendering', 'Iluminaci|Bloom', 'Paleta', 'Inyecci']}
TITULOS['poder'] = TITULOS['objeto']
CL_ALIAS = {'poder_energia': 'poder', 'pj': 'personaje', 'obj': 'objeto', 'esc': 'escenario'}
def ncl(x): return CL_ALIAS.get(x, x)
PREAMBULO = re.compile(r'^\s*(claro|aqu[ií] (tienes|est[aá])|por supuesto|here is|sure[,!]|certainly)\b', re.I)
USD_ARGON = 0.005          # Banco POST /api/adn (Argon), por imagen
USD_HOJA_EST = 0.134       # ledger #421 de Ako (1 imagen V1); estimado, cotizar en Banco antes
GATE = '/opt/myia-taller-n8n/cajas/HABILITAR_PAGO_ADN'
ID = re.compile(r'^[a-z0-9][a-z0-9_-]{1,79}$')
# HOJA APROBADA (inmi 2-nov-2026, orden Ricardo 17:32 Bogotá): el sello guarda la hoja aprobada (copia fija en cubo_fijo/hojas/) y
# ensamblar la usa SIEMPRE por encima de la foto del cliente, para cualquier canal. Voz: 9 rasgos obligatorios (mismo criterio que el nodo 4).
HOJA_OK = ('/opt/myia-taller-n8n/trabajo/', '/opt/myia-taller-n8n/cajas/cubo_fijo/hojas/')
VOZ_R = ('timbre', 'tono', 'ritmo', 'acento', 'idioma', 'edad_aparente', 'energia', 'textura', 'diccion')
def voz_fails(v):
    if not isinstance(v, dict): return ['voz: no es objeto voz_adn']
    f = [] if v.get('schema') == 'voz_adn/v1_universal' else ['voz: schema']
    if v.get('motor') is not None: f.append('voz: motor debe ser null (universal)')
    f += [f'voz: falta {r}' for r in VOZ_R if not str((v.get('rasgos') or {}).get(r) or '').strip()]
    if len(str(v.get('descriptor_universal_en') or '').split(',')) < 4: f.append('voz: descriptor_universal_en < 4 rasgos')
    return f
def hoja_de(e):
    """(ruta, fuente, aviso): hoja aprobada (sha verificado) > hoja_ref > foto del cliente."""
    ha = e.get('hoja_aprobada') or {}
    if ha.get('ruta'):
        if os.path.isfile(ha['ruta']) and (not ha.get('sha256') or sha(ha['ruta']) == ha['sha256']): return ha['ruta'], 'hoja_aprobada', None
        av = f"{e['id']}: hoja_aprobada no existe o su sha cambió (no se usa)"
    else: av = None
    if e.get('hoja_ref'): return e['hoja_ref'], 'hoja_ref', av
    return e.get('imagen_ref'), ('foto_cliente' if e.get('imagen_ref') else None), av
# REFERENCIA DE OBJETOS (inmi 2-nov-2026, orden Ricardo): un objeto, poder o escenario NUNCA usa como referencia la foto ORIGINAL de un
# personaje (carpeta personajes/<id>/referencia-cliente/ o la imagen_ref/imagenes de una ficha de personaje). Los objetos los crea el paso 00
# (4b/4b2 → SELLO OBJ, imagen pintada). Si un objeto de verdad necesita al personaje («necesita_personaje»: true + «dueno»), usa la HOJA
# APROBADA del dueño (cubo_fijo/hojas/, sha verificado), nunca la foto. Genérico para cualquier canal.
FOTO_PJ = re.compile(r'/personajes/[^/]+/referencia-cliente/')
def foto_de_personaje(x, c=None):
    x = str(x or '')
    if not x: return False
    if FOTO_PJ.search(x): return True
    for e in (c or {}).get('personajes', []) or []:
        if x in [str(y) for y in ([e.get('imagen_ref')] + list(e.get('imagenes') or []) + list(e.get('refs') or [])) if y]: return True
    return False
def hoja_aprobada_de(c, pid):
    for e in (c or {}).get('personajes', []) or []:
        if e.get('id') == pid or pid in (e.get('ids_canal') or []):
            r, f, _ = hoja_de(e)
            return r if f == 'hoja_aprobada' else None
    return None
def refs_no_personaje(c, e, imgs):
    """(imágenes, avisos) para un objeto/poder/escenario: sin fotos de personajes; + hoja aprobada del dueño si la ficha la pide."""
    av, ok = [], []
    for x in imgs or []:
        if foto_de_personaje(x, c): av.append(f"{(e or {}).get('id', '?')}: no se usa la foto original de un personaje como referencia de objeto ({os.path.basename(str(x))})")
        else: ok.append(x)
    if (e or {}).get('necesita_personaje') and e.get('dueno'):
        h = hoja_aprobada_de(c, e['dueno'])
        if h: ok.append(h)
        else: av.append(f"{e['id']}: necesita al personaje {e['dueno']} pero no tiene hoja aprobada en cubo_fijo/hojas/")
    return ok, av
now = lambda: datetime.datetime.now().astimezone().isoformat(timespec='seconds')
def out(d, code=0): print(json.dumps(d, ensure_ascii=False)); sys.exit(code)
def rj(p): return json.load(open(p, encoding='utf-8'))
def rt(p): return open(p, encoding='utf-8').read()
def sha(p): return hashlib.sha256(open(p, 'rb').read()).hexdigest()
def wj(p, d):
    tmp = p + '.tmp'; json.dump(d, open(tmp, 'w', encoding='utf-8'), ensure_ascii=False, indent=2); os.replace(tmp, p)
def b64(s):
    if s.startswith('b64.'): s = s[4:]
    s += '=' * (-len(s) % 4); return json.loads(base64.urlsafe_b64decode(s).decode())
def log(ev):
    with open(f'{R}/historial.jsonl', 'a', encoding='utf-8') as f: f.write(json.dumps({'ts': now(), **ev}, ensure_ascii=False) + '\n')
def catalogo():
    c = {k: [] for k in CLASES}
    for k in CLASES:
        for p in sorted(glob.glob(f'{R}/{k}/*.json')):
            e = rj(p); e['_archivo'] = p; c[k].append(e)
    return c
def adn_id(e): return e.get('adn_id', e['id'])
def ako_path(e): return f"{R}/adn/{adn_id(e)}_ako.json"
def v3_path(e): return f"{R}/adn/{adn_id(e)}_v3.json"
def maestros():
    r = {}
    for cl, f in list(MAESTRO.items()) + [('director', PLANTILLA)]:
        p = f'{MA}/{f}'; r[cl] = {'archivo': p, 'sha256': sha(p)[:16]} if os.path.exists(p) else None
    return r
def overrides(canal, escena):
    p = f'{R}/overrides.json'
    if not os.path.exists(p) or not canal: return {'prohibiciones': [], 'reglas': [], 'fuente': None}
    cn = (rj(p).get('canales') or {}).get(canal) or {}
    g = cn.get('global') or {}; s = (cn.get('escenas') or {}).get(str(escena)) or {} if escena not in (None, '') else {}
    return {'prohibiciones': (g.get('prohibiciones') or []) + (s.get('prohibiciones') or []),
            'reglas': (g.get('reglas') or []) + (s.get('reglas') or []), 'fuente': f'overrides.json#{canal}/{escena}'}
def canal_info(canal, d=None):
    """{ESTILO_CANAL}/{CANAL}: del pedido o de canales/<canal>.json (copiado de la ficha del canal). Nunca se inventa."""
    d = d or {}; f = {}
    p = f'{R}/canales/{canal}.json' if canal and ID.match(canal) else ''
    if p and os.path.exists(p): f = rj(p)
    return {'ESTILO_CANAL': d.get('estilo_canal') or f.get('estilo_canal') or '', 'CANAL': d.get('canal_nombre') or f.get('nombre') or canal or ''}
def llenar(txt, vars_):
    for k, v in vars_.items():
        if v: txt = txt.replace('{' + k + '}', v)
    return txt, sorted(set(re.findall(r'\{([A-Z_]{3,})\}', txt)))

def parse_ako(texto, clase):
    """Valida el formato de salida de Ako: 5 bloques con sus títulos, sin preámbulo; bloque 5 = inyección (no PJ)."""
    fails = []; t = (texto or '').strip()
    if not t: return {'status': 'FAIL', 'fails': ['adn_vacio'], 'bloques': [], 'inyeccion': None}
    if PREAMBULO.search(t.split('\n', 1)[0]): fails.append('preambulo')
    kws = TITULOS.get(clase)
    if not kws: return {'status': 'FAIL', 'fails': ['clase_desconocida:' + str(clase)], 'bloques': [], 'inyeccion': None}
    pos, heads = 0, []
    for n, kw in enumerate(kws, 1):
        m = re.compile(rf'^[ \t>#*_\-]*{n}[.)][^\n:]*?(?:{kw})(?:[^\n:]*:[*_]*|[^\n]*$)', re.M | re.I).search(t, pos)
        if not m: fails.append(f'falta_bloque_{n}:{kw}'); continue
        heads.append((n, m.start(), m.end(), re.sub(r'[*#_>\s]+', ' ', m.group(0)).strip(' -'))); pos = m.end()
    bloques = []
    for j, (n, s, e, tit) in enumerate(heads):
        fin = heads[j + 1][1] if j + 1 < len(heads) else len(t)
        cuerpo = t[e:fin].strip()
        if len(cuerpo) < 15: fails.append(f'bloque_{n}_vacio')
        bloques.append({'n': n, 'titulo': tit, 'texto': cuerpo})
    if clase == 'personaje':
        b3 = next((b for b in bloques if b['n'] == 3), None)
        if b3 and len({x.lower()[:5] for x in re.findall(r'(normal|feliz|nervios|enojad|triste)', b3['texto'], re.I)}) < 5: fails.append('bloque_3_sin_5_expresiones')
        b1 = next((b for b in bloques if b['n'] == 1), None); txt1 = b1['texto'] if b1 else ''
        mh = re.search(r'Estatura en metros\W*:?\W*([0-9]+(?:[.,][0-9]+)?)\s*m\b', txt1, re.I)
        mc = re.search(r'Proporci[oó]n en cabezas\W*:?\W*([0-9]+(?:[.,][0-9]+)?)', txt1, re.I)
        altura_adn = float(mh.group(1).replace(',', '.')) if mh else None; cabezas_adn = float(mc.group(1).replace(',', '.')) if mc else None
        if altura_adn is None: fails.append('bloque_1_sin_estatura_en_metros' + ('_FALTA_DATO' if re.search(r'Estatura en metros\W*:?\W*FALTA_DATO', txt1, re.I) else ''))
        if cabezas_adn is None: fails.append('bloque_1_sin_proporcion_en_cabezas')
    if re.search(r'\[GAP', t): fails.append('gap_en_adn')
    iny = None
    if clase != 'personaje':
        b5 = next((b for b in bloques if b['n'] == 5), None); iny = b5['texto'] if b5 else None
        if not iny: fails.append('sin_parrafo_inyeccion')
    r = {'status': 'FAIL' if fails else 'PASS_SELLABLE', 'fails': fails, 'bloques': bloques, 'inyeccion': iny}
    if clase == 'personaje': r.update(altura_m=altura_adn, cabezas=cabezas_adn)
    return r
TOL_ALTURA = 0.02
def comparar_altura(e):
    """v2: ADN manda; Blender solo mide y compara. Devuelve el informe (nunca cambia altura_m)."""
    a, b = e.get('altura_m'), e.get('altura_blender_m')
    r = {'id': e.get('id'), 'altura_adn_m': a, 'altura_blender_m': b, 'diferencia_pct': None, 'estado': None}
    if a is None: r['estado'] = 'FALTA_ALTURA_ADN'
    elif b is None: r['estado'] = 'SIN_MEDIDA_BLENDER'
    else:
        r['diferencia_pct'] = round((float(b) / float(a) - 1) * 100, 2)
        r['estado'] = 'OK' if abs(float(b) / float(a) - 1) <= TOL_ALTURA else 'DIFERENCIA_MAYOR_2PCT (escalar molde al ADN)'
    return r
def adn_ako(e):
    p = ako_path(e)
    if not os.path.exists(p): return None
    a = rj(p); return {**a, 'archivo': p, 'sha256': sha(p)[:16]}
def resumen(e):
    a = adn_ako(e); v3 = v3_path(e)
    return {'formato': 'ako' if a else None, 'ako': ({'archivo': a['archivo'], 'status': a.get('status'), 'fails': a.get('fails'), 'sha256': a['sha256'],
            'bloques': [b['titulo'] for b in a.get('bloques') or []]} if a else None),
            'legado_forense_v3': ({'archivo': v3, 'status': rj(v3).get('status'), 'uso': 'histórico/control; NO formato Ako'} if os.path.exists(v3) else None)}
def find(c, i, canal=None):
    """id exacto o alias ids_canal; si se da canal, la entrada debe ser de ese canal (o sin canal)."""
    for k, L in c.items():
        for e in L:
            if e['id'] == i or i in (e.get('ids_canal') or []):
                if canal and e.get('canal') and e.get('canal') != canal: return k, e, 'canal_distinto:' + str(e.get('canal'))
                return k, e, None
    return None, None, None
def ver(c):
    fails, ids = [], set()
    for k, L in c.items():
        for e in L:
            i = e.get('id')
            if not i or not ID.match(i): fails.append(f'{k}:id_invalido:{i}'); continue
            if i in ids: fails.append('id_duplicado:' + i)
            ids.add(i)
            if e.get('sellado'):
                a = adn_ako(e)
                if not a: fails.append('sellado_sin_adn_ako:' + i)
                elif a.get('status') != 'PASS_SELLABLE': fails.append('sellado_adn_fail:' + i)
                if not e.get('frase_sello'): fails.append('sellado_sin_frase:' + i)
            if e.get('edad') is not None: fails.append('edad_prohibida:' + i)
            if k == 'personajes' and e.get('sellado') and e.get('altura_m') is None: fails.append('falta_altura_adn:' + i)   # v2: manda el ADN
            txt = json.dumps({x: y for x, y in e.items() if x != '_archivo'}, ensure_ascii=False).lower()
            t2 = re.sub(r'no auroras|auroras no|sin auroras|"auroras"', '', txt)
            if 'aurora' in t2: fails.append('aurora:' + i)
    for cl, m in maestros().items():
        if not m: fails.append('falta_maestro:' + cl)
    return fails
def clase_de(k, e): return ncl(e.get('clase')) if ncl(e.get('clase')) in MAESTRO else CLASES.get(k, 'objeto')
def pedidos_extraer(k, e, d):
    """Pedidos cotizados con el Maestro de Ako de su clase. NO se ejecutan aquí."""
    cl = clase_de(k, e) if k else ncl(d.get('clase') or 'personaje')
    mf = f"{MA}/{MAESTRO.get(cl, '')}"
    if not os.path.exists(mf): return {'ok': False, 'error': 'falta_maestro:' + cl}
    canal = d.get('canal') or e.get('canal') or ''
    txt, faltan = llenar(rt(mf), canal_info(canal, {**e, **d}))
    imgs = d.get('imagenes') or e.get('imagenes') or ([e['imagen_ref']] if e.get('imagen_ref') else [])
    av_ref = []
    if cl != 'personaje': imgs, av_ref = refs_no_personaje(c, e, imgs)   # orden Ricardo 2-nov: objetos sin foto de personaje
    gate = os.path.exists(GATE)
    pago = 'CERRADO' if not gate else 'CERRADO: gate presente pero este script NUNCA paga; Banco + OK Ricardo + ledger'
    base = {'maestro': os.path.basename(mf), 'maestro_sha256': sha(mf)[:16], 'prompt': txt, 'faltan_variables': faltan}
    if cl == 'personaje':
        ped = [{'fase': 1, 'que': 'generar HOJA (turnaround 5 vistas + 5 expresiones) con la imagen de referencia', 'tipo': 'imagen',
                'endpoint': 'Banco POST /api/generar', 'entrada_imagenes': imgs, 'usd_estimado': USD_HOJA_EST, 'fuente_precio': 'ledger #421 Ako (1 imagen)',
                'pago': pago, 'requiere': 'HABILITAR_PAGO + OK de Ricardo'},
               {'fase': 2, 'que': 'ADN técnico 5 bloques desde la HOJA de fase 1', 'tipo': 'texto (visión)', 'endpoint': 'Banco POST /api/adn (Argon)',
                'entrada_imagenes': ['<hoja de fase 1>'], 'usd': USD_ARGON, 'pago': 'CERRADO (tope 0)', 'requiere': 'HABILITAR_PAGO + OK de Ricardo'}]
    else:
        ped = [{'fase': 'ADN', 'que': f'ADN {cl} 5 bloques + párrafo de inyección', 'tipo': 'texto (visión)', 'endpoint': 'Banco POST /api/adn (Argon)',
                'entrada_imagenes': imgs, 'usd': USD_ARGON * max(1, len(imgs)), 'pago': 'CERRADO (tope 0)', 'requiere': 'HABILITAR_PAGO + OK de Ricardo'}]
    tot = round(sum(p_.get('usd', p_.get('usd_estimado', 0)) for p_ in ped), 3)
    avisos = list(av_ref)
    if not imgs: avisos.append('sin imagen de referencia en la entrada: no se puede pedir nada' + (' (los objetos salen del paso 00: 4b/4b2 → SELLO OBJ)' if cl != 'personaje' else ''))
    if faltan: avisos.append('faltan variables del canal: ' + ','.join(faltan))
    return {'clase': cl, **base, 'pedidos': ped, 'cotizado_usd': tot, 'pago': 'CERRADO', 'gastado_usd': 0, 'avisos': avisos,
            'despues': 'respuesta del modelo -> cubo_fijo sellar {id,clase,adn_ako_texto} (valida 5 bloques de Ako)'}

a = sys.argv[1:] or ['leer']
op = a[0]
c = catalogo()
if op == 'leer':
    out({'ok': True, 'raiz': R, 'programa': 'maestros_ako v1', 'maestros': maestros(), 'overrides': os.path.exists(f'{R}/overrides.json'),
         'cubo': {k: [{**e, 'adn': resumen(e)} for e in L] for k, L in c.items()}})
if op == 'alturas':   # v2: informe gratis ADN vs Blender (no cambia nada)
    L = [comparar_altura(e) for e in c['personajes'] if e.get('canal') and e.get('sellado')]
    out({'ok': True, 'regla': 'manda el ADN; Blender solo mide y compara (±2%)', 'personajes': L, 'usd': 0})
if op == 'ver':
    f = ver(c); out({'ok': not f, 'ver_fails': f, 'n': {k: len(L) for k, L in c.items()}}, 0 if not f else 1)
if op == 'ensamblar':
    arg = a[1] if len(a) > 1 else ''
    if not arg.startswith('b64.'):   # legado: lista de ids
        fijos = []
        for i in [x for x in arg.split(',') if x]:
            k, e, err = find(c, i)
            if not e: out({'ok': False, 'error': 'faltante_en_cubo:' + i}, 1)
            fijos.append({'id': e['id'], 'clase': clase_de(k, e), 'sellado': bool(e.get('sellado')), 'version': e.get('version', 1),
                          'frase': e.get('frase_sello') or f"[FIJO:{e['id']} sin sellar]", 'adn': resumen(e)})
        if not fijos: out({'ok': False, 'error': 'sin_ids: vienen de la toma o del PUENTE'}, 1)
        out({'ok': True, 'modo': 'legado_ids', 'fijos': fijos, 'prompt_fijos': '\n'.join(f['frase'] for f in fijos)})
    d = b64(arg); canal = d.get('canal') or ''; esc = d.get('escena')
    faltan, avisos = [], []
    def uno(i, clase_esperada):
        k, e, err = find(c, i, canal)
        if not e: faltan.append(f'{clase_esperada}:{i}:no_esta_en_cubo'); return {'id': i, 'clase': clase_esperada, 'adn_ako': None, 'motivo': 'no está en el cubo'}
        if err: faltan.append(f'{clase_esperada}:{i}:{err}'); return {'id': e['id'], 'clase': clase_esperada, 'adn_ako': None, 'motivo': err}
        x = adn_ako(e); cl = clase_de(k, e)
        r = {'id': e['id'], 'alias': i if i != e['id'] else None, 'clase': cl, 'nombre': e.get('nombre') or e['id'], 'version': e.get('version', 1),
             'sellado': bool(e.get('sellado')), 'hoja_sola': bool(e.get('hoja_sola')),
             'dueno': e.get('dueno'), 'legado_v3': os.path.exists(v3_path(e))}
        r['hoja_ref'], r['hoja_fuente'], av = hoja_de(e)
        if av: avisos.append(av)
        if cl != 'personaje' and r['hoja_ref']:   # orden Ricardo 2-nov: un objeto nunca lleva la foto original de un personaje
            _ok, _av = refs_no_personaje(c, e, [r['hoja_ref']])
            if not _ok: r['hoja_ref'], r['hoja_fuente'] = None, None
            avisos.extend(_av)
        if e.get('hoja_aprobada'): r['hoja_aprobada'] = {x: e['hoja_aprobada'].get(x) for x in ('sha256', 'aprobado_por', 'cuando', 'origen')}
        if cl == 'personaje' and e.get('imagen_ref') and r['hoja_ref'] != e.get('imagen_ref'): r['foto_cliente'] = e['imagen_ref']
        if not x: faltan.append(f'{cl}:{e["id"]}:sin_adn_ako' + (' (solo forense v3 legado)' if r['legado_v3'] else '')); r['adn_ako'] = None; r['motivo'] = 'sin ADN formato Ako en disco: correr extraer (cotizado)'; return r
        if x.get('status') != 'PASS_SELLABLE': faltan.append(f'{cl}:{e["id"]}:adn_ako_FAIL'); r['motivo'] = 'ADN Ako en FAIL'
        r['adn_ako'] = {'status': x.get('status'), 'sha256': x['sha256'], 'texto': '\n\n'.join(f"{b['titulo']}\n{b['texto']}" for b in x.get('bloques') or []),
                        'inyeccion': x.get('inyeccion')}
        return r
    pjs = [uno(i, 'personaje') for i in d.get('personajes') or []]
    objs = [uno(i, 'objeto') for i in d.get('objetos') or []]
    escn = uno(d['escenario'], 'escenario') if d.get('escenario') else None
    est = None
    if d.get('estilo'): est = uno(d['estilo'], 'estilo')
    elif canal:
        cand = [e for e in c['estilo'] if e.get('canal') == canal or canal in (e.get('ids_canal') or [])]
        if cand: est = uno(cand[0]['id'], 'estilo')
    if not pjs: faltan.append('casting:la toma no trae personajes')
    if not escn: faltan.append('escenario:la toma no trae escenario')
    if not est: faltan.append('estilo:no hay estilo del canal en el cubo')
    pf = f'{MA}/{PLANTILLA}'
    if not os.path.exists(pf): out({'ok': False, 'error': 'falta_plantilla_director'}, 1)
    ov = overrides(canal, esc)
    ci = canal_info(canal, d)
    if not ci['ESTILO_CANAL']: avisos.append('sin estilo_canal (canales/<canal>.json o pedido)')
    out({'ok': not faltan, 'modo': 'ako', 'canal': canal, 'escena': esc, 'toma_id': d.get('toma_id'),
         'fijos': {'personajes': pjs, 'objetos': objs, 'escenario': escn, 'estilo': est}, 'faltan': faltan, 'avisos': avisos,
         'plantilla_director': rt(pf), 'plantilla_sha256': sha(pf)[:16], 'maestros': maestros(), 'overrides': ov, 'canal_vars': ci,
         'usd': 0, 'nota': 'FIJO = ADN Ako en disco, inalterado; orden imágenes fondo→molde→hojas→estilo último; altura: manda el ADN (altura_m), Blender solo mide y compara'})
if op in ('registrar_pj', 'sellar'):
    d = b64(a[1]); i = d.get('id', '')
    if not ID.match(i): out({'ok': False, 'error': 'id_invalido'}, 1)
    k = 'personajes' if op == 'registrar_pj' else DIR_DE.get(d.get('clase', 'poder'), 'poderes')
    d.pop('edad', None)
    if d.get('altura_cm') is not None:   # v2: una medida de Blender NO pisa la altura del ADN; se guarda aparte para comparar
        if d.get('altura_fuente') == 'blender': d['altura_blender_m'] = round(float(d.pop('altura_cm')) / 100, 4); d.pop('altura_fuente', None)
        else: d['altura_cm_ignorada'] = d.pop('altura_cm'); d['altura_nota'] = 'v2: la altura oficial es altura_m del ADN (tabla personajes.json); altura_cm sin fuente Blender se ignora'
    d.pop('altura_m', None) if d.get('altura_m') is None else None   # nunca se borra la altura del ADN que ya está en disco
    p = f'{R}/{k}/{i}.json'
    old = rj(p) if os.path.exists(p) else {}
    if op == 'sellar':
        ha = d.get('hoja_aprobada')
        if ha:
            if not isinstance(ha, dict) or not all(ha.get(x) for x in ('ruta', 'aprobado_por', 'cuando')):
                out({'ok': False, 'error': 'hoja_aprobada necesita ruta, aprobado_por y cuando'}, 1)
            src = os.path.realpath(ha['ruta'])
            if not src.startswith(HOJA_OK) or not os.path.isfile(src): out({'ok': False, 'error': 'hoja_aprobada: no existe o está fuera de trabajo/ o cubo_fijo/hojas/'}, 1)
            h = sha(src); dst = f"{R}/hojas/{i}_{h[:16]}{os.path.splitext(src)[1].lower() or '.png'}"
            if not os.path.exists(dst): os.makedirs(f'{R}/hojas', exist_ok=True); shutil.copyfile(src, dst)
            if sha(dst) != h: out({'ok': False, 'error': 'hoja_aprobada: copia con sha distinto'}, 1)
            d['hoja_aprobada'] = {**ha, 'ruta': dst, 'sha256': h, 'origen_ruta': src}; d['hoja_ref'] = dst
        if 'voz_adn' in d:
            fv = voz_fails(d['voz_adn'])
            if fv: out({'ok': False, 'error': 'voz_adn_no_cumple_9_rasgos', 'fails': fv}, 1)
        cl = ncl(d.get('clase') or old.get('clase') or CLASES[k])
        e0 = {**old, **{x: y for x, y in d.items() if x != 'adn_ako_texto'}, 'id': i}
        txt = d.pop('adn_ako_texto', None)
        if txt:
            pa = parse_ako(txt, cl)
            if pa['status'] != 'PASS_SELLABLE': out({'ok': False, 'error': 'adn_no_cumple_formato_ako', 'fails': pa['fails']}, 1)
            mf = f"{MA}/{MAESTRO[cl]}"
            wj(ako_path(e0), {'schema': 'myia.adn.ako/v1', 'id': adn_id(e0), 'clase': cl, 'canal': d.get('canal') or old.get('canal'),
                              'maestro': MAESTRO[cl], 'maestro_sha256': sha(mf)[:16], **pa, 'texto': txt.strip(), 'creado': now()})
        x = adn_ako(e0)
        if not x: out({'ok': False, 'error': 'sin_adn_ako_en_disco: correr extraer (cotizado) y sellar con adn_ako_texto'}, 1)
        if x.get('status') != 'PASS_SELLABLE': out({'ok': False, 'error': 'adn_ako_FAIL', 'fails': x.get('fails')}, 1)
        d['frase_sello'] = x.get('inyeccion') or '\n\n'.join(f"{b['titulo']}\n{b['texto']}" for b in x.get('bloques') or [])
        d['clase'] = cl; d['sellado'] = True
    d = {**{x: y for x, y in old.items() if x not in ('_archivo',)}, **d} if old else d   # nunca se pierden campos (adn_id, canal, ids_canal)
    if old:
        campos = ('frase_sello', 'adn_id', 'voz_ref', 'subclase', 'sello_hash_perfil', 'hoja_aprobada', 'voz_adn')
        if any(old.get(x) != d.get(x) for x in campos if x in d):
            v = old.get('version', 1); os.makedirs(f'{R}/versiones', exist_ok=True)
            wj(f'{R}/versiones/{i}_v{v}.json', old); d['version'] = v + 1
        else: d['version'] = old.get('version', 1)
    else: d.setdefault('version', 1)
    d['actualizado'] = now(); d['origen'] = op
    wj(p, d); log({'op': op, 'id': i, 'k': k, 'version': d['version']})
    r = {'ok': True, 'escrito': p, 'entrada': d, 'ver_fails': ver(catalogo())}
    if op == 'registrar_pj' and not adn_ako(d): r['extraer'] = pedidos_extraer('personajes', d, {})
    out(r)
if op == 'extraer':
    arg = a[1] if len(a) > 1 else ''
    d = b64(arg) if arg.startswith('b64.') else {'id': arg}
    i = d.get('id', '')
    if not ID.match(i): out({'ok': False, 'error': 'id_invalido_o_vacio: el id viene del canal/toma, no hay ejemplo fijo'}, 1)
    k, e, err = find(c, i, d.get('canal'))
    if err: out({'ok': False, 'error': err, 'id': i}, 1)
    e = e or {'id': i, **({'clase': d['clase']} if d.get('clase') else {})}
    x = adn_ako(e)
    if x:
        log({'op': 'extraer', 'id': i, 'fuente': 'disco', 'usd': 0})
        out({'ok': True, 'fuente': 'disco (US$0)', 'formato': 'ako', 'id': i, 'adn_archivo': x['archivo'], 'adn_ako': x, 'status': x.get('status'),
             'fails': x.get('fails'), 'sellable': x.get('status') == 'PASS_SELLABLE'})
    plan = pedidos_extraer(k, e, d)
    out({'ok': False, 'fuente': 'falta_en_disco', 'id': i, 'en_cubo': bool(k),
         'legado_forense_v3': v3_path(e) if os.path.exists(v3_path(e)) else None, **plan}, 0)
out({'ok': False, 'error': 'op desconocida'}, 1)
