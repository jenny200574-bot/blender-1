"""Recibo de paquete normalizado y de núcleo.

Un artefacto sin este recibo, o con hashes distintos del código y de la
entrada que lo produjeron, no se reutiliza. No aprueba escena, física ni render.
"""
import hashlib
import json
from pathlib import Path

ESQUEMA = 'compatibilidad_artefacto/1'
COMPILADORES = ['objetos_adn.compilar', 'traductor_adn.compilar']
CODIGO_PAQUETE = (
    'motor/apariencia_base_cpu.py',
    'motor/compatibilidad_artefacto.py',
    'motor/eje_objetos.py',
    'motor/malla_cabeza.py',
    'motor/objetos_adn.py',
    'motor/superficies_adn.py',
    'motor/traductor_adn.py',
)
_EXTRA_NUCLEO = (
    'motor/compatibilidad_artefacto.py',
    'motor/malla_cabeza.py',
    'motor/nucleo_bueno_cpu.py',
)


class ReusoIncompatible(ValueError):
    def __init__(self, motivos):
        self.motivos = list(motivos)
        self.faltantes = self.motivos
        super().__init__('REUSO_INCOMPATIBLE: ' + json.dumps(self.motivos, ensure_ascii=False))


def huella_obj(data):
    payload = json.dumps(data, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False)
    return hashlib.sha256(payload.encode()).hexdigest()


def _sha_archivo(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def archivos_nucleo(root):
    root = Path(root)
    carpeta = root / 'motor' / 'heredado'
    if not carpeta.is_dir():
        return []
    hallados = sorted(p.relative_to(root).as_posix() for p in carpeta.glob('*.py'))
    return sorted(set(hallados).union(_EXTRA_NUCLEO))


def _huella_codigo(root, relativos):
    root = Path(root)
    codigo = {}
    faltan = []
    for rel in relativos:
        path = root / rel
        if not path.is_file():
            faltan.append(rel)
            continue
        codigo[rel] = _sha_archivo(path)
    return codigo, faltan


def _leer_json(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def _escribir(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2, allow_nan=False) + '\n', encoding='utf-8')


def _motivo(codigo, **detalle):
    row = {'codigo': codigo}
    row.update(detalle)
    return row


def _marcadores_paquete(data):
    ejes = data.get('_eje_objetos') if isinstance(data, dict) else None
    cabeza = data.get('_cabeza_compilada') if isinstance(data, dict) else None
    motivos = []
    if not isinstance(ejes, dict) or ejes.get('esquema') != ESQUEMA or not isinstance(ejes.get('ejes'), list):
        motivos.append(_motivo('FALTA_MARCA_EJES', detalle='El paquete no fue cerrado por objetos_adn.compilar de este esquema'))
    if not isinstance(cabeza, dict) or cabeza.get('esquema') != ESQUEMA or not isinstance(cabeza.get('entidades'), list):
        motivos.append(_motivo('FALTA_MARCA_CABEZA', detalle='El paquete no fue cerrado por traductor_adn.compilar de este esquema'))
    if motivos:
        return motivos
    presentes = sorted({eje for prop in data.get('props') or [] if isinstance(prop, dict) for eje in (prop.get('axis_ids') or [])})
    if sorted(ejes['ejes']) != presentes:
        motivos.append(_motivo('EJES_NO_COINCIDEN_CON_PROPS', detalle='La marca de ejes y axis_ids de los props no son el mismo conjunto'))
    return motivos


def sellar_paquete(root, paquete):
    """Escribe el recibo si la entrada trae las marcas de este esquema. Si no, no sella."""
    root = Path(root)
    paquete = Path(paquete)
    entrada = paquete / 'entrada_escena.json'
    if not entrada.is_file():
        return False
    try:
        data = _leer_json(entrada)
    except (OSError, json.JSONDecodeError, TypeError, ValueError):
        return False
    if _marcadores_paquete(data):
        return False
    codigo, faltan = _huella_codigo(root, CODIGO_PAQUETE)
    if faltan:
        return False
    recibo = {
        'esquema': ESQUEMA,
        'tipo': 'paquete_normalizado',
        'compiladores': list(COMPILADORES),
        'codigo': codigo,
        'entrada_sha256': _sha_archivo(entrada),
        'produccion_aprobada': False,
        'no_es_aprobacion': 'Solo ata el paquete al código que lo compiló. No aprueba física, escena ni render.',
    }
    _escribir(paquete / 'compatibilidad_paquete.json', recibo)
    return True


def sellar_nucleo(root, blend, entrada_json):
    """Sella el .blend con el código del núcleo y la huella del legacy que lo construyó."""
    root = Path(root)
    blend = Path(blend)
    entrada_json = Path(entrada_json)
    if not entrada_json.is_file():
        raise FileNotFoundError(str(entrada_json))
    codigo, faltan = _huella_codigo(root, archivos_nucleo(root))
    if faltan:
        raise FileNotFoundError('Falta código del núcleo: ' + ', '.join(faltan))
    data = _leer_json(entrada_json)
    recibo = {
        'esquema': ESQUEMA,
        'tipo': 'nucleo',
        'codigo': codigo,
        'entrada_huella': huella_obj(data),
        'produccion_aprobada': False,
        'no_es_aprobacion': 'Solo ata el núcleo al código y al legacy que lo construyeron. No aprueba la escena.',
    }
    _escribir(blend.parent / 'compatibilidad_nucleo.json', recibo)
    return True


def _comparar_codigo(root, relativos, recibo):
    motivos = []
    codigo, faltan = _huella_codigo(root, relativos)
    for rel in faltan:
        motivos.append(_motivo('FALTA_CODIGO', archivo=rel))
    visto = recibo.get('codigo')
    if not isinstance(visto, dict):
        motivos.append(_motivo('RECIBO_SIN_CODIGO'))
        return motivos
    if sorted(visto) != sorted(relativos):
        motivos.append(_motivo('CONJUNTO_DE_CODIGO_DISTINTO', esperado=list(relativos), encontrado=sorted(visto)))
        return motivos
    for rel, digest in codigo.items():
        if visto.get(rel) != digest:
            motivos.append(_motivo('CODIGO_DISTINTO', archivo=rel))
    return motivos


def exigir_paquete(root, paquete):
    paquete = Path(paquete)
    path = paquete / 'compatibilidad_paquete.json'
    entrada = paquete / 'entrada_escena.json'
    if not path.is_file():
        return [_motivo('FALTA_RECIBO_PAQUETE', detalle='Hay que rehacer el preflight con este código. No se reutiliza el paquete viejo.')]
    if not entrada.is_file():
        return [_motivo('FALTA_ENTRADA_PAQUETE')]
    try:
        recibo = _leer_json(path)
        data = _leer_json(entrada)
    except (OSError, json.JSONDecodeError, TypeError, ValueError):
        return [_motivo('RECIBO_PAQUETE_ILEGIBLE')]
    motivos = []
    if recibo.get('esquema') != ESQUEMA or recibo.get('tipo') != 'paquete_normalizado':
        motivos.append(_motivo('ESQUEMA_PAQUETE', detalle='El recibo no es de este esquema'))
    if recibo.get('compiladores') != COMPILADORES:
        motivos.append(_motivo('COMPILADORES_DISTINTOS'))
    motivos.extend(_marcadores_paquete(data))
    motivos.extend(_comparar_codigo(root, CODIGO_PAQUETE, recibo))
    if recibo.get('entrada_sha256') != _sha_archivo(entrada):
        motivos.append(_motivo('ENTRADA_PAQUETE_DISTINTA', detalle='entrada_escena.json cambió después del sello'))
    return motivos


def exigir_nucleo(root, blend, legacy):
    blend = Path(blend)
    path = blend.parent / 'compatibilidad_nucleo.json'
    if not path.is_file():
        return [_motivo('FALTA_RECIBO_NUCLEO', detalle='Hay que reconstruir el núcleo con este código. No se abre el .blend viejo.')]
    if not isinstance(legacy, dict):
        return [_motivo('FALTA_LEGACY', detalle='El paquete no trae legacy para cotejar el núcleo')]
    try:
        recibo = _leer_json(path)
    except (OSError, json.JSONDecodeError, TypeError, ValueError):
        return [_motivo('RECIBO_NUCLEO_ILEGIBLE')]
    motivos = []
    if recibo.get('esquema') != ESQUEMA or recibo.get('tipo') != 'nucleo':
        motivos.append(_motivo('ESQUEMA_NUCLEO'))
    actuales = archivos_nucleo(root)
    motivos.extend(_comparar_codigo(root, actuales, recibo))
    if recibo.get('entrada_huella') != huella_obj(legacy):
        motivos.append(_motivo('LEGACY_DISTINTO', detalle='El legacy del paquete no es el que construyó este núcleo'))
    return motivos
