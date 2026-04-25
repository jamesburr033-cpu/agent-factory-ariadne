# Ariadne Agent Factory Build Rules

## Project identity
- Master Agent: Ariadne
- Critic / Safety Agent: Tron
- Dedicated machine: Lenovo P620 named Ariadne
- Build location: C:\AI\agent_factory_ariadne

## Safety rules
- Do not touch Epic, ServiceNow, work systems, PHI, credentials, email, purchases, or real external submissions.
- All submit, send, save, purchase, delete, credential, deployment, and production actions require human approval.
- Browser automation must remain local-demo-only unless explicitly approved.
- Do not modify approval rules to reduce safety.
- Do not add external APIs, cloud services, telemetry, or background workers without approval.
- Do not store secrets or sensitive data in the repo.

## Development rules
- Use Python 3.12.
- Keep tests passing.
- Prefer simple, inspectable code over complex frameworks.
- Add or update tests for every new behavior.
- Keep Playwright local-demo flows submit-blocked by default.
- Maintain JSONL audit logging.
- Tron must review proposed actions.
- Self-improvement may propose changes but may not silently apply them.

## Current milestone
v0.2 works:
- Local GPU Deal Evaluator form
- Playwright fills safe fields
- Before/after screenshots
- Submit not clicked
- Tron approval gate active

## Next milestone
v0.3:
Build a Human Review Console for approving, rejecting, revising, and saving lessons from Ariadne runs.
