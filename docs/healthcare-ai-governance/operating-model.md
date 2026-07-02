# Healthcare AI Governance Operating Model

This operating model defines how AI features move from idea to intake, review, pilot, monitoring, and retirement.

## 1. Purpose

The purpose is to make governance practical. Every healthcare AI feature needs clear ownership, defined scope, human review, evidence, monitoring, and escalation.

## 2. Roles

| Role | Primary responsibility |
| --- | --- |
| Business owner | Owns the operational need, value case, staffing impact, and workflow adoption. |
| Clinical owner | Owns clinical safety, appropriateness, and patient-impact review. |
| Technical owner | Owns configuration, integration, environment planning, access review, and change coordination. |
| Privacy owner | Reviews PHI use, retention, disclosure, minimum necessary access, and patient privacy risk. |
| Security owner | Reviews vendor, access, logging, integration, and technical controls. |
| Compliance owner | Reviews policy, regulatory, audit, and documentation expectations. |
| Revenue-cycle owner | Reviews coding, billing, authorization, denial, and medical necessity impact. |
| Governance lead | Coordinates intake, review, decision tracking, monitoring, escalation, and evidence register updates. |
| End-user representative | Validates workflow fit, burden, usability, and training needs. |
| Vendor contact | Provides documentation, support path, release notes, issue response, and feature-change information. |

## 3. Lifecycle

### Stage 1, idea

A requestor identifies an AI feature, AI-enabled workflow, vendor tool, or internal automation opportunity.

Required output:

- Clear use case
- Expected benefit
- Known data involved
- Proposed users
- Initial owner

### Stage 2, intake

Complete `ai-feature-intake.md`.

Exit criteria:

- Scope is understandable
- Patient-impact level is estimated
- PHI and data needs are documented
- Human review expectation is stated
- Accountable owner is named

### Stage 3, risk review

Complete `ai-risk-review.md`.

Exit criteria:

- Risk tier assigned
- Required controls listed
- Vendor and organization responsibilities clarified
- Decision recorded in `evidence-register.md`

### Stage 4, pilot planning

Define pilot limits before exposing the feature broadly.

Pilot controls may include:

- Limited users
- Limited clinics, departments, specialties, or encounter types
- Non-production or test environment when possible
- No automated patient-facing use without separate approval
- No unsupervised clinical decision-making
- Enhanced monitoring cadence
- Clear restriction or disablement path

### Stage 5, monitoring

Use `model-monitoring-and-drift.md`.

Monitoring must include:

- Safety and quality feedback
- User edits, overrides, and complaints
- Workflow impact
- Vendor release notes or feature changes
- Equity or subgroup concerns when applicable
- Evidence of review and follow-up

### Stage 6, expansion or restriction

The governance group decides whether to expand, continue, restrict, pause, disable, or retire the feature.

Expansion requires:

- Pilot evidence reviewed
- Open risks accepted or mitigated
- Monitoring plan updated
- Responsible owners confirmed
- Decision recorded

## 4. Decision cadence

| Risk tier | Suggested review cadence |
| --- | --- |
| Tier 1 | Intake review, then annual or major-change review. |
| Tier 2 | Intake review, pilot or go-live review, then quarterly until stable. |
| Tier 3 | Formal review before pilot, frequent early monitoring, governance review before expansion. |
| Tier 4 | Block or escalate before any use. Reconsider only after remediation. |

## 5. Escalation triggers

Escalate immediately when any of the following occur:

- Patient harm concern
- Privacy incident concern
- Security concern
- Unapproved use case
- Repeated hallucination or misleading output
- Revenue integrity concern
- Vendor behavior changes without sufficient notice
- User feedback indicates unsafe reliance or workflow harm
- No clear owner for active monitoring

## 6. Minimum approval standard

An AI feature should not move forward unless the governance record answers these questions:

1. What is the approved use?
2. What is out of scope?
3. What data is used?
4. Who is accountable?
5. What humans must review?
6. What could go wrong?
7. What controls reduce that risk?
8. How will feedback be monitored?
9. How will drift or vendor changes be detected?
10. How can the feature be restricted or disabled?

## 7. Ariadne alignment

Ariadne should treat healthcare AI governance as a review-gated workflow.

Allowed in portfolio mode:

- Draft governance templates
- Summarize non-PHI policy notes
- Create intake and review scaffolds
- Track open questions
- Suggest monitoring criteria
- Produce human-review checklists

Requires separate human approval and appropriate systems:

- PHI access
- Production EHR changes
- Patient-facing workflow use
- Final clinical, legal, privacy, or compliance approval
