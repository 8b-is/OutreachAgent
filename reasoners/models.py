"""Flat Pydantic schemas for linkedin-outreach-agent.

Contract rules enforced here:
- Every schema passed to `.ai(schema=...)` has 2-4 flat fields (no deep nesting).
- Every `.ai()` gate/specialist schema includes `confident: bool` with a deterministic
  fallback constructor in `helpers.py`.
"""

from pydantic import BaseModel, Field


class TrackRoutingDecision(BaseModel):
    """Layer 2 intake decision selecting outreach track and proof citations."""

    primary_track: str = Field(
        description=(
            "One of: tokyo_in_person_hardware, verifiable_rl_environments, "
            "ssm_hardware_codesign, swe_agent_compression, b2b_turnkey_sprint"
        )
    )
    active_citation_ids: list[str] = Field(
        description="2-4 citation IDs from the 8b-is proof registry (e.g. CIT-OMNI-ESP32, CIT-HEADROOMZ-MOE)"
    )
    routing_rationale: str = Field(
        description="One concise sentence explaining why this track matches the prospect"
    )
    confident: bool = Field(
        description="True only when prospect signals clearly map to a specific track"
    )


class TechnicalBridgeAnalysis(BaseModel):
    """Layer 3 specialist output mapping prospect papers/repos to 8b-is artifacts."""

    hook_thesis: str = Field(
        description="Concrete 1-2 sentence technical bridge linking prospect work to 8b-is"
    )
    matched_citation_ids: list[str] = Field(
        description="Citation IDs directly supporting the technical bridge"
    )
    confident: bool = Field(
        description="True if specific paper, repo, or engineering hook is verified"
    )


class OfferFraming(BaseModel):
    """Layer 3 specialist output framing the concrete demo, sprint, or lab collaboration."""

    offer_headline: str = Field(
        description="Specific collaboration or fixed-scope sprint offer"
    )
    concrete_deliverable: str = Field(
        description="Exact artifact, live benchmark, or 7-day deliverable"
    )
    confident: bool = Field(
        description="True if offer matches prospect role and geographic/technical context"
    )


class ConnectionNoteDraft(BaseModel):
    """Layer 3 specialist output for the initial LinkedIn connection request (<=300 chars)."""

    note_text: str = Field(
        description="LinkedIn connection request note strictly under 285 characters, zero fluff"
    )
    hook_used: str = Field(
        description="Exact paper, model, or system referenced in the opening line"
    )
    confident: bool = Field(
        description="True if note is grounded, under 300 chars, and free of AI cliches"
    )


class FollowupSequenceDraft(BaseModel):
    """Layer 3 specialist output for the post-connection 3-touch DM sequence."""

    day1_dm: str = Field(
        description="Day 1 follow-up DM after connection acceptance (<=420 chars)"
    )
    day3_artifact_drop: str = Field(
        description="Day 3 technical proof drop with specific 8b-is repo/dataset/silicon metrics (<=750 chars)"
    )
    day7_cta: str = Field(
        description="Day 7 low-friction closing CTA (<=320 chars)"
    )
    confident: bool = Field(
        description="True if all 3 touches cite real 8b-is metrics without buzzwords"
    )


class CitationVerificationVerdict(BaseModel):
    """Layer 4 deep verifier checking that drafted claims match canonical 8b-is citations."""

    all_claims_grounded: bool = Field(
        description="True only if every metric and repo cited matches the canonical registry"
    )
    verified_citation_ids: list[str] = Field(
        description="Citation IDs confirmed present and accurately stated in the draft"
    )
    discrepancy_note: str = Field(
        description="Empty string if grounded, or exact discrepancy to fix"
    )
    confident: bool = Field(
        description="True if verification against registry is unambiguous"
    )


class AdversarialAuditResult(BaseModel):
    """Layer 3->4 adversarial challenger verdict (HUNT -> PROVE)."""

    passed_audit: bool = Field(
        description="True only if zero AI slop, zero ungrounded claims, and all char limits hold"
    )
    slop_or_hallucination_flags: list[str] = Field(
        description="Specific issues found (cliches, unverified numbers, char overflow)"
    )
    revision_directive: str = Field(
        description="Exact surgical instruction for the reconciler to fix any flags"
    )
    confident: bool = Field(
        description="True if audit judgement is definitive"
    )


class ReconciledCampaignOutput(BaseModel):
    """Final reconciled LinkedIn outreach sequence after adversarial audit."""

    connection_note_300: str = Field(
        description="Final LinkedIn connection note strictly <=300 characters"
    )
    day1_followup_dm: str = Field(
        description="Final Day 1 DM strictly <=450 characters"
    )
    day3_technical_drop: str = Field(
        description="Final Day 3 technical artifact drop with verifiable repo/HF/silicon citations"
    )
    confident: bool = Field(
        description="True if sequence is ready to send without human rewrite"
    )
