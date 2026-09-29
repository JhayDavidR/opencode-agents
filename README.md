# opencode-agents

Orquestación de agentes de [OpenCode](https://opencode.ai) para desarrollar sobre **código
espagueti heredado**: Avansat TMS, con PHP 5.4, jQuery, archivos en ISO-8859-1, consultas SQL
dentro de las vistas y archivos de miles de líneas sin pruebas automáticas.

Esta carpeta es la configuración `.opencode` completa: agentes, comandos, skills con sus
scripts, plantillas y protecciones. Se clona dentro de la carpeta de trabajo y OpenCode la
carga al arrancar.

---

## 1. El problema: un modelo de lenguaje frente a código espagueti

Si a un asistente de IA se le pide "implementa este requerimiento" sobre un sistema heredado,
estos son los errores que más se repiten:

| Riesgo | Qué pasa en la práctica |
|---|---|
| Codificación | El editor nativo guarda en UTF-8 un archivo ISO-8859-1 y rompe todos los acentos del sistema |
| Reescritura | El modelo "mejora" el código vecino: renombra, extrae o reordena, y el diff deja de ser revisable |
| Rutas y símbolos inventados | Cita funciones o líneas que no leyó, o edita un archivo equivocado |
| Contexto perdido | Al cambiar de sesión se olvidan las decisiones, y el siguiente paso contradice al anterior |
| Lectores olvidados | Cambiar una tabla rompe informes y exportables que la leen desde otros módulos |
| Aplicación parcial | Una edición queda a medias y el archivo termina sin compilar |
| Sin trazabilidad | Nadie puede reconstruir qué se cambió, por qué, ni con qué respaldo |

## 2. La solución: orquestación con el estado en disco

No hay un LLM "director" encima de los demás. La orquestación se apoya en cinco reglas:

1. **El estado vive en archivos, no en el chat.** Cada id tiene una carpeta `_agentes/` con
   la especificación (`ID_SPEC.md`), las actas, los lotes aplicados y un registro
   (`REGISTRO.jsonl`). Se puede cambiar de sesión, de modelo o de equipo sin perder nada.
2. **Un router determinista dice qué sigue.** `id_workspace.py siguiente <id>` lee la carpeta
   y responde con el comando exacto del próximo paso. Es un script de Python, así que no gasta
   tokens ni adivina.
3. **Cada paso tiene un solo responsable.** Cada comando está asignado a un agente con permisos
   mínimos: el analista especifica pero no escribe código, el implementador escribe pero no
   certifica su propio alcance, y así con los demás.
4. **Escritura todo o nada.** Ningún agente edita PHP o JS directamente. Todo pasa por
   `apply_blocks.py`, que funciona así:
   - aplica lotes de bloques *buscar/reemplazar* que deben anclar de forma única;
   - conserva la codificación y los finales de línea;
   - guarda un respaldo del original;
   - corre `php -l` o `node --check`;
   - valida que los comentarios cumplan el estándar;
   - deja constancia en `REGISTRO.jsonl`.
5. **El desarrollador decide.** La ruta de desarrollo se confirma al inicio y las dudas llegan
   como preguntas con opciones. Git lo ejecuta solo el desarrollador.

```
 documento (PDF/Word/mockups)
        │  /leer        lector ──────────► REQUERIMIENTO_<id>.md (R1..Rn con cita literal)
        ▼
 /spec  analista ─── preguntas ───► tú ──► ID_SPEC.md (ruta confirmada, ítems, decisiones, trazabilidad)
        │
        │  (opcional) /scope /mapa /impacto   avansat_expert ─► SCOPE / MAP / IMPACTO.json
        ▼
 /implementar <id> <archivo>   implementer ─► BLOQUES ─► apply_blocks.py (todo o nada + lint + respaldo)
        │                                                 └─► REGISTRO.jsonl, ACTA_<archivo>.md
        ▼
 prueba en navegador (tú) ── falla puntual ──► /cambio ─► /implementar ... items N
        ▼
 /documentar  documenter ─► manual técnico       /commit ─► mensaje y PR       /reporte ─► cierre del día

 En cualquier momento: /siguiente <id>  (guia + router: "¿qué sigue?")
```

## 3. Agentes y comandos

| Comando | Agente | Para qué |
|---|---|---|
| `/siguiente [id]` | guia | Qué sigue y con qué comando |
| `/leer <id> ["ruta"]` | lector | Documento con imágenes → requerimiento numerado |
| `/spec <id>` | analista | Ruta de desarrollo, preguntas y `ID_SPEC.md` |
| `/cambio <id> <ajuste>` | analista | Ajuste pequeño a un spec existente, sin releer código |
| `/scope`, `/mapa`, `/impacto`, `/equivalencia` | avansat_expert | Alcance, flujo entre archivos, impacto en lectores y porte entre módulos |
| `/implementar <id> [archivo] [items N]` | implementer | Código nuevo, archivo por archivo, o solo los ítems que cambiaron |
| `/migrar`, `/migrar-curado`, `/comentarios` | migrator | Llevar cambios de una copia vieja a una limpia y corregir comentarios |
| `/comparar <a> <b>` | comparator_agent | Depurar o comparar versiones |
| `/documentar <id> <qué se probó>` | documenter | Manual técnico con trazabilidad |
| `/commit <id> [feat\|fix]` | commits | Mensaje de commit y de pull request (git lo corres tú) |
| `/reporte [horas]` | time_report | Reporte del día a partir de la bitácora |

El detalle de cada paso, los recorridos por tipo de id (nuevo, porte, migración), los modelos
sugeridos y los costos están en **[FLUJO.md](FLUJO.md)**.

## 4. Instalación y configuración

### Requisitos

| Qué | Para qué | Obligatorio |
|---|---|---|
| OpenCode (probado con 1.18.x) | Ejecutar los agentes | Sí |
| Credencial de un proveedor de modelos | Los agentes `lector`, `guia` y `commits` traen fijo `zai-coding-plan/*` | Sí |
| Python 3 en el PATH | Todos los scripts de `skills/` | Sí |
| Node en el PATH | Lint JS (`node --check`) | Recomendado |
| PHP 5.4 en el PATH | Lint PHP con la versión real de producción (`php -l`) | Recomendado |
| Pillow (`pip install pillow`) | Extraer imágenes de los PDF para `/leer` | Opcional |

### Pasos (una vez por equipo)

1. **Clonar como `.opencode`** dentro de la carpeta desde la que abrirás OpenCode, que es la
   que agrupa tus repos y tus ids:

   ```bash
   cd D:/MiEspacioDeTrabajo
   git clone <url-del-repo> .opencode
   ```

2. **Autenticar el proveedor de modelos:**

   ```bash
   opencode auth login
   opencode auth list
   ```

   Si usas otro proveedor, cambia la línea `model:` de `agents/lector.md`, `agents/guia.md` y
   `agents/commits.md`. El lector necesita un modelo que acepte imágenes y PDF.

3. **Registrar tus carpetas.** Ninguna ruta viene escrita en los agentes: se guardan en tu
   perfil (`%USERPROFILE%\.opencode_oet_rutas.json`), fuera del repo.

   ```bash
   python .opencode/skills/id-workspace/id_workspace.py configurar --ids "D:/MiEspacioDeTrabajo/ids" --repo sate_standa="D:/MiEspacioDeTrabajo/sate_standa" --repo ws_rndc="D:/MiEspacioDeTrabajo/ws_rndc"
   ```

   Para comprobarlo:

   ```bash
   python .opencode/skills/id-workspace/id_workspace.py raices
   ```

4. **Abrir OpenCode desde la carpeta que contiene `.opencode`**, no desde dentro de un repo
   ni desde la carpeta de un id. Después de cambiar algo en `.opencode`, reinicia OpenCode:
   la configuración se lee al arrancar.

5. **Primer uso:**

   ```bash
   python .opencode/skills/id-workspace/id_workspace.py init "D:/MiEspacioDeTrabajo/ids/09_Septiembre/580000"
   ```

   Luego, dentro de OpenCode: `/siguiente 580000`.

## 5. Protecciones incluidas

- **Git solo lo ejecuta el desarrollador.** Hay tres capas: `opencode.json`, el permiso de cada
  agente y el plugin `plugins/sin-git.js`, que revisa el texto de cada comando antes de
  ejecutarlo.
- **Nadie edita PHP, JS, HTM o INC con el editor nativo.** `opencode.json` lo prohíbe a todos
  los agentes; solo `apply_blocks.py` escribe esos archivos.
- **`apply_blocks.py` tiene límites:**
  - solo escribe los *Archivos objetivo* del spec;
  - nunca escribe con el repo en `master` o `main`;
  - avisa si el archivo cambió fuera del flujo.
- **`protected_paths.txt`** lista rutas donde ningún script escribe. Sin ese archivo, los
  scripts de escritura se niegan a escribir.
- **Estándar de comentarios:** un comentario con referencias del flujo (ítems, requisitos,
  nombres de agentes) se rechaza con `ESTANDAR`.

## 6. Estructura del repositorio

```
agents/          definición de cada agente (modo, modelo, permisos, instrucciones)
commands/        comandos /xxx y el agente al que se asignan
skills/          instrucciones SKILL.md y scripts Python (router, apply_blocks, lectura, bitácora...)
templates/       plantilla del ID_SPEC y prompt para análisis en un chat externo
plugins/         sin-git.js
opencode.json    permisos globales
protected_paths.txt
FLUJO.md         manual de uso completo
```

No se versionan (ver `.gitignore`):
- lo que OpenCode instala al arrancar (`node_modules`, `package.json`);
- la caché de Python;
- la bitácora personal (`logs/`);
- temporales;
- material propio de un id o ya retirado.

## 7. Cómo contribuir

- Si cambias un agente o un script, prueba el flujo completo con un id real antes de subirlo:
  `/siguiente`, `/implementar` en simulación y `apply_blocks.py` sin `--apply`.
- Las reglas nuevas van al agente responsable del paso y, si se pueden verificar
  automáticamente, al script (por ejemplo, la guardia `ESTANDAR` de `apply_blocks.py`).
- Documenta el cambio en `FLUJO.md`.
