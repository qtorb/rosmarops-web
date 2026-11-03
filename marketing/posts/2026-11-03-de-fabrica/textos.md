# «De fábrica»: textos (GTM-78)

Para Albert: los publica él en sus cuentas. Los corchetes llevan el fichero y el campo de cada afirmación, para que el advisor lo compruebe; se quitan al publicar. Todos los ficheros están en `observatory/data/agents/` de rosmarops-web (main). Gráficos: `chart.png` (ES) y `chart.en.png` (EN).

Canal recomendado primero: LinkedIn en castellano, porque es donde ya tienes el post de RosmarOps y este lo continúa con un dato que se entiende sin instalar nada.

---

## LinkedIn · ES (enlace al final)

En los tres agentes que evalúa RosmarOps, Claude Code, Cursor y Hermes Agent, el modo con el que arrancan de fábrica deja que otro modelo de IA decida lo que, si no, te preguntarían a ti. [claude-code.json default_mode.name = auto, who_decides = another_model · cursor.json default_mode.name = auto_review, who_decides = another_model, basis = documented_recommendation · hermes-agent.json default_mode.name = smart, who_decides = another_model]

He puesto en un gráfico qué hace cada uno sin preguntarte, según su documentación oficial: leer ficheros, escribirlos, ejecutar órdenes, sacar datos fuera y usar herramientas MCP. [capabilities[].action, default, source.url]

Claude Code lee tus carpetas de trabajo y ejecuta órdenes de solo lectura sin preguntar; para editar ficheros, pregunta. [claude-code.json cap-read-working-dirs, cap-readonly-commands, cap-edit]

Cursor lee de todo el ordenador desde su terminal aislado y escribe en las carpetas de trabajo sin preguntar; las órdenes, internet y MCP los pregunta. [cursor.json cap-sandbox-read, cap-write-workspace, cap-terminal, cap-network, cap-mcp]

Hermes Agent hace las cinco cosas sin preguntar; solo las órdenes que encajan con un patrón peligroso pasan antes por otro modelo. [hermes-agent.json cap-read-shell, cap-write-tools, cap-exec (note), cap-network, cap-mcp]

Y donde el gráfico dice «pregunta», de fábrica no te pregunta a ti: lo decide otro modelo. [default_mode.who_decides = another_model en los tres]

Es un mapa de lo que permite la configuración de fábrica, no un veredicto sobre ningún agente.

Si trabajas con agentes: ¿sabías con qué modo arranca el tuyo y quién responde cuando dice que pregunta?

https://rosmarops.com/es/metodologia/

## LinkedIn · ES (enlace en el primer comentario)

El mismo texto, sin la última línea. Primer comentario:

Cómo leemos cada fuente y qué significa cada casilla: https://rosmarops.com/es/metodologia/

---

## X · ES · post suelto (con chart.png)

En Claude Code, Cursor y Hermes Agent, el modo de fábrica deja que otro modelo de IA decida lo que, si no, te preguntarían a ti. Esto es lo que hace cada uno sin preguntarte, según su documentación oficial. https://rosmarops.com/es/metodologia/

[default_mode.name y who_decides de los tres; capabilities[] de los tres]

## X · ES · hilo de 3 (alternativa; chart.png en el primero)

1/ En los tres agentes que evalúa RosmarOps (Claude Code, Cursor y Hermes Agent), el modo con el que arrancan deja que otro modelo de IA decida lo que, si no, te preguntarían a ti. [default_mode de los tres]

2/ Sin preguntar, de fábrica: Claude Code lee tus carpetas de trabajo y ejecuta órdenes de solo lectura. Cursor lee todo el ordenador desde su terminal y escribe en el proyecto. Hermes Agent lee, escribe, ejecuta, sale a internet y usa MCP. [claude-code.json cap-read-working-dirs, cap-readonly-commands · cursor.json cap-sandbox-read, cap-write-workspace · hermes-agent.json cap-read-shell, cap-write-tools, cap-exec, cap-network, cap-mcp]

3/ Es un mapa de lo que permite la configuración de fábrica, no un veredicto. Cómo lo leemos, fuente a fuente: https://rosmarops.com/es/metodologia/

---

## LinkedIn · EN (link at the end)

In the three agents RosmarOps evaluates, Claude Code, Cursor and Hermes Agent, the mode they start in out of the box lets another AI model decide what they would otherwise ask you. [claude-code.json default_mode.name = auto, who_decides = another_model · cursor.json default_mode.name = auto_review, who_decides = another_model, basis = documented_recommendation · hermes-agent.json default_mode.name = smart, who_decides = another_model]

I put in one chart what each of them does without asking you, according to its official documentation: reading files, writing them, running commands, sending data out and using MCP tools. [capabilities[].action, default, source.url]

Claude Code reads your working folders and runs read-only commands without asking; to edit files, it asks. [claude-code.json cap-read-working-dirs, cap-readonly-commands, cap-edit]

Cursor reads the whole computer from its sandboxed terminal and writes in your working folders without asking; commands, the internet and MCP, it asks. [cursor.json cap-sandbox-read, cap-write-workspace, cap-terminal, cap-network, cap-mcp]

Hermes Agent does all five without asking; only commands that match a dangerous pattern go through another model first. [hermes-agent.json cap-read-shell, cap-write-tools, cap-exec (note), cap-network, cap-mcp]

And where the chart says "asks", out of the box it does not ask you: another model decides. [default_mode.who_decides = another_model in all three]

It is a map of what the factory configuration allows, not a verdict on any agent.

If you work with agents: did you know which mode yours starts in, and who answers when it says it asks?

https://rosmarops.com/methodology/

## LinkedIn · EN (link in the first comment)

The same text without the last line. First comment:

How we read each source and what each cell means: https://rosmarops.com/methodology/

---

## X · EN · single post (with chart.en.png)

In Claude Code, Cursor and Hermes Agent, the factory mode lets another AI model decide what they would otherwise ask you. This is what each one does without asking, according to its official documentation. https://rosmarops.com/methodology/

[default_mode.name and who_decides of the three; capabilities[] of the three]

## X · EN · 3-post thread (alternative; chart.en.png on the first)

1/ In the three agents RosmarOps evaluates (Claude Code, Cursor and Hermes Agent), the mode they start in lets another AI model decide what they would otherwise ask you. [default_mode of the three]

2/ Without asking, out of the box: Claude Code reads your working folders and runs read-only commands. Cursor reads the whole computer from its terminal and writes in your project. Hermes Agent reads, writes, runs commands, goes online and uses MCP. [claude-code.json cap-read-working-dirs, cap-readonly-commands · cursor.json cap-sandbox-read, cap-write-workspace · hermes-agent.json cap-read-shell, cap-write-tools, cap-exec, cap-network, cap-mcp]

3/ It is a map of what the factory configuration allows, not a verdict. How we read it, source by source: https://rosmarops.com/methodology/
