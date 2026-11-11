"""validador.py — Ficha de esqueleto v1 (MYIA · prototipo · CPU · US$0).

Valida una FICHA DE ESQUELETO (la que Argon devolvería, o una de EJEMPLO escrita a mano)
ANTES de que Blender la arme. No usa IA ni red. Sin dependencias externas.

Convenciones fijas (las mismas que el constructor Blender):
- Unidades: todas las coordenadas y medidas son FRACCIONES de altura_m (1.0 = altura total en reposo).
- Ejes del cuerpo en reposo: +Z arriba, -Y frente (hacia donde mira), +X = lado IZQUIERDO del personaje (L), -X = derecho (R).
- Suelo en z = 0. El punto más alto del cuerpo (piezas) debe quedar en z ≈ 1.0.
- Límites de giro en grados, en EJES DEL CUERPO aplicados en la cabeza del hueso:
    x = cabeceo/flexión (giro alrededor del eje lateral X), y = alabeo lateral (alrededor del eje frente-atrás Y),
    z = giro horizontal (alrededor del eje vertical Z). Orden de aplicación XYZ. 0 = reposo.
- Espejo L↔R (plano x=0): cabeza/cola con x negado; límite x igual; límites y, z negados e intercambiados.

Uso: python3 validador.py ficha.json [--json]
Salida: código 0 si APTA, 1 si RECHAZADA.
"""
from __future__ import annotations
import json, math, re, sys

SCHEMA = 'ficha_esqueleto/v1'
PLANTILLAS = ('bipedo_humano', 'ave', 'cuadrupedo', 'pez', 'serpiente', 'objeto_magico', 'otro')
ROLES = ('raiz', 'cadera', 'columna', 'pecho', 'cuello', 'cabeza', 'mandibula', 'pico', 'oreja', 'copete', 'cola',
         'hombro', 'brazo', 'antebrazo', 'mano', 'ala', 'pierna', 'pie', 'dedos', 'pata_delantera', 'pata_trasera',
         'aleta', 'otro')
PRIMITIVAS = ('esfera', 'capsula', 'cilindro', 'cono', 'caja', 'toro')
LADOS = ('C', 'L', 'R')
TIPOS_FUENTE = ('web', 'conocimiento', 'hoja_personaje', 'deduccion')
TIPOS_ORIGEN = ('EJEMPLO_MANUAL', 'argon', 'plantilla')   # [constructores_v1_20261109] + 'plantilla' = ficha automática desde ADN (generar_ficha_humana.py)
HEX = re.compile(r'^#[0-9A-Fa-f]{6}$')

# Mínimos anatómicos por plantilla: rol -> (lados, mínimo de huesos por lado)
MINIMOS = {
    'ave':           {'cabeza': ('C', 1), 'cuello': ('C', 1), 'cola': ('C', 1), 'ala': ('LR', 2), 'pierna': ('LR', 2)},
    'cuadrupedo':    {'cabeza': ('C', 1), 'cuello': ('C', 1), 'columna': ('C', 1),
                      'pata_delantera': ('LR', 3), 'pata_trasera': ('LR', 3)},
    'bipedo_humano': {'cabeza': ('C', 1), 'cuello': ('C', 1), 'columna': ('C', 1),
                      'brazo': ('LR', 1), 'antebrazo': ('LR', 1), 'pierna': ('LR', 2)},
    'pez':           {'cabeza': ('C', 1), 'columna': ('C', 2), 'cola': ('C', 1)},
    'serpiente':     {'cabeza': ('C', 1), 'columna': ('C', 4)},
}
ROLES_APOYO = ('pierna', 'pie', 'dedos', 'pata_delantera', 'pata_trasera')
TOL_ESPEJO = 0.01      # fracción de altura
TOL_SUELO = 0.03
LARGO_MIN, LARGO_MAX = 0.005, 1.2


ROLES_CADENA_ALA = ('brazo', 'antebrazo', 'mano', 'ala')
def cadena_ala(H, lado):
    """Ala de ave por PERTENENCIA a la cadena real del miembro anterior: huesos del mismo lado con rol brazo (húmero),
    antebrazo o mano/ala, unidos padre→hijo. Cuenta como ala la cadena que termina en un hueso rol 'ala', o la que
    tiene brazo → antebrazo → mano en ese orden. Devuelve la cadena más larga (nombres de raíz a punta) o []."""
    mejor = []
    for n, h in H.items():
        if h.get('lado') != lado or h.get('rol') not in ('ala', 'mano'):
            continue
        cad = [n]; p = h.get('padre')
        while p in H and H[p].get('lado') == lado and H[p].get('rol') in ROLES_CADENA_ALA and p not in cad:
            cad.insert(0, p); p = H[p].get('padre')
        roles = [H[x].get('rol') for x in cad]
        ok = roles[-1] == 'ala' or ('brazo' in roles and 'antebrazo' in roles and roles.index('brazo') < roles.index('antebrazo') < len(roles) - 1)
        if ok and len(cad) > len(mejor):
            mejor = cad
    return mejor


class Informe:
    def __init__(self):
        self.errores, self.avisos = [], []

    def err(self, cod, msg):
        self.errores.append({'codigo': cod, 'detalle': msg})

    def av(self, cod, msg):
        self.avisos.append({'codigo': cod, 'detalle': msg})

    @property
    def apta(self):
        return not self.errores

    def dict(self):
        return {'apta': self.apta, 'errores': self.errores, 'avisos': self.avisos}


def _vec(v, n=3):
    return isinstance(v, list) and len(v) == n and all(isinstance(x, (int, float)) and math.isfinite(x) for x in v)


def _dist(a, b):
    return math.sqrt(sum((x - y) ** 2 for x, y in zip(a, b)))


def espejo_nombre(n):
    for a, b in (('_L', '_R'), ('_R', '_L')):
        if n.endswith(a):
            return n[:-2] + b
    return None


def espejo_limites(lim):
    """Límites del lado opuesto: x igual; y, z negados e intercambiados."""
    return {'x': list(lim['x']), 'y': [-lim['y'][1], -lim['y'][0]], 'z': [-lim['z'][1], -lim['z'][0]]}


def _bbox_pieza(p, huesos):
    """Caja envolvente conservadora (fracción de altura) de una pieza."""
    if p.get('modo') == 'hueso':
        h = huesos[p['hueso']]
        r = p['radio']
        pts = [h['cabeza'], h['cola']]
        return [min(q[i] for q in pts) - r for i in range(3)], [max(q[i] for q in pts) + r for i in range(3)]
    c, rad = p['centro'], p['radios']
    rmax = max(rad) if any(abs(a) > 1e-9 for a in p.get('rotacion_deg', [0, 0, 0])) else None
    if p['primitiva'] == 'toro':
        rmax = rad[0] + rad[2] if rmax is None else max(rmax, rad[0] + rad[2])
        return [c[i] - rmax for i in range(3)], [c[i] + rmax for i in range(3)]
    r = [rmax] * 3 if rmax else rad
    return [c[i] - r[i] for i in range(3)], [c[i] + r[i] for i in range(3)]


def validar(f) -> Informe:
    I = Informe()
    if not isinstance(f, dict):
        I.err('E_FORMATO', 'la ficha no es un objeto JSON')
        return I
    # --- cabecera ---
    if f.get('schema') != SCHEMA:
        I.err('E_SCHEMA', f'schema debe ser {SCHEMA!r}')
    for k in ('id', 'nombre'):
        if not isinstance(f.get(k), str) or not f.get(k).strip():
            I.err('E_CAMPO', f'falta {k}')
    plantilla = f.get('plantilla')
    if plantilla not in PLANTILLAS:
        I.err('E_PLANTILLA', f'plantilla {plantilla!r} no es una de {PLANTILLAS}')
    alt = f.get('altura_m')
    if not isinstance(alt, (int, float)) or not (0.01 <= alt <= 30):
        I.err('E_ALTURA', f'altura_m {alt!r} fuera de [0.01, 30] m')
    if not isinstance(f.get('es_ficticio'), bool):
        I.err('E_CAMPO', 'es_ficticio debe ser true/false')
    elif f['es_ficticio'] and not (isinstance(f.get('analogo_real'), str) and f['analogo_real'].strip()):
        I.err('E_FICTICIO', 'personaje ficticio sin analogo_real (animal real del que se dedujo el esqueleto)')
    o = f.get('origen') or {}
    if o.get('tipo') not in TIPOS_ORIGEN:
        I.err('E_ORIGEN', f'origen.tipo debe ser uno de {TIPOS_ORIGEN}')
    # --- fuentes ---
    fu = f.get('fuentes')
    if not isinstance(fu, list) or not fu:
        I.err('E_FUENTES', 'sin fuentes citadas')
    else:
        for i, s in enumerate(fu):
            if not isinstance(s, dict) or s.get('tipo') not in TIPOS_FUENTE or not s.get('titulo') or not s.get('afirma'):
                I.err('E_FUENTES', f'fuente {i} incompleta (tipo∈{TIPOS_FUENTE}, titulo, afirma)')
            elif s['tipo'] == 'web' and not re.match(r'^https?://', str(s.get('url') or '')):
                I.err('E_FUENTES', f'fuente web {i} sin url http(s)')
        if f.get('es_ficticio') and not any(isinstance(s, dict) and s.get('tipo') == 'deduccion' for s in fu):
            I.err('E_FICTICIO', 'ficticio: falta una fuente tipo "deduccion" que explique cómo se derivó del analogo_real')
    # --- huesos ---
    hs = f.get('huesos')
    if not isinstance(hs, list) or not hs:
        I.err('E_HUESOS', 'sin huesos')
        return I
    H = {}
    for i, h in enumerate(hs):
        n = h.get('nombre') if isinstance(h, dict) else None
        if not isinstance(n, str) or not re.match(r'^[A-Za-z][A-Za-z0-9_]{0,62}$', n):
            I.err('E_NOMBRE', f'hueso {i}: nombre inválido {n!r}')
            continue
        if n in H:
            I.err('E_DUPLICADO', f'nombre de hueso repetido: {n}')
            continue
        H[n] = h
        if not (_vec(h.get('cabeza')) and _vec(h.get('cola'))):
            I.err('E_COORD', f'{n}: cabeza/cola deben ser [x,y,z] numéricos')
            continue
        L = _dist(h['cabeza'], h['cola'])
        if not (LARGO_MIN <= L <= LARGO_MAX):
            I.err('E_LARGO', f'{n}: largo {L:.4f} (fracción de altura) fuera de [{LARGO_MIN}, {LARGO_MAX}]')
        for q in (h['cabeza'], h['cola']):
            if not (-1.5 <= q[0] <= 1.5 and -2.0 <= q[1] <= 2.0 and -0.05 <= q[2] <= 1.2):
                I.err('E_COORD', f'{n}: punto {q} fuera del volumen razonable (x±1.5, y±2, z −0.05..1.2)')
        if h.get('rol') not in ROLES:
            I.err('E_ROL', f'{n}: rol {h.get("rol")!r} no es uno de la lista')
        lado = h.get('lado')
        if lado not in LADOS:
            I.err('E_LADO', f'{n}: lado debe ser C/L/R')
        else:
            esp = espejo_nombre(n)
            if lado in 'LR' and (esp is None or not n.endswith('_' + lado)):
                I.err('E_LADO', f'{n}: lado {lado} exige sufijo _{lado}')
            if lado == 'C' and esp is not None:
                I.err('E_LADO', f'{n}: lado C no puede terminar en _L/_R')
            if lado == 'C' and (abs(h['cabeza'][0]) > TOL_ESPEJO or abs(h['cola'][0]) > TOL_ESPEJO):
                I.err('E_SIMETRIA', f'{n}: hueso central fuera del plano x=0')
            if lado == 'L' and min(h['cabeza'][0], h['cola'][0]) < -TOL_ESPEJO:
                I.err('E_SIMETRIA', f'{n}: hueso L debe estar en x ≥ 0 (+X = izquierda del personaje)')
            if lado == 'R' and max(h['cabeza'][0], h['cola'][0]) > TOL_ESPEJO:
                I.err('E_SIMETRIA', f'{n}: hueso R debe estar en x ≤ 0')
        lim = h.get('limites_deg')
        if not isinstance(lim, dict) or set(lim) != {'x', 'y', 'z'}:
            I.err('E_LIMITES', f'{n}: limites_deg debe tener exactamente x, y, z')
        else:
            for ax, r in lim.items():
                if not (_vec(r, 2) and -180 <= r[0] <= r[1] <= 180):
                    I.err('E_LIMITES', f'{n}.{ax}: {r} debe ser [min, max] con −180 ≤ min ≤ max ≤ 180')
                elif not (r[0] <= 0 <= r[1]):
                    I.err('E_LIMITES', f'{n}.{ax}: {r} no incluye 0 (la pose de reposo quedaría prohibida)')
                elif r[1] - r[0] > 270:
                    I.err('E_LIMITES', f'{n}.{ax}: rango {r[1]-r[0]}° > 270° (articulación sin tope)')
    # árbol
    raices = [n for n, h in H.items() if h.get('padre') in (None, '')]
    if len(raices) != 1:
        I.err('E_RAIZ', f'debe haber exactamente 1 raíz; hay {len(raices)}: {raices}')
    for n, h in H.items():
        p = h.get('padre')
        if p not in (None, '') and p not in H:
            I.err('E_PADRE', f'{n}: padre {p!r} no existe')
    # ciclos / alcanzabilidad
    for n in H:
        seen, cur = set(), n
        while cur is not None:
            if cur in seen:
                I.err('E_CICLO', f'ciclo en la cadena de padres desde {n}')
                break
            seen.add(cur)
            p = H.get(cur, {}).get('padre')
            cur = p if p in H else None
    # cercanía al padre (las piezas se mueven juntas; un hijo lejísimos del padre = error de datos)
    for n, h in H.items():
        p = H.get(h.get('padre')) if h.get('padre') in H else None
        if p and p.get('rol') == 'raiz':
            continue   # la raíz es el ancla en el suelo: sus hijos directos pueden empezar lejos de ella
        if p and _vec(h.get('cabeza')) and _vec(p.get('cabeza')) and _vec(p.get('cola')):
            d = min(_dist(h['cabeza'], p['cola']), _dist(h['cabeza'], p['cabeza']))
            if d > 0.35:
                I.err('E_DESCONECTADO', f'{n}: su cabeza está a {d:.3f} de su padre {h["padre"]} (> 0.35)')
            elif d > 0.12:
                I.av('A_SEPARADO', f'{n}: cabeza a {d:.3f} del padre {h["padre"]}')
    # simetría
    for n, h in H.items():
        if h.get('lado') != 'L':
            continue
        m = espejo_nombre(n)
        if m not in H:
            I.err('E_SIMETRIA', f'{n} no tiene par {m}')
            continue
        r = H[m]
        if r.get('lado') != 'R':
            I.err('E_SIMETRIA', f'{m} debe ser lado R')
        if r.get('rol') != h.get('rol'):
            I.err('E_SIMETRIA', f'{n}/{m}: rol distinto')
        pl, pr = h.get('padre'), r.get('padre')
        if (espejo_nombre(pl) or pl) != pr:
            I.err('E_SIMETRIA', f'{n}/{m}: padres no espejados ({pl} vs {pr})')
        if _vec(h.get('cabeza')) and _vec(r.get('cabeza')) and _vec(h.get('cola')) and _vec(r.get('cola')):
            for k in ('cabeza', 'cola'):
                a, b = h[k], r[k]
                if _dist([-a[0], a[1], a[2]], b) > TOL_ESPEJO:
                    I.err('E_SIMETRIA', f'{n}/{m}: {k} no espejada ({a} vs {b})')
        lh, lr = h.get('limites_deg'), r.get('limites_deg')
        try:
            if espejo_limites(lh) != {k: list(v) for k, v in lr.items()}:
                I.err('E_SIMETRIA_LIM', f'{n}/{m}: límites no espejados (esperado {espejo_limites(lh)}, hay {lr})')
        except Exception:
            pass
    for n, h in H.items():
        if h.get('lado') == 'R' and espejo_nombre(n) not in H:
            I.err('E_SIMETRIA', f'{n} no tiene par L')
    # mínimos por plantilla
    for rol, (lados, k) in MINIMOS.get(plantilla, {}).items():
        for lado in lados:
            c = sum(1 for h in H.values() if h.get('rol') == rol and h.get('lado') == lado)
            if rol == 'ala' and c < k:
                cad = cadena_ala(H, lado)
                if len(cad) > c:
                    I.av('A_ALA_POR_CADENA', f'ala {lado}: cuenta la cadena anatómica {cad} (brazo/húmero → antebrazo → mano/ala)')
                    c = len(cad)
            if c < k:
                I.err('E_ANATOMIA', f'plantilla {plantilla}: rol {rol} lado {lado} tiene {c} huesos, mínimo {k}')
    # --- piezas ---
    ps = f.get('piezas')
    if not isinstance(ps, list) or not ps:
        I.err('E_PIEZAS', 'sin piezas de cuerpo')
        ps = []
    nombres_p = set()
    zmin, zmax = 9.0, -9.0
    con_pieza = set()
    for i, p in enumerate(ps):
        pn = p.get('nombre') if isinstance(p, dict) else None
        if not pn or pn in nombres_p:
            I.err('E_PIEZA', f'pieza {i}: nombre vacío o repetido ({pn!r})')
            continue
        nombres_p.add(pn)
        if p.get('hueso') not in H:
            I.err('E_PIEZA', f'{pn}: hueso {p.get("hueso")!r} no existe')
            continue
        if p.get('primitiva') not in PRIMITIVAS:
            I.err('E_PIEZA', f'{pn}: primitiva {p.get("primitiva")!r} no es una de {PRIMITIVAS}')
            continue
        if not HEX.match(str(p.get('color', ''))):
            I.err('E_PIEZA', f'{pn}: color debe ser #RRGGBB')
        if p.get('modo') == 'hueso':
            if p['primitiva'] not in ('capsula', 'cilindro', 'cono'):
                I.err('E_PIEZA', f'{pn}: modo hueso solo para capsula/cilindro/cono')
                continue
            if not isinstance(p.get('radio'), (int, float)) or not (0.002 <= p['radio'] <= 0.6):
                I.err('E_PIEZA', f'{pn}: radio inválido')
                continue
        elif p.get('modo') == 'libre':
            if not (_vec(p.get('centro')) and _vec(p.get('radios')) and all(0.001 <= r <= 1.0 for r in p['radios'])):
                I.err('E_PIEZA', f'{pn}: libre exige centro [x,y,z] y radios [rx,ry,rz] en (0.001..1.0]')
                continue
            if 'rotacion_deg' in p and not _vec(p['rotacion_deg']):
                I.err('E_PIEZA', f'{pn}: rotacion_deg debe ser [x,y,z]')
                continue
            hb = H[p['hueso']]
            if _vec(hb.get('cabeza')) and _vec(hb.get('cola')):
                d = min(_dist(p['centro'], hb['cabeza']), _dist(p['centro'], hb['cola']),
                        _dist(p['centro'], [(a + b) / 2 for a, b in zip(hb['cabeza'], hb['cola'])]))
                if d > 0.4:
                    I.err('E_PIEZA', f'{pn}: centro a {d:.3f} de su hueso {p["hueso"]} (> 0.4)')
        else:
            I.err('E_PIEZA', f'{pn}: modo debe ser "hueso" o "libre"')
            continue
        if not (_vec(H[p['hueso']].get('cabeza')) and _vec(H[p['hueso']].get('cola'))):
            continue
        con_pieza.add(p['hueso'])
        mn, mx = _bbox_pieza(p, H)
        zmin, zmax = min(zmin, mn[2]), max(zmax, mx[2])
    if ps and zmin < 9:
        if abs(zmin) > TOL_SUELO + 1e-6:   # 1e-6: error de coma flotante (9-nov: -0.030000000000000002 rechazado por redondeo)
            I.err('E_SUELO', f'el cuerpo no apoya en el suelo: z mínimo de piezas = {zmin:.3f} (debe ser ≈0 ±{TOL_SUELO})')
        if not (0.9 <= zmax <= 1.1):
            I.err('E_ALTURA_PIEZAS', f'punto más alto de piezas z = {zmax:.3f}; debe ser ≈1.0 (0.9..1.1) porque todo es fracción de altura_m')
    sin = [n for n, h in H.items() if n not in con_pieza and h.get('rol') not in ('raiz',)]
    if sin:
        I.av('A_SIN_PIEZA', f'huesos sin pieza visible: {sin}')
    # apoyo: si hay huesos de apoyo, alguno toca el suelo
    apoyo = [h for h in H.values() if h.get('rol') in ROLES_APOYO and _vec(h.get('cola'))]
    if apoyo and min(min(h['cola'][2], h['cabeza'][2]) for h in apoyo) > 0.05:
        I.err('E_APOYO', 'ningún hueso de pierna/pata/pie llega al suelo (z ≤ 0.05)')
    # --- rostro: ojos y nariz/pico ---
    ro = f.get('rostro')
    if not isinstance(ro, dict):
        I.err('E_ROSTRO', 'falta rostro (ojos + nariz/pico)')
    else:
        hb = H.get(ro.get('hueso'))
        if hb is None:
            I.err('E_ROSTRO', f'rostro.hueso {ro.get("hueso")!r} no existe')
        else:
            if hb.get('rol') != 'cabeza':
                I.err('E_ROSTRO', 'rostro.hueso debe ser el hueso de rol cabeza')
            oj, na = ro.get('ojos') or {}, ro.get('nariz') or {}
            if not (_vec(oj.get('centro_L')) and isinstance(oj.get('radio'), (int, float)) and 0.002 <= oj['radio'] <= 0.2):
                I.err('E_ROSTRO', 'ojos requiere centro_L [x,y,z] y radio (0.002..0.2); el R se espeja')
            elif oj['centro_L'][0] <= 0:
                I.err('E_ROSTRO', 'ojos.centro_L debe tener x > 0 (+X = izquierda)')
            if not (_vec(na.get('centro')) and isinstance(na.get('radio'), (int, float)) and na.get('primitiva') in ('esfera', 'cono')):
                I.err('E_ROSTRO', 'nariz requiere centro, radio y primitiva esfera|cono')
            elif abs(na['centro'][0]) > TOL_ESPEJO:
                I.err('E_ROSTRO', 'nariz/pico debe estar centrada (x≈0)')
            if not I.errores or all(e['codigo'] != 'E_ROSTRO' for e in I.errores):
                if _vec(hb.get('cabeza')) and _vec(hb.get('cola')) and _vec(oj.get('centro_L')) and _vec(na.get('centro')):
                    yc = (hb['cabeza'][1] + hb['cola'][1]) / 2
                    if not oj['centro_L'][1] < yc:
                        I.err('E_ROSTRO', 'los ojos no están al frente (−Y) del centro de la cabeza')
                    if not na['centro'][1] < oj['centro_L'][1]:
                        I.err('E_ROSTRO', 'la nariz/pico no está delante (−Y) de los ojos')
                    for q, que in ((oj['centro_L'], 'ojo'), (na['centro'], 'nariz')):
                        d = min(_dist(q, hb['cabeza']), _dist(q, hb['cola']))
                        if d > 0.45:
                            I.err('E_ROSTRO', f'{que} a {d:.3f} del hueso cabeza (> 0.45)')
    # --- poses de prueba (opcional) dentro de límites ---
    for pn, pose in (f.get('poses_prueba') or {}).items():
        for b, rot in pose.items():
            if b not in H:
                I.err('E_POSE', f'pose {pn}: hueso {b} no existe')
            elif not _vec(rot):
                I.err('E_POSE', f'pose {pn}/{b}: debe ser [x,y,z] grados')
            else:
                lim = H[b].get('limites_deg') or {}
                for ax, v in zip('xyz', rot):
                    r = lim.get(ax)
                    if r and not (r[0] <= v <= r[1]):
                        I.av('A_POSE_FUERA', f'pose {pn}/{b}.{ax}={v} fuera de {r}; el constructor la recorta')
    return I


def main(argv):
    if not argv:
        print(__doc__)
        return 2
    f = json.load(open(argv[0], encoding='utf-8'))
    I = validar(f)
    if '--json' in argv:
        print(json.dumps(I.dict(), ensure_ascii=False, indent=2))
    else:
        print(('APTA' if I.apta else 'RECHAZADA') + f'  {argv[0]}  errores={len(I.errores)} avisos={len(I.avisos)}')
        for e in I.errores:
            print('  ERROR', e['codigo'], e['detalle'])
        for a in I.avisos:
            print('  aviso', a['codigo'], a['detalle'])
    return 0 if I.apta else 1


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
