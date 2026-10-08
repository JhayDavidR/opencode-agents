---
name: financiero-consultor
description: >
  House conventions of Avansat Financiero (repo consultor): screens, AJAX, database
  prefixes, the Consulta class and its transactions, menu and authorization tables,
  vouchers, Excel import and export. Load it whenever a target file of the id lives
  in the consultor repo (or consultor_cfs). The TMS screen rules of avansat-ui do NOT
  apply there.
---

# financiero-consultor

Learned in id 587624 (Conciliacion FOPAT, client LXPANT, 2026-10). Every entry was
verified in the code or in the client's database at that time. Treat it as a lead:
before citing a line, read it with `read-file`.

## Files and screens

- PHP 5.4, ISO-8859-1, CRLF, like the TMS.
- The client's application folder (`c_<cliente>`, e.g. `c_lxpant_dm`) loads the screens of
  the central code through the menu: `rut_archiv = '../consultor/modules/<modulo>/<archivo>.php'`.
  Inside a screen, `$this -> conexion` is the connection and `DIR_APLICA_CENTRAL` is `consultor`.
- Screens are built with `DinamicHtml` (Form, Table, Row, Label, Select, Info, Hidden, Button,
  Popup, MakeHtml) and lists with `DinamicList`. The `Form` class and the components of the
  avansat-ui skill are TMS-only. Examples: `modules/concil/ins_concil_bancar.php`,
  `modules/concil/ins_config_fopatx.php`.
- `lib/general/functions.inc` is reached by a different relative path from a screen
  (`../consultor/lib/general/functions.inc`, cwd = client folder) and from an AJAX file
  (`../../lib/general/functions.inc`, cwd = module folder). A class shared by both checks
  `file_exists` and uses `include_once`.
- Messages to the user: SweetAlert2 (`js/sweetalert/v11.15.10/sweetalert2.js`, `Swal.fire`).
  Never `alert()` or `confirm()`.
- New file names follow the module: `ins_` insert/process screen, `anu_` annul, `inf_`
  report (in `modules/inform/`), `ajax_` AJAX route, `class_` logic, JS in `js/` with the
  screen's name.

## Database

| prefix in SQL | database |
|---|---|
| `CONS.` | the client's financial database |
| `OTRA.` | the client's TMS database (in consultor it is NOT `BASE_DATOS`) |
| `consultor.` | central database: menu, authorization catalog |
| constant `EMPRESA` | the company's NIT |

- `Consulta( $sql, $conexion, $flag )` (`lib/general/conexion_lib.inc`): `B` begins a
  transaction, `R` rolls back on error, `RC` commits (and rolls back on error), `C` commits.
  One business operation = one transaction from the first `B` to the last `RC`.
  Results: `ret_matriz('a')` associative rows, `ret_matriz('i')` numeric, `ret_arreglo`
  one row.
- On a database error `Consulta` PRINTS an HTML message and exits. An AJAX call then gets
  HTML instead of JSON: the JS must handle a parse error with an E-TEC SweetAlert.
- Consecutive of a voucher type: `tab_genera_tipcom.val_numaut`, read with
  `SELECT ... FOR UPDATE` inside the transaction, then `+ 1`.
- Vouchers: `tab_genera_enccom` / `tab_genera_detcom`. A voucher can be annulled from
  Financiero > Comprobantes > Anular (`ind_anulad = '1'`) without the module that created
  it knowing: any module state tied to a voucher must check `ind_anulad` too.
- Triggers on `tab_genera_enccom` raise 45001 (date before the closing date) and 45002
  (closed year). Validate before inserting so the user gets the literal message, not the
  trigger error.
- Reference code for posting: `modules/autren/ins_autren_causac.php` (consecutive, header,
  detail), `modules/compro/anu_compro_compro.php` (closing date, closed periods, user window).

## Menu and authorizations (central database)

- `consultor.tab_genera_servic` (11 columns: cod_servic, nom_servic, des_servic, rut_archiv,
  rut_jscrip, bod_jscrip, cod_aplica, usr_creaci, fec_creaci, usr_modifi, fec_modifi).
- `consultor.tab_servic_servic (cod_serpad, cod_serhij)`: the tree. A service with no row as
  `cod_serhij` shows at the ROOT of the menu.
- The parent of a new menu is confirmed with a query, never copied from a sibling (a sibling
  may have no parent row; that is how 587624 landed at the root):
  `SELECT s.cod_servic, s.nom_servic FROM consultor.tab_genera_servic s WHERE s.nom_servic LIKE '<texto>%' AND NOT EXISTS (SELECT 1 FROM consultor.tab_servic_servic r WHERE r.cod_serhij = s.cod_servic);`
  (Consultas/Reportes = 6330 in the central database LXPANT uses; verify per environment).
- Per client: `tab_perfil_servic (cod_perfil, cod_servic)` gives the option to a profile.
  The menu is cached in the session: log out and in after changing it.
- Authorizations: catalog `consultor.tab_autori_campos (cod_autori, nom_autori, usr_creaci,
  fec_creaci NOT NULL, usr_modifi, fec_modifi)`; per client `tab_autori_perfil (cod_autori,
  cod_perfil, val_minimo, val_maximo, usr_creaci, fec_creaci)`; checked with
  `GetAutorization( <cod>, $_SESSION['datos_usuario']['cod_perfil'], $conexion )` from
  functions.inc. The next free `cod_autori` comes from `SELECT MAX(cod_autori)`.
- Database scripts of an id: one file `SQL_<id>_<CLIENTE>.sql` in the id folder, ISO-8859-1,
  re-runnable (`CREATE TABLE IF NOT EXISTS`, `INSERT IGNORE`), with verification queries and
  a commented rollback. The developer runs it.

## AJAX

- Entry pattern: `modules/tablasMaestras/contables/RetencionFopat/mod_genera_fopatx.php`
  (`Ajax=on`, `lib/general/ajax.inc`). Read `$_REQUEST`, answer
  `json_encode( array( 'status' => 'success'|'error', 'code' => 'E-RN'|'E-DAT'|'E-TEC'|'M-ADV', 'message' => ..., 'data' => ... ) )`.
- Text going out: `utf8_encode` every string before `json_encode` (PHP 5.4 returns false on
  latin1). Text coming in from the browser is UTF-8: `utf8_decode` before comparing with or
  storing into latin1 tables.
- Export to Excel: put an HTML table in `$_SESSION['SQL_XLS']` and open
  `modules/inform/excel_downloader.php` (do not modify it). Escape every cell with
  `htmlspecialchars`.

## Excel import (PHPExcel)

- `lib/PHPExcel/Classes/PHPExcel.php`; reference reader `modules/cuentasporpagar/causaciones/importar/imp_causac.php`.
- Cell values arrive in UTF-8: `utf8_decode` before validating or storing.
- A date typed as a date arrives as an Excel serial number:
  `PHPExcel_Shared_Date::isDateTime( $celda )` then `PHPExcel_Shared_Date::ExcelToPHPObject( $valor ) -> format( 'd/m/Y H:i:s' )`.
- Validate the extension on the ORIGINAL file name (`$_FILES[...]['name']`): the temporary path
  of an upload does not end in `.xls`.
