"""Claim creation and evidence de-duplication for verification workflows."""

from typing import Iterable, List
from uuid import uuid4

from backend.app.schemas.verification import ClaimEvidenceRecord, VerifiableClaim


class ClaimService:
    """Creates verifiable claims and preserves unique, source-linked evidence."""

    def create_claim(self, claim_text: str, claim_id: str | None = None) -> VerifiableClaim:
        """Create a claim without assigning a confidence score."""
        return VerifiableClaim(id=claim_id or str(uuid4()), claim_text=claim_text)

    def deduplicate_evidence(self, evidence: Iterable[ClaimEvidenceRecord]) -> List[ClaimEvidenceRecord]:
        """Keep each exact source excerpt once while retaining different sources' evidence."""
        unique_evidence: List[ClaimEvidenceRecord] = []
        seen = set()
        for item in evidence:
            key = (item.source_url.rstrip("/"), item.evidence_text.strip(), item.relation.value)
            if key not in seen:
                seen.add(key)
                unique_evidence.append(item)
        return unique_evidence
