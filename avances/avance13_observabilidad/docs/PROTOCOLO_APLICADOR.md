# Protocolo seguro del aplicador (t164/165)

Python 3.12.3 (VPS) y 3.13 (box): `os.replace`, `os.fsync`, `fcntl.flock`, `os.fchmod`. Sin infraestructura nueva.

## Qué hace y qué no
- Reemplazo: archivo temporal en el mismo directorio + `os.replace` (POSIX atómico para el nombre).
- Candado **advisory** `fcntl.flock` (`LOCK_EX|LOCK_NB`) en `supervisor_oro_constructor.apply.lock`.
- Relee el hash **bajo lock** tras el respaldo y otra vez antes del replace. Si no es el original `129187406f4381fb7740e561e7835336211590e5aaf5ef2b92b1559ea5e87c85`, falla `CAMBIO_AJENO_*` y **no fuerza**.
- Conserva el modo del destino (`fchmod`); rechaza symlink.
- Falla explícita (`ok:false`); no declara éxito si el hash final no es el parche.
- **Límite:** no es CAS perfecto. Un escritor que ignora el lock (otro `cp`, editor, `copy2`) puede competir. Durante la implantación no debe haber otros deploys ni editores sobre ese archivo.

## `.off` no es candado de construcción
`observabilidad_cierre.off` **desactiva la observabilidad nueva y la recuperación**, no el lanzamiento de oro/constructor. Con `.off` el `main` de producción **sigue pudiendo construir**. **Prohibido** invocar `python3 supervisor_oro_constructor.py` sin `MYIA_SUPERVISOR_SIMULACION` o `MYIA_SUPERVISOR_SOLO_RECUPERAR` como «prueba». Eso no es prueba de instalador.

## Pasos (Ricardo; este agente no despliega)
1. Ningún otro deploy sobre `operaciones/`.
2. `python3 aplicar_observabilidad.py --destino …/supervisor_oro_constructor.py --solo-verificar` (debe ser original).
3. `python3 aplicar_observabilidad.py --destino …/supervisor_oro_constructor.py` (deja `.off`; no quitarlo aquí).
4. Revertir: `python3 aplicar_observabilidad.py --destino … --revertir --respaldo <bak.orig>`.

No autorrelanza. No toca cámara/física. No reconstruye `copia_fuentes_hashes.json`.
