#!/usr/bin/env python3
"""PISTA INMI (2026-10-30): orden 109 — entrada «ver o109 …» (por la entrada SSH restringida, acción «ver» ya permitida).
  paso00_cadena ver o109 cubo01 --canal C --capitulo N [--escena 9] [--revalidar archivo]   → cubo 01 consolidado (cotiza; gratis)
  paso00_cadena ver o109 cubo02 --canal C --capitulo N [--escena 9] [--tomas 4]             → cubo 02 molde 3D por toma (gratis)
  paso00_cadena ver o109 cubo01o112 --canal C --capitulo N [--escena 9] [--revalidar archivo]  → o112: cubo 01 con EVENTOS detallados (cotiza; gratis)
  paso00_cadena ver o109 cubo02video --canal C --capitulo N [--escena 9]                     → o112: cubo 02v video gris 3D (gratis)
  paso00_cadena ver o109 cubo02poses --canal C --capitulo N [--escena 9] [--tomas 4]        → o110: cubo 02c molde con POSE por toma (gratis)
Desde n8n NUNCA paga: --correr no se acepta aquí (el pago va por la línea de comandos del taller con guarda + OK escrito de Ricardo)."""
import json, sys


def main(argv):
    if not argv or argv[0] not in ('cubo01', 'cubo02', 'cubo02poses', 'cubo01o112', 'cubo02video'): return {'ok': False, 'error': 'uso: ver o109 cubo01|cubo02 --canal … --capitulo …'}
    if '--correr' in argv: return {'ok': False, 'error': 'desde n8n no se paga: el cubo 01 solo cotiza aquí'}
    if argv[0] == 'cubo01':
        import cubo01_o109 as M
    elif argv[0] == 'cubo01o112':
        import cubo01_o114 as M   # o114: o113 + validador (romper/mover sin objeto = rechazo; acoplados cuentan en cuadro)
    elif argv[0] == 'cubo02video':
        import cubo02_video_o114 as M   # o114: poses sin deriva de escala + GUARDIA DEL CUERPO cuadro a cuadro
    elif argv[0] == 'cubo02poses':
        import cubo02_poses_o110 as M
    else:
        import cubo02_molde_o109 as M
    return M.main(argv[1:])


if __name__ == '__main__': print(json.dumps(main(sys.argv[1:]), ensure_ascii=False))
