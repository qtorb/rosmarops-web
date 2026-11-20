# El plugin de Claude Code en los directorios (GTM-189 B)

Preparado el 20-11-2026 para que Albert decida y firme el envío. **No se ha enviado nada a ningún sitio.** Las páginas de cada directorio se leyeron el 20-11-2026.

Plugin: [qtorb/rosmarops-claude-code](https://github.com/qtorb/rosmarops-claude-code), leído en `main`:

- `.claude-plugin/plugin.json`: versión 0.2.0, licencia AGPL-3.0.
- `.claude-plugin/marketplace.json`: el repositorio es también su propio marketplace.
- `.claude-plugin/icon.png`, de 1024×1024.
- Un hook `SessionStart` que ejecuta `rosmarops session-check` (`hooks/hooks.json`).
- La skill `/rosmarops`, que ejecuta `rosmarops statusline` (`skills/rosmarops/SKILL.md`).
- El README tiene 223 palabras fuera de los bloques de código. El primer commit es del 17-11-2026.

Nunca «secure», «safe», «protects» ni sus traducciones, ni en lo que se envía ni aquí.

## Decidido (Albert, 20-11-2026)

1. **El directorio de Anthropic lo presenta Albert.** Pide un plan de pago de Claude (Pro, Max, Ultra, Team o Enterprise; en Team o Enterprise, solo el Owner o quien tenga el permiso Directory), una cuenta de GitHub conectada en claude.ai con permiso de escritura en el repositorio y un email de contacto. No he creado ni conectado nada.
2. **awesome-claude-code, a partir del 01-12-2026**, cuando el plugin cumple 14 días desde el primer commit (17-11). El formulario lo rellena una persona: lo envía Albert.
3. **Solo listas que enlazan.** No se presenta en las que copian el plugin dentro de su propio repositorio (ComposioHQ/awesome-claude-plugins): la copia se queda vieja, porque no se actualiza con nuestras versiones. Por eso esa lista no aparece en este documento.
4. **Claude Marketplaces ofrece una revisión prioritaria de pago, de 4 $.** No hace falta pagarla, porque la cola gratuita existe.
5. **skills.sh no admite envíos.** Lista las skills según la telemetría de su CLI (`npx skills add`). No se propone.

No se ha enviado nada a ningún directorio ni lista.

## 1. Directorio oficial de Anthropic

- **Dónde:** [claude.ai/directory](https://claude.ai/directory). Sirve plugins a Claude, a Cowork y a Claude Code.
- **Reglas:** [publicar](https://claude.com/docs/directory/publish), [enviar un plugin](https://claude.com/docs/plugins/submit.md) y [lista previa](https://claude.com/docs/plugins/pre-submission-checklist).
- **Cómo se envía:** desde el portal [claude.ai/directory/manage](https://claude.ai/directory/manage):
  1. Submit new › Plugin bundle.
  2. Repositorio.
  3. Validate.
  4. Datos del listado.
  5. Data handling.
  6. Compliance.
  7. Submit for review.

  Antes se puede comprobar en local con `claude plugin validate`. Los PR a `anthropics/claude-plugins-official` ya no se atienden, y `claude-plugins-community` es una copia de solo lectura.
- **Qué piden**, con lo que cumple el plugin hoy:

| Requisito | Estado del plugin |
| --- | --- |
| `plugin.json` con `name` en minúsculas, dígitos y guiones, de 64 caracteres como mucho | Cumple: `rosmarops` |
| README con 40 palabras o más fuera de los bloques de código | Cumple: 223 |
| `LICENSE` o campo `license` | Cumple: los dos |
| `hooks/hooks.json` válido, solo con eventos documentados | Cumple: `SessionStart` |
| SKILL.md con un `description` de texto | Cumple |
| Ninguna credencial; ningún `npx` o `uvx` sin versión fijada | Cumple: no hay ninguno |
| El README describe todo lo que el plugin ejecuta, envía o descarga | Cumple cuando se fusione qtorb/rosmarops-claude-code#4, que nombra `rosmarops session-check` y `rosmarops statusline` |
| Subir `version` en cada versión | Hay que hacerlo en cada envío |

- **Revisión:** validación automática y examen de seguridad en cada versión. Además, una persona revisa el primer listado. Si un primer envío falla el examen de seguridad, se rechaza.
- **Lo que no piden:** capturas, CHANGELOG, SECURITY.md ni temas de GitHub.
- **Qué se enviaría:**

| Campo | Texto | De dónde sale |
| --- | --- | --- |
| Nombre | RosmarOps | `plugin.json`, `displayName` |
| Descripción | Tells you in one line, when a Claude Code session opens, what changed in what your agents can do. | `plugin.json`, `description` |
| Descripción larga | Each time you open a Claude Code session, RosmarOps tells you in one line what changed in what your agents can do: new `allow` rules, hooks, MCP servers, skills or subagents, in your user settings or in the project you just opened. If nothing changed, it says nothing. | README del plugin, primer párrafo |
| Qué necesita | This plugin does not include RosmarOps. It calls the program you installed, so updates and the integrity check stay with the program. | README del plugin, «What it needs» |
| Data handling: ¿envía datos? | No. «It does not use the network.» | README del plugin, «What it does not do» |
| Data handling: qué lee | «It does not read the content of your files, your keys or your conversations.» | README del plugin, «What it does not do» |
| Qué ejecuta | When a Claude Code session starts, the plugin runs `rosmarops session-check`, which only reads Claude Code's settings and tells you what changed since you last opened the project. The `/rosmarops` command shows your last result and the command to run a full review in a terminal; to get that result it may run `rosmarops statusline`, which only reads the file your last review left. The plugin never starts a review, never uses the network and never changes your settings. | README del plugin, tercer párrafo (qtorb/rosmarops-claude-code#4, sin fusionar todavía) |
| Web | https://rosmarops.com | `plugin.json`, `homepage` |
| Licencia | AGPL-3.0 | `plugin.json`, `license` |

## 2. Marketplaces y listas de plugins de la comunidad

| Sitio | Cómo se entra | Qué piden | Cuenta o pago | Qué falta |
| --- | --- | --- | --- | --- |
| [Claude Marketplaces](https://claudemarketplaces.com/about) ([envío](https://claudemarketplaces.com/submit)) | Lo encuentra solo si el repositorio tiene un `marketplace.json` válido, o se envía entrando con GitHub | No dicen mínimo de estrellas; un editor revisa los listados nuevos | GitHub. Revisión prioritaria opcional de 4 $ | Nada de lo que piden. Puede que ya esté listado: no lo he buscado |
| [Chat2AnyLLM awesome-claude-plugins](https://chat2anyllm.github.io/awesome-claude-plugins/) | Sigue los marketplaces listados en `Chat2AnyLLM/awesome-repo-configs`; la página no dice cómo entrar | No lo dicen | No lo dicen | No se sabe |

Texto para Claude Marketplaces, si pide descripción: «Tells you in one line, when a Claude Code session opens, what changed in what your agents can do.» (`plugin.json`).

## 3. Listas de Claude Code

| Sitio | Cómo se entra | Qué piden | Qué falta |
| --- | --- | --- | --- |
| [hesreallyhim/awesome-claude-code](https://github.com/hesreallyhim/awesome-claude-code/blob/main/CONTRIBUTING.md) | Solo por el formulario de *issue* en la web; no admite PR ni `gh` | Lo envía una persona. Una línea de descripción, «not a sales pitch», sin emojis. El repositorio necesita 14 días desde el primer commit con desarrollo activo, o 100 estrellas | **Hasta el 01-12-2026 no cumple los 14 días** (primer commit el 17-11). No hay categoría de plugins: encaja en Hooks. El formulario no lo he podido abrir; sus campos salen de una copia de terceros |
| [jqueryscript/awesome-claude-code](https://github.com/jqueryscript/awesome-claude-code#contribution-guidelines) | No lo dicen: la sección está «Under Construction» | Formato de línea: `[**name**](url) - (N ⭐) - description` | Las reglas no se conocen |

Texto para hesreallyhim/awesome-claude-code:

- **Nombre:** RosmarOps for Claude Code (título del README del plugin).
- **Descripción:** «Tells you in one line, when a Claude Code session opens, what changed in what your agents can do.» (`plugin.json`).
- **Categoría:** Hooks.
- **Por qué es útil:** «If nothing changed, it says nothing.» (README del plugin, primer párrafo).

Si el formulario pide algo más, es **FALTA TEXTO**.

## Lo que no se ha podido leer

- El formulario de awesome-claude-code (robots.txt lo bloquea).
- La política del directorio de Anthropic (Software Directory Policy).
- El CONTRIBUTING de buildwithclaude. Además, buildwithclaude no admite repositorios externos.
- Las reglas de aitmpl.com.
