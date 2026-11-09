"""Helpers del modo directa SB (sin bpy): diagnóstico y opciones experimentales."""
import re

# Solo geometría de escenario (no props de historia tipo obj-* ni personajes).
_PREFIJOS_DESPEJE = ('muro_', 'amb-esc-', 'pared_', 'techo_', 'suelo_', 'cortina_', 'ventana_')


def es_geometria_escenario_auto(nombre):
    if not nombre:
        return False
    low = nombre.lower()
    return any(low.startswith(p) for p in _PREFIJOS_DESPEJE) or low.startswith('muro') or 'cortinas' in low


def es_entidad_historia(nombre, act_ids, act_mesh_names):
    if not nombre:
        return False
    act_ids = act_ids or ()
    if nombre in act_ids or nombre in (act_mesh_names or ()):
        return True
    return any(nombre == pid or nombre.startswith(pid + '.') or nombre.startswith(pid + '_') for pid in act_ids)


def tapadores_escenario_desde_malos(malos, act_ids=(), act_mesh_names=()):
    out = set()
    for row in malos or []:
        msg = row[1] if len(row) > 1 else ''
        if 'otro personaje' in msg:
            continue
        for m in re.finditer(r'\(([^)]+)\)', msg):
            nombre = m.group(1).strip()
            if nombre.startswith('escenario:'):
                nombre = nombre.split('escenario:', 1)[1].strip()
            if nombre and not es_entidad_historia(nombre, act_ids, act_mesh_names) and es_geometria_escenario_auto(nombre):
                if any(x in msg for x in ('escenario', 'pegada', 'dentro de geometría')):
                    out.add(nombre)
                elif 'tapado' in msg and msg.startswith('cámara'):
                    out.add(nombre)
    return frozenset(out)


def clasificar_motivos_directa(malos):
    cats = {'encuadre': 0, 'oclusion_escenario': 0, 'holgura_escenario': 0, 'eje_180': 0, 'inclinacion_roll': 0, 'cara_espalda': 0, 'otros': 0}
    for row in malos or []:
        msg = row[1] if len(row) > 1 else ''
        if 'fuera de cuadro' in msg:
            cats['encuadre'] += 1
        elif 'tapado' in msg and 'escenario' in msg:
            cats['oclusion_escenario'] += 1
        elif 'pegada' in msg or 'dentro de geometría' in msg:
            cats['holgura_escenario'] += 1
        elif '180' in msg:
            cats['eje_180'] += 1
        elif 'inclinación' in msg or 'roll' in msg:
            cats['inclinacion_roll'] += 1
        elif 'espaldas' in msg:
            cats['cara_espalda'] += 1
        else:
            cats['otros'] += 1
    return cats


def retroceder_tray_holgura(tray, frac):
    if not frac or frac <= 0:
        return tray
    salida = []
    for x in tray:
        y = dict(x)
        mira = y.get('mira')
        if mira is not None:
            d = y['loc'] - mira
            if hasattr(d, 'length') and d.length > 1e-6:
                y['loc'] = y['loc'] + d.normalized() * (d.length * float(frac))
        salida.append(y)
    return salida
