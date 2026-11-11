"""m3_router — enrutador de movimientos especiales + adaptación autónoma (PLANO_MOVIMIENTOS_ESPECIALES, t961u–t964u).
tipo_movimiento: normal | vuelo_alas | vuelo_sin_alas | pelea_exagerada | sin_forma.
Reglas (programa): el molde NUNCA se cambia; si falta un hueso/plantilla -> STOP pedir_a_fabrica.
Adaptación: Argon compone/parchea una receta; la revisión mide; máx. 4 intentos, ≤US$0.75 por llamada, ≤US$3 por movimiento,
20 s entre llamadas, parar ante 429, sin reintentos automáticos pagos. El ledger se escribe ANTES de cada llamada."""
import json, time, re, unicodedata
from datetime import datetime

INTENTOS_MAX = 4; TOPE_LLAMADA = 0.75; TOPE_MOVIMIENTO = 3.0; PAUSA_S = 20

def norm(s): return ''.join(c for c in unicodedata.normalize('NFKD', str(s or '').lower()) if not unicodedata.combining(c))

def clasificar(accion, texto=''):
    t = norm(accion) + ' ' + norm(texto)
    if re.search(r'\bvuel|\bvola|\bdespeg|\baterriz.*(volando|desde el aire)', t):
        return 'vuelo_alas' if re.search(r'\bala(s)?\b|aletea', t) else 'vuelo_sin_alas'
    if re.search(r'pelea|golpe|patada|punetazo|karate|boxe', t): return 'pelea_exagerada'
    if re.search(r'humo|liquid|tentacul|deform|sin forma', t): return 'sin_forma'
    return 'normal'

ROLES_EXIGIDOS = {'vuelo_alas': ['ala'], 'sin_forma': ['tentaculo|deforme']}

def enrutar(pedido, kimodo_on=False, roles_molde=None):
    """Devuelve la decisión (programa). Si no hay clip ni método: Kimodo (texto) si está encendido; si no, reporte_rechazo."""
    tipo = clasificar(pedido.get('accion'), pedido.get('texto'))
    dec = {"personaje": pedido.get('personaje'), "accion": pedido.get('accion'), "tipo_movimiento": tipo}
    if tipo in ROLES_EXIGIDOS and roles_molde is not None:
        falta = [r for r in ROLES_EXIGIDOS[tipo] if not any(re.search(r, x) for x in roles_molde)]
        if falta:
            dec.update(tipo_ejecucion='rechazo', metodo='STOP pedir_a_fabrica', reporte_rechazo=reporte_rechazo(
                pedido, 1, [{"check": "MOLDE_FALTA_HUESO", "medido": falta, "campos_receta_sospechosos": []}], 0.0,
                instruccion="No parchear receta: pedir a la fábrica de personajes los huesos/plantilla faltantes.")); return dec
    if tipo == 'vuelo_alas': dec.update(tipo_ejecucion='receta', metodo='receta vuelo_alas (vuelo_alas.py)'); return dec
    if tipo == 'vuelo_sin_alas': dec.update(tipo_ejecucion='receta', metodo='receta vuelo_sin_alas (vuelo_alas.py)'); return dec
    if tipo == 'pelea_exagerada' and not kimodo_on:
        dec.update(tipo_ejecucion='rechazo', metodo='sin clip de pelea en biblioteca', reporte_rechazo=reporte_rechazo(
            pedido, 1, [{"check": "SIN_CLIP", "medido": "pelea", "campos_receta_sospechosos": ["fuente_bloques.clips_mocap"]}], 0.0))
        return dec
    if kimodo_on:
        dec.update(tipo_ejecucion='kimodo', metodo='Kimodo GPU (texto)', kimodo_texto=texto_kimodo(pedido)); return dec
    dec.update(tipo_ejecucion='rechazo', metodo='sin clip ni método', reporte_rechazo=reporte_rechazo(
        pedido, 1, [{"check": "SIN_METODO", "medido": pedido.get('accion'), "campos_receta_sospechosos": ["fuente_bloques"]}], 0.0))
    return dec

def texto_kimodo(p):
    return f"{p.get('sujeto') or 'A person'} {norm(p.get('accion'))}s" + (f": {p.get('texto')}" if p.get('texto') else '')

def reporte_rechazo(pedido, intento, fallos, gasto, instruccion=None):
    return {"schema": "reporte_rechazo/v1", "receta_id": pedido.get('receta_id') or f"{pedido.get('personaje')}:{pedido.get('accion')}",
            "intento": intento, "intentos_max": INTENTOS_MAX, "gasto_acumulado_usd": round(gasto, 4), "tope_usd": TOPE_MOVIMIENTO,
            "resultado": "RECHAZO", "fallos": fallos, "historial_cambios": pedido.get('historial', []),
            "instruccion_a_argon": instruccion or "Devuelve la misma receta cambiando SOLO los campos listados en campos_receta_sospechosos. No repitas valores del historial que ya fallaron. No inventes huesos."}

CHECK_A_CAMPOS = {
    'ACELERACION': ['fuente_bloques.trayectoria.acel_max_m_s2', 'fuente_bloques.trayectoria.waypoints', 'retime.factor'],
    'ACEL_COM': ['fuente_bloques.trayectoria.acel_max_m_s2', 'fuente_bloques.trayectoria.waypoints', 'retime.factor'],
    'VEL_ANG': ['fuente_bloques.trayectoria.waypoints', 'exageracion'],
    'JERK_ALTO': ['fuente_bloques.trayectoria.waypoints', 'fuente_bloques.trayectoria.acel_max_m_s2', 'limites_revision.jerk_max_m_s3'],
    'RESBALE_PIE': ['limites_revision.pie_apoyado_vel_max_m_s'],
    'PENETRACION': ['fuente_bloques.trayectoria.waypoints'],
    'CAMARA_4G': ['exageracion.camera_shake'],
}

def adaptar(pedido, receta, ejecutar, revisar, argon_parche, ledger_antes, ledger_despues, log=print):
    """Bucle de adaptación autónoma. ejecutar(receta)->resultado; revisar(resultado)->lista de fallos [{check,...}];
    argon_parche(reporte, receta)->(receta_nueva, usd, http_status). Sin Argon (argon_parche=None) solo mide y reporta."""
    gasto = 0.0; hist = []
    for intento in range(1, INTENTOS_MAX + 1):
        res = ejecutar(receta); fallos = revisar(res)
        if not fallos: return {"estado": "OK", "intento": intento, "receta": receta, "gasto_usd": gasto, "historial": hist}
        for f in fallos: f.setdefault('campos_receta_sospechosos', CHECK_A_CAMPOS.get(f['check'], []))
        if any(f['check'] == 'MOLDE_FALTA_HUESO' for f in fallos):
            return {"estado": "STOP_pedir_a_fabrica", "reporte_rechazo": reporte_rechazo(pedido, intento, fallos, gasto), "gasto_usd": gasto}
        rep = reporte_rechazo(dict(pedido, historial=hist), intento, fallos, gasto)
        if argon_parche is None or intento == INTENTOS_MAX or gasto + TOPE_LLAMADA > TOPE_MOVIMIENTO + 1e-9:
            return {"estado": "RECHAZO_FINAL", "reporte_rechazo": rep, "gasto_usd": gasto, "historial": hist}
        if intento > 1: time.sleep(PAUSA_S)
        ledger_antes({"que": f"Argon parche receta {rep['receta_id']} intento {intento + 1}", "tope_usd": TOPE_LLAMADA})
        nueva, usd, status = argon_parche(rep, receta)
        gasto += float(usd or 0); ledger_despues({"usd": usd, "status": status})
        if status == 429: return {"estado": "STOP_429", "reporte_rechazo": rep, "gasto_usd": gasto}
        cambiados = [k for k in rep['fallos'][0]['campos_receta_sospechosos']]
        hist.append({"intento": intento + 1, "campos_cambiados": cambiados, "cuando": datetime.now().astimezone().isoformat(timespec='seconds')})
        receta = nueva
    return {"estado": "RECHAZO_FINAL", "gasto_usd": gasto, "historial": hist}
