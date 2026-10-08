#!/usr/bin/env python
# -*- coding: ascii -*-
"""
apply_blocks.py - aplica en bloque un lote de TRANSFER_BLOCK ya verificados,
sin pasar por ningun agente.

Para que existe: aplicar un bloque que YA fue verificado no requiere juicio.
Requiere exactitud. El pipeline de agentes gastaba dos subagentes en frio por
bloque (validar, escribir, diferenciar, revisar comentarios) para hacer algo
determinista. Este script hace lo mismo en segundos y sin varianza.

GARANTIA CENTRAL: todo o nada. Si UN solo bloque no ancla exactamente una vez,
no se escribe NADA. Nunca deja el archivo a medio aplicar.

USO

  Simulacion (por defecto, no escribe nada):
    python apply_blocks.py PROMPT_tanda3.txt

  Aplicar de verdad:
    python apply_blocks.py PROMPT_tanda3.txt --apply

  Redirigir el destino declarado en los bloques:
    python apply_blocks.py bloques.txt --apply --override class_manifi.php=D:\ruta\real.php

  Ver el diff completo en vez del resumen:
    python apply_blocks.py PROMPT_tanda3.txt --diff

  Dejar trazabilidad (una linea JSON por archivo escrito: bytes, md5, backup,
  items, copia del lote en _agentes/lotes/ y, con --lint, el resultado del lint):
    python apply_blocks.py bloques.txt --apply --registro <carpeta_id>/_agentes/REGISTRO.jsonl --lint

  --lint: tras escribir, php -l (.php/.inc) o node --check (.js) sobre el archivo
  y sobre su backup. error_nuevo = el backup no tenia ese error (es del cambio);
  error_previo = el backup ya lo tenia; no_ejecutado = falta el binario.

LOTE DE UN ID (el lote o el --registro estan en <carpeta_id>/_agentes/)

  - file_path acepta el nombre logico del ID_SPEC ({repo:sate_standa}\\..., {id}\\...)
    o la ruta de este equipo: se resuelve con lo registrado en id_workspace.py.
  - Solo se escriben archivos listados en 'Archivos objetivo' del ID_SPEC
    (FUERA_DE_ALCANCE). Un archivo de un repo registrado solo se escribe desde el
    lote de un id: un repo no se toca fuera del flujo.
  - Nunca en la rama master/main de un repo (RAMA_BASE): la rama del id la crea
    el desarrollador. Este script lee .git como archivos; NUNCA ejecuta git.
  - Archivo NUEVO: si el ID_SPEC lo marca "nuevo: si" en Archivos objetivo y no existe,
    se crea con UN bloque de search_block vacio (todo el contenido en replace_block),
    en ISO-8859-1 y CRLF; su carpeta debe existir. Con search vacio sobre un archivo
    que ya existe el bloque no ancla (MULTIPLE) y no se escribe nada.
  - El backup va a <carpeta_id>/_agentes/respaldos/, fuera del repo: dentro del
    repo ensuciaria git status y se podria colar en un commit.
  - El REGISTRO guarda ademas la ruta logica, la rama, la huella de cada item
    del lote (el router pide de nuevo solo los items que cambien en el spec) y
    avisa si el archivo cambio fuera del flujo desde la ultima escritura.

SALIDA

Por bloque: cuantas veces ancla y su estado. Al final, las metricas de
espaciado que son el criterio de aceptacion de este proyecto: lineas, finales
de linea, lineas que empiezan con tab, lineas con espacios finales, salto
final. Cualquier deriva ahi es ruido que hace ilegible el diff en revision.

CODIGOS DE SALIDA
  0  simulacion limpia, o escritura aplicada y verificada
  1  algun bloque no ancla de forma unica: no se escribio nada
  2  caracteres fuera de latin-1 en un replace: no se escribio nada
  3  un comentario nuevo cita el andamiaje del flujo (R<n>, item, spec, agente), o una linea
     nueva usa alert()/confirm() nativo en vez de SweetAlert: no se escribio nada
  4  error de uso o de lectura
  5  con --apply, algun destino cae en .opencode/protected_paths.txt: no se escribio nada
  6  FUERA_DE_ALCANCE (el archivo no esta en el ID_SPEC, o es de un repo y el lote no es
     de un id), RAMA_BASE (el repo esta en master/main) o RUTA sin resolver: no se escribio nada
  7  con --apply --lint: lote aplicado, pero el lint da un error que el backup no tenia
"""

import argparse
import difflib
import os
import re
import shutil
import subprocess
import sys
import tempfile
import datetime
import hashlib
import json

# La salida la lee OpenCode por un pipe y la decodifica como UTF-8. En Windows
# Python escribe por defecto en cp1252: cada acento del diff llegaba como U+FFFD
# y un byte 0x80-0x9F tumbaba el script.
for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding='utf-8', errors='replace')
    except AttributeError:
        pass

# Las rutas logicas, los repos registrados, la rama y las huellas de items los
# resuelve id_workspace.py: una sola implementacion para el router y para aqui.
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'id-workspace'))
import id_workspace as idw  # noqa: E402

RE_BLOCK = re.compile(r'---TRANSFER_BLOCK---(.*?)---END_TRANSFER_BLOCK---', re.S)
# Los delimitadores usan [ \t]* y NUNCA \s*. Un \s* cruza saltos de linea y se
# come las lineas en blanco del final del bloque, que entonces sobreviven a la
# sustitucion y aparecen duplicadas en el resultado. Ese ruido de espaciado es
# exactamente lo que hace ilegible un diff en revision.
RE_PATH = re.compile(r'^[ \t]*file_path:[ \t]*(.+?)[ \t]*$', re.M)
RE_SEARCH = re.compile(r'^[ \t]*search_block:[ \t]*\n(.*?)\n[ \t]*replace_block:[ \t]*\n', re.S | re.M)
RE_REPLACE = re.compile(r'\n[ \t]*replace_block:[ \t]*\n(.*?)(?:\n[ \t]*justification:[ \t]*|\Z)', re.S)
RE_JUST = re.compile(r'\n[ \t]*justification:[ \t]*(.*?)[ \t]*$', re.S)
# "item 5: ...", "items 5,6: ...", "item 5 y 6: ..." -> [5, 6]
RE_ITEMS = re.compile(r'(?i)\bitems?\s+([\d][\d\s,y]*)')


def leer(path):
    with open(path, 'rb') as fh:
        return fh.read()


def metricas(raw):
    """Las metricas de espaciado que son el criterio de aceptacion."""
    txt = raw.decode('latin-1')
    crlf = txt.count('\r\n')
    lf = txt.count('\n') - crlf
    lineas = txt.replace('\r\n', '\n').split('\n')
    if lineas and lineas[-1] == '':
        lineas = lineas[:-1]
        salto_final = True
    else:
        salto_final = False
    return {
        'bytes': len(raw),
        'lineas': len(lineas),
        'crlf': crlf,
        'lf_sueltos': lf,
        'tab_inicial': sum(1 for l in lineas if l.startswith('\t')),
        'espacios_finales': sum(1 for l in lineas if l != l.rstrip()),
        'salto_final': salto_final,
    }


def parsear_bloques(texto):
    bloques = []
    for i, cuerpo in enumerate(RE_BLOCK.findall(texto), 1):
        mp = RE_PATH.search(cuerpo)
        ms = RE_SEARCH.search(cuerpo)
        mr = RE_REPLACE.search(cuerpo)
        if not (mp and ms and mr):
            bloques.append({'n': i, 'error': 'bloque mal formado (falta file_path, search_block o replace_block)'})
            continue
        # Sin strip: los delimitadores ya acotan el contenido exacto, y estos
        # bloques terminan legitimamente en lineas en blanco que forman parte
        # del texto a localizar. Recortarlas descuadra el resultado.
        mj = RE_JUST.search(cuerpo)
        just = ' '.join(mj.group(1).split()) if mj else ''
        mi = RE_ITEMS.search(just)
        bloques.append({
            'n': i,
            'path': mp.group(1).strip().strip('"'),
            'search': ms.group(1),
            'replace': mr.group(1),
            'justificacion': just,
            'items': sorted(set(int(x) for x in re.findall(r'\d+', mi.group(1)))) if mi else [],
        })
    return bloques


def lint(path, bak):
    """(resultado, comando, salida, salida_backup). Nunca lanza: sin binario es no_ejecutado."""
    ext = os.path.splitext(path)[1].lower()
    if ext in ('.php', '.inc'):
        binario, args = shutil.which('php'), ['-l']
    elif ext == '.js':
        binario, args = shutil.which('node'), ['--check']
    else:
        return 'sin_lint', '', 'no hay lint para %s' % ext, ''
    if not binario:
        return 'no_ejecutado', '', '%s no esta en el PATH' % ('php' if ext != '.js' else 'node'), ''

    def correr(ruta):
        try:
            p = subprocess.run([binario] + args + [ruta], capture_output=True, timeout=120)
            texto = (p.stdout + p.stderr).decode('latin-1', 'replace').strip()
            return p.returncode, texto
        except Exception as exc:
            return 99, 'no se pudo ejecutar: %s' % exc

    codigo, salida = correr(path)
    if codigo == 0:
        return 'ok', os.path.basename(binario) + ' ' + ' '.join(args), salida, ''
    # node --check exige extension .js: el backup se lintea desde una copia temporal.
    tmp = None
    ruta_bak = bak
    if ext == '.js':
        fd, tmp = tempfile.mkstemp(suffix='.js')
        os.close(fd)
        shutil.copyfile(bak, tmp)
        ruta_bak = tmp
    codigo_bak, salida_bak = correr(ruta_bak)
    if tmp:
        os.remove(tmp)
    resultado = 'error_previo' if codigo_bak != 0 else 'error_nuevo'
    return resultado, os.path.basename(binario) + ' ' + ' '.join(args), salida, salida_bak


# code-doc-standard: un comentario del codigo describe el negocio, nunca el andamiaje
# del flujo (numeros de requisito, items, spec, agentes). Se valida aqui para que
# ningun autor - agente o persona - lo deje pasar.
RE_COMENTARIO = re.compile(r'(//|/\*|^\s*\*|^\s*#|<!--)')
RE_ANDAMIAJE = re.compile(r'\bR\d{1,3}\b|\bitems?\b|\bID_SPEC\b|\bTRANSFER_BLOCK\b|\bsearch_block\b|\bprompt\b'
                          r'|\b(implementer|analista|migrator|documenter|avansat_expert)\b', re.I)


ALERTA_NATIVA = re.compile(r'(?<![\w.$])(?:window\.)?(?:alert|confirm)\s*\(')


def andamiaje_en_comentarios(texto):
    """Lineas de comentario del replace_block que citan el andamiaje del flujo."""
    malas = []
    for linea in texto.split('\n'):
        m = RE_COMENTARIO.search(linea)
        if m and RE_ANDAMIAJE.search(linea[m.start():]):
            malas.append(linea.strip()[:90])
    return malas


def normaliza_eol(texto, usa_crlf):
    t = texto.replace('\r\n', '\n')
    return t.replace('\n', '\r\n') if usa_crlf else t


def rutas_protegidas():
    """Lee .opencode/protected_paths.txt. None si no existe."""
    cfg = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'protected_paths.txt')
    if not os.path.isfile(cfg):
        return None
    with open(cfg, 'r', encoding='utf-8') as fh:
        return [l.strip().replace(chr(92), '/').strip('/').lower()
                for l in fh if l.strip() and not l.strip().startswith('#')]


def es_protegida(path, protegidas):
    ruta = '/' + os.path.abspath(path).replace(chr(92), '/').strip('/').lower() + '/'
    return any('/' + frag + '/' in ruta for frag in protegidas)


def carpeta_id(*rutas):
    """La carpeta del id si el registro o el lote viven en <id>/_agentes/ junto a un ID_SPEC."""
    for p in rutas:
        if not p:
            continue
        d = os.path.dirname(os.path.abspath(p))
        if os.path.basename(d).lower() == '_agentes' and os.path.isfile(os.path.join(d, 'ID_SPEC.md')):
            return os.path.dirname(d)
    return None


def ultimo_md5(registro, path, base):
    """md5 que dejo la ultima fila del REGISTRO para este archivo (None si no hay)."""
    if not registro or not os.path.isfile(registro):
        return None
    objetivo = idw.clave(path)
    ultimo = None
    for linea in open(registro, 'r', encoding='utf-8', errors='replace'):
        try:
            fila = json.loads(linea)
        except ValueError:
            continue
        if fila.get('md5_despues') and idw.clave_fila(fila, base) == objetivo:
            ultimo = fila['md5_despues']
    return ultimo


def main():
    ap = argparse.ArgumentParser(add_help=True)
    ap.add_argument('blocks_file', help='archivo con los ---TRANSFER_BLOCK---')
    ap.add_argument('--apply', action='store_true', help='escribir de verdad (por defecto solo simula)')
    ap.add_argument('--override', action='append', default=[],
                    help='nombre.php=RUTA para redirigir el destino (repetible)')
    ap.add_argument('--diff', action='store_true', help='imprimir el diff unificado completo')
    ap.add_argument('--registro', help='con --apply, agrega una linea JSON por archivo escrito a este .jsonl')
    ap.add_argument('--lint', action='store_true', help='con --apply, lint del resultado y del backup')
    ap.add_argument('--hallazgo', default='', help='con --registro, hallazgo que corrige este lote (ej. H1)')
    args = ap.parse_args()

    if not os.path.isfile(args.blocks_file):
        sys.stderr.write('ERROR: no existe %s\n' % args.blocks_file)
        return 4

    overrides = {}
    for o in args.override:
        if '=' not in o:
            sys.stderr.write('ERROR: --override espera nombre=ruta\n')
            return 4
        k, v = o.split('=', 1)
        overrides[k.strip()] = v.strip()

    # Normalizar los saltos del LOTE antes de parsear. Los archivos de prompt
    # suelen venir con CRLF y LF mezclados segun el editor que los guardo, y
    # esa mezcla se colaba dentro de los search/replace. El final de linea que
    # vale es el del ARCHIVO DESTINO, y se reaplica en normaliza_eol().
    crudo = leer(args.blocks_file)
    try:
        texto = crudo.decode('utf-8')
    except UnicodeDecodeError:
        # Lotes escritos a mano en sesiones viejas pueden venir en latin-1.
        # Decodificarlos mal convierte cada acento en U+FFFD, y el bloque se
        # rechaza despues como UNENCODABLE: un sintoma que enganaba sobre la
        # causa real.
        texto = crudo.decode('latin-1')
    texto = texto.replace('\r\n', '\n').replace('\r', '\n')
    bloques = parsear_bloques(texto)
    if not bloques:
        sys.stderr.write('ERROR: no se encontro ningun ---TRANSFER_BLOCK--- en el archivo\n')
        return 4

    base_id = carpeta_id(args.registro, args.blocks_file)

    # Agrupar por archivo destino, conservando el orden de aparicion.
    por_archivo = []
    for b in bloques:
        if 'error' in b:
            print('  %2d  MAL FORMADO: %s' % (b['n'], b['error']))
            return 1
        destino = overrides.get(os.path.basename(b['path'].replace('\\', '/')), b['path'])
        destino, error = idw.expandir(destino, base_id)
        if error:
            print('RUTA: bloque %d: %s. No se escribio nada.' % (b['n'], error))
            return 6
        for entrada in por_archivo:
            if os.path.normcase(entrada['path']) == os.path.normcase(destino):
                entrada['bloques'].append(b)
                break
        else:
            por_archivo.append({'path': destino, 'bloques': [b]})

    # Alcance: con un id, solo sus Archivos objetivo; sin id, nunca un repo.
    nuevos = set()
    if base_id:
        spec = idw.leer_spec(os.path.join(base_id, '_agentes', 'ID_SPEC.md'))
        permitidos = set(idw.clave(idw.absoluta(a['ruta'], base_id)) for a in spec['archivos'])
        nuevos = set(idw.clave(idw.absoluta(a['ruta'], base_id)) for a in spec['archivos'] if idw.es_nuevo(a))
        for entrada in por_archivo:
            if idw.clave(entrada['path']) not in permitidos:
                print('FUERA_DE_ALCANCE: %s no esta en Archivos objetivo del ID_SPEC de %s. '
                      'No se escribio nada.' % (entrada['path'], os.path.basename(base_id)))
                return 6
    else:
        for entrada in por_archivo:
            repo = idw.repo_de(os.path.abspath(entrada['path']))
            if repo:
                print('FUERA_DE_ALCANCE: %s es del repo %s y el lote no es de un id (<id>/_agentes/). '
                      'No se escribio nada.' % (entrada['path'], repo[0]))
                return 6

    if args.apply:
        protegidas = rutas_protegidas()
        if protegidas is None:
            print('PROTEGIDO: falta .opencode/protected_paths.txt. No se escribio nada.')
            return 5
        for entrada in por_archivo:
            if es_protegida(entrada['path'], protegidas):
                print('PROTEGIDO: %s esta dentro de una ruta protegida. No se escribio nada.' % entrada['path'])
                return 5
        for entrada in por_archivo:
            repo = idw.repo_de(os.path.abspath(entrada['path']))
            git = idw.info_git(repo[1]) if repo else None
            entrada['repo'] = repo[0] if repo else None
            entrada['git'] = git
            if git and git['rama'] in idw.RAMAS_BASE:
                print('RAMA_BASE: el repo %s esta en la rama %s. Crea la rama del id (los comandos de git '
                      'los ejecuta el desarrollador) y vuelve a aplicar. No se escribio nada.'
                      % (repo[0], git['rama']))
                return 6

    print('Lote: %d bloque(s) sobre %d archivo(s)' % (len(bloques), len(por_archivo)))
    print('Modo: %s' % ('APLICAR' if args.apply else 'SIMULACION (no escribe nada)'))

    planes = []
    fallo = 0

    for entrada in por_archivo:
        path = entrada['path']
        print('')
        print('=' * 74)
        print('DESTINO: %s' % path)
        entrada['creado'] = False
        if not os.path.isfile(path):
            # Archivo NUEVO del id: solo si el spec lo marca 'nuevo: si', con UN bloque de
            # search_block vacio (el contenido completo va en el replace). Nunca crea carpetas.
            if idw.clave(path) not in nuevos:
                print('  *** NO EXISTE *** (si el id lo crea, marca "nuevo: si" en Archivos objetivo)')
                fallo = 1
                continue
            if len(entrada['bloques']) != 1 or entrada['bloques'][0]['search'].strip():
                print('  *** NUEVO: el archivo no existe; se crea con UN solo bloque de search_block vacio ***')
                fallo = 1
                continue
            if not os.path.isdir(os.path.dirname(path)):
                print('  *** NUEVO: la carpeta %s no existe; este script no crea carpetas ***' % os.path.dirname(path))
                fallo = 1
                continue
            entrada['creado'] = True
            print('  NUEVO: el archivo se crea con este lote (ISO-8859-1, CRLF)')

        raw = b'' if entrada['creado'] else leer(path)
        antes = metricas(raw)
        # Un archivo nuevo sigue el estandar de la casa: CRLF.
        usa_crlf = True if entrada['creado'] else antes['crlf'] > antes['lf_sueltos']
        txt = raw.decode('latin-1')
        print('  antes: %d bytes, %d lineas, %s, %d tab-inicial, %d con espacios finales'
              % (antes['bytes'], antes['lineas'], 'CRLF' if usa_crlf else 'LF',
                 antes['tab_inicial'], antes['espacios_finales']))
        print('  ' + '-' * 70)

        trabajo = txt
        for b in entrada['bloques']:
            s = normaliza_eol(b['search'], usa_crlf)
            r = normaliza_eol(b['replace'], usa_crlf)
            try:
                r.encode('latin-1')
            except UnicodeEncodeError as exc:
                print('  %2d  UNENCODABLE: el replace trae caracteres fuera de latin-1 (%s)' % (b['n'], exc))
                fallo = 2
                continue
            # El formato es ambiguo cuando un bloque termina en lineas en
            # blanco: no hay forma de saber si pertenecen al texto o separan
            # del siguiente marcador. En vez de adivinar, se prueban las
            # variantes y se usa la que ancla EXACTAMENTE una vez. El mismo
            # recorte se aplica al replace, para que el delta de lineas no se
            # descuadre.
            recorte = 0
            n = trabajo.count(s)
            while n != 1 and s.endswith('\n') and recorte < 4:
                s = s[:-1] if not s.endswith('\r\n') else s[:-2]
                if r.endswith('\r\n'):
                    r = r[:-2]
                elif r.endswith('\n'):
                    r = r[:-1]
                recorte += 1
                n = trabajo.count(s)

            # Solo las lineas nuevas: un comentario legacy que ya estaba en el search no se juzga.
            previas = set(l.strip() for l in s.split('\n'))
            malas = [l for l in andamiaje_en_comentarios(r) if l.strip() not in previas]
            if malas:
                for l in malas:
                    print('  %2d  ESTANDAR  comentario con andamiaje del flujo: %s' % (b['n'], l))
                fallo = fallo or 3
            # Mensajes al usuario: siempre SweetAlert (swal / sweetAlertN / Swal.fire), nunca alert()/confirm() nativo.
            nativas = [l for l in r.split('\n') if l.strip() not in previas and ALERTA_NATIVA.search(l)
                       and not l.strip().startswith(('//', '*', '/*', '#'))]
            if nativas:
                for l in nativas:
                    print('  %2d  ESTANDAR  alerta nativa, usar SweetAlert: %s' % (b['n'], l.strip()[:120]))
                fallo = fallo or 3

            etiqueta = s.strip().splitlines()[0][:56] if s.strip() else '(vacio)'
            if n == 1:
                trabajo = trabajo.replace(s, r, 1)
                nota = '' if recorte == 0 else '  (recorte %d)' % recorte
                print('  %2d  OK        %s%s' % (b['n'], etiqueta, nota))
            elif n == 0:
                print('  %2d  NOT_FOUND %s' % (b['n'], etiqueta))
                fallo = fallo or 1
            else:
                print('  %2d  MULTIPLE(%d) %s' % (b['n'], n, etiqueta))
                fallo = fallo or 1

        nuevo_raw = trabajo.encode('latin-1')
        despues = metricas(nuevo_raw)
        print('  ' + '-' * 70)
        print('  despues: %d bytes (%+d), %d lineas (%+d), %d tab-inicial (%+d), %d con espacios finales (%+d)'
              % (despues['bytes'], despues['bytes'] - antes['bytes'],
                 despues['lineas'], despues['lineas'] - antes['lineas'],
                 despues['tab_inicial'], despues['tab_inicial'] - antes['tab_inicial'],
                 despues['espacios_finales'], despues['espacios_finales'] - antes['espacios_finales']))

        mezcla = (despues['crlf'] > 0 and despues['lf_sueltos'] > 0)
        if mezcla:
            print('  *** AVISO: el resultado mezcla CRLF y LF ***')
        if despues['salto_final'] != antes['salto_final']:
            print('  *** AVISO: cambio el salto final ***')

        a = txt.replace('\r\n', '\n').split('\n')
        b_ = trabajo.replace('\r\n', '\n').split('\n')
        diff = list(difflib.unified_diff(a, b_, lineterm='', n=0))
        add = sum(1 for l in diff if l.startswith('+') and not l.startswith('+++'))
        rem = sum(1 for l in diff if l.startswith('-') and not l.startswith('---'))
        print('  diff: %d lineas anadidas, %d retiradas' % (add, rem))
        if args.diff:
            print('')
            for l in diff:
                print('    ' + l)

        planes.append((path, raw, nuevo_raw, entrada, add, rem))

    print('')
    print('=' * 74)
    if fallo:
        print('RESULTADO: el lote NO es aplicable. No se escribio nada.')
        print('Regla todo-o-nada: un solo bloque que no ancle detiene el lote entero,')
        print('para no dejar ningun archivo a medio aplicar.')
        return fallo

    if not args.apply:
        print('RESULTADO: simulacion limpia. Todos los bloques anclan de forma unica.')
        print('Vuelve a correrlo con --apply para escribir.')
        return 0

    sello = datetime.datetime.now().strftime('%Y-%m-%d_%H%M%S')
    lote_copia = None
    if args.registro:
        # El BLOQUES_<archivo>.txt se sobrescribe en cada pasada: esta copia es la
        # unica forma de saber despues que escribio EXACTAMENTE este lote (manual,
        # reversion de un item, retrabajo).
        dir_lotes = os.path.join(os.path.dirname(os.path.abspath(args.registro)), 'lotes')
        if not os.path.isdir(dir_lotes):
            os.makedirs(dir_lotes)
        lote_copia = os.path.join(dir_lotes, '%s_%s' % (sello, os.path.basename(args.blocks_file)))
        shutil.copyfile(args.blocks_file, lote_copia)
    peor_lint = 0
    for path, raw, nuevo_raw, entrada, add, rem in planes:
        bloques_archivo = entrada['bloques']
        # Con un id el backup va a _agentes/respaldos: nunca dentro de un repo.
        if base_id:
            dir_resp = os.path.join(base_id, '_agentes', 'respaldos')
            if not os.path.isdir(dir_resp):
                os.makedirs(dir_resp)
            bak = os.path.join(dir_resp, '%s.PRE_%s.bak' % (os.path.basename(path), sello))
            if os.path.exists(bak):
                # dos archivos del lote con el mismo nombre en carpetas distintas
                bak = os.path.join(dir_resp, '%s_%s.PRE_%s.bak' % (
                    os.path.basename(os.path.dirname(path)), os.path.basename(path), sello))
        else:
            bak = '%s.PRE_%s.bak' % (path, sello)
        md5_previo = ultimo_md5(args.registro, path, base_id)
        cambio_externo = bool(md5_previo) and md5_previo != hashlib.md5(raw).hexdigest()
        if cambio_externo:
            print('AVISO_CAMBIO_EXTERNO: %s cambio fuera del flujo desde su ultima escritura registrada '
                  '(editor, pull o cambio de rama). El lote anclo sobre el estado actual; revisa el diff.'
                  % os.path.basename(path))
        with open(bak, 'wb') as fh:
            fh.write(raw)
        with open(path, 'wb') as fh:
            fh.write(nuevo_raw)
        releido = leer(path)
        estado = 'OK' if releido == nuevo_raw else '*** LA RELECTURA NO COINCIDE ***'
        md5_antes = hashlib.md5(raw).hexdigest()
        md5_despues = hashlib.md5(releido).hexdigest()
        print('ESCRITO  %s  (%d bytes)  %s' % (path, len(releido), estado))
        print('BACKUP   %s' % bak)
        print('MD5      antes %s  despues %s' % (md5_antes, md5_despues))
        resultado_lint = None
        if args.lint:
            res, cmd, salida, salida_bak = lint(path, bak)
            resultado_lint = {'resultado': res, 'comando': cmd, 'salida': salida[:800],
                              'salida_backup': salida_bak[:800]}
            print('LINT     %s: %s%s' % (os.path.basename(path), res, ('  (%s)' % cmd) if cmd else ''))
            if res != 'ok' and salida:
                for l in salida.splitlines()[:6]:
                    print('         ' + l)
            if res == 'error_nuevo':
                peor_lint = 7
        if args.registro:
            # Fuente de la ficha de trazabilidad del manual: nadie transcribe
            # ni calcula estos valores a mano.
            items = sorted(set(i for b in bloques_archivo for i in b['items']))
            huellas = {}
            if base_id:
                huellas = idw.huellas_items(os.path.join(base_id, '_agentes', 'ID_SPEC.md'),
                                            [str(i) for i in items])
            git = entrada.get('git') or {}
            fila = {
                'fecha': datetime.datetime.now().isoformat(timespec='seconds'),
                'archivo': os.path.abspath(path),
                'archivo_ref': idw.simbolizar(os.path.abspath(path), base_id),
                'repo': entrada.get('repo'),
                'rama': git.get('rama'),
                'commit_base': git.get('commit'),
                'items_hash': huellas,
                'cambio_externo': cambio_externo,
                'backup_ref': idw.simbolizar(os.path.abspath(bak), base_id),
                'lote': os.path.abspath(args.blocks_file),
                'lote_copia': os.path.abspath(lote_copia),
                'items': items,
                'bloques_detalle': [{'n': b['n'], 'items': b['items'], 'justificacion': b['justificacion'][:200]}
                                    for b in bloques_archivo],
                'hallazgo': args.hallazgo or None,
                'lint': resultado_lint,
                'bloques': len(bloques_archivo),
                'lineas_anadidas': add,
                'lineas_retiradas': rem,
                'bytes_antes': len(raw),
                'bytes_despues': len(releido),
                'md5_antes': md5_antes,
                'md5_despues': md5_despues,
                'backup': os.path.abspath(bak),
                'verificado': releido == nuevo_raw,
                'creado': entrada.get('creado', False),
            }
            carpeta = os.path.dirname(os.path.abspath(args.registro))
            if not os.path.isdir(carpeta):
                os.makedirs(carpeta)
            with open(args.registro, 'a', encoding='utf-8') as fh:
                fh.write(json.dumps(fila, ensure_ascii=False) + '\n')
            print('REGISTRO %s' % args.registro)
    if lote_copia:
        print('LOTE     %s' % lote_copia)
    print('')
    print('RESULTADO: lote aplicado. El backup es del estado ORIGINAL completo,')
    print('no del bloque anterior: un solo punto de retorno para todo el lote.')
    if peor_lint:
        print('LINT: hay un error que el backup NO tenia: es del cambio. Corrigelo (un ciclo)')
        print('o restaura el backup.')
    elif not args.lint:
        print('PENDIENTE, y no lo hace este script sin --lint: php -l / node --check sobre el')
        print('archivo completo.')
    print('PENDIENTE siempre: la prueba funcional en navegador.')
    return peor_lint


if __name__ == '__main__':
    sys.exit(main())
