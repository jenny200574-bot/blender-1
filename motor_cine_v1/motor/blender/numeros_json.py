"""numeros_json — coercer campos numéricos de JSON (cámara/SB/entrada). Código propio MYIA.

Acepta int/float y cadenas numéricas (coma decimal, sufijo opcional mm/cm/m/deg).
Un valor no parseable (p.ej. «por medir en 02N») NUNCA se convierte en 0 en silencio:
se lanza ValorNoNumerico, o —si el campo admite reserva óptica (distancia_m / altura_m)—
queda en None para que el motor calcule o use un respaldo documentado.
Universal: cualquier canal/capítulo/escena/campo numérico del JSON."""
import math, re

_UNIDAD = re.compile(
    r'^\s*([+-]?(?:\d+(?:[.,]\d*)?|\.\d+)(?:[eE][+-]?\d+)?)\s*'
    r'(mm|cm|m|deg|°|grados)?\s*$',
    re.I,
)
_PLACEHOLDER = re.compile(
    r'por\s+medir|pendiente|a\s+medir|\btbd\b|\bn/?a\b|\bnone\b|\bnull\b|'
    r'sin\s+dato|sin\s+medir|no\s+medid',
    re.I,
)

# Claves que, si aparecen, deben ser número o lista de números.
CAMPOS_NUM = {
    'distancia_m', 'lente_mm', 'altura_m', 'giro_grados', 't', 't_abs',
    'sensor_mm', 'fps', 'yaw', 'pitch', 'roll', 'frame_ini', 'frame_fin',
    'f0', 'f1', 'k',
}

# Sin reserva: si no se puede parsear, error claro.
CAMPOS_DUROS = {'lente_mm', 't', 't_abs', 'sensor_mm', 'fps', 'frame_ini', 'frame_fin'}

# Con reserva: placeholder o basura -> None (el caller documenta el aviso / calcula).
CAMPOS_SUAVES = {'distancia_m', 'altura_m', 'giro_grados'}

# Cobertura vertical del sujeto (fracción de su altura) por tipo de plano.
# Estándar cinematográfico, no hay valores por canal ni por escena.
COBERTURA_PLANO = {
    'ECU': 0.28, 'CU': 0.40, 'MCU': 0.55, 'MS': 0.70,
    'MLS': 0.95, 'FS': 1.20, 'MWS': 1.60, 'WS': 2.20,
    'LS': 3.00, 'EWS': 4.50,
}


class ValorNoNumerico(ValueError):
    """Un campo que debía ser numérico no se pudo convertir."""


def es_placeholder(v):
    if v is None:
        return True
    if isinstance(v, str) and (not v.strip() or _PLACEHOLDER.search(v.strip())):
        return True
    return False


def _unidad_destino(campo):
    if not campo:
        return None
    if campo.endswith('_mm') or campo == 'sensor_mm':
        return 'mm'
    if campo.endswith('_m'):
        return 'm'
    if 'grados' in campo or campo in ('yaw', 'pitch', 'roll'):
        return 'deg'
    return None


def _convertir(n, origen, destino):
    if not origen or not destino or origen == destino:
        return n
    a_m = {'mm': 0.001, 'cm': 0.01, 'm': 1.0}
    if origen in a_m and destino in a_m:
        return n * a_m[origen] / a_m[destino]
    # deg/°: no hay conversión de longitud
    return n


def a_numero(v, campo=None, obligatorio=False):
    """Convierte v a float. None/vacío -> None (o error si obligatorio).
    Lanza ValorNoNumerico si no es parseable (nunca devuelve 0 inventado)."""
    if v is None or (isinstance(v, str) and not v.strip()):
        if obligatorio:
            raise ValorNoNumerico(f"{campo or 'valor'}: está vacío y se requiere un número")
        return None
    if isinstance(v, bool):
        raise ValorNoNumerico(f"{campo or 'valor'}: booleano «{v}» no es un número")
    if isinstance(v, (int, float)):
        x = float(v)
        if not math.isfinite(x):
            raise ValorNoNumerico(f"{campo or 'valor'}: no es finito ({v})")
        return x
    if isinstance(v, str):
        if es_placeholder(v):
            if obligatorio:
                raise ValorNoNumerico(
                    f"{campo or 'valor'}: «{v}» no es un número (marca de «aún no medido»); "
                    f"no se convierte a 0 en silencio"
                )
            return None
        m = _UNIDAD.match(v)
        if not m:
            raise ValorNoNumerico(
                f"{campo or 'valor'}: no se puede convertir «{v}» en número "
                f"(se acepta int/float o cadena numérica con unidad opcional mm/cm/m/deg)"
            )
        n = float(m.group(1).replace(',', '.'))
        if not math.isfinite(n):
            raise ValorNoNumerico(f"{campo or 'valor'}: no es finito («{v}»)")
        u = (m.group(2) or '').lower().replace('°', 'deg').replace('grados', 'deg')
        dest = _unidad_destino(campo)
        if u and dest:
            n = _convertir(n, u, dest)
        return n
    raise ValorNoNumerico(f"{campo or 'valor'}: tipo {type(v).__name__} no se puede convertir en número")


def distancia_desde_plano(plano, lente_mm, altura_m, sensor_h_mm):
    """Distancia cámara-sujeto (m) para encuadrar la cobertura del plano, con lente y sensor dados.
    Óptica pinhole: dist = (cobertura * altura * lente_mm) / sensor_vertical_mm.
    Universal: no hay constantes de un canal, capítulo, escena o personaje concreto."""
    if lente_mm is None or altura_m is None or not sensor_h_mm:
        raise ValorNoNumerico(
            f"no se puede calcular distancia_m: faltan plano={plano!r} lente_mm={lente_mm!r} "
            f"altura_m={altura_m!r} sensor_h_mm={sensor_h_mm!r}"
        )
    cov = COBERTURA_PLANO.get((plano or '').upper(), COBERTURA_PLANO['FS'])
    d = (float(cov) * float(altura_m) * float(lente_mm)) / float(sensor_h_mm)
    return max(0.05, d)


def _coercer_campo(clave, val, ruta, avisos, duros, suaves):
    """Un valor escalar de un campo numérico: duro (error si no hay número) o suave (None + aviso)."""
    if clave in duros:
        if es_placeholder(val):
            raise ValorNoNumerico(
                f"{ruta}.{clave}: «{val}» no es un número (campo obligatorio, no hay reserva)"
            )
        return a_numero(val, clave, obligatorio=True)
    # suaves o valor no parseable de campo con reserva
    if es_placeholder(val):
        if val is not None and not (isinstance(val, str) and not val.strip()):
            avisos.append(f"{ruta}.{clave}: «{val}» no numérico -> None")
        return None
    try:
        return a_numero(val, clave, obligatorio=False)
    except ValorNoNumerico:
        avisos.append(f"{ruta}.{clave}: «{val}» no numérico -> None")
        return None


def _normalizar_valor(clave, val, ruta, avisos, duros, suaves):
    if isinstance(val, list):
        out = []
        for i, x in enumerate(val):
            if isinstance(x, (list, dict)):
                out.append(normalizar_numericos(x, f"{ruta}.{clave}[{i}]", avisos, duros, suaves))
            else:
                out.append(_coercer_campo(clave, x, f"{ruta}.{clave}[{i}]", avisos, duros, suaves))
        return out
    if isinstance(val, dict):
        return normalizar_numericos(val, f"{ruta}.{clave}", avisos, duros, suaves)
    return _coercer_campo(clave, val, ruta, avisos, duros, suaves)


def normalizar_numericos(obj, ruta='$', avisos=None, duros=None, suaves=None):
    """Recorre dict/list y convierte las claves de CAMPOS_NUM a float (o lista de float).
    Mutación in-place y valor de retorno = el mismo objeto. avisos se llena con reservas suaves."""
    if avisos is None:
        avisos = []
    if duros is None:
        duros = CAMPOS_DUROS
    if suaves is None:
        suaves = CAMPOS_SUAVES
    if isinstance(obj, list):
        for i, x in enumerate(obj):
            if isinstance(x, (dict, list)):
                normalizar_numericos(x, f"{ruta}[{i}]", avisos, duros, suaves)
        return obj
    if not isinstance(obj, dict):
        return obj
    for k, v in list(obj.items()):
        if k in CAMPOS_NUM:
            obj[k] = _normalizar_valor(k, v, ruta, avisos, duros, suaves)
        elif isinstance(v, (dict, list)):
            normalizar_numericos(v, f"{ruta}.{k}", avisos, duros, suaves)
    return obj


def normalizar_camara(cv):
    """Normaliza un documento de cámara v1/v2. Devuelve (cv, avisos).
    distancia_m / altura_m no medidos quedan en None (el motor calcula o usa altura del personaje).
    lente_mm, t, t_abs, sensor_mm ilegibles lanzan ValorNoNumerico."""
    avisos = []
    normalizar_numericos(cv, '$camara', avisos)
    return cv, avisos
