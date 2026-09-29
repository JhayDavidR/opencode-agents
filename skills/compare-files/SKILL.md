---
name: compare-files
description: >
  Compares two legacy PHP files (development vs production) and generates a 
  unified diff showing only the changed lines. 
  Strictly preserves ISO-8859-1 (latin1) encoding to avoid character corruption.
---

# compare-files

Generates a unified diff between the development version and the production version.

## Required Inputs

| Parameter   | Description                                      |
|-------------|--------------------------------------------------|
| `file_dev`  | Full path to the modified file (development)     |
| `file_prod` | Full path to the original file (production)      |

## Execution

```bash
python "<skill_dir>/compare_files.py" "<file_dev>" "<file_prod>"
```
