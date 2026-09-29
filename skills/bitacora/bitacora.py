#!/usr/bin/env python
# -*- coding: ascii -*-
"""
bitacora.py - bitacora diaria de trabajo, una linea por accion de un agente.

Existe porque ningun agente ve las sesiones de los demas: time_report arma el
reporte del dia leyendo este archivo, no la memoria de una conversacion.

Archivo: <carpeta .opencode>/logs/AAAA-MM-DD.md (append-only).

USO
  python bitacora.py add --id 580000 --agente implementer --accion "..." --resultado "..."
  python bitacora.py show                    bitacora de hoy
  python bitacora.py show --fecha 2026-09-15
"""
import argparse
import datetime
import os
import sys

# /reporte inyecta esta salida por un pipe que se decodifica como UTF-8; en
# Windows Python escribe por defecto en cp1252 y los acentos llegaban rotos.
for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding='utf-8', errors='replace')
    except AttributeError:
        pass

OPENCODE = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))


def logs_configurados():
    """Carpeta registrada con 'id_workspace.py configurar --logs' para este proyecto,
    para que la bitacora sea una sola aunque se trabaje en dos equipos."""
    import json
    try:
        with open(os.path.join(os.path.expanduser('~'), '.opencode_oet_rutas.json'), 'r', encoding='utf-8') as fh:
            cfg = json.load(fh)
    except (IOError, OSError, ValueError):
        return None
    proyecto = os.path.normcase(os.path.normpath(os.path.dirname(OPENCODE)))
    return (cfg.get(proyecto) or {}).get('logs')


LOGS = os.environ.get('OET_LOGS_DIR') or logs_configurados() or os.path.join(OPENCODE, 'logs')


def limpiar(texto):
    # Una accion = una linea: los saltos romperian la tabla.
    return ' '.join((texto or '').replace('|', '/').split())


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest='comando')
    a = sub.add_parser('add')
    a.add_argument('--id', default='-')
    a.add_argument('--agente', required=True)
    a.add_argument('--accion', required=True)
    a.add_argument('--resultado', default='')
    s = sub.add_parser('show')
    s.add_argument('--fecha', default=datetime.date.today().isoformat())
    args = ap.parse_args()

    if args.comando == 'add':
        hoy = datetime.date.today().isoformat()
        ruta = os.path.join(LOGS, hoy + '.md')
        if not os.path.isdir(LOGS):
            os.makedirs(LOGS)
        nuevo = not os.path.isfile(ruta)
        with open(ruta, 'a', encoding='utf-8') as fh:
            if nuevo:
                fh.write('# Bitacora %s\n\n| hora | id | agente | accion | resultado |\n|---|---|---|---|---|\n' % hoy)
            fh.write('| %s | %s | %s | %s | %s |\n' % (
                datetime.datetime.now().strftime('%H:%M'), limpiar(args.id), limpiar(args.agente),
                limpiar(args.accion), limpiar(args.resultado)))
        print('BITACORA: %s' % ruta)
        return 0

    if args.comando == 'show':
        ruta = os.path.join(LOGS, args.fecha + '.md')
        if not os.path.isfile(ruta):
            print('SIN_BITACORA: no hay registros para %s' % args.fecha)
            return 3
        sys.stdout.write(open(ruta, 'r', encoding='utf-8').read())
        return 0

    ap.print_help()
    return 4


if __name__ == '__main__':
    sys.exit(main())
