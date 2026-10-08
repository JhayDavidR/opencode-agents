# ID_SPEC

id: <completar: numero del id>
titulo: <completar: nombre corto de la funcionalidad>
tipo: <completar: nuevo | porte | migracion>
modulo: <completar: carpeta del modulo en sate_standa, ej. manifi, liquid, factur>
autor: <completar: nombre como debe salir en el manual tecnico>
confirmar_antes_de_aplicar: no

<!--
id: es el numero que llevan los comentarios "ID <id>:" en el codigo. La carpeta del id
puede llamarse distinto (ej. 566647_v2): esa carpeta es el argumento de los comandos.
tipo:
  nuevo     -> funcionalidad que no existe en ningun lado.
  porte     -> la funcionalidad YA existe en otro modulo/archivo (seccion Referencia) y se
               adapta a otro con logica propia. Flujo: /equivalencia -> items -> /implementar.
  migracion -> los cambios del id existen en una copia vieja del MISMO archivo. Flujo: /migrar.
confirmar_antes_de_aplicar:
  no -> el implementador aplica solo si todos los items son SEGURO y la simulacion es limpia.
  si -> siempre muestra el resumen y espera tu OK antes de escribir.
Cualquier item con veredicto RIESGO o BLOQUEADO se detiene igual, sin importar este valor.
Despues de llenarlo: /siguiente <carpeta> dice que comando va.
-->

## Ruta de desarrollo

<!-- La confirma el analista contigo al inicio (skill ruta-desarrollo). Mientras no diga
     "confirmada: si", /implementar, /migrar y /equivalencia no arrancan. -->
confirmada: no
carpeta: {id}
base: <completar: repo y rama del id, ej. sate_standa rama REQ_<id> desde master commit ...; copias en {id} si las hay>
tipo: <completar: nuevo | porte | migracion - razon>
alcance de esta entrega: <completar: requisitos incluidos; fuera: los que quedan para otra entrega>
archivos objetivo: <completar: en orden de implementacion>
recorrido: <completar: pequeno | grande -> comandos en orden>
base de datos: <completar: DDL, quien lo aplica, aplicado si/no | sin cambios de esquema>

## Archivos objetivo

<!-- Rutas con NOMBRE LOGICO, nunca con la unidad de un equipo (el id se trabaja en varios equipos):
       {repo:sate_standa}\modulo\archivo.php   archivo del repo, en la rama del id (el caso normal)
       {id}\subcarpeta\archivo.php             copia en la carpeta del id (fuera de todo repo)
     Cada equipo las resuelve con 'id_workspace.py configurar'. apply_blocks solo escribe estos archivos.
     fuente: solo en tipo migracion (la copia vieja, SRC, de solo lectura, en {id}). Borrala en los demas tipos.
     nuevo: si -> el archivo no existe y lo crea el id (apply_blocks lo crea con un bloque de search vacio;
     su carpeta debe existir). Borrala si el archivo ya existe. -->
- ruta: {repo:sate_standa}\<completar: modulo\archivo>
  rol: <completar: frontend | ruta AJAX | logica de negocio | vista | informe>
  fuente: <completar solo en migracion: {id}\ruta de la copia vieja; borrar esta linea si no aplica>

## Alcance de impacto

<!-- Donde buscar quien lee los simbolos que se tocan. Se lee, nunca se escribe.
     Una linea raiz por carpeta. Para buscar en TODO el repo usa "- raiz: {repo:sate_standa}":
     los agentes lo recorren con symbol_readers.py --prefilter (solo abren los archivos que
     contienen algun simbolo). -->
- raiz: {repo:sate_standa}\<completar: modulo>
- extensiones: .php .js

## Referencia

<!-- Solo para tipo: porte. Borra la seccion en los demas casos. -->
<!-- par: archivo de referencia (ya implementado, solo lectura) -> archivo objetivo -->
- par: <completar: ruta referencia> -> <completar: ruta objetivo>
- marcador: ID <completar: id>
- documentacion: <completar: rutas de manuales del id en la referencia, o borrar>

## Reglas globales

<!-- Reglas que aplican a TODOS los items, en palabras del dominio. Borra la linea si no hay. -->
- <completar o borrar>

## Matriz de casos

<!-- Solo si el id decide algo por una combinacion de condiciones (regimen del tercero y de la
     empresa, parametro general y marca del registro, obligacion, tipo de vinculacion, perfil).
     Una linea por combinacion; las que el requerimiento no cambia dicen "como hoy". Cada item
     que toca esa logica la cumple en SU archivo (linea casos: del item) y la prueba la recorre
     entera. Borra la seccion si el id no condiciona nada. -->
- (a) <completar: condicion> -> <completar: resultado esperado>
- (b) <completar: condicion> -> como hoy

## Cambios ajenos al id

<!-- Solo si en los mismos archivos viajan cambios que NO son de este id (una correccion,
     otro desarrollo). Los agentes no les ponen el marcador del id y el manual los lista en
     "Correcciones incluidas ajenas al ID". Una linea por grupo de cambios, con sus simbolos.
     Borra la seccion si no hay. -->

## Decisiones del desarrollador

<!-- Una linea por respuesta tuya (preguntas del analista o /spec ... respuestas:):
     - AAAA-MM-DD <pregunta> -> <respuesta literal> -->

## Trazabilidad del requerimiento

<!-- Una linea por cada R de REQUERIMIENTO_<carpeta>.md: R<n> -> item N | pregunta N |
     fuera de esta entrega: razon | no aplica: razon. Borra la seccion si el id no tiene R. -->

## Preguntas abiertas

<!-- Solo lo que no pudiste responder cuando el analista pregunto. Mientras tenga algo,
     /implementar y /migrar no arrancan. -->

## Items

### Item 1
archivo: <completar: nombre del archivo, debe estar en Archivos objetivo>
ubicacion: <completar: funcion, metodo, case o seccion>
objetivo: <completar: que debe pasar, observable por el usuario>
simbolos: <completar: variables, campos, funciones, columnas que se tocan o se leen>
referencia: <solo porte: bloque de EQUIVALENCIA.json (R1, R2...) o archivo:funcion de la referencia; borrar si no aplica>
adaptacion: <solo porte: que cambia respecto a la referencia por la logica propia del objetivo; borrar si no aplica>
casos: <completar: letras de la Matriz de casos que este archivo debe cumplir, ej. a, b, d; borrar si no hay matriz>
reutiliza: <completar: variable, funcion, consulta o rama existente en ESTE archivo que el item usa o extiende (archivo:linea), o "nada (buscado: <que> en <archivo>)">
criterios_aceptacion:
- <completar: resultado verificable en ESTE archivo; nunca "igual que el item N">
no_tocar:
- <completar: comportamiento o codigo que debe seguir igual>
pruebas_negativas:
- <completar: escenario que hoy funciona y debe seguir funcionando>
