---
name: read-file
description: >
  Reads a legacy file preserving ISO-8859-1 encoding, with numbered lines.
  Supports locating a pattern (--find) and reading only a line range, so
  huge legacy files are never dumped whole. Use instead of the native read
  tool on legacy PHP/JS files to avoid encoding corruption.
---

# read-file

Lee un archivo legacy respetando ISO-8859-1 (latin1) y lo muestra con
números de línea. Nunca re-codifica el archivo.

## Método obligatorio: localizar, luego leer una ventana

Los archivos legacy de este proyecto suelen tener miles de líneas y cientos
de KB. Volcar uno entero puede costar seis cifras en tokens y el script lo
rechaza por encima de su umbral. El flujo correcto son dos pasos baratos:

1. **Localizar** — devuelve solo los números de línea, sin contenido:

   ```bash
   python "<skill_dir>/read_file.py" "<file_path>" --find "function NombreFuncion"
   ```

2. **Leer la ventana** — típicamente 40 líneas de margen a cada lado:

   ```bash
   python "<skill_dir>/read_file.py" "<file_path>" <start_line> <end_line>
   ```

Sin argumentos de rango, el script vuelca el archivo solo si tiene 800
líneas o menos; por encima de eso responde `REFUSED` y recuerda este
método.

## Formato de salida

Cada línea sale como `NNNNNN | contenido`. Al copiar un `search_block`
para `apply_blocks.py`, **quita el número y el separador `" | "`** — solo
el contenido cuenta para el match byte a byte.

La salida siempre es UTF-8 (el archivo se lee como ISO-8859-1): los acentos
llegan tal cual y `apply_blocks.py` los vuelve a escribir en ISO-8859-1.
