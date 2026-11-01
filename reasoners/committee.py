"""Layer 2 intake routing, conditional escalation, Layer 3->4 adversarial challenger,
and final campaign reconciler for linkedin-outreach-agent.
"""

from __future__ import annotations

import os
from typing import Any

from agentfield import AgentRouter

from .helpers import (
    PROOF_CITATION_REGISTRY,
    enforce_char_limit,
    fallback_adversarial_audit,
    fallback_reconciled_output,
    fallback_track_routing,
    safe_ai_gate,
    scan_anti_slop_violations,
)
from .models import (
    AdversarialAuditResult,
    CitationVerificationVerdict,
    ConnectionNoteDraft,
    FollowupSequenceDraft,
    ReconciledCampaignOutput,
    TrackRoutingDecision,
)

NODE_ID = os.getenv("AGENT_NODE_ID", "linkedin-outreach-agent")
router = AgentRouter(prefix="", tags=["committee"])

VALID_TRACKS = {
    "tokyo_in_person_hardware",
    "verifiable_rl_environments",
    "ssm_hardware_codesign",
    "swe_agent_compression",
    "b2b_turnkey_sprint",
}


@router.reasoner(tags=["intake", "layer3"])
async def deep_track_escalation(
    dossier_prose: str,
    fallback_dossier: dict[str, Any],
    model: str | None = None,
) -> TrackRoutingDecision:
    """Layer 3 escalation reasoner called when initial track classification is ambiguous."""
    decision = await safe_ai_gate(
        router,
        system=(
            "You are the senior GTM & research strategy lead at 8b-is. The initial intake "
            "router was uncertain or selected invalid citations. Carefully inspect the "
            "prospect's location, published research, and outreach goal to select the single "
            "highest-leverage outreach track from:\n"
            "- tokyo_in_person_hardware (for Tokyo-based labs like Sakana AI or Azabudai/Shinjuku targets)\n"
            "- verifiable_rl_environments (for decentralized RL / post-training labs like Prime Intellect & Nous Research)\n"
            "- ssm_hardware_codesign (for SSM/MoE/hardware co-design labs like Zyphra)\n"
            "- swe_agent_compression (for coding-agent & RLCEF labs like Poolside AI)\n"
            "- b2b_turnkey_sprint (for commercial 7-day fixed-scope engineering sprints)\n"
            "Also select 2-4 valid citation IDs from: CIT-OMNI-ESP32, CIT-OMNI-ZYNQ, "
            "CIT-HEADROOMZ-MOE, CIT-HF-TRACES, CIT-ARNAUTH-PQ, CIT-8B-GRANTS, "
            "CIT-SPRINT-PKG-A, CIT-SPRINT-PKG-B, CIT-SPRINT-PKG-C."
        ),
        user=dossier_prose,
        schema=TrackRoutingDecision,
        model=model,
        fallback_fn=lambda: fallback_track_routing(
            fallback_dossier, reason="deep_track_escalation defaulted to verified dossier"
        ),
    )
    valid_cits = [c for c in decision.active_citation_ids if c in PROOF_CITATION_REGISTRY]
    if decision.primary_track not in VALID_TRACKS or not valid_cits:
        return fallback_track_routing(
            fallback_dossier, reason="deep_track_escalation defaulted to verified dossier"
        )
    decision.active_citation_ids = valid_cits
    return decision


@router.reasoner(tags=["intake", "layer2"])
async def classify_outreach_track(
    dossier_prose: str,
    fallback_dossier: dict[str, Any],
    model: str | None = None,
) -> TrackRoutingDecision:
    """Layer 2 dynamic intake gate classifying the outreach track and active citations."""
    decision = await safe_ai_gate(
        router,
        system=(
            "Classify this LinkedIn outreach campaign into the optimal technical track:\n"
            "1. tokyo_in_person_hardware — Tokyo targets (Sakana AI, Azabudai Hills, TIB Nov 7)\n"
            "2. verifiable_rl_environments — RL environments & verifiable inference (Prime Intellect, Nous Research)\n"
            "3. ssm_hardware_codesign — Hybrid SSM / MoE / hardware co-design (Zyphra)\n"
            "4. swe_agent_compression — Software engineering models & terminal coding agents (Poolside AI)\n"
            "5. b2b_turnkey_sprint — Fixed-scope 7-day B2B engineering sprints ($6.5k/$9.5k/$12.5k)\n"
            "Pick 2-4 citation IDs from the dossier. Set confident=false if uncertain."
        ),
        user=dossier_prose,
        schema=TrackRoutingDecision,
        model=model,
        fallback_fn=lambda: TrackRoutingDecision(
            primary_track="escalate",
            active_citation_ids=[],
            routing_rationale="Escalating to deep_track_escalation.",
            confident=False,
        ),
    )

    valid_cits = [c for c in decision.active_citation_ids if c in PROOF_CITATION_REGISTRY]
    if (
        not decision.confident
        or decision.primary_track not in VALID_TRACKS
        or not valid_cits
    ):
        escalated_dict = await router.call(
            f"{NODE_ID}.deep_track_escalation",
            dossier_prose=dossier_prose,
            fallback_dossier=fallback_dossier,
            model=model,
        )
        return TrackRoutingDecision(**escalated_dict)

    decision.active_citation_ids = valid_cits
    return decision


@router.reasoner(tags=["audit", "layer3"])
async def challenge_outreach_draft(
    draft_brief_prose: str,
    connection_note_text: str,
    day1_dm_text: str,
    active_citation_ids: list[str],
    model: str | None = None,
) -> AdversarialAuditResult:
    """Layer 3 adversarial reviewer (HUNT -> PROVE) that calls Layer 4 `verify_citation_grounding`."""
    deterministic_flags: list[str] = []
    if len(connection_note_text) > 300:
        deterministic_flags.append(
            f"Connection note exceeds 300 chars ({len(connection_note_text)} chars)."
        )
    if len(day1_dm_text) > 450:
        deterministic_flags.append(
            f"Day 1 DM exceeds 450 chars ({len(day1_dm_text)} chars)."
        )
    deterministic_flags.extend(scan_anti_slop_violations(draft_brief_prose))

    citation_dict = await router.call(
        f"{NODE_ID}.verify_citation_grounding",
        draft_brief_prose=draft_brief_prose,
        active_citation_ids=active_citation_ids,
        model=model,
    )
    citation_verdict = CitationVerificationVerdict(**citation_dict)
    if not citation_verdict.all_claims_grounded and citation_verdict.discrepancy_note:
        deterministic_flags.append(
            f"Citation discrepancy: {citation_verdict.discrepancy_note}"
        )

    audit_context_prose = (
        f"{draft_brief_prose}\n\n"
        f"=== LAYER 4 CITATION VERIFICATION ===\n"
        f"All Claims Grounded: {citation_verdict.all_claims_grounded}\n"
        f"Verified Citations: {', '.join(citation_verdict.verified_citation_ids)}\n"
        f"Discrepancy Note: {citation_verdict.discrepancy_note or 'None'}\n"
        f"Deterministic Pre-Check Flags: {'; '.join(deterministic_flags) if deterministic_flags else 'None'}"
    )

    audit = await safe_ai_gate(
        router,
        system=(
            "You are a ruthless adversarial editor reviewing founder-to-founder LinkedIn "
            "outreach to frontier AI researchers. Flag any generic AI phrasing, vague praise, "
            "ungrounded metrics, or bloated sentences. If the draft is sharp, peer-level, "
            "and grounded in the verified citations with zero deterministic flags, set "
            "passed_audit=true."
        ),
        user=audit_context_prose,
        schema=AdversarialAuditResult,
        model=model,
        fallback_fn=lambda: fallback_adversarial_audit(deterministic_flags),
    )

    if deterministic_flags:
        merged_flags = list(dict.fromkeys(deterministic_flags + audit.slop_or_hallucination_flags))
        audit.passed_audit = False
        audit.slop_or_hallucination_flags = merged_flags
    return audit


@router.reasoner(tags=["reconcile", "layer2"])
async def reconcile_campaign_sequence(
    draft_brief_prose: str,
    conn_note_dict: dict[str, Any],
    sequence_dict: dict[str, Any],
    active_citation_ids: list[str],
    model: str | None = None,
) -> dict[str, Any]:
    """Layer 2 reconciler: invokes Layer 3 `challenge_outreach_draft` (which invokes Layer 4
    `verify_citation_grounding`) and produces the final char-verified LinkedIn campaign pack.
    """
    conn_note = ConnectionNoteDraft(**conn_note_dict)
    sequence = FollowupSequenceDraft(**sequence_dict)

    audit_dict = await router.call(
        f"{NODE_ID}.challenge_outreach_draft",
        draft_brief_prose=draft_brief_prose,
        connection_note_text=conn_note.note_text,
        day1_dm_text=sequence.day1_dm,
        active_citation_ids=active_citation_ids,
        model=model,
    )
    audit = AdversarialAuditResult(**audit_dict)

    if audit.passed_audit and not audit.slop_or_hallucination_flags:
        final_conn = enforce_char_limit(conn_note.note_text, 300)
        final_day1 = enforce_char_limit(sequence.day1_dm, 450)
        final_day3 = enforce_char_limit(sequence.day3_artifact_drop, 850)
        final_day7 = enforce_char_limit(sequence.day7_cta, 350)
        reconciled_confident = True
    else:
        revision_prose = (
            f"{draft_brief_prose}\n\n"
            f"=== ADVERSARIAL AUDIT FLAGS TO FIX ===\n"
            f"Flags: {'; '.join(audit.slop_or_hallucination_flags)}\n"
            f"Directive: {audit.revision_directive}\n"
            "Rewrite connection_note_300 (strictly <= 285 chars), day1_followup_dm (<= 420 chars), "
            "and day3_technical_drop (<= 780 chars) to resolve every flag while keeping exact "
            "8b-is citations."
        )
        polished = await safe_ai_gate(
            router,
            system=(
                "You are the final executive editor at 8b-is. Apply the adversarial audit "
                "directives with surgical precision. Preserve exact technical hooks and "
                "keep connection_note_300 strictly under 285 characters."
            ),
            user=revision_prose,
            schema=ReconciledCampaignOutput,
            model=model,
            fallback_fn=lambda: fallback_reconciled_output(conn_note, sequence),
        )
        if not polished.connection_note_300.strip():
            polished = fallback_reconciled_output(conn_note, sequence)
        final_conn = enforce_char_limit(polished.connection_note_300, 300)
        final_day1 = enforce_char_limit(polished.day1_followup_dm, 450)
        final_day3 = enforce_char_limit(polished.day3_technical_drop, 850)
        final_day7 = enforce_char_limit(sequence.day7_cta, 350)
        reconciled_confident = polished.confident

    post_slop = scan_anti_slop_violations(f"{final_conn} {final_day1} {final_day3}")
    governance_status = (
        "APPROVED_READY_TO_SEND"
        if (len(final_conn) <= 300 and len(final_day1) <= 450 and not post_slop)
        else "NEEDS_HUMAN_REVIEW"
    )

    return {
        "governance_status": governance_status,
        "reconciled_confident": reconciled_confident,
        "audit": audit.model_dump(),
        "final_sequence": {
            "connection_note_300": final_conn,
            "connection_note_char_count": len(final_conn),
            "day1_followup_dm": final_day1,
            "day1_dm_char_count": len(final_day1),
            "day3_technical_drop": final_day3,
            "day3_drop_char_count": len(final_day3),
            "day7_closing_cta": final_day7,
            "day7_cta_char_count": len(final_day7),
        },
    }
