"""Layer 3 & Layer 4 specialist reasoners for linkedin-outreach-agent.

Registered via `AgentRouter(prefix="", tags=["specialist"])` so reasoner IDs match
function names cleanly (`extract_technical_bridge`, `structure_commercial_or_collab_offer`,
`draft_connection_note`, `draft_multitouch_sequence`, `verify_citation_grounding`).
"""

from __future__ import annotations

import os
from typing import Any

from agentfield import AgentRouter

from .helpers import (
    PROOF_CITATION_REGISTRY,
    enforce_char_limit,
    fallback_citation_verdict,
    fallback_connection_note,
    fallback_followup_sequence,
    fallback_offer_framing,
    fallback_technical_bridge,
    render_registry_subset_to_prose,
    safe_ai_gate,
)
from .models import (
    CitationVerificationVerdict,
    ConnectionNoteDraft,
    FollowupSequenceDraft,
    OfferFraming,
    TechnicalBridgeAnalysis,
)

NODE_ID = os.getenv("AGENT_NODE_ID", "linkedin-outreach-agent")
router = AgentRouter(prefix="", tags=["specialist"])


@router.reasoner(tags=["research", "layer3"])
async def extract_technical_bridge(
    dossier_prose: str,
    selected_track: str,
    active_citation_ids: list[str],
    fallback_dossier: dict[str, Any],
    model: str | None = None,
) -> TechnicalBridgeAnalysis:
    """Maps the prospect's specific papers, models, or repos to 8b-is proof citations."""
    registry_prose = render_registry_subset_to_prose(active_citation_ids)
    result = await safe_ai_gate(
        router,
        system=(
            "You are a principal AI systems researcher at 8b-is. Given a prospect dossier "
            "and canonical 8b-is proof citations, formulate a razor-sharp 1-2 sentence "
            "technical bridge connecting their exact published work (e.g. CTM, Hermes 4, "
            "INTELLECT-3/TOPLOC, Zamba2/ZAYA1, Laguna/RLCEF) to our verified hardware or "
            "formal sufficiency artifacts. Never invent metrics outside the registry. "
            "Set confident=true only if the technical connection is specific and grounded."
        ),
        user=(
            f"Outreach Track: {selected_track}\n\n"
            f"Prospect Dossier:\n{dossier_prose}\n\n"
            f"Active 8b-is Citations:\n{registry_prose}"
        ),
        schema=TechnicalBridgeAnalysis,
        model=model,
        fallback_fn=lambda: fallback_technical_bridge(fallback_dossier),
    )
    if not result.hook_thesis.strip():
        return fallback_technical_bridge(fallback_dossier)

    valid_ids = [cid for cid in result.matched_citation_ids if cid in PROOF_CITATION_REGISTRY]
    if not valid_ids:
        valid_ids = [cid for cid in active_citation_ids if cid in PROOF_CITATION_REGISTRY] or [
            "CIT-HEADROOMZ-MOE"
        ]
    result.matched_citation_ids = valid_ids
    return result


@router.reasoner(tags=["offer", "layer3"])
async def structure_commercial_or_collab_offer(
    dossier_prose: str,
    selected_track: str,
    fallback_dossier: dict[str, Any],
    model: str | None = None,
) -> OfferFraming:
    """Structures a track-appropriate collaboration milestone or Zone 1 7-day Turnkey Sprint."""
    result = await safe_ai_gate(
        router,
        system=(
            "You structure high-signal technical collaborations and fixed-scope engineering "
            "sprints for 8b-is (Project Omni Tokyo-to-Vietnam Sprint).\n"
            "- If track == 'tokyo_in_person_hardware': offer a 12-minute live in-person demo "
            "in Tokyo (Azabudai Hills / Shinjuku / TIB Nov 7 Finale) of our Pocket Omni ESP32 "
            "ternary rig (4,096 trit ops in 18 us) + 8b.HeadroomZ.\n"
            "- If track == 'verifiable_rl_environments': offer to co-publish a verifiable "
            "Context-Compression RL Environment using PeetPedro/headroomz-compression-traces "
            "and (pi, V_pi, R_pi) projection certificates.\n"
            "- If track == 'ssm_hardware_codesign': offer a joint pJ/trit & router latency "
            "benchmark on Omni Rev-A Zynq UltraScale+ (1.84 TOPS @ 450 MHz, 0 DSPs).\n"
            "- If track == 'swe_agent_compression': offer a live benchmark of 8b.HeadroomZ "
            "(85.33% tool output compression) + arnauth PQ capability envelopes on their coding agent.\n"
            "- If track == 'b2b_turnkey_sprint': offer a 7-day fixed-scope Turnkey Sprint "
            "(PKG_A $6.5k Ternary Edge, PKG_B $9.5k Zig/eBPF, or PKG_C $12.5k Agent Graph, 50% upfront)."
        ),
        user=f"Selected Track: {selected_track}\n\n{dossier_prose}",
        schema=OfferFraming,
        model=model,
        fallback_fn=lambda: fallback_offer_framing(fallback_dossier),
    )
    if not result.offer_headline.strip():
        return fallback_offer_framing(fallback_dossier)
    return result


@router.reasoner(tags=["copywriting", "layer3"])
async def draft_connection_note(
    dossier_prose: str,
    selected_track: str,
    fallback_dossier: dict[str, Any],
    model: str | None = None,
) -> ConnectionNoteDraft:
    """Drafts a LinkedIn connection request note strictly <= 300 characters."""
    result = await safe_ai_gate(
        router,
        system=(
            "Write a peer-to-peer founder/researcher LinkedIn connection note from Peter "
            "(8b-is, currently in Tokyo for Project Omni).\n"
            "HARD RULES:\n"
            "1. MAXIMUM 280 characters (LinkedIn hard cap is 300 chars including spaces).\n"
            "2. Open directly with the prospect's first name and their specific work (e.g. CTM, "
            "INTELLECT-3, Hermes 4, Zamba2/ZAYA1, Laguna/RLCEF).\n"
            "3. State ONE concrete 8b-is metric (e.g. '85.3% tool token cut w/ (pi,V_pi,R_pi) "
            "proofs' or '4,096 trit ops in 18us on ESP32 / 1.84 TOPS LUT6').\n"
            "4. Zero AI cliches ('I hope this finds you well', 'synergy', 'game-changing', 'delve')."
        ),
        user=f"Track: {selected_track}\n\n{dossier_prose}",
        schema=ConnectionNoteDraft,
        model=model,
        fallback_fn=lambda: fallback_connection_note(fallback_dossier),
    )
    if not result.note_text.strip():
        return fallback_connection_note(fallback_dossier)

    result.note_text = enforce_char_limit(result.note_text, 300)
    return result


@router.reasoner(tags=["copywriting", "layer3"])
async def draft_multitouch_sequence(
    dossier_prose: str,
    selected_track: str,
    fallback_dossier: dict[str, Any],
    model: str | None = None,
) -> FollowupSequenceDraft:
    """Drafts the post-connection 3-touch LinkedIn DM sequence (Day 1, Day 3, Day 7)."""
    result = await safe_ai_gate(
        router,
        system=(
            "Write a 3-touch LinkedIn DM follow-up sequence from Peter (8b-is) after the "
            "prospect accepts the connection request.\n"
            "- day1_dm (<= 420 chars): Thank them briefly, connect their specific technical "
            "architecture to our verified 8b-is artifact, and propose the concrete low-friction step.\n"
            "- day3_artifact_drop (<= 750 chars): Share concrete technical links/proofs from the "
            "dossier (github.com/8b-is/headroomz, PeetPedro/headroomz-compression-traces, "
            "github.com/8b-is/arnauth, or live Tokyo Pocket Omni ESP32 / Zynq 1.84 TOPS telemetry).\n"
            "- day7_cta (<= 320 chars): Polite, zero-pressure closing note offering an async "
            "benchmark on their traces or a 12-min call/coffee.\n"
            "Never use marketing buzzwords or sycophancy."
        ),
        user=f"Track: {selected_track}\n\n{dossier_prose}",
        schema=FollowupSequenceDraft,
        model=model,
        fallback_fn=lambda: fallback_followup_sequence(fallback_dossier),
    )
    if not result.day1_dm.strip():
        return fallback_followup_sequence(fallback_dossier)

    result.day1_dm = enforce_char_limit(result.day1_dm, 450)
    result.day3_artifact_drop = enforce_char_limit(result.day3_artifact_drop, 800)
    result.day7_cta = enforce_char_limit(result.day7_cta, 350)
    return result


@router.reasoner(tags=["verification", "layer4"])
async def verify_citation_grounding(
    draft_brief_prose: str,
    active_citation_ids: list[str],
    model: str | None = None,
) -> CitationVerificationVerdict:
    """Layer 4 deep verifier invoked by `challenge_outreach_draft` to prove claim grounding."""
    registry_prose = render_registry_subset_to_prose(active_citation_ids)
    verdict = await safe_ai_gate(
        router,
        system=(
            "You are a strict technical fact-checker. Compare the drafted LinkedIn outreach "
            "messages against the canonical 8b-is proof citation registry. Verify that every "
            "numerical metric (e.g. 85.33%, 1.84 TOPS, 450 MHz, 4,096 trit ops in 18 us, "
            "142/142 tests, $6.5k/$9.5k/$12.5k sprints) accurately reflects the registry without "
            "exaggeration or fabrication."
        ),
        user=(
            f"Canonical 8b-is Registry:\n{registry_prose}\n\n"
            f"Drafted Outreach Dossier:\n{draft_brief_prose}"
        ),
        schema=CitationVerificationVerdict,
        model=model,
        fallback_fn=lambda: fallback_citation_verdict(active_citation_ids),
    )
    return verdict
