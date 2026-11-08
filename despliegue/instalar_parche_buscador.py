#!/usr/bin/env python3
"""Instala el buscador de posición sobre el candidato que ya tiene el parche de 13.

No toca fisica_final.py. Si un hash previo no es el de avance11, no escribe nada.
Por defecto solo informa. --aplicar escribe.
"""
import argparse
import hashlib
import json
import os
import sys
from pathlib import Path

FISICA = 'motor/fisica_final.py'
FISICA_SHA = '3423c9a777eb0157d49eb90869f39227fb7cf834322e2705a605a37a66d418d2'


def sha256(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def cargar(manifiesto):
    data = json.loads(Path(manifiesto).read_text(encoding='utf-8'))
    if data.get('esquema') != 'parche_buscador_posicion/1':
        raise SystemExit('El manifiesto no es parche_buscador_posicion/1')
    archivos = data.get('archivos')
    if not isinstance(archivos, list) or not archivos:
        raise SystemExit('El manifiesto no lista archivos')
    rutas = [item.get('ruta') for item in archivos]
    if any(not isinstance(ruta, str) or not ruta or ruta.startswith('/') or '..' in Path(ruta).parts for ruta in rutas):
        raise SystemExit('Ruta de paquete no permitida')
    if len(set(rutas)) != len(rutas):
        raise SystemExit('Rutas repetidas')
    if FISICA in rutas or any(ruta.endswith('fisica_final.py') for ruta in rutas):
        raise SystemExit('El paquete intenta reemplazar fisica_final.py')
    return data


def revisar(destino, origen, data):
    destino = Path(destino)
    origen = Path(origen)
    errores = []
    fisica = destino / FISICA
    if not fisica.is_file():
        errores.append('falta ' + FISICA + '; no es el candidato y no se crea')
    elif sha256(fisica) != FISICA_SHA:
        errores.append(FISICA + ' no tiene el hash del VPS ' + FISICA_SHA + '; no se reemplaza la física')
    for item in data['archivos']:
        ruta = item['ruta']
        src = origen / ruta
        dst = destino / ruta
        if not src.is_file():
            errores.append('falta el archivo nuevo en el paquete: ' + ruta)
            continue
        if sha256(src) != item['despues']:
            errores.append('el paquete no trae el hash nuevo de ' + ruta)
        antes = item['antes']
        if antes is None:
            if dst.exists():
                errores.append('ya existe ' + ruta + '; no se sobrescribe un archivo que debía faltar')
        else:
            if not dst.is_file():
                errores.append('falta el archivo previo ' + ruta)
            elif sha256(dst) != antes:
                errores.append('hash previo distinto en ' + ruta + '; no se pisa un cambio concurrente')
    return errores


def aplicar(destino, origen, data):
    destino = Path(destino)
    origen = Path(origen)
    fisica = destino / FISICA
    hash_fisica = sha256(fisica)
    for item in data['archivos']:
        dst = destino / item['ruta']
        if item['antes'] is not None and sha256(dst) != item['antes']:
            return ['el hash cambió antes de escribir ' + item['ruta'] + '; no se escribió ese archivo']
        dst.parent.mkdir(parents=True, exist_ok=True)
        parcial = dst.with_name(dst.name + '.parcial_buscador')
        parcial.write_bytes((origen / item['ruta']).read_bytes())
        os.replace(parcial, dst)
        if sha256(dst) != item['despues']:
            return ['la escritura de ' + item['ruta'] + ' no coincide con el hash nuevo']
    if sha256(fisica) != hash_fisica or sha256(fisica) != FISICA_SHA:
        return [FISICA + ' cambió durante la instalación']
    return []


def main(argv=None):
    parser = argparse.ArgumentParser(description='Instala el buscador si los hashes previos coinciden')
    parser.add_argument('--destino', required=True)
    parser.add_argument('--origen', required=True)
    parser.add_argument('--manifiesto', required=True)
    parser.add_argument('--aplicar', action='store_true')
    args = parser.parse_args(argv)
    data = cargar(args.manifiesto)
    errores = revisar(args.destino, args.origen, data)
    if errores:
        for linea in errores:
            print('RECHAZADO', linea)
        return 2
    if not args.aplicar:
        print('SECO ' + str(len(data['archivos'])) + ' archivos listos; fisica_final.py no se toca. Falta --aplicar.')
        return 0
    fallos = aplicar(args.destino, args.origen, data)
    if fallos:
        for linea in fallos:
            print('FALLO', linea)
        return 3
    print('APLICADO ' + str(len(data['archivos'])) + ' archivos. fisica_final.py sigue en ' + FISICA_SHA)
    return 0


if __name__ == '__main__':
    sys.exit(main())
