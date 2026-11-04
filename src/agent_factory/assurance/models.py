"""Versioned, strictly validated records for synthetic-only actions."""
from __future__ import annotations

import hashlib
import json
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, computed_field


def canonical_json(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode("utf-8")


def sha256(value: object) -> str:
    return hashlib.sha256(canonical_json(value)).hexdigest()


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class ActionIntent(StrictModel):
    schema_version: Literal["1"] = "1"
    run_id: str = Field(min_length=1, max_length=128)
    action_id: str = Field(min_length=1, max_length=128)
    proposer_agent: str = Field(min_length=1, max_length=128)
    tool_id: str = Field(min_length=1, max_length=128)
    operation: str = Field(min_length=1, max_length=128)
    target: str = Field(min_length=1, max_length=128)
    arguments: dict[str, str]

    @computed_field
    @property
    def arguments_sha256(self) -> str:
        return sha256(self.arguments)


class ReviewDecision(StrictModel):
    """A demo approval; NOT an authenticated human identity."""
    run_id: str = Field(min_length=1)
    action_id: str = Field(min_length=1)
    arguments_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    reviewer_principal: str = Field(min_length=1)
    review_source: Literal["synthetic_test_fixture"]
    decision: Literal["approved", "rejected", "needs_revision"]


class CapabilityGrant(StrictModel):
    schema_version: Literal["1"] = "1"
    grant_id: str
    run_id: str
    action_id: str
    arguments_sha256: str
    tool_id: str
    operation: str
    target: str
    issued_at: int
    expires_at: int
    max_uses: Literal[1] = 1
    policy_version: Literal["aa-001-synthetic-v1"] = "aa-001-synthetic-v1"
    issuer: Literal["synthetic_demo_authority"] = "synthetic_demo_authority"
    signature: str

    def signed_payload(self) -> dict[str, object]:
        return self.model_dump(exclude={"signature"})


class DispatchResult(StrictModel):
    action_id: str
    status: Literal["blocked", "observed_succeeded", "observed_failed", "unknown_effect"]
    reason: str
    observed_state_sha256: str | None = None
