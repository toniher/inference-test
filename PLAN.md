# Plan: test pipeline for actions/ai-inference (v3 only)

## Context
Empty repo (`toniher/inference-test`, only `.gitignore`). Goal: GitHub Actions workflows exercising `actions/ai-inference@v3`: simple prompts first, then MCP (dummy local server, GitHub MCP, eventually edammcp).

v3 = Copilot CLI only. Needs `npm i -g @github/copilot` + `COPILOT_GITHUB_TOKEN` (PAT with "Copilot Requests", account with Copilot). Action runs `copilot -p … -s --no-ask-user`; no MCP inputs, but Copilot CLI reads `~/.copilot/mcp-config.json` (any MCP server) and has GitHub MCP built in. Tools gated by `copilot-allow-tools` (→ `--allow-tool`, e.g. `dummy` or `dummy(secret_word)`).

## Files to create
```
.github/workflows/ai-inference.yml         # phases 1–2
.github/workflows/edam-mcp.yml             # phase 3
.github/actions/setup-copilot/action.yml   # composite: setup-node, npm i -g @github/copilot, fail fast if COPILOT_PAT empty
.github/prompts/pong.prompt.txt            # "Reply with exactly the word PONG"
.github/prompts/summary.prompt.yml         # messages + {{repo}}/{{readme}} templates, model: gpt-4.1
.github/prompts/system.txt                 # "Be terse. No markdown."
mcp/dummy_server.py                        # FastMCP stdio server
mcp/requirements.txt                       # mcp
mcp/edam_smoke.py                          # direct MCP client test for edammcp (no LLM)
fixtures/meta.yml                          # sample nf-core-style module description
scripts/assert_contains.sh                 # assert_contains <file> <regex> [--not]; prints response, exits 1 on miss
README.md                                  # secrets setup + what each job tests
```

Triggers: `workflow_dispatch` + `push` to main on relevant paths. Every LLM job asserts with `scripts/assert_contains.sh` on `steps.<id>.outputs.response-file` and appends the response to `$GITHUB_STEP_SUMMARY`. Env `COPILOT_GITHUB_TOKEN: ${{ secrets.COPILOT_PAT }}`.

## Phase 1 — plain prompts (`ai-inference.yml`)
1. `simple-prompt` — inline prompt, `model: gpt-4.1` → assert `PONG`.
2. `prompt-file` — `pong.prompt.txt` + `system-prompt-file`.
3. `prompt-yml` — `summary.prompt.yml`, `input: repo: …`, `file_input: readme: ./README.md` → assert repo name.

## Phase 2 — MCP basics (`ai-inference.yml`)
4. `dummy-mcp` — setup-python, `pip install -r mcp/requirements.txt`, write `~/.copilot/mcp-config.json`:
   `{"mcpServers":{"dummy":{"type":"local","command":"python","args":["${{ github.workspace }}/mcp/dummy_server.py"],"tools":["*"]}}}`
   Dummy tools: `secret_word()` → `PURPLE-OTTER-4217`, `add(a,b)`, `echo(text)`.
   `copilot-allow-tools: dummy`; prompt "Call secret_word and add 17+25" → assert `PURPLE-OTTER-4217` and `42`.
5. `dummy-mcp-denied` — same config, no allow-tools → assert secret absent. `continue-on-error: true` (observational).
6. `github-mcp` — built-in GitHub MCP, allow its server name → prompt to list top-level files of this repo → assert `README.md`.

## Phase 3 — edammcp (`edam-mcp.yml`)
- Setup: checkout `edamontology/edammcp` (pin a commit SHA) into `/tmp/edammcp`, `astral-sh/setup-uv` with cache, `uv sync`; `actions/cache` for HF/sentence-transformers model cache (key on edammcp SHA); warm step that runs the mapper once so models are downloaded before Copilot starts the server.
- `edam-smoke` (no LLM): `mcp/edam_smoke.py` uses the `mcp` Python client over stdio to call `map_to_edam_concept_tool("sequence alignment")` → expect `data_0863`; `query_biotools_by_text_exact_match_tool(id="bwa")` → expect BWA. Deterministic server check.
- `edam-llm`: mcp-config with `edam` server (`uv --directory /tmp/edammcp run edam-mcp`), `copilot-allow-tools: edam`; prompt "Map 'short read aligner' to EDAM operations, return URIs" → assert `operation_\d{4}` (optionally `operation_0292`).
- `edam-annotate` (scenario demo): prompt with `file_input: meta: fixtures/meta.yml` asking for suggested EDAM topic/operation/format annotations as YAML → assert ≥1 EDAM URI; write to step summary. Later extension: run on PRs touching `meta.yml` and post as PR comment.

### edammcp considerations
Server: Python stdio (`uv run edam-mcp`), 7 tools: `map_to_edam_concept_tool`, `suggest_new_concept_tool`, `segment_text_tool`, `get_workflow_summary_tool`, `query_biotools_by_text_tool`, `query_biotools_by_text_exact_match_tool`, `query_biotools_by_edam_terms_tool`. Usable only through v3; v2 supports only the built-in GitHub MCP.

**Caveats**
- ML models download on first run → slow jobs unless cached (`actions/cache` on the HF/sentence-transformers cache plus the uv cache; key on the edammcp SHA).
- Runner limits: 7–16 GB RAM, no GPU. Check that model memory and CPU inference fit; measure job duration.
- Copilot CLI MCP startup timeout can be shorter than model load time → warm step before inference; if still slow, check whether the timeout is configurable.
- `query_biotools_*` hit the bio.tools API → network flakiness and rate limits. Keep bio.tools assertions in separate jobs so mapping tests don't fail with them.
- Upstream is young (25 open issues, active pushes) → pin a commit SHA and bump it deliberately.
- Outputs are fuzzy: confidence scores and labels vary. Assert on stable EDAM IDs (`data_0863`, `operation_0292`) or ID patterns only.
- Tool permissions: allow only the needed tools (`edam(map_to_edam_concept_tool)`, …) rather than the whole server where possible.
- Cost and latency: each LLM job consumes Copilot premium requests, so limit triggers with path filters and `workflow_dispatch`.
- Untrusted PR content (e.g. a fork's `meta.yml`) is fed to the model → prompt-injection risk. Don't give write tools/tokens to jobs on `pull_request` from forks; post comments from a separate job with minimal permissions.

**Scenarios (future, beyond the demo)**
1. PR annotation suggestions: on PRs touching nf-core `meta.yml`, Galaxy tool XML or bio.tools JSON, map descriptions → suggested EDAM topics/operations/formats posted as a PR comment.
2. Annotation linting: flag obsolete EDAM URIs or low-confidence matches against the description; warn or fail below a threshold.
3. bio.tools cross-check: compare local metadata with the registry entry (`query_biotools_by_text_exact_match_tool`).
4. Related-tool discovery: list existing tools with the same EDAM terms (`query_biotools_by_edam_terms_tool`) on new-tool PRs.
5. Gap reports: `suggest_new_concept_tool` drafts new-concept proposals into an issue or artifact for EDAM curators.
6. Scheduled batch: run over a directory of descriptions and upload a JSON/CSV report artifact.

**Testing layers**
1. Deterministic, no LLM: `edam-smoke` (above) checks the server and tools in CI. Run it first; LLM jobs `needs:` it.
2. LLM + MCP: `edam-llm`, a single mapping prompt asserting on an ID pattern.
3. End-to-end scenario: `edam-annotate` on a fixture, asserting the output is valid YAML with ≥1 EDAM URI (parse with `yq`).
4. Negative: same config without `copilot-allow-tools` → expect no EDAM IDs from tool calls (observational, `continue-on-error`).
5. Record timings (model load, job total) in the step summary to judge whether caching or a larger runner is needed.

## Secrets
- `COPILOT_PAT` — fine-grained PAT with "Copilot Requests" permission. Required by every job except `edam-smoke`.

## Verification
1. Locally: `actionlint`; run `python mcp/dummy_server.py` via MCP inspector; run `mcp/edam_smoke.py` against a local edammcp checkout.
2. Push, `gh workflow run ai-inference.yml` / `edam-mcp.yml`, `gh run watch`, `gh run view --log-failed`.
3. Assertions are case-insensitive regex on stable tokens/IDs only (LLM output nondeterministic).

## Open items to confirm during implementation
- Exact built-in GitHub MCP server name for `--allow-tool`.
- Whether `-p` mode honours `~/.copilot/mcp-config.json`; fallback: `copilot-cli-path` wrapper script adding `--additional-mcp-config @file`.
- Copilot CLI MCP startup timeout vs edammcp model load time (mitigated by warm cache).
