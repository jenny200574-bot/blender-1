"""Construye biblioteca_formas.json (una ficha por forma), prueba cada forma (medidas y estados roto/deformado/flotando)
y prepara la escena de la hoja de contacto para blender_auto. US$0, local, sin red ni IA.
uso: python3 construir_biblioteca.py [carpeta_salida]"""
import json, math, os, sys, traceback
AQUI = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, os.path.dirname(AQUI)); sys.path.insert(0, AQUI)
import formas_detalle as FD, formas_biblioteca as FB, datos_fichas as DF
os.umask(0o077)
SAL = sys.argv[1] if len(sys.argv) > 1 else os.path.join(AQUI, 'salida_biblioteca')
TOL_TIPICO = 0.02
COLGADOS = {'cable_colgante': 'cuelga a la altura alto_m (no apoya en el piso)', 'marquesina': 'va en la pared; alto_m = altura del borde alto'}
BIB_OBJ = os.path.normpath(os.path.join(AQUI, '..', '..', 'biblioteca_objetos.json'))
viejo = {o['id']: o for o in json.load(open(BIB_OBJ, encoding='utf-8'))['objetos']}

def _crudo(fid, w, d, h, prm=None):
    T = FD.transformador([0, 0], 0, 0); out = []
    for p in FB.G[fid](w, d, h, **(prm or {})):
        if p.get('tipo') == '_pieza_interna': out.append(p['pieza'])
        else: out += FD.parte_a_piezas(p, T)
    return out

def piezas_de(fid, w, d, h, prm=None, vueltas=8):
    """genera la forma y la AJUSTA a ancho x fondo x alto pedidos: corrige los parámetros internos
    (iterando) hasta que la caja medida coincide; así quien pide 'mesa 1.2 x 0.8 x 0.75' recibe eso."""
    a = [w, d, h]; mejor = None
    for _ in range(vueltas):
        pz = _crudo(fid, a[0], a[1], a[2], prm); mn, mx = FD.bbox(pz); bb = [mx[i] - mn[i] for i in range(3)]
        if fid in COLGADOS: bb[2] = mx[2]                # alto = altura de su punto más alto sobre el piso
        err = max(abs(bb[0] - w), abs(bb[1] - d), abs(bb[2] - h))
        if mejor is None or err < mejor[0]: mejor = (err, pz)
        if err <= 0.002: break
        a = [max(1e-3, a[i] * (t / bb[i] if bb[i] > 1e-6 else 1.0)) for i, t in enumerate((w, d, h))]
    pz = mejor[1]; mn, _ = FD.bbox(pz)
    if fid in COLGADOS: return pz                     # colgada: se mide hasta su punto alto, no se baja al piso
    return FD.desplazar(pz, [0, 0, -mn[2]])          # siempre apoyada en z = 0

def anclajes(pz):
    mn, mx = FD.bbox(pz); cx, cy = (mn[0] + mx[0]) / 2, (mn[1] + mx[1]) / 2; zm = (mn[2] + mx[2]) / 2; r = lambda v: [round(x, 3) for x in v]
    a = {'base': r([cx, cy, mn[2]]), 'encima': r([cx, cy, mx[2]]), 'frente': r([cx, mn[1], zm]), 'atras': r([cx, mx[1], zm]),
         'izquierda': r([mn[0], cy, zm]), 'derecha': r([mx[0], cy, zm])}
    nombres = {'asiento': 'sentarse', 'tablero': 'superficie', 'encimera': 'superficie', 'tapa': 'superficie_tapa', 'colchon': 'acostarse',
               'pantalla': 'pantalla', 'hoja': 'puerta_hoja', 'puerta': 'puerta_hoja', 'mango': 'agarre', 'empunadura': 'agarre', 'asa': 'agarre',
               'manillar': 'agarre', 'luminaria': 'luz', 'pantalla_lampara': 'luz', 'difusor': 'luz', 'llama': 'luz', 'boca': 'boca', 'balda': 'balda',
               'superficie': 'superficie', 'cabina': 'cabina', 'rueda': 'rueda', 'cuerda': 'colgar'}
    cont = {}
    for p in pz:
        base = (p.get('nombre') or '').split('_')[0] if p.get('nombre') not in nombres else p.get('nombre')
        k = nombres.get(p.get('nombre')) or nombres.get(base)
        if not k: continue
        pm, px = FD.bbox_pieza(p); cont[k] = cont.get(k, 0) + 1; key = k if cont[k] == 1 else f'{k}_{cont[k]}'
        if cont[k] <= 4: a[key] = r([(pm[0] + px[0]) / 2, (pm[1] + px[1]) / 2, px[2]])
    return a

def probar_estados(pz):
    res = {}
    def prueba(nombre, fn):
        try:
            out = fn(); ok = bool(out) and len(FD.bbox(out)) == 2
            res[nombre] = {'admite': ok, 'operacion': OPS[nombre], 'piezas_resultado': len(out)}
        except Exception as e:
            res[nombre] = {'admite': False, 'operacion': OPS[nombre], 'error': f'{type(e).__name__}: {e}'}
    prueba('roto', lambda: FD.fragmentar(pz, {'trozos': 3, 'separacion_m': 0.05, 'angulo_max_grados': 12, 'caida': 'al_piso', 'semilla': 1}))
    hay_caja = any(p['t'] == 'caja' for p in pz)
    if hay_caja: prueba('deformado', lambda: FD.deformar(pz, {'modo': 'curvar', 'amplitud_m': 0.05, 'segmentos': 5}))
    else: res['deformado'] = {'admite': False, 'operacion': OPS['deformado'], 'motivo': 'deformar dobla solo cajas; esta forma no tiene cajas (se puede romper o mover)'}
    prueba('flotando', lambda: FD.desplazar(pz, [0, 0, 0.5]))
    prueba('girado_volcado', lambda: FD.girar(pz, [90, 0, 0]))
    return res
OPS = {'roto': 'fragmentar', 'deformado': 'deformar', 'flotando': 'desplazar (z>0, apoyado_en: null)', 'girado_volcado': 'girar'}
HUECO = {'muro', 'muro_ladrillo', 'casa_simple', 'edificio_bloque', 'pared_agujero', 'portico', 'caseta'}
VEHICULO_LARGO_X = 'vehiculos'

def fuente_medidas(fid, cat, w, d, h, vid):
    if not vid: return 'típico propuesto por Star (estándar razonable), por confirmar por canal — PENDIENTE fuente externa'
    o = viejo.get(vid); m = o['medidas']; vw, vd, vh = m.get('ancho_m'), m.get('fondo_m'), m.get('alto_m')
    if [vw, vd, vh] == [0.2, 0.2, 0.2]: return f'biblioteca_objetos.json#{vid} solo tenía 0.2x0.2x0.2 genérico; aquí típico propuesto por Star, por confirmar por canal'
    if (vw, vd, vh) == (w, d, h): return f'biblioteca_objetos.json#{vid} (típico, por confirmar por canal)'
    if cat == VEHICULO_LARGO_X and (vd, vw, vh) == (w, d, h): return f'biblioteca_objetos.json#{vid} (mismas medidas; aquí el largo va en x)'
    return f'basado en biblioteca_objetos.json#{vid} ({vw}x{vd}x{vh}); aquí {w}x{d}x{h} porque la forma compuesta incluye todas sus partes; por confirmar por canal'

def main():
    fichas, errores = [], []
    for fid in sorted(FB.G, key=lambda k: (DF.D[k][0], k)):
        cat, en, w, d, h, vid = DF.D[fid]
        try:
            pz = piezas_de(fid, w, d, h)
        except Exception as e:
            errores.append({'id': fid, 'error': traceback.format_exc(limit=2)}); continue
        mn, mx = FD.bbox(pz); bb = [mx[i] - mn[i] for i in range(3)]
        if fid in COLGADOS: bb[2] = mx[2]
        dif = [round(bb[0] - w, 4), round(bb[1] - d, 4), round(bb[2] - h, 4)]
        ajusta = all(abs(x) <= TOL_TIPICO for x in dif) and (abs(mn[2]) <= TOL_TIPICO or fid in COLGADOS)
        tipos = sorted({p['t'] for p in pz}); est = probar_estados(pz)
        if fid in HUECO: est['con_hueco'] = {'admite': True, 'operacion': 'abrir_hueco (si se usa como límite pared/muro)'}
        fi = {'id': fid, 'nombre_generico': fid.replace('_', ' '), 'nombre_en': en, 'categoria': cat,
              'medidas_tipicas': {'ancho_m': w, 'fondo_m': d, 'alto_m': h}, 'medidas_fuente': fuente_medidas(fid, cat, w, d, h, vid),
              'orientacion': 'origen en el centro de la base; x = ancho, y = fondo, z = alto; frente hacia -y' + ('; vehículos: largo en x, frente hacia +x' if cat == VEHICULO_LARGO_X else ''),
              'parametros': {'ancho_m': 'cualquiera', 'fondo_m': 'cualquiera', 'alto_m': 'cualquiera', 'otros': sorted(set(FB.G[fid].__code__.co_varnames[3:FB.G[fid].__code__.co_argcount]))},
              'bbox_generado_m': [round(x, 4) for x in bb], 'diferencia_vs_tipico_m': dif, 'ajusta_a_medidas': ajusta,
              'colgado': COLGADOS.get(fid), 'base_m': round(mn[2], 4) if fid in COLGADOS else 0.0,
              'piezas': len(pz), 'tipos_de_pieza': tipos, 'anclajes_m': anclajes(pz), 'estados': est,
              'color_guia': 'solo para ver la forma; no es color de molde',
              'color_molde': None, 'color_molde_regla': 'lo pone la ficha del objeto en el canal (config del canal); la biblioteca no fija colores de molde',
              'origen': 'generado por código (formas_biblioteca.py, código propio de Star; sin descargas, sin IA, US$0)', 'licencia': 'propia de Star',
              'equivale_a_biblioteca_objetos': vid}
        fichas.append(fi)
    return fichas, errores

def estado_piezas(pz, estado):
    """aplica un estado genérico a las piezas de una forma (mismas operaciones que usará la ficha del escenario)."""
    if estado == 'roto': return FD.fragmentar(pz, {'trozos': 3, 'separacion_m': 0.06, 'angulo_max_grados': 15, 'caida': 'al_piso', 'semilla': 3})
    if estado == 'deformado': return FD.deformar(pz, {'modo': 'curvar', 'amplitud_m': max(0.03, 0.08 * max(FD.bbox(pz)[1][2], 0.3)), 'segmentos': 6})
    if estado == 'flotando': return FD.girar(FD.desplazar(pz, [0, 0, 0.35]), [0, 12, 8])
    if estado == 'volcado': return FD.girar(pz, [90, 0, 0])
    return pz

def escena_items(items, sal, nombre, por_fila=8, res=(480, 360)):
    """items = [(instancia_id, nombre_visible, piezas_internas)]; grilla + una vista perspectiva por item mirando a su centro."""
    obj_dir = os.path.join(sal, 'objetos_' + nombre); os.makedirs(obj_dir, exist_ok=True)
    objs, vistas, x, y, fila_max, col = [], [], 0.0, 0.0, 0.0, 0
    for iid, nom, pz in items:
        mn, mx = FD.bbox(pz); bb = [mx[i] - mn[i] for i in range(3)]
        hueco = max(bb[0], bb[1], 1.0) + 2.5
        if col == por_fila: x = 0.0; y += fila_max; fila_max = 0.0; col = 0
        pz2 = FD.desplazar(pz, [-((mn[0] + mx[0]) / 2), -((mn[1] + mx[1]) / 2), -mn[2]])
        piezas = [FD.a_blender(p, f"{iid}_{i:03d}", None) for i, p in enumerate(pz2)]
        for q in piezas: q.setdefault('color_rgb', [0.6, 0.6, 0.6])
        o = {'id': 'F_' + iid, 'nombre': nom, 'nombre_en': nom, 'forma': 'compuesta',
             'medidas': {'ancho_m': round(bb[0], 4), 'fondo_m': round(bb[1], 4), 'alto_m': round(bb[2], 4), 'base_m': 0.0},
             'color_rgb': [0.6, 0.6, 0.6], 'pieza_blender': {'piezas': piezas, 'prefijo': iid}}
        json.dump(o, open(os.path.join(obj_dir, o['id'] + '.json'), 'w', encoding='utf-8'), ensure_ascii=False)
        cx, cy = x + hueco / 2, y + hueco / 2
        objs.append({'objeto_id': o['id'], 'instancia_id': iid, 'pos_m': [round(cx, 3), round(cy, 3)], 'estado': 'normal', 'etiqueta': iid})
        R = max(bb); dist = max(0.3, R * 1.75); zc = bb[2] / 2
        vistas.append({'nombre': iid, 'tipo': 'perspectiva', 'pos_m': [round(cx - dist * 0.55, 3), round(cy - dist * 0.72, 3), round(zc + dist * 0.42, 3)],
                       'mirar_a_m': [round(cx, 3), round(cy, 3), round(zc, 3)], 'lente_mm': 35})
        x += hueco; fila_max = max(fila_max, hueco); col += 1
    W = max(o_['pos_m'][0] for o_ in objs) + 15; D = y + fila_max + 15; c = [round(W / 2 - 7.5, 2), round(D / 2 - 7.5, 2)]
    esc = {'id': nombre, 'tolerancia_m': 0.01,
           'piso': {'ancho_m': round(W, 1), 'fondo_m': round(D, 1), 'centro_m': c, 'espesor_m': 0.02, 'color_rgb': [0.86, 0.86, 0.84], 'estado': 'normal', 'etiqueta': 'piso'},
           'limites': [], 'cielo': {'hay_cielo': True, 'color_rgb': [0.94, 0.95, 0.97], 'nota': 'fondo claro de la hoja de contacto de la biblioteca (no es clima de ninguna escena)'}, 'objetos': objs,
           'camara_guia': {'resolucion': list(res), 'vistas': vistas}}
    p = os.path.join(sal, nombre + '.json'); json.dump(esc, open(p, 'w', encoding='utf-8'), ensure_ascii=False, indent=1); return p, obj_dir

MUESTRA_ESTADOS = ['silla', 'mesa_patas', 'estanteria', 'puerta', 'auto_sedan', 'farola', 'arbol_frondoso', 'muro', 'barril', 'televisor', 'escalera_recta', 'lampara_pie']

if __name__ == '__main__':
    fichas, errores = main()
    viejo_formas = {}
    for o in viejo.values(): viejo_formas[o.get('forma')] = viejo_formas.get(o.get('forma'), 0) + 1
    res = {'version': 1, 'nombre': 'biblioteca de formas paramétricas (genérica, sin canal)', 'generado_por': 'construir_biblioteca.py',
           'antes': {'biblioteca_objetos_json': len(viejo), 'por_forma': viejo_formas, 'tipos_de_parte_formas_detalle': 8},
           'ahora': {'formas': len(fichas), 'tipos_de_parte_formas_detalle': len(FD.PARTES), 'partes': list(FD.PARTES)},
           'errores': errores, 'fichas': fichas}
    out = os.path.join(AQUI, 'biblioteca_formas.json'); json.dump(res, open(out, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    malas = [f['id'] for f in fichas if not f['ajusta_a_medidas']]
    print('formas', len(fichas), 'errores', len(errores), 'no_ajustan', len(malas), malas)
    for e in errores: print(e['id'], e['error'][-300:])
    if '--escena' in sys.argv:
        os.makedirs(SAL, exist_ok=True)
        it = [(f['id'], f['nombre_generico'], piezas_de(f['id'], f['medidas_tipicas']['ancho_m'], f['medidas_tipicas']['fondo_m'], f['medidas_tipicas']['alto_m'])) for f in fichas]
        print(escena_items(it, SAL, 'hoja_biblioteca'))
        ids = {f['id']: f for f in fichas}; it2 = []
        for fid in [m for m in MUESTRA_ESTADOS if m in ids]:
            m = ids[fid]['medidas_tipicas']; pz = piezas_de(fid, m['ancho_m'], m['fondo_m'], m['alto_m'])
            for e in ('intacto', 'roto', 'deformado', 'flotando', 'volcado'):
                if e == 'deformado' and not ids[fid]['estados']['deformado']['admite']: continue
                it2.append((f'{fid}__{e}', f'{fid} {e}', estado_piezas(pz, e)))
        print(escena_items(it2, SAL, 'hoja_estados', por_fila=5))
