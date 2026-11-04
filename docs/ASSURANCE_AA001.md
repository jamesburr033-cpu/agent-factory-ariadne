# AA-001 + AA-002 synthetic runtime authorization and evidence reconciliation proof

Status: development-only experimental addition; **not deployed to the P620**.

This additive package introduces a strictly limited authorization contract. It only supports writing one of three fields (`feature_name`, `owner`, `status`) in a local JSON fixture selected by the test harness. It does not integrate with the existing `ActionQueue`, browsers, Epic, email, real tools, or agent tool dispatch yet. Existing functionality remains unchanged.

## Commands on a *clean working branch* (Python 3.12)

```powershell
cd C:\AI\agent_factory_ariadne
# Apply the reviewed files to a non-main working branch first.
python -m pip install -e ".[dev]"
python -m pytest -q tests/assurance
python -m pytest -q
python scripts/assurance_demo.py
```

The demo uses a temporary directory and produces an allowed fixture update, a blocked `send_message`, and a small hash-chained event sequence. Temporary artifacts are deleted on completion.

## AA-002 read-only evidence reconciler (prototype)

`assurance.monitor.AssuranceReconciler` inspects a verified snapshot of the
hash-chained audit ledger and the synthetic grant-consumption table.
It detects: consumed grants with no dispatch event; dispatch without terminal
receipt; duplicate dispatches; unknown grants; unexpected terminal receipts;
missing tool/action identifiers; audit corruption; and `unknown_effect` events
that need human investigation. It never retries an uncertain side effect.

The reconciler runs **in the same OS/process trust domain** as the synthetic
broker and is not yet a protected independent monitoring service.
The two SQLite databases are observed in separate transactions, so run this
check with demo dispatches quiescent to avoid transient false positives.
Independent monitor identity, immutable external anchors, authenticated
reviewer identities, and tool-broker integration remain mandatory before
any real tool can be connected.

## Threat model and limitations

- A **demo:*** reviewer identity is a synthetic test fixture, **not** an authenticated human approval.
- The HMAC signing key, grant ledger, audit database, and broker are currently in one Python trust domain. This is not independently isolated monitoring or tamper-proof evidence. Keep all production, clinical, employer, purchase, messaging, credential, and external automation adapters unconnected.
- SQLite grant consumption uses an atomic transaction to block concurrent reuse. Consumed grants are not refunded on audit failures.
- SQLite hash chaining can detect modification of existing events, but deletion of the tail or rewriting the whole database requires an external checkpoint to detect.
- A process crash between synthetic fixture write and audit result can leave `unknown_effect`. The safe response is investigation and reconciliation, not a blind retry.
- If the audit store cannot be read/written or fails its integrity check, dispatch refuses to proceed; existing records are not rewritten.

## Next milestones

AA-002 still to complete: Run the broker, grant-signing keys, protected evidence writer and monitor as separate OS identities/services. Implement authenticated reviewer identity and external audit anchors. The current same-process reconciler is a first testable component, **not** completion of that security boundary. Only after completing that work should existing executors be migrated behind the broker.

AA-003: Complete protected post-dispatch coverage verification, recovery and incident queues.

AA-004+: Adversarial eval campaigns with sequestered holdouts, Streamlit console, and release rehearsals.
