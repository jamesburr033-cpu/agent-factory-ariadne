# Evidence Register

Use this register to track the evidence behind AI governance decisions. The point is to avoid informal approval by memory, chat, or assumption.

## 1. Evidence table

| ID | Date | Feature | Evidence type | Owner | Location or link | Decision supported | Status | Next action |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| EVID-001 |  |  | Intake |  |  |  | Draft |  |
| EVID-002 |  |  | Risk review |  |  |  | Draft |  |
| EVID-003 |  |  | Privacy review |  |  |  | Draft |  |
| EVID-004 |  |  | Security review |  |  |  | Draft |  |
| EVID-005 |  |  | Clinical safety review |  |  |  | Draft |  |
| EVID-006 |  |  | User training |  |  |  | Draft |  |
| EVID-007 |  |  | Monitoring report |  |  |  | Draft |  |

## 2. Evidence types

Use consistent categories.

- Intake
- Risk review
- Clinical safety review
- Privacy review
- Security review
- Compliance review
- Revenue-cycle review
- Equity or bias review
- Vendor documentation
- Contract or BAA evidence
- User training
- Test script
- Test result
- Pilot approval
- Go-live approval
- Feedback review
- Monitoring report
- Incident review
- Rollback decision
- Retirement decision

## 3. Approval log

| Date | Feature | Decision | Approver | Role | Conditions | Expiration or next review |
| --- | --- | --- | --- | --- | --- | --- |
|  |  |  |  |  |  |  |

Decision values:

- Rejected
- Needs more information
- Approved for analysis
- Approved for pilot
- Approved with restrictions
- Approved for production use
- Paused
- Disabled
- Retired

## 4. Issue log

| Date | Feature | Issue | Severity | Source | Owner | Status | Resolution |
| --- | --- | --- | --- | --- | --- | --- | --- |
|  |  |  |  |  |  |  |  |

Severity values:

- Low, workflow inconvenience
- Moderate, repeated quality or usability issue
- High, patient impact possible or compliance concern possible
- Critical, patient harm concern, privacy incident concern, or unsafe output pattern

## 5. Required evidence before pilot

- [ ] Completed AI feature intake
- [ ] Completed risk review
- [ ] Named accountable owner
- [ ] Approved scope and prohibited uses
- [ ] Human review requirements documented
- [ ] Privacy review completed if PHI is involved
- [ ] Security review completed if vendor, integration, credentials, or external access is involved
- [ ] Clinical safety review completed if patient-specific clinical content is involved
- [ ] Revenue-cycle review completed if coding, claims, billing, authorization, or denial appeal is involved
- [ ] User training or guidance drafted
- [ ] Monitoring owner named
- [ ] Rollback or restriction path documented

## 6. Required evidence before expansion

- [ ] Pilot results reviewed
- [ ] Feedback reviewed and closed or assigned
- [ ] Safety events reviewed
- [ ] Workflow burden reviewed
- [ ] Equity or subgroup concerns reviewed
- [ ] Vendor release notes reviewed
- [ ] Risk tier re-confirmed
- [ ] Monitoring cadence updated
- [ ] Approval body decision recorded

## 7. PHI handling note

Do not place PHI in this repository. Use references to approved internal evidence locations instead of copying screenshots, prompts, patient identifiers, notes, labs, MRNs, or chart content.
