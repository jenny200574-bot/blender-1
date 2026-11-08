"""Interpolación de acciones de cámara. Blender 4.2 usa fcurves; 4.4+ usa layers."""

def curvas_de_accion(action):
    """Devuelve las F-Curves reales. No inventa curvas si el API no las trae."""
    if action is None:
        raise ValueError('Acción de cámara ausente; no se cambia la interpolación')
    if hasattr(action, 'layers'):
        curvas = []
        for layer in action.layers:
            for strip in layer.strips:
                for slot in getattr(action, 'slots', []):
                    bag = strip.channelbag(slot)
                    if bag is not None:
                        curvas.extend(bag.fcurves)
        return curvas
    if hasattr(action, 'fcurves'):
        return list(action.fcurves)
    raise ValueError('La acción no tiene act.layers ni act.fcurves; no se fuerza la interpolación')

def fijar_constante(action):
    """Un keyframe por cuadro: interpolación CONSTANT, sin tramos inventados."""
    n = 0
    for curva in curvas_de_accion(action):
        for punto in curva.keyframe_points:
            punto.interpolation = 'CONSTANT'
            n += 1
    return n
