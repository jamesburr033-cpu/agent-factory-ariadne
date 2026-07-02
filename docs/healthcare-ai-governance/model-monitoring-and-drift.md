# Model Monitoring and Drift Plan

Use this plan before pilot or go-live. The purpose is to make post-deployment ownership explicit instead of assuming the AI feature will remain safe, accurate, and useful over time.

## 1. Monitoring summary

| Field | Response |
| --- | --- |
| Feature name |  |
| Monitoring owner |  |
| Operational owner |  |
| Clinical owner, if applicable |  |
| Vendor contact or support path |  |
| First review date |  |
| Review cadence |  |
| Current status |  |

## 2. What must be monitored

| Area | Question | Metric or evidence | Owner | Cadence |
| --- | --- | --- | --- | --- |
| Output accuracy | Are summaries, drafts, recommendations, or classifications correct enough for the approved use? |  |  |  |
| Safety events | Are users reporting unsafe, misleading, missing, or hallucinated output? |  |  |  |
| Human override | How often do users reject, edit, or ignore AI output? |  |  |  |
| Workflow burden | Is the feature saving time or creating rework? |  |  |  |
| Equity and bias | Are issues concentrated by language, clinic, specialty, payer, race, age, sex, disability, or other relevant subgroup? |  |  |  |
| Privacy | Are prompts, logs, outputs, and retention behaving as approved? |  |  |  |
| Security | Are access, integration, and credential controls still appropriate? |  |  |  |
| Revenue integrity | Are coding, billing, authorization, appeal, or medical necessity outputs being reviewed properly? |  |  |  |
| User feedback | Is feedback being reviewed, triaged, assigned, and closed? |  |  |  |
| Vendor changes | Did the vendor update model behavior, prompts, UI, settings, or release notes? |  |  |  |

## 3. Drift signals

Drift means the feature behaves differently from the approved baseline or no longer fits the workflow safely.

### Output drift

- More incorrect, incomplete, or misleading outputs
- New hallucination patterns
- Loss of important clinical or operational context
- Outputs that sound more confident than the evidence supports
- Increased user edits, overrides, or complaints

### Workflow drift

- Users start relying on the tool for decisions outside the approved scope
- Users copy AI text without review
- Staff develop workarounds that bypass intended safeguards
- The feature is used by a different specialty, clinic, team, or patient population than approved

### Vendor or platform drift

- Release notes describe AI behavior changes
- Model, prompt, UI, or configuration changes occur
- Feedback routing changes
- Audit logging, retention, or data-use terms change
- Vendor validation evidence is updated or withdrawn

## 4. Thresholds and triggers

| Trigger | Escalation level | Required action | Owner |
| --- | --- | --- | --- |
| Any patient harm concern | Critical | Pause or restrict use, notify governance owner, open safety review. |  |
| Repeated hallucinated or misleading output | High | Review examples, notify vendor, increase monitoring, consider rollback. |  |
| Privacy or inappropriate disclosure concern | Critical | Escalate to privacy and security, preserve evidence, restrict use if needed. |  |
| Unapproved use case discovered | High | Stop expansion, retrain users, update scope decision. |  |
| User feedback backlog exceeds threshold | Moderate | Assign reviewer and close loop with owners. |  |
| Vendor update affects behavior | Moderate or High | Review release note, determine whether re-validation is needed. |  |
| Equity concern or subgroup performance gap | High | Analyze affected workflow, restrict use if needed, define remediation. |  |

## 5. Feedback review process

1. Capture user feedback with date, role, location, feature, patient-impact concern, and screenshot or output sample when appropriate.
2. Remove or protect PHI in any portfolio artifact.
3. Triage severity within the agreed service level.
4. Assign owner.
5. Decide whether the issue is user training, configuration, vendor defect, model limitation, workflow mismatch, or governance gap.
6. Track closure in the evidence register.
7. Feed repeat issues into the next governance review.

## 6. Monitoring meeting agenda

Use this for the first 30 days of a pilot, then reduce cadence only if risk is stable.

- Review safety issues and near misses
- Review user feedback and unresolved items
- Review accuracy or rework samples
- Review equity or subgroup signals
- Review vendor release notes or support responses
- Review changes to scope, users, or workflow
- Decide whether to continue, restrict, expand, pause, or retire

## 7. Rollback or restriction plan

| Control | Details |
| --- | --- |
| How to disable feature |  |
| Who can disable feature |  |
| Communication owner |  |
| Downtime or fallback workflow |  |
| Evidence to preserve |  |
| Vendor notification path |  |
| Re-approval requirement |  |

## 8. Current monitoring decision

| Decision | Selected |
| --- | --- |
| Continue as approved |  |
| Continue with added monitoring |  |
| Restrict scope |  |
| Pause pilot |  |
| Disable feature |  |
| Escalate to governance body |  |

Decision notes:
