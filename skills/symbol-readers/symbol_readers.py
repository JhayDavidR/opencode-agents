#!/usr/bin/env python
# -*- coding: ascii -*-
"""
symbol_readers.py - localiza TODOS los usos de uno o varios simbolos en
archivos legacy PHP / JS codificados en ISO-8859-1.

Su razon de ser: en este codigo base la presentacion se usa como dato. Un
texto visible, un campo oculto o el value de un select alimentan validaciones
en otro archivo. Cambiar uno sin saber quien lo lee es la causa numero uno de
regresiones. Este script contesta "quien lo lee" de forma mecanica, para que
el agente solo tenga que juzgar el riesgo, no buscar.

No interpreta, no opina, no modifica nada. Lee y clasifica.

USO

  Sobre archivos concretos:
    python symbol_readers.py --symbol nom_descarID --file a.js --file b.php

  Sobre una carpeta (--root se puede repetir):
    python symbol_readers.py --symbol GetTrayler --root ruta/modulo --ext .php --ext .js

  Sobre TODO sate_standa (miles de archivos): --prefilter recorre todo pero
  solo escanea los archivos cuyos bytes contienen algun simbolo, y el limite
  de --max-files se aplica a esos candidatos, no al arbol completo:
    python symbol_readers.py --symbol tab_manrem_consol --root <sate_standa> --prefilter

  Varios simbolos a la vez:
    python symbol_readers.py --symbol Insert --symbol Update --file class.php

  Salida JSON estricta (para consumo por agente):
    ... --json

SALIDA

Por cada simbolo: el total, el desglose por patron (para poder afirmar un
conteo sin depender de un solo grep) y cada ocurrencia con archivo, linea,
clasificacion y el texto exacto de la linea.

CODIGOS DE SALIDA
  0  se encontro al menos una ocurrencia de cada simbolo
  3  algun simbolo tuvo CERO ocurrencias (no es error: es un hallazgo)
  4  error de uso o de lectura
"""

import argparse
import json
import os
import re
import sys

# La salida la lee OpenCode por un pipe y la decodifica como UTF-8. En Windows
# Python escribe por defecto en cp1252: cada acento llegaba como U+FFFD y un
# byte 0x80-0x9F tumbaba el script.
for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding='utf-8', errors='replace')
    except AttributeError:
        pass

MAX_FILES_DEFAULT = 400
MAX_LINE_ECHO = 240


def leer_lineas(path):
    """Lee siempre como latin-1: nunca falla y no reinterpreta los bytes."""
    with open(path, 'rb') as fh:
        raw = fh.read()
    return raw.decode('latin-1').replace('\r\n', '\n').split('\n')


def construir_patrones(sym):
    """Patrones de clasificacion, del mas especifico al mas generico.

    El orden importa: una linea se clasifica con el primero que coincida.
    """
    s = re.escape(sym)
    return [
        ('definicion_php',   re.compile(r'\bfunction\s+&?\s*' + s + r'\s*\(')),
        ('definicion_js',    re.compile(r'(?:\bfunction\s+' + s + r'\s*\()|(?:\b' + s + r'\s*[:=]\s*function\s*\()')),
        ('llamada_metodo',   re.compile(r'(?:->|::)\s*' + s + r'\s*\(')),
        ('llamada',          re.compile(r'(?<![\w$>:.])' + s + r'\s*\(')),
        ('acceso_post_get',  re.compile(r'\$_(?:POST|GET|REQUEST|AJAX)\s*\[\s*[\'"]' + s + r'[\'"]\s*\]')),
        # Escritura de DOM antes que lectura: es la que puede pisar un valor
        # que otra funcion da por sentado. Exige el simbolo y un setter en la
        # misma linea, con argumento no vacio.
        ('escritura_dom',    re.compile(
            r'(?:#' + s + r'\b|getElementById\s*\(\s*[\'"]' + s + r'[\'"]|getElementsByName\s*\(\s*[\'"]' + s + r'[\'"])'
            r'[^;]*?(?:\.(?:val|html|text|prop|attr)\s*\(\s*[^\s)]|\.(?:value|checked|innerHTML|innerText|disabled|selectedIndex)\s*=(?!=))')),
        ('selector_dom',     re.compile(r'(?:#' + s + r'\b)|(?:getElementById\s*\(\s*[\'"]' + s + r'[\'"])|(?:getElementsByName\s*\(\s*[\'"]' + s + r'[\'"])')),
        ('escritura',        re.compile(r'(?<![\w$])\$?' + s + r'\s*=(?![=>])')),
        ('propiedad',        re.compile(r'(?:->|\.)\s*' + s + r'\b')),
        ('literal_cadena',   re.compile(r'[\'"]' + s + r'[\'"]')),
        ('variable_php',     re.compile(r'\$' + s + r'\b')),
        ('mencion',          re.compile(r'(?<![\w$])' + s + r'(?![\w$])')),
    ]


RE_COMENTARIO = re.compile(r'^\s*(?://|\*|/\*|#)')


def clasificar(linea, patrones):
    for nombre, rx in patrones:
        if rx.search(linea):
            return nombre
    return None


def escanear_archivo(path, simbolos):
    """Devuelve {simbolo: [ocurrencias]} para un archivo."""
    lineas = leer_lineas(path)
    patrones = dict((s, construir_patrones(s)) for s in simbolos)
    # Filtro barato: si el simbolo no aparece ni como substring, no se recorre.
    texto = '\n'.join(lineas)
    salida = {}
    for sym in simbolos:
        salida[sym] = []
        if sym not in texto:
            continue
        pats = patrones[sym]
        for i, linea in enumerate(lineas, 1):
            if sym not in linea:
                continue
            kind = clasificar(linea, pats)
            if kind is None:
                continue
            salida[sym].append({
                'file': path,
                'line': i,
                'kind': kind,
                'in_comment': bool(RE_COMENTARIO.match(linea)),
                'text': linea.strip()[:MAX_LINE_ECHO],
            })
    return salida


def recolectar_archivos(args):
    archivos = list(args.file or [])
    if args.root:
        exts = [e.lower() if e.startswith('.') else '.' + e.lower()
                for e in (args.ext or ['.php', '.js'])]
        for raiz in args.root:
            for base, dirs, nombres in os.walk(raiz):
                dirs[:] = [d for d in dirs if d not in ('.git', '.svn', 'node_modules', '.idea')]
                for n in nombres:
                    if os.path.splitext(n)[1].lower() in exts:
                        archivos.append(os.path.join(base, n))
    vistos = set()
    unicos = []
    for a in archivos:
        ap = os.path.normpath(a)
        if ap not in vistos and os.path.isfile(ap):
            vistos.add(ap)
            unicos.append(ap)
    return unicos


def prefiltrar(archivos, simbolos):
    """Solo los archivos cuyos bytes contienen algun simbolo. Los --file se
    conservan siempre: el usuario los pidio por nombre."""
    agujas = [s.encode('latin-1', 'replace') for s in simbolos]
    salida = []
    for a in archivos:
        try:
            with open(a, 'rb') as fh:
                raw = fh.read()
        except (IOError, OSError):
            continue
        if any(ag in raw for ag in agujas):
            salida.append(a)
    return salida


def main():
    ap = argparse.ArgumentParser(add_help=True)
    ap.add_argument('--symbol', action='append', required=True,
                    help='simbolo a rastrear (repetible)')
    ap.add_argument('--file', action='append', help='archivo a escanear (repetible)')
    ap.add_argument('--root', action='append', help='carpeta a recorrer recursivamente (repetible)')
    ap.add_argument('--ext', action='append', help='extension a incluir con --root (por defecto .php y .js)')
    ap.add_argument('--prefilter', action='store_true',
                    help='escanear solo los archivos que contienen algun simbolo (para recorrer sate_standa entero)')
    ap.add_argument('--max-files', type=int, default=MAX_FILES_DEFAULT)
    ap.add_argument('--json', action='store_true', help='salida JSON estricta')
    args = ap.parse_args()

    if not args.file and not args.root:
        sys.stderr.write('ERROR: indica al menos --file o --root\n')
        return 4

    archivos = recolectar_archivos(args)
    recorridos = len(archivos)
    if args.prefilter:
        pedidos = set(os.path.normpath(f) for f in (args.file or []))
        candidatos = set(prefiltrar([a for a in archivos if a not in pedidos], args.symbol))
        archivos = [a for a in archivos if a in pedidos or a in candidatos]
    if not archivos:
        sys.stderr.write('ERROR: ningun archivo legible en el alcance indicado\n')
        return 4
    if len(archivos) > args.max_files:
        sys.stderr.write('ERROR: %d archivos supera el limite de %d. Acota el alcance%s.\n'
                         % (len(archivos), args.max_files,
                            '' if args.prefilter else ' o usa --prefilter'))
        if args.prefilter:
            # Dice QUE simbolo infla el alcance: casi siempre una palabra generica
            # (response, Chart, data) o una funcion de libreria, que no es un lector
            # del cambio. Sin esto el agente no sabe que quitar.
            por_simbolo = []
            for s in args.symbol:
                aguja = s.encode('latin-1', 'replace')
                n = 0
                for a in archivos:
                    try:
                        with open(a, 'rb') as fh:
                            if aguja in fh.read():
                                n += 1
                    except (IOError, OSError):
                        pass
                por_simbolo.append((n, s))
            por_simbolo.sort(reverse=True)
            sys.stderr.write('ARCHIVOS POR SIMBOLO (los primeros inflan el alcance):\n')
            for n, s in por_simbolo:
                sys.stderr.write('  %6d  %s\n' % (n, s))
            sys.stderr.write('Quita los simbolos genericos o de libreria, o buscalos solo con --file '
                             'sobre los archivos del id.\n')
        return 4

    simbolos = args.symbol
    acumulado = dict((s, []) for s in simbolos)
    for path in archivos:
        try:
            parcial = escanear_archivo(path, simbolos)
        except Exception as exc:
            sys.stderr.write('AVISO: no se pudo leer %s (%s)\n' % (path, exc))
            continue
        for s in simbolos:
            acumulado[s].extend(parcial[s])

    resultado = {'scope_files': len(archivos), 'walked_files': recorridos,
                 'prefilter': bool(args.prefilter), 'symbols': []}
    huerfano = False
    for s in simbolos:
        occ = acumulado[s]
        if not occ:
            huerfano = True
        por_tipo = {}
        for o in occ:
            por_tipo[o['kind']] = por_tipo.get(o['kind'], 0) + 1
        resultado['symbols'].append({
            'symbol': s,
            'total_occurrences': len(occ),
            'counts_by_kind': por_tipo,
            'files_touched': sorted(set(o['file'] for o in occ)),
            'occurrences': occ,
        })

    if args.json:
        sys.stdout.write(json.dumps(resultado, indent=2, ensure_ascii=True))
        sys.stdout.write('\n')
    else:
        if args.prefilter:
            print('ALCANCE: %d archivo(s) con algun simbolo, de %d recorridos (--prefilter)'
                  % (resultado['scope_files'], recorridos))
        else:
            print('ALCANCE: %d archivo(s)' % resultado['scope_files'])
        for entrada in resultado['symbols']:
            print('')
            print('=' * 72)
            print('SIMBOLO: %s' % entrada['symbol'])
            print('TOTAL: %d ocurrencia(s) en %d archivo(s)'
                  % (entrada['total_occurrences'], len(entrada['files_touched'])))
            if entrada['total_occurrences'] == 0:
                print('SIN OCURRENCIAS en el alcance indicado.')
                continue
            print('DESGLOSE POR TIPO: %s' % ', '.join(
                '%s=%d' % (k, v) for k, v in sorted(entrada['counts_by_kind'].items())))
            print('-' * 72)
            actual = None
            for o in entrada['occurrences']:
                if o['file'] != actual:
                    actual = o['file']
                    print('  %s' % actual)
                marca = ' [COMENTARIO]' if o['in_comment'] else ''
                print('    %6d  %-16s%s  %s' % (o['line'], o['kind'], marca, o['text']))

    return 3 if huerfano else 0


if __name__ == '__main__':
    sys.exit(main())
