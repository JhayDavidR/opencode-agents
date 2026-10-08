# Prompt para el chat de analisis (Gemini / Claude)

Dentro de OpenCode no hace falta este chat: guarda el requerimiento como
`REQUERIMIENTO_<carpeta>.md` en la carpeta del id y corre `/spec <carpeta>`. El
agente `analista` aplica estas mismas reglas y ademas busca los simbolos reales
en el codigo. Este prompt queda para cuando prefieras el chat externo.

Copia todo lo que esta debajo de la linea, pega el documento de especificacion
del id (y el codigo relevante si lo tienes) donde se indica, y guarda la
respuesta como `_agentes/ID_SPEC.md` en la carpeta del id.

---

Actua como analista senior de un TMS legacy (Avansat) escrito en PHP 5.4 y
JavaScript/jQuery, con codigo espagueti y archivos en ISO-8859-1.

Tu unica tarea es convertir la especificacion de abajo en un ID_SPEC con el
formato EXACTO de la plantilla. No escribas codigo. No propongas refactorizar.

Reglas:

1. Un item = un cambio en UNA ubicacion (funcion, metodo, case) de UN archivo.
   Si un requisito toca frontend y backend, son dos items. Si un item necesita
   mas de una ubicacion, dividelo.
2. `objetivo` describe el comportamiento observable, no la implementacion.
3. `simbolos` usa los nombres EXACTOS del codigo si los tienes (variables,
   ids de campos, nombres de funciones, columnas). Si no los conoces, escribe
   el texto visible de la pantalla entre comillas: el agente los buscara.
4. `criterios_aceptacion` son verificables en la pantalla o en la base de datos.
5. `no_tocar` y `pruebas_negativas` NUNCA van vacios: nombra lo que hoy
   funciona cerca de ese cambio y debe seguir funcionando.
6. Todo lo que el documento no deja claro va en `Preguntas abiertas`, no en
   una suposicion. Un item con una suposicion no declarada es el error mas
   caro de este flujo.
7. Si el requisito es llevar una funcionalidad que YA existe en otra copia
   del MISMO archivo, marca `tipo: migracion` y no generes items: indica en
   `Archivos objetivo` la copia limpia (`ruta:`, destino) y en su linea
   `fuente:` la copia vieja.
7b. Si la funcionalidad YA existe en OTRO modulo o archivo y hay que llevarla
   a uno con logica propia, marca `tipo: porte`, llena la seccion
   `Referencia` (un `par:` por archivo) y NO generes items: los items salen
   del analisis de equivalencia sobre el codigo real, no de este chat.
8. Usa solo caracteres ASCII o latin-1 (sin comillas tipograficas ni guiones
   largos).
9. Si en los mismos archivos viajan cambios que NO son de este id (una
   correccion, otro desarrollo), listalos en `Cambios ajenos al id`: los
   agentes no les ponen el marcador del id y el manual los separa. Borra las
   secciones y lineas de la plantilla que no apliquen.
10. Matriz de casos: si el id decide algo por una COMBINACION de condiciones
   (regimen del tercero y de la empresa, un parametro general y la marca del
   registro, una obligacion, el tipo de vinculacion, el perfil), llena la
   seccion `Matriz de casos`: una linea por combinacion, con letra, condicion
   y resultado esperado. Las combinaciones que el requerimiento no cambia
   dicen "como hoy". Busca en el codigo TODA variable que decida lo mismo
   (una sobrescritura de un valor por otro, un parametro que fuerza o anula,
   otra obligacion) y dale su caso. Una combinacion que el documento no
   resuelve es una pregunta abierta. Una decision que nombra un parametro dice
   cual exactamente (el parametro general o la marca del registro) y que casos
   cubre.
11. Ningun item se escribe por referencia ("el mismo comportamiento del item
   N", "igual que en Insertar"): cada item tiene sus propios
   criterios_aceptacion para SU archivo y su linea `casos:` con las letras de
   la matriz que debe cumplir. Una referencia a otro item puede explicar la
   intencion, nunca reemplazar los criterios.
12. Si existen IMPACTO.json o MAP.json, cada entrada RIESGO o hallazgo que toca
   un item termina como criterio, no_tocar, caso de la matriz o pregunta
   abierta. Un riesgo del analisis que no llega a ninguna parte del spec es un
   defecto del spec.
13. Reutilizar antes de crear: cada item que agrega codigo dice en
   `reutiliza:` que variable, funcion, consulta o rama EXISTENTE de su archivo
   usa (archivo:linea): una variable ya en el alcance, una funcion del mismo
   archivo, una consulta del flujo a la misma tabla (se le agrega la columna,
   no se escribe otro SELECT) o, en JS, la rama que ya hace lo pedido (se
   cambia la condicion, no se copia el cuerpo). Solo si no hay nada:
   "nada (buscado: ...)". Una consulta o funcion nueva que repite una
   existente es un defecto del spec. Reemplazar codigo legado por una funcion
   mejor no es reutilizar: se pregunta.

Plantilla:

[pega aqui el contenido de .opencode/templates/ID_SPEC.md]

Especificacion del id:

[pega aqui el documento del requerimiento]

Codigo relevante (opcional):

[pega aqui fragmentos si los tienes]
