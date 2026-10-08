#!/usr/bin/env python
# -*- coding: ascii -*-
"""
id_workspace.py - resuelve la carpeta de un id, su carpeta de trabajo _agentes
y el siguiente paso del flujo.

Existe para que ningun agente adivine rutas ni gaste turnos buscando, y para
que nadie tenga que escribir a mano en un prompt los hechos que un agente
necesita: la carpeta del id, sate_standa, y los bytes, lineas, finales de
linea y codificacion de cada archivo objetivo salen de aqui, siempre igual.

Estructura que asume:
  <IDS_ROOT>/<NN_Mes>/<carpeta>/             documentos del id (y copias solo si hacen falta)
  <IDS_ROOT>/<NN_Mes>/<carpeta>/_agentes/    todo lo que escriben los agentes
      ID_SPEC.md                    entrada: la especificacion parametrizada del id
      SCOPE.json MAP.json IMPACTO.json EQUIVALENCIA_<archivo>.json
      ITEMS_<archivo>_BORRADOR.md   borrador de items de un porte
      BLOQUES_<archivo>.txt         lotes de implementer / migrator
      CERTIFICADO_<archivo>.md      certificado de impacto de implementer
      REGISTRO.jsonl                trazabilidad que escribe apply_blocks
      respaldos/                    estado original de cada archivo antes de cada lote

Raices: NINGUNA viene escrita en este script ni en el ID_SPEC. Cada equipo
registra las suyas una vez con 'configurar'; quedan en ~/.opencode_oet_rutas.json
(perfil del usuario, fuera de .opencode, asi copiar .opencode a otro equipo no
arrastra rutas ajenas). Las variables OET_IDS_ROOT / OET_SATE_STANDA ganan si existen.
PROYECTO es la carpeta que contiene .opencode, desde donde se abre OpenCode.
  IDS_ROOT     carpeta que agrupa los ids por mes (<IDS_ROOT>/<NN_Mes>/<carpeta>)
  repos        nombre logico -> carpeta en este equipo (sate_standa, ws_rndc, ...).
               Tambien una carpeta que no es repo (la de un cliente) se registra asi.

Rutas en el ID_SPEC: con nombre logico, nunca con la unidad de este equipo.
  {repo:sate_standa}\\manifi\\class_manifi.php   archivo del repo (el caso normal)
  {id}\\manifi\\class_manifi_viejo.php           archivo dentro de la carpeta del id
Cada equipo las resuelve con lo que registro; 'normalizar' convierte un spec viejo.
Sin IDS_ROOT todo funciona igual pasando la RUTA COMPLETA del id; solo el
nombre corto y el resumen de todos los ids la necesitan.

Git: este script NUNCA ejecuta git. La rama y el commit de cada repo se leen de
los archivos de .git (HEAD, refs) solo para avisar; las ramas las crea el desarrollador.

USO
  python id_workspace.py raices                   PROYECTO, IDS_ROOT y repos de este equipo (con su rama)
  python id_workspace.py configurar [--ids "<ruta>"] [--repo nombre="<ruta>"]... [--logs "<ruta>"]
                                                  registra las raices de este equipo
                                                  (--sate "<ruta>" equivale a --repo sate_standa=...)
  python id_workspace.py ruta      <carpeta>      imprime la carpeta del id
  python id_workspace.py estado    <carpeta>      hechos del id: spec, archivos objetivo, _agentes
  python id_workspace.py contexto  <carpeta> <archivo> [--items N,M]
                                                  solo lo que necesita una correccion puntual
  python id_workspace.py items     <carpeta>      indice compacto del ID_SPEC (para /cambio)
  python id_workspace.py siguiente [<carpeta>]    ruta del flujo y el comando que sigue
                                                  (sin carpeta: resumen de todos los ids)
  python id_workspace.py verificado <carpeta> <archivo> --items N,M
                                                  deja en REGISTRO que esos items ya estaban
                                                  en el archivo (corrida sin escritura)
  python id_workspace.py sellar    <carpeta>      toma como aplicados los items vigentes de los
                                                  archivos ya escritos (una vez, en ids en curso)
  python id_workspace.py normalizar <carpeta>     pasa las rutas del ID_SPEC y del REGISTRO a
                                                  nombres logicos (con respaldo)
  python id_workspace.py init      <ruta completa del id>   crea _agentes/ID_SPEC.md ahi
  python id_workspace.py init      <carpeta> [NN_Mes]       carpeta existente, o nueva en ese mes
                                                  (sin ruta ni mes no crea nada: la ubicacion es tuya)

<carpeta> es el NOMBRE de la carpeta del id (ej. 566647_v2) o su ruta completa.

CODIGOS DE SALIDA
  0 ok | 2 el id aparece en mas de una carpeta | 3 no existe | 4 error de uso
"""
import datetime
import hashlib
import json
import os
import re
import shutil
import sys

# La salida la lee OpenCode por un pipe y la decodifica como UTF-8. En Windows
# Python escribe por defecto en cp1252: cada acento llegaba como U+FFFD.
for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding='utf-8', errors='replace')
    except AttributeError:
        pass

AQUI = os.path.dirname(os.path.abspath(__file__))
OPENCODE = os.path.normpath(os.path.join(AQUI, '..', '..'))
PROYECTO = os.path.dirname(OPENCODE)
PLANTILLA = os.path.join(OPENCODE, 'templates', 'ID_SPEC.md')
TRABAJO = '_agentes'
SCRIPT = 'python .opencode/skills/id-workspace/id_workspace.py'
MESES = ['Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio', 'Julio',
         'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre']
CONFIG = os.path.join(os.path.expanduser('~'), '.opencode_oet_rutas.json')


def leer_config():
    try:
        with open(CONFIG, 'r', encoding='utf-8') as fh:
            return json.load(fh)
    except (IOError, OSError, ValueError):
        return {}


def raiz(variable, clave_cfg):
    """(ruta o None, origen). Solo lo que el usuario declaro: variable de entorno o configurar."""
    if os.environ.get(variable):
        return os.path.normpath(os.environ[variable]), 'variable ' + variable
    valor = leer_config().get(clave(PROYECTO), {}).get(clave_cfg)
    if valor:
        return os.path.normpath(valor), CONFIG
    return None, ''


def clave(ruta):
    return os.path.normcase(os.path.normpath(ruta))


def repos_registrados():
    """{nombre logico: carpeta} de este equipo. 'sate' (formato anterior de
    configurar) cuenta como sate_standa; OET_SATE_STANDA gana, como antes."""
    entrada = leer_config().get(clave(PROYECTO), {})
    repos = dict((k, os.path.normpath(v)) for k, v in (entrada.get('repos') or {}).items() if v)
    if entrada.get('sate') and 'sate_standa' not in repos:
        repos['sate_standa'] = os.path.normpath(entrada['sate'])
    if os.environ.get('OET_SATE_STANDA'):
        repos['sate_standa'] = os.path.normpath(os.environ['OET_SATE_STANDA'])
    return repos


IDS_ROOT, IDS_ORIGEN = raiz('OET_IDS_ROOT', 'ids')
REPOS = repos_registrados()
SATE_STANDA = REPOS.get('sate_standa')
SATE_ORIGEN = 'variable OET_SATE_STANDA' if os.environ.get('OET_SATE_STANDA') else CONFIG


# ---------------------------------------------------------------- rutas logicas

# {id}\resto  |  {repo:nombre}\resto  |  {repo:nombre} (la raiz del repo)
RE_TOKEN = re.compile(r'^\{(id|repo:([^}\\/]+))\}(?:[\\/]+(.*))?$', re.I)


def expandir(ruta, base=None):
    """Ruta escrita en el spec -> ruta de ESTE equipo. (ruta, error).
    Las absolutas quedan igual (specs viejos) y las relativas cuelgan de la carpeta del id."""
    ruta = (ruta or '').strip().strip('"')
    m = RE_TOKEN.match(ruta)
    if not m:
        if base and ruta and not os.path.isabs(ruta) and '<completar' not in ruta:
            return os.path.normpath(os.path.join(base, ruta)), ''
        return ruta, ''
    resto = m.group(3) or ''
    if m.group(1).lower() == 'id':
        if not base:
            return ruta, 'SIN_ID: {id} necesita la carpeta del id'
        raiz_ = base
    else:
        nombre = m.group(2)
        raiz_ = next((v for k, v in REPOS.items() if k.lower() == nombre.lower()), None)
        if not raiz_:
            return ruta, ('REPO_NO_REGISTRADO: "%s" no esta registrado en este equipo. Una vez: '
                          '%s configurar --repo %s="<carpeta del repo>"' % (nombre, SCRIPT, nombre))
    return (os.path.normpath(os.path.join(raiz_, resto)) if resto else raiz_), ''


def simbolizar(ruta, base=None):
    """Inversa de expandir: una ruta absoluta dentro de la carpeta del id o de un
    repo registrado se escribe con su nombre logico. Lo demas queda igual."""
    if not ruta or RE_TOKEN.match(ruta) or not os.path.isabs(ruta):
        return ruta
    a = clave(ruta)
    candidatos = [('{repo:%s}' % k, v) for k, v in sorted(REPOS.items())]
    if base:
        candidatos.append(('{id}', base))
    mejor = None
    for token, raiz_ in candidatos:
        r = clave(raiz_).rstrip('\\/')
        if a == r or a.startswith(r + os.sep):
            if mejor is None or len(r) > len(clave(mejor[1])):
                mejor = (token, raiz_)
    if not mejor:
        return ruta
    resto = os.path.normpath(ruta)[len(os.path.normpath(mejor[1]).rstrip('\\/')):].lstrip('\\/')
    return mejor[0] + ('\\' + resto if resto else '')


def repo_de(ruta):
    """(nombre, carpeta) del repo registrado que contiene la ruta, o None."""
    if not ruta or not os.path.isabs(ruta):
        return None
    a = clave(ruta)
    mejor = None
    for k, v in REPOS.items():
        r = clave(v).rstrip('\\/')
        if (a == r or a.startswith(r + os.sep)) and (mejor is None or len(r) > len(clave(mejor[1]))):
            mejor = (k, v)
    return mejor


def es_nuevo(archivo):
    """True si el Archivo objetivo del spec dice 'nuevo: si' (el id lo crea; aun no existe)."""
    return (archivo.get('nuevo') or '').strip().lower().startswith('si')


# Ramas en las que apply_blocks no escribe: el desarrollo va en la rama del id.
RAMAS_BASE = ('master', 'main')


def _leer_txt(ruta):
    try:
        with open(ruta, 'r', encoding='utf-8', errors='replace') as fh:
            return fh.read()
    except (IOError, OSError):
        return None


def info_git(carpeta):
    """{'rama', 'commit', 'fetch'} leyendo .git como archivos. Nunca ejecuta git.
    None si la carpeta no es un repo."""
    git = os.path.join(carpeta, '.git')
    if os.path.isfile(git):
        # worktree o submodulo: el archivo .git dice "gitdir: <ruta>"
        linea = (_leer_txt(git) or '').strip()
        if not linea.startswith('gitdir:'):
            return None
        git = os.path.normpath(os.path.join(carpeta, linea[7:].strip()))
    if not os.path.isdir(git):
        return None
    head = (_leer_txt(os.path.join(git, 'HEAD')) or '').strip()
    if not head:
        return None
    comun = git
    commondir = _leer_txt(os.path.join(git, 'commondir'))
    if commondir:
        comun = os.path.normpath(os.path.join(git, commondir.strip()))
    info = {'rama': None, 'commit': None, 'fetch': None}
    if head.startswith('ref:'):
        ref = head[4:].strip()
        info['rama'] = ref[len('refs/heads/'):] if ref.startswith('refs/heads/') else ref
        suelto = _leer_txt(os.path.join(comun, *ref.split('/')))
        if suelto:
            info['commit'] = suelto.strip()[:10]
        else:
            for l in (_leer_txt(os.path.join(comun, 'packed-refs')) or '').splitlines():
                partes = l.strip().split(' ')
                if len(partes) == 2 and partes[1] == ref:
                    info['commit'] = partes[0][:10]
    else:
        info['commit'] = head[:10] + ' (sin rama)'
    fetch = os.path.join(comun, 'FETCH_HEAD')
    if os.path.isfile(fetch):
        info['fetch'] = datetime.datetime.fromtimestamp(os.path.getmtime(fetch)).strftime('%Y-%m-%d %H:%M')
    return info


# ---------------------------------------------------------------- huellas de items

def textos_items(ruta_spec):
    """{numero: texto} de cada '### Item N' del ID_SPEC, sin comentarios ni lineas vacias."""
    crudo = _leer_txt(ruta_spec)
    if crudo is None:
        return {}
    texto = re.sub(r'<!--.*?-->', '', crudo, flags=re.S)
    items, actual, en_items = {}, None, False
    for linea in texto.splitlines():
        m = re.match(r'^##\s+(.*?)\s*$', linea)
        if m:
            en_items = m.group(1).strip().lower().startswith('items')
            actual = None
            continue
        if not en_items:
            continue
        mi = re.match(r'^###\s+Item\s+(\S+)', linea)
        if mi:
            actual = mi.group(1)
            items[actual] = []
            continue
        if actual is not None and linea.strip():
            items[actual].append(' '.join(linea.split()))
    return dict((n, '\n'.join(ls)) for n, ls in items.items())


def huellas_items(ruta_spec, numeros=None):
    """{numero: huella} del texto vigente de cada item. Cambia si cambia su texto."""
    salida = {}
    for n, t in textos_items(ruta_spec).items():
        if numeros is None or n in numeros:
            salida[n] = hashlib.sha1(t.encode('utf-8')).hexdigest()[:12]
    return salida


def es_escritura(fila):
    """Las filas 'verificado' y 'sello' no escribieron el archivo."""
    return not fila.get('tipo')


def exigir_ids_root():
    if IDS_ROOT and os.path.isdir(IDS_ROOT):
        return
    if IDS_ROOT:
        print('SIN_IDS_ROOT: la carpeta registrada no existe: %s' % IDS_ROOT)
    else:
        print('SIN_IDS_ROOT: este equipo no ha registrado la carpeta de ids.')
    print('Usa la ruta completa del id entre comillas, o registrala una vez:')
    print('  %s configurar --ids "<carpeta que agrupa los ids>" --repo sate_standa="<carpeta del repo>"' % SCRIPT)
    sys.exit(3)


# ---------------------------------------------------------------- carpetas

def buscar(carpeta):
    if os.path.isabs(carpeta):
        return [os.path.normpath(carpeta)] if os.path.isdir(carpeta) else []
    if not IDS_ROOT or not os.path.isdir(IDS_ROOT):
        return []
    hallados = []
    for mes in sorted(os.listdir(IDS_ROOT)):
        cand = os.path.join(IDS_ROOT, mes, carpeta)
        if os.path.isdir(cand):
            hallados.append(cand)
    return hallados


def resolver(carpeta):
    if os.path.isabs(carpeta):
        if os.path.isdir(carpeta):
            return os.path.normpath(carpeta)
        print('NO_EXISTE: %s no es una carpeta' % carpeta)
        sys.exit(3)
    exigir_ids_root()
    hallados = buscar(carpeta)
    if not hallados:
        print('NO_EXISTE: no hay carpeta %s en %s' % (carpeta, IDS_ROOT))
        print('Si esta en otro lugar, pasa su ruta completa entre comillas.')
        sys.exit(3)
    if len(hallados) > 1:
        print('MULTIPLE: la carpeta %s aparece en varios meses:' % carpeta)
        for h in hallados:
            print('  ' + h)
        sys.exit(2)
    return hallados[0]


def todas_las_carpetas():
    salida = []
    for mes in sorted(os.listdir(IDS_ROOT)):
        dmes = os.path.join(IDS_ROOT, mes)
        if not os.path.isdir(dmes):
            continue
        for c in sorted(os.listdir(dmes)):
            if os.path.isdir(os.path.join(dmes, c)):
                salida.append((mes, c, os.path.join(dmes, c)))
    return salida


# ---------------------------------------------------------------- ID_SPEC

def leer_spec(ruta):
    """Campos y secciones que usa el router. Tolerante: lo ausente queda vacio."""
    crudo = open(ruta, 'r', encoding='utf-8', errors='replace').read()
    texto = re.sub(r'<!--.*?-->', '', crudo, flags=re.S)
    spec = {'completar': texto.count('<completar'), 'archivos': [], 'raices': [],
            'pares': [], 'preguntas': 0, 'items': [], 'ajenos': 0,
            'ruta_confirmada': False, 'trazados': 0, 'decisiones': 0}
    seccion = ''
    item = None
    preguntas_libres = 0
    for linea in texto.splitlines():
        m = re.match(r'^##\s+(.*?)\s*$', linea)
        if m:
            seccion = m.group(1).strip().lower()
            continue
        if not seccion:
            m = re.match(r'^(id|titulo|tipo|modulo|confirmar_antes_de_aplicar|autor):[ \t]*(.*?)\s*$', linea)
            if m:
                valor = m.group(2)
                spec[m.group(1)] = '' if '<completar' in valor else valor
            continue
        if seccion.startswith('ruta de desarrollo'):
            if re.match(r'^\s*confirmada:\s*si\b', linea, re.I):
                spec['ruta_confirmada'] = True
        elif seccion.startswith('trazabilidad'):
            if re.match(r'^\s*-\s*R\d+\s*->', linea):
                spec['trazados'] += 1
        elif seccion.startswith('decisiones'):
            if re.match(r'^\s*-\s+\S', linea):
                spec['decisiones'] += 1
        elif seccion.startswith('archivos objetivo'):
            m = re.match(r'^\s*-\s*ruta:\s*(.+?)\s*$', linea)
            if m:
                spec['archivos'].append({'ruta': m.group(1), 'rol': '', 'fuente': '', 'nuevo': ''})
                continue
            # nuevo: si -> el archivo aun no existe; lo crea apply_blocks con un bloque de search vacio.
            m = re.match(r'^\s+(rol|fuente|nuevo):\s*(.+?)\s*$', linea)
            if m and spec['archivos'] and '<completar' not in m.group(2):
                spec['archivos'][-1][m.group(1)] = m.group(2)
        elif seccion.startswith('alcance de impacto'):
            m = re.match(r'^\s*-\s*raiz:\s*(.+?)\s*$', linea)
            if m:
                spec['raices'].append(m.group(1))
        elif seccion.startswith('referencia'):
            m = re.match(r'^\s*-\s*par:\s*(.+?)\s*->\s*(.+?)\s*$', linea)
            if m and '<completar' not in linea:
                spec['pares'].append((m.group(1), m.group(2)))
        elif seccion.startswith('preguntas abiertas'):
            if re.match(r'^\s*(\d+[.)]|[-*])\s+\S', linea):
                spec['preguntas'] += 1
            elif linea.strip() and not re.match(r'^\(?\s*(ninguna|no hay|sin preguntas)\b', linea.strip(), re.I):
                preguntas_libres = 1
        elif seccion.startswith('cambios ajenos'):
            if re.match(r'^\s*[-*]\s+\S', linea) and '<completar' not in linea:
                spec['ajenos'] += 1
        elif seccion.startswith('items'):
            m = re.match(r'^###\s+Item\s+(\S+)', linea)
            if m:
                item = {'n': m.group(1), 'archivo': ''}
                spec['items'].append(item)
                continue
            m = re.match(r'^archivo:\s*(.+?)\s*$', linea)
            if m and item is not None and '<completar' not in m.group(1):
                item['archivo'] = m.group(1)
    if not spec['preguntas']:
        spec['preguntas'] = preguntas_libres
    # Un item sin archivo (el de la plantilla, o uno a medio escribir) no guia a nadie.
    spec['items_sin_archivo'] = sum(1 for i in spec['items'] if not i['archivo'])
    spec['items'] = [i for i in spec['items'] if i['archivo']]
    spec['tipo'] = (spec.get('tipo') or '').strip().lower()
    spec['archivos'] = [a for a in spec['archivos'] if '<completar' not in a['ruta']]
    return spec


# ---------------------------------------------------------------- hechos de disco

def hechos_archivo(ruta):
    """Las metricas que apply_blocks usa como criterio de aceptacion, mas la codificacion."""
    try:
        with open(ruta, 'rb') as fh:
            raw = fh.read()
    except (IOError, OSError):
        return None
    crlf = raw.count(b'\r\n')
    lf = raw.count(b'\n') - crlf
    if crlf and lf:
        eol = 'mixto (%d CRLF, %d LF)' % (crlf, lf)
    else:
        eol = 'CRLF' if crlf else ('LF' if lf else 'sin saltos')
    lineas = raw.replace(b'\r\n', b'\n').split(b'\n')
    salto_final = bool(lineas) and lineas[-1] == b''
    if salto_final:
        lineas = lineas[:-1]
    if not re.search(b'[\x80-\xff]', raw):
        cod = 'ascii'
    else:
        try:
            raw.decode('utf-8')
            cod = 'UTF-8 (!) el flujo espera ISO-8859-1: revisa si un editor lo convirtio'
        except UnicodeDecodeError:
            cod = 'ISO-8859-1'
    c1 = len(re.findall(b'[\x80-\x9f]', raw))
    return {
        'bytes': len(raw), 'lineas': len(lineas), 'eol': eol,
        'salto_final': salto_final, 'codificacion': cod, 'bytes_c1': c1,
        'tab_inicial': sum(1 for l in lineas if l.startswith(b'\t')),
        'espacios_finales': sum(1 for l in lineas if l != l.rstrip()),
    }


def absoluta(ruta, base):
    """La ruta del spec resuelta en este equipo ({id}, {repo:x}, relativa o absoluta)."""
    return expandir(ruta, base)[0]


def clave_fila(fila, base):
    """Clave del archivo de una fila de REGISTRO: su nombre logico resuelto aqui
    (sirve en cualquier equipo) o, en filas viejas, la ruta absoluta."""
    if fila.get('archivo_ref'):
        ruta, error = expandir(fila['archivo_ref'], base)
        if not error:
            return clave(ruta)
    return clave(fila.get('archivo', ''))


def cargar_registro(trabajo):
    filas = []
    ruta = os.path.join(trabajo, 'REGISTRO.jsonl')
    if os.path.isfile(ruta):
        for linea in open(ruta, 'r', encoding='utf-8', errors='replace'):
            linea = linea.strip()
            if linea:
                try:
                    filas.append(json.loads(linea))
                except ValueError:
                    pass
    return filas


def fecha_archivo(ruta):
    return datetime.datetime.fromtimestamp(os.path.getmtime(ruta)).strftime('%Y-%m-%d %H:%M')


def nombre_para_comandos(base):
    """El nombre corto si con el se vuelve a encontrar esta misma carpeta; si no
    (id fuera de IDS_ROOT, o nombre repetido), la ruta completa entre comillas."""
    nombre = os.path.basename(base)
    try:
        if [clave(h) for h in buscar(nombre)] == [clave(base)]:
            return nombre
    except OSError:
        pass
    return '"%s"' % base


def contexto(base):
    """Todo lo que el router y 'estado' necesitan de una carpeta de id."""
    trabajo = os.path.join(base, TRABAJO)
    ctx = {'base': base, 'carpeta': nombre_para_comandos(base), 'trabajo': trabajo,
           'artefactos': [], 'spec': None, 'registro': [], 'aplicados': {}, 'huellas': {},
           'requerimientos': [], 'bloques_sueltos': 0, 'manual': None, 'documentos': []}
    for n in sorted(os.listdir(base)):
        p = os.path.join(base, n)
        if os.path.isfile(p):
            if re.match(r'(?i)requerimiento.*\.(md|txt)$', n):
                ctx['requerimientos'].append(n)
            if re.match(r'(?i)bloques_.*\.txt$', n):
                ctx['bloques_sueltos'] += 1
            if re.search(r'(?i)\.(pdf|docx|odt|png|jpe?g|gif|webp)$', n):
                ctx['documentos'].append(n)
    fuentes = os.path.join(base, '_requerimiento', 'fuentes')
    if os.path.isdir(fuentes):
        ctx['documentos'] += ['_requerimiento/fuentes/' + n for n in sorted(os.listdir(fuentes))
                              if os.path.isfile(os.path.join(fuentes, n))]
    for raiz_, _, archivos in os.walk(base):
        for n in archivos:
            if re.match(r'(?i)DOCUMENTACION_TECNICA_ID.*\.html$', n):
                ctx['manual'] = os.path.join(raiz_, n)
    if os.path.isdir(trabajo):
        ctx['artefactos'] = [n for n in sorted(os.listdir(trabajo))
                             if os.path.isfile(os.path.join(trabajo, n))]
        spec = os.path.join(trabajo, 'ID_SPEC.md')
        if os.path.isfile(spec):
            ctx['spec'] = leer_spec(spec)
            ctx['huellas'] = huellas_items(spec)
        ctx['registro'] = cargar_registro(trabajo)
        for fila in ctx['registro']:
            ctx['aplicados'].setdefault(clave_fila(fila, base), []).append(fila)
    return ctx


def etiqueta(ruta_abs, spec, base):
    """Nombre corto de un archivo objetivo para comandos y artefactos (ACTA_, BLOQUES_,
    CERTIFICADO_) y para el campo archivo: de los items. Es el nombre del archivo; si otro
    objetivo del id se llama igual (ConsultaInterfaz.php en sate_standa y en ws_rndc), lleva
    delante el repo, o la carpeta si los dos son del mismo repo: ws_rndc-ConsultaInterfaz.php."""
    nombre = os.path.basename(ruta_abs.replace('\\', '/'))
    iguales = [absoluta(a['ruta'], base) for a in spec['archivos']
               if os.path.basename(absoluta(a['ruta'], base).replace('\\', '/')).lower() == nombre.lower()]
    if len(iguales) <= 1:
        return nombre
    propio = repo_de(ruta_abs)
    mismo_repo = [r for r in iguales if clave(r) != clave(ruta_abs) and repo_de(r) == propio]
    if propio and not mismo_repo:
        return '%s-%s' % (propio[0], nombre)
    return '%s-%s' % (os.path.basename(os.path.dirname(ruta_abs)), nombre)


def items_de(spec, nombre):
    """Numeros de item del spec cuyo archivo es 'nombre', en el orden del spec."""
    return [i['n'] for i in spec['items'] if os.path.basename(i['archivo'].replace('\\', '/')) == nombre]


def estado_items(ctx, filas, numeros):
    """Por item del archivo: 'ok' | 'cambiado' | 'pendiente'. None si ninguna fila
    del archivo tiene huellas (ids trabajados antes de las huellas: logica por fechas)."""
    con_huella = sorted((f for f in filas if f.get('items_hash')), key=lambda f: f.get('fecha', ''))
    if not con_huella:
        return None
    estados = {}
    for n in numeros:
        ultima = None
        for f in con_huella:
            if n in f['items_hash']:
                ultima = f['items_hash'][n]
        if ultima is None:
            # Aplicado antes de las huellas (aparece en 'items' de una fila vieja): se
            # da por hecho; 'sellar' lo deja con huella. Nunca visto: pendiente.
            antes = any(n in [str(i) for i in f.get('items', [])] for f in filas)
            estados[n] = 'ok' if antes else 'pendiente'
        else:
            estados[n] = 'ok' if ultima == ctx['huellas'].get(n) else 'cambiado'
    return estados


def tiene(ctx, nombre):
    return nombre in ctx['artefactos']


def ultima_sugerencia_commit(trabajo, repo=None):
    """Fecha ISO del ultimo mensaje de commit que dejo /commit ('' si ninguno).
    Con repo, solo los mensajes registrados para ese repo."""
    fechas = []
    for linea in (_leer_txt(os.path.join(trabajo, 'COMMITS.jsonl')) or '').splitlines():
        try:
            fila = json.loads(linea)
        except ValueError:
            continue
        if repo is None or fila.get('repo') == repo:
            fechas.append(fila.get('fecha', ''))
    return max(fechas or [''])


# 'items: 4: SEGURO (...); 5: RIESGO (...)' de cada corrida del ACTA. La hora de la
# cabecera (22:08) no coincide: el veredicto tiene que seguir a los dos puntos.
VEREDICTO_ACTA = re.compile(r'(?:^|[\s;,(])(\w+)\s*:\s*(SEGURO|RIESGO|BLOQUEADO|YA_APLICADO)\b')


def veredictos_acta(ruta_acta):
    """{item: (veredicto, cabecera de la corrida)} de la ULTIMA corrida del ACTA que
    da veredicto a cada item. Vacio si el ACTA no existe o no trae la linea 'items:'."""
    salida = {}
    for corrida in re.split(r'(?m)^(?=## Corrida)', _leer_txt(ruta_acta) or ''):
        if not corrida.startswith('## Corrida'):
            continue
        lineas = corrida.splitlines()
        cabecera = lineas[0][3:].strip()
        for linea in lineas:
            m = re.match(r'(?i)^\s*items\s*:(.*)$', linea)
            if m:
                for n, veredicto in VEREDICTO_ACTA.findall(' ' + m.group(1)):
                    salida[n] = (veredicto, cabecera)
    return salida


# ---------------------------------------------------------------- router

def ruta_del_flujo(ctx):
    """(pasos, siguiente, notas). pasos: lista de (marca, texto)."""
    c = ctx['carpeta']
    spec = ctx['spec']
    pasos, notas = [], []
    siguiente = None

    if ctx['bloques_sueltos'] and not ctx['registro']:
        notas.append('Hay %d BLOQUES_*.txt fuera de _agentes y no hay REGISTRO.jsonl: este id se trabajo '
                     'fuera del flujo de comandos. El router no ve lo que ya se aplico y /documentar no '
                     'tendra ficha de trazabilidad.' % ctx['bloques_sueltos'])

    sin_requerimiento = ('pasa el documento del requerimiento: /leer %s "<ruta del PDF o Word>"   '
                         '(si es un cambio menor sin documento: /spec %s cambio: <descripcion>)' % (c, c))
    if ctx['documentos'] and not ctx['requerimientos']:
        pasos.append(('[ ]', '/leer %s   (%d documento(s) sin convertir a REQUERIMIENTO)'
                      % (c, len(ctx['documentos']))))
    elif ctx['requerimientos']:
        pasos.append(('[x]', 'requerimiento: %s' % ', '.join(ctx['requerimientos'])))

    if spec is None:
        pasos.append(('[ ]', 'ID_SPEC: no existe _agentes/ID_SPEC.md'))
        if ctx['requerimientos']:
            siguiente = '/spec %s   (crea _agentes/ID_SPEC.md desde %s)' % (c, ctx['requerimientos'][0])
        elif ctx['documentos']:
            siguiente = '/leer %s   (convierte %s en REQUERIMIENTO_%s.md; luego /spec)' % (
                c, ', '.join(ctx['documentos'][:3]), os.path.basename(ctx['base']))
        else:
            siguiente = sin_requerimiento
        return pasos, siguiente, notas

    tipo = spec['tipo']
    cabecera_ok = spec.get('id') and tipo in ('nuevo', 'porte', 'migracion')
    if not cabecera_ok:
        pasos.append(('[ ]', 'ID_SPEC sin llenar (id/tipo vacios, %d campos <completar)' % spec['completar']))
        if ctx['requerimientos']:
            siguiente = '/spec %s' % c
        elif ctx['documentos']:
            siguiente = '/leer %s   (luego /spec %s)' % (c, c)
        else:
            siguiente = sin_requerimiento
        return pasos, siguiente, notas
    pasos.append(('[x]', 'ID_SPEC: id %s, tipo %s, %d item(s), %d archivo(s) objetivo'
                  % (spec['id'], tipo, len(spec['items']), len(spec['archivos']))))
    if ctx['documentos'] and not ctx['requerimientos']:
        notas.append('Hay documento(s) del requerimiento sin REQUERIMIENTO_*.md: /leer %s y luego /spec %s '
                     'contrasta el ID_SPEC con el documento' % (c, c))
    if spec['completar']:
        pasos.append(('[!]', 'ID_SPEC tiene %d campo(s) <completar sin llenar' % spec['completar']))
    bloqueo = None
    bloqueo_ruta = None
    if spec['ruta_confirmada']:
        pasos.append(('[x]', 'ruta de desarrollo confirmada (%d decision(es) registradas)' % spec['decisiones']))
    else:
        bloqueo_ruta = ('confirma la ruta de desarrollo: /spec %s   (el analista te la propone con evidencia '
                        'y te pregunta; queda en la seccion Ruta de desarrollo del ID_SPEC)' % c)
        bloqueo = bloqueo_ruta
        pasos.append(('[!]', 'Ruta de desarrollo sin confirmar -> /implementar, /migrar y /equivalencia no arrancan'))
    if spec['preguntas']:
        bloqueo = bloqueo or (
            'responde las %d pregunta(s) abiertas: /spec %s (el analista te las pregunta una a una) '
            'o /spec %s respuestas: 1) ... Mientras tanto puedes correr los pasos de analisis.'
            % (spec['preguntas'], c, c))
        pasos.append(('[!]', 'Preguntas abiertas: %d -> /implementar y /migrar no arrancan' % spec['preguntas']))

    objetivos = []
    for a in spec['archivos']:
        ruta, error = expandir(a['ruta'], ctx['base'])
        if error:
            notas.append(error)
            bloqueo = bloqueo or error
        objetivos.append(dict(a, abs=ruta))
    ruta_spec = os.path.join(ctx['trabajo'], 'ID_SPEC.md')
    spec_editado = datetime.datetime.fromtimestamp(os.path.getmtime(ruta_spec)).isoformat()

    # Repos que toca el id: el desarrollo va en una rama propia, nunca en master.
    # Se lee .git como archivos; las ramas las crea el desarrollador.
    repos_id = {}
    for a in objetivos:
        r = repo_de(a['abs'])
        if r:
            repos_id[r[0]] = r[1]
    for nombre_repo, carpeta_repo in sorted(repos_id.items()):
        g = info_git(carpeta_repo)
        if not g:
            pasos.append(('[x]', 'carpeta registrada %s (no es repo git)' % nombre_repo))
            continue
        desc = 'repo %s: rama %s, commit %s%s' % (nombre_repo, g['rama'] or '-', g['commit'] or '-',
                                                  (', ultimo fetch %s' % g['fetch']) if g['fetch'] else '')
        if g['rama'] in RAMAS_BASE:
            pasos.append(('[!]', desc + ' -> crea la rama del id antes de escribir'))
            bloqueo = bloqueo or ('en %s crea la rama del id desde %s actualizado (ej. REQ_%s); los comandos '
                                  'de git los ejecutas tu. apply_blocks no escribe en %s'
                                  % (nombre_repo, g['rama'], spec.get('id') or '<id>', '/'.join(RAMAS_BASE)))
        else:
            pasos.append(('[x]', desc))
            if spec.get('id') and spec['id'] not in (g['rama'] or ''):
                notas.append('la rama %s de %s no menciona el id %s: confirma que es la rama del id'
                             % (g['rama'], nombre_repo, spec['id']))
            # El commit avanzo desde la ultima escritura del id y /commit no dejo constancia:
            # lo mas probable es que el desarrollador commiteo a mano, y el proximo /commit
            # volveria a proponer esos archivos.
            escritas = sorted((f for f in ctx['registro'] if es_escritura(f) and f.get('repo') == nombre_repo),
                              key=lambda f: f.get('fecha', ''))
            if escritas and g['commit'] and escritas[-1].get('commit_base'):
                base_ultima = escritas[-1]['commit_base']
                corto = min(len(base_ultima), len(g['commit']))
                if (base_ultima[:corto] != g['commit'][:corto]
                        and ultima_sugerencia_commit(ctx['trabajo'], nombre_repo) < escritas[-1].get('fecha', '')):
                    notas.append('el commit de %s cambio desde la ultima escritura del id (%s -> %s) y /commit no '
                                 'registro mensaje: si ya commiteaste esos archivos, registralo para que el proximo '
                                 '/commit no los repita: python .opencode/skills/commit-msg/commit_msg.py %s '
                                 '--registrar %s --tipo <feat|fix>'
                                 % (nombre_repo, base_ultima, g['commit'], c, nombre_repo))

    for a in objetivos:
        a['nombre'] = etiqueta(a['abs'], spec, ctx['base'])
        a['delta'] = []
        filas = ctx['aplicados'].get(clave(a['abs']), [])
        a['aplicado'] = bool(filas)
        estados = estado_items(ctx, filas, items_de(spec, a['nombre'])) if tipo != 'migracion' else None
        if estados is not None:
            # Con huellas: solo vuelve lo que cambio en el spec o nunca se aplico.
            a['delta'] = [n for n in items_de(spec, a['nombre']) if estados[n] != 'ok']
            a['aplicado'] = not a['delta']
            cambiados = [n for n in a['delta'] if estados[n] == 'cambiado']
            if cambiados:
                notas.append('items cambiados en el ID_SPEC desde su ultima aplicacion en %s: %s'
                             % (a['nombre'], ','.join(cambiados)))
        else:
            # Sin huellas (id anterior): el ID_SPEC se edito DESPUES de la ultima
            # escritura de este archivo y ninguna corrida lo reviso despues (su ACTA
            # es mas vieja que el spec): vuelve a quedar pendiente entero.
            acta = os.path.join(ctx['trabajo'], 'ACTA_%s.md' % a['nombre'])
            revisado = (os.path.isfile(acta) and
                        datetime.datetime.fromtimestamp(os.path.getmtime(acta)).isoformat() >= spec_editado)
            if filas and spec_editado > max(f.get('fecha', '') for f in filas) and not revisado:
                a['aplicado'] = False
                notas.append('ID_SPEC editado despues de aplicar %s: /implementar <carpeta> %s revisa sus items '
                             'contra el spec vigente (aplica solo lo que falte; si todo esta, lo deja en el ACTA)'
                             % (a['nombre'], a['nombre']))
        if not a['aplicado'] and not os.path.isfile(a['abs']):
            if es_nuevo(a):
                # Archivo que el id crea: no es un faltante. Solo su carpeta debe existir.
                if not os.path.isdir(os.path.dirname(a['abs'])):
                    notas.append('la carpeta de %s no existe: %s' % (a['nombre'], os.path.dirname(a['abs'])))
                    if not bloqueo:
                        bloqueo = 'crea la carpeta %s (el archivo nuevo %s va ahi)' % (
                            os.path.dirname(a['abs']), a['nombre'])
            elif repo_de(a['abs']):
                notas.append('FALTA %s en el repo: revisa la ruta del ID_SPEC o que estes en la rama correcta'
                             % a['abs'])
                if not bloqueo:
                    bloqueo = 'revisa la ruta de %s en el ID_SPEC (no existe en el repo: %s)' % (a['nombre'], a['abs'])
            else:
                notas.append('FALTA la copia de trabajo %s: copiala (del repo o de donde corresponda) '
                             'antes de /implementar o /migrar ese archivo' % a['abs'])
                if not bloqueo:
                    bloqueo = 'copia %s a %s (la copia de trabajo no existe)' % (a['nombre'], a['abs'])

    def cmd_implementar(a):
        todos = items_de(spec, a['nombre'])
        parcial = a['delta'] and len(a['delta']) < len(todos)
        return '/implementar %s %s%s' % (c, a['nombre'], (' items ' + ','.join(a['delta'])) if parcial else '')

    def paso_prueba_y_manual():
        """Solo se llama cuando ningun paso obligatorio quedo pendiente."""
        faltan = [a['nombre'] for a in objetivos if not a['aplicado']]
        if faltan or not objetivos:
            pasos.append(('[!]', 'archivos objetivo sin escritura en REGISTRO.jsonl: %s'
                          % (', '.join(faltan) or 'no hay Archivos objetivo')))
            return ('revisa el ID_SPEC: ningun paso pendiente cubre %s (falta su item, su par o su ruta)'
                    % (', '.join(faltan) or 'los archivos del id'))
        ultimo = max([f.get('fecha', '') for a in objetivos for f in ctx['aplicados'][clave(a['abs'])]
                      if es_escritura(f)] or [''])
        manual = ctx['manual']
        if manual and datetime.datetime.fromtimestamp(os.path.getmtime(manual)).isoformat() >= ultimo:
            pasos.append(('[x]', 'manual: %s' % os.path.basename(manual)))
            if repos_id and ultima_sugerencia_commit(ctx['trabajo']) < ultimo:
                pasos.append(('[ ]', '/commit %s   (mensaje del commit y del pull request)' % c))
                return ('/commit %s   (te deja el mensaje del commit y del pull request; git lo ejecutas tu)' % c)
            return ('/reporte <horas> <notas>  al cierre del dia (si probaste mas casos: '
                    '/documentar %s <casos nuevos> actualiza el manual)' % c)
        pasos.append(('[ ]', 'prueba funcional en navegador (criterios_aceptacion + pruebas_negativas)'))
        pasos.append(('[ ]', '/documentar %s <que se probo>' % c))
        return ('prueba en el navegador los criterios_aceptacion y pruebas_negativas del ID_SPEC; '
                'luego: /documentar %s <que probaste y resultado>' % c)

    if tipo == 'migracion':
        if not objetivos:
            pasos.append(('[ ]', 'Archivos objetivo: falta ruta (DEST) y fuente (SRC)'))
            return pasos, 'completa en el ID_SPEC la ruta (copia limpia) y la linea fuente: (copia vieja)', notas
        for a in objetivos:
            cmd = '/migrar %s "%s" "%s"' % (c, a['abs'], a['fuente'] or '<SRC>')
            if a['aplicado']:
                pasos.append(('[x]', 'migrado %s (%d escritura(s) en REGISTRO)'
                              % (a['nombre'], len(ctx['aplicados'][clave(a['abs'])]))))
            else:
                pasos.append(('[ ]', cmd))
                if not a['fuente']:
                    notas.append('%s no tiene linea fuente: en el ID_SPEC' % a['nombre'])
                siguiente = siguiente or (bloqueo or cmd + '   (sesion nueva: /new)')
        return pasos, siguiente or paso_prueba_y_manual(), notas

    if tipo == 'porte':
        if not spec['pares']:
            pasos.append(('[ ]', 'Referencia: no hay lineas par: referencia -> objetivo'))
            return pasos, 'completa la seccion Referencia del ID_SPEC (un par: por archivo objetivo)', notas
        for ref, obj in spec['pares']:
            nombre = os.path.basename(obj.replace('\\', '/'))
            equiv = 'EQUIVALENCIA_%s.json' % nombre
            borrador = 'ITEMS_%s_BORRADOR.md' % nombre
            items = [i for i in spec['items'] if os.path.basename(i['archivo'].replace('\\', '/')) == nombre]
            destino = [a for a in objetivos if a['nombre'] == nombre]
            aplicado = bool(destino) and destino[0]['aplicado']
            if not tiene(ctx, equiv):
                pasos.append(('[ ]', '/equivalencia %s %s' % (c, nombre)))
                siguiente = siguiente or (bloqueo_ruta or '/equivalencia %s %s   (sesion nueva: /new)' % (c, nombre))
            elif not items:
                pasos.append(('[x]', equiv))
                pasos.append(('[ ]', 'revisar %s y pasar los items aprobados al ID_SPEC' % borrador))
                siguiente = siguiente or ('revisa %s (adaptacion, NO_APLICA, PENDIENTE DE REVISION) y copia '
                                          'los items aprobados a la seccion Items del ID_SPEC' % borrador)
            elif not aplicado:
                cmd = cmd_implementar(destino[0]) if destino else '/implementar %s %s' % (c, nombre)
                pasos.append(('[x]', '%s + %d item(s) en el ID_SPEC' % (equiv, len(items))))
                pasos.append(('[ ]', cmd))
                if not destino:
                    notas.append('%s no esta en Archivos objetivo: agrega su ruta al ID_SPEC' % nombre)
                siguiente = siguiente or (bloqueo or cmd + '   (sesion nueva: /new)')
            else:
                pasos.append(('[x]', 'implementado %s' % nombre))
        return pasos, siguiente or paso_prueba_y_manual(), notas

    # tipo nuevo
    if not objetivos:
        pasos.append(('[ ]', '/scope %s   (no hay Archivos objetivo)' % c))
        return pasos, '/scope %s' % c, notas
    opcionales = []
    if tiene(ctx, 'SCOPE.json'):
        pasos.append(('[x]', 'SCOPE.json'))
    if len(objetivos) > 1:
        if tiene(ctx, 'MAP.json'):
            pasos.append(('[x]', 'MAP.json'))
        else:
            pasos.append(('[-]', '/mapa %s   (opcional: flujo entre los %d archivos)' % (c, len(objetivos))))
            opcionales.append('/mapa %s' % c)
    if tiene(ctx, 'IMPACTO.json'):
        pasos.append(('[x]', 'IMPACTO.json (%s)' % fecha_archivo(os.path.join(ctx['trabajo'], 'IMPACTO.json'))))
    else:
        pasos.append(('[-]', '/impacto %s   (opcional: si toca algo que otros archivos leen)' % c))
        opcionales.append('/impacto %s' % c)
    orden_item = lambda n: (len(n), n)
    for a in objetivos:
        items = items_de(spec, a['nombre'])
        cert = 'CERTIFICADO_%s.md' % a['nombre']
        escrituras = [f for f in ctx['aplicados'].get(clave(a['abs']), []) if es_escritura(f)]
        if a['aplicado']:
            if items:
                pasos.append(('[x]', 'implementado %s (items %s)' % (a['nombre'], ','.join(items))))
            else:
                registrados = sorted(set(str(i) for f in escrituras for i in f.get('items', [])), key=orden_item)
                pasos.append(('[x]', 'implementado %s (sin item propio en el ID_SPEC%s)'
                              % (a['nombre'], ('; REGISTRO: items ' + ','.join(registrados)) if registrados else '')))
        else:
            cmd = cmd_implementar(a)
            pasos.append(('[ ]', '%s   (items %s)' % (cmd, ','.join(a['delta'] or items) or 'NINGUNO')))
            if not items:
                notas.append('%s no tiene items en el ID_SPEC: sobra en Archivos objetivo o falta su item' % a['nombre'])
            siguiente = siguiente or (bloqueo or cmd + '   (sesion nueva: /new)')
        if not items and escrituras:
            # Un item que reparte su logica entre dos archivos deja a uno sin item: el
            # router nunca lo vuelve a pedir y un /cambio de esa logica no llega a el.
            notas.append('%s tiene escrituras en REGISTRO.jsonl pero ningun item propio en el ID_SPEC: un ajuste '
                         'futuro a esa logica no se enrutara a este archivo. Dale su item (/cambio %s ...) y, si el '
                         'codigo ya esta, marcalo: python .opencode/skills/id-workspace/id_workspace.py verificado '
                         '%s %s --items <N>' % (a['nombre'], c, c, a['nombre']))
        # RIESGO/BLOQUEADO solo cuenta para items que siguen pendientes, y por el veredicto
        # de su ultima corrida en el ACTA: el certificado cita RIESGO tambien para decir
        # que un riesgo del IMPACTO quedo resuelto.
        pendientes = a['delta'] or ([] if a['aplicado'] else items)
        if pendientes:
            veredictos = veredictos_acta(os.path.join(ctx['trabajo'], 'ACTA_%s.md' % a['nombre']))
            en_espera = [n for n in pendientes if veredictos.get(n, ('',))[0] in ('RIESGO', 'BLOQUEADO')]
            if en_espera:
                notas.append('ACTA_%s.md: %s en la corrida "%s": esperan tu decision antes de reintentar '
                             '(su linea pendiente: dice que lo desbloquea)'
                             % (a['nombre'], ', '.join('item %s %s' % (n, veredictos[n][0]) for n in en_espera),
                                veredictos[en_espera[-1]][1]))
            elif not veredictos and tiene(ctx, cert):
                # ACTA de una corrida anterior al formato 'items: N: VEREDICTO'.
                texto = _leer_txt(os.path.join(ctx['trabajo'], cert)) or ''
                if re.search(r'\b(RIESGO|BLOQUEADO)\b', texto):
                    notas.append('%s menciona RIESGO/BLOQUEADO y su ACTA no trae veredictos por item: revisa '
                                 'si los items pendientes esperan tu decision' % cert)
    if siguiente and opcionales and not bloqueo:
        siguiente += '\n           antes, si aplica: ' + '  |  '.join(opcionales)
    return pasos, siguiente or paso_prueba_y_manual(), notas


# ---------------------------------------------------------------- comandos

def cmd_raices():
    print('PROYECTO:    %s' % PROYECTO)
    if not IDS_ROOT:
        print('IDS_ROOT:    no registrada')
    else:
        print('IDS_ROOT:    %s%s   (de %s)' % (IDS_ROOT, '' if os.path.isdir(IDS_ROOT) else '  NO EXISTE', IDS_ORIGEN))
    logs = leer_config().get(clave(PROYECTO), {}).get('logs')
    print('BITACORA:    %s' % (os.environ.get('OET_LOGS_DIR') or logs or os.path.join(OPENCODE, 'logs')))
    print('REPOS (en el ID_SPEC se escriben {repo:<nombre>}\\...):')
    if not REPOS:
        print('  ninguno registrado')
    for nombre, carpeta in sorted(REPOS.items()):
        if not os.path.isdir(carpeta):
            print('  %-22s %s   NO EXISTE' % (nombre, carpeta))
            continue
        g = info_git(carpeta)
        estado = ('rama %s, commit %s%s' % (g['rama'] or '-', g['commit'] or '-',
                                            (', ultimo fetch %s' % g['fetch']) if g['fetch'] else '')
                  if g else 'carpeta sin git')
        print('  %-22s %s   (%s)' % (nombre, carpeta, estado))
    if not IDS_ROOT or not REPOS:
        print('')
        print('Registralas una vez en este equipo (quedan en %s):' % CONFIG)
        print('  %s configurar --ids "<carpeta que agrupa los ids>" --repo sate_standa="<carpeta del repo>"' % SCRIPT)
        print('Sin IDS_ROOT todo funciona pasando la ruta completa del id entre comillas.')
    return 0


def cmd_configurar(args):
    uso = ('ERROR: uso: configurar [--ids "<ruta>"] [--repo nombre="<ruta>"]... [--logs "<ruta>"] '
           '(--sate "<ruta>" equivale a --repo sate_standa="<ruta>")')
    valores, repos = {}, {}
    i = 0
    while i < len(args):
        if args[i] in ('--ids', '--logs', '--sate') and i + 1 < len(args):
            v = args[i + 1].strip().strip('"')
            if args[i] == '--sate':
                repos['sate_standa'] = v
            else:
                valores[args[i][2:]] = v
            i += 2
        elif args[i] == '--repo' and i + 1 < len(args) and '=' in args[i + 1]:
            k, v = args[i + 1].split('=', 1)
            k = k.strip()
            if not re.match(r'^[A-Za-z0-9_.-]+$', k):
                print('ERROR: el nombre del repo solo lleva letras, numeros, _ . -: %s' % k)
                return 4
            repos[k] = v.strip().strip('"')
            i += 2
        else:
            print(uso)
            return 4
    if not valores and not repos:
        print(uso)
        return 4
    for k, v in list(valores.items()) + [('repo ' + k, v) for k, v in repos.items()]:
        if not os.path.isabs(v) or not os.path.isdir(v):
            print('ERROR: --%s debe ser una carpeta existente con ruta completa: %s' % (k, v))
            return 4
    cfg = leer_config()
    entrada = cfg.setdefault(clave(PROYECTO), {})
    for k, v in valores.items():
        entrada[k] = os.path.normpath(v)
    if repos:
        registrados = entrada.setdefault('repos', {})
        if entrada.get('sate') and 'sate_standa' not in registrados:
            registrados['sate_standa'] = entrada['sate']
        for k, v in repos.items():
            registrados[k] = os.path.normpath(v)
        if 'sate_standa' in registrados:
            entrada['sate'] = registrados['sate_standa']   # para scripts que leen el formato anterior
    with open(CONFIG, 'w', encoding='utf-8') as fh:
        json.dump(cfg, fh, indent=2, ensure_ascii=False)
    print('GUARDADO en %s para el proyecto %s:' % (CONFIG, PROYECTO))
    for k in ('ids', 'logs'):
        if k in entrada:
            print('  %-22s %s' % (k, entrada[k]))
    for k, v in sorted((entrada.get('repos') or {}).items()):
        print('  repo %-17s %s' % (k, v))
    return 0


def cmd_estado(base):
    ctx = contexto(base)
    print('PROYECTO:    %s' % PROYECTO)
    print('SATE_STANDA: %s' % (SATE_STANDA or 'no registrada en este equipo: usa las lineas raiz del ID_SPEC'))
    for nombre, carpeta in sorted(REPOS.items()):
        g = info_git(carpeta) if os.path.isdir(carpeta) else None
        print('REPO %-18s %s%s' % (nombre, carpeta,
                                   ('   rama %s, commit %s' % (g['rama'] or '-', g['commit'] or '-')) if g else ''))
    print('ID_DIR:      %s' % base)
    print('TRABAJO:     %s' % ctx['trabajo'])
    if not os.path.isdir(ctx['trabajo']):
        print('  (sin carpeta _agentes todavia)')
    else:
        print('')
        print('ARTEFACTOS en _agentes:')
        for n in ctx['artefactos']:
            p = os.path.join(ctx['trabajo'], n)
            print('  %-44s %9d bytes  %s' % (n, os.path.getsize(p), fecha_archivo(p)))
    spec = ctx['spec']
    if spec is None:
        print('FALTA: ID_SPEC.md')
    else:
        print('')
        print('ID_SPEC: id=%s tipo=%s modulo=%s confirmar_antes_de_aplicar=%s autor=%s'
              % (spec.get('id') or '-', spec['tipo'] or '-', spec.get('modulo') or '-',
                 spec.get('confirmar_antes_de_aplicar') or '-', spec.get('autor') or '-'))
        print('  items: %d%s | preguntas abiertas: %d | campos <completar: %d | cambios ajenos al id: %d'
              % (len(spec['items']),
                 (' (+%d sin archivo)' % spec['items_sin_archivo']) if spec['items_sin_archivo'] else '',
                 spec['preguntas'], spec['completar'], spec['ajenos']))
        print('  ruta de desarrollo: %s | decisiones registradas: %d | requisitos trazados: %d'
              % ('confirmada' if spec['ruta_confirmada'] else 'SIN CONFIRMAR', spec['decisiones'], spec['trazados']))
        for r in spec['raices']:
            ruta, error = expandir(r, base)
            if error:
                print('  raiz de impacto: %s   %s' % (r, error))
            else:
                print('  raiz de impacto: %s%s' % (ruta, '' if os.path.isdir(ruta) else '   (NO EXISTE)'))
        for ref, obj in spec['pares']:
            print('  par: %s -> %s' % (absoluta(ref, base), absoluta(obj, base)))
        if spec['archivos']:
            print('')
            print('ARCHIVOS OBJETIVO - hechos leidos del disco ahora; no re-derivarlos.')
            print('(la primera linea es la ruta en ESTE equipo: usala para leer y en file_path)')
            for a in spec['archivos']:
                ruta, error = expandir(a['ruta'], base)
                h = hechos_archivo(ruta) if not error else None
                nombre = etiqueta(ruta, spec, base)
                if error:
                    print('  [SIN RESOLVER] %s   %s' % (a['ruta'], error))
                    continue
                if h is None:
                    if es_nuevo(a):
                        print('  [NUEVO] %s   (lo crea /implementar: un bloque con search_block vacio)' % ruta)
                        items = items_de(spec, etiqueta(ruta, spec, base))
                        print('      en el spec: %s | rol %s | items: %s'
                              % (a['ruta'], a['rol'] or '-', ', '.join(items) or 'ninguno'))
                    else:
                        print('  [FALTA] %s' % ruta)
                    continue
                aplicado = ctx['aplicados'].get(clave(ruta), [])
                r = repo_de(ruta)
                print('  %s' % ruta)
                print('      en el spec: %s%s' % (a['ruta'], ('   (repo %s)' % r[0]) if r else ''))
                print('      rol %s | %d bytes, %d lineas, %s, salto final %s, %s'
                      % (a['rol'] or '-', h['bytes'], h['lineas'], h['eol'],
                         'si' if h['salto_final'] else 'no', h['codificacion']))
                print('      tab-inicial %d, espacios finales %d%s | escrituras en REGISTRO: %d'
                      % (h['tab_inicial'], h['espacios_finales'],
                         (', bytes 0x80-0x9F: %d' % h['bytes_c1']) if h['bytes_c1'] else '',
                         len(aplicado)))
                if a['fuente']:
                    hf = hechos_archivo(absoluta(a['fuente'], base))
                    print('      fuente %s%s' % (absoluta(a['fuente'], base), '' if hf else '   (NO EXISTE)'))
                items = items_de(spec, nombre)
                estados = estado_items(ctx, aplicado, items)
                if estados:
                    print('      items: %s' % (', '.join('%s %s' % (n, estados[n]) for n in items) or 'ninguno'))
                else:
                    print('      items: %s' % (', '.join(items) or 'ninguno'))
    if ctx['requerimientos']:
        print('')
        print('REQUERIMIENTO: %s' % ', '.join(ctx['requerimientos']))
    if ctx['documentos']:
        print('DOCUMENTOS: %s' % ', '.join(ctx['documentos']))
    pasos, siguiente, notas = ruta_del_flujo(ctx)
    for n in notas:
        print('AVISO: ' + n)
    print('')
    print('SIGUIENTE: %s' % siguiente)
    return 0


def cmd_siguiente(base):
    ctx = contexto(base)
    pasos, siguiente, notas = ruta_del_flujo(ctx)
    spec = ctx['spec'] or {}
    print('ID %s  (carpeta %s, tipo %s)' % (spec.get('id') or '?', ctx['carpeta'], spec.get('tipo') or '?'))
    print('ID_DIR: %s' % base)
    print('')
    for marca, texto in pasos:
        print('  %s %s' % (marca, texto))
    for n in notas:
        print('  AVISO: ' + n)
    print('')
    print('SIGUIENTE: %s' % siguiente)
    print('')
    print('([x] hecho  [ ] pendiente  [-] opcional  [!] requiere tu decision)')
    return 0


def cmd_resumen():
    exigir_ids_root()
    print('IDS_ROOT: %s' % IDS_ROOT)
    print('')
    for mes, carpeta, base in todas_las_carpetas():
        ctx = contexto(base)
        pasos, siguiente, notas = ruta_del_flujo(ctx)
        spec = ctx['spec'] or {}
        print('%-13s %-12s tipo %-9s -> %s' % (mes, carpeta, spec.get('tipo') or '-',
                                                siguiente.split('\n')[0]))
    print('')
    print('Detalle de un id: /siguiente <carpeta>')
    return 0


def cmd_init(carpeta, mes):
    # La ubicacion del id la decide el desarrollador, nunca el script: o una
    # ruta completa, o un nombre que ya existe, o un nombre con su mes explicito.
    if os.path.isabs(carpeta):
        base = os.path.normpath(carpeta)
    else:
        exigir_ids_root()
        existentes = buscar(carpeta)
        if len(existentes) > 1:
            resolver(carpeta)
        if existentes:
            base = existentes[0]
        elif mes:
            base = os.path.join(IDS_ROOT, mes, carpeta)
        else:
            print('FALTA_UBICACION: la carpeta %s no existe y no dijiste donde crearla.' % carpeta)
            print('Crea tu la carpeta del id donde quieras y pasa su ruta completa:')
            print('  %s init "D:\\ruta\\de\\tu\\id"' % SCRIPT)
            print('o indica el mes: %s init %s 09_Septiembre' % (SCRIPT, carpeta))
            return 4
    carpeta = os.path.basename(base)
    trabajo = os.path.join(base, TRABAJO)
    if not os.path.isdir(trabajo):
        os.makedirs(trabajo)
    spec = os.path.join(trabajo, 'ID_SPEC.md')
    if os.path.isfile(spec):
        print('YA_EXISTE: %s (no se sobrescribe)' % spec)
    elif os.path.isfile(PLANTILLA):
        texto = open(PLANTILLA, 'r', encoding='utf-8').read()
        # Nunca una ruta de este equipo en el spec: nombres logicos que cada equipo resuelve.
        texto = texto.replace('{ID_DIR}', '{id}').replace('{SATE_STANDA}', '{repo:sate_standa}')
        numero = re.match(r'(\d+)', carpeta)
        if numero:
            texto = texto.replace('id: <completar: numero del id>', 'id: ' + numero.group(1), 1)
        with open(spec, 'w', encoding='utf-8', newline='\n') as fh:
            fh.write(texto)
        print('CREADO: %s' % spec)
    print('ID_DIR: %s' % base)
    print('El codigo se trabaja en el repo, en la rama del id (la creas tu). En esta carpeta van los documentos'
          ' y solo las copias que no viven en un repo. Luego: /leer %s "<ruta del documento>" y /spec %s'
          ' (cambio menor sin documento: /spec %s cambio: <descripcion>)'
          % ((nombre_para_comandos(base),) * 3))
    return 0


def cmd_items(base):
    """Indice compacto del ID_SPEC para /cambio: una linea por item, sin leer codigo."""
    ruta = os.path.join(base, TRABAJO, 'ID_SPEC.md')
    if not os.path.isfile(ruta):
        print('FALTA: %s' % ruta)
        return 3
    texto = re.sub(r'<!--.*?-->', '', open(ruta, 'r', encoding='utf-8', errors='replace').read(), flags=re.S)
    items, actual, seccion = [], None, ''
    ultimo_r, decisiones = 0, []
    for linea in texto.splitlines():
        m = re.match(r'^##\s+(.*?)\s*$', linea)
        if m:
            seccion = m.group(1).strip().lower()
            continue
        if seccion.startswith('trazabilidad'):
            mr = re.match(r'^\s*-\s*R(\d+)\s*->', linea)
            if mr:
                ultimo_r = max(ultimo_r, int(mr.group(1)))
        elif seccion.startswith('decisiones'):
            if re.match(r'^\s*-\s+\S', linea):
                decisiones.append(linea.strip()[2:])
        elif seccion.startswith('items'):
            mi = re.match(r'^###\s+Item\s+(\S+)', linea)
            if mi:
                actual = {'n': mi.group(1), 'archivo': '', 'ubicacion': '', 'objetivo': ''}
                items.append(actual)
                continue
            mc = re.match(r'^(archivo|ubicacion|objetivo):\s*(.*?)\s*$', linea)
            if mc and actual is not None:
                actual[mc.group(1)] = mc.group(2)

    def corto(t, n):
        return t if len(t) <= n else t[:n - 3] + '...'
    print('INDICE ID_SPEC  %s' % ruta)
    print('items: %d | ultimo R trazado: R%d (el siguiente es R%d) | decisiones: %d'
          % (len(items), ultimo_r, ultimo_r + 1, len(decisiones)))
    print('')
    for i in items:
        print('Item %-3s %-24s | %s' % (i['n'], i['archivo'], corto(i['ubicacion'], 70)))
        print('         objetivo: %s' % corto(i['objetivo'], 200))
    if decisiones:
        print('')
        print('Ultimas decisiones:')
        for d in decisiones[-5:]:
            print('  - ' + corto(d, 160))
    return 0


# ---------------------------------------------------------------- correcciones puntuales

def objetivo_por_nombre(spec, base, archivo):
    """(ruta en este equipo, entrada del spec) del archivo objetivo con esa etiqueta
    (el nombre del archivo, o <repo>-<nombre> cuando el nombre se repite en el id)."""
    nombre = os.path.basename(archivo.replace('\\', '/')).lower()
    for a in spec['archivos']:
        ruta = absoluta(a['ruta'], base)
        if etiqueta(ruta, spec, base).lower() == nombre:
            return ruta, a
    return None, None


def items_crudos(ruta_spec):
    """{numero: lineas tal cual} de cada '### Item N' (para mostrarlos completos)."""
    texto = re.sub(r'<!--.*?-->', '', _leer_txt(ruta_spec) or '', flags=re.S)
    items, actual, en_items = {}, None, False
    for linea in texto.splitlines():
        m = re.match(r'^##\s+(.*?)\s*$', linea)
        if m:
            en_items = m.group(1).strip().lower().startswith('items')
            actual = None
            continue
        mi = re.match(r'^###\s+Item\s+(\S+)', linea) if en_items else None
        if mi:
            actual = mi.group(1)
            items[actual] = [linea]
        elif actual is not None:
            items[actual].append(linea)
    return items


def secciones(ruta_spec):
    """{titulo en minusculas: lineas} de las secciones '## ' del spec."""
    texto = re.sub(r'<!--.*?-->', '', _leer_txt(ruta_spec) or '', flags=re.S)
    salida, actual = {}, None
    for linea in texto.splitlines():
        m = re.match(r'^##\s+(.*?)\s*$', linea)
        if m:
            actual = m.group(1).strip().lower()
            salida[actual] = []
        elif actual is not None and linea.strip():
            salida[actual].append(linea)
    return salida


def _entradas_con(obj, simbolos, salida):
    """Las entradas mas pequenas de un JSON que mencionan algun simbolo."""
    if isinstance(obj, (dict, list)):
        hijos = obj.values() if isinstance(obj, dict) else obj
        encontrado = False
        for h in hijos:
            encontrado = _entradas_con(h, simbolos, salida) or encontrado
        if encontrado:
            return True
    texto = json.dumps(obj, ensure_ascii=False)
    if isinstance(obj, (dict, list)) and any(s in texto for s in simbolos):
        salida.append(texto if len(texto) <= 1200 else texto[:1200] + ' ...')
        return True
    return False


def parse_items(texto):
    return [n.strip() for n in re.split(r'[,\s]+', texto or '') if n.strip()]


def es_simbolo(palabra):
    """Si una palabra de 'simbolos:' es un nombre del codigo y no prosa del item
    ('hoy', 'cambia', 'servicios'): lleva guion bajo, mayuscula interior (camelCase),
    es un $variable o es una etiqueta en mayusculas (RETENCIONFUENTEMANIFIESTO)."""
    if palabra.startswith('$_') or palabra == '$this':
        return False
    return ('_' in palabra or palabra.startswith('$') or re.search(r'[a-z][A-Z]', palabra) is not None
            or (palabra.isupper() and len(palabra) >= 6))


def veredictos_impacto(datos, simbolos):
    """Lineas 'VEREDICTO simbolo: razon' de los targets del IMPACTO que tocan los
    simbolos, RIESGO y BLOQUEADO primero. Las entradas pequenas que imprime
    _entradas_con no traen el veredicto: esta es la parte que decide."""
    lineas = []
    for t in (datos or {}).get('targets', []) if isinstance(datos, dict) else []:
        if not isinstance(t, dict):
            continue
        # Solo por el nombre del target: casi todos los textos citan los simbolos comunes.
        nombre_t = str(t.get('symbol') or '')
        if not any(re.search(r'(?<![A-Za-z0-9_])%s(?![A-Za-z0-9_])' % re.escape(s), nombre_t) for s in simbolos):
            continue
        veredicto = t.get('verdict') or '-'
        razon = ' '.join(str(t.get('verdict_reason') or '').split())
        lineas.append((0 if veredicto in ('RIESGO', 'BLOQUEADO') else 1,
                       '%s %s: %s' % (veredicto, t.get('symbol') or '?',
                                      razon if len(razon) <= 600 else razon[:600] + ' ...')))
    return [l for _, l in sorted(lineas, key=lambda x: x[0])]


def cmd_contexto(base, archivo, numeros):
    """Lo que necesita una correccion puntual y nada mas. Reemplaza leer 'estado', el
    ID_SPEC entero, el ACTA entero y el IMPACTO entero en una corrida con 'items N'."""
    ctx = contexto(base)
    spec = ctx['spec']
    ruta_spec = os.path.join(ctx['trabajo'], 'ID_SPEC.md')
    if spec is None:
        print('FALTA: %s' % ruta_spec)
        return 3
    ruta, entrada = objetivo_por_nombre(spec, base, archivo)
    if not ruta:
        print('NO_EN_SPEC: %s no esta en Archivos objetivo del ID_SPEC' % archivo)
        return 3
    nombre = etiqueta(ruta, spec, base)
    todos = items_de(spec, nombre)
    filas = ctx['aplicados'].get(clave(ruta), [])
    estados = estado_items(ctx, filas, todos) or {}
    if not numeros:
        numeros = [n for n in todos if estados.get(n) in ('cambiado', 'pendiente')] or todos
    ajenos = [n for n in numeros if n not in todos]

    print('CONTEXTO DELTA  id %s (carpeta %s) - %s - items %s'
          % (spec.get('id') or '?', ctx['carpeta'], nombre, ','.join(numeros)))
    print('tipo %s | confirmar_antes_de_aplicar %s | ruta %s | preguntas abiertas %d'
          % (spec['tipo'] or '-', spec.get('confirmar_antes_de_aplicar') or '-',
             'confirmada' if spec['ruta_confirmada'] else 'SIN CONFIRMAR', spec['preguntas']))
    if ajenos:
        print('AVISO: items %s no son de %s en el ID_SPEC' % (','.join(ajenos), nombre))
    h = hechos_archivo(ruta)
    print('')
    print('ARCHIVO (hechos del disco ahora, linea base del paso 6):')
    print('  %s' % ruta)
    print('  en el spec: %s' % entrada['ruta'])
    if h is None:
        print('  [FALTA] el archivo no existe')
    else:
        print('  %d bytes, %d lineas, %s, salto final %s, %s, tab-inicial %d, espacios finales %d'
              % (h['bytes'], h['lineas'], h['eol'], 'si' if h['salto_final'] else 'no', h['codificacion'],
                 h['tab_inicial'], h['espacios_finales']))
    if estados:
        print('  estado de sus items: %s' % ', '.join('%s %s' % (n, estados[n]) for n in todos))

    secs = secciones(ruta_spec)
    crudos = items_crudos(ruta_spec)
    print('')
    print('ITEMS PEDIDOS (texto vigente del ID_SPEC):')
    simbolos = set()
    for n in numeros:
        for linea in crudos.get(n, ['### Item %s  (NO EXISTE en el ID_SPEC)' % n]):
            print('  ' + linea)
            m = re.match(r'^\s*simbolos:\s*(.*)$', linea)
            if m:
                # $_REQUEST, $_POST... aparecen en todo el IMPACTO: la clave entre corchetes si sirve.
                # Sin el '$': los JSON escriben la variable con y sin el.
                simbolos.update(w.lstrip('$') for w in re.findall(r'[A-Za-z_$][A-Za-z0-9_]{3,}', m.group(1))
                                if es_simbolo(w))
    for titulo in ('reglas globales', 'matriz de casos', 'cambios ajenos al id'):
        clave_sec = next((k for k in secs if k.startswith(titulo)), None)
        if clave_sec and secs[clave_sec]:
            print('')
            print(titulo.upper() + ':')
            for linea in secs[clave_sec]:
                print('  ' + linea)
    clave_dec = next((k for k in secs if k.startswith('decisiones')), None)
    if clave_dec:
        patron = re.compile(r'(?i)\bitems?\s*(%s)\b|%s' % ('|'.join(re.escape(n) for n in numeros),
                                                            re.escape(nombre)))
        decisiones = [l for l in secs[clave_dec] if patron.search(l)]
        ultimas = [l for l in secs[clave_dec][-3:] if l not in decisiones]
        if decisiones or ultimas:
            print('')
            print('DECISIONES DEL DESARROLLADOR (de estos items o este archivo, y las 3 ultimas) - obligatorias:')
            for linea in decisiones + ultimas:
                print('  ' + linea)

    acta = os.path.join(ctx['trabajo'], 'ACTA_%s.md' % nombre)
    texto_acta = _leer_txt(acta)
    if texto_acta:
        corridas = re.split(r'(?m)^(?=## Corrida)', texto_acta)
        corridas = [c_ for c_ in corridas if c_.startswith('## Corrida')]
        respuestas = []
        for c_ in corridas[:-1]:
            for linea in c_.splitlines():
                if re.match(r'^\s*preguntas y respuestas:', linea) and not re.search(r':\s*ninguna\s*$', linea, re.I):
                    respuestas.append('%s -> %s' % (c_.splitlines()[0][3:], linea.strip()))
        print('')
        print('ACTA_%s (%d corridas; se muestran las respuestas del desarrollador y la ultima corrida):'
              % (nombre, len(corridas)))
        for r in respuestas:
            print('  ' + r)
        if corridas:
            for linea in corridas[-1].rstrip().splitlines():
                print('  | ' + linea)

    if simbolos:
        for nombre_json in ('IMPACTO.json', 'MAP.json', 'SCOPE.json', 'EQUIVALENCIA_%s.json' % nombre):
            p = os.path.join(ctx['trabajo'], nombre_json)
            if not os.path.isfile(p):
                continue
            try:
                datos = json.loads(_leer_txt(p) or 'null')
            except ValueError:
                continue
            if nombre_json == 'IMPACTO.json':
                veredictos = veredictos_impacto(datos, sorted(simbolos))
                if veredictos:
                    print('')
                    print('IMPACTO.json - veredicto de los simbolos de estos items (RIESGO/BLOQUEADO primero):')
                    for v in veredictos:
                        print('  ' + v)
            salida = []
            _entradas_con(datos, sorted(simbolos), salida)
            if salida:
                print('')
                print('%s - entradas que mencionan %s:' % (nombre_json, ', '.join(sorted(simbolos))))
                for s in salida[:12]:
                    print('  ' + s)
                if len(salida) > 12:
                    print('  ... %d entradas mas (lee %s solo si las necesitas)' % (len(salida) - 12, nombre_json))
    print('')
    print('ALCANCE: trabaja SOLO los items %s. No verifiques los demas items del archivo.' % ','.join(numeros))
    print('Si todos quedan YA_APLICADO sin escribir: %s verificado %s %s --items %s'
          % (SCRIPT, ctx['carpeta'], nombre, ','.join(numeros)))
    return 0


def _append_registro(trabajo, fila):
    with open(os.path.join(trabajo, 'REGISTRO.jsonl'), 'a', encoding='utf-8') as fh:
        fh.write(json.dumps(fila, ensure_ascii=False) + '\n')


def _md5(ruta):
    try:
        with open(ruta, 'rb') as fh:
            return hashlib.md5(fh.read()).hexdigest()
    except (IOError, OSError):
        return None


def _como_numero(n):
    return int(n) if n.isdigit() else n


def cmd_verificado(base, archivo, numeros):
    """Una corrida que no escribio nada (items YA_APLICADO) tambien cuenta: sin esta
    fila el router los volveria a pedir cada vez."""
    ctx = contexto(base)
    spec = ctx['spec']
    if spec is None:
        print('FALTA: ID_SPEC.md')
        return 3
    ruta, _ = objetivo_por_nombre(spec, base, archivo)
    if not ruta:
        print('NO_EN_SPEC: %s no esta en Archivos objetivo del ID_SPEC' % archivo)
        return 3
    if not numeros:
        print('ERROR: verificado requiere --items N,M')
        return 4
    nombre = etiqueta(ruta, spec, base)
    ajenos = [n for n in numeros if n not in items_de(spec, nombre)]
    if ajenos:
        print('ERROR: items %s no son de %s en el ID_SPEC' % (','.join(ajenos), nombre))
        return 4
    huellas = huellas_items(os.path.join(ctx['trabajo'], 'ID_SPEC.md'), numeros)
    fila = {'fecha': datetime.datetime.now().isoformat(timespec='seconds'), 'tipo': 'verificado',
            'archivo': ruta, 'archivo_ref': simbolizar(ruta, base),
            'items': [_como_numero(n) for n in numeros], 'items_hash': huellas,
            'bloques': 0, 'md5_despues': _md5(ruta)}
    _append_registro(ctx['trabajo'], fila)
    print('VERIFICADO %s items %s (sin escritura) -> REGISTRO.jsonl' % (nombre, ','.join(numeros)))
    return 0


def cmd_sellar(base):
    """Paso unico para ids en curso: los items vigentes de cada archivo que el router
    ya da por aplicado quedan con huella. Desde ahi solo vuelve lo que cambie."""
    ctx = contexto(base)
    spec = ctx['spec']
    if spec is None:
        print('FALTA: ID_SPEC.md')
        return 3
    ruta_spec = os.path.join(ctx['trabajo'], 'ID_SPEC.md')
    spec_editado = datetime.datetime.fromtimestamp(os.path.getmtime(ruta_spec)).isoformat()
    sellados = 0
    for a in spec['archivos']:
        ruta = absoluta(a['ruta'], base)
        nombre = etiqueta(ruta, spec, base)
        items = items_de(spec, nombre)
        filas = ctx['aplicados'].get(clave(ruta), [])
        if not filas or not items:
            print('  %-34s sin escrituras o sin items: nada que sellar' % nombre)
            continue
        estados = estado_items(ctx, filas, items)
        if estados is not None:
            print('  %-34s ya tiene huellas: %s' % (nombre, ', '.join('%s %s' % (n, estados[n]) for n in items)))
            continue
        acta = os.path.join(ctx['trabajo'], 'ACTA_%s.md' % nombre)
        revisado = (os.path.isfile(acta) and
                    datetime.datetime.fromtimestamp(os.path.getmtime(acta)).isoformat() >= spec_editado)
        if spec_editado > max(f.get('fecha', '') for f in filas) and not revisado:
            print('  %-34s PENDIENTE: el spec cambio despues de su ultima corrida; /implementar primero' % nombre)
            continue
        fila = {'fecha': datetime.datetime.now().isoformat(timespec='seconds'), 'tipo': 'sello',
                'archivo': ruta, 'archivo_ref': simbolizar(ruta, base),
                'items': [_como_numero(n) for n in items],
                'items_hash': huellas_items(ruta_spec, items), 'bloques': 0, 'md5_despues': _md5(ruta)}
        _append_registro(ctx['trabajo'], fila)
        sellados += 1
        print('  %-34s SELLADO items %s' % (nombre, ','.join(items)))
    print('SELLO: %d archivo(s). Desde ahora /siguiente pide solo los items que cambien en el ID_SPEC.' % sellados)
    return 0


RE_LINEA_RUTA = re.compile(r'^(\s*(?:-\s*)?(?:ruta|raiz|fuente|carpeta):[ \t]*)(.+?)([ \t]*)$')
RE_LINEA_PAR = re.compile(r'^(\s*-\s*par:[ \t]*)(.+?)([ \t]*->[ \t]*)(.+?)([ \t]*)$')


def cmd_normalizar(base):
    """Pasa las rutas absolutas del ID_SPEC y del REGISTRO a nombres logicos, para
    que el id funcione en cualquier equipo. Deja respaldo de lo que cambia."""
    trabajo = os.path.join(base, TRABAJO)
    ruta_spec = os.path.join(trabajo, 'ID_SPEC.md')
    sello = datetime.datetime.now().strftime('%Y-%m-%d_%H%M')
    if not os.path.isfile(ruta_spec):
        print('FALTA: %s' % ruta_spec)
        return 3
    with open(ruta_spec, 'r', encoding='utf-8', newline='') as fh:
        lineas = fh.read().split('\n')
    cambios = []
    for i, linea in enumerate(lineas):
        fin = '\r' if linea.endswith('\r') else ''
        cuerpo = linea[:-1] if fin else linea
        m = RE_LINEA_PAR.match(cuerpo)
        if m:
            nuevo = m.group(1) + simbolizar(m.group(2), base) + m.group(3) + simbolizar(m.group(4), base) + m.group(5)
        else:
            m = RE_LINEA_RUTA.match(cuerpo)
            if not m:
                continue
            nuevo = m.group(1) + simbolizar(m.group(2), base) + m.group(3)
        if nuevo != cuerpo:
            cambios.append((cuerpo.strip(), nuevo.strip()))
            lineas[i] = nuevo + fin
    if cambios:
        shutil.copy2(ruta_spec, os.path.join(trabajo, 'ID_SPEC_anterior_%s_normalizar.md' % sello))
        original = os.stat(ruta_spec)
        with open(ruta_spec, 'w', encoding='utf-8', newline='') as fh:
            fh.write('\n'.join(lineas))
        # Cambiar la forma de escribir una ruta no cambia el spec: se conserva su
        # fecha, que el router compara con las escrituras de los ids sin huellas.
        os.utime(ruta_spec, (original.st_atime, original.st_mtime))
    print('ID_SPEC: %d ruta(s) pasadas a nombre logico' % len(cambios))
    for antes, despues in cambios:
        print('  - %s' % antes)
        print('  + %s' % despues)

    registro = os.path.join(trabajo, 'REGISTRO.jsonl')
    filas = cargar_registro(trabajo)
    agregadas = 0
    for f in filas:
        for campo in ('archivo', 'backup', 'lote', 'lote_copia'):
            ref = campo + '_ref'
            if f.get(campo) and not f.get(ref):
                simbolica = simbolizar(f[campo], base)
                if simbolica != f[campo]:
                    f[ref] = simbolica
                    agregadas += 1
    if agregadas:
        shutil.copyfile(registro, registro + '.antes_normalizar_' + sello)
        with open(registro, 'w', encoding='utf-8') as fh:
            for f in filas:
                fh.write(json.dumps(f, ensure_ascii=False) + '\n')
    print('REGISTRO: %d referencia(s) logicas agregadas (las rutas originales se conservan)' % agregadas)
    return 0


def main():
    args = sys.argv[1:]
    acciones = ('raices', 'configurar', 'ruta', 'estado', 'siguiente', 'init', 'items',
                'contexto', 'verificado', 'sellar', 'normalizar')
    if not args or args[0] not in acciones:
        print(__doc__)
        return 4
    accion = args[0]
    carpeta = args[1].strip().strip('"') if len(args) > 1 else ''
    if accion == 'raices':
        return cmd_raices()
    if accion == 'configurar':
        return cmd_configurar(args[1:])
    if accion == 'siguiente' and not carpeta:
        return cmd_resumen()
    if not carpeta:
        print('ERROR: %s requiere <carpeta>' % accion)
        return 4
    if accion == 'init':
        return cmd_init(carpeta, args[2].strip() if len(args) > 2 else '')
    base = resolver(carpeta)
    if accion == 'ruta':
        print(base)
        return 0
    if accion == 'estado':
        return cmd_estado(base)
    if accion == 'items':
        return cmd_items(base)
    if accion == 'sellar':
        return cmd_sellar(base)
    if accion == 'normalizar':
        return cmd_normalizar(base)
    if accion in ('contexto', 'verificado'):
        resto = args[2:]
        archivo = resto[0].strip().strip('"') if resto and not resto[0].startswith('--') else ''
        numeros = []
        for i, a in enumerate(resto):
            if a == '--items' and i + 1 < len(resto):
                numeros = parse_items(resto[i + 1])
            elif a.startswith('--items='):
                numeros = parse_items(a.split('=', 1)[1])
            elif a.lower() == 'items' and i + 1 < len(resto):
                numeros = parse_items(resto[i + 1])
        if not archivo:
            print('ERROR: %s requiere <carpeta> <archivo> [--items N,M]' % accion)
            return 4
        if accion == 'contexto':
            return cmd_contexto(base, archivo, numeros)
        return cmd_verificado(base, archivo, numeros)
    return cmd_siguiente(base)


if __name__ == '__main__':
    sys.exit(main())
