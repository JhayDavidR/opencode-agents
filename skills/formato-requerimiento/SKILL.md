---
name: formato-requerimiento
description: >
  Exact format of REQUERIMIENTO_<carpeta>.md, the requirement of an id turned
  into numbered, traceable statements (R1..Rn) with literal quotes, screens,
  parameters and open doubts. The lector writes it; the analista reads it and
  maps every R to an item, a question or "fuera de esta entrega".
---

# formato-requerimiento

One file per id, in the id folder root: `<ID_DIR>/REQUERIMIENTO_<carpeta>.md`,
UTF-8, Spanish. Sections in this order; omit a section only if it would be empty,
except `Requisitos`, which always exists.

```
# REQUERIMIENTO <id>

carpeta: <carpeta>
generado: <AAAA-MM-DD HH:MM> por lector
fuentes:
- F1 <archivo> | <tipo> | <n> paginas | sha256 <12> | usado: si (vigente)
- F2 <archivo> | ... | usado: no (pruebas de una version anterior)

## Datos del documento
- solicitante, id inicial, version y fecha del documento, complejidad,
  modulos afectados, aprobado por (lo que el documento traiga)

## Resumen
3-5 frases en terminos de negocio. [interpretacion]

## Requisitos
R1. <un comportamiento observable, una sola cosa>
    fuente: F1.p2.L3-L9 | imagen: _requerimiento/img/F1_p2_1.png
    literal: "<cita exacta, lineas unidas>"
    tipo: pantalla | proceso | dato | reporte | exportable | transmision | parametro | no funcional
    modulo o ruta de menu: <como lo nombra el documento, ej. Manifiestos > Insertar>
    [interpretacion: solo si el literal no basta; nunca una regla nueva]

R2. ...

## Pantallas y mockups
### _requerimiento/img/F1_p2_1.png (F1 pagina 2)
textos visibles: "Consolidar Remesa", "PAQ24", ...
que muestra [interpretacion]: ...
requisitos: R1, R2

## Parametros, tablas y campos mencionados
- ind_recopa: "<literal>" (F1.p1.L30)

## Fuera de alcance o notas del documento
- <lo que el documento excluye o condiciona, con su referencia>

## Dudas del documento
D1. <pregunta concreta que el documento deja abierta> (afecta R3, R4; ver F1.p2.L5)

## Aclaraciones
<!-- Respuestas del desarrollador a preguntas del lector (fecha, pregunta, respuesta literal).
     Se conserva al regenerar el archivo. -->
```

## Rules

1. **Atomic**: one R = one behavior a tester can check. A paragraph that asks
   for three things is three R. Split by module or screen too: "Insertar,
   Insertar*, Actualizar y Actualizar*" stays one R only if the behavior is
   identical in all of them.
2. **Complete**: every sentence of the vigente document that asks for
   something ends up in exactly one R, in `Fuera de alcance o notas`, or in
   `Datos del documento`. Nothing is silently dropped.
3. **Stable numbering**: R numbers never change once the analista used them.
   When regenerating, keep existing numbers and append new ones.
4. **Literal first**: `literal` is copied, never paraphrased. Interpretation
   goes only in `[interpretacion: ...]`.
5. **Doubts are questions**: `Dudas del documento` are concrete and answerable
   in one sentence. The analista asks them to the developer with the code in
   front of it; you only state them.
