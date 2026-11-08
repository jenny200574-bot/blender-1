# Fuentes oficiales versionadas (procesos / OS)

Usadas por el parche; no APIs de pago ni inferencia.

| Interfaz | Versión | Uso |
|---|---|---|
| Python `subprocess.Popen.returncode` | [3.12](https://docs.python.org/3.12/library/subprocess.html#subprocess.Popen.returncode) | `None` = aún no terminó; `-N` = terminado por señal N (POSIX). |
| Python `Popen.wait` | 3.12 | Espera al hijo y rellena returncode. |
| Python `os.replace` | [3.12](https://docs.python.org/3.12/library/os.html#os.replace) | Reemplazo atómico del JSON de estado y del supervisor en el aplicador. |
| Python `os.fsync` / `os.fchmod` | 3.12 | Durabilidad y conservación del modo del destino. |
| Python `fcntl.flock` | 3.12 | Candado advisory (corridas y aplicador). No es CAS: quien ignora el lock puede competir. |
| Linux `boot_id` | Kernel sysctl `random/boot_id` ([admin-guide/sysctl/kernel](https://www.kernel.org/doc/html/latest/admin-guide/sysctl/kernel.html)) | UUID de arranque: «generated the first time this is retrieved, and unvarying after that». Ruta: `/proc/sys/kernel/random/boot_id`. |
| Linux `/proc/<pid>/stat` campo 22 starttime | [proc(5)](https://man7.org/linux/man-pages/man5/proc.5.html) | Evitar falso positivo por reuso de PID. |
| systemd `sd_id128_get_boot` | [docs](https://www.freedesktop.org/software/systemd/man/latest/sd_id128_get_boot.html) | Confirma que userspace lee el mismo `boot_id` del kernel. |

Entorno de prueba: Python 3.12.3, Linux 6.12.113. No se promete ABI estable de `boot_id` más allá de la documentación kernel citada.
