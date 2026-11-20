# Dónde presentar el repositorio de plantillas (GTM-188 §5)

Preparado el 20-11-2026 para cuando la exportación de BV-266 haya llenado `qtorb/rosmarops-templates`. **No se ha enviado nada a ningún sitio.** Las páginas se leyeron el 20-11-2026.

La skill irá en `skills/rosmarops-templates/SKILL.md`, con `name` y `description`, cuando la exportación de BV-266 la deje (hoy el repositorio solo tiene LICENSE y, en el PR #1, el README y `templates/`). La licencia es MIT.

Decidido por Albert el 20-11-2026: el directorio de Anthropic lo presenta él; solo se presenta en listas que enlazan, no en las que copian el contenido en su propio repositorio, porque la copia se queda vieja (por eso ComposioHQ/awesome-claude-skills no está en la tabla); y no se envía nada hasta que se firme.

| Sitio | Cómo se entra | Qué piden | Qué le falta hoy al repositorio |
| --- | --- | --- | --- |
| [Directorio de Anthropic](https://claude.com/docs/directory/publish) ([enviar un plugin](https://claude.com/docs/plugins/submit.md)) | Portal [claude.ai/directory/manage](https://claude.ai/directory/manage). Las skills no se envían solas: van en un paquete. Una carpeta con `skills/<name>/SKILL.md` y sin `plugin.json` pasa con una nota y se lista solo para Claude Code | Plan de pago de Claude. GitHub conectado en claude.ai. README de 40 palabras o más fuera de los bloques de código. LICENSE. Nada de credenciales. Revisión automática y, la primera vez, de una persona | Todo el contenido, porque está vacío. Un `plugin.json` si se quiere más que «solo Claude Code»; no está en el brief. La cuenta de pago la decide Albert |
| [anthropics/skills](https://github.com/anthropics/skills) | No dice cómo pueden enviar los de fuera (no tiene CONTRIBUTING) | `name` y `description` en el SKILL.md | No hay vía de envío |
| [VoltAgent/awesome-agent-skills](https://github.com/VoltAgent/awesome-agent-skills/blob/main/CONTRIBUTING.md) | PR «Add skill: author/skill-name» | Entrada `- **[author/skill-name](url)** - …`, de 10 palabras o menos. Uso real. «Brand new skills that were just created are not accepted.» | Contenido y uso real: hoy no se admite |
| [travisvn/awesome-claude-skills](https://github.com/travisvn/awesome-claude-skills/blob/main/CONTRIBUTING.md) | PR, una skill por PR | **10 estrellas como mínimo.** Descripción de 1 o 2 frases. Cierran los PR hechos con ayuda de IA | Contenido y 10 estrellas. El PR lo tiene que hacer Albert |
| [hesreallyhim/awesome-claude-code](https://github.com/hesreallyhim/awesome-claude-code/blob/main/CONTRIBUTING.md) | Solo el formulario web de *issue*, rellenado por una persona | 14 días desde el primer commit con desarrollo activo, o 100 estrellas. Una línea, «not a sales pitch». Categoría Agent Skills | Contenido y 14 días de historia |
| [skills.sh](https://www.skills.sh/docs/faq) | No hay envío: lista según la telemetría de `npx skills add` | — | No se propone: depende de telemetría |

## Textos que se enviarían

Solo frases ya escritas: la `description` de la skill y la primera línea del README del repositorio (las dos están en los briefs de BV-266 y GTM-188):

- Descripción de una línea: «Settings that make your AI coding agent ask before it acts.» (README).
- Descripción de la skill: «Apply a RosmarOps permission template to this project so the agent asks before it acts.» (SKILL.md, primera frase de `description`).
- Descripción corta para VoltAgent (10 palabras o menos): «Settings that make your AI coding agent ask before acting» (dada por el advisor el 20-11).

## Cuándo se puede presentar en las listas con condiciones

Primer commit del repositorio: 20-11-2026. Ninguna se cumple antes de que BV-266 llene el repositorio.

| Lista | Condición | Fecha más temprana |
| --- | --- | --- |
| hesreallyhim/awesome-claude-code | 14 días desde el primer commit con desarrollo activo, o 100 estrellas | 04-12-2026, si para entonces ya está la exportación; si no, el día en que llegue a 100 estrellas |
| travisvn/awesome-claude-skills | 10 estrellas como mínimo. El PR lo hace Albert | El día en que el repositorio tenga 10 estrellas; no tiene fecha fija |
| VoltAgent/awesome-agent-skills | Uso real; no admiten skills recién creadas | No la fijan. Lo más pronto: cuando haya uso real que enseñar, no antes de la exportación de BV-266 |
| Directorio de Anthropic | Contenido, README de 40 palabras, LICENSE. Lo presenta Albert | El día en que BV-266 llene el repositorio |
