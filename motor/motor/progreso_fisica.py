"""Progreso de etapa 13 (física final): líneas FISICA_PROGRESO y progreso_fisica.json atómico."""
import json
import os
import time
from pathlib import Path


class Progreso:
    def __init__(self, salida, reloj=time.monotonic, pared=time.time, imprimir=print, cada_s=5.0):
        self.salida = Path(salida) if salida is not None else None
        self.reloj = reloj
        self.pared = pared
        self.imprimir = imprimir
        self.cada_s = cada_s
        self.t0 = reloj()
        self.ultimo = None
        self.estado = {'estado': 'EN_CURSO', 'pid': os.getpid(), 'etapa': 13, 'inicio_unix': pared()}

    def transcurrido(self):
        return self.reloj() - self.t0

    def _rss_mb(self):
        try:
            import resource
            return round(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024.0, 1)
        except Exception:
            return None

    def _escribir(self):
        if self.salida is None:
            return
        self.salida.mkdir(parents=True, exist_ok=True)
        destino = self.salida / 'progreso_fisica.json'
        parcial = destino.with_name(destino.name + '.parcial')
        parcial.write_text(json.dumps(self.estado, ensure_ascii=False, default=str), encoding='utf-8')
        os.replace(parcial, destino)

    FIJOS = frozenset(('estado', 'pid', 'etapa', 'inicio_unix', 'fase', 'segundos', 'actualizado_unix', 'rss_mb'))

    def marcar(self, forzar=False, **datos):
        if 'fase' in datos and datos['fase'] != self.estado.get('fase'):
            for k in [k for k in self.estado if k not in self.FIJOS]:
                del self.estado[k]
        self.estado.update(datos)
        self.estado['rss_mb'] = self._rss_mb()
        ahora = self.reloj()
        if not forzar and self.ultimo is not None and ahora - self.ultimo < self.cada_s:
            return False
        self.ultimo = ahora
        self.estado['segundos'] = round(ahora - self.t0, 3)
        self.estado['actualizado_unix'] = self.pared()
        self._escribir()
        self.imprimir('FISICA_PROGRESO ' + json.dumps(self.estado, ensure_ascii=False, default=str), flush=True)
        return True

    def cerrar(self, estado, **datos):
        self.estado.update(datos)
        self.estado['estado'] = estado
        self.estado['rss_mb'] = self._rss_mb()
        self.estado['segundos'] = round(self.reloj() - self.t0, 3)
        self.estado['actualizado_unix'] = self.pared()
        self._escribir()
        self.imprimir('FISICA_PROGRESO ' + json.dumps(self.estado, ensure_ascii=False, default=str), flush=True)
