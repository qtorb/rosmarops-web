# Observatory (branch `observatory`, not deployed)

- `data/agents/*.json`: copy of `qtorb/rosmarops-vigil` @ 486dd44, `data/observatory/agents/`. Validated in CI against `schema/observatory.v1.schema.json` (same commit).
- `i18n/{en,es,ca}.json`: fixed texts of the templates. EN is the source; ES and CA must have exactly the same keys (the build stops otherwise). Verified by the product advisor and signed by Albert on 2026-10-28 (commit 0d29ab1 texts).
- `build.py`: standard-library generator. `python3 observatory/build.py` writes `site/observatory/`, `site/es/observatorio/`, `site/ca/observatori/` and the JSON files. An agent page is generated only when the agent has at least one entry in `changes` or `ratings`. Ratings are never rendered.
- Every page carries `noindex` and nothing is added to sitemaps or `llms.txt` while `NOINDEX = True`.
- `tests/fixture/`: one synthetic agent, used only by CI to render the agent page template. Never copied to `site/`.
- The deploy workflow only runs on `main` and uploads an explicit file list, so nothing here reaches the server.
