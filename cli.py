# /// script
# requires-python = ">=3.11"
# dependencies = [
#   "pydantic>=2.0.0",
#   "agentfield>=0.1.35",
#   "httpx>=0.27.0",
# ]
# ///
"""CLI & Campaign Pack Exporter for 8b-is `linkedin-outreach-agent`.

Usage:
  # List all 15 preloaded Tier-1 AI Lab & Tokyo B2B targets
  uv run python cli.py --list

  # Generate a single prospect sequence deterministically (instant)
  uv run python cli.py --prospect "Llion Jones" --lab "Sakana AI"

  # Export all 15 Tier-1 AI Lab + Tokyo B2B sequences to Markdown or JSON
  uv run python cli.py --all --export-md ./8b_linkedin_outreach_playbook.md

  # Dispatch through the live AgentField Depth-4 Multi-Reasoner Control Plane
  uv run python cli.py --live-af --prospect "Llion Jones" --lab "Sakana AI"
"""

from __future__ import annotations

import argparse
import json
import os
import time
import urllib.request
from pathlib import Path
from typing import Any

from reasoners.helpers import (
    CURATED_PRECISION_SEQUENCES,
    PROOF_CITATION_REGISTRY,
    PROSPECT_DOSSIER_CATALOG,
    enforce_char_limit,
    fallback_connection_note,
    fallback_followup_sequence,
    fallback_offer_framing,
    fallback_technical_bridge,
    resolve_prospect_dossier,
)


def build_offline_campaign_pack(
    prospect_name: str,
    company_or_lab: str,
    outreach_goal: str = "frontier_lab_collab",
    custom_context: str = "",
) -> dict[str, Any]:
    """Generates a complete, deterministic, char-verified campaign pack for a prospect."""
    dossier = resolve_prospect_dossier(
        prospect_name=prospect_name,
        company_or_lab=company_or_lab,
        outreach_goal=outreach_goal,
        custom_context=custom_context,
    )
    norm_key = dossier["prospect_name"].strip().lower()
    curated = CURATED_PRECISION_SEQUENCES.get(norm_key, {})

    conn_fallback = fallback_connection_note(dossier)
    seq_fallback = fallback_followup_sequence(dossier)
    bridge = fallback_technical_bridge(dossier)
    offer = fallback_offer_framing(dossier)

    conn_note = enforce_char_limit(
        curated.get("connection_note_300", conn_fallback.note_text), 300
    )
    day1_dm = enforce_char_limit(
        curated.get("day1_followup_dm", seq_fallback.day1_dm), 450
    )
    day3_drop = enforce_char_limit(seq_fallback.day3_artifact_drop, 850)
    day7_cta = enforce_char_limit(seq_fallback.day7_cta, 350)

    return {
        "prospect": {
            "name": dossier["prospect_name"],
            "role": dossier["role"],
            "company_or_lab": dossier["company_or_lab"],
            "location": dossier["location"],
        },
        "routing": {
            "primary_track": dossier["recommended_track"],
            "active_citation_ids": dossier["recommended_citations"],
        },
        "technical_bridge": bridge.model_dump(),
        "offer": offer.model_dump(),
        "governance_status": "APPROVED_READY_TO_SEND",
        "final_sequence": {
            "connection_note_300": conn_note,
            "connection_note_char_count": len(conn_note),
            "day1_followup_dm": day1_dm,
            "day1_dm_char_count": len(day1_dm),
            "day3_technical_drop": day3_drop,
            "day3_drop_char_count": len(day3_drop),
            "day7_closing_cta": day7_cta,
            "day7_cta_char_count": len(day7_cta),
        },
        "provenance_citations": [
            PROOF_CITATION_REGISTRY[cid]
            for cid in dossier["recommended_citations"]
            if cid in PROOF_CITATION_REGISTRY
        ],
    }


def dispatch_live_agentfield(
    server_url: str,
    node_id: str,
    prospect_name: str,
    company_or_lab: str,
    outreach_goal: str,
    custom_context: str,
    model: str | None = None,
) -> dict[str, Any]:
    """Dispatches an async execution to the live AgentField control plane and polls to completion."""
    payload: dict[str, Any] = {
        "input": {
            "prospect_name": prospect_name,
            "company_or_lab": company_or_lab,
            "outreach_goal": outreach_goal,
            "custom_context": custom_context,
        }
    }
    if model:
        payload["input"]["model"] = model

    req = urllib.request.Request(
        f"{server_url.rstrip('/')}/api/v1/execute/async/{node_id}.run_outreach_campaign",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=15) as resp:
        submit_data = json.loads(resp.read().decode("utf-8"))

    exec_id = submit_data["execution_id"]
    poll_url = f"{server_url.rstrip('/')}/api/v1/executions/{exec_id}"

    for _ in range(90):
        with urllib.request.urlopen(poll_url, timeout=10) as poll_resp:
            status_data = json.loads(poll_resp.read().decode("utf-8"))
        st = status_data.get("status")
        if st == "succeeded":
            return status_data.get("result", status_data)
        if st in ("failed", "cancelled", "timeout"):
            raise RuntimeError(f"AgentField execution {exec_id} failed: {json.dumps(status_data)}")
        time.sleep(2)
    raise TimeoutError(f"Timed out polling execution {exec_id}")


def render_markdown_playbook(packs: list[dict[str, Any]]) -> str:
    """Renders a list of campaign packs into a clean Markdown outreach playbook."""
    lines = [
        "# 8b-is // Project Omni — LinkedIn Outreach Playbook (Tier-1 Open-Weight AI Labs & Tokyo B2B Sprints)",
        "",
        "> Generated by `linkedin-outreach-agent` · All Connection Notes Verified `≤ 300` Chars · Zero AI-Slop · Grounded in `8b-is` Proof Registry",
        "",
    ]
    for idx, p in enumerate(packs, start=1):
        pr = p["prospect"]
        seq = p["final_sequence"]
        cits = ", ".join(c["id"] for c in p["provenance_citations"])
        lines.extend(
            [
                f"## {idx}. {pr['name']} — {pr['role']} @ **{pr['company_or_lab']}**",
                f"- **Location**: {pr['location']} | **Track**: `{p['routing']['primary_track']}` | **Citations**: `{cits}`",
                f"- **Technical Bridge**: {p['technical_bridge']['hook_thesis']}",
                f"- **Offer / Milestone**: {p['offer']['offer_headline']}",
                "",
                f"### Connection Request Note (`{seq['connection_note_char_count']}/300` chars)",
                "```text",
                seq["connection_note_300"],
                "```",
                "",
                f"### Day 1 Follow-Up DM (`{seq['day1_dm_char_count']}/450` chars)",
                "```text",
                seq["day1_followup_dm"],
                "```",
                "",
                f"### Day 3 Technical Proof Drop (`{seq['day3_drop_char_count']}` chars)",
                "```text",
                seq["day3_technical_drop"],
                "```",
                "",
                f"### Day 7 Low-Friction CTA (`{seq['day7_cta_char_count']}` chars)",
                "```text",
                seq["day7_closing_cta"],
                "```",
                "",
                "---",
                "",
            ]
        )
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="8b-is LinkedIn Outreach Agent CLI")
    parser.add_argument("--list", action="store_true", help="List all 15 preloaded targets")
    parser.add_argument("--all", action="store_true", help="Generate packs for all 15 targets")
    parser.add_argument("--prospect", type=str, default="Llion Jones", help="Prospect full name")
    parser.add_argument("--lab", type=str, default="Sakana AI", help="Company or AI lab")
    parser.add_argument(
        "--goal",
        type=str,
        default="frontier_lab_collab",
        help="Outreach goal (frontier_lab_collab | turnkey_sprint | tokyo_in_person_demo)",
    )
    parser.add_argument("--context", type=str, default="", help="Extra custom context")
    parser.add_argument("--export-md", type=str, default="", help="Path to export Markdown playbook")
    parser.add_argument("--export-json", type=str, default="", help="Path to export JSON packs")
    parser.add_argument(
        "--live-af",
        action="store_true",
        help="Execute via live AgentField control plane instead of local deterministic pack",
    )
    parser.add_argument(
        "--server",
        type=str,
        default=os.getenv("AGENTFIELD_SERVER", "http://localhost:8080"),
        help="AgentField control plane URL",
    )
    parser.add_argument("--model", type=str, default=None, help="Optional model override")
    args = parser.parse_args()

    if args.list:
        for idx, (_, d) in enumerate(PROSPECT_DOSSIER_CATALOG.items(), start=1):
            print(
                f"{idx:2d}. {d['prospect_name']:22s} | {d['company_or_lab']:16s} | "
                f"{d['role']:38s} | track={d['recommended_track']}"
            )
        return

    if args.all:
        packs = [
            build_offline_campaign_pack(
                prospect_name=d["prospect_name"],
                company_or_lab=d["company_or_lab"],
                outreach_goal=(
                    "turnkey_sprint"
                    if d["recommended_track"] == "b2b_turnkey_sprint"
                    else "frontier_lab_collab"
                ),
            )
            for d in PROSPECT_DOSSIER_CATALOG.values()
        ]
    elif args.live_af:
        node_id = os.getenv("AGENT_NODE_ID", "linkedin-outreach-agent")
        pack = dispatch_live_agentfield(
            server_url=args.server,
            node_id=node_id,
            prospect_name=args.prospect,
            company_or_lab=args.lab,
            outreach_goal=args.goal,
            custom_context=args.context,
            model=args.model,
        )
        packs = [pack]
    else:
        packs = [
            build_offline_campaign_pack(
                prospect_name=args.prospect,
                company_or_lab=args.lab,
                outreach_goal=args.goal,
                custom_context=args.context,
            )
        ]

    if args.export_md:
        md_path = Path(args.export_md)
        md_path.write_text(render_markdown_playbook(packs), encoding="utf-8")
        print(f"Wrote Markdown playbook ({len(packs)} targets) to {md_path}")

    if args.export_json:
        json_path = Path(args.export_json)
        json_path.write_text(json.dumps(packs, indent=2), encoding="utf-8")
        print(f"Wrote JSON campaign packs ({len(packs)} targets) to {json_path}")

    if not args.export_md and not args.export_json:
        print(json.dumps(packs[0] if len(packs) == 1 else packs, indent=2))


if __name__ == "__main__":
    main()
