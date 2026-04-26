# Ariadne Agent Factory

Local-first, safety-gated Master Agent scaffold for the Lenovo P620 named **Ariadne**.

- **Master Agent:** Ariadne
- **Critic / Safety Agent:** Tron
- **Machine:** Lenovo ThinkStation P620 named Ariadne

## What v0.2 does

v0.2 adds a safe local browser demo:

- Uses a local HTML form: `examples/gpu_deal_form.html`
- Fills GPU deal evaluation fields through Playwright when explicitly requested
- Takes before/after screenshots in `memory/screenshots/`
- Does **not** click submit
- Does **not** contact sellers
- Does **not** use real websites
- Does **not** use credentials
- Does **not** touch ServiceNow, Epic, PHI, or work systems

## What v0.3 adds

v0.3 adds a local Human Review Console. v0.3.1 improves run selection and artifact filtering:

- Reads Ariadne run logs from `memory/agent_runs.jsonl`
- Shows the latest browser-demo run by default when one exists, otherwise the latest run
- Provides filters for all runs, browser demo runs, self-improvement runs, and runs with high-risk actions
- Displays task text, routing, screen observation, recommended actions, approval decisions, Tron review, and demo screenshots
- Displays improvement proposals for self-improvement runs when present
- Displays only screenshots referenced by the selected run's `artifacts.browser_demo` object
- Lets James record approve, reject, or needs-revision decisions
- Lets James save lessons learned
- Writes review decisions to `memory/review_decisions.jsonl`
- Writes lessons to `memory/lessons_learned.jsonl`
- Does **not** submit forms, send messages, save records, purchase items, access real websites, use credentials, or touch work systems

## What v0.4 adds

v0.4 adds a local Review-Gated Action Queue. v0.4.1 improves console labels, controls, and execution audit detail:

- Writes proposed actions to `memory/action_queue.jsonl` with `pending` approval status
- Logs queue creation, approval decisions, execution attempts, and final execution results to `memory/action_queue_events.jsonl`
- Shows queued actions for the selected run in the Human Review Console
- Labels queued actions by action type, field, value preview, approval status, and execution status
- Lets James approve, reject, or mark queued actions as needing revision
- Allows execution only for explicitly approved, not-yet-executed, low/medium-risk local demo `fill_field` or `suggest_values` actions
- Runs a Tron final check before queue execution
- Logs attempted_by, result, blocked_reason, and Tron final-check result for execution attempts
- Never executes `submit_form`, `send_message`, `save_record`, `delete_data`, `purchase_item`, credential, deploy, or production actions in v0.4

## What v0.5 adds

v0.5 adds a read-only browser research sandbox for approved non-work websites. v0.5.1 improves routing and console visibility:

- Uses `configs/browser_allowlist.yaml`
- Initially allows read-only research on `ebay.com`, `craigslist.org`, `offerup.com`, and `amazon.com`
- Lists Facebook as restricted read-only only when accessible without login
- Opens approved URLs in read-only mode when browser support is installed
- Extracts visible listing fields such as title, price, location, condition, seller notes, listing URL, red flags, and recommended next step
- Saves observations to `memory/browser_research_runs.jsonl`
- Captures screenshots to `memory/browser_research_screenshots/` when live browser research is used
- Shows browser research findings in the Human Review Console
- Routes URL-based read-only research before form-fill handling, even when the prompt says not to submit forms
- Adds a Browser Research Runs console filter and prefers the latest browser research run by default
- Separates Browser Research Artifacts from Browser Demo Artifacts
- Ignores obvious navigation/header/footer text such as `Skip to main content` when extracting listing titles
- Queues draft seller messages as pending high-risk actions only; Ariadne does not send them
- Keeps login, credential entry, contact, bid, buy, checkout, submit, captcha bypass, work systems, PHI, and aggressive scraping blocked

## What v0.6 adds

v0.6 adds Personal Workflow Memory for approved reusable patterns. v0.6.1 confirms browser research proposed actions are reviewable in the Action Queue:

- Stores approved reusable patterns in `memory/patterns.jsonl`
- Reads approved lessons from `memory/lessons_learned.jsonl`
- Adds `WorkflowPattern`, `PatternSource`, and `PatternConfidence` schemas
- Adds `PatternMemory` for read-only pattern retrieval during normal agent runs
- Adds seed GPU deal patterns for timestamped photos, GPU-Z screenshots, benchmark or stress-test videos with visible temperatures, avoiding deposits, avoiding off-platform payment pressure, preferring local pickup validation, discounting offers when proof is missing, and keeping seller messages draft-only
- Applies relevant approved patterns to GPU Deal Evaluator and Browser Research recommendations
- Logs pattern usage to `memory/pattern_usage.jsonl`
- Adds review-console controls to promote a lesson to a pattern, create a manual approved pattern, and deactivate a pattern
- Queues Browser Research `proposed_actions`, including draft seller messages, as pending `not_executed` action queue records tied to the browser research `run_id`
- Keeps draft seller message actions high-risk and blocked from execution even if approved
- Does not write new patterns automatically during normal Ariadne runs
- Patterns inform recommendations only and never authorize sending, buying, submitting, deleting, credential, deployment, or production actions

## Setup

From PowerShell:

```powershell
cd C:\AI\agent_factory_ariadne
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
python -m pytest
```

If PowerShell blocks activation:

```powershell
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
.\.venv\Scripts\Activate.ps1
```

## Run the planning-only demo

```powershell
python -m agent_factory.main "Help me evaluate an RTX 3090 GPU listing. Price is 650 dollars, 24 GB VRAM, used, local pickup, seller says it works but has not provided benchmarks. Recommend red flags, offer price, and a draft seller message. Do not send anything." --mode assisted_fill
```

This returns structured JSON with routing, actions, approval decisions, Tron review, and audit logging.

## Install browser demo support

```powershell
python -m pip install -e ".[dev,browser]"
python -m playwright install chromium
```

## Run the local GPU Deal Evaluator browser demo

```powershell
python -m agent_factory.main "Help me evaluate an RTX 3090 GPU listing. Price is 650 dollars, 24 GB VRAM, used, local pickup, seller says it works but has not provided benchmarks. Recommend red flags, offer price, and a draft seller message. Do not send anything." --mode demo --execute-demo-form
```

Expected behavior:

- Ariadne opens the local HTML form headlessly
- Ariadne fills allowlisted fields
- Ariadne creates before/after screenshots
- Ariadne does not submit the form
- Tron still marks submit as requiring approval before execution

## Safety model

Allowed without approval:

- Read/summarize task text
- Suggest values
- Fill allowlisted local demo fields in assisted/demo mode

Requires approval:

- Submit form
- Send message
- Save record
- Delete data
- Purchase item
- Modify code
- Change approval rules

Blocked by default:

- Access PHI
- Production Epic changes without governance
- Silent self-modification
- Granting itself new permissions

## Useful commands

Run tests:

```powershell
python -m pytest
```

Install review console support:

```powershell
python -m pip install -e ".[dev,ui]"
```

Run the Human Review Console:

```powershell
python -m agent_factory.review_console
```

The console opens a local Streamlit app bound to `localhost`. Review buttons append JSONL review records and lessons. Queue execution is limited to approved low/medium-risk local demo fill/suggest actions after Tron final check.

v0.4 usage notes:

- Use the filter dropdown to focus on all runs, browser demo runs, self-improvement runs, or runs with high-risk actions.
- Use the run dropdown to select a specific Ariadne run by timestamp, run ID, task type, selected agent, and short task text.
- Browser demo artifacts show before/after screenshots only when those exact paths are referenced by the selected run.
- The Action Queue section shows queued actions for the selected run.
- Use `Approve action`, `Reject action`, or `Mark needs revision` to record queue review state.
- `Execute approved local demo action` only records execution for safe local demo fill/suggest actions after approval and Tron final check.
- Submit, send, save, delete, purchase, credential, deploy, and production actions show a warning and remain blocked.

v0.4.1 validation steps:

1. Run the local GPU demo plan to create queued actions:

```powershell
python -m agent_factory.main "Evaluate RTX 3090 listing price is 650 dollars 24 GB VRAM used" --mode demo
```

2. Start the console:

```powershell
python -m agent_factory.review_console
```

3. Select the run and open Action Queue expanders. Confirm labels look like `fill_field | Recommended offer | $550-$600 | pending | not_executed`.
4. Approve a low-risk local demo `fill_field` action, then execute it.
5. Open a `submit_form` action and confirm the visible warning remains, execution is blocked, and an audit event is appended if attempted.
6. Check queue events:

```powershell
Get-Content .\memory\action_queue_events.jsonl -Tail 10
```

v0.5 read-only browser research example:

```powershell
python -m agent_factory.main "Research this GPU listing read-only: https://www.ebay.com/itm/example" --mode demo
```

Expected behavior:

- URL domain must be approved in `configs/browser_allowlist.yaml`
- Ariadne reads visible page text only and may capture a screenshot
- Ariadne extracts listing-style fields when visible
- Tron reviews scam risk, missing proof, price reasonableness, and approval needed before contact
- Any draft seller message is queued as pending review only
- No login, contact, send, bid, buy, checkout, submit, credential, or work-system action is executed

View browser research runs:

```powershell
Get-Content .\memory\browser_research_runs.jsonl -Tail 5
```

v0.6 pattern memory usage:

```powershell
Get-Content .\memory\patterns.jsonl
Get-Content .\memory\pattern_usage.jsonl -Tail 10
python -m agent_factory.review_console
```

In the review console, use Pattern Memory controls to promote approved lessons, create manual patterns, or deactivate stale patterns. Normal agent runs only read active patterns and log which patterns influenced recommendations.

v0.6.1 browser research queue validation:

1. Run a read-only browser research task:

```powershell
python -m agent_factory.main "Read-only research this eBay GPU listing https://www.ebay.com/itm/example" --mode demo
```

2. Open the Human Review Console:

```powershell
python -m agent_factory.review_console
```

3. Select the browser research run and confirm the Action Queue shows a `send_message | Draft seller message | ... | pending | not_executed` record.
4. Approve the draft seller message if desired. Execution must remain blocked.
5. Confirm the blocked execution attempt is logged:

```powershell
Get-Content .\memory\action_queue_events.jsonl -Tail 10
```

v0.5.1 validation steps:

1. Run a read-only URL task that mentions form submission safety:

```powershell
python -m agent_factory.main "Read-only research this eBay GPU listing https://www.ebay.com/itm/example and do not submit forms" --mode demo
```

2. Open the console and choose the `browser research runs` filter:

```powershell
python -m agent_factory.review_console
```

3. Confirm the selected run shows `Browser Research Artifacts` with research metadata, listing fields, Tron review, proposed actions, and any referenced screenshot path.
4. Confirm `Browser Demo Artifacts` remains separate and does not show older GPU demo screenshots for browser research runs.

View latest audit log:

```powershell
Get-Content .\memory\agent_runs.jsonl -Tail 1
```

View screenshots:

```powershell
dir .\memory\screenshots
```

View queued actions:

```powershell
Get-Content .\memory\action_queue.jsonl -Tail 5
```

View queue events:

```powershell
Get-Content .\memory\action_queue_events.jsonl -Tail 10
```

## v0.6.1 status

Completed in v0.6.1:

- Added a visible Streamlit review console
- Shows plan, actions, approvals, Tron review, improvement proposals, and selected-run screenshots
- Allows James to approve, reject, mark needs revision, and save lessons learned
- Adds run filters and defaults to the latest executed browser-demo run when available
- Stops scanning `memory/screenshots/` for unrelated images
- Adds a review-gated local action queue with append-only JSONL audit events
- Improves Action Queue row labels, action detail display, and disabled execution controls
- Executes only approved low/medium-risk local demo fill/suggest actions after Tron final check
- Adds read-only browser research for approved non-work listing sites
- Saves extracted listing observations and shows them in the review console
- Fixes URL-based read-only browser research routing before form-fill routing
- Makes browser research runs easy to find and preferred by default in the console
- Filters listing-title extraction to avoid obvious navigation/header/footer text
- Queues draft seller messages without sending them
- Adds approved personal workflow patterns for GPU deal evaluation
- Applies relevant patterns to red flags, next steps, draft messages, and Tron review context
- Logs pattern usage while keeping pattern writes explicit and review-console gated
- Queues browser research draft seller messages for review while keeping `send_message` non-executable
- Keeps non-allowlisted websites, form submission, messaging, purchases, credentials, PHI, and work systems blocked
