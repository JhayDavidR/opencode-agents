---
name: preguntas-desarrollador
description: >
  When and how an agent asks the developer with the question tool, and where
  the answer is persisted so that no decision lives only in the chat. Load it
  before the first question of a session.
---

# preguntas-desarrollador

The requirement never specifies everything. A question at the right moment is
cheaper than a wrong item, a wrong block or a rework. But an answer that stays
in the chat is lost for the next agent and for the manual: every answer is
written to disk the moment you receive it.

## When to ask

Ask ONLY when the answer changes what you write:
- a business rule the document leaves open (value of a parameter, what happens
  with legacy data, which screens are included);
- the development route (skill `ruta-desarrollo`);
- a RIESGO decision: a reader outside the plan would be affected;
- approval before a write that the spec marks `confirmar_antes_de_aplicar: si`;
- which document is the vigente requirement.

Never ask:
- what the scripts or the code can tell you (locate it first);
- "which part of the file should I look at";
- for permission to follow your own workflow.

## How to ask

Use the `question` tool, never a free-text question at the end of a message.

- Up to 4 questions per call; group everything you need at that point.
- Each question: a short header, the question in one sentence, and the
  evidence that makes it necessary (`F1.p2.L5`, `class_manifi.php:6611`).
- 2 to 4 options, mutually exclusive, each with its consequence in a few
  words. Put your recommendation FIRST and end its label with `(Recomendado)`.
  The developer can always type a different answer.
- Include an option such as "No se / consultar con negocio" when the developer
  may not know: that answer is valid and keeps the question open.

## After the answer - mandatory

1. Write the answer literally, with date and the question, in YOUR artifact:

| agent | where |
|---|---|
| lector | `REQUERIMIENTO_<carpeta>.md`, section `Aclaraciones` |
| analista | `ID_SPEC.md`: the decision where it belongs (Reglas globales, item, Ruta de desarrollo) AND one line in `Decisiones del desarrollador` |
| implementer, migrator | `_agentes/ACTA_<archivo>.md`, current run section |
| documenter | `_agentes/PRUEBAS.md` |

2. Only then continue. "No se / consultar" leaves the item open: `Preguntas
   abiertas` for the analista, `BLOQUEADO` for the implementer. Continue with
   everything that does not depend on it.
3. Never ask the same thing twice in a session. After two rounds on one topic
   without a usable answer, record it as open and move on.

## If the question tool is not available

(A non-interactive run.) Write the questions, with their options, in your
artifact where the answer would go, and stop that part of the work. Never
choose an option on the developer's behalf.
