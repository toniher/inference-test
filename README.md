# inference-test

A test bed for [`actions/ai-inference@v3`](https://github.com/actions/ai-inference). v3 runs prompts through the GitHub Copilot CLI, so every job needs a Copilot-enabled account behind it. The plan is in [PLAN.md](PLAN.md). Only Phase 1 (plain prompts) exists so far. MCP tests come later.

## What you need to set up

### 1. A GitHub account with Copilot

The token you create in step 2 must belong to an account that has a Copilot seat (personal plan, or one assigned by an organization). If that is an organization seat, check that the org policy allows Copilot CLI. Without it the action fails at authentication.

### 2. A fine-grained personal access token

Classic tokens (`ghp_`) don't work with the Copilot CLI. The token must be fine-grained.

1. Go to [github.com/settings/personal-access-tokens/new](https://github.com/settings/personal-access-tokens/new).
2. Set **Resource owner** to your personal account. Organizations don't offer the Copilot permission.
3. Set an expiration. Short is fine: you can regenerate it.
4. Pick any **Repository access** option, such as "Public repositories".
5. Under **Permissions**, open the **Account** tab, click **Add permissions**, and select **Copilot Requests**.
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

## What Phase 1 tests

| Job | Checks | Passes when |
| --- | --- | --- |
| `simple-prompt` | Inline `prompt` input | Response contains `PONG` |
| `prompt-file` | `prompt-file` and `system-prompt-file` with plain text files | Response contains `PONG` |
| `prompt-yml` | A `.prompt.yml` template filled from `input` and `file_input` (the README) | Response mentions `inference-test` |

Assertions are case-insensitive regex matches (see `scripts/assert_contains.sh`), because model output varies between runs. A job fails fast with a clear message if `COPILOT_PAT` is empty.

## Things that will trip you up

- **Fork pull requests get no secrets.** The workflow runs on `push` to `main` and on manual dispatch only, so this doesn't come up here. Don't add a `pull_request` trigger without thinking about it.
- **Each run uses Copilot quota.** Each job makes at least one model call. The path filter on `push` keeps unrelated commits from triggering runs.
- **The token expires.** An expired PAT shows up as an authentication failure in the action, not as the "secret is empty" error.
- **Model names.** Jobs set `model: ''` so the Copilot CLI picks its default. The action's own default, `gpt-4.1`, is not available on every plan: it failed with `Model "gpt-4.1" is not available`. To pin a model, set `model:` in the workflow.
- **Not verified yet.** These workflows have not been run. The first run may need small fixes.

## Layout

```
.github/workflows/ai-inference.yml        Phase 1 jobs
.github/actions/setup-copilot/            installs Node and the Copilot CLI, checks the token
.github/prompts/                          prompt and system-prompt files
scripts/assert_contains.sh                response assertions
PLAN.md                                   full plan, including MCP phases
```
