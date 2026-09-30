#!/usr/bin/env python
# -*- coding: ascii -*-
"""
resumen_cambios.py - hechos para resumir, por archivo, lo que se modifico en un id,
y las sentencias SQL del spec. Solo lee: no escribe nada.

Existe para que el resumen final (con el que el desarrollador llena a mano su
guion de montaje) salga de lo que de verdad se escribio (REGISTRO.jsonl) y del
SQL del ID_SPEC, no de la memoria de una sesion.

USO
  python resumen_cambios.py <carpeta>

SQL: se toma de la seccion '## Scripts SQL' del ID_SPEC si existe; si no, de la
linea 'base de datos:' de '## Ruta de desarrollo'. Cada sentencia empieza en su
propia linea (ALTER, INSERT, UPDATE, CREATE, DELETE, DROP, REPLACE) y termina en
el primer ';' fuera de comillas.

CODIGOS DE SALIDA
  0 ok | 3 no existe el id o su ID_SPEC | 4 error de uso
"""
import os
import re
import sys

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding='utf-8', errors='replace')
    except AttributeError:
        pass

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(AQUI, '..', 'id-workspace'))
import id_workspace as idw  # noqa: E402

INICIO_SQL = re.compile(r'(?im)^[ \t]*(ALTER\s+TABLE|INSERT\s+INTO|UPDATE\s+\S+\s+SET|CREATE\s+(?:TABLE|INDEX|UNIQUE|TRIGGER|VIEW)'
                        r'|DELETE\s+FROM|DROP\s+(?:TABLE|INDEX|TRIGGER|VIEW)|REPLACE\s+INTO)\b')


def archivos_escritos(base, ctx):
    """[(grupo, rel, datos)] en el orden de 'Archivos objetivo' del spec, luego los demas."""
    grupos = {}
    for f in ctx['registro']:
        if not idw.es_escritura(f):
            continue
        ruta = idw.absoluta(f.get('archivo_ref') or f.get('archivo', ''), base)
        repo = idw.repo_de(ruta)
        if repo:
            grupo, rel = repo[0], os.path.relpath(ruta, repo[1]).replace('\\', '/')
        else:
            grupo = 'copias'
            rel = os.path.relpath(ruta, base).replace('\\', '/') if idw.clave(ruta).startswith(idw.clave(base)) else ruta
        d = grupos.setdefault((grupo, rel), {'ruta': ruta, 'items': set(), 'cambios': [], 'nuevo': None,
                                             'mas': 0, 'menos': 0})
        if d['nuevo'] is None:
            d['nuevo'] = not f.get('bytes_antes') and not f.get('md5_antes')
        d['items'].update(str(i) for i in f.get('items', []))
        d['mas'] += f.get('lineas_anadidas', 0) or 0
        d['menos'] += f.get('lineas_retiradas', 0) or 0
        for b in f.get('bloques_detalle') or []:
            j = ' '.join((b.get('justificacion') or '').split())
            if j and j not in d['cambios']:
                d['cambios'].append(j)
    orden = [idw.clave(idw.absoluta(a['ruta'], base)) for a in ctx['spec']['archivos']]

    def pos(k):
        c = idw.clave(grupos[k]['ruta'])
        return (orden.index(c) if c in orden else len(orden), k)
    return [(k[0], k[1], grupos[k]) for k in sorted(grupos, key=pos)]


def objetivos(ruta_spec, numeros):
    salida = []
    crudos = idw.items_crudos(ruta_spec)
    for n in sorted(numeros, key=lambda x: (len(x), x)):
        linea = next((l.strip() for l in crudos.get(n, []) if l.strip().lower().startswith('objetivo:')), '')
        if linea:
            salida.append((n, linea[len('objetivo:'):].strip()))
    return salida


def sentencias_sql(ruta_spec):
    """Sentencias del spec, cada una en una sola linea."""
    secs = idw.secciones(ruta_spec)
    bloque = next((v for k, v in secs.items() if k.startswith('scripts sql')), None)
    if bloque is None:
        ruta = next((v for k, v in secs.items() if k.startswith('ruta de desarrollo')), [])
        bloque, dentro = [], False
        for linea in ruta:
            if re.match(r'^base de datos\s*:', linea.strip(), re.I) and not linea.startswith((' ', '\t')):
                dentro = True
                continue
            if dentro and re.match(r'^[a-z][\w ]*:', linea):
                break
            if dentro:
                bloque.append(linea)
    texto = '\n'.join(bloque)
    salida = []
    for m in INICIO_SQL.finditer(texto):
        i, comilla = m.start(1), None
        j = i
        while j < len(texto):
            c = texto[j]
            if comilla:
                if c == comilla:
                    if j + 1 < len(texto) and texto[j + 1] == comilla:
                        j += 1
                    else:
                        comilla = None
            elif c in ('\'', '"'):
                comilla = c
            elif c == ';':
                break
            j += 1
        if j < len(texto):
            sentencia = ' '.join(texto[i:j + 1].split())
            if not salida or sentencia != salida[-1]:
                salida.append(sentencia)
    return salida


def main():
    args = sys.argv[1:]
    if not args or args[0].startswith('--'):
        print(__doc__)
        return 4
    base = idw.resolver(args[0].strip().strip('"'))
    ctx = idw.contexto(base)
    spec = ctx['spec']
    if spec is None:
        print('FALTA: %s' % os.path.join(ctx['trabajo'], 'ID_SPEC.md'))
        return 3
    ruta_spec = os.path.join(ctx['trabajo'], 'ID_SPEC.md')
    filas = archivos_escritos(base, ctx)
    sql = sentencias_sql(ruta_spec)
    print('RESUMEN DE CAMBIOS DEL ID %s  (carpeta %s)  "%s"'
          % (spec.get('id') or '?', os.path.basename(base), spec.get('titulo') or '-'))
    if not filas and not sql:
        print('SIN_CAMBIOS: REGISTRO.jsonl no tiene escrituras y el spec no trae SQL.')
        return 0
    for n, (grupo, rel, d) in enumerate(filas, 1):
        print('')
        print('ARCHIVO %d  %s  %s  (%s, +%d/-%d lineas)'
              % (n, grupo, rel, 'Nuevo' if d['nuevo'] else 'Existente', d['mas'], d['menos']))
        for num, obj in objetivos(ruta_spec, d['items']):
            print('  objetivo item %s: %s' % (num, obj if len(obj) <= 400 else obj[:397] + '...'))
        print('  cambios escritos (el ultimo manda si contradice a uno anterior):')
        for j in d['cambios'][-8:]:
            print('    - %s' % (j if len(j) <= 220 else j[:217] + '...'))
    print('')
    print('SQL (%d sentencias, del ID_SPEC, en orden de ejecucion):' % len(sql))
    for n, s in enumerate(sql, 1):
        print('  %d. %s' % (n, s))
    if not sql:
        print('  (ninguna: el spec no trae scripts en "base de datos:" ni en "## Scripts SQL")')
    return 0


if __name__ == '__main__':
    sys.exit(main())
