"""t366u (Ricardo, 3-nov-2026): RECORTE POR ESCENARIO del pedido 4a4 — GENÉRICO (cualquier canal, cualquier número de escenarios).
Antes cada pedido de 4a4 llevaba los documentos COMPLETOS de los pasos anteriores (orden tras orden se sumó contexto y nadie
recortó): un escenario con 3 escenas mandaba ~213 mil caracteres y la llamada pasaba el tope de tiempo. Ahora cada pedido lleva
SOLO lo de SU escenario (sus escenas, sus objetos, su molde), sin metadatos que no se pintan, y el resto del guion solo con el título.
También recorta el pedido 2C (personajes): CONFIG/BASE/GUION solo con lo necesario para estados por escena.
Todo se maneja desde llamadas_config.json → «recorte_pedido» (activo=false → pedido como antes, sin tocar nada).
Gratis, sin red: solo arma texto. Devuelve además un INFORME de lo quitado (se muestra al cotizar, antes de pagar)."""
import json, re

def _j(o): return json.dumps(o, ensure_ascii=False, separators=(',', ':'))
def _sz(o): return len(o) if isinstance(o, str) else len(_j(o))

def config(cfg_llamadas, paso):
    c = ((cfg_llamadas or {}).get('recorte_pedido') or {})
    if not c.get('activo'): return None
    p = (c.get('pasos') or {}).get(paso)
    return p if isinstance(p, dict) and p.get('activo', True) else None

# ------------------------------------------------------------------ piezas genéricas
def quitar_claves(o, claves):
    """Copia sin las claves dadas, a cualquier profundidad (metadatos que no se pintan: justificaciones, autorrevisiones…)."""
    if isinstance(o, dict): return {k: quitar_claves(v, claves) for k, v in o.items() if k not in claves}
    if isinstance(o, list): return [quitar_claves(v, claves) for v in o]
    return o

def quitar_vacios(o, vacios):
    """Copia sin las claves cuyo valor es «vacío» (lista/texto vacío, None, "falta"): no aportan nada a la imagen."""
    def es_vacio(v): return any(type(v) is type(z) and v == z for z in vacios) or (v is None and None in vacios)
    if isinstance(o, dict): return {k: quitar_vacios(v, vacios) for k, v in o.items() if not es_vacio(v)}
    if isinstance(o, list): return [quitar_vacios(v, vacios) for v in o]
    return o

def _escenas_de(x):
    if not isinstance(x, dict): return None
    if 'escenas' in x and isinstance(x['escenas'], list): return {str(n) for n in x['escenas']}
    if 'escena' in x and isinstance(x['escena'], (str, int)): return {str(x['escena'])}
    return None

def filtrar_por_escena(o, nums):
    """En toda lista de registros que dicen su escena («escena» o «escenas»), deja solo los de ESTAS escenas.
    Registro sin escena o con «escenas»: [] (vale para todas) se queda. Si el filtro dejara la lista vacía, queda entera (seguro)."""
    if isinstance(o, dict): return {k: filtrar_por_escena(v, nums) for k, v in o.items()}
    if isinstance(o, list):
        xs = [filtrar_por_escena(v, nums) for v in o]
        marcados = [x for x in xs if _escenas_de(x) is not None]
        if not marcados: return xs
        quedan = [x for x in xs if _escenas_de(x) is None or not _escenas_de(x) or (_escenas_de(x) & nums)]
        return quedan if quedan else xs
    return o

def guion_del_escenario(g, titulos_todos, titulos_mios, cab_max, vecinas_chars):
    """Corta el guion por los títulos de escena de la BASE (base.escenas[].titulo, línea exacta del guion). Escenas del escenario:
    completas. Vecinas (la anterior y la siguiente): sus primeros `vecinas_chars`. Las demás: solo su título. Cabecera: `cab_max`.
    Si no encuentra los títulos en el guion, lo deja ENTERO (seguro) y lo avisa."""
    lineas = g.split('\n'); pos = []
    for t in titulos_todos:
        k = next((i for i, l in enumerate(lineas) if l.strip() == str(t).strip()), None)
        if k is not None: pos.append((k, t))
    pos.sort()
    if not pos or not any(t in titulos_mios for _, t in pos): return g, 'no encontré los títulos de escena en el guion: va ENTERO'
    trozos = [('_cab', '\n'.join(lineas[:pos[0][0]]))]
    for j, (k, t) in enumerate(pos):
        fin = pos[j + 1][0] if j + 1 < len(pos) else len(lineas)
        trozos.append((t, '\n'.join(lineas[k:fin])))
    mias = [i for i, (t, _) in enumerate(trozos) if t in titulos_mios]
    vecinas = {i + d for i in mias for d in (-1, 1)} - set(mias) - {0}
    out = []
    for i, (t, x) in enumerate(trozos):
        if t == '_cab': out.append(x[:cab_max] + (' […]' if len(x) > cab_max else ''))
        elif i in mias: out.append(x)
        elif i in vecinas and vecinas_chars > 0:
            out.append(x[:vecinas_chars] + (' […escena vecina, recortada]' if len(x) > vecinas_chars else ''))
        else: out.append(f'{t}\n[escena de otro escenario: solo el título]')
    return '\n'.join(out), None

def _menciona(o, claves):
    s = _j(o).replace('\\"', '"')
    return any(k and k in s for k in claves)

# ------------------------------------------------------------------ el recorte del 4a4
def recortar_4a4(rc, ids, base_grupo, cfg_canal, i4_esc, inv4b1, inv4c1, moldes_blk, d4p, g, escenas_todas=()):
    """rc = config del paso (llamadas_config.recorte_pedido.pasos.prompts_escenarios). escenas_todas = base.escenas COMPLETAS (para cortar el guion).
    Devuelve (partes_nuevas, informe)."""
    q = set(rc.get('quitar_claves') or [])
    escenas = [e for e in (base_grupo.get('escenas') or [])]
    nums = {str(e.get('numero')) for e in escenas if e.get('numero') is not None}
    inf = {'escenarios': list(ids), 'escenas': sorted(nums, key=lambda x: (len(x), x)), 'quitado': {}, 'avisos': []}
    def nota(b, antes, despues, que): inf['quitado'][b] = {'antes': _sz(antes), 'despues': _sz(despues), 'que': que}

    # 1) objetos que de verdad tocan estos escenarios (para filtrar el catálogo)
    oids = set()
    for x in inv4b1 or []: oids.add(x.get('objeto_id'))
    for x in inv4c1 or []: oids.add(x.get('objeto_id'))
    for x in (d4p or {}).get('objetos_del_lugar') or []: oids.add(x.get('objeto_id'))
    for e in i4_esc or []:
        for o in e.get('objetos_del_lugar_posicion') or []:
            if isinstance(o, dict): oids.add(o.get('objeto_id'))
    for m in (moldes_blk or {}).get('moldes') or []: oids |= set((m.get('posiciones_del_molde') or {}).keys())
    oids.discard(None)

    # 2) CONFIG del canal: solo lo que usa el prompt (el estilo va en su bloque propio; los personajes NO se describen en 4a4)
    cc = cfg_canal if isinstance(cfg_canal, dict) else {}
    keep = rc.get('config_claves') or []; keep_d = rc.get('config_datos_claves') or []
    cfg2 = {k: cc[k] for k in keep if k in cc}
    if isinstance(cc.get('datos'), dict): cfg2['datos'] = {k: cc['datos'][k] for k in keep_d if k in cc['datos']}
    nota('CONFIG_CANAL', cc, cfg2, f"quedan {sorted(cfg2)} (+ datos: {sorted(cfg2.get('datos') or {})}); fuera: {sorted(set(cc) - set(cfg2))} y datos {sorted(set(cc.get('datos') or {}) - set(keep_d))}")

    # 3) BASE: solo escenas del grupo (ya venía así), catálogo con los objetos de estos escenarios, dudas/contradicciones que los tocan (resumidas)
    b2 = dict(base_grupo)
    cat = dict(b2.get('catalogo_oficial') or {})
    if isinstance(cat.get('objetos'), list) and oids:
        cat['objetos'] = [x for x in cat['objetos'] if x.get('id') in oids or _menciona(x, list(ids))]
    b2['catalogo_oficial'] = cat
    claves_rel =[REDACTED]
    for k in rc.get('base_resumir') or []:
        if isinstance(b2.get(k), list):
            b2[k] = [{kk: (str(d.get(kk))[:int(rc.get('resumen_chars', 400))] if d.get(kk) is not None else None) for kk in (rc.get('resumen_campos') or ['duda_id', 'texto', 'decision'])}
                     for d in b2[k] if isinstance(d, dict) and _menciona(d, claves_rel)]
    b2 = quitar_claves(b2, q)
    nota('BASE', base_grupo, b2, f"catálogo: solo objetos de este escenario ({len(cat.get('objetos') or [])}); {', '.join(rc.get('base_resumir') or [])}: solo las que nombran este escenario, sus objetos o sus escenas, resumidas; sin {sorted(q)}")

    # 4) 4A1: lo de este escenario sin duplicados del molde ni metadatos; listas por escena filtradas
    qa = q | set(rc.get('quitar_4a1') or [])
    a2 = [filtrar_por_escena(quitar_claves(e, qa), nums) for e in i4_esc or []]
    nota('INVESTIGACION_4A1', {'escenarios': i4_esc}, {'escenarios': a2}, f"sin {sorted(qa)} (las cámaras van en MOLDES)")

    # 5) 4B1 / 4C1: solo apariciones / estados / usos de ESTAS escenas, sin metadatos
    qo = q | set(rc.get('quitar_objetos') or [])
    b1 = [filtrar_por_escena(quitar_claves(x, qo), nums) for x in inv4b1 or []]
    c1 = [filtrar_por_escena(quitar_claves(x, qo), nums) for x in inv4c1 or []]
    nota('INVESTIGACION_4B1', {'objetos': inv4b1}, {'objetos': b1}, f"mismos objetos ({len(b1)}); apariciones/estados/usos solo de las escenas {inf['escenas']}; sin {sorted(qo)} (prompts del objeto suelto: son para 4b2/4c2, no para pintar el lugar)")
    nota('INVESTIGACION_4C1', {'objetos': inv4c1}, {'objetos': c1}, f"mismos objetos ({len(c1)}); estados solo de las escenas {inf['escenas']}; sin {sorted(qo)}")

    # 6) MOLDES: «armado» sin las líneas que ya van leídas en posiciones_del_molde / camaras_del_molde
    pat = [re.compile(x) for x in rc.get('molde_armado_ya_leido') or []]
    m2 = json.loads(_j(moldes_blk or {}))
    for m in m2.get('moldes') or []:
        if isinstance(m.get('armado'), list): m['armado'] = [a for a in m['armado'] if not any(p.match(str(a)) for p in pat)]
    qi = set(rc.get('quitar_indice_imagenes') or [])
    if qi and isinstance(m2.get('imagenes_adjuntas'), list): m2['imagenes_adjuntas'] = [{k: v for k, v in x.items() if k not in qi} for x in m2['imagenes_adjuntas']]
    m2 = quitar_claves(m2, q)
    nota('MOLDES', moldes_blk, m2, 'armado sin las líneas de objetos y cámaras (ya van como posiciones_del_molde y camaras_del_molde); índice de imágenes sin ' + str(sorted(qi)) + ' (repetido en camaras_del_molde)')

    # 7) 4P: solo lo de estos escenarios (ya venía así) sin metadatos
    p2 = filtrar_por_escena(quitar_claves(d4p, q), nums)
    nota('PROFUNDIZACION_4P', d4p, p2, f'sin {sorted(q)}')

    # 8) GUION: escenas del escenario completas, vecinas recortadas, el resto solo con título
    tit_all = [e.get('titulo') for e in (escenas_todas or []) if e.get('titulo')]
    tit_mias = {e.get('titulo') for e in escenas if e.get('titulo')}
    g2, av = guion_del_escenario(g, tit_all, tit_mias, int(rc.get('guion_cabecera_chars', 1500)), int(rc.get('guion_vecinas_chars', 400)))
    if av: inf['avisos'].append(av)
    nota('GUION', g, g2, f"completas las escenas {inf['escenas']}; anterior/siguiente: primeros {rc.get('guion_vecinas_chars', 400)} caracteres; las demás solo el título; cabecera {rc.get('guion_cabecera_chars', 1500)} caracteres")

    out = {'cfg': cfg2, 'base': b2, 'd4p': p2, 'i4': a2, 'inv4b1': b1, 'inv4c1': c1, 'moldes': m2}
    if 'quitar_valores_vacios' in rc:   # al final: los filtros de arriba miran «escenas»: [] (vale para todas) antes de quitar vacíos
        vz = list(rc.get('quitar_valores_vacios') or [])
        out = {k: quitar_vacios(v, vz) for k, v in out.items()}
        for b, k in (('CONFIG_CANAL', 'cfg'), ('BASE', 'base'), ('PROFUNDIZACION_4P', 'd4p'), ('MOLDES', 'moldes')):
            inf['quitado'][b]['despues'] = _sz(out[k])
        inf['quitado']['INVESTIGACION_4A1']['despues'] = _sz({'escenarios': out['i4']})
        inf['quitado']['INVESTIGACION_4B1']['despues'] = _sz({'objetos': out['inv4b1']})
        inf['quitado']['INVESTIGACION_4C1']['despues'] = _sz({'objetos': out['inv4c1']})
        inf['vacios_quitados'] = 'claves con valor vacío o "falta" (' + ', '.join(json.dumps(z, ensure_ascii=False) for z in vz) + ')'
    out['guion'] = g2
    return out, inf


# ------------------------------------------------------------------ el recorte del 2C (personajes)
def _slim_obj(o, keep):
    """Deja solo las claves pedidas (orden de keep). Si keep es False/None → None (quitar bloque).
    Si keep == 'completo' → objeto tal cual."""
    if keep is False or keep is None: return None
    if keep == 'completo': return o
    if not isinstance(o, dict): return o
    if isinstance(keep, list): return {k: o[k] for k in keep if k in o}
    return o

def recortar_2c(rc, base, cfg_canal, g):
    """rc = config del paso (llamadas_config.recorte_pedido.pasos.personajes).
    2C necesita TODAS las escenas (estados por escena) y TODOS los personajes del catálogo.
    Recorta: CONFIG (solo reglas/estilo/fichas), BASE (identidades + presencia por escena + ids útiles),
    GUION (cabecera corta + escenas narrativas; sin notas de producción).
    Devuelve (partes_nuevas, informe). Gratis, sin red."""
    inf = {'paso': 'personajes', 'quitado': {}, 'avisos': [], 'personajes_base': [], 'escenas_base': []}
    def nota(b, antes, despues, que): inf['quitado'][b] = {'antes': _sz(antes), 'despues': _sz(despues), 'que': que}

    cc = cfg_canal if isinstance(cfg_canal, dict) else {}
    keep = list(rc.get('config_claves') or [])
    keep_d = list(rc.get('config_datos_claves') or [])
    keep_b = list(rc.get('biblia_claves') or [])
    cfg2 = {k: cc[k] for k in keep if k in cc and k not in ('datos', 'biblia')}
    if 'datos' in keep and isinstance(cc.get('datos'), dict):
        cfg2['datos'] = {k: cc['datos'][k] for k in keep_d if k in cc['datos']}
    if 'biblia' in keep and isinstance(cc.get('biblia'), dict):
        bib = cc['biblia']
        cfg2['biblia'] = {k: bib[k] for k in keep_b if k in bib} if keep_b else bib
    # personajes del canal: fichas (ropa/descripcion) — necesarias para deducir con origen config_canal
    if 'personajes' in keep and isinstance(cc.get('personajes'), list):
        cfg2['personajes'] = cc['personajes']
    if rc.get('nota_texto'):
        cfg2['_nota_recorte_2c'] = rc['nota_texto']
    nota('CONFIG_CANAL', cc, cfg2,
         f"quedan {sorted(k for k in cfg2 if not k.startswith('_'))}"
         f" (+ datos: {sorted(cfg2.get('datos') or {})}; biblia: {sorted(cfg2.get('biblia') or {})}); "
         f"fuera: {sorted(set(cc) - set(cfg2) - {'_nota_recorte_2c'})}")

    bj = base if isinstance(base, dict) else {}
    b2 = {'capitulo': bj.get('capitulo')}
    esc_keep = list(rc.get('base_escena_claves') or
                    ['numero', 'titulo', 'tipo', 'escenario_id', 'int_ext', 'hora', 'clima', 'personajes', 'continuidad'])
    cont_keep = rc.get('base_continuidad_claves')  # None = continuidad entera; lista = subclaves
    escenas = []
    for e in (bj.get('escenas') or []):
        if not isinstance(e, dict): continue
        row = {k: e[k] for k in esc_keep if k in e}
        if 'continuidad' in row and isinstance(row['continuidad'], dict) and isinstance(cont_keep, list):
            row['continuidad'] = {k: row['continuidad'][k] for k in cont_keep if k in row['continuidad']}
        escenas.append(row)
    b2['escenas'] = escenas
    inf['escenas_base'] = [str(e.get('numero')) for e in escenas if e.get('numero') is not None]

    cat0 = bj.get('catalogo_oficial') or {}
    cat_cfg = rc.get('base_catalogo') or {}
    cat2 = {}
    # personajes: siempre completo (ids + formas) — salida 2C exige un registro por cada uno
    pjs = cat0.get('personajes') if cat_cfg.get('personajes', 'completo') != False else []
    cat2['personajes'] = pjs if isinstance(pjs, list) else []
    inf['personajes_base'] = [(p.get('id') or p.get('personaje_id'), p.get('nombre')) for p in cat2['personajes'] if isinstance(p, dict)]
    for bloque, default in (('escenarios', ['id', 'nombre', 'escenas']),
                            ('objetos', ['id', 'nombre']),
                            ('efectos', False)):
        keep_blk = cat_cfg[bloque] if bloque in cat_cfg else default
        raw = cat0.get(bloque)
        if keep_blk is False or keep_blk is None:
            continue
        if keep_blk == 'completo':
            cat2[bloque] = raw
        elif isinstance(raw, list) and isinstance(keep_blk, list):
            cat2[bloque] = [{k: x[k] for k in keep_blk if isinstance(x, dict) and k in x} for x in raw]
        else:
            cat2[bloque] = raw
    b2['catalogo_oficial'] = cat2

    # contradicciones/dudas de la BASE: solo las que nombran personajes (si se piden)
    pnames = []
    for p in cat2.get('personajes') or []:
        if isinstance(p, dict):
            pnames += [str(p.get('id') or ''), str(p.get('nombre') or '')]
    pnames = [x for x in pnames if x]
    for k in rc.get('base_resumir') or []:
        xs = bj.get(k)
        if not isinstance(xs, list): continue
        campos = rc.get('resumen_campos') or ['tipo', 'texto', 'motivo']
        lim = int(rc.get('resumen_chars', 300))
        filtradas = []
        for d in xs:
            if not isinstance(d, dict): continue
            if pnames and not _menciona(d, pnames): continue
            filtradas.append({kk: (str(d.get(kk))[:lim] if d.get(kk) is not None else None) for kk in campos if kk in d or True})
        b2[k] = filtradas
    for k in rc.get('base_quitar') or []:
        b2.pop(k, None)
    q = set(rc.get('quitar_claves') or [])
    if q: b2 = quitar_claves(b2, q)
    nota('BASE', bj, b2,
         f"escenas={len(escenas)} campos={esc_keep}; catálogo personajes={len(cat2.get('personajes') or [])}, "
         f"objetos={len(cat2.get('objetos') or [])}, escenarios={len(cat2.get('escenarios') or [])}; "
         f"sin efectos={('efectos' not in cat2)}; quitado {list(rc.get('base_quitar') or [])}")

    # GUION: cabecera corta + todas las escenas de la BASE completas; títulos de producción fuera
    tit_all = [e.get('titulo') for e in (bj.get('escenas') or []) if isinstance(e, dict) and e.get('titulo')]
    quitar_tit = set(rc.get('guion_quitar_titulos') or [])
    # también detectar cabeceras tipo "10. Notas..." aunque no estén en BASE
    tit_mias = {t for t in tit_all if t}
    g2, av = guion_del_escenario(g, tit_all + list(quitar_tit), tit_mias,
                                 int(rc.get('guion_cabecera_chars', 800)),
                                 int(rc.get('guion_vecinas_chars', 0)))
    if av: inf['avisos'].append(av)
    # si quedaron secciones de notas (título no en BASE), recortar por línea de título exacta
    if quitar_tit and not av:
        lineas = g2.split('\n'); out=[]; skip=False
        for ln in lineas:
            if ln.strip() in quitar_tit: skip=True; continue
            # nueva escena de la BASE reinicia
            if any(ln.strip() == t for t in tit_mias): skip=False
            if not skip: out.append(ln)
        g3 = '\n'.join(out)
        if len(g3) < len(g2): g2 = g3
    nota('GUION', g, g2,
         f"cabecera {rc.get('guion_cabecera_chars', 800)} chars; escenas BASE completas ({len(tit_mias)}); "
         f"sin títulos {sorted(quitar_tit) or '—'}")

    # integridad: no perder personajes ni escenas
    if len(inf['personajes_base']) != len(cat0.get('personajes') or []):
        inf['avisos'].append(f"ALERTA: personajes BASE {len(cat0.get('personajes') or [])} → recorte {len(inf['personajes_base'])}")
    if len(inf['escenas_base']) != len(bj.get('escenas') or []):
        inf['avisos'].append(f"ALERTA: escenas BASE {len(bj.get('escenas') or [])} → recorte {len(inf['escenas_base'])}")

    if 'quitar_valores_vacios' in rc:
        vz = list(rc.get('quitar_valores_vacios') or [])
        cfg2 = quitar_vacios(cfg2, vz)
        b2 = quitar_vacios(b2, vz)
        inf['quitado']['CONFIG_CANAL']['despues'] = _sz(cfg2)
        inf['quitado']['BASE']['despues'] = _sz(b2)
        inf['vacios_quitados'] = True

    antes = _sz(cc) + _sz(bj) + _sz(g)
    despues = _sz(cfg2) + _sz(b2) + _sz(g2)
    inf['total_bloques'] = {'antes': antes, 'despues': despues, 'ahorro': antes - despues}
    return {'cfg': cfg2, 'base': b2, 'guion': g2}, inf
