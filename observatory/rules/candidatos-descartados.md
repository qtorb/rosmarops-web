# Candidatos que salen del Observatorio

Registro interno, no se publica en la web. Aquí va cada candidato que sale de `observatory/data/candidates.json` porque no cumple una de las cuatro condiciones de entrada (i18n `index.criteria_1`–`criteria_4`), con su motivo y su fuente. Si un motivo deja de valer (por ejemplo, un agente añade una forma de exposición propia), se vuelve a mirar y, si cumple, se abre su ficha.

Decidido por Albert el 06-11-2026 (GTM-98).

| Candidato | Fabricante | Condición que no cumple | Motivo | Fuente |
|---|---|---|---|---|
| Microsoft Agent Framework | Microsoft | 4 | Es el sucesor oficial de AutoGen, que ya tiene ficha (`autogen.json`) y lee el mismo repositorio (F25, `microsoft/agent-framework`). No añade una forma de exposición que no esté cubierta. | https://github.com/microsoft/autogen (README: «Microsoft Agent Framework (MAF) is the enterprise‑ready successor to AutoGen») |
| Mistral Vibe | Mistral AI | 4 | Lo propio que se encontró es la telemetría activa por defecto y los ajustes de organización que llegan desde la nube; las dos cosas ya están cubiertas por otros agentes del Observatorio. | https://github.com/mistralai/mistral-vibe (README y CHANGELOG.md, 3.0.4) |
| Open Interpreter | Open Interpreter | 4 | La versión actual es un fork de Codex («Open Interpreter is a fork of OpenAI's Codex»), que ya tiene ficha. Compartir `AGENTS.md` y `~/.agents/skills` con otros agentes ya está cubierto. | https://github.com/openinterpreter/open-interpreter (README) |
| Pi | Earendil Inc. (repositorio earendil-works/pi) | 4 | Un agente sin sistema de permisos propio, ampliable con extensiones de npm o git. OpenClaw, que ya tiene ficha, está construido sobre Pi. | https://github.com/earendil-works/pi (README: «See OpenClaw for a real-world integration»; «Pi does not include a built-in permission system») |

Pi: el autor es Mario Zechner y la empresa, Earendil Inc. (pi.dev, earendil.com); «earendil-works» es solo el nombre de la organización en GitHub y npm. El repositorio antiguo `badlogic/pi-mono` sigue respondiendo con las mismas etiquetas.
