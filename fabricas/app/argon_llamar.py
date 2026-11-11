# -*- coding: utf-8 -*-
"""Una llamada a Argon (sin reintentos). Corre en el venv con google-genai. La credencial la resuelve el cliente existente
del motor (myia_argon._cliente) con la RUTA ya configurada en el motor v9; aquí no se abre ni se imprime ninguna clave.
Imprime UNA línea JSON: ok, tokens_entrada, tokens_salida, finish, codigo, error."""
import argparse, importlib.util, json, os, sys
from pathlib import Path
ap = argparse.ArgumentParser(); ap.add_argument('--prompt', default=''); ap.add_argument('--salida', default='')
ap.add_argument('--modelo', default='gemini-4-argon'); ap.add_argument('--max-out', type=int, default=32768); ap.add_argument('--nivel', default='HIGH'); ap.add_argument('--chequear', action='store_true'); ap.add_argument('--chequear-red', action='store_true')
a = ap.parse_args()
V9 = Path('/opt/myia-motor-v9/v9_motor_unico_20261107/pruebas_aisladas_01')
CLIENTE = Path('/opt/myia-motor-v9/v9_motor_unico_20261107/dependencias_externas/workspace/STAR_MOTOR_UNIVERSAL_v2_20261030/src/cajas/myia_argon.py')
def fin(**k): print(json.dumps(k, ensure_ascii=False)); sys.exit(0 if k.get('ok') else 1)
try:
    envf = Path('/opt/myia-fabricas/secretos/argon.env')   # la pone el operador: una línea MYIA_ARGON_CRED=<ruta> (600); aquí solo se lee la RUTA
    if not os.environ.get('MYIA_ARGON_CRED') and envf.is_file():
        for l in envf.read_text().splitlines():
            if l.startswith('MYIA_ARGON_CRED='): os.environ['MYIA_ARGON_CRED'] = l.split('=', 1)[1].strip()
    if not os.environ.get('MYIA_ARGON_CRED'):
        ruta = json.loads((V9 / 'config/argon_transporte.json').read_text()).get('existing_file')   # ruta, no contenido
        if ruta: os.environ['MYIA_ARGON_CRED'] = ruta
    spec = importlib.util.spec_from_file_location('myia_argon_cliente', CLIENTE); m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
    client = m._cliente()
    if a.chequear: fin(ok=True, chequeo='cliente Argon construido (sin red, sin costo)')
    if a.chequear_red:   # [20261110] chequeo gratis con red: token OAuth + metadatos del modelo (models.get, no genera ni factura)
        info = client.models.get(model=a.modelo)
        fin(ok=True, chequeo='token OAuth + models.get (sin generación, sin costo)', modelo=getattr(info, 'name', None))
    from google.genai import types
    conf = types.GenerateContentConfig(thinking_config=types.ThinkingConfig(thinking_level=a.nivel, include_thoughts=True),
                                       max_output_tokens=[REDACTED]
    texto, uso, finish = '', None, None
    for ch in client.models.generate_content_stream(model=a.modelo, contents=Path(a.prompt).read_text(encoding='utf-8'), config=conf):
        for c in ch.candidates or []:
            for p in (c.content.parts if c.content else []) or []:
                if not getattr(p, 'thought', False) and getattr(p, 'text', None): texto += p.text
            if c.finish_reason: finish = str(c.finish_reason)
        if ch.usage_metadata: uso = ch.usage_metadata
    Path(a.salida).write_text(texto, encoding='utf-8')
    tin = (uso.prompt_token_count or 0) if uso else None
    tout = ((uso.candidates_token_count or 0) + (uso.thoughts_token_count or 0)) if uso else None
    trunc = 'MAX_TOKENS' in str(finish)
    fin(ok=bool(texto) and not trunc, tokens_entrada=tin, tokens_salida=tout, finish=finish, caracteres=len(texto),
        error='respuesta truncada (MAX_TOKENS)' if trunc else None)
except Exception as e:
    cod = getattr(e, 'code', None) or getattr(e, 'status_code', None)
    if not isinstance(cod, int): cod = 429 if '429' in str(e)[:200] or 'RESOURCE_EXHAUSTED' in str(e)[:300] else None
    fin(ok=False, codigo=cod, error=f'{type(e).__name__}: {str(e)[:300]}')
