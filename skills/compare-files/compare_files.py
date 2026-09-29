# -*- coding: latin-1 -*-
import sys
import os
import difflib

# La salida la lee OpenCode por un pipe y la decodifica como UTF-8. En Windows
# Python escribe por defecto en cp1252: cada acento del diff llegaba como U+FFFD
# y un byte 0x80-0x9F tumbaba el script.
for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding='utf-8', errors='replace')
    except AttributeError:
        pass

if len(sys.argv) != 3:
    print("Error: Se requieren 2 argumentos: <file_dev> <file_prod>")
    sys.exit(1)

file_dev = sys.argv[1]
file_prod = sys.argv[2]

try:
    with open(file_dev, 'r', encoding='latin-1') as f1, open(file_prod, 'r', encoding='latin-1') as f2:
        dev_lines = f1.readlines()
        prod_lines = f2.readlines()

    # Generar diff unificado (n=3 para mostrar 3 l�neas de contexto alrededor del cambio)
    diff = list(difflib.unified_diff(
        prod_lines, dev_lines, 
        fromfile='PRODUCCION', tofile='DESARROLLO', n=3
    ))

    if not diff:
        print("No hay diferencias entre los archivos.")
    else:
        print("".join(diff))

except Exception as e:
    print(f"Error comparando archivos: {e}")
    sys.exit(1)