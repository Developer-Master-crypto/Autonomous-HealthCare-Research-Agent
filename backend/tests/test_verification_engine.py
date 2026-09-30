"""Tests for transparent research evidence verification and conflict detection."""

from backend.app.schemas.verification import (
    ClaimEvidenceRecord,
    EvidenceRelation,
    VerificationStatus,
)
from backend.app.services.claim_service import ClaimService
from backend.app.services.verification_service import VerificationService


def evidence(url: str, relation: EvidenceRelation, text: str = "Cardiology is listed.") -> ClaimEvidenceRecord:
    return ClaimEvidenceRecord(
        source_url=url,
        source_title="Source title",
        evidence_text=text,
        relation=relation,
    )


def claim():
    return ClaimService().create_claim("Hospital X provides cardiology services.", claim_id="claim-1")


def test_agreement_from_independent_sources_is_supported():
    result = VerificationService().verify_claim(claim(), [
        evidence("https://hospital.example/services", EvidenceRelation.SUPPORTS),
        evidence("https://registry.example/hospital-x", EvidenceRelation.SUPPORTS),
    ])
    assert result.status == VerificationStatus.SUPPORTED
    assert result.conflicts == []


def test_disagreement_preserves_both_evidence_sets():
    supporting = evidence("https://hospital.example/services", EvidenceRelation.SUPPORTS, "Cardiology is available.")
    contradicting = evidence("https://directory.example/hospital-x", EvidenceRelation.CONTRADICTS, "Cardiology service is unavailable.")
    result = VerificationService().verify_claim(claim(), [supporting, contradicting])
    assert result.status == VerificationStatus.CONFLICTING
    assert result.conflicts[0].supporting_evidence == [supporting]
    assert result.conflicts[0].contradicting_evidence == [contradicting]


def test_single_source_is_insufficient_evidence():
    result = VerificationService().verify_claim(claim(), [evidence("https://hospital.example/services", EvidenceRelation.SUPPORTS)])
    assert result.status == VerificationStatus.INSUFFICIENT_EVIDENCE


def test_no_evidence_is_insufficient_evidence():
    result = VerificationService().verify_claim(claim(), [])
    assert result.status == VerificationStatus.INSUFFICIENT_EVIDENCE


def test_duplicate_evidence_does_not_count_as_independent_support():
    item = evidence("https://hospital.example/services", EvidenceRelation.SUPPORTS)
    result = VerificationService().verify_claim(claim(), [item, item])
    assert result.status == VerificationStatus.INSUFFICIENT_EVIDENCE
    assert result.evidence == [item]
