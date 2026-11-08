"""Enlaza el eje de continuidad del SB con un objeto ya construido. No inventa posiciones."""
from seguridad import error

def par_eje(eje, armatures, objetos):
    """(actor, objeto) si el segundo extremo existe. Si no, ambiguo: no se mide."""
    if not eje:
        return None
    brazos = sorted(armatures, key=len, reverse=True)
    if eje in objetos:
        for actor in brazos:
            if eje.startswith(actor + '-') and len(eje) > len(actor) + 1:
                return (actor, eje)
    for actor in brazos:
        if eje.startswith(actor + '-'):
            resto = eje[len(actor) + 1:]
            if resto in armatures or resto in objetos:
                return (actor, resto)
            return ('ambiguo', actor, resto)
    return ('ambiguo', None, eje)

def _citados(texto, prop_ids):
    encontrados = [pid for pid in prop_ids if pid and pid in texto]
    if encontrados:
        return encontrados
    return [pid for pid in prop_ids if pid and texto.startswith(pid)]

def enlazar(vinetas, prop_ids, personajes):
    """Devuelve {id_de_eje: id_de_prop} solo cuando el SB cita un único objeto construido."""
    aliases = {}
    errores = []
    personas = sorted(set(personajes), key=len, reverse=True)
    props = list(dict.fromkeys(prop_ids))
    citados_por_eje = {}
    vistos = []
    for vin in vinetas or []:
        cont = (vin or {}).get('continuidad') or {}
        eje = cont.get('eje')
        if not isinstance(eje, str) or not eje:
            continue
        actor = next((p for p in personas if eje.startswith(p + '-')), None)
        if actor is None:
            errores.append(error('camera/continuidad.eje', 'SB + constructor', 'El eje no empieza por un personaje de la escena: ' + eje, 'EJE_SIN_OBJETO'))
            continue
        resto = eje[len(actor) + 1:]
        if not resto:
            errores.append(error('camera/continuidad.eje', 'SB + constructor', 'Eje sin segundo extremo: ' + eje, 'EJE_SIN_OBJETO'))
            continue
        if resto in personas:
            continue
        if eje not in citados_por_eje:
            citados_por_eje[eje] = []
            vistos.append(eje)
        textos = []
        for cambio in cont.get('cambios_declarados') or []:
            if not isinstance(cambio, dict):
                continue
            for clave in ('antes', 'despues'):
                if isinstance(cambio.get(clave), str):
                    textos.append(cambio[clave])
        for texto in textos:
            citados_por_eje[eje].extend(_citados(texto, props))
    for eje in vistos:
        unicos = list(dict.fromkeys(citados_por_eje[eje]))
        if len(unicos) != 1:
            errores.append(error('camera/' + eje, 'SELLO OBJ + escenario vivo + SB', 'El eje ' + eje + ' no tiene un único objeto construido citado en el SB (' + ', '.join(unicos) + '). No se inventa el vínculo ni la posición.', 'EJE_SIN_OBJETO', dato_encontrado=unicos, dato_esperado='un id de prop ya construido'))
            continue
        aliases[eje] = unicos[0]
    return aliases, errores

def alias_vacio(prop, eje_id):
    """El vacío del eje copia la transformación medida del prop. No inventa otra posición."""
    if not isinstance(prop, dict) or not isinstance(prop.get('position_m'), list) or len(prop['position_m']) != 3:
        raise ValueError('El objeto del eje ' + eje_id + ' no tiene position_m medida; no se inventa su posición')
    giro = prop.get('rotation_deg')
    if giro is None:
        giro = [0, 0, 0]
    if not isinstance(giro, list) or len(giro) != 3:
        raise ValueError('El objeto del eje ' + eje_id + ' no tiene rotation_deg medida')
    return {'id': eje_id, 'parent_id': prop['id'], 'position_m': list(prop['position_m']), 'rotation_deg': list(giro), 'source': 'continuidad.eje', 'of': prop['id']}
