---
name: lectura-documentos
description: >
  How to read the requirement documents of a development id (control de
  cambios, especificaciones, mockups, capturas) from the output of
  leer_requerimiento.py: which files are the requirement and which are not,
  how to read text and images without inventing, and how to separate what the
  document says from what you interpret. Load it before reading any document
  of an id.
---

# lectura-documentos

The document is the contract with the business. Everything downstream (ID_SPEC,
code, manual) is only as good as this reading. Your job is to transcribe and
organize, never to complete what the document leaves open.

## 1. Which files are the requirement

An id folder (or the path the developer gives) often mixes documents. Classify
each candidate from its name and first page before extracting:

| kind | typical name | is it the requirement? |
|---|---|---|
| control de cambios / especificacion / requerimiento | `Control de cambios ID <id> Version N.pdf`, `Especificacion...` | YES. If several versions exist, the vigente one is the highest version or the one whose document table says `Vigente` |
| requerimiento inicial referenced by the control de cambios | `... ID <otro id>` | context only; read it only if the vigente document says the change modifies it |
| pruebas / evidencias / guion de montaje / instructivo / manual | `Pruebas ID...`, `Evidencia_...`, `INT-FR-06 Formato Guion de Montaje...`, `Manual tecnico...` | NO. They describe tests or deployment of a previous attempt. Never mix them into the requirement; mention them in `Fuentes` as "no usado" |

When it is not obvious, ask the developer (skill `preguntas-desarrollador`), one
multi-select question listing the candidates with your proposal marked.

## 2. Text

- EXTRACCION.md is the only source of text. Cite every requirement with its
  reference `F<n>.p<pag>.L<linea>` (or a range `L3-L9`), exactly as printed.
- PDF text comes in layout lines: one sentence can span several `L`. Join them
  for the literal quote; keep the words and their order exactly, fix nothing
  (not even typos: "consulado" stays "consulado", you may add "[sic]").
- Repeated headers are already removed. Page counters like "Pagina 4 de 3" are
  document defects: ignore them.
- Tables in forms (Datos basicos, Impacto) are metadata: keep the useful facts
  (solicitante, id inicial, modulos afectados, complejidad) in `Datos del documento`.

## 3. Images

- Read EVERY image marked `REVISAR` with the read tool. Skip `omitida (logo o icono)`.
- For each one write two separate things:
  1. **Textos visibles (literal)**: every label, button, column header, menu
     path, field value and message you can read, in quotes, exactly as shown.
     Unreadable text is `[ilegible]`, never a guess.
  2. **Que muestra [interpretacion]**: the screen and what the mockup marks as
     new or changed (arrows, circles, highlighted columns, example values).
- Tie each image to the requirements it illustrates (the text on the same
  page is usually its caption).
- Example values in mockups (PAQ24, PAQ25, city names) are EXAMPLES, not data
  rules. Say so when you use them.

If EXTRACCION.md has no images because Pillow is missing, read the source PDF
itself with the read tool (it arrives as an attachment) and say in `Fuentes`
that images were read page by page from the PDF.

## 4. What you never do

- Never add a requirement the document does not state, even if it is "obvious"
  for the code. The analista and the code decide HOW; the document says WHAT.
- Never resolve an ambiguity: write it as a `Duda del documento` (D1, D2...),
  with the references that make it ambiguous.
- Never read or mention the source code: you do not have it and it is not your job.
