# -*- coding: utf-8 -*-
"""Ejecuta con PHP (5.4 si esta en el PATH) un plan de prueba sobre un archivo PHP del id,
sin servidor ni base de datos, y reporta el resultado de cada paso.

Uso:
  python probar_php.py <plan.json> [--caso <nombre>] [--php <ruta php.exe>]

El plan (JSON, UTF-8) lo escribe quien revisa, normalmente en <ID_DIR>/pruebas/PRUEBA_<archivo>.json:
{
  "archivo": "{repo:consultor}\\modules\\concil\\class_x.php",   # ruta logica o absoluta
  "directorio": "{repo:consultor}\\modules\\concil",            # opcional: chdir antes del include (por defecto, la carpeta del archivo)
  "constantes": {"DIR_APLICA_CENTRAL": "consultor", "CONS": "c_x", "OTRA": "sate_x", "EMPRESA": "900497857"},
  "sesion": {"datos_usuario": {"cod_usuari": "prueba", "cod_perfil": "1"}},
  "mock": [                                                    # opcional: reemplaza la clase Consulta (sin BD)
    {"contiene": ["tab_x_parame"], "filas": [{"ind_mandan": "R"}]},
    {"contiene": ["tab_manifi_cargax"], "por": "cod_manifi = '([^']+)'",
     "filas_por": {"MN1": [{"cod_manifi": "MN1"}]}}
  ],
  "pasos": [
    {"nuevo": "ClaseX", "args": [null], "guardar": "obj"},
    {"llamar": "$obj->LeerArchivo", "args": ["{nombre}", "{ruta}", "$errores"], "guardar": "filas",
     "imprimir": ["$errores", "contar:$filas"]},
    {"llamar": "$obj->Conciliar", "args": ["$filas", "2026", "09"], "guardar": "res",
     "imprimir": ["agrupar:est_concil:$res.detalle", "$res.resumen"]}
  ],
  "casos": [{"nombre": "01", "vars": {"nombre": "a.xls", "ruta": "D:/.../a.xls"}, "mock": []}]
}

Argumentos de un paso: un texto "$nombre" es la variable guardada (se pasa por referencia si el
metodo la recibe por referencia; nace como array vacio); "$a.b" entra en un campo. "{var}" se
reemplaza con las vars del caso. Lo demas va literal (null, numeros, textos, listas, objetos).
Un paso con "solo_si": "$v" se ejecuta solo si esa variable no esta vacia (ej. Conciliar solo si
ValidarArchivo devolvio TRUE). Una regla del mock con "variable": "$res.detalle" devuelve esas filas
(lo que el codigo grabo en un paso anterior y relee de la BD en otro).
imprimir: "$v" (JSON, recortado), "contar:$v", "agrupar:<campo>:$v" (conteo por valor de un campo
en una lista de filas), "sumar:<campo>:$v", "fila:<n>:$v", "columnas:<c1,c2>:$v" (una linea por fila).
Con mock se listan al final las sentencias de escritura (INSERT/UPDATE/DELETE) y las consultas que
ninguna regla del mock atendio (devolvieron 0 filas): ahi suele estar el dato que falta simular.
Codigo de salida: 0 si PHP termino sin error fatal; 1 si hubo fatal o error de plan.
"""
import json
import os
import re
import subprocess
import sys
import tempfile

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(AQUI, '..', 'id-workspace'))
try:
    import id_workspace
except Exception:  # sin el router se aceptan solo rutas absolutas
    id_workspace = None


def ruta_real(ruta):
    if ruta and ruta.startswith('{') and id_workspace:
        r, error = id_workspace.expandir(ruta)
        if error:
            sys.exit('ruta %s: %s' % (ruta, error))
        return r
    return ruta


def lit(v):
    """Valor JSON -> literal PHP."""
    if v is None:
        return 'NULL'
    if v is True:
        return 'TRUE'
    if v is False:
        return 'FALSE'
    if isinstance(v, (int, float)):
        return repr(v)
    if isinstance(v, str):
        return "'" + v.replace('\\', '\\\\').replace("'", "\\'") + "'"
    if isinstance(v, list):
        return 'array(' + ', '.join(lit(x) for x in v) + ')'
    if isinstance(v, dict):
        return 'array(' + ', '.join('%s => %s' % (lit(k), lit(x)) for k, x in v.items()) + ')'
    raise ValueError('valor no soportado: %r' % (v,))


def var(expr):
    """"$a.b.c" -> $V['a']['b']['c']"""
    partes = expr[1:].split('.')
    return '$V' + ''.join('[%s]' % lit(p) for p in partes)


def sustituir(v, vars_caso):
    if isinstance(v, str):
        for k, x in vars_caso.items():
            v = v.replace('{%s}' % k, str(x))
        return v
    if isinstance(v, list):
        return [sustituir(x, vars_caso) for x in v]
    if isinstance(v, dict):
        return dict((k, sustituir(x, vars_caso)) for k, x in v.items())
    return v


def arg(v):
    if isinstance(v, str) and re.match(r'^\$[A-Za-z_][\w.]*$', v):
        return var(v)
    return lit(v)


MOCK_PHP = r'''
class Consulta {
  var $f = array(); var $p = 0;
  function Consulta( $q, $c = NULL, $t = 'N' ) {
    $q1 = preg_replace( '/\s+/', ' ', $q );
    if ( preg_match( '/^\s*(INSERT|UPDATE|DELETE|REPLACE)/i', $q1 ) ) { $GLOBALS['__ESCRITURAS'][] = substr( $q1, 0, 220 ); return; }
    foreach ( $GLOBALS['__MOCK'] as $r ) {
      $ok = TRUE;
      foreach ( $r['contiene'] as $s ) { if ( strpos( $q1, $s ) === FALSE ) { $ok = FALSE; } }
      if ( isset( $r['no_contiene'] ) ) { foreach ( $r['no_contiene'] as $s ) { if ( strpos( $q1, $s ) !== FALSE ) { $ok = FALSE; } } }
      if ( !$ok ) { continue; }
      if ( isset( $r['variable'] ) ) { $this -> f = __ruta( $r['variable'] ); return; }
      if ( isset( $r['por'] ) ) {
        $this -> f = ( preg_match( '/'.$r['por'].'/', $q1, $m ) && isset( $r['filas_por'][$m[1]] ) ) ? $r['filas_por'][$m[1]] : array();
      } else { $this -> f = $r['filas']; }
      return;
    }
    $GLOBALS['__SIN_MOCK'][] = substr( $q1, 0, 220 );
  }
  function __fila( $fila, $m ) {
    if ( $m == 'a' ) { return $fila; }
    if ( $m == 'i' ) { return array_values( $fila ); }
    return array_merge( $fila, array_values( $fila ) );
  }
  function ret_matriz( $m = 'b' ) { $o = array(); foreach ( $this -> f as $x ) { $o[] = $this -> __fila( $x, $m ); } return $o; }
  function ret_matriz2() { return $this -> ret_matriz( 'b' ); }
  function ret_arreglo( $m = 'b' ) { if ( !isset( $this -> f[$this -> p] ) ) { return FALSE; } return $this -> __fila( $this -> f[$this -> p++], $m ); }
  function ret_vector() { return $this -> ret_arreglo( 'i' ); }
  function ret_num_rows() { return sizeof( $this -> f ); }
  function ret_resultado() { return TRUE; }
}
'''

AYUDA_PHP = r'''
function __ruta( $p ) { $v = $GLOBALS['V']; foreach ( explode( '.', substr( $p, 1 ) ) as $k ) { if ( !isset( $v[$k] ) ) { return array(); } $v = $v[$k]; } return is_array( $v ) ? $v : array(); }
function __u( $v ) { if ( is_array( $v ) ) { $o = array(); foreach ( $v as $k => $x ) { $o[$k] = __u( $x ); } return $o; } return is_string( $v ) ? utf8_encode( $v ) : $v; }
function __j( $v ) { $s = json_encode( __u( $v ), JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES ); return strlen( $s ) > 3000 ? substr( $s, 0, 3000 ).'...(recortado, '.strlen( $s ).' bytes)' : $s; }
function __imp( $et, $v ) { echo '    '.$et.' = '.__j( $v )."\n"; }
'''


def imprimir(expr):
    m = re.match(r'^(contar|agrupar|sumar|fila|columnas)(?::([^:$]+))?:(\$[\w.]+)$', expr)
    if not m:
        if not re.match(r'^\$[\w.]+$', expr):
            raise ValueError('imprimir no reconocido: %s' % expr)
        return '__imp(%s, isset(%s) ? %s : NULL);' % (lit(expr), var(expr), var(expr))
    op, p, v = m.group(1), m.group(2), var(m.group(3))
    et = lit(expr)
    if op == 'contar':
        return '__imp(%s, is_array(%s) ? sizeof(%s) : 0);' % (et, v, v)
    if op == 'agrupar':
        return ('$__g = array(); foreach ((array)%s as $__x) { $__k = isset($__x[%s]) ? (string)$__x[%s] : "(vacio)"; '
                '$__g[$__k] = (isset($__g[$__k]) ? $__g[$__k] : 0) + 1; } ksort($__g); __imp(%s, $__g);'
                % (v, lit(p), lit(p), et))
    if op == 'sumar':
        return ('$__s = 0; foreach ((array)%s as $__x) { $__s += isset($__x[%s]) ? $__x[%s] : 0; } __imp(%s, round($__s, 2));'
                % (v, lit(p), lit(p), et))
    if op == 'fila':
        return '__imp(%s, isset(%s[%d]) ? %s[%d] : NULL);' % (et, v, int(p), v, int(p))
    cols = [c.strip() for c in p.split(',')]
    return ('echo "    " . %s . "\\n"; foreach ((array)%s as $__x) { $__o = array(); foreach (%s as $__c) '
            '{ $__o[] = isset($__x[$__c]) ? $__x[$__c] : "-"; } echo "      " . utf8_encode(implode(" | ", $__o)) . "\\n"; }'
            % (et, v, lit(cols)))


def generar(plan, caso):
    vars_caso = caso.get('vars', {})
    archivo = ruta_real(sustituir(plan['archivo'], vars_caso))
    directorio = ruta_real(plan.get('directorio')) or os.path.dirname(archivo)
    php = ['<?php', 'error_reporting(E_ALL & ~E_NOTICE & ~E_STRICT & ~E_DEPRECATED);', 'ini_set("display_errors", "1");',
           '$V = array(); $GLOBALS["__ESCRITURAS"] = array(); $GLOBALS["__SIN_MOCK"] = array();']
    for k, v in plan.get('constantes', {}).items():
        php.append('define(%s, %s);' % (lit(k), lit(v)))
    for k, v in plan.get('sesion', {}).items():
        php.append('$_SESSION[%s] = %s;' % (lit(k), lit(v)))
    mock = caso.get('mock', []) + plan.get('mock', [])
    if mock or 'mock' in plan:
        php.append('$GLOBALS["__MOCK"] = %s;' % lit(sustituir(mock, vars_caso)))
        php.append(MOCK_PHP)
    php.append(AYUDA_PHP)
    php.append('chdir(%s);' % lit(directorio.replace('\\', '/')))
    php.append('include_once(%s);' % lit(archivo.replace('\\', '/')))
    for n, paso in enumerate(plan['pasos'], 1):
        paso = sustituir(paso, vars_caso)
        args = ', '.join(arg(a) for a in paso.get('args', []))
        for a in paso.get('args', []):
            if isinstance(a, str) and re.match(r'^\$[A-Za-z_]\w*$', a):
                php.append('if (!isset(%s)) { %s = array(); }' % (var(a), var(a)))
        if 'nuevo' in paso:
            llamada, texto = 'new %s(%s)' % (paso['nuevo'], args), 'new %s' % paso['nuevo']
        else:
            destino = paso['llamar']
            if '->' in destino:
                obj, met = destino.split('->', 1)
                llamada = '%s->%s(%s)' % (var(obj), met, args)
            else:
                llamada = '%s(%s)' % (destino, args)
            texto = destino
        cuerpo = ['echo "PASO %d %s\\n";' % (n, texto.replace('$', '\\$')),
                  ('%s = %s;' % (var('$' + paso['guardar']), llamada)) if paso.get('guardar') else '%s;' % llamada]
        cuerpo += [imprimir(e) for e in paso.get('imprimir', [])]
        if paso.get('solo_si'):
            php.append('if (!empty(%s)) { %s } else { echo "PASO %d %s: omitido (%s vacio)\\n"; }'
                       % (var(paso['solo_si']), ' '.join(cuerpo), n, texto.replace('$', '\\$'),
                          paso['solo_si'].replace('$', '\\$')))
        else:
            php.extend(cuerpo)
    if mock or 'mock' in plan:
        php.append('echo "ESCRITURAS (" . sizeof($GLOBALS["__ESCRITURAS"]) . ")\\n"; foreach ($GLOBALS["__ESCRITURAS"] as $__q) { echo "    " . utf8_encode($__q) . "\\n"; }')
        php.append('$__u = array_unique($GLOBALS["__SIN_MOCK"]); echo "CONSULTAS SIN REGLA EN EL MOCK (" . sizeof($__u) . ")\\n"; foreach ($__u as $__q) { echo "    " . utf8_encode($__q) . "\\n"; }')
    php.append('echo "FIN OK\\n";')
    return '\r\n'.join(php) + '\r\n'


def main():
    args = sys.argv[1:]
    if not args or args[0] in ('-h', '--help'):
        print(__doc__)
        return 0
    ruta_plan = args[0]
    solo = args[args.index('--caso') + 1] if '--caso' in args else None
    php_exe = args[args.index('--php') + 1] if '--php' in args else 'php'
    with open(ruta_plan, encoding='utf-8') as f:
        plan = json.load(f)
    casos = plan.get('casos') or [{'nombre': 'unico'}]
    tmp = os.path.join(AQUI, '..', '..', 'tmp')
    os.makedirs(tmp, exist_ok=True)
    fallos = 0
    for caso in casos:
        if solo and caso.get('nombre') != solo:
            continue
        try:
            codigo = generar(plan, caso)
        except (ValueError, KeyError) as e:
            print('ERROR DE PLAN en el caso %s: %s' % (caso.get('nombre'), e))
            return 1
        fd, ruta_php = tempfile.mkstemp(suffix='.php', prefix='prueba_', dir=tmp)
        with os.fdopen(fd, 'wb') as f:
            f.write(codigo.encode('latin-1', errors='replace'))
        print('=== CASO %s' % caso.get('nombre', ''))
        try:
            r = subprocess.run([php_exe, '-d', 'date.timezone=America/Bogota', ruta_php],
                               capture_output=True, timeout=300)
        except FileNotFoundError:
            print('php no esta en el PATH: instala PHP 5.4 (ver FLUJO.md seccion 5) o pasa --php <ruta>')
            return 1
        salida = (r.stdout + r.stderr).decode('utf-8', errors='replace')
        print(salida.rstrip())
        if 'FIN OK' not in salida:
            fallos += 1
            print('!!! el caso no llego al final: error fatal o exit() del codigo probado (ver arriba)')
        os.remove(ruta_php)
    return 1 if fallos else 0


if __name__ == '__main__':
    sys.exit(main())
