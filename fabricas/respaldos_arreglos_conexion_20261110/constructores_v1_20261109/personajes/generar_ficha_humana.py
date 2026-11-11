# -*- coding: utf-8 -*-
"""generar_ficha_humana.py — constructores_v1_20261109 (fábrica de personajes, plantilla bipedo_humano). US$0, sin IA.

Arma la FICHA DE ESQUELETO v1 de un personaje humano SOLO desde datos sellados (genérico: cualquier canal, cualquier id):
  - ADN Ako sellado (cubo_fijo/adn/<id>_ako.json): bloque 1 «Estatura en metros» (o «N.NN m») y «Proporción en cabezas»,
    bloque 2 piel/ojos/cabello/accesorios, bloque 4 vestuario (colores en orden, calzado, emblema, luces).
  - Sello del cubo (cubo_fijo/personajes/<id>.json): altura_m oficial y tipo.
  - Tabla del canal (trabajo/biblioteca/<canal>/personajes/personajes.json): altura_m oficial.
Regla de altura (fase 2, cubo_fijo_v2): manda el ADN; todas las fuentes deben coincidir ±2 %; si falta → STOP (exit 2);
si chocan → STOP (exit 3). No es humano → exit 4 (va por la ruta Argon, no por plantilla).
Rig: J_Bip_* de Star adaptado a roles del validador (el mismo que salió para Valentina el 9-nov); la proporción en cabezas
reescala el bloque cabeza+cuello y el cuerpo, todo en fracción de altura (punto más alto = 1). Con 4,5 cabezas el rig es
idéntico al de Valentina.
Uso: python3 generar_ficha_humana.py --adn A.json --sello S.json --tabla T.json --canal C --id ID --salida DIR
Salida: DIR/ficha_esqueleto.json + DIR/ficha_informe.json. Imprime una línea JSON."""
from __future__ import annotations
import argparse, copy, hashlib, json, re, sys, unicodedata
from datetime import datetime
from pathlib import Path

TOL = 0.02
HEADS_BASE = 4.5        # proporción de la plantilla
Z_CUELLO = 0.72         # inicio del bloque cabeza+cuello en la plantilla (fracción de altura)

# ---- tabla de color texto → hex (frase más larga gana). Misma tabla que dio los hex de Valentina (9-nov). ----
COLORES = {
    'piel morena calida': '#C68642', 'piel morena': '#C68642', 'piel trigueña': '#D2A06D', 'piel trigueña clara': '#E0B285',
    'piel clara': '#F1C27D', 'piel blanca': '#FFDBAC', 'piel rosada': '#F5C6A5', 'piel oscura': '#8D5524', 'piel negra': '#6B4226',
    'piel canela': '#C68C53', 'piel morena oscura': '#8D5524', 'piel aceitunada': '#C9A26B', 'piel bronceada': '#C68642',
    'magenta': '#C2185B', 'purpura oscuro': '#4A148C', 'morado oscuro': '#4A148C', 'purpura': '#6A1B9A', 'morado': '#6A1B9A',
    'violeta': '#7B1FA2', 'lila': '#B39DDB', 'rosa neon': '#FF4081', 'rosa': '#F48FB1', 'rosado': '#F48FB1', 'fucsia': '#E91E63',
    'rojo': '#E53935', 'rojo oscuro': '#B71C1C', 'granate': '#880E4F', 'vino': '#7B1F2B', 'naranja': '#FB8C00', 'anaranjado': '#FB8C00',
    'amarillo': '#FDD835', 'dorado': '#D4AF37', 'mostaza': '#C9A227', 'ocre': '#C9A227', 'crema': '#F2E2CE', 'beige': '#D7CCC8',
    'blanco': '#F5F5F5', 'gris claro': '#BDBDBD', 'gris': '#9E9E9E', 'gris oscuro': '#616161', 'plateado': '#C0C0C0', 'plata': '#C0C0C0',
    'negro': '#212121', 'azul marino': '#1F3A6B', 'azul oscuro': '#0D47A1', 'azul cobalto': '#2F5FC4', 'azul electrico': '#2979FF',
    'azul cielo': '#7EB6E6', 'azul claro': '#64B5F6', 'azul': '#1E88E5', 'celeste': '#4FC3F7', 'turquesa': '#26C6DA', 'cian': '#00BCD4',
    'verde oscuro': '#1B5E20', 'verde lima': '#C0CA33', 'verde menta': '#98D8C8', 'verde': '#43A047', 'oliva': '#808000',
    'marron oscuro': '#3E2723', 'cafe oscuro': '#3E2723', 'marron': '#6D4C41', 'cafe': '#6D4C41', 'chocolate': '#5D4037',
    'castaño muy oscuro': '#1A0F0A', 'castaño oscuro': '#3B2416', 'castaño claro': '#8D6E63', 'castaño': '#5D4037',
    'rubio': '#E6C27A', 'pelirrojo': '#B5472E', 'cobrizo': '#B87333', 'canoso': '#D0D0D0', 'azabache': '#0B0B0B',
}
COLORES_N = {}
def _n(s):
    s = unicodedata.normalize('NFD', s.lower())
    return ''.join(c for c in s if unicodedata.category(c) != 'Mn' or c == '\u0303').replace('n\u0303', 'ñ')
for _k, _v in COLORES.items():
    COLORES_N[_n(_k)] = _v
# [color_genero 20261110] el ADN dice «capa morada», «lona roja», «pantalones blancos»: se aceptan femenino y plural
def _variantes(k):
    w = k.split(' ')
    if w[0] == 'piel': return []
    def pl(x): return x + 's' if x.endswith(('a', 'e', 'o')) else (x + 'es' if x.endswith(('l', 'n', 's', 'r')) else x)
    fem = [x[:-1] + 'a' if x.endswith('o') else x for x in w]
    return [' '.join(fem), ' '.join(pl(x) for x in w), ' '.join(pl(x) for x in fem)]
for _k, _v in list(COLORES_N.items()):
    for _var in _variantes(_k):
        if _var != _k: COLORES_N.setdefault(_var, _v)
HEX = re.compile(r'#[0-9A-Fa-f]{6}\b')

def color_en(texto, prefijo=''):
    """Primer color del texto (frase más larga en la posición más temprana). prefijo='piel ' para piel."""
    t = _n(texto)
    mejor = None
    for k, v in COLORES_N.items():
        if prefijo and not k.startswith(prefijo):
            continue
        if not prefijo and k.startswith('piel '):
            continue
        for m in re.finditer(r'\b' + re.escape(k) + r'\b', t):
            cand = (m.start(), -len(k), v, k)
            if mejor is None or cand < mejor:
                mejor = cand
            break
    return (mejor[2], mejor[3]) if mejor else (None, None)

def colores_en_orden(texto):
    t = _n(texto); out = []; i = 0
    while True:
        best = None
        for k, v in COLORES_N.items():
            if k.startswith('piel '): continue
            m = re.compile(r'\b' + re.escape(k) + r'\b').search(t, i)
            if m and (best is None or (m.start(), -len(k)) < (best[0], -len(best[1]))):
                best = (m.start(), k, v)
        if not best: return out
        out.append((best[2], best[1])); i = best[0] + len(best[1])

def frase(texto, clave, n=160):
    """Fragmento del texto desde la palabra clave (para buscar su color)."""
    t = _n(texto); m = re.search(clave, t)
    return t[m.start(): m.start() + n] if m else ''

def tono(hexc, f=(0.85, 0.80, 1.05)):
    h = hexc.lstrip('#'); c = [int(h[i:i + 2], 16) for i in (0, 2, 4)]
    return '#' + ''.join(f'{max(0, min(255, int(c[i] * f[i]))):02X}' for i in range(3))

def color_cerca(texto, clave, n=60, prefijo=''):
    """Color dicho cerca de CADA aparición de la palabra clave (la primera que traiga color gana)."""
    t = _n(texto)
    for m in re.finditer(clave, t):
        h, k = color_en(t[m.start(): m.start() + n], prefijo)
        if h: return h, k
    return None, None

def num(s): return float(s.replace(',', '.'))

def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def altura_tabla(tabla, pid):
    if not tabla: return None, None
    corto = pid[4:] if pid.startswith('gdc-') else pid
    for p in tabla.get('personajes') or []:
        if p.get('id') in (pid, corto) or pid in (p.get('ids_mapa') or []):
            return p.get('altura_m'), p.get('id')
    return None, None

def lim(x0, x1, y0, y1, z0, z1): return {'x': [x0, x1], 'y': [y0, y1], 'z': [z0, z1]}
def hueso(nombre, padre, cabeza, cola, rol, lado, limites, funcion):
    return {'nombre': nombre, 'padre': padre, 'cabeza': cabeza, 'cola': cola, 'rol': rol, 'lado': lado, 'limites_deg': limites, 'funcion': funcion}
def espejo_h(h):
    m = copy.deepcopy(h)
    m['nombre'] = h['nombre'][:-1] + ('R' if h['nombre'].endswith('_L') else 'L')
    m['lado'] = 'R' if h['lado'] == 'L' else 'L'
    m['cabeza'] = [-h['cabeza'][0], h['cabeza'][1], h['cabeza'][2]]
    m['cola'] = [-h['cola'][0], h['cola'][1], h['cola'][2]]
    if h['padre'] and h['padre'].endswith('_L'): m['padre'] = h['padre'][:-1] + 'R'
    lx = h['limites_deg']
    m['limites_deg'] = {'x': list(lx['x']), 'y': [-lx['y'][1], -lx['y'][0]], 'z': [-lx['z'][1], -lx['z'][0]]}
    return m
def pieza_libre(nombre, hueso_, prim, centro, radios, color, rot=None):
    return {'nombre': nombre, 'hueso': hueso_, 'primitiva': prim, 'modo': 'libre', 'centro': centro, 'radios': radios,
            'rotacion_deg': rot or [0, 0, 0], 'color': color}
def pieza_hueso(nombre, hueso_, prim, radio, color):
    return {'nombre': nombre, 'hueso': hueso_, 'primitiva': prim, 'modo': 'hueso', 'radio': radio, 'color': color}

class Remap:
    """Reescala la plantilla (4,5 cabezas) a N cabezas: bloque cabeza+cuello ×k, cuerpo comprimido para que el tope siga en 1."""
    def __init__(self, cabezas):
        self.k = HEADS_BASE / float(cabezas)
        self.top_body = 1 - (1 - Z_CUELLO) * self.k
        self.b = self.top_body / Z_CUELLO
        self.wb = self.b ** 0.5
    def r(self, x): return round(x, 5)
    def p(self, v, cabeza=None):
        x, y, z = v
        if cabeza is None: cabeza = z > Z_CUELLO + 1e-9
        if cabeza:
            return [self.r(x * self.k), self.r(y * self.k), self.r(self.top_body + (z - Z_CUELLO) * self.k)]
        return [self.r(x * self.wb), self.r(y * self.wb), self.r(z * self.b)]
    def rad(self, v, cabeza):
        if isinstance(v, list):
            return [self.r(v[0] * (self.k if cabeza else self.wb)), self.r(v[1] * (self.k if cabeza else self.wb)), self.r(v[2] * (self.k if cabeza else self.b))]
        return self.r(v * (self.k if cabeza else self.wb))

HUESOS_CABEZA = {'cuello', 'cabeza'}

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--adn', required=True); ap.add_argument('--sello', required=True); ap.add_argument('--tabla')
    ap.add_argument('--canal', required=True); ap.add_argument('--id', required=True); ap.add_argument('--salida', required=True)
    a = ap.parse_args()
    sal = Path(a.salida); sal.mkdir(parents=True, exist_ok=True)
    inf = {'id': a.id, 'canal': a.canal, 'programa': 'generar_ficha_humana.py constructores_v1_20261109', 'gasto_usd': 0,
           'fuentes': {}, 'estado': None}
    def fin(estado, code, **kw):
        inf.update(estado=estado, **kw)
        (sal / 'ficha_informe.json').write_text(json.dumps(inf, ensure_ascii=False, indent=1), encoding='utf-8')
        print(json.dumps({'estado': estado, **{k: inf.get(k) for k in ('altura_m', 'cabezas', 'n_huesos', 'n_piezas', 'motivo')}}, ensure_ascii=False))
        sys.exit(code)
    sello = json.loads(Path(a.sello).read_text(encoding='utf-8')); inf['fuentes']['sello'] = {'ruta': a.sello, 'sha256': sha(a.sello)}
    raw = Path(a.adn).read_text(encoding='utf-8'); inf['fuentes']['adn'] = {'ruta': a.adn, 'sha256': sha(a.adn)}
    try:
        adn = json.loads(raw)
    except ValueError:   # ADN en texto (salida sello_pago): bloques «1. …» a «5. …»; se exige que el sello del cubo esté PASS
        partes = re.split(r'(?m)^[ \t>#*_\-]*([1-5])[.)]', raw)
        bl = [{'n': int(partes[i]), 'titulo': '', 'texto': partes[i + 1].strip()} for i in range(1, len(partes) - 1, 2)]
        adn = {'status': 'PASS_SELLABLE' if sello.get('sellado') and len(bl) >= 4 else 'TEXTO_SIN_SELLO', 'bloques': bl, 'texto': raw}
    tabla = json.loads(Path(a.tabla).read_text(encoding='utf-8')) if a.tabla and Path(a.tabla).is_file() else None
    if tabla: inf['fuentes']['tabla'] = {'ruta': a.tabla, 'sha256': sha(a.tabla)}
    if adn.get('status') != 'PASS_SELLABLE': fin('STOP_ADN_NO_SELLADO', 2, motivo=f"ADN status {adn.get('status')}")
    if sello.get('canal') and sello['canal'] != a.canal: fin('STOP_CANAL_DISTINTO', 2, motivo=f"sello canal {sello.get('canal')}")
    B = {b['n']: b['texto'] for b in adn.get('bloques') or []}
    b1, b2, b4 = B.get(1, ''), B.get(2, ''), B.get(4, '')
    todo = adn.get('texto') or '\n'.join(B.values())
    # ---- tipo: solo humanos por plantilla ----
    tipo = (sello.get('tipo') or '').lower()
    no_humano = re.search(r'\b(ave|pollito|polluelo|perro|gato|animal|cuadr[uú]pedo|robot|criatura|alien|monstruo|dinosaurio|insecto|pez)\b', _n(b1))
    if tipo not in ('persona', 'humano', 'humana') or no_humano:
        fin('NO_HUMANO_RUTA_ARGON', 4, motivo=f"tipo={tipo!r} ({no_humano.group(0) if no_humano else 'sello no es persona'}): ficha no humana va por investigación Argon (pagada, aparte)")
    # ---- altura (manda el ADN) ----
    mh = re.search(r'Estatura en metros\W*:?\W*([0-9]+(?:[.,][0-9]+)?)\s*m\b', b1, re.I) or re.search(r'\b([0-9]+[.,][0-9]+)\s*m\b', b1)
    mc = re.search(r'Proporci[oó]n en cabezas\W*:?\W*([0-9]+(?:[.,][0-9]+)?)', b1, re.I) or re.search(r'([0-9]+(?:[.,][0-9]+)?)\s*cabezas', b1, re.I)
    h_adn = num(mh.group(1)) if mh else None
    cabezas = num(mc.group(1)) if mc else None
    h_sello = sello.get('altura_m')
    h_tabla, id_tabla = altura_tabla(tabla, a.id)
    fuentes_h = {'adn': h_adn, 'sello_cubo_fijo': h_sello, 'tabla_canal': h_tabla}
    inf['alturas'] = fuentes_h
    if h_adn is None:
        # El ADN no trae metros: solo se acepta si el sello del cubo Y la tabla del canal traen la MISMA altura (±2 %),
        # p. ej. Don Caos 0,18 m (orden de Ricardo 2-nov-2026 en el sello). Si falta una de las dos o no coinciden → STOP.
        if h_sello is not None and h_tabla is not None and abs(float(h_tabla) / float(h_sello) - 1) <= TOL:
            h_adn = float(h_sello); inf['altura_fuente'] = 'sello_cubo_fijo+tabla_canal (ADN sin metros)'
            inf.setdefault('avisos', []).append(f'ADN sin estatura en metros: se usa {h_adn} m del sello del cubo, confirmada por la tabla del canal')
        else:
            fin('STOP_FALTA_DATO', 2, motivo='ADN sin estatura en metros (bloque 1) y sello/tabla no la confirman juntos')
    if cabezas is None: fin('STOP_FALTA_DATO', 2, motivo='ADN sin proporción en cabezas (bloque 1)')
    conflictos = {k: v for k, v in fuentes_h.items() if v is not None and abs(float(v) / h_adn - 1) > TOL}
    if conflictos: fin('STOP_CONFLICTO', 3, motivo=f'alturas no coinciden ±2 % con el ADN {h_adn}: {conflictos}')
    if not (1.5 <= cabezas <= 9): fin('STOP_FALTA_DATO', 2, motivo=f'proporción en cabezas fuera de rango humano: {cabezas}')
    # ---- colores (hex del ADN si vienen; si no, tabla de texto) ----
    hexes = HEX.findall(todo); vacios = []; col_fuente = {}
    def slot(nombre, texto, clave, prefijo='', defecto=None):
        h, k = color_cerca(texto, clave, 70, prefijo)
        if h: col_fuente[nombre] = f'texto ADN «{k}»'; return h
        col_fuente[nombre] = f'VACÍO → {defecto}'; vacios.append(f'color {nombre}: el ADN no lo dice; se usa {defecto}'); return defecto
    PIEL = slot('piel', b2 + ' ' + b1, r'piel', 'piel ', '#E0AC69')
    CABELLO = slot('cabello', b2 + ' ' + b1, r'cabello|pelo', '', '#3B2416')
    OJOS = slot('ojos', b2 + ' ' + b1, r'iris|ojos', '', '#3E2723')
    ropa = colores_en_orden(b4)
    TRAJE_1 = ropa[0][0] if ropa else '#5B9BD5'
    TRAJE_2 = next((h for h, k in ropa if h != TRAJE_1), tono(TRAJE_1, (0.6, 0.6, 0.6)))
    col_fuente['traje_primario'] = f'vestuario 1.er color «{ropa[0][1]}»' if ropa else 'VACÍO'
    col_fuente['traje_secundario'] = next((f'vestuario 2.º color «{k}»' for h, k in ropa if h != TRAJE_1), 'derivado del primario')
    # [color_genero 20261110] mangas y prenda inferior: si el ADN dice su color, manda ese
    t_man = frase(b4, r'mangas?\b', 60)
    BRAZOS = color_en(t_man)[0] or TRAJE_2
    col_fuente['brazos'] = f'mangas «{color_en(t_man)[1]}»' if color_en(t_man)[0] else 'secundario'
    # piernas: color de la prenda inferior si el ADN lo dice; si no, el secundario (como antes)
    t_inf = frase(b4, r'prenda inferior|pantalon|falda|short|bermuda|leggin|mallas', 140)
    PIERNAS = color_en(t_inf)[0] or TRAJE_2
    col_fuente['piernas'] = f'prenda inferior «{color_en(t_inf)[1]}»' if color_en(t_inf)[0] else 'secundario'
    t_calz = frase(b4, r'calzado|botas|zapatos|zapatillas|tenis|sandalias|pantuflas', 200)
    m_col = re.search(r'\bcolor\s+([a-zñ ]+)', t_calz)
    CALZADO = (color_en(m_col.group(0))[0] if m_col else None) or color_en(t_calz)[0] or TRAJE_1
    col_fuente['calzado'] = 'texto calzado' if t_calz else 'VACÍO → traje'
    CASCO = color_cerca(b2 + ' ' + b4, r'casco', 50)[0] if re.search(r'casco', _n(b2 + b4)) else None
    if re.search(r'casco', _n(b2 + b4)) and not CASCO: CASCO = TRAJE_2; vacios.append('color casco: el ADN no lo dice; se usa el traje secundario')
    m_emb = next((m for m in (re.search(r'(corazon|estrella|rayo|atomo)', _n(b4)), re.search(r'(insignia|emblema|logo)', _n(b4))) if m), None)
    EMBLEMA = color_cerca(b4, m_emb.group(1), 40)[0] if m_emb else None
    NEON = None
    m_neon = re.search(r'(neon|emisiv|luminos|brillant|ilumina)', _n(b4))
    if m_neon:
        NEON = next((h for h, k in colores_en_orden(b4) if 'neon' in k), None) or color_en(frase(b4, m_neon.group(0), 80))[0]
    NARIZ = tono(PIEL)
    if hexes: vacios.append(f'el ADN trae hex {sorted(set(hexes))}: revisar asignación (la plantilla usa el texto)')
    else: vacios.append('ADN no trae hex: colores deducidos del texto con la tabla fija de generar_ficha_humana.py')
    # ---- rig (plantilla J_Bip_* de Star, roles del validador) ----
    R = Remap(cabezas)
    H = []
    def hb(nombre, padre, c, t, rol, lado, limites, funcion):
        cab = nombre in HUESOS_CABEZA
        H.append(hueso(nombre, padre, R.p(c, cab or None), R.p(t, cab or None), rol, lado, limites, funcion))
    hb('raiz', None, [0, 0, 0], [0, 0, 0.04], 'raiz', 'C', lim(0, 0, 0, 0, -135, 135), 'ancla en el suelo')
    hb('cadera', 'raiz', [0, 0, 0.48], [0, 0, 0.52], 'cadera', 'C', lim(-40, 40, -25, 25, -45, 45), 'pelvis; pivote de piernas y torso')
    hb('columna', 'cadera', [0, 0, 0.52], [0, 0, 0.62], 'columna', 'C', lim(-30, 35, -20, 20, -40, 40), 'lumbar / abdomen')
    hb('pecho', 'columna', [0, 0, 0.62], [0, 0, 0.72], 'pecho', 'C', lim(-25, 30, -20, 20, -35, 35), 'tórax')
    hb('cuello', 'pecho', [0, 0, 0.72], [0, 0, 0.78], 'cuello', 'C', lim(-35, 35, -30, 30, -60, 60), 'cuello')
    hb('cabeza', 'cuello', [0, 0, 0.78], [0, 0, 0.96], 'cabeza', 'C', lim(-35, 35, -30, 30, -70, 70), f'cráneo (~{round(100 / cabezas)} % de la altura, {cabezas:g} cabezas)')
    hb('hombro_L', 'pecho', [0.02, 0, 0.70], [0.10, 0, 0.70], 'hombro', 'L', lim(-40, 40, -50, 80, -40, 40), 'clavícula / hombro')
    hb('brazo_L', 'hombro_L', [0.10, 0, 0.70], [0.14, 0.02, 0.52], 'brazo', 'L', lim(-80, 170, -70, 70, -60, 90), 'húmero; flexión X hasta ~170°')
    hb('antebrazo_L', 'brazo_L', [0.14, 0.02, 0.52], [0.15, 0.02, 0.34], 'antebrazo', 'L', lim(-10, 140, -20, 20, -80, 80), 'cúbito/radio; flexión de codo en X')
    hb('mano_L', 'antebrazo_L', [0.15, 0.02, 0.34], [0.16, 0.02, 0.28], 'mano', 'L', lim(-40, 40, -30, 30, -40, 40), 'mano (sin dedos; detalle lo pone Nano Banana)')
    hb('femur_L', 'cadera', [0.06, 0, 0.48], [0.06, 0, 0.26], 'pierna', 'L', lim(-110, 30, -30, 30, -35, 35), 'fémur; −X = adelante (−Y)')
    hb('tibia_L', 'femur_L', [0.06, 0, 0.26], [0.06, 0, 0.055], 'pierna', 'L', lim(-20, 140, -15, 15, -20, 20), 'tibia; flexión de rodilla')
    hb('pie_L', 'tibia_L', [0.06, 0.01, 0.055], [0.06, -0.08, 0.02], 'pie', 'L', lim(-35, 45, -20, 20, -30, 30), 'pie / calzado')
    for n in ('hombro_L', 'brazo_L', 'antebrazo_L', 'mano_L', 'femur_L', 'tibia_L', 'pie_L'):
        H.append(espejo_h(next(h for h in H if h['nombre'] == n)))
    P = []
    def pl(nombre, hueso_, prim, centro, radios, color, rot=None):
        cab = hueso_ in HUESOS_CABEZA
        P.append(pieza_libre(nombre, hueso_, prim, R.p(centro, cab), R.rad(radios, cab), color, rot))
    def ph(nombre, hueso_, prim, radio, color):
        P.append(pieza_hueso(nombre, hueso_, prim, R.rad(radio, hueso_ in HUESOS_CABEZA), color))
    pl('cadera_mesh', 'cadera', 'esfera', [0, 0, 0.50], [0.10, 0.08, 0.07], PIERNAS)
    pl('torso', 'columna', 'caja', [0, 0, 0.58], [0.09, 0.06, 0.07], TRAJE_1)
    pl('pecho_mesh', 'pecho', 'caja', [0, 0, 0.67], [0.10, 0.07, 0.06], TRAJE_1)
    if m_emb and EMBLEMA: pl('corazon' if m_emb.group(1) == 'corazon' else 'emblema', 'pecho', 'esfera', [0, -0.07, 0.66], [0.035, 0.02, 0.03], EMBLEMA)
    ph('cuello_mesh', 'cuello', 'cilindro', 0.035, PIEL)
    pl('cabeza_mesh', 'cabeza', 'esfera', [0, 0, 0.88], [0.11, 0.10, 0.12], PIEL)
    if CASCO:
        pl('casco', 'cabeza', 'esfera', [0, 0.01, 0.92], [0.125, 0.115, 0.10], CASCO)
        if re.search(r'orejera', _n(b2 + b4)):
            pl('casco_oreja_L', 'cabeza', 'cilindro', [0.12, 0, 0.88], [0.04, 0.04, 0.03], CASCO, [90, 0, 0])
            pl('casco_oreja_R', 'cabeza', 'cilindro', [-0.12, 0, 0.88], [0.04, 0.04, 0.03], CASCO, [90, 0, 0])
    elif re.search(r'\b(gorra|sombrero|gorro|boina)\b', _n(b2 + b4)):
        g = re.search(r'\b(gorra|sombrero|gorro|boina)\b', _n(b2 + b4)).group(1)
        pl(g, 'cabeza', 'esfera', [0, 0.01, 0.95], [0.12, 0.115, 0.06], color_en(frase(b2 + ' ' + b4, g, 60))[0] or TRAJE_1)
    calvo = re.search(r'\b(calvo|calva|rapad[oa]|sin cabello|sin pelo)\b', _n(b2))
    if not calvo:
        pl('cabello', 'cabeza', 'esfera', [0, 0.06, 0.86], [0.10, 0.12, 0.14], CABELLO)
        if re.search(r'(media espalda|espalda|largo|larga|cola de caballo|coleta|trenza|melena)', _n(frase(b2, r'cabello|pelo', 220))):
            pl('cabello_cola', 'cabeza', 'cono', [0, 0.10, 0.70], [0.08, 0.08, 0.16], CABELLO, [20, 0, 0])
    calz = re.search(r'\b(botas|bota|zapatos|zapatillas|tenis|sandalias|pantuflas)\b', _n(b4))
    nc = 'bota' if (not calz or calz.group(1).startswith('bota')) else 'zapato'
    for lado, sx in (('L', 1), ('R', -1)):
        ph(f'brazo_sup_{lado}', f'brazo_{lado}', 'capsula', 0.035, BRAZOS)
        ph(f'brazo_inf_{lado}', f'antebrazo_{lado}', 'capsula', 0.030, TRAJE_1)
        pl(f'mano_{lado}', f'mano_{lado}', 'esfera', [sx * 0.155, 0.02, 0.30], [0.035, 0.03, 0.035], TRAJE_1 if re.search(r'guantes', _n(b4)) else PIEL)
        ph(f'muslo_{lado}', f'femur_{lado}', 'capsula', 0.045, PIERNAS)
        ph(f'pierna_{lado}', f'tibia_{lado}', 'capsula', 0.038, PIERNAS)
        pl(f'{nc}_{lado}', f'pie_{lado}', 'caja', [sx * 0.06, -0.03, 0.03], [0.04, 0.07, 0.03], CALZADO)
    if NEON: pl('neon_pecho', 'pecho', 'caja', [0, -0.075, 0.67], [0.08, 0.008, 0.01], NEON)
    rostro = {'hueso': 'cabeza', 'ojos': {'centro_L': R.p([0.045, -0.09, 0.90], True), 'radio': R.rad(0.022, True)},
              'nariz': {'centro': R.p([0.0, -0.11, 0.86], True), 'radio': R.rad(0.015, True), 'primitiva': 'esfera', 'color': NARIZ,
                        'nota': 'solo marca de mirada (detalle lo pone Nano Banana)'}}
    poses = {'de_pie': {},
             'caminar': {'femur_L': [-35, 0, 0], 'tibia_L': [25, 0, 0], 'pie_L': [-10, 0, 0], 'femur_R': [20, 0, 0], 'tibia_R': [10, 0, 0],
                         'brazo_L': [25, -10, -15], 'brazo_R': [-25, 10, 15], 'antebrazo_L': [30, 0, 0], 'antebrazo_R': [20, 0, 0]},
             'sentada': {'cadera': [8, 0, 0], 'columna': [-5, 0, 0], 'femur_L': [-78, 0, 6], 'tibia_L': [85, 0, 0], 'pie_L': [-12, 0, 0],
                         'femur_R': [-78, 0, -6], 'tibia_R': [85, 0, 0], 'pie_R': [-12, 0, 0], 'brazo_L': [25, -20, 15], 'brazo_R': [25, 20, -15],
                         'antebrazo_L': [40, 0, 0], 'antebrazo_R': [40, 0, 0]},
             'brazos_arriba': {'hombro_L': [0, 25, 0], 'hombro_R': [0, -25, 0], 'brazo_L': [160, -15, 0], 'brazo_R': [160, 15, 0],
                               'antebrazo_L': [15, 0, 0], 'antebrazo_R': [15, 0, 0]}}
    vacios += ['Sin dedos ni boca detallada (pedido Ricardo: solo ojos y nariz para la mirada; el detalle lo pone Nano Banana).',
               'Casco/cabello/calzado: geometría de plantilla según palabras del ADN, no de un plano métrico.',
               'Límites articulares: rangos cartoon del maniquí J_Bip_* de Star (~80 % AAOS), no medidos en el personaje.']
    nombre = sello.get('nombre') or a.id
    ficha = {'schema': 'ficha_esqueleto/v1', 'id': a.id, 'nombre': f'{nombre} — ficha humana desde ADN (plantilla)', 'plantilla': 'bipedo_humano',
             'es_ficticio': True, 'analogo_real': f'humano (Homo sapiens), {cabezas:g} cabezas de altura', 'altura_m': h_adn,
             'origen': {'tipo': 'plantilla', 'autor': 'generar_ficha_humana.py (fábrica personajes, constructores_v1_20261109), sin IA',
                        'fecha': datetime.now().astimezone().isoformat(timespec='seconds'),
                        'aviso': 'Ficha automática desde el ADN sellado + rig J_Bip_* de Star. NO Argon. US$0.'},
             'fuentes': [{'tipo': 'hoja_personaje', 'titulo': f'ADN Ako sellado {Path(a.adn).name}', 'url': None,
                          'afirma': (b1[:300] + ' … ' + b4[:300]).strip()},
                         {'tipo': 'hoja_personaje', 'titulo': f'sello cubo_fijo {Path(a.sello).name}', 'url': None,
                          'afirma': f"altura_m {h_sello}; nunca_cambia: {sello.get('nunca_cambia')}"},
                         {'tipo': 'conocimiento', 'titulo': 'maniqui_huesos.py Star (J_Bip_* humanoide)', 'url': None,
                          'afirma': 'esqueleto bípedo humano; ejes +Z arriba −Y frente'},
                         {'tipo': 'deduccion', 'titulo': 'Deducción para personaje ficticio humano (plantilla)', 'url': None,
                          'afirma': f'se toma el esqueleto humanoide de Star, se escala a {h_adn} m (ADN) y se ajusta a {cabezas:g} cabezas '
                                    '(bloque cabeza+cuello ×4,5/N, cuerpo comprimido para que el tope siga en 1); colores desde el texto del ADN; sin dedos'}],
             'huesos': H, 'piezas': P, 'rostro': rostro, 'poses_prueba': poses, 'vacios': vacios,
             'ids_mapa': sello.get('ids_canal') or [], 'colores_fuente': col_fuente,
             'adn_conflictos': {'altura_fuentes': fuentes_h}}
    (sal / 'ficha_esqueleto.json').write_text(json.dumps(ficha, ensure_ascii=False, indent=1), encoding='utf-8')
    fin('FICHA_OK', 0, altura_m=h_adn, cabezas=cabezas, n_huesos=len(H), n_piezas=len(P), colores=col_fuente,
        ficha=str(sal / 'ficha_esqueleto.json'))

if __name__ == '__main__':
    main()
