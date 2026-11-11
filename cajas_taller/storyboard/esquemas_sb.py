"""PISTA INMI (2026-11-01) esquemas JSON de las llamadas del ADAPTIVE CINEMATIC DIRECTOR (subconjunto de llamada_segura: type, properties,
required, items, enum). Regla Vertex: arreglos sin minItems/maxItems de más de 3 exactos (no se usan). Los enums salen del DSL fijado."""
import json
import sb_comun as S

STR = {'type': 'string'}
NUM = {'type': 'number'}
LST = {'type': 'array', 'items': STR}


def _obj(req, props): return {'type': 'object', 'required': list(req), 'properties': props}


def generos_ids():
    return sorted((S.leer(S.AQUI / 'config' / 'perfiles' / '_indice.json') or {}).get('perfiles') or {})


def etapa1():
    seg = _obj(['desde_cita', 'hasta_cita', 'generos', 'tono', 'emociones', 'intensidad', 'por_que'], {
        'desde_cita': STR, 'hasta_cita': STR,
        'generos': {'type': 'array', 'items': _obj(['genero', 'peso'], {'genero': {'type': 'string', 'enum': generos_ids()}, 'peso': NUM})},
        'subgenero': STR, 'tono': STR, 'emociones': LST, 'intensidad': {'type': 'integer'}, 'por_que': STR})
    return _obj(['escenas', 'arco_capitulo', 'revision'], {
        'escenas': {'type': 'array', 'items': _obj(['escena', 'segmentos'], {'escena': STR, 'segmentos': {'type': 'array', 'items': seg}})},
        'arco_capitulo': STR, 'revision': {'type': 'array', 'items': _obj(['chequeo', 'ok'], {'chequeo': STR, 'ok': {'type': 'boolean'}, 'nota': STR})}})


def vineta():
    tam = {'type': 'string', 'enum': S.tokens_de('SHOT_SIZE')}
    ang = {'type': 'string', 'enum': S.tokens_de('CAMERA_ANGLE')}
    lado = {'type': 'string', 'enum': ['L', 'C', 'R']}
    aj = S.ajustes()
    return _obj(['id', 'orden', 't', 'beats_01', 'beat_narrativo', 'segmento_genero', 'intencion_narrativa', 'beats_visuales', 'secuencia',
                 'director_imagen', 'actuacion', 'director_camara', 'ritmo', 'transicion_salida', 'audio', 'continuidad', 'justificacion'], {
        'id': STR, 'orden': {'type': 'integer'}, 't': {'type': 'array', 'items': NUM},
        'beats_01': LST, 'beat_narrativo': STR, 'segmento_genero': {'type': 'integer'},
        'intencion_narrativa': STR, 'beats_visuales': LST, 'secuencia': STR,
        'director_imagen': _obj(['plano', 'angulo', 'lente_mm', 'perspectiva', 'dsl_encuadre', 'en_cuadro', 'objetos', 'composicion', 'continuidad_con_anterior'], {
            'plano': tam, 'angulo': ang, 'lente_mm': NUM, 'perspectiva': STR, 'dsl_encuadre': STR,
            'en_cuadro': {'type': 'array', 'items': _obj(['id', 'lado', 'profundidad', 'mira_a'], {
                'id': STR, 'lado': lado, 'profundidad': {'type': 'string', 'enum': ['frente', 'medio', 'fondo']}, 'mira_a': STR, 'orientacion': STR})},
            'objetos': {'type': 'array', 'items': _obj(['nombre', 'lado', 'estado'], {'nombre': STR, 'lado': lado, 'profundidad': STR, 'estado': STR})},
            'composicion': STR, 'continuidad_con_anterior': STR}),
        'actuacion': {'type': 'array', 'items': _obj(['id', 'expresion', 'gestos', 'postura', 'movimiento', 'intensidad'], {
            'id': STR, 'expresion': STR, 'gestos': STR, 'postura': STR, 'movimiento': STR, 'intensidad': {'type': 'integer'}})},
        'director_camara': _obj(['dsl_movimiento', 'encuadre_inicio', 'encuadre_fin', 'velocidad', 'motivacion'], {
            'dsl_movimiento': STR, 'encuadre_inicio': tam, 'encuadre_fin': tam,
            'velocidad': {'type': 'string', 'enum': list(S.registro().speed_scale)}, 'motivacion': STR}),
        'ritmo': _obj(['duracion_s', 'pausas'], {'duracion_s': NUM, 'pausas': {'type': 'array', 'items': _obj(['t', 'motivo'], {'t': {'type': 'array', 'items': NUM}, 'motivo': STR})}}),
        'transicion_salida': _obj(['tipo', 'motivo'], {'tipo': {'type': 'string', 'enum': aj['transiciones']}, 'motivo': STR}),
        'audio': {'type': 'array', 'items': _obj(['tipo', 'quien', 't', 'texto'], {
            'tipo': {'type': 'string', 'enum': ['dialogo', 'narracion', 'voz_off', 'sonido', 'silencio']}, 'quien': STR,
            't': {'type': 'array', 'items': NUM}, 'texto': STR})},
        'continuidad': _obj(['debe_mantenerse', 'eje', 'direccion_pantalla', 'cambios_declarados'], {
            'debe_mantenerse': LST, 'eje': STR, 'direccion_pantalla': {'type': 'string', 'enum': ['L2R', 'R2L', 'neutral']},
            'cambios_declarados': {'type': 'array', 'items': _obj(['que', 'personaje', 'antes', 'despues', 'beat_01'], {
                'que': {'type': 'string', 'enum': ['vestuario', 'danos', 'objetos', 'eje', 'direccion_pantalla', 'posicion', 'luz']},
                'personaje': STR, 'antes': STR, 'despues': STR, 'beat_01': STR})}}),
        'justificacion': _obj(['emocion_buscada', 'por_que'], {'emocion_buscada': STR, 'por_que': STR})})


def memoria():
    pj = _obj(['id', 'vestuario', 'danos', 'objetos', 'posicion', 'arco_emocional'], {
        'id': STR, 'vestuario': LST, 'danos': LST, 'objetos': LST,
        'posicion': _obj(['lado', 'zona'], {'lado': {'type': 'string', 'enum': ['L', 'C', 'R']}, 'zona': STR}), 'arco_emocional': STR})
    return _obj(['personajes', 'direccion_pantalla', 'eje', 'objetos_escena'], {
        'personajes': {'type': 'array', 'items': pj}, 'direccion_pantalla': {'type': 'string', 'enum': ['L2R', 'R2L', 'neutral']}, 'eje': STR,
        'objetos_escena': LST})


def narrativa():
    return _obj(['intencion_escena', 'estructura', 'beats_narrativos'], {
        'intencion_escena': STR, 'estructura': STR,
        'beats_narrativos': {'type': 'array', 'items': _obj(['id', 'beats_01', 'segmento_genero', 'intencion', 'enfatizar', 'ocultar', 'ritmo'], {
            'id': STR, 'beats_01': LST, 'segmento_genero': {'type': 'integer'}, 'intencion': STR, 'enfatizar': STR, 'ocultar': STR, 'ritmo': STR})}})


def etapa3y4():
    return _obj(['escena', 'duracion_s', 'niveles_aplicados', 'narrativa', 'vinetas', 'memoria_salida', 'revision'], {
        'escena': STR, 'duracion_s': NUM,
        'niveles_aplicados': _obj(['nivel_1_generos', 'nivel_2_estilo', 'nivel_3_reglamento'], {'nivel_1_generos': LST, 'nivel_2_estilo': STR, 'nivel_3_reglamento': STR}),
        'narrativa': narrativa(), 'vinetas': {'type': 'array', 'items': vineta()}, 'memoria_salida': memoria(),
        'revision': {'type': 'array', 'items': _obj(['chequeo', 'ok'], {'chequeo': STR, 'ok': {'type': 'boolean'}, 'nota': STR})}})


def reparar():
    return _obj(['vinetas'], {'vinetas': {'type': 'array', 'items': vineta()}, 'eliminar': LST, 'memoria_salida': memoria(), 'narrativa': narrativa()})


def escribir():
    """Deja los esquemas en prompts/ (para leerlos y para el sha del prompt fijo)."""
    for nom, f in (('etapa1_esquema.json', etapa1), ('etapa3y4_esquema.json', etapa3y4), ('reparar_esquema.json', reparar)):
        (S.AQUI / 'prompts' / nom).write_text(json.dumps(f(), ensure_ascii=False, indent=1, sort_keys=True), encoding='utf-8')


if __name__ == '__main__':
    escribir(); print('ok')
