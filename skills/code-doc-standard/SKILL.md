---
name: code-doc-standard
description: >
  Single source of the rules for id comments written into legacy PHP/JS source
  files (marker shape, when to comment, budget, forbidden content) and for
  search_block anchors. Load it once before writing or reviewing any
  replace_block that carries comments.
---

# code-doc-standard

Mark BLOCKS, not lines. Comment DECISIONS, not code. The reader is a colleague
opening this file in two years, not a reviewer of this run.

Why it exists, so nobody "improves" it away: the id must stay greppable for
years, but per-line markers turn a file into noise. This project once reached
92 markers in a single JS file.

## Scope of the marker - decide BEFORE writing any comment

`ID <id>:` means "this line exists because of development <id>". It is a
traceability tag, not a signature.

- A change that belongs to the id carries the marker.
- A change that does NOT belong to the id (incidental bug, regression guard,
  fix of pre-existing behaviour) carries NO marker and normally no comment. At
  most ONE short plain line saying what the line does, never naming the id.
- Symbol names NEVER carry the id (`foo566647` is forbidden). Name it for what
  it does.
- If you cannot say in one phrase why a line belongs to the id, it does not.

## When to comment - exhaustive list

1. **New function or method**: no INICIO/FIN pair. Docblock in the style the
   neighbouring functions use, with one line `ID <id>: <what it does>`.
2. **New/modified fragment of 5 executable lines or fewer** inside an existing
   function: ONE line above it, no closing line: `// ID <id>: <what it does>`.
3. **More than 5 executable lines**: same header, optionally ONE extra context
   line, closed by exactly `// ---` (nothing else on that line; never "FIN" or "FIN ID").
   Comments and blank lines do not count as executable.
4. **Existing line modified**: comment it only if reverting it silently changes
   behaviour a user notices, OR it compensates for something in ANOTHER file,
   OR a competent reader would "fix" it back. Otherwise no comment.
5. **New variable, assignment, rename, reorder**: no comment.
6. **Duplicated logic**: the header states the RULE in the domain's words, not
   the operands, and does not list the file/line of every twin.
7. **Same explanation N times** in one function: written once, at the first
   occurrence.
8. **Prefix**: only `ID <id>:`. Never "Ajuste Req", "Requerimiento ID",
   "REQ ID", "ID <id> -", "--- INICIO".

In PHP use the comment style the surrounding lines use (`//` or `#`); in
HTML/HTM templates use `<!-- ID <id>: ... -->`.

## Budget

One marker per functional block of the id. A file with more than ~25 markers,
or more than one comment line per eight lines of added code inside a block,
did not apply this standard: collapse before applying.

## Never

- restate what the next line plainly does;
- commented-out code, TODO, debug leftovers, author names, dates;
- rows of dashes as separators;
- first person or narrating the work ("se corrigio", "se agrego", "ahora se
  valida"). Present tense, describing the code as it stands;
- any character outside ISO-8859-1: accented letters and enye are fine;
  typographic quotes, em dashes and ellipsis are not (apply_blocks rejects them);
- anything from the agent tooling in source comments: TRANSFER_BLOCK,
  search_block, ID_SPEC, agent, prompt, item, guardrail, or any agent name.
  Restate a rule in the domain's own words instead ("no llamar a
  CalculateTotal aqui: vuelve a disparar el flete sugerido SICETAC").

## Anchor rule for search_block

Never anchor on a line made only of braces or whitespace: include at least one
line with a unique identifier (variable, call, case label). Use the minimum
number of lines that makes the block appear exactly once. Copy it from a
`read_file.py` output of THIS session, minus the `NNNNNN | ` prefix - never
from memory.
