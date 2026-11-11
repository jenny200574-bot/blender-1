"""PISTA INMI (2026-11-01) MEMORIA DE CONTINUIDAD del capítulo (cubos/SB/memoria_continuidad.json). Gratis.
Por escena: entrada (= salida de la escena anterior del capítulo) y salida (la del storyboard VALIDADO). Lleva vestuario, daños, objetos,
posición/lado, dirección de pantalla, eje y arco emocional, de escena en escena. Solo se escribe después de validar."""
import time
import sb_comun as S

ARCHIVO = 'memoria_continuidad.json'


def _dic(salida):
    """memoria_salida (lista de personajes) → forma de memoria (dict por id)."""
    s = salida or {}
    return {'personajes': {p['id']: {k: p.get(k) for k in ('vestuario', 'danos', 'objetos', 'posicion', 'arco_emocional')} for p in s.get('personajes') or []},
            'direccion_pantalla': s.get('direccion_pantalla') or 'neutral', 'eje': s.get('eje') or '', 'objetos_escena': s.get('objetos_escena') or []}


def leer(carpeta_sb): return S.leer(carpeta_sb / ARCHIVO) or {'version': 'sb_v1', 'escenas': {}}


def entrada(carpeta_sb, escenas_orden, n, datos_00=None):
    """Memoria con la que ENTRA la escena n: la salida de la escena anterior del capítulo. Si no existe, solo los hechos del 00 (y aviso)."""
    M = leer(carpeta_sb); av = []
    orden = [str(x) for x in escenas_orden]; k = orden.index(str(n)) if str(n) in orden else -1
    prev = orden[k - 1] if k > 0 else None
    e = {'personajes': {}, 'direccion_pantalla': 'neutral', 'eje': '', 'objetos_escena': [], 'escena_anterior': prev, 'fuente': 'inicio del capítulo'}
    if prev:
        sp = ((M.get('escenas') or {}).get(prev) or {}).get('salida')
        if sp: e.update(sp); e['fuente'] = f'salida validada del storyboard de la escena {prev}'
        else: e['fuente'] = f'la escena {prev} aún no tiene storyboard validado: solo hechos del mapa 00'; av.append(f'escena {n}: sin memoria de la escena {prev} (aún sin storyboard): continuidad solo con los hechos del 00')
    if datos_00: e['hechos_00_anterior'] = datos_00
    return e, av


def registrar(carpeta_sb, n, ent, salida, de, archivo=ARCHIVO):
    f = carpeta_sb / archivo; M = S.leer(f) or {'version': 'sb_v1', 'escenas': {}}
    M['escenas'][str(n)] = {'entrada': ent, 'salida': _dic(salida), 'de': de, 'fecha': time.strftime('%Y-%m-%dT%H:%M:%S%z')}
    return S.guardar(f, M)
