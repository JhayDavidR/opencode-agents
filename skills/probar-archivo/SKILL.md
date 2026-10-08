---
name: probar-archivo
description: >
  Executes a PHP file of the id (a class, its functions, the reader of an uploaded
  file) with PHP 5.4 and no server or database, following a JSON test plan:
  constants, session, a mock of the Consulta class (rules by query text) and a
  sequence of calls whose results are printed compactly. Used by /revisar to check
  the code against pruebas/ESPERADO.md before the developer tests in the browser.
---

# probar-archivo

```bash
python .opencode/skills/probar-archivo/probar_php.py "<ID_DIR>/pruebas/PRUEBA_<archivo>.json" [--caso <nombre>]
```

The full format of the plan is in the docstring of `probar_php.py` (run it with
`--help`). The plan lives in the id folder, next to the test files, so it stays as the
regression test of that file: every later `/revisar` runs it again.

## When it applies

- Classes and functions with logic: reading and validating a file, cross-checking,
  computing totals, building an accounting voucher.
- NOT screens (ins_*.php that print HTML through DinamicHtml) nor JS: those are
  reviewed statically and tested in the browser.

## How to write a plan

1. `archivo`: the logical path of the target file, as in Archivos objetivo.
2. `constantes`: the ones the file uses (consultor: `DIR_APLICA_CENTRAL`, `CONS`, `OTRA`,
   `EMPRESA`; sate_standa: `BASE_DATOS`, ...). Any short value works: the mock matches by
   table name, not by database prefix.
3. `mock`: one rule per query the tested methods make. Rules are checked in order and the
   first match wins: put the specific ones first (two tables in `contiene`) and the
   generic ones after. `por` + `filas_por` answers per key (manifest, document);
   `variable` answers with what an earlier step produced (rows the code stored and reads
   back). Use only data the spec, the test files or the developer gave.
4. `pasos`: create the object, call the methods in the order the screen does, keep the
   results with `guardar` and print only what ESPERADO.md states (`agrupar`, `sumar`,
   `columnas`). `solo_si` skips a step when an earlier one failed (a rejected file is
   not cross-checked).
5. `casos`: one per test file or parameter variant, with its `vars`.

## Reading the output

- `FIN OK` at the end of a case: PHP ran to the end. Without it there was a fatal error
  or an `exit` of the tested code (the line above says which).
- `ESCRITURAS`: the INSERT/UPDATE/DELETE the code sent; check them against the
  criteria (what is written, in which format, how many).
- `CONSULTAS SIN REGLA EN EL MOCK`: queries that got 0 rows. Harmless when 0 rows is the
  normal answer (no closed period, no missing third party); otherwise add the rule or
  report it as `no verificado`.
- PHP warnings and notices appear inline: a warning inside the tested code is a finding.

Real example: `ids/10_Octubre/587624/pruebas/PRUEBA_class_concil_fopatx.json`
(4 cases: clean file, cases file with both mandantes, rejected file).
