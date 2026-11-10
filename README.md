# inference-test

A test bed for [`actions/ai-inference@v3`](https://github.com/actions/ai-inference). v3 runs prompts through the GitHub Copilot CLI, so every job needs a Copilot-enabled account behind it. The plan is in [PLAN.md](PLAN.md). Phases 1 (plain prompts), 2 (MCP basics) and 3 ([edammcp](https://github.com/edamontology/edammcp)) exist.

## What you need to set up

### 1. A GitHub account with Copilot

The token you create in step 2 must belong to an account that has a Copilot seat (personal plan, or one assigned by an organization). If that is an organization seat, check that the org policy allows Copilot CLI. Without it the action fails at authentication.

### 2. A fine-grained personal access token

Classic tokens (`ghp_`) don't work with the Copilot CLI. The token must be fine-grained.

1. Go to [github.com/settings/personal-access-tokens/new](https://github.com/settings/personal-access-tokens/new).
2. Set **Resource owner** to your personal account. Organizations don't offer the Copilot permission.
3. Set an expiration. Short is fine: you can regenerate it.
4. Pick any **Repository access** option, such as "Public repositories".
5. Under **Permissions**, open the **Account** tab, click **Add permissions**, and select **Copilot Requests** with the **Read-only** access level. This worked in the first successful run.
6. Generate the token and copy it. GitHub shows it once.

This permission doesn't appear on the REST API page listing fine-grained permissions, because it isn't a REST API permission. Source: [Authenticating Copilot CLI](https://docs.github.com/en/copilot/how-tos/copilot-cli/set-up-copilot-cli/authenticate-copilot-cli).

### 3. A repository secret

In this repository: Settings → Secrets and variables → Actions → New repository secret.

- Name: `COPILOT_PAT`
- Value: the token from step 2

Or from a terminal:

```bash
gh secret set COPILOT_PAT
```

### 4. Actions settings

- Settings → Actions → General: Actions must be enabled. The default "Allow all actions" works. If you restrict actions, allow `actions/ai-inference@v3`, `actions/checkout`, and `actions/setup-node`.
- Workflow permissions can stay on the read-only default. The workflow asks only for `contents: read`.

### 5. Put the workflow on the default branch

`workflow_dispatch` only shows up once the workflow file is on `main`. Push this repository to `main` first. The push also triggers the workflow once, because the path filter covers `.github/**`.

## Running it

```bash
gh workflow run ai-inference.yml
gh run watch
gh run view --log-failed   # if something broke
```

Or use Actions → ai-inference → Run workflow in the web UI. Each job also writes the model response to the run summary.

## What the jobs test

| Job | Checks | Passes when |
| --- | --- | --- |
| `simple-prompt` | Inline `prompt` input | Response contains `PONG` |
| `prompt-file` | `prompt-file` and `system-prompt-file` with plain text files | Response contains `PONG` |
| `prompt-yml` | A `.prompt.yml` template filled from `input` and `file_input` (the README) | Response mentions `inference-test` |
| `dummy-mcp` | Local stdio MCP server (`mcp/dummy_server.py`) registered in `~/.copilot/mcp-config.json`, allowed with `copilot-allow-tools: dummy` | Response has `PURPLE-OTTER-4217` and `42`, values only the tools can supply |
| `dummy-mcp-denied` | Same server, no `copilot-allow-tools` | Response lacks the secret. Observational: failure doesn't fail the run |
| `github-mcp` | Copilot's built-in GitHub MCP server, `copilot-allow-tools: github-mcp-server` | Response lists `README.md`. Observational: the server name is unverified |

Assertions are case-insensitive regex matches (see `scripts/assert_contains.sh`), because model output varies between runs. A job fails fast with a clear message if `COPILOT_PAT` is empty.

## edammcp (`edam-mcp.yml`)

Tests the [EDAM ontology MCP server](https://github.com/edamontology/edammcp) through the Copilot CLI, using a pinned commit (`8e9cc81…`, set in `.github/actions/setup-edam/action.yml`). Bump the pin on purpose.

| Job | Checks | Passes when |
| --- | --- | --- |
| `edam-smoke` | `mcp/edam_smoke.py` calls `map_to_edam_concept_tool` and `query_biotools_by_text_exact_match_tool` directly. No LLM, no secrets | Mapping returns EDAM IDs and bio.tools returns BWA |
| `edam-llm` | Runs after `edam-smoke`. Two prompts with `copilot-allow-tools: edam`: map "short read aligner", then annotate `fixtures/meta.yml` from a `.prompt.yml` template | Both responses contain an EDAM ID such as `operation_3198` |

Assertions look for any ID of the form `topic|operation|data|format_NNNN`, because the mapping scores and top matches vary. The LLM jobs can't prove the model called the tool rather than recalling an ID. The model is told not to answer from memory, which is the only guard.

Things to watch:

- **Python version.** The setup uses Python 3.13: `onnxruntime` (an edammcp dependency) has no wheel for the 3.14 that the runner image ships, so `uv sync` failed on the first run.
- **Install size and time.** The sentence-transformers dependency pulls in PyTorch. A local `.venv` was 5.7 GB. The workflow caches uv and the Hugging Face model (`all-MiniLM-L6-v2`). The `edam-smoke` job writes its duration to the run summary, so the first run shows what a cold start costs.
- **Server startup.** The server downloads the EDAM ontology and builds embeddings for about 2,400 concepts on start (about 20 s locally with warm caches). Each setup runs the smoke test first to warm the ontology and model caches before Copilot starts the server. If the Copilot CLI's MCP startup timeout is shorter than a cold start, `edam-llm` fails with no tool call.
- **Network.** The server fetches `edamontology.org/EDAM.owl` and calls the bio.tools API. Either being down fails `edam-smoke`.
- **Not tested here yet.** A denied-tool variant like `dummy-mcp-denied` is left out: the model knows EDAM IDs, so a pass or fail would say little about tool access.

## Model choice

The action's default, `gpt-4.1`, was retired from Copilot on 2026-06-01, so the first run failed with `Model "gpt-4.1" is not available`. The jobs now pin `claude-haiku-5.5`:

- **Cheap.** It ties with GPT-6 Luna for the lowest per-token price on the pricing page: $0.10 per 1M input tokens and $0.50 per 1M output tokens. A test prompt costs a fraction of a cent.
- **Stable.** A pinned model doesn't change under the tests, and the model that ran is known.
- **Tested.** Both `claude-haiku-5.5` and `gpt-6-luna` answered `PONG` locally with `copilot --model <id>`. The ID format is lowercase and dashed, with a dot in the version.

Whether the CI token's plan includes `claude-haiku-5.5` is only known after a run. If it fails with "not available", switch to `gpt-6-luna` in `.github/workflows/ai-inference.yml`. Setting `model: ''` makes the CLI choose its own default, but the log doesn't say which model that was.

References:

- [Supported AI models in GitHub Copilot](https://docs.github.com/en/copilot/reference/ai-models/supported-models): model list, per-client and per-plan availability, retirement history (GPT-4.1).
- [Models and pricing for GitHub Copilot](https://docs.github.com/en/copilot/reference/copilot-billing/models-and-pricing): per-token prices. Copilot bills in GitHub AI Credits (1 credit = $0.01).

Model availability depends on the Copilot plan and on organization policy, and the page's availability tables didn't survive text extraction, so check them in a browser if a model is rejected.

## Things that will trip you up

- **Fork pull requests get no secrets.** The workflow runs on `push` to `main` and on manual dispatch only, so this doesn't come up here. Don't add a `pull_request` trigger without thinking about it.
- **Each run uses Copilot quota.** Each job makes at least one model call. The path filter on `push` keeps unrelated commits from triggering runs.
- **The token expires.** An expired PAT shows up as an authentication failure in the action, not as the "secret is empty" error.
- **Model.** Jobs pin `model: claude-haiku-5.5`. See [Model choice](#model-choice).
- **Not verified yet.** These workflows have not been run. The first run may need small fixes.

## Layout

```
.github/workflows/ai-inference.yml        Phase 1 and 2 jobs
.github/workflows/edam-mcp.yml            Phase 3 jobs
.github/actions/setup-edam/               installs a pinned edammcp, caches, warms, smoke-tests
.github/actions/setup-copilot/            installs Node and the Copilot CLI, checks the token
.github/prompts/                          prompt and system-prompt files
scripts/assert_contains.sh                response assertions
mcp/dummy_server.py                       dummy MCP server (pin `mcp<2`; 2.x renamed FastMCP)
mcp/smoke_dummy.py                        calls the dummy server directly, no LLM
mcp/edam_smoke.py                         calls edammcp directly, no LLM
fixtures/meta.yml                         sample tool description for the annotate prompt
PLAN.md                                   full plan, including MCP phases
```
