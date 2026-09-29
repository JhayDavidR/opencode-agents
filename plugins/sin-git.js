// Git lo ejecuta SOLO el desarrollador. Este plugin es la garantia: los permisos
// de opencode.json y de cada agente comparan patrones contra el comando completo,
// y la documentacion de OpenCode no dice como trata un comando compuesto
// ("cd x;git commit", "python -c \"...git...\""). Aqui se revisa el texto entero
// antes de ejecutar cualquier comando de bash, para todos los agentes (tambien
// build, plan y los subagentes).
//
// Los scripts del flujo no necesitan git: la rama y el commit se leen de los
// archivos de .git (id_workspace.py) y el control de cambios lo lleva REGISTRO.jsonl.

// git o gh como palabra de comando: al inicio o despues de espacio, ; & | ( ` " '
// y seguido de espacio, fin o comilla. ".git" (carpeta) y "digit" no coinciden.
const GIT = /(^|[\s;&|(`"'])(git|gh)(\.exe)?(?=$|[\s"'`;&|)])/i

export const SinGit = async () => {
  return {
    "tool.execute.before": async (input, output) => {
      if (input.tool !== "bash") return
      const comando = String((output.args && output.args.command) || "")
      if (GIT.test(comando)) {
        throw new Error(
          "BLOQUEADO: los comandos de git los ejecuta solo el desarrollador. " +
          "No lo intentes de otra forma: la rama y el commit salen de " +
          "'id_workspace.py estado' y los cambios de REGISTRO.jsonl. " +
          "Si el paso necesita git, dile al desarrollador el comando exacto."
        )
      }
    },
  }
}
