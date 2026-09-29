#!/usr/bin/env python
# -*- coding: ascii -*-
"""
leer_requerimiento.py - extrae, sin interpretar, el texto y las imagenes de los
documentos de un id (PDF, Word, LibreOffice, imagenes) para que el agente
lector los lea.

Existe porque el requerimiento llega casi siempre en PDF con mockups, y ningun
modelo de texto lo abre. El script hace lo mecanico - texto por pagina, tablas,
imagenes a archivos, encabezados repetidos fuera - y deja una referencia estable
por linea (F1.p2.L5) para que el agente cite literal y nunca de memoria. La
interpretacion de las imagenes la hace el agente lector con un modelo con vision.

Salida, dentro de la carpeta del id:
  _requerimiento/fuentes/     copia de los documentos pasados con --doc
  _requerimiento/img/         imagenes extraidas (F<n>_p<pag>_<k>.<ext>)
  _requerimiento/EXTRACCION.md

USO
  python leer_requerimiento.py <carpeta> --listar                 candidatos, sin extraer
  python leer_requerimiento.py <carpeta>                          extrae todos los candidatos
  python leer_requerimiento.py <carpeta> --doc "<ruta>" [--doc ...]   copia y extrae SOLO esos
  python leer_requerimiento.py <carpeta> --solo "<nombre>" [--solo ...]  extrae solo esos candidatos

Candidatos: documentos en la raiz de la carpeta del id y en _requerimiento/fuentes
(.pdf .docx .odt .png .jpg .jpeg .gif .webp .txt). Nunca los .php/.js del id.

Dependencias: pypdf (texto de PDF). Pillow (imagenes de PDF, `pip install pillow`).
PyMuPDF opcional (renderiza paginas escaneadas). Word y LibreOffice sin dependencias.

CODIGOS DE SALIDA
  0 ok | 3 la carpeta no existe | 4 uso | 5 ruta protegida | 6 nada que extraer
"""
import argparse
import datetime
import hashlib
import os
import re
import shutil
import sys
import zipfile
import xml.etree.ElementTree as ET

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding='utf-8', errors='replace')
    except AttributeError:
        pass

AQUI = os.path.dirname(os.path.abspath(__file__))
OPENCODE = os.path.normpath(os.path.join(AQUI, '..', '..'))
sys.path.insert(0, os.path.join(OPENCODE, 'skills', 'id-workspace'))
import id_workspace  # noqa: E402  (resuelve la carpeta igual que el resto del flujo)

EXT_DOC = ('.pdf', '.docx', '.odt', '.txt')
EXT_IMG = ('.png', '.jpg', '.jpeg', '.gif', '.webp')
MIN_LADO = 80          # imagenes menores (logos, iconos) se listan pero no se revisan
MIN_TEXTO_PAGINA = 40  # menos caracteres: pagina escaneada o solo imagen


def protegida(ruta):
    cfg = os.path.join(OPENCODE, 'protected_paths.txt')
    if not os.path.isfile(cfg):
        return True
    frags = [l.strip().replace('\\', '/').strip('/').lower()
             for l in open(cfg, encoding='utf-8') if l.strip() and not l.strip().startswith('#')]
    r = '/' + os.path.abspath(ruta).replace('\\', '/').strip('/').lower() + '/'
    return any('/' + f + '/' in r for f in frags)


def sha(ruta):
    h = hashlib.sha256()
    with open(ruta, 'rb') as fh:
        for b in iter(lambda: fh.read(1 << 16), b''):
            h.update(b)
    return h.hexdigest()


def candidatos(base, fuentes):
    salida = []
    for d in (base, fuentes):
        if not os.path.isdir(d):
            continue
        for n in sorted(os.listdir(d)):
            p = os.path.join(d, n)
            ext = os.path.splitext(n)[1].lower()
            if not os.path.isfile(p) or ext not in EXT_DOC + EXT_IMG:
                continue
            if re.match(r'(?i)(requerimiento_|documentacion_tecnica_)', n):
                continue
            salida.append(p)
    return salida


# ------------------------------------------------------------------ PDF

def extraer_pdf(ruta, tag, dir_img, avisos):
    from pypdf import PdfReader
    lector = PdfReader(ruta)
    paginas = []
    hay_pil = True
    for i, pag in enumerate(lector.pages, 1):
        texto = pag.extract_text() or ''
        imgs = []
        if hay_pil:
            try:
                for k, im in enumerate(pag.images, 1):
                    imgs.append(guardar_img_pdf(im, '%s_p%d_%d' % (tag, i, k), dir_img))
            except ImportError:
                hay_pil = False
                avisos.append('Sin Pillow: las imagenes del PDF no se extrajeron (pip install pillow).')
            except Exception as exc:  # una imagen corrupta no detiene el resto
                avisos.append('%s pagina %d: imagen no extraida (%s)' % (tag, i, exc))
        paginas.append({'n': i, 'texto': texto, 'imgs': imgs})
    for p in paginas:
        if len(p['texto'].strip()) < MIN_TEXTO_PAGINA:
            p['escaneada'] = True
            render = renderizar_pagina(ruta, p['n'], '%s_p%d_pagina' % (tag, p['n']), dir_img)
            if render:
                p['imgs'].append(render)
            else:
                avisos.append('%s pagina %d sin capa de texto: revisar su imagen (PyMuPDF no instalado para renderizarla).'
                              % (tag, p['n']))
    return paginas, len(lector.pages)


def guardar_img_pdf(im, base, dir_img):
    nombre = im.name or ''
    ext = os.path.splitext(nombre)[1].lower()
    ancho = alto = None
    try:
        pil = im.image
        ancho, alto = pil.size
        if ext not in ('.png', '.jpg', '.jpeg'):
            ext = '.png'
            destino = os.path.join(dir_img, base + ext)
            pil.save(destino)
        else:
            destino = os.path.join(dir_img, base + ext)
            open(destino, 'wb').write(im.data)
    except Exception:
        ext = ext or '.bin'
        destino = os.path.join(dir_img, base + ext)
        open(destino, 'wb').write(im.data)
    return {'ruta': destino, 'ancho': ancho, 'alto': alto}


def renderizar_pagina(ruta, n, base, dir_img):
    try:
        import fitz  # PyMuPDF, opcional
    except ImportError:
        return None
    doc = fitz.open(ruta)
    pix = doc[n - 1].get_pixmap(dpi=150)
    destino = os.path.join(dir_img, base + '.png')
    pix.save(destino)
    return {'ruta': destino, 'ancho': pix.width, 'alto': pix.height, 'render': True}


# ------------------------------------------------------------------ Word / LibreOffice

W = '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}'
T_ODF = '{urn:oasis:names:tc:opendocument:xmlns:text:1.0}'
TB_ODF = '{urn:oasis:names:tc:opendocument:xmlns:table:1.0}'


def texto_docx(elem):
    return ''.join(t.text or '' for t in elem.iter(W + 't'))


def extraer_docx(ruta, tag, dir_img):
    lineas = []
    with zipfile.ZipFile(ruta) as z:
        raiz = ET.fromstring(z.read('word/document.xml'))
        cuerpo = raiz.find(W + 'body')
        for bloque in list(cuerpo) if cuerpo is not None else []:
            if bloque.tag == W + 'p':
                t = texto_docx(bloque).strip()
                if t:
                    lineas.append(t)
            elif bloque.tag == W + 'tbl':
                for fila in bloque.iter(W + 'tr'):
                    celdas = [texto_docx(c).strip().replace('|', '/') for c in fila.iter(W + 'tc')]
                    lineas.append('| ' + ' | '.join(celdas) + ' |')
        imgs = extraer_media(z, 'word/media/', tag, dir_img)
    return [{'n': 1, 'texto': '\n'.join(lineas), 'imgs': imgs}], 1


def extraer_odt(ruta, tag, dir_img):
    lineas = []
    with zipfile.ZipFile(ruta) as z:
        raiz = ET.fromstring(z.read('content.xml'))
        for elem in raiz.iter():
            if elem.tag in (T_ODF + 'p', T_ODF + 'h'):
                t = ''.join(elem.itertext()).strip()
                if t:
                    lineas.append(t)
        imgs = extraer_media(z, 'Pictures/', tag, dir_img)
    return [{'n': 1, 'texto': '\n'.join(lineas), 'imgs': imgs}], 1


def extraer_media(z, prefijo, tag, dir_img):
    imgs = []
    k = 0
    for n in sorted(z.namelist()):
        ext = os.path.splitext(n)[1].lower()
        if n.startswith(prefijo) and ext in EXT_IMG + ('.emf', '.wmf'):
            k += 1
            destino = os.path.join(dir_img, '%s_img%d%s' % (tag, k, ext))
            open(destino, 'wb').write(z.read(n))
            imgs.append({'ruta': destino, 'ancho': None, 'alto': None})
    return imgs


# ------------------------------------------------------------------ utilidades

def encabezados_repetidos(paginas):
    """Lineas que se repiten en al menos el 60% de las paginas (membrete, pie)."""
    if len(paginas) < 3:
        return set()
    cuenta = {}
    for p in paginas:
        for l in set(x.strip() for x in p['texto'].splitlines() if x.strip()):
            cuenta[l] = cuenta.get(l, 0) + 1
    return set(l for l, c in cuenta.items() if c >= 0.6 * len(paginas))


def dimension(img):
    if img.get('ancho') is None:
        try:
            from PIL import Image
            with Image.open(img['ruta']) as im:
                img['ancho'], img['alto'] = im.size
        except Exception:
            pass
    return img


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('carpeta')
    ap.add_argument('--doc', action='append', default=[])
    ap.add_argument('--solo', action='append', default=[])
    ap.add_argument('--listar', action='store_true')
    args = ap.parse_args()

    base = id_workspace.resolver(args.carpeta.strip().strip('"'))
    salida = os.path.join(base, '_requerimiento')
    fuentes = os.path.join(salida, 'fuentes')
    dir_img = os.path.join(salida, 'img')

    if not args.listar and protegida(base):
        print('PROTEGIDO: %s esta dentro de una ruta protegida. No se escribio nada.' % base)
        return 5

    elegidos = []
    for d in args.doc:
        d = d.strip().strip('"')
        if not os.path.isfile(d):
            print('ERROR: no existe %s' % d)
            return 4
        if args.listar:
            elegidos.append(d)
            continue
        os.makedirs(fuentes, exist_ok=True)
        destino = os.path.join(fuentes, os.path.basename(d))
        if not os.path.isfile(destino) or sha(destino) != sha(d):
            shutil.copy2(d, destino)
        elegidos.append(destino)

    todos = candidatos(base, fuentes)
    if args.listar:
        print('CARPETA: %s' % base)
        print('CANDIDATOS (%d):' % len(todos + elegidos))
        for p in elegidos + todos:
            info = ''
            if p.lower().endswith('.pdf'):
                try:
                    from pypdf import PdfReader
                    info = '%d paginas' % len(PdfReader(p).pages)
                except Exception as exc:
                    info = 'no se pudo abrir (%s)' % exc
            print('  %-60s %9d bytes  %s  %s  sha256 %s'
                  % (os.path.basename(p), os.path.getsize(p),
                     datetime.datetime.fromtimestamp(os.path.getmtime(p)).strftime('%Y-%m-%d'),
                     info, sha(p)[:12]))
        return 0

    # --doc (fuera de la carpeta) y --solo (ya en la carpeta) se combinan: un id puede
    # tener el documento en Descargas y una nota de socializacion en su carpeta.
    if args.solo:
        quiero = [s.strip().strip('"').lower() for s in args.solo]
        ya = set(os.path.normcase(os.path.abspath(p)) for p in elegidos)
        elegidos += [p for p in todos if os.path.basename(p).lower() in quiero
                     and os.path.normcase(os.path.abspath(p)) not in ya]
    elif not elegidos:
        elegidos = todos
    if not elegidos:
        print('NADA_QUE_EXTRAER: no hay documentos en %s ni en %s. Pasa la ruta con --doc "<ruta>".' % (base, fuentes))
        return 6

    if os.path.isdir(dir_img):
        shutil.rmtree(dir_img)
    os.makedirs(dir_img)

    avisos, bloques, tabla = [], [], []
    for n, ruta in enumerate(elegidos, 1):
        tag = 'F%d' % n
        ext = os.path.splitext(ruta)[1].lower()
        try:
            if ext == '.pdf':
                paginas, total = extraer_pdf(ruta, tag, dir_img, avisos)
            elif ext == '.docx':
                paginas, total = extraer_docx(ruta, tag, dir_img)
            elif ext == '.odt':
                paginas, total = extraer_odt(ruta, tag, dir_img)
            elif ext == '.txt':
                paginas, total = [{'n': 1, 'texto': open(ruta, encoding='utf-8', errors='replace').read(), 'imgs': []}], 1
            else:
                destino = os.path.join(dir_img, '%s%s' % (tag, ext))
                shutil.copy2(ruta, destino)
                paginas, total = [{'n': 1, 'texto': '', 'imgs': [{'ruta': destino}], 'solo_imagen': True}], 1
        except Exception as exc:
            avisos.append('%s %s: no se pudo leer (%s)' % (tag, os.path.basename(ruta), exc))
            continue
        tabla.append((tag, os.path.basename(ruta), ext[1:], total, sha(ruta)[:12], ruta))
        repetidos = encabezados_repetidos(paginas)
        bloques.append((tag, os.path.basename(ruta), paginas, repetidos))

    lineas = ['# Extraccion del requerimiento - %s' % os.path.basename(base), '',
              'Generado %s por leer_requerimiento.py. Es texto EXTRAIDO, no interpretado: cita las '
              'referencias F<n>.p<pag>.L<linea> tal cual.' % datetime.datetime.now().strftime('%Y-%m-%d %H:%M'), '',
              '## Fuentes', '', '| ref | archivo | tipo | paginas | sha256 | ruta |', '|---|---|---|---|---|---|']
    for t in tabla:
        lineas.append('| %s | %s | %s | %d | %s | %s |' % t)
    revisar = []
    for tag, nombre, paginas, repetidos in bloques:
        lineas += ['', '## %s - %s' % (tag, nombre)]
        if repetidos:
            lineas += ['', 'Encabezado o pie repetido en las paginas (omitido abajo):']
            lineas += ['    ' + r for r in sorted(repetidos)]
        for p in paginas:
            lineas += ['', '### %s pagina %d%s' % (tag, p['n'], '  (SIN CAPA DE TEXTO: leer su imagen)' if p.get('escaneada') else '')]
            k = 0
            for l in p['texto'].splitlines():
                l = l.rstrip()
                if not l.strip() or l.strip() in repetidos:
                    continue
                k += 1
                lineas.append('%s.p%d.L%d  %s' % (tag, p['n'], k, l))
            for img in p['imgs']:
                img = dimension(img)
                rel = os.path.relpath(img['ruta'], base).replace('\\', '/')
                tam = '%sx%s' % (img.get('ancho'), img.get('alto')) if img.get('ancho') else 'tamano ?'
                chica = img.get('ancho') and img.get('alto') and min(img['ancho'], img['alto']) < MIN_LADO
                marca = 'omitida (logo o icono)' if chica else 'REVISAR'
                lineas.append('IMAGEN %s  %s  %s' % (rel, tam, marca))
                if not chica:
                    revisar.append(rel)
    if avisos:
        lineas += ['', '## Avisos', ''] + ['- ' + a for a in avisos]
    with open(os.path.join(salida, 'EXTRACCION.md'), 'w', encoding='utf-8', newline='\n') as fh:
        fh.write('\n'.join(lineas) + '\n')

    print('EXTRACCION: %s' % os.path.join(salida, 'EXTRACCION.md'))
    for t in tabla:
        print('  %s %s (%s, %d pag., sha256 %s)' % t[:5])
    print('IMAGENES_POR_REVISAR: %d' % len(revisar))
    for r in revisar:
        print('  ' + r)
    for a in avisos:
        print('AVISO: ' + a)
    return 0


if __name__ == '__main__':
    sys.exit(main())
