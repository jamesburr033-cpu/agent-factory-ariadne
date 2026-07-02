# AI Risk Review

Use this document after intake to decide whether an AI feature is acceptable, blocked, or acceptable only with constraints.

## 1. Review summary

| Field | Response |
| --- | --- |
| Feature name |  |
| Review date |  |
| Review owner |  |
| Business owner |  |
| Clinical owner |  |
| Current decision |  |
| Next review date |  |

## 2. Risk tier

| Tier | Description | Selected |
| --- | --- | --- |
| Tier 1, minimal risk | General productivity with no PHI and no patient-specific decision support. |  |
| Tier 2, controlled operational risk | Uses healthcare context but requires human review and does not directly determine care, payment, or access. |  |
| Tier 3, high impact | Influences clinical, coding, authorization, denial, access, or patient communication decisions. |  |
| Tier 4, restricted or blocked | Safety-critical, insufficient transparency, unacceptable privacy risk, or no clear accountable owner. |  |

Risk tier rationale:

## 3. NIST AI RMF style mapping

| Function | Review questions | Notes |
| --- | --- | --- |
| Govern | Who owns the feature, policy, approvals, and exceptions? |  |
| Map | What workflow, users, patients, data, and harm pathways are in scope? |  |
| Measure | How will safety, accuracy, bias, privacy, security, usability, and drift be tested? |  |
| Manage | What controls, monitoring, rollback, training, and escalation paths are required? |  |

## 4. Healthcare risk domains

| Domain | Key question | Risk rating | Required control |
| --- | --- | --- | --- |
| Clinical safety | Could the output mislead a clinician, patient, coder, or staff member? |  |  |
| Privacy | Is PHI used, disclosed, retained, logged, or sent externally? |  |  |
| Security | Does the feature introduce new access, credential, integration, or vendor risk? |  |  |
| Bias and equity | Could output quality differ by language, race, age, disability, sex, insurance, or socioeconomic factors? |  |  |
| Transparency | Can users tell when AI is involved and what they must verify? |  |  |
| Workflow fit | Does the feature increase burden, confusion, delays, or unsafe shortcuts? |  |  |
| Revenue integrity | Could it affect coding, billing, denial appeal, authorization, or medical necessity? |  |  |
| Legal and compliance | Are policies, contracts, BAAs, retention rules, and audit expectations addressed? |  |  |
| Monitoring | Is there a named owner for post-go-live review and drift monitoring? |  |  |

Risk rating scale: Low, Moderate, High, Critical, Unknown.

## 5. Required controls

Check all controls required before pilot or go-live.

- [ ] Named accountable owner
- [ ] Approved scope and prohibited uses
- [ ] Minimum necessary PHI review
- [ ] Security review
- [ ] Privacy review
- [ ] Compliance review
- [ ] Clinical safety review
- [ ] Revenue-cycle review
- [ ] Bias and equity review
- [ ] User training and attestation language
- [ ] Clear AI disclosure or labeling
- [ ] Human review requirement
- [ ] Audit log or evidence trail
- [ ] Feedback monitoring process
- [ ] Rollback or disablement plan
- [ ] Vendor responsibility clarification
- [ ] Monitoring cadence and drift thresholds

## 6. Vendor and platform responsibility questions

Use these when reviewing Epic AI, vendor AI, or any hosted AI capability.

1. What part of the model, prompt, workflow, or feature is controlled by the vendor?
2. What configuration choices are owned by the healthcare organization?
3. Who monitors user feedback submitted inside the product?
4. What is the expected turnaround time for vendor review of safety or quality feedback?
5. Who reviews model drift, feature drift, prompt changes, or output-quality changes?
6. How are release notes, model updates, and changed behavior communicated?
7. What audit logs are available to the organization?
8. What data is retained, for how long, and where?
9. Is customer data used for model training, tuning, evaluation, or vendor analytics?
10. What evidence can the vendor provide for validation, known limitations, and subgroup performance?
11. What happens if the organization disables the feature?
12. What support path exists for urgent safety concerns?

## 7. Approval decision

| Decision | Meaning | Selected |
| --- | --- | --- |
| Approved | Acceptable for defined use with listed controls. |  |
| Approved with restrictions | Acceptable only with additional limits, monitoring, or phased rollout. |  |
| Pilot only | May be tested with limited users, limited data, and enhanced monitoring. |  |
| Needs remediation | Cannot proceed until required gaps are closed. |  |
| Blocked | Risk is not acceptable for the proposed use. |  |

Decision rationale:

Required restrictions:

Required follow-up evidence:

Final reviewer:
