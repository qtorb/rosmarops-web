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
| El README describe todo lo que el plugin ejecuta, envía o descarga | **Falta:** no nombra las órdenes `rosmarops session-check` ni `rosmarops statusline` |
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
| Qué ejecuta | **FALTA TEXTO.** Hace falta una frase que nombre `rosmarops session-check` (al abrir una sesión) y `rosmarops statusline` (con `/rosmarops`). Tiene que estar antes en el README del plugin. | — |
| Web | https://rosmarops.com | `plugin.json`, `homepage` |
| Licencia | AGPL-3.0 | `plugin.json`, `license` |

## 1 bis. Bloqueos del portal y organización verificada (GTM-192, lectura del 20-11-2026)

El portal (claude.ai/directory/manage) bloquea el envío de qtorb/rosmarops-claude-code por dos motivos, según lo que vio Albert:

1. «Hooks of type command accepted only from Verified organizations».
2. Hay ficheros fuera de la lista permitida (`tests/check-no-network.sh`) y un aviso de `tests/` que nombra `.claude-plugin/icon.png`.

No se ha solicitado nada, no se ha creado ninguna cuenta ni se ha enviado nada.

### (a)-(c) Organización verificada: la documentación pública no la describe

He leído estas páginas el 20-11-2026:
- Publish to the directory: https://claude.com/docs/directory/publish.md
- Submit your plugin: https://claude.com/docs/plugins/submit.md
- Plugin pre-submission checklist: https://claude.com/docs/plugins/pre-submission-checklist.md
- Track your directory submission: https://claude.com/docs/directory/submission-status.md
- Connector verification: https://claude.com/docs/connectors/verification.md
- Plugins: https://claude.com/docs/plugins
- El índice entero: https://claude.com/docs/llms.txt

**Ninguna habla de una «organización verificada»,** ni de que los hooks de tipo `command` se acepten solo de ellas. El índice no tiene ninguna página sobre verificar una organización, verificar un dominio o verificar un publicador.

Esto es lo más cercano que sí dicen:
- **Quién puede enviar:** cualquiera con plan de pago de Claude (Pro, Max, Team o Enterprise). En Pro y Max, desde la propia cuenta y sin rol. En Team y Enterprise, un Owner, o en Enterprise quien tenga el permiso Directory. Los planes Free no pueden enviar. El listado pertenece a la organización desde la que se envía, y la primera organización que envía una carpeta de un repositorio se queda con ese listado. No hay programa de socios al que apuntarse antes. Fuente: publish.md, «Confirm you can submit to the directory».
- **La etiqueta «Verified» es de conectores MCP, no de organizaciones.** No se solicita: la decide Anthropic durante la revisión. Fuente: publish.md, «Prepare for review», y connectors/verification.md, «List your own connector».
- **Hooks:** la lista de comprobación solo pide que `hooks/hooks.json` sea JSON válido y use los eventos y tipos de la referencia de hooks. No menciona ninguna restricción por tipo de organización. Fuente: pre-submission-checklist.md, «Hooks, skills, commands, and agents».
- **Plazos:** «Review time isn't fixed» (submission-status.md). No hay nada sobre cuánto tarda verificar una organización.
- **Contacto para una submission de plugin:** el menú del plugin en el portal («Get help» o «Contact Anthropic»), o `directory@anthropic.com`, donde las respuestas pueden tardar (submission-status.md, «Contact Anthropic about a submission»).

**Por tanto, sin respuesta en la documentación:**
- qué es una organización verificada y qué pide (entidad legal, dominio, documentos, plan, coste);
- cómo se solicita;
- si puede verificarse una organización de una persona o una cuenta personal;
- cuánto tarda.

Lo único que hay es el mensaje del portal, que solo ve Albert con su cuenta. **Condición de parada de GTM-192: se para aquí.** Lo que se puede hacer:
1. Albert abre el mensaje del portal y mira si enlaza a una página o a un formulario.
2. Si no enlaza a nada, se pregunta en «Get help» o «Contact Anthropic» desde el plugin, o en `directory@anthropic.com`.

Dos páginas no se han podido leer en esta sesión porque pedían aprobación y no había nadie para darla:
- https://claude.com/docs/directory (la portada de esa sección);
- la Software Directory Policy: https://support.claude.com/en/articles/13145358-anthropic-software-directory-policy

Quedan por leer; podrían tratar el tema.

### (d) Que el envío contenga solo la carpeta del plugin

**Lo que dice la documentación:**
- La carpeta del plugin es la que contiene `.claude-plugin/plugin.json`, y puede estar en la raíz o en una subcarpeta. Quien instala recibe solo esa carpeta (pre-submission-checklist.md, «Review what validation and the scan check»).
- En el paso Source, «Plugin path (optional)» es esa carpeta, y «Branch or tag (optional)» es la rama o etiqueta que el directorio sigue (submit.md, «Enter the source and validate»).
- «If the plugin is one folder in a larger repository, give that folder as the plugin path when you submit; the directory reads and scans only that folder» (submit.md, «Update a published plugin»).
- El repositorio y la carpeta no se pueden cambiar después de enviar (submit.md, «Change the tracked branch or tag»).

**Cómo está hoy el repositorio** (`main`): todo en la raíz.
- Del plugin: `.claude-plugin/plugin.json`, `.claude-plugin/icon.png`, `.claude-plugin/marketplace.json`, `hooks/hooks.json`, `skills/rosmarops/SKILL.md`, `README.md` y `LICENSE`.
- De desarrollo: `tests/check-no-network.sh`, `tests/check-shape.sh` y `.github/workflows/ci.yml`.

**Opción A: el plugin en una subcarpeta de `main`.** El contenido de los ficheros del plugin no cambia; solo se mueven.

| Queda dentro de `plugin/` | Queda en la raíz |
| --- | --- |
| `.claude-plugin/plugin.json` y `.claude-plugin/icon.png` | `tests/`, `.github/workflows/ci.yml` y `LICENSE` |
| `hooks/hooks.json` y `skills/rosmarops/SKILL.md` | `.claude-plugin/marketplace.json`, con `"source": "./plugin"` en lugar de `"./"` |
| `README.md` (el portal pide un README de 40 palabras como mínimo dentro de la carpeta del plugin) y una copia de `LICENSE` (la pide dentro de la carpeta) | un `README.md` corto que apunte a `plugin/README.md`, para quien llegue al repositorio |

Lo que cambia fuera del plugin:
- **Pruebas:** `tests/check-shape.sh` y `tests/check-no-network.sh` tienen que mirar dentro de `plugin/`: hoy hacen `cd "$(dirname "$0")/.."` y leen la raíz.
- **CI:** `ci.yml` pasa a validar `claude plugin validate --strict ./plugin`. La validación del marketplace sigue en la raíz.
- **Quien ya lo instaló** con `/plugin marketplace add qtorb/rosmarops-claude-code` sigue funcionando, porque el marketplace sigue en la raíz y apunta a `./plugin`. Esto conviene probarlo antes de fusionar.
- **En el portal:** Repository `qtorb/rosmarops-claude-code`, Plugin path `plugin`, Branch vacío (sigue `main`).

**Opción B: una rama aparte con solo el plugin** (por ejemplo `directory`). `main` no cambia. La rama lleva solo `.claude-plugin/plugin.json`, `.claude-plugin/icon.png`, `hooks/`, `skills/`, `README.md` y `LICENSE`, y en el portal se pone como Branch. El coste es mantenerla igual que `main` en cada versión, porque el directorio publica lo que hay en esa rama. Si no se hace a mano, hace falta un paso de publicación que la actualice.

**Lo que no resuelve ninguna de las dos:**
- **El bloqueo 1 sigue.** El hook de `SessionStart` es de tipo `command`, y sin ese hook el plugin no hace nada.
- **Dos riesgos solo para la opción A,** porque la lista de comprobación es más estricta con los plugins en subcarpeta:
  - Los comandos de hook tienen que escribir cada ruta completa desde `${CLAUDE_PLUGIN_ROOT}`. El nuestro, `rosmarops` con `session-check`, no lleva ruta: es un programa que ya está en el PATH. La documentación no dice qué pasa con un comando sin ruta, así que puede bloquear o no. Hay que pasarle «Validate».
  - Si el validador no puede seguir lo que ejecuta un hook, lo retiene para un revisor («Scripts the validator couldn't follow»).

  La opción B mantiene el plugin en la raíz de su rama y evita los dos.
- **El aviso que nombra `.claude-plugin/icon.png`:** desde aquí no veo su texto exacto. PNG es un tipo permitido, y ningún fichero de `tests/` nombra el icono. Haría falta el texto literal del portal.

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
