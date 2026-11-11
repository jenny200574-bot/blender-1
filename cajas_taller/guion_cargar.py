# -*- coding: utf-8 -*-
"""MYIA · Taller n8n · 3b Cargar mi guion (gratis, 5-nov-2026).
Sube el guion COMPLETO del capítulo (txt/md) por el formulario de n8n y lo deja
como guion canónico en studio.db (misma puerta que «Cargar mi guion» del panel).
Sin red, sin IA, sin ledger.

Uso (entrada restringida n8ntaller):
  paso00_cadena guion revisar --canal C --capitulo N|ep-...
  paso00_cadena guion ficha   --canal C --sesion S --datos B64URL(json)
  paso00_cadena guion subir   --canal C --sesion S --nombre F --parte i --de n --datos B64URL
  paso00_cadena guion guardar --canal C --sesion S [--capitulo N|ep-...] [--quien QUIEN]
"""
from __future__ import annotations
import argparse, base64, hashlib, json, os, re, secrets, sqlite3, time
from pathlib import Path

CAJAS = Path('/opt/myia-taller-n8n/cajas')
TRABAJO = Path('/opt/myia-taller-n8n/trabajo/paso00_cadena')
STUDIO_DB = Path('/opt/myia-staging-arreglos-20261026/demo_chat/estudio/web/data/studio.db')
TABLA = 'myia_capitulo_guion'
MAX_CARACTERES = 2_000_000
ID_OK = re.compile(r'^[A-Za-z0-9._-]{1,120}$')
NOMBRE_OK = re.compile(r'^[A-Za-z0-9._-]{1,200}$')
EXT_OK = {'.txt', '.md', '.text', '.markdown'}


def ahora():
    return time.strftime('%Y-%m-%dT%H:%M:%S%z')


def b64(s: str) -> bytes:
    s = str(s or '')
    return base64.urlsafe_b64decode(s + '=' * (-len(s) % 4))


def sha_txt(t: str) -> str:
    return hashlib.sha256((t or '').encode('utf-8')).hexdigest()


def entrada(canal: str) -> Path:
    d = TRABAJO / canal / '_entrada_guion'
    d.mkdir(parents=True, exist_ok=True)
    return d


def sesion_dir(canal: str, s: str) -> Path:
    if not ID_OK.fullmatch(str(s or '')):
        raise ValueError('sesión no válida')
    d = entrada(canal) / s
    d.mkdir(parents=True, exist_ok=True)
    return d


def wj(p: Path, o):
    p.parent.mkdir(parents=True, exist_ok=True)
    t = p.with_suffix(p.suffix + '.tmp')
    t.write_text(json.dumps(o, ensure_ascii=False, indent=1), encoding='utf-8')
    os.replace(t, p)


def rj(p: Path, d=None):
    try:
        return json.loads(p.read_text(encoding='utf-8'))
    except Exception:
        return d


def db(rw=False):
    if rw:
        return sqlite3.connect(str(STUDIO_DB))
    return sqlite3.connect(f'file:{STUDIO_DB}?mode=ro', uri=True)


def tablas(con):
    con.execute(
        f'CREATE TABLE IF NOT EXISTS {TABLA}(id TEXT PRIMARY KEY, episode_id TEXT NOT NULL, channel_id TEXT, fuente TEXT NOT NULL, '
        'estado TEXT NOT NULL, canonico INTEGER DEFAULT 0, guion TEXT, sha256 TEXT, caracteres INTEGER, nombre_archivo TEXT, ref TEXT, '
        'indicaciones TEXT, entradas_sha256 TEXT, propuesta TEXT, errores TEXT, avisos TEXT, modelo TEXT, nivel TEXT, usd REAL DEFAULT 0, '
        'intentos INTEGER DEFAULT 0, pedido_sha256 TEXT, pedido_caracteres INTEGER, cargado_por TEXT, aprobado_por TEXT, aprobado_at TEXT, '
        'created_at TEXT, updated_at TEXT)'
    )
    con.execute(f'CREATE INDEX IF NOT EXISTS {TABLA}_ep ON {TABLA}(episode_id, canonico)')


def episodio(con, canal: str, capitulo: str):
    if str(capitulo).startswith('ep-'):
        r = con.execute('SELECT id, channel_id, number, title FROM episodes WHERE id=? AND channel_id=?', (capitulo, canal)).fetchone()
    else:
        r = con.execute('SELECT id, channel_id, number, title FROM episodes WHERE channel_id=? AND number=?', (canal, int(capitulo))).fetchone()
    if not r:
        raise ValueError(f'no hay capítulo {capitulo} en el canal {canal}')
    return {'id': r[0], 'channel_id': r[1], 'number': r[2], 'title': r[3]}


def canonico(con, eid: str):
    r = con.execute(
        f'SELECT id, episode_id, channel_id, fuente, estado, canonico, sha256, caracteres, nombre_archivo, updated_at '
        f'FROM {TABLA} WHERE episode_id=? AND canonico=1 ORDER BY updated_at DESC', (eid,)
    ).fetchone()
    if not r:
        return None
    return {
        'id': r[0], 'episode_id': r[1], 'channel_id': r[2], 'fuente': r[3], 'estado': r[4],
        'canonico': bool(r[5]), 'sha256': r[6], 'caracteres': r[7], 'nombre_archivo': r[8], 'updated_at': r[9],
    }


def revisar(canal: str, capitulo: str):
    if not ID_OK.fullmatch(canal):
        raise ValueError('canal no válido')
    con = db(False)
    try:
        tablas(con)
        e = episodio(con, canal, capitulo)
        c = canonico(con, e['id'])
        return {
            'ok': True,
            'accion': 'guion revisar',
            'canal': canal,
            'capitulo': e['number'],
            'episodio': e['id'],
            'titulo': e.get('title'),
            'listo_paso00': bool(c),
            'canonico': c,
            'aviso': None if c else 'Falta el guion canónico: súbelo con el formulario «3b · formulario cargar guion» (txt/md) o déjalo en el panel del capítulo.',
        }
    finally:
        con.close()


def ficha(canal: str, s: str, datos: str):
    if not ID_OK.fullmatch(canal):
        raise ValueError('canal no válido')
    d = json.loads(b64(datos).decode('utf-8'))
    if not isinstance(d, dict):
        raise ValueError('ficha no es un objeto')
    cap = str(d.get('capitulo') or d.get('episodio') or '').strip()
    quien = str(d.get('quien') or 'ricardo-n8n').strip()[:80]
    nombre = str(d.get('nombre_archivo') or '').strip()[:200]
    wj(sesion_dir(canal, s) / 'ficha.json', {'capitulo': cap, 'quien': quien, 'nombre_archivo': nombre, 'canal': canal})
    return {'ok': True, 'accion': 'guion ficha', 'sesion': s, 'canal': canal, 'capitulo': cap}


def subir(canal: str, s: str, nombre: str, parte: int, de: int, datos: str):
    if not ID_OK.fullmatch(canal):
        raise ValueError('canal no válido')
    if not NOMBRE_OK.fullmatch(nombre or ''):
        raise ValueError('nombre de archivo no válido')
    ext = Path(nombre).suffix.lower()
    if ext not in EXT_OK:
        raise ValueError('solo se aceptan .txt o .md')
    parte, de = int(parte), int(de)
    if parte < 1 or de < 1 or parte > de:
        raise ValueError('parte/de inválidos')
    d = sesion_dir(canal, s)
    (d / 'partes').mkdir(exist_ok=True)
    (d / 'partes' / f'{nombre}.{parte:04d}-de-{de:04d}').write_bytes(b64(datos))
    meta = rj(d / 'subidas.json', {'archivos': {}})
    meta['archivos'][nombre] = {'de': de, 'partes_ok': sorted({
        int(p.name.split('.')[-1].split('-')[0]) for p in (d / 'partes').glob(f'{nombre}.*')
    })}
    wj(d / 'subidas.json', meta)
    return {'ok': True, 'accion': 'guion subir', 'parte': parte, 'de': de, 'nombre': nombre}


def _ensamblar(d: Path, nombre: str, de: int) -> bytes:
    bits = []
    for i in range(1, de + 1):
        p = d / 'partes' / f'{nombre}.{i:04d}-de-{de:04d}'
        if not p.is_file():
            raise ValueError(f'falta la parte {i}/{de} de {nombre}')
        bits.append(p.read_bytes())
    return b''.join(bits)


def guardar(canal: str, s: str, capitulo: str | None = None, quien: str | None = None):
    if not ID_OK.fullmatch(canal):
        raise ValueError('canal no válido')
    d = sesion_dir(canal, s)
    fi = rj(d / 'ficha.json')
    if not fi:
        raise ValueError('la sesión no tiene ficha')
    cap = str(capitulo or fi.get('capitulo') or '').strip()
    if not cap:
        raise ValueError('falta --capitulo (número o ep-…)')
    sub = rj(d / 'subidas.json', {}).get('archivos') or {}
    if len(sub) != 1:
        raise ValueError('sube exactamente UN archivo de guion (.txt o .md)')
    nombre, info = next(iter(sub.items()))
    raw = _ensamblar(d, nombre, int(info['de']))
    # decodificar texto tal cual (utf-8; si falla, latin-1 sin reescribir saltos)
    try:
        texto = raw.decode('utf-8')
    except UnicodeDecodeError:
        texto = raw.decode('latin-1')
    if not texto.strip():
        raise ValueError('el archivo del guion está vacío')
    n = len(texto)
    if n > MAX_CARACTERES:
        raise ValueError(f'el guion tiene {n} caracteres (máx {MAX_CARACTERES}); no se recorta')
    nombre_archivo = str(fi.get('nombre_archivo') or nombre)[:200]
    quien = str(quien or fi.get('quien') or 'ricardo-n8n')[:80]

    con = db(True)
    try:
        tablas(con)
        e = episodio(con, canal, cap)
        eid = e['id']
        # snapshot del canónico anterior (para rollback de pruebas)
        prev = canonico(con, eid)
        if prev:
            wj(d / 'canonico_antes.json', prev)
            # also dump previous text hash only (not full text in session meta)
        rid = 'cg3-' + secrets.token_hex(6)
        now = ahora()
        con.execute(f'UPDATE {TABLA} SET canonico=0, updated_at=? WHERE episode_id=? AND canonico=1', (now, eid))
        con.execute(
            f'INSERT INTO {TABLA}(id,episode_id,channel_id,fuente,estado,canonico,guion,sha256,caracteres,nombre_archivo,ref,cargado_por,'
            'aprobado_por,aprobado_at,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)',
            (rid, eid, e['channel_id'], 'usuario', 'cargado', 1, texto, sha_txt(texto), n, nombre_archivo, f'n8n-3b:{s}',
             quien, quien, now, now, now),
        )
        con.commit()
        c = canonico(con, eid)
        # copy assembled file to trabajo for audit
        dest = TRABAJO / canal / f"cap{int(e['number']):02d}_{eid}" / 'archivo'
        dest.mkdir(parents=True, exist_ok=True)
        outp = dest / f'guion_cargado_{rid}{Path(nombre).suffix.lower() or ".txt"}'
        outp.write_bytes(raw)
        return {
            'ok': True,
            'accion': 'guion guardar',
            'canal': canal,
            'capitulo': e['number'],
            'episodio': eid,
            'guardado': {'id': rid, 'sha256': sha_txt(texto), 'caracteres': n, 'nombre_archivo': nombre_archivo, 'archivo_auditoria': str(outp)},
            'canonico': c,
            'canonico_antes': prev,
            'listo_paso00': True,
        }
    finally:
        con.close()


def main(argv):
    ap = argparse.ArgumentParser(prog='guion')
    ap.add_argument('accion', choices=['revisar', 'ficha', 'subir', 'guardar'])
    ap.add_argument('--canal', required=True)
    ap.add_argument('--capitulo')
    ap.add_argument('--sesion')
    ap.add_argument('--datos')
    ap.add_argument('--nombre')
    ap.add_argument('--parte', type=int)
    ap.add_argument('--de', type=int)
    ap.add_argument('--quien')
    a = ap.parse_args(argv)
    if a.accion == 'revisar':
        if not a.capitulo:
            raise SystemExit('falta --capitulo')
        return revisar(a.canal, a.capitulo)
    if a.accion == 'ficha':
        return ficha(a.canal, a.sesion, a.datos)
    if a.accion == 'subir':
        return subir(a.canal, a.sesion, a.nombre, a.parte, a.de, a.datos)
    if a.accion == 'guardar':
        return guardar(a.canal, a.sesion, a.capitulo, a.quien)
    raise SystemExit('accion no válida')


if __name__ == '__main__':
    import sys
    print(json.dumps(main(sys.argv[1:]), ensure_ascii=False))
