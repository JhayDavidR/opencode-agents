---
name: ruta-desarrollo
description: >
  The development route of an id, confirmed with the developer at the start
  and written in the ID_SPEC section "Ruta de desarrollo": id folder, repo and
  branch the id is developed on (or the copies, when a file lives outside every
  repo), tipo, scope of this delivery, target files, size and the path of
  commands, database changes. No implementation starts without it.
---

# ruta-desarrollo

Every later agent assumes the route. A wrong base (an outdated branch, a stale
copy), a wrong tipo or an
unclear scope costs the whole id, and none of them can be seen in the code.
That is why the route is proposed with evidence and confirmed by the developer
before any item is written.

## What the route contains

| # | decision | evidence you bring | typical question |
|---|---|---|---|
| 1 | Carpeta del id and base: repo(s), branch and base commit | `id_workspace.py estado`: each repo's branch, commit and last fetch (read from .git as files - you never run git); files present, bytes, encoding; previous attempts in the folder | "El id se desarrolla en la rama REQ_<id> de sate_standa, creada desde master actualizado (ultimo fetch <fecha>)?" If the repo is still on master: the developer creates the branch (git is theirs); state it, the route can be confirmed anyway |
| 2 | Tipo: nuevo, porte or migracion | rules 7 and 7b of PROMPT_ANALISIS; whether the feature exists in another file or in an older copy | "Es desarrollo nuevo o se lleva desde <referencia>?" |
| 3 | Scope of THIS delivery | the R of the requirement grouped by module; what depends on what | "En esta entrega van R1-R4 (Manifiestos) y el resto queda para la parte 2?" |
| 4 | Target files, with logical paths (`{repo:<nombre>}\...`; `{id}\...` only outside every repo) | symbol_readers hits; files the requirement names; files that live outside the registered repos (client folders, another repo not registered) | "X vive en la carpeta del cliente: la trabajamos como copia en {id}\\...?" / "El repo Y no esta registrado en este equipo: cual es su carpeta?" |
| 5 | Size and path of commands | files and items: small = 1 file and at most 3 items (spec, implementar); large = /impacto (and /mapa with 2+ files), one session per file, implementation order | usually no question: state it |
| 6 | Database | DDL the change needs, who applies it and whether it is already applied | "El ALTER ya esta aplicado en la BD de pruebas?" |

## How

1. Gather the evidence first (estado, requirement, one symbol_readers pass).
2. ONE `question` call with up to 4 questions presenting your proposal as the
   recommended option (skill `preguntas-desarrollador`). Decisions 5 and
   anything already settled by the spec or the prompt are stated, not asked.
3. Write the section in the ID_SPEC, right after the header:

```
## Ruta de desarrollo

confirmada: si (AAAA-MM-DD, respuestas del desarrollador en Decisiones del desarrollador)
carpeta: {id}
base: <repo y rama del id, ej. sate_standa rama REQ_562380 desde master commit d0a42356e; copias en {id} y su origen si las hay; intentos previos descartados: ...>
tipo: <tipo> - <razon en una frase>
alcance de esta entrega: <R incluidos> ; fuera: <R excluidos y por que>
archivos objetivo: <nombres, en orden de implementacion>
recorrido: <pequeno | grande> -> <comandos en orden>
base de datos: <DDL, quien lo aplica, aplicado si/no | sin cambios de esquema>
```

4. If the ID_SPEC already has `confirmada: si`, do not ask again unless the
   prompt says "reconfirmar ruta" or the requirement changed (new version of
   the document, new R). In that case ask only about what changed.

`confirmada: no` (or no section) blocks /implementar, /migrar and
/equivalencia: the router prints it as a pending step.
