---
description: "[migrator] Corrige SOLO los comentarios del id en un archivo ya migrado o implementado (MODE COMMENTS). Uso: /comentarios <carpeta_id> <archivo> [lineas o que corregir]"
agent: migrator
---
MODE: COMMENTS
Argumentos: $ARGUMENTS
(el primero es la carpeta del id; el segundo, el archivo; el resto, las ventanas de lineas o que comentarios corregir. Sin ventanas, localiza los marcadores del id con read_file.py --find.)
