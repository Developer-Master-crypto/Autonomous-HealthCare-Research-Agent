"""Explicit evidence-conflict detection that never discards either side."""

from typing import Iterable, List

from backend.app.schemas.verification import (
    ClaimEvidenceRecord,
    EvidenceConflict,
    EvidenceRelation,
    VerifiableClaim,
)


class ConflictService:
    """Creates reviewable conflicts from explicit contradicting evidence."""

    def detect(self, claim: VerifiableClaim, evidence: Iterable[ClaimEvidenceRecord]) -> List[EvidenceConflict]:
        """Return a conflict when any source explicitly contradicts the claim."""
        evidence_list = list(evidence)
        contradicting = [item for item in evidence_list if item.relation == EvidenceRelation.CONTRADICTS]
        if not contradicting:
            return []
        supporting = [item for item in evidence_list if item.relation == EvidenceRelation.SUPPORTS]
        return [EvidenceConflict(
            claim_id=claim.id,
            claim_text=claim.claim_text,
            supporting_evidence=supporting,
            contradicting_evidence=contradicting,
        )]
