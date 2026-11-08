"""Carga un módulo del motor por su ruta real.

El núcleo solo pone heredado/ en sys.path. Un import plano no ve
motor/malla_cabeza.py. Una copia bajo heredado/ no es la fuente.
"""
import importlib.util
from pathlib import Path


def cargar(nombre):
    if not isinstance(nombre, str) or not nombre.isidentifier() or nombre.startswith('_'):
        raise ValueError('Nombre de módulo no permitido')
    ruta = Path(__file__).resolve().parents[1] / (nombre + '.py')
    if not ruta.is_file():
        raise ModuleNotFoundError(
            'Falta el módulo único ' + str(ruta) + '. No se usa una copia bajo heredado/.'
        )
    spec = importlib.util.spec_from_file_location('motor_unico_' + nombre, ruta)
    if spec is None or spec.loader is None:
        raise ModuleNotFoundError(str(ruta))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod
