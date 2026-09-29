# -*- coding: utf-8 -*-
"""
read_file.py

Lee un archivo legacy respetando ISO-8859-1 (latin1) y lo imprime con
numeros de linea. Nunca re-codifica el archivo: solo lo lee.

CAMBIO v2 (auditoria 2026-09-09):
  - Acepta un rango OPCIONAL de lineas. Leer manifi2.js completo cuesta
    ~100k tokens por invocacion; leer una ventana de 60 lineas cuesta ~1k.
  - Modo --find: localiza un patron y devuelve solo los numeros de linea
    donde aparece, para decidir que ventana leer sin volcar el archivo.
  - Sin rango, si el archivo supera MAX_AUTO_LINES, se niega a volcarlo
    entero y explica como pedir un rango.

Uso:
  python read_file.py <file_path>
  python read_file.py <file_path> <start_line> <end_line>
  python read_file.py <file_path> --find "<texto>"
"""
import os
import sys

# La salida la lee OpenCode por un pipe y la decodifica como UTF-8. En Windows
# Python escribe por defecto en cp1252: cada acento llegaba como U+FFFD (y el
# search_block copiado de ahi ya no anclaba) y un byte 0x80-0x9F tumbaba el
# script con 'charmap' codec can't encode.
for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding='utf-8', errors='replace')
    except AttributeError:
        pass

MAX_AUTO_LINES = 800


def load_lines(file_path):
    with open(file_path, 'r', encoding='latin-1', newline='') as f:
        return f.read().split('\n')


def main():
    argv = sys.argv[1:]
    if not argv:
        print("ERROR: Missing argument. Usage:")
        print("  python read_file.py <file_path>")
        print("  python read_file.py <file_path> <start_line> <end_line>")
        print("  python read_file.py <file_path> --find \"<texto>\"")
        sys.exit(1)

    file_path = argv[0]
    if not os.path.isfile(file_path):
        print("ERROR: File does not exist or is not a file: %s" % file_path)
        sys.exit(1)

    size = os.path.getsize(file_path)
    lines = load_lines(file_path)
    total = len(lines)

    print("=== FILE_START: %s ===" % file_path)
    print("=== SIZE_BYTES: %d | TOTAL_LINES: %d ===" % (size, total))

    # Modo busqueda: solo numeros de linea, sin volcar contenido.
    if len(argv) >= 3 and argv[1] == '--find':
        needle = argv[2]
        hits = [i + 1 for i, l in enumerate(lines) if needle in l]
        print("=== FIND: %r -> %d ocurrencia(s) ===" % (needle, len(hits)))
        for n in hits[:200]:
            preview = lines[n - 1].strip()[:120]
            print("%6d | %s" % (n, preview))
        if len(hits) > 200:
            print("... (%d ocurrencias mas, refina el patron)" % (len(hits) - 200))
        print("=== FILE_END ===\n")
        return

    # Modo rango.
    if len(argv) >= 3:
        try:
            start, end = int(argv[1]), int(argv[2])
        except ValueError:
            print("ERROR: start_line y end_line deben ser enteros.")
            sys.exit(1)
        start = max(1, start)
        end = min(total, end)
        if start > end:
            print("ERROR: start_line (%d) > end_line (%d)." % (start, end))
            sys.exit(1)
    else:
        if total > MAX_AUTO_LINES:
            print("=== REFUSED: El archivo tiene %d lineas (limite automatico "
                  "%d). ===" % (total, MAX_AUTO_LINES))
            print("Volcarlo entero desperdicia el contexto. Localiza primero:")
            print("  python read_file.py \"%s\" --find \"nombre_de_la_funcion\""
                  % file_path)
            print("y luego lee la ventana:")
            print("  python read_file.py \"%s\" <start_line> <end_line>"
                  % file_path)
            print("=== FILE_END ===\n")
            sys.exit(1)
        start, end = 1, total

    print("=== RANGE: %d-%d de %d ===" % (start, end, total))
    for n in range(start, end + 1):
        print("%6d | %s" % (n, lines[n - 1].rstrip('\r')))
    print("=== FILE_END: mostradas %d de %d lineas ===\n" % (end - start + 1, total))


if __name__ == '__main__':
    try:
        main()
    except PermissionError:
        print("ERROR: Permission denied reading file.")
        sys.exit(1)
    except Exception as e:
        print("ERROR: Unexpected exception reading file: %s" % e)
        sys.exit(1)
