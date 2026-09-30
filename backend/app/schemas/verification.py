"""Pydantic contracts for transparent, source-preserving claim verification."""

from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field


class EvidenceRelation(str, Enum):
    SUPPORTS = "supports"
    CONTRADICTS = "contradicts"


class VerificationStatus(str, Enum):
    SUPPORTED = "supported"
    CONFLICTING = "conflicting"
    INSUFFICIENT_EVIDENCE = "insufficient_evidence"


class VerifiableClaim(BaseModel):
    """A claim to verify without an ungrounded confidence score."""

    id: str
    claim_text: str = Field(min_length=1)


class ClaimEvidenceRecord(BaseModel):
    """An exact evidence excerpt and the source's stated relationship to a claim."""

    evidence_text: str = Field(min_length=1)
    source_id: Optional[str] = None
    source_url: str = Field(min_length=1)
    source_title: str = Field(min_length=1)
    relation: EvidenceRelation


class EvidenceConflict(BaseModel):
    """An explicit contradictory evidence set retained for human review."""

    claim_id: str
    claim_text: str
    supporting_evidence: List[ClaimEvidenceRecord] = Field(default_factory=list)
    contradicting_evidence: List[ClaimEvidenceRecord] = Field(default_factory=list)


class ClaimVerificationResult(BaseModel):
    """Verification outcome with all unique evidence and detected conflicts."""

    claim: VerifiableClaim
    status: VerificationStatus
    evidence: List[ClaimEvidenceRecord] = Field(default_factory=list)
    conflicts: List[EvidenceConflict] = Field(default_factory=list)
