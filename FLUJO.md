# Flujo de trabajo con agentes (OpenCode)

Abrir OpenCode SIEMPRE desde la carpeta que contiene `.opencode`
(ej. `D:\PhpStormGrupoOet`; en otro equipo, la suya: ninguna ruta del flujo depende de eso).
Desde dentro de `sate_standa` (repo git) esta configuracion no se carga, y desde la
carpeta de un id los scripts `.opencode/skills/...` no se encuentran.
Despues de editar algo en `.opencode`, cierra y vuelve a abrir OpenCode: la
configuracion se lee al arrancar.

## 0. Punto de entrada: `/siguiente`

    /siguiente <carpeta>     que toca con ese id y el comando exacto
    /siguiente               resumen de todos los ids

No hace falta recordar las tablas de abajo: el router (`id_workspace.py siguiente`)
lee la carpeta del id (documentos, REQUERIMIENTO, ID_SPEC, `_agentes`, REGISTRO.jsonl,
manual) y dice el paso siguiente. Sesion nueva (`/new`) antes de `/implementar`,
`/equivalencia` y `/migrar` (necesitan el contexto limpio); `/leer`, `/spec`,
`/siguiente`, `/documentar` y `/reporte` pueden ir en la misma sesion. Nada se pierde
entre sesiones: todo lo que un agente decide queda en la carpeta del id.
Desde la terminal da lo mismo, sin gastar tokens:

    python .opencode/skills/id-workspace/id_workspace.py siguiente <carpeta>

## 0b. Una vez por equipo: registrar tus carpetas

Ninguna ruta viene escrita en los agentes, en los scripts ni en el ID_SPEC. Cada equipo
le dice al script, UNA vez, donde estan sus carpetas (se guarda en tu perfil de usuario,
`%USERPROFILE%\.opencode_oet_rutas.json`, fuera de `.opencode`: copiar `.opencode` o la
carpeta de un id a otro equipo no arrastra rutas ajenas). Los repos se registran con un
NOMBRE LOGICO: si en otro equipo el repo se llama distinto (ej. `tms`), se registra igual
como `sate_standa`.

    python .opencode/skills/id-workspace/id_workspace.py configurar --ids "<carpeta que agrupa tus ids>" --repo sate_standa="<carpeta del repo>" --repo ws_rndc="<carpeta del repo>"
    python .opencode/skills/id-workspace/id_workspace.py raices

Un repo nuevo (o la carpeta de un cliente) se agrega cuando un id lo necesite:
`configurar --repo <nombre>="<carpeta>"`. `raices` muestra cada repo con su rama actual.
Opcional, si trabajas en dos equipos y quieres una sola bitacora: `configurar --logs "<carpeta>"`.

En el ID_SPEC las rutas se escriben con ese nombre y cada equipo las resuelve:

    - ruta: {repo:sate_standa}\manifi\ajax.php      archivo del repo (el caso normal)
    - ruta: {id}\manifi\archivo_viejo.php           copia en la carpeta del id

Un spec viejo con rutas `D:\...` se convierte con
`id_workspace.py normalizar <carpeta>` (deja respaldo; ya se hizo con 548866 y 548866_v2).

## 1. Preparar el id: carpeta y rama

La carpeta del id guarda los documentos (requerimiento, evidencias) y `_agentes`. El codigo
se trabaja EN EL REPO, en una rama del id. Copias en la carpeta del id solo para lo que no
vive en un repo (la carpeta de un cliente) o la copia vieja de una migracion.

1. Tu, en el repo (git lo ejecutas SOLO tu): actualiza la base y crea la rama del id.

       git checkout master
       git pull
       git checkout -b REQ_580000

   apply_blocks no escribe mientras el repo este en master/main (`RAMA_BASE`), y
   `/siguiente` te lo recuerda.
2. Crea la carpeta del id con el explorador y pasa su ruta completa:

       python .opencode/skills/id-workspace/id_workspace.py init "D:\...\ids\08_Agosto\580000"

   Crea solo `_agentes\ID_SPEC.md` dentro de ESA carpeta, con rutas logicas. El script
   nunca elige la carpeta por ti: sin ruta completa (o sin `NN_Mes` para un nombre nuevo)
   no crea nada. El documento del requerimiento puede quedarse donde esta: se lo pasas a
   `/leer` con su ruta.

En los comandos puedes usar el nombre de la carpeta (si esta bajo `ids\<mes>\`) o su
ruta completa entre comillas (si esta en cualquier otro lugar).
Los ids que empezaron con copias (548866, 548866_v2) siguen asi hasta cerrar: el flujo
acepta los dos modos segun lo que diga `Archivos objetivo`.

## 2. Del documento al ID_SPEC

1. `/leer <carpeta> "<ruta del PDF o Word>"` (opcional: solo si hay documento). El agente
   `lector` (modelo fijo glm-5.3-flash, el unico de Z.AI que ve imagenes) extrae el texto con
   `leer_requerimiento.py`, mira cada mockup y escribe `REQUERIMIENTO_<carpeta>.md`: requisitos
   R1..Rn con cita literal y referencia (F1.p2.L5), pantallas, parametros y dudas. Si en la
   carpeta hay varios documentos (pruebas, guiones, evidencias) te pregunta cual es el vigente.
2. `/spec <carpeta>`: el `analista`
   - te propone la **ruta de desarrollo** (carpeta y base de las copias, tipo, alcance de esta
     entrega, archivos en orden, recorrido, cambios de BD) y te la confirma con preguntas;
   - busca los simbolos reales en el codigo;
   - te pregunta, con opciones y su recomendacion, todo lo que el requerimiento no dice;
   - escribe el ID_SPEC con cada respuesta en su lugar, la seccion `Decisiones del
     desarrollador` y la `Trazabilidad del requerimiento` (cada R -> item, pregunta o fuera de
     esta entrega).
   Lo que no sepas responder queda en `Preguntas abiertas` y bloquea /implementar hasta que
   lo respondas (`/spec <carpeta>` otra vez, o `/spec <carpeta> respuestas: 1) ...`).
   Cambio menor sin documento: `/spec <carpeta> cambio: <descripcion>` (el texto queda como
   REQUERIMIENTO). Alternativa sin agente: el chat externo con
   `.opencode/templates/PROMPT_ANALISIS.md`.

**Matriz de casos.** Si el id decide algo por una combinacion de condiciones (regimen del
tercero y de la empresa, un parametro general y la marca del registro, una obligacion), el
analista escribe la seccion `Matriz de casos` del ID_SPEC: una linea por combinacion con su
resultado, y "como hoy" en las que no cambian. Cada item lleva `casos:` y criterios propios
para su archivo (nunca "igual que el item N"). El implementer certifica y revisa cada caso
evaluando las condiciones del diff, y deja la linea `matriz:` en el ACTA; la prueba en el
navegador recorre la matriz entera. Origen: en 556574 Actualizar copio a medias el cambio de
Insertar y rompio el caso "empresa R.S.T." sin que el lint ni la autorrevision lo vieran.

Las preguntas llegan con la herramienta `question` de OpenCode (eliges una opcion o
escribes la tuya). Toda respuesta queda escrita en un archivo: el chat no es evidencia.

## 3. Comandos (cada uno asignado a UN agente)

| comando | agente | cuando |
|---|---|---|
| `/siguiente [id]` | guia | siempre: dice que sigue y con que comando |
| `/leer <id> ["ruta"]` | lector | hay documento (PDF, Word, mockups): -> REQUERIMIENTO numerado |
| `/spec <id> [notas, respuestas, cambio:]` | analista | ruta de desarrollo + preguntas + ID_SPEC |
| `/cambio <id> <ajuste>` | analista (modo cambio) | ajuste pequeno a un spec ya existente: sin leer codigo, deja listo `/implementar ... items N` |
| `/scope <id>` | avansat_expert | modulo desconocido: que archivos toca |
| `/mapa <id>` | avansat_expert | varios archivos comparten logica |
| `/impacto <id> [simbolos]` | avansat_expert | revision independiente antes de tocar algo sensible |
| `/equivalencia <id> <archivo>` | avansat_expert | PORTE: donde va cada cambio de la referencia en el objetivo y que cambia |
| `/implementar <id> [archivo] [items N,M]` | implementer | codigo NUEVO (incluye certificado de impacto propio); con `items N` solo esos items (correccion puntual) |
| `/migrar <id> [DEST] [SRC]` | migrator | mismo archivo, de copia vieja a copia limpia |
| `/migrar-curado <id> <BLOQUES> [n]` | migrator | aplicar un BLOQUES ya generado y filtrado a mano, sin regenerar |
| `/comentarios <id> <archivo> [lineas]` | migrator | corregir solo los comentarios del id en un archivo ya escrito |
| `/comparar <a> <b>` | comparator_agent | depurar un fallo o comparar versiones/modulos |
| `/documentar <id> [que se probo]` | documenter | tras la prueba funcional |
| `/commit <id> [feat\|fix] [notas]` | commits | mensaje del commit y del pull request de Bitbucket; git lo ejecutas tu |
| `/resumen <id> [notas]` | resumen | al final del id: tabla en el chat de lo que se modifico en cada archivo (Existente/Nuevo) y las sentencias SQL del spec, para llenar el guion de montaje. No escribe archivos |
| `/reporte [horas] [notas]` | time_report | cierre del dia |

Recorridos tipicos:
- ajuste despues de probar (id ya implementado): `/cambio <id> <ajuste>` -> `/siguiente <id>` -> `/implementar <id> <archivo> items N` (sesion nueva) -> prueba -> `/commit <id> fix`
- cambio menor sin documento: `/spec <id> cambio: ...` -> `/implementar` -> prueba -> `/documentar` -> `/commit` -> `/reporte`
- id pequeno con documento: `/leer` -> `/spec` -> `/implementar` -> prueba en navegador -> `/documentar` -> `/commit` -> `/reporte`
- id grande o modulo desconocido: `/leer` -> `/spec` -> `/scope` -> `/mapa` -> `/impacto` -> `/implementar <id> <archivo>` (una sesion por archivo) -> ...
- migracion del mismo archivo: `/migrar` -> prueba -> `/documentar`
- porte a otro modulo con logica propia: `/equivalencia <id> <archivo>` (una sesion por archivo) -> revisar ITEMS_*_BORRADOR.md y pasarlos al ID_SPEC -> `/implementar <id> <archivo>` -> prueba -> `/documentar`

`<id>` en los comandos es el NOMBRE DE LA CARPETA del id (ej. 566647_v2). El numero de los comentarios sale del campo `id:` del ID_SPEC.

## 3.1 Correccion puntual (sin que el analista ni el implementador recorran todo)

Cuando la prueba en navegador falla en un punto concreto:

1. `/cambio <id> <lo que fallo, en tus palabras>` (analista, modelo flash). No lee codigo:
   relaciona tu texto con los items, te confirma con UNA pregunta y actualiza SOLO esos items.
   Si el cambio toca la ruta o una regla de negocio, te dice que va por `/spec`.
2. `/siguiente <id>`. El router compara la huella de cada item con la de su ultima
   aplicacion (REGISTRO.jsonl) y te da el comando exacto con SOLO los items que cambiaron:
   `/implementar <id> <archivo> items N`. Los items que no cambiaron no se vuelven a revisar.
3. `/new` y ese comando (implementer, modelo flash, esfuerzo high). En modo delta corre
   `id_workspace.py contexto <id> <archivo> --items N` en lugar de leer el spec, el ACTA y
   el IMPACTO completos (en 548866/ajax.php: 15 KB contra 117 KB).
4. Prueba en navegador. Si pasa: `/commit <id> fix`.

Si un item queda YA_APLICADO sin escribir, el implementer corre
`id_workspace.py verificado <id> <archivo> --items N` y el router deja de pedirlo.
Un item = un archivo: si un cambio mueve logica a otro archivo, ese archivo lleva su propio
item. `/siguiente` avisa cuando un archivo tiene escrituras en REGISTRO.jsonl pero ningun item
(un /cambio futuro de esa logica no llegaria a el); se corrige dandole su item y, si el codigo
ya esta, con `verificado`. Los avisos de RIESGO/BLOQUEADO salen del veredicto de cada item en
la ultima corrida de su ACTA (linea `items:`), solo para items que siguen pendientes.
Los ids en curso antes de las huellas se sellan una vez con `id_workspace.py sellar <id>`
(ya se hizo con 548866 y 548866_v2).

## 3.2 Commit y pull request (git lo ejecutas SOLO tu)

Ningun agente ejecuta git: lo bloquean `opencode.json` (global y en cada agente) y el
plugin `.opencode/plugins/sin-git.js`, que revisa todo comando antes de ejecutarlo.
`/commit <id> [feat|fix]` deja en `_agentes`:

- `COMMIT_<repo>.txt`: `[REQ_<id>] <feat|fix>: <descripcion corta>` y hasta 4 lineas de detalle;
- `PR_<repo>.txt`: titulo y 2-3 lineas para "Create pull request" de Bitbucket;

y te da los comandos (`git add <archivos del id>`, `git commit -F <COMMIT_...txt>`) para que
los corras tu desde el repo. Toma solo lo escrito desde el ultimo mensaje sugerido
(`--todo` para todo el id).

Si commiteas a mano (sin `/commit`), `/siguiente` lo nota (el commit del repo cambio desde la
ultima escritura del id y no hay mensaje registrado) y te da la linea para registrarlo, asi el
proximo `/commit` no vuelve a proponer esos archivos:
`python .opencode/skills/commit-msg/commit_msg.py <id> --registrar <repo> --tipo <feat|fix>`

## 3b. Ruta estandar por tipo de id (quien hace cada paso)

Regla: cada paso tiene UN responsable. Si no es un comando, lo haces tu.
Escribir el prompt sin comando NO cambia de agente: en ese caso elige el agente con Tab.

### Tipo `nuevo` (funcionalidad que no existe)

| # | paso | responsable | como | sale |
|---|---|---|---|---|
| 0 | rama del id en el repo | tu (git) | `git checkout -b REQ_<id>` desde master actualizado | rama del id |
| 1 | crear carpeta | tu (terminal) | `id_workspace.py init <id>` | `_agentes/ID_SPEC.md` con rutas logicas |
| 1b | leer el documento (si hay) | **lector** | `/leer <id> "<ruta>"` | REQUERIMIENTO_<id>.md |
| 2 | ruta de desarrollo, preguntas e items | **analista** (o chat) | `/spec <id>` | ID_SPEC lleno, ruta confirmada |
| 3 | que archivos toca (solo si el modulo es desconocido) | **avansat_expert** | `/scope <id>` | SCOPE.json |
| 4 | flujo entre archivos (solo si son 2 o mas) | **avansat_expert** | `/mapa <id>` | MAP.json |
| 5 | impacto independiente (solo si toca algo sensible) | **avansat_expert** | `/impacto <id>` | IMPACTO.json |
| 6 | implementar, un archivo por sesion | **implementer** | `/implementar <id> <archivo>` | CERTIFICADO, BLOQUES, REGISTRO |
| 7 | prueba funcional | tu (navegador) | criterios + pruebas negativas del ID_SPEC | notas de prueba |
| 8 | manual tecnico | **documenter** | `/documentar <id> <que se probo>` | DOCUMENTACION_TECNICA_ID<id>.html |
| 9 | reporte del dia | **time_report** | `/reporte <horas> <notas>` | texto para copiar |

### Tipo `porte` (existe en otro modulo con logica distinta)

| # | paso | responsable | como | sale |
|---|---|---|---|---|
| 1 | crear carpeta | tu (terminal) | `id_workspace.py init <id>` | ID_SPEC vacio |
| 2 | ID_SPEC sin items: pares referencia -> objetivo | **analista** (o chat, o tu) | `/spec <id>` (regla 7b) | ID_SPEC con `Referencia` |
| 3 | equivalencia, un archivo objetivo por sesion | **avansat_expert** | `/equivalencia <id> <archivo>` | EQUIVALENCIA_*.json, ITEMS_*_BORRADOR.md |
| 4 | aprobar items y pasarlos al ID_SPEC | tu | revisar `adaptacion`, NO_APLICA, PENDIENTE DE REVISION | ID_SPEC con items |
| 5 | implementar, mismo orden, un archivo por sesion | **implementer** | `/implementar <id> <archivo>` | CERTIFICADO, BLOQUES, REGISTRO |
| 6 | prueba funcional | tu (navegador) | | notas de prueba |
| 7 | manual tecnico | **documenter** | `/documentar <id> <que se probo>` | manual .html |
| 8 | reporte del dia | **time_report** | `/reporte <horas> <notas>` | texto |

### Tipo `migracion` (mismos cambios, copia vieja -> copia limpia del MISMO archivo)

| # | paso | responsable | como | sale |
|---|---|---|---|---|
| 1 | crear carpeta y copiar DEST limpio + SRC viejo | tu | terminal | archivos en la carpeta del id |
| 2 | ID_SPEC con `ruta` (DEST) y `fuente` (SRC); cambios ajenos si los hay | **analista** o tu | `/spec <id>` | ID_SPEC |
| 3 | generar, comentar, aplicar, lint | **migrator** | `/migrar <id>` | BLOQUES, REGISTRO |
| 4 | prueba funcional | tu (navegador) | | notas |
| 5 | manual tecnico | **documenter** | `/documentar <id> <que se probo>` | manual .html |
| 6 | reporte | **time_report** | `/reporte` | texto |

### En cualquier momento

| situacion | responsable | como |
|---|---|---|
| no se que sigue / en que iba | **guia** | `/siguiente [id]` |
| un bloque fallo, algo se ve raro, comparar versiones o modulos | **comparator_agent** | `/comparar <a> <b>` |
| deshacer una escritura | tu | en el repo con git (lo ejecutas tu), o copiar `_agentes\respaldos\<archivo>.PRE_<fecha>.bak` sobre el archivo |
| mensaje de commit y pull request | **commits** | `/commit <id> [feat\|fix]` |

## 3c. Modelos sugeridos (los eliges tu en OpenCode; solo `guia` tiene modelo fijo)

Criterio: el razonamiento fuerte va donde un error se propaga (analisis e implementacion);
los modelos rapidos, donde el trabajo es mecanico. Sugerencia por rol, no benchmark:
ajustar con la evidencia de cada piloto.

| agente | tarea | sugerido | alternativa | esfuerzo |
|---|---|---|---|---|
| lector | documento -> REQUERIMIENTO | zai-coding-plan/glm-5.3-flash (fijo: es el unico con entrada de imagen y PDF) | - | high |
| analista | requerimiento -> ID_SPEC | zai-coding-plan/glm-5.3 | zai-coding-plan/glm-5.2 | max |
| analista | `/cambio` (ajuste pequeno) | zai-coding-plan/glm-5.3-flash | byteplus/deepseek-v4-flash | normal |
| avansat_expert | SCOPE / MAP | zai-coding-plan/glm-5.3-flash | byteplus/deepseek-v4-flash | max |
| avansat_expert | EQUIVALENCIA / IMPACTO | zai-coding-plan/glm-5.3-flash (validado en piloto 566647) | zai-coding-plan/glm-5.3 si el resultado trae muchas `confidence: baja` o falla la revision | max |
| implementer | codigo nuevo con riesgo: SQL dentro de transacciones, logica que se cruza con otra funcionalidad (ej. el Prevalidador en class_manifi), codigo central de todos los clientes (ws_rndc), porte | zai-coding-plan/glm-5.3 | byteplus/deepseek-v4-pro | max |
| implementer | codigo nuevo local y con patron en el mismo archivo: un check o campo en pantalla, mostrar/ocultar por AJAX, una columna condicional en un INSERT/UPDATE, un dato informativo (validado en 562380: ajax.php de vehicu) | zai-coding-plan/glm-5.3-flash | byteplus/deepseek-v4-flash | high |
| implementer | delta con `items N` (1-2 bloques, criterios concretos) o verificacion YA_APLICADO | zai-coding-plan/glm-5.3-flash | byteplus/deepseek-v4-flash | high |
| migrator | migracion mismo archivo | zai-coding-plan/glm-5.3-highspeed | byteplus/deepseek-v4-flash | normal |
| documenter | manual detallado | zai-coding-plan/glm-5.3 | byteplus/kimi-k2.5 | normal |
| comparator_agent | diff / depuracion | zai-coding-plan/glm-5.3-flash | byteplus/deepseek-v4-flash | normal |
| time_report | reporte del dia | zai-coding-plan/glm-5-turbo | zai-coding-plan/glm-4.7 | bajo |
| guia | relevo del router | zai-coding-plan/glm-5-turbo (fijo en el agente) | - | bajo |
| commits | mensaje de commit y pull request | zai-coding-plan/glm-5-turbo (fijo en el agente) | - | bajo |
| resumen | resumen final por archivo | zai-coding-plan/glm-5-turbo (fijo en el agente) | - | bajo |

Evitar modelos flash/turbo en el analisis completo (`/spec`), en la primera implementacion de
un archivo y en el documenter: producen lo que llega a produccion o razonan escenarios de
fallo. Flash SI sirve en `/cambio` (emparejar texto con items) y en los deltas con `items N`:
ahi la red de seguridad no es el modelo sino apply_blocks (todo o nada), el lint, el checklist
de reglas globales del ACTA y la revision del diff.

Costo (cuota de 5 horas): cada paso de un agente reenvia TODO el contexto acumulado. Por eso:
- una sesion nueva (`/new`) por cada `/implementar` y cada `/cambio`: el contexto arranca vacio;
- `items N` siempre en los ajustes: el agente no revisa el archivo entero;
- esfuerzo `high` en deltas, `max` solo en la primera implementacion;
- ajustes con `/cambio`, no con `/spec` (este relee requerimiento y codigo);
- ids grandes en carpetas por parte (ej. `548866_p2`): specs cortos, ejecuciones baratas.
Las alternativas `byteplus/*` necesitan credencial: en `D:\PhpStormGrupoOet` hoy solo
esta autenticado Z.AI Coding Plan (`opencode auth list`).

Anota en `/reporte` (notas) que modelo usaste en cada paso mientras se estandariza.

## 4. Que queda en `_agentes/`

| archivo | lo escribe | lo lee |
|---|---|---|
| `../REQUERIMIENTO_<carpeta>.md` (raiz del id) | lector, o analista con `cambio:` | analista, documenter |
| `../_requerimiento/` (fuentes, img, EXTRACCION.md) | leer_requerimiento.py | lector |
| ID_SPEC.md (con Ruta de desarrollo, Decisiones, Trazabilidad) | tu, o analista (`/spec`) | todos |
| ID_SPEC_anterior_<fecha>.md | analista, al aplicar una propuesta que aprobaste | tu |
| ACTA_<archivo>.md | implementer, migrator (una seccion por corrida, nunca se borra) | documenter, la siguiente corrida |
| lotes/<fecha>_BLOQUES_*.txt | apply_blocks.py (copia del lote tal como se aplico) | documenter, retrabajo |
| PRUEBAS.md | documenter (tus notas de prueba, con fecha) | documenter |
| ID_SPEC_PROPUESTA.md | analista, si el ID_SPEC ya tenia cambios tuyos | tu (lo fusionas) |
| SCOPE.json, MAP.json, IMPACTO.json | avansat_expert | implementer, documenter |
| EQUIVALENCIA_<archivo>.json, ITEMS_<archivo>_BORRADOR.md | avansat_expert | tu (revision), implementer, documenter |
| CERTIFICADO_<archivo>.md | implementer | documenter |
| BLOQUES_<archivo>.txt | implementer, migrator | apply_blocks, documenter |
| REGISTRO.jsonl | apply_blocks.py (--registro); `verificado` y `sellar` de id_workspace.py | documenter, router, /commit |
| respaldos/<archivo>.PRE_<fecha>.bak | apply_blocks.py (estado original antes de cada lote; fuera del repo) | tu, documenter |
| COMMIT_<repo>.txt, PR_<repo>.txt | commits (`/commit`) | tu (commit, Bitbucket) |
| COMMITS.jsonl | commit_msg.py --registrar (desde cuando toma cambios el siguiente /commit) | commit_msg.py, router |
REGISTRO.jsonl es lo que le dice al router que un archivo ya se aplico y lo que llena la
ficha de trazabilidad del manual: aplica SIEMPRE con `--registro --lint` (los agentes ya lo
hacen). Cada fila guarda tambien los items del lote, la copia del lote, el resultado del
lint del archivo y de su backup (`error_nuevo` = lo introdujo el cambio), la ruta logica
(`archivo_ref`), el repo, la rama, el commit base y la huella de cada item del lote.
Bitacora diaria: `.opencode/logs/AAAA-MM-DD.md`, o la carpeta de `configurar --logs` (la usan
`/reporte` y `/commit`).

## 5. Requisitos del equipo

| que | para que | estado en D:\PhpStormGrupoOet (2026-09-21) |
|---|---|---|
| OpenCode abierto desde la carpeta que contiene `.opencode` | cargar agentes y encontrar los scripts | - |
| `python` en el PATH | todos los scripts | OK (3.14) |
| `node` en el PATH | lint JS (`node --check`) | OK (v24) |
| `php` en el PATH, idealmente 5.4 | lint PHP (`php -l`); un 5.4 rechaza tambien la sintaxis prohibida | OK (PHP 5.4.45, verificado 2026-09-25). En otro equipo sin el, el lint PHP sale "no ejecutado". Oficial: https://downloads.php.net/~windows/releases/archives/php-5.4.45-nts-Win32-VC9-x86.zip (necesita VC++ 2008 x86) |
| Pillow (`pip install pillow`) | extraer las imagenes de los PDF para `/leer` | sin el, el lector lee el PDF completo como adjunto |
| credencial del proveedor del modelo | ejecutar los agentes | Z.AI OK; BytePlus sin credencial |

## Protecciones

- Git lo ejecuta SOLO el desarrollador. Tres capas: `opencode.json` global (cubre build, plan y
  subagentes), el permiso de cada agente, y el plugin `.opencode/plugins/sin-git.js`, que revisa
  el texto de todo comando antes de ejecutarlo (tambien `cd x;git ...` o `python -c "...git..."`).
  La rama y el commit se leen de los archivos de `.git`, sin ejecutar git.
- `apply_blocks.py` en un id: solo escribe los `Archivos objetivo` del ID_SPEC (`FUERA_DE_ALCANCE`),
  nunca con el repo en master/main (`RAMA_BASE`), nunca un archivo de repo desde un lote que no
  sea de un id, y avisa `AVISO_CAMBIO_EXTERNO` si el archivo cambio fuera del flujo desde su
  ultima escritura (editor, pull, cambio de rama).
- Archivos nuevos (tipo `nuevo` con archivos que aun no existen): el ID_SPEC marca `nuevo: si` en
  su entrada de `Archivos objetivo`; `estado` lo muestra `[NUEVO]` y el router no lo pide copiar.
  `apply_blocks.py` lo crea solo con UN bloque de `search_block` vacio, en ISO-8859-1 y CRLF, si su
  carpeta existe; el REGISTRO lo anota con `creado: true`. Sin `nuevo: si`, un archivo que no
  existe sigue siendo `*** NO EXISTE ***`.
- `protected_paths.txt`: los scripts de escritura se niegan a escribir en esas rutas (`PROTEGIDO`):
  `.git`, `_respaldos`, `node_modules`. Los repos ya no van ahi.
- Los agentes no pueden abrir .php/.js/.htm/.inc con la lectura nativa (UTF-8): usan read_file.py.
- `opencode.json` prohibe a CUALQUIER agente (tambien build y plan) editar .php/.js/.htm/.inc
  con la edicion nativa, que los reescribiria en UTF-8. Solo `apply_blocks.py` escribe esos archivos.
- Los scripts escriben su salida en UTF-8: OpenCode ve los acentos tal cual y el search_block
  copiado de read_file.py ancla byte a byte.
- Cada `--apply` de un id deja `_agentes/respaldos/<archivo>.PRE_<fecha>.bak` con el estado
  original completo, fuera del repo (no ensucia git status ni se cuela en un commit).
