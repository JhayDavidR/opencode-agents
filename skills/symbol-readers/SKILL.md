---
name: symbol-readers
description: >
  Finds EVERY use of one or more symbols across legacy ISO-8859-1 PHP/JS
  files, classified into definition, call, write, DOM read, DOM write,
  $_POST access and string literal. Answers "who reads this" mechanically,
  before anything is touched. Mandatory in MODE IMPACTO: it replaces the
  hand-written grep and produces a per-pattern count.
---

# symbol-readers

Answers exactly one question, and answers it without judgement: **who uses
this symbol, where, and in what way.**

In this codebase presentation is used as data: a visible label, a hidden field
or a select's value feed validations that live in another file. Changing one
without knowing who reads it is the main source of regressions. This script is
the step that prevents that.

## Usage

Against specific files:

```bash
python "<skill_dir>/symbol_readers.py" --symbol nom_descarID --file a.js --file b.php
```

Against a whole folder:

```bash
python "<skill_dir>/symbol_readers.py" --symbol GetTrayler --root path/to/module --ext .php --ext .js
```

`--root` can be repeated. Against the WHOLE codebase (sate_standa has ~6600
files, far above the limit), add `--prefilter`: it walks every folder but scans
only the files whose bytes contain a symbol, and the file limit applies to those
candidates. `ALCANCE` then reports both numbers:

```bash
python "<skill_dir>/symbol_readers.py" --symbol tab_manrem_consol --root <SATE_STANDA> --ext .php --ext .js --ext .inc --prefilter
```

`<SATE_STANDA>` is printed by `id_workspace.py estado <carpeta>`.

Several symbols in one run - always prefer this: it reads each file once
instead of N times:

```bash
python "<skill_dir>/symbol_readers.py" --symbol Insert --symbol Update --file class.php
```

Add `--json` for strict JSON output.

## Classification

Every occurrence gets exactly one kind, in this priority order:

| kind | meaning |
|---|---|
| `definicion_php` / `definicion_js` | declared here |
| `llamada_metodo` | invoked via `->` or `::` |
| `llamada` | direct invocation |
| `acceso_post_get` | arrives through `$_POST` / `$_GET` / `$_REQUEST` / `$_AJAX` |
| `escritura_dom` | **overwrites** a DOM value (`.val('x')`, `.value =`, `.checked =`) |
| `selector_dom` | **reads** a DOM value |
| `escritura` | assignment to a variable |
| `propiedad` | accessed as an object property |
| `literal_cadena` | appears quoted |
| `variable_php` | `$symbol` |
| `mencion` | appears as a bare word |

`escritura_dom` ranks above `selector_dom` on purpose: a writer is what can
overwrite a value another function takes for granted.

Every occurrence also carries `in_comment`, so comments are not counted as real
readers.

## Why the per-kind breakdown

The output includes `DESGLOSE POR TIPO`. That is what lets you assert a count
without depending on a single search pattern: if the total and the breakdown do
not match what you expected, the scope is wrong, not the code.

## Exit codes

| code | meaning |
|---|---|
| `0` | every symbol had at least one occurrence |
| `3` | some symbol had ZERO occurrences. **Not an error: a finding.** Usually dead code, or the symbol does not exist in that tree |
| `4` | usage error, empty scope, or too many files |

## Limits

- Scans at most 400 files (`--max-files` changes it). Above that the script
  refuses instead of taking minutes: narrow the folder or use `--prefilter`.
- Always decodes as latin-1: it never fails on encoding and never reinterprets
  bytes.
- Skips `.git`, `.svn`, `node_modules` and `.idea`.
- With the default `--ext` (`.php`, `.js`), `.bak` files stay out. That is
  deliberate: a `.bak` is not a reader.
- **It does not find indirect readers.** A value reached through an
  intermediate variable, through a name built at runtime, or through an SQL
  query will not appear here. That part is the agent's judgement, not the
  script's.
