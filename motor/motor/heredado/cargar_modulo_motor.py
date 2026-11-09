"""Carga un módulo del motor por su ruta real.

El núcleo solo pone heredado/ en sys.path. Un import plano no ve
motor/malla_cabeza.py. Una copia bajo heredado/ no es la fuente.
"""
import importlib.util
from pathlib import Path


def _rutas_modulo(nombre):
    here = Path(__file__).resolve().parent
    vistos = set()
    for base in (here.parent, here.parent / 'motor', here.parents[1], here.parents[1] / 'motor'):
        base = base.resolve()
        if base in vistos:
            continue
        vistos.add(base)
        p = base / (nombre + '.py')
        if p.is_file():
            yield p

def cargar(nombre):
    if not isinstance(nombre, str) or not nombre.isidentifier() or nombre.startswith('_'):
        raise ValueError('Nombre de módulo no permitido')
    candidatas = list(_rutas_modulo(nombre))
    if not candidatas:
        here = Path(__file__).resolve().parent
        esperado = (here.parent / (nombre + '.py')).resolve()
        raise ModuleNotFoundError(
            'Falta el módulo único ' + str(esperado) + '. No se usa una copia bajo heredado/.'
        )
    ruta = candidatas[0]
    spec = importlib.util.spec_from_file_location('motor_unico_' + nombre, ruta)
    if spec is None or spec.loader is None:
        raise ModuleNotFoundError(str(ruta))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod
