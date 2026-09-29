#!/usr/bin/env python
# -*- coding: ascii -*-
"""
gen_blocks.py - genera los TRANSFER_BLOCK de una migracion comparando la copia
de trabajo vieja (FUENTE de contenido) contra la copia limpia (DESTINO).

El problema que resuelve: la entrega anterior se rechazo porque el diff era
irrevisable - 13 530 lineas cuando el cambio real eran 392. El 97% era ruido de
espaciado, porque el archivo se pego dentro del IDE y este reformateo al pegar.

La regla que lo evita, y que este script aplica mecanicamente:

    en los tramos donde las dos versiones dicen lo MISMO, se conserva
    SIEMPRE la linea del DESTINO, con su indentacion y sus espacios
    finales exactos.

Asi solo viajan las lineas que cambian de verdad. Comparar ignorando espacios
es lo que separa cambio real de ruido; escribir tomando la linea del destino es
lo que impide reintroducirlo.

USO

  python gen_blocks.py --dest <copia_limpia> --src <copia_vieja> --out bloques.txt

  --context N     lineas de contexto inicial a cada lado (por defecto 3)
  --gap N         dos cambios separados por N lineas iguales o menos se funden
                  en un solo bloque (por defecto 6)

SALIDA

Un archivo con un ---TRANSFER_BLOCK--- por region de cambio, listo para
`apply_blocks.py` (el agente migrator solo le agrega los comentarios). Cada
bloque trae ya su anclaje comprobado: el script expande el contexto hasta que
el search_block aparece EXACTAMENTE UNA VEZ en el destino, y lo declara.

LO QUE NO HACE, y es deliberado: no escribe ni reescribe comentarios. El
marcador del id, que bloque lo lleva y como se redacta es criterio del
desarrollador. El script produce el cambio de codigo; los comentarios se
revisan y se ajustan antes de aplicar.

CODIGOS DE SALIDA
  0  bloques generados, todos con anclaje unico
  1  alguna region no logro anclaje unico ni con el maximo de contexto
  4  error de uso o de lectura
"""

import argparse
import difflib
import os
import re
import sys

# La salida la lee OpenCode por un pipe y la decodifica como UTF-8; en Windows
# Python escribe por defecto en cp1252.
for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding='utf-8', errors='replace')
    except AttributeError:
        pass

MAX_EXPANSION = 60


def leer_lineas(path):
    raw = open(path, 'rb').read()
    txt = raw.decode('latin-1')
    usa_crlf = txt.count('\r\n') > (txt.count('\n') - txt.count('\r\n'))
    lineas = txt.replace('\r\n', '\n').split('\n')
    salto_final = bool(lineas) and lineas[-1] == ''
    if salto_final:
        lineas = lineas[:-1]
    return lineas, usa_crlf, salto_final


def norm(l):
    """Normaliza para COMPARAR: colapsa todo espacio. Nunca para escribir."""
    return re.sub(r'\s+', ' ', l).strip()


def construir_regiones(ops, gap):
    """Agrupa opcodes no-'equal' adyacentes en regiones."""
    regiones = []
    actual = None
    for tag, i1, i2, j1, j2 in ops:
        if tag == 'equal':
            if actual and (i2 - i1) > gap:
                regiones.append(actual)
                actual = None
            continue
        if actual is None:
            actual = {'i1': i1, 'i2': i2, 'j1': j1, 'j2': j2, 'ops': []}
        actual['i2'] = i2
        actual['j2'] = j2
        actual['ops'].append((tag, i1, i2, j1, j2))
    if actual:
        regiones.append(actual)
    return regiones


def construir_replace(dest, src, ops, i1, i2):
    """Texto de reemplazo: la linea del DESTINO en los tramos iguales."""
    out = []
    for tag, a1, a2, b1, b2 in ops:
        if tag == 'equal':
            out.extend(dest[a1:a2])          # <- la clave: destino, no fuente
        elif tag in ('replace', 'insert'):
            out.extend(src[b1:b2])
        # 'delete': no se emite nada
    return out


def main():
    ap = argparse.ArgumentParser(add_help=True)
    ap.add_argument('--dest', required=True, help='copia limpia: el archivo que se va a modificar')
    ap.add_argument('--src', required=True, help='copia de trabajo vieja: de donde sale el contenido')
    ap.add_argument('--out', required=True, help='archivo de bloques a escribir')
    ap.add_argument('--context', type=int, default=3)
    ap.add_argument('--gap', type=int, default=6)
    args = ap.parse_args()

    for p in (args.dest, args.src):
        if not os.path.isfile(p):
            sys.stderr.write('ERROR: no existe %s\n' % p)
            return 4

    dest, dest_crlf, _ = leer_lineas(args.dest)
    src, _, _ = leer_lineas(args.src)
    print('DESTINO: %s  (%d lineas, %s)' % (args.dest, len(dest), 'CRLF' if dest_crlf else 'LF'))
    print('FUENTE : %s  (%d lineas)' % (args.src, len(src)))

    sm = difflib.SequenceMatcher(None, [norm(l) for l in dest], [norm(l) for l in src], autojunk=False)
    ops = sm.get_opcodes()
    reales = sum((a2 - a1) + (b2 - b1) for t, a1, a2, b1, b2 in ops if t != 'equal')
    regiones = construir_regiones(ops, args.gap)
    print('Cambios reales (ignorando espaciado): %d lineas en %d region(es)' % (reales, len(regiones)))
    print('')

    texto_dest = '\n'.join(dest)
    bloques = []
    fallos = 0

    for n, reg in enumerate(regiones, 1):
        ctx = args.context
        while True:
            a = max(0, reg['i1'] - ctx)
            b = min(len(dest), reg['i2'] + ctx)
            search = dest[a:b]
            # contexto al frente y al final: identico en ambos lados
            ops_reg = [(t, x1, x2, y1, y2) for (t, x1, x2, y1, y2) in ops
                       if not (x2 <= a or x1 >= b)]
            replace = []
            for t, x1, x2, y1, y2 in ops_reg:
                if t == 'equal':
                    # Tramo identico: SIEMPRE la linea del destino, recortada a
                    # la ventana. Aqui es donde se evita el ruido de espaciado.
                    replace.extend(dest[max(x1, a):min(x2, b)])
                elif t in ('replace', 'insert'):
                    # Las regiones se delimitan por tramos 'equal', asi que un
                    # opcode de cambio nunca queda cortado por la ventana.
                    replace.extend(src[y1:y2])
                # 'delete': no se emite nada
            s_txt = '\n'.join(search)
            veces = texto_dest.count(s_txt)
            if veces == 1 or ctx >= MAX_EXPANSION:
                break
            ctx += 3

        if veces != 1:
            print('  %2d  *** SIN ANCLAJE UNICO *** (%d ocurrencias con %d de contexto)' % (n, veces, ctx))
            fallos += 1
            continue

        r_txt = '\n'.join(replace)
        if s_txt == r_txt:
            print('  %2d  sin cambio efectivo, se omite' % n)
            continue
        print('  %2d  lineas dest %d-%d  ->  %d lineas  (contexto %d, ancla unica)'
              % (n, a + 1, b, len(replace), ctx))
        bloques.append((args.dest, s_txt, r_txt, a + 1, b))

    # El archivo de bloques se escribe en UTF-8, que es lo que espera
    # apply_blocks.py (lo transcodifica a latin-1 al aplicar). Escribirlo en
    # latin-1 hacia que los acentos llegaran como basura.
    with open(args.out, 'wb') as fh:
        cab = ('# Bloques generados por gen_blocks.py\n'
               '# DESTINO: %s\n# FUENTE : %s\n'
               '# %d bloque(s). Cada search_block anclado a UNA sola ocurrencia.\n'
               '# PENDIENTE DE CRITERIO HUMANO: revisar y redactar los comentarios\n'
               '# del id antes de aplicar. El script no los escribe.\n\n'
               % (args.dest, args.src, len(bloques)))
        fh.write(cab.encode('utf-8'))
        for i, (path, s, r, l1, l2) in enumerate(bloques, 1):
            b = ('---TRANSFER_BLOCK---\nfile_path: %s\n\nsearch_block:\n%s\n'
                 'replace_block:\n%s\njustification: region %d, lineas %d-%d del destino\n'
                 '---END_TRANSFER_BLOCK---\n\n' % (path, s, r, i, l1, l2))
            fh.write(b.encode('utf-8'))

    print('')
    print('Escrito: %s  (%d bloques)' % (args.out, len(bloques)))
    print('SIGUIENTE PASO: revisar los comentarios, luego')
    print('  python apply_blocks.py "%s"        <- simula' % args.out)
    print('  python apply_blocks.py "%s" --apply' % args.out)
    return 1 if fallos else 0


if __name__ == '__main__':
    sys.exit(main())
