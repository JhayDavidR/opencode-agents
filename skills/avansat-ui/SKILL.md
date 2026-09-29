---
name: avansat-ui
description: >
  House standard for building or changing screens in the Avansat TMS (PHP 5.4
  + jQuery, ISO-8859-1): the Form class of lib/general/form_lib.inc and its
  global CSS classes, IncludeJS/IncludeCss, the select library (Chosen, also
  for multiple), date and month/year pickers, charts (Chart.js v4) and
  tooltips. Load it before writing or specifying ANY item that creates or
  changes a field, filter, button, section, select, calendar or chart.
---

# avansat-ui

A new control that ignores the house standard looks foreign on the screen and
behaves differently from its siblings (focus colours, input masks, widths). The
standard below was measured on the codebase (counts of files that use each
option, 2026-09-22). Rule zero overrides everything: **before creating a
control, find a sibling screen in the SAME module that already has one, read
it with read_file.py and copy its pattern.** Cite that file:line in the
certificate. Use this skill only when the module has no precedent.

## 1. Build fields with the Form class, never with raw HTML

`lib/general/form_lib.inc`, class `Form`. Every screen already has
`$mForm = new Form( "action:...; method:post; name:frm_xxx" )`.

Properties are ONE string `"clave:valor; clave:valor"` (GetProperties). The
`name` gets its `id` automatically as `<name>ID` (SetProperties): never write
the id by hand, and read it in JS as `#<name>ID`.

| need | call | classes it applies by itself |
|---|---|---|
| section header (the grey bar) | `$mForm -> Table('tr'); $mForm -> Line( "Titulo", "t2", 0, 0, "left" ); $mForm -> CloseTable('tr');` | same as "Listado" |
| label | `$mForm -> Label( "Mes:", "for:fec_filtroID; width:25%;" );` | cell `celda_etiqueta` |
| text / date input | `$mForm -> Input( "name:fec_filtro; width:25%; size:10;" );` | cell `celda_info`, input `campo_texto`; focus `campo_texto_on` |
| full date with calendar | add `calendar:yes;` to Input | calendar icon + `BlurDate` mask (433 files use it) |
| select | `$mForm -> Select( $options, "name:cod_xxx; width:25%;" );` | select `form_01`; $options = array( array(valor, texto) ) |
| select multiple | `$mForm -> Select( $options, "name:fil_proces[]; id:fil_procesID; multiple:yes; width:25%;", $keysSelected );` | name with `[]` so PHP receives an array, and an EXPLICIT id without brackets (otherwise the id becomes `fil_proces[]ID`, unusable from jQuery). Pattern: "name:cod_obltri[]; id:cod_obltriID; multiple:yes" |
| read-only value | `$mForm -> Info( "name:x; value:..." );` | `celda_info` |
| hidden | `$mForm -> Hidden( "name:x; value:..." );` | - |
| button | `$mForm -> StyleButton( "name:but_x; align:center; value:Aplicar; onclick:Funcion();" );` | house button |
| end of row | add `end:y;` to the last control of the row | closes the `<tr>` |

Texts go through htmlentities with ISO-8859-1 inside the class: pass them as
they come from the DB, do not encode them again.

## 2. Include JS and CSS with the helpers

- `IncludeJS( "archivo.js" )` loads from `../DIR_APLICA_CENTRAL/js/`
  (lib/general/functions.inc:87). Subfolders: `IncludeJS( "multiselect/x.js" )`.
- `IncludeCss( "archivo.css" )` loads from `../DIR_APLICA_CENTRAL/estilos/`
  (functions.inc:106); another folder goes as second parameter.
- No CDN. If the screen already includes a library, do not include it twice.

## 3. Selects: Chosen (416 files)

Single and multiple selects are enhanced with Chosen:

    IncludeJS( "chosen.jquery.js" );
    IncludeCss( "chosen.css" );
    ...
    $("#fil_procesID").chosen({ width: '300px', placeholder_text_multiple: 'Todos los procesos' });

(pattern of conduc/ins_conduc_conduc.php:151-152). An empty multiple select
means "all": do not add a fake "Todos" option. `jquery.multiselect` exists
(js/multiselect, 25 files) but is the minority: use it only if the module
already does.

## 4. Dates

- Full date: Form `Input` with `calendar:yes` (section 1).
- Month and year only: jQuery UI datepicker (90 files) with
  `changeMonth: true, changeYear: true, dateFormat: 'yy-mm'` and the day grid
  hidden, `minDate` = first record in the DB (a SELECT MIN(...) printed by PHP),
  `maxDate` = today. Check with read_file.py that the screen loads jQuery UI;
  if not, include the build its module already uses (`jquery-ui-1.9.1.custom.js`
  is the most common).
- The value that reaches PHP is validated with a regular expression before SQL.

## 5. Charts: Chart.js v4 of the TMS

- `index/js/lib/chart.js` (v4.5.0) + `index/js/lib/chartjs-plugin-datalabels.js`
  (v2.0.0), registered with `Chart.register(ChartDataLabels)` (index/index.php:773).
  Never `Chart.bundle.min.js`.
- Colours: there is no house palette in the codebase. Use this one, in order,
  cycling: `#bb0000` (the red of the house title bar), `#1f4e79`, `#2e8b57`,
  `#e69f00`, `#6a3d9a`, `#008b8b`, `#8b4513`, `#c71585`, `#556b2f`, `#4682b4`.
  One colour per category, never a single colour for every bar.
- Hover text: `options.plugins.tooltip.callbacks` of Chart.js (not a separate
  library). Mouse cursor `pointer` over a clickable bar.
- Data from PHP: json_encode with texts passed through utf8_encode (PHP 5.4
  returns false with ISO-8859-1 accents).

## 6. Never

- Raw `<input>`, `<select>`, `<table>` when a Form method exists.
- Inline `style=` to imitate a class the Form already applies.
- New CSS files for a single screen, CDNs, or a second copy of a library.
- Arrow functions, let/const or template literals in JS: match the file.
