"""Progreso, tope de tiempo y cancelación de la etapa de cámara.

No decide si una toma pasa. Escribe una línea CAMARA_PROGRESO con flush y un
progreso_camara.json atómico para que un supervisor lo lea aunque el log esté
en búfer. Si se agota MOTOR_CAMARA_LIMITE_S o aparece el archivo de
MOTOR_CANCELAR_ARCHIVO, levanta CamaraInterrumpida: la etapa no termina en falso OK.
Sin bpy: se prueba con Python normal.
"""
import json
import math
import os
import time
from pathlib import Path

ENV_LIMITE = 'MOTOR_CAMARA_LIMITE_S'
ENV_CANCELAR = 'MOTOR_CANCELAR_ARCHIVO'


class Interrupcion(BaseException):
    """Corte pedido desde fuera (tope o cancelación). No hereda de Exception para que
    ningún `except Exception` del motor lo convierta en un fallo de candidato y siga."""
    codigo = 'INTERRUMPIDO'


class CamaraInterrumpida(Interrupcion):
    def __init__(self, codigo, detalle):
        self.codigo = codigo
        self.detalle = detalle
        self.faltantes = []
        super().__init__(codigo + ': ' + detalle)


def limite_desde_entorno(entorno=None):
    entorno = os.environ if entorno is None else entorno
    crudo = entorno.get(ENV_LIMITE)
    if crudo is None or str(crudo).strip() == '':
        return None
    try:
        valor = float(crudo)
    except ValueError:
        raise ValueError(ENV_LIMITE + ' no es un número de segundos: ' + repr(crudo))
    if not math.isfinite(valor) or valor <= 0:
        raise ValueError(ENV_LIMITE + ' debe ser > 0 segundos: ' + repr(crudo))
    return valor


class Progreso:
    def __init__(self, salida, limite_s=None, cancelar=None, reloj=time.monotonic, pared=time.time,
                 imprimir=print, cada_s=5.0):
        self.salida = Path(salida) if salida is not None else None
        self.limite_s = limite_s
        self.cancelar = Path(cancelar) if cancelar else None
        self.reloj = reloj
        self.pared = pared
        self.imprimir = imprimir
        self.cada_s = cada_s
        self.t0 = reloj()
        self.ultimo = None
        self.estado = {'estado': 'EN_CURSO', 'pid': os.getpid(), 'inicio_unix': pared(), 'limite_s': limite_s}

    @classmethod
    def desde_entorno(cls, salida, entorno=None, **k):
        entorno = os.environ if entorno is None else entorno
        return cls(salida, limite_s=limite_desde_entorno(entorno), cancelar=entorno.get(ENV_CANCELAR) or None, **k)

    def transcurrido(self):
        return self.reloj() - self.t0

    def revisar(self):
        if self.cancelar is not None and self.cancelar.exists():
            raise CamaraInterrumpida('CANCELADO', 'apareció ' + str(self.cancelar))
        if self.limite_s is not None and self.transcurrido() > self.limite_s:
            raise CamaraInterrumpida('CAMARA_TIEMPO_AGOTADO', 'la cámara pasó de %.0f s (%s)' % (self.limite_s, ENV_LIMITE))

    def _escribir(self):
        if self.salida is None:
            return
        self.salida.mkdir(parents=True, exist_ok=True)
        destino = self.salida / 'progreso_camara.json'
        parcial = destino.with_name(destino.name + '.parcial')
        parcial.write_text(json.dumps(self.estado, ensure_ascii=False, default=str), encoding='utf-8')
        os.replace(parcial, destino)

    FIJOS = frozenset(('estado', 'pid', 'inicio_unix', 'limite_s', 'lotes_por_cuadro', 'toma', 'toma_n', 'tomas',
                       'frame_ini', 'frame_fin', 'fase', 'segundos', 'actualizado_unix', 'rss_mb',
                       'meshes_total', 'meshes_sin_usuarios', 'purga_meshes'))

    def marcar(self, forzar=False, **datos):
        """Actualiza el estado. Escribe si forzar o si pasaron cada_s desde la última escritura.
        Al cambiar de fase se borran los contadores de la fase anterior."""
        self.revisar()
        if 'fase' in datos and datos['fase'] != self.estado.get('fase'):
            for k in [k for k in self.estado if k not in self.FIJOS]:
                del self.estado[k]
        self.estado.update(datos)
        ahora = self.reloj()
        if not forzar and self.ultimo is not None and ahora - self.ultimo < self.cada_s:
            return False
        self.ultimo = ahora
        self.estado['segundos'] = round(ahora - self.t0, 3)
        self.estado['actualizado_unix'] = self.pared()
        self._escribir()
        self.imprimir('CAMARA_PROGRESO ' + json.dumps(self.estado, ensure_ascii=False, default=str), flush=True)
        return True

    def cerrar(self, estado, **datos):
        self.estado.update(datos)
        self.estado['estado'] = estado
        self.estado['segundos'] = round(self.reloj() - self.t0, 3)
        self.estado['actualizado_unix'] = self.pared()
        self._escribir()
        self.imprimir('CAMARA_PROGRESO ' + json.dumps(self.estado, ensure_ascii=False, default=str), flush=True)
