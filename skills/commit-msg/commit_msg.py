#!/usr/bin/env python
# -*- coding: ascii -*-
"""
commit_msg.py - reune los hechos para el mensaje de commit y del pull request de
un id, por repo. NUNCA ejecuta git: el desarrollador hace add, commit y push.

Existe porque el mensaje debe salir de lo que de verdad se escribio (REGISTRO.jsonl)
y de lo que se decidio (bitacora, ID_SPEC), no de la memoria de una sesion.

USO
  python commit_msg.py <carpeta>              hechos desde el ultimo mensaje sugerido
  python commit_msg.py <carpeta> --todo       hechos de todo el id
  python commit_msg.py <carpeta> --registrar <repo> [--tipo feat|fix]
                                              deja constancia en _agentes/COMMITS.jsonl de
                                              que ya se escribio el mensaje de ese repo

Formato del equipo (lo aplica el agente commits):
  [REQ_<id>] <feat|fix>: <descripcion corta en espanol>

CODIGOS DE SALIDA
  0 ok | 3 no existe el id o su ID_SPEC | 4 error de uso
"""
import datetime
import json
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

OPENCODE = os.path.normpath(os.path.join(AQUI, '..', '..'))


def dir_bitacora():
    if os.environ.get('OET_LOGS_DIR'):
        return os.environ['OET_LOGS_DIR']
    logs = idw.leer_config().get(idw.clave(idw.PROYECTO), {}).get('logs')
    return logs or os.path.join(OPENCODE, 'logs')


def es_del_id(id_fila, accion, id_spec, carpeta_id, archivos):
    """Un id grande se parte en carpetas (548866, 548866_v2) que comparten numero:
    la fila es de esta carpeta si la nombra, o si nombra uno de sus archivos."""
    if id_fila == carpeta_id:
        return True
    if id_fila != id_spec:
        return False
    if carpeta_id == id_spec:
        return not re.search(r'\b%s_\w+' % re.escape(id_spec), accion)
    return carpeta_id in accion or any(a in accion for a in archivos)


def bitacora_del_id(id_spec, carpeta_id, archivos, desde):
    """Filas (fecha hora, agente, accion, resultado) de la bitacora para esta carpeta de id."""
    carpeta = dir_bitacora()
    filas = []
    if not os.path.isdir(carpeta):
        return filas
    for nombre in sorted(os.listdir(carpeta)):
        m = re.match(r'^(\d{4}-\d{2}-\d{2})\.md$', nombre)
        if not m:
            continue
        for linea in open(os.path.join(carpeta, nombre), 'r', encoding='utf-8', errors='replace'):
            partes = [p.strip() for p in linea.strip().strip('|').split('|')]
            if len(partes) < 5 or not re.match(r'^\d{2}:\d{2}$', partes[0]):
                continue
            if not es_del_id(partes[1], partes[3], id_spec, carpeta_id, archivos):
                continue
            cuando = '%sT%s' % (m.group(1), partes[0])
            if cuando >= desde[:16]:
                filas.append((cuando.replace('T', ' '), partes[2], partes[3], partes[4]))
    return filas


def sugerencias(trabajo):
    salida = []
    ruta = os.path.join(trabajo, 'COMMITS.jsonl')
    if os.path.isfile(ruta):
        for linea in open(ruta, 'r', encoding='utf-8', errors='replace'):
            try:
                salida.append(json.loads(linea))
            except ValueError:
                pass
    return salida


def agrupar(base, filas):
    """{grupo: {'carpeta', 'archivos': {relativa: datos}}}. grupo = repo o 'copias'."""
    grupos = {}
    for f in filas:
        ruta = idw.absoluta(f.get('archivo_ref') or f.get('archivo', ''), base)
        repo = idw.repo_de(ruta)
        if repo:
            grupo, carpeta = repo
            rel = os.path.relpath(ruta, carpeta).replace('\\', '/')
        else:
            grupo, carpeta = 'copias', base
            rel = os.path.relpath(ruta, base).replace('\\', '/') if ruta.lower().startswith(base.lower()) else ruta
        g = grupos.setdefault(grupo, {'carpeta': carpeta, 'archivos': {}})
        d = g['archivos'].setdefault(rel, {'items': set(), 'mas': 0, 'menos': 0, 'escrituras': 0,
                                            'rama': None})
        d['items'].update(str(i) for i in f.get('items', []))
        d['mas'] += f.get('lineas_anadidas', 0) or 0
        d['menos'] += f.get('lineas_retiradas', 0) or 0
        d['escrituras'] += 1
        d['rama'] = f.get('rama') or d['rama']
    return grupos


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
    trabajo = ctx['trabajo']
    previas = sugerencias(trabajo)

    if '--registrar' in args:
        i = args.index('--registrar')
        if i + 1 >= len(args):
            print('ERROR: --registrar <repo>')
            return 4
        repo = args[i + 1]
        tipo = args[args.index('--tipo') + 1] if '--tipo' in args and args.index('--tipo') + 1 < len(args) else ''
        carpeta = idw.REPOS.get(repo)
        git = idw.info_git(carpeta) if carpeta else None
        fila = {'fecha': datetime.datetime.now().isoformat(timespec='seconds'), 'repo': repo,
                'rama': (git or {}).get('rama'), 'commit_base': (git or {}).get('commit'), 'tipo': tipo}
        with open(os.path.join(trabajo, 'COMMITS.jsonl'), 'a', encoding='utf-8') as fh:
            fh.write(json.dumps(fila, ensure_ascii=False) + '\n')
        print('REGISTRADO: mensaje de %s en COMMITS.jsonl (desde aqui /commit toma solo lo nuevo)' % repo)
        return 0

    todo = '--todo' in args
    desde = '' if todo or not previas else max(p.get('fecha', '') for p in previas)
    escrituras = [f for f in ctx['registro'] if idw.es_escritura(f) and f.get('fecha', '') > desde]
    archivos_id = [os.path.basename(idw.absoluta(a['ruta'], base).replace('\\', '/')) for a in spec['archivos']]

    print('COMMIT DEL ID %s  (carpeta %s)  "%s"  tipo de id: %s'
          % (spec.get('id') or '?', os.path.basename(base), spec.get('titulo') or '-', spec['tipo'] or '-'))
    print('Prefijo: [REQ_%s]' % (spec.get('id') or '?'))
    print('Tipo sugerido: %s' % ('fix (ya se sugirio un mensaje antes: esto es ajuste o correccion)' if previas
                                  else 'feat (primer mensaje del id)'))
    print('Desde: %s' % (desde or 'el inicio del id'))
    if not escrituras:
        print('')
        print('SIN_CAMBIOS: no hay escrituras en REGISTRO.jsonl desde %s. Usa --todo para todo el id.'
              % (desde or 'el inicio'))
        return 0

    grupos = agrupar(base, escrituras)
    for grupo in sorted(grupos, key=lambda g: (g == 'copias', g)):
        g = grupos[grupo]
        print('')
        if grupo == 'copias':
            print('COPIAS EN LA CARPETA DEL ID (no estan en un repo: se copian al repo antes del commit)')
        else:
            git = idw.info_git(g['carpeta']) or {}
            print('REPO %s  (%s)  rama actual %s' % (grupo, g['carpeta'], git.get('rama') or '-'))
            if git.get('rama') in idw.RAMAS_BASE:
                print('  AVISO: el repo esta en %s; el commit va en la rama del id' % git['rama'])
        print('  archivos (rutas para el add, relativas al repo):')
        for rel, d in sorted(g['archivos'].items()):
            print('    %-60s items %-10s +%d/-%d  (%d escritura(s))'
                  % (rel, ','.join(sorted(d['items'], key=lambda x: (len(x), x))) or '-', d['mas'], d['menos'],
                     d['escrituras']))
        destino = 'COMMIT_%s.txt' % grupo
        print('  ESCRIBE: %s  y  %s' % (os.path.join(trabajo, destino), os.path.join(trabajo, 'PR_%s.txt' % grupo)))

    filas = bitacora_del_id(spec.get('id') or '', os.path.basename(base), archivos_id, desde or '0000')
    print('')
    print('LO QUE SE HIZO (bitacora, %d filas; resume desde aqui, sin copiar):' % len(filas))
    for cuando, agente, accion, resultado in filas[-25:]:
        texto = accion if len(accion) <= 220 else accion[:217] + '...'
        print('  %s %s: %s  [%s]' % (cuando, agente, texto, resultado[:60]))
    if len(filas) > 25:
        print('  ... %d filas anteriores omitidas' % (len(filas) - 25))
    decisiones = next((v for k, v in idw.secciones(os.path.join(trabajo, 'ID_SPEC.md')).items()
                       if k.startswith('decisiones')), [])
    if decisiones:
        print('')
        print('ULTIMAS DECISIONES DEL DESARROLLADOR:')
        for linea in decisiones[-3:]:
            print('  ' + (linea if len(linea) <= 220 else linea[:217] + '...'))
    print('')
    print('Despues de escribir cada COMMIT_<repo>.txt: python .opencode/skills/commit-msg/commit_msg.py %s '
          '--registrar <repo> --tipo <feat|fix>' % os.path.basename(base))
    return 0


if __name__ == '__main__':
    sys.exit(main())
