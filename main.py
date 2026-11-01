"""LinkedIn Outreach Multi-Reasoner Agent for 8b-is & Project Omni.

Entry reasoner: `linkedin-outreach-agent.run_outreach_campaign`
Architecture:   Dynamic Track Routing + Parallel Specialist Hunters + HUNT->PROVE Adversarial Audit (Depth 4)
"""

from __future__ import annotations

import asyncio
import os
from typing import Any

from agentfield import AIConfig, Agent
from fastapi import Request
from fastapi.responses import HTMLResponse, JSONResponse

from dispatcher import LOG_PATH, TARGET_LINKEDIN_URLS, run_playwright_campaign
from reasoners import committee_router, specialists_router
from reasoners.helpers import (
    PROOF_CITATION_REGISTRY,
    PROSPECT_DOSSIER_CATALOG,
    fallback_connection_note,
    fallback_followup_sequence,
    render_dossier_to_prose,
    render_specialist_drafts_to_prose,
    resolve_prospect_dossier,
)
from reasoners.models import (
    ConnectionNoteDraft,
    FollowupSequenceDraft,
    OfferFraming,
    TechnicalBridgeAnalysis,
    TrackRoutingDecision,
)

app = Agent(
    node_id=os.getenv("AGENT_NODE_ID", "linkedin-outreach-agent"),
    agentfield_server=os.getenv("AGENTFIELD_SERVER", "http://localhost:8080"),
    version="1.0.0",
    description=(
        "8b-is & Project Omni multi-reasoner LinkedIn outreach engine targeting "
        "Tier-1 open-weight AI labs (Sakana AI, Nous Research, Prime Intellect, "
        "Zyphra, Poolside AI) and Tokyo B2B 7-day Turnkey Sprints."
    ),
    ai_config=AIConfig(
        model=os.getenv("AI_MODEL", "openrouter/google/gemini-2.5-flash"),
    ),
    dev_mode=True,
)

app.include_router(committee_router)
app.include_router(specialists_router)


# ---------------------------------------------------------------------------
# Deterministic @app.skill() Capabilities
# ---------------------------------------------------------------------------


@app.skill(tags=["catalog", "deterministic"])
def lookup_prospect_and_proof_dossier(
    prospect_name: str,
    company_or_lab: str,
    outreach_goal: str = "frontier_lab_collab",
    custom_context: str = "",
) -> dict[str, Any]:
    """Deterministically resolves a prospect profile and canonical 8b-is proof citations."""
    return resolve_prospect_dossier(
        prospect_name=prospect_name,
        company_or_lab=company_or_lab,
        outreach_goal=outreach_goal,
        custom_context=custom_context,
    )


@app.skill(tags=["catalog", "deterministic"])
def list_tier1_lab_targets() -> dict[str, Any]:
    """Returns all preloaded Tier-1 AI Lab founders/researchers and 8b-is proof citations."""
    targets = [
        {
            "key": key,
            "prospect_name": val["prospect_name"],
            "role": val["role"],
            "company_or_lab": val["company_or_lab"],
            "location": val["location"],
            "recommended_track": val["recommended_track"],
            "recommended_citations": val["recommended_citations"],
        }
        for key, val in PROSPECT_DOSSIER_CATALOG.items()
    ]
    return {
        "total_targets": len(targets),
        "targets": targets,
        "citations": PROOF_CITATION_REGISTRY,
    }


# ---------------------------------------------------------------------------
# Layer 1 Public Entry Reasoner (`tags=["entry"]`)
# ---------------------------------------------------------------------------


@app.reasoner(tags=["entry"])
async def run_outreach_campaign(
    prospect_name: str,
    company_or_lab: str,
    outreach_goal: str = "frontier_lab_collab",
    custom_context: str = "",
    model: str | None = None,
) -> dict[str, Any]:
    """Orchestrates the 4-layer LinkedIn outreach pipeline for a target researcher or B2B lead.

    Call Graph (Depth 4):
    1. `lookup_prospect_and_proof_dossier` (@app.skill)
    2. `classify_outreach_track` (Layer 2) -> conditionally escalates to `deep_track_escalation` (Layer 3)
    3. Parallel fan-out across Layer 3 specialists (`extract_technical_bridge`,
       `structure_commercial_or_collab_offer`, `draft_connection_note`, `draft_multitouch_sequence`)
    4. `reconcile_campaign_sequence` (Layer 2) -> calls `challenge_outreach_draft` (Layer 3)
       -> calls `verify_citation_grounding` (Layer 4)
    """
    # Step 1: Deterministic dossier lookup via control-plane skill call
    dossier = await app.call(
        f"{app.node_id}.lookup_prospect_and_proof_dossier",
        prospect_name=prospect_name,
        company_or_lab=company_or_lab,
        outreach_goal=outreach_goal,
        custom_context=custom_context,
    )
    dossier_prose = render_dossier_to_prose(dossier)

    # Step 2: Dynamic intake track routing (escalates to Layer 3 if confidence is low)
    track_dict = await app.call(
        f"{app.node_id}.classify_outreach_track",
        dossier_prose=dossier_prose,
        fallback_dossier=dossier,
        model=model,
    )
    track = TrackRoutingDecision(**track_dict)

    # Step 3: Dynamic runtime branching + parallel specialist fan-out
    # Augment dossier prose with track-specific priority framing before parallel dispatch
    if track.primary_track == "tokyo_in_person_hardware":
        track_directive = (
            "PRIORITY DIRECTIVE: Target is in Tokyo. Highlight live in-person demo availability "
            "at Azabudai Hills / Shinjuku / TIB Nov 7 Vietnam-Japan AI Finale with the physical "
            "Pocket Omni ESP32 ternary rig (4,096 trit ops in 18 us)."
        )
    elif track.primary_track == "b2b_turnkey_sprint":
        track_directive = (
            "PRIORITY DIRECTIVE: Commercial B2B target. Anchor on our 7-day fixed-scope Turnkey "
            "Sprints ($6.5k PKG_A Ternary Edge, $9.5k PKG_B Zig/eBPF, $12.5k PKG_C Agent Graph, "
            "50% Stripe upfront)."
        )
    else:
        track_directive = (
            f"PRIORITY DIRECTIVE: Frontier lab research track ({track.primary_track}). Anchor on "
            "verifiable repositories (github.com/8b-is/headroomz, github.com/8b-is/arnauth) and "
            "Hugging Face traces (PeetPedro/headroomz-compression-traces)."
        )

    enriched_dossier_prose = f"{dossier_prose}\n\n{track_directive}"

    bridge_dict, offer_dict, conn_note_dict, sequence_dict = await asyncio.gather(
        app.call(
            f"{app.node_id}.extract_technical_bridge",
            dossier_prose=enriched_dossier_prose,
            selected_track=track.primary_track,
            active_citation_ids=track.active_citation_ids,
            fallback_dossier=dossier,
            model=model,
        ),
        app.call(
            f"{app.node_id}.structure_commercial_or_collab_offer",
            dossier_prose=enriched_dossier_prose,
            selected_track=track.primary_track,
            fallback_dossier=dossier,
            model=model,
        ),
        app.call(
            f"{app.node_id}.draft_connection_note",
            dossier_prose=enriched_dossier_prose,
            selected_track=track.primary_track,
            fallback_dossier=dossier,
            model=model,
        ),
        app.call(
            f"{app.node_id}.draft_multitouch_sequence",
            dossier_prose=enriched_dossier_prose,
            selected_track=track.primary_track,
            fallback_dossier=dossier,
            model=model,
        ),
    )

    bridge = TechnicalBridgeAnalysis(**bridge_dict)
    offer = OfferFraming(**offer_dict)
    conn_note = ConnectionNoteDraft(**conn_note_dict)
    sequence = FollowupSequenceDraft(**sequence_dict)

    # Step 4: Render specialist outputs to natural-language prose and run HUNT->PROVE
    # adversarial audit + reconciliation (Layers 2 -> 3 -> 4)
    draft_brief_prose = render_specialist_drafts_to_prose(
        dossier_prose=enriched_dossier_prose,
        track=track,
        bridge=bridge,
        offer=offer,
        conn_note=conn_note,
        sequence=sequence,
    )

    reconciled = await app.call(
        f"{app.node_id}.reconcile_campaign_sequence",
        draft_brief_prose=draft_brief_prose,
        conn_note_dict=conn_note.model_dump(),
        sequence_dict=sequence.model_dump(),
        active_citation_ids=bridge.matched_citation_ids or track.active_citation_ids,
        model=model,
    )

    campaign_payload = {
        "prospect": {
            "name": dossier["prospect_name"],
            "role": dossier["role"],
            "company_or_lab": dossier["company_or_lab"],
            "location": dossier["location"],
        },
        "routing": track.model_dump(),
        "technical_bridge": bridge.model_dump(),
        "offer": offer.model_dump(),
        "governance_status": reconciled["governance_status"],
        "audit": reconciled["audit"],
        "final_sequence": reconciled["final_sequence"],
        "provenance_citations": [
            PROOF_CITATION_REGISTRY[cid]
            for cid in (bridge.matched_citation_ids or track.active_citation_ids)
            if cid in PROOF_CITATION_REGISTRY
        ],
    }

    # Best-effort store in agent memory so operator UI / cross-run history can inspect it
    try:
        cache_key = f"campaign:{dossier['company_or_lab'].lower()}:{dossier['prospect_name'].lower()}"
        await app.memory.set(cache_key, campaign_payload, scope="agent")
    except Exception:
        pass

    return campaign_payload


# ---------------------------------------------------------------------------
# Built-in 8b.is / Project Omni Operator Web UI (`/dashboard`) + `/api/dispatch`
# ---------------------------------------------------------------------------


@app.post("/api/dispatch")
async def api_dispatch_outreach(request: Request) -> JSONResponse:
    """Triggers automated Playwright outreach dispatch for a single prospect or all 16 targets."""
    body = await request.json()
    prospect_key = (body.get("prospect_key") or "").strip().lower()
    li_at = (body.get("li_at") or os.getenv("LI_AT", "")).strip() or None
    dry_run = bool(body.get("dry_run", False))

    if prospect_key and prospect_key in PROSPECT_DOSSIER_CATALOG:
        target_keys = [prospect_key]
    elif body.get("tier1_only"):
        target_keys = [
            k
            for k in PROSPECT_DOSSIER_CATALOG
            if k not in ("tokyo b2b lead", "joe rogan / comedy mothership")
        ]
    else:
        target_keys = list(PROSPECT_DOSSIER_CATALOG.keys())

    try:
        results = await run_playwright_campaign(
            target_keys=target_keys,
            li_at_cookie=li_at,
            dry_run=dry_run,
            headless=bool(li_at),
        )
        return JSONResponse({"ok": True, "dispatched": len(results), "results": results})
    except Exception as exc:
        return JSONResponse(
            {"ok": False, "error": str(exc), "target_keys": target_keys},
            status_code=500,
        )


@app.get("/api/dispatch/logs")
async def api_dispatch_logs() -> JSONResponse:
    """Returns the persisted outreach dispatch audit log (`outreach_dispatch_log.json`)."""
    import json as _json

    if LOG_PATH.exists():
        try:
            return JSONResponse({"logs": _json.loads(LOG_PATH.read_text(encoding="utf-8"))})
        except Exception:
            pass
    return JSONResponse({"logs": []})


@app.get("/dashboard", response_class=HTMLResponse)
async def outreach_dashboard() -> HTMLResponse:
    """Renders an interactive 8b.is Aurora-themed LinkedIn Outreach command center with 1-click & batch dispatch."""
    cards_html: list[str] = []
    for idx, (key, dossier) in enumerate(PROSPECT_DOSSIER_CATALOG.items()):
        conn = fallback_connection_note(dossier)
        seq = fallback_followup_sequence(dossier)
        cits = ", ".join(dossier["recommended_citations"])
        url_entry = TARGET_LINKEDIN_URLS.get(key, {})
        linkedin_url = url_entry.get("linkedin_url", "https://www.linkedin.com/feed/")
        search_url = url_entry.get("search_url", linkedin_url)
        safe_id = f"p{idx}"

        cards_html.append(
            f"""
            <div class="card" id="card-{safe_id}">
              <div class="card-header">
                <div>
                  <span class="badge">{dossier['company_or_lab']}</span>
                  <span class="track-pill">{dossier['recommended_track']}</span>
                  <h3>{dossier['prospect_name']} — <span class="role">{dossier['role']}</span></h3>
                  <div class="loc">📍 {dossier['location']} · Citations: <code>{cits}</code></div>
                  <div class="links">
                    🔗 <a href="{linkedin_url}" target="_blank" rel="noopener">{linkedin_url}</a>
                    &nbsp;|&nbsp; <a href="{search_url}" target="_blank" rel="noopener">Search Fallback</a>
                  </div>
                </div>
              </div>
              <div class="action-bar">
                <button class="btn btn-primary" onclick="copyAndOpen('{safe_id}', '{linkedin_url}')">
                  🚀 Copy Note ({len(conn.note_text)}/300) &amp; Open LinkedIn Profile
                </button>
                <button class="btn btn-secondary" onclick="copyText('dm1-{safe_id}', this)">
                  📋 Copy Day 1 DM
                </button>
                <button class="btn btn-secondary" onclick="copyText('dm3-{safe_id}', this)">
                  📋 Copy Day 3 Proof
                </button>
                <button class="btn btn-violet" onclick="autoDispatchSingle('{key}', this)">
                  🤖 Auto-Send via Playwright
                </button>
              </div>
              <div class="block">
                <div class="label">Connection Request Note ({len(conn.note_text)} / 300 chars — APPROVED_READY_TO_SEND)</div>
                <pre id="conn-{safe_id}">{conn.note_text}</pre>
              </div>
              <div class="block">
                <div class="label">Day 1 Follow-Up DM ({len(seq.day1_dm)} / 450 chars)</div>
                <pre id="dm1-{safe_id}">{seq.day1_dm}</pre>
              </div>
              <div class="block">
                <div class="label">Day 3 Technical Proof Drop</div>
                <pre id="dm3-{safe_id}">{seq.day3_artifact_drop}</pre>
              </div>
            </div>
            """
        )

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <title>8b.is // Project Omni — LinkedIn Outreach Dispatcher (Peter Lodri)</title>
  <style>
    :root {{
      --bg: #07090e;
      --panel: #0f1420;
      --border: #1e293b;
      --cyan: #00f5d4;
      --violet: #a855f7;
      --amber: #f59e0b;
      --text: #e2e8f0;
      --muted: #94a3b8;
    }}
    body {{
      margin: 0;
      padding: 28px 36px;
      background: radial-gradient(circle at 15% 0%, #111c35 0%, var(--bg) 55%);
      color: var(--text);
      font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
    }}
    header {{
      border-bottom: 1px solid var(--border);
      padding-bottom: 18px;
      margin-bottom: 22px;
      display: flex;
      justify-content: space-between;
      align-items: flex-start;
      flex-wrap: wrap;
      gap: 16px;
    }}
    h1 {{
      margin: 0 0 6px 0;
      font-size: 22px;
      letter-spacing: -0.02em;
      color: var(--cyan);
    }}
    .sub {{ color: var(--muted); font-size: 13px; }}
    .control-bar {{
      background: rgba(15, 20, 32, 0.9);
      border: 1px solid rgba(0, 245, 212, 0.35);
      border-radius: 10px;
      padding: 14px 18px;
      margin-bottom: 22px;
      display: flex;
      flex-wrap: wrap;
      align-items: center;
      gap: 12px;
    }}
    .control-bar input {{
      background: #06080d;
      border: 1px solid #334155;
      color: var(--text);
      padding: 8px 12px;
      border-radius: 6px;
      font-size: 12.5px;
      min-width: 300px;
    }}
    .btn {{
      cursor: pointer;
      border-radius: 6px;
      padding: 7px 12px;
      font-size: 12px;
      font-weight: 600;
      border: 1px solid transparent;
      transition: all 0.15s ease;
    }}
    .btn-primary {{
      background: var(--cyan);
      color: #041014;
    }}
    .btn-primary:hover {{ filter: brightness(1.1); }}
    .btn-secondary {{
      background: #1e293b;
      color: var(--text);
      border-color: #334155;
    }}
    .btn-secondary:hover {{ background: #334155; }}
    .btn-violet {{
      background: rgba(168, 85, 247, 0.2);
      color: #e9d5ff;
      border-color: rgba(168, 85, 247, 0.5);
    }}
    .btn-violet:hover {{ background: rgba(168, 85, 247, 0.35); }}
    .action-bar {{
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
      margin: 10px 0 12px 0;
    }}
    .links {{
      font-size: 12px;
      margin-top: 4px;
    }}
    .links a {{
      color: var(--cyan);
      text-decoration: none;
    }}
    .links a:hover {{ text-decoration: underline; }}
    .grid {{
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(480px, 1fr));
      gap: 18px;
    }}
    .card {{
      background: var(--panel);
      border: 1px solid var(--border);
      border-radius: 10px;
      padding: 16px 18px;
    }}
    .badge {{
      background: rgba(0, 245, 212, 0.12);
      color: var(--cyan);
      border: 1px solid rgba(0, 245, 212, 0.35);
      border-radius: 4px;
      padding: 2px 8px;
      font-size: 11px;
      font-weight: 600;
      text-transform: uppercase;
    }}
    .track-pill {{
      background: rgba(168, 85, 247, 0.14);
      color: #d8b4fe;
      border-radius: 4px;
      padding: 2px 8px;
      font-size: 11px;
      margin-left: 6px;
    }}
    h3 {{ margin: 10px 0 4px 0; font-size: 16px; }}
    .role {{ color: var(--muted); font-weight: 400; }}
    .loc {{ color: var(--muted); font-size: 12px; margin-bottom: 4px; }}
    .block {{ margin-top: 10px; }}
    .label {{
      font-size: 11px;
      text-transform: uppercase;
      letter-spacing: 0.05em;
      color: var(--amber);
      margin-bottom: 4px;
    }}
    pre {{
      margin: 0;
      padding: 10px;
      background: #06080d;
      border: 1px solid #1a2436;
      border-radius: 6px;
      white-space: pre-wrap;
      font-size: 12.5px;
      line-height: 1.45;
      color: #f8fafc;
    }}
    #status-banner {{
      font-size: 12.5px;
      color: var(--cyan);
      margin-left: auto;
    }}
  </style>
</head>
<body>
  <header>
    <div>
      <h1>8B-IS // PROJECT OMNI — LINKEDIN OUTREACH DISPATCHER (Account: Peter Lodri)</h1>
      <div class="sub">
        16 Verified Targets · 5 Tier-1 Open-Weight AI Labs (Sakana AI, Prime Intellect, Nous Research, Zyphra, Poolside AI) + Tokyo B2B + Joe Rogan / Austin
      </div>
    </div>
  </header>

  <div class="control-bar">
    <strong style="color: var(--cyan); font-size: 13px;">⚡ Batch Automation:</strong>
    <input id="li-at-input" type="password" placeholder="Optional: Paste LinkedIn li_at cookie for headless auto-send..." />
    <button class="btn btn-primary" onclick="launchSequentialTabs()">
      🚀 1-Click Assisted Mode (Copy First Note &amp; Open Top 5 Profiles)
    </button>
    <button class="btn btn-violet" onclick="autoDispatchBatch(true)">
      🤖 Auto-Dispatch 14 Tier-1 Lab Founders (Playwright)
    </button>
    <button class="btn btn-secondary" onclick="autoDispatchBatch(false)">
      🤖 Auto-Dispatch All 16 Targets
    </button>
    <span id="status-banner">Ready · Authenticated for Peter Lodri</span>
  </div>

  <div class="grid">
    {''.join(cards_html)}
  </div>

  <script>
    async function copyAndOpen(safeId, url) {{
      const noteEl = document.getElementById('conn-' + safeId);
      const text = noteEl ? noteEl.innerText : '';
      try {{
        await navigator.clipboard.writeText(text);
        document.getElementById('status-banner').innerText =
          '✅ Copied <=300 char note (' + text.length + ' chars) to clipboard! Opening ' + url;
      }} catch (e) {{
        console.error(e);
      }}
      window.open(url, '_blank', 'noopener');
    }}

    async function copyText(elemId, btn) {{
      const el = document.getElementById(elemId);
      if (!el) return;
      const old = btn.innerText;
      await navigator.clipboard.writeText(el.innerText);
      btn.innerText = '✅ Copied!';
      setTimeout(() => {{ btn.innerText = old; }}, 1600);
    }}

    async function autoDispatchSingle(prospectKey, btn) {{
      const liAt = document.getElementById('li-at-input').value.trim();
      const old = btn.innerText;
      btn.innerText = '⏳ Dispatching...';
      document.getElementById('status-banner').innerText = '⏳ Dispatching ' + prospectKey + '...';
      try {{
        const res = await fetch('/api/dispatch', {{
          method: 'POST',
          headers: {{ 'Content-Type': 'application/json' }},
          body: JSON.stringify({{ prospect_key: prospectKey, li_at: liAt }})
        }});
        const data = await res.json();
        if (data.ok && data.results && data.results[0]) {{
          btn.innerText = '✅ ' + data.results[0].status;
          document.getElementById('status-banner').innerText =
            '✅ ' + prospectKey + ': ' + data.results[0].status;
        }} else {{
          btn.innerText = '⚠️ Check Terminal/Auth';
          document.getElementById('status-banner').innerText =
            '⚠️ ' + (data.error || 'Run uv run python dispatcher.py --run-all on host');
        }}
      }} catch (e) {{
        btn.innerText = old;
        document.getElementById('status-banner').innerText = '⚠️ Error: ' + e;
      }}
    }}

    async function autoDispatchBatch(tier1Only) {{
      const liAt = document.getElementById('li-at-input').value.trim();
      document.getElementById('status-banner').innerText =
        '⏳ Running Playwright batch dispatch...';
      try {{
        const res = await fetch('/api/dispatch', {{
          method: 'POST',
          headers: {{ 'Content-Type': 'application/json' }},
          body: JSON.stringify({{ tier1_only: tier1Only, li_at: liAt }})
        }});
        const data = await res.json();
        document.getElementById('status-banner').innerText =
          data.ok
            ? ('✅ Dispatched ' + data.dispatched + ' targets!')
            : ('⚠️ ' + (data.error || 'Use host CLI dispatcher.py'));
      }} catch (e) {{
        document.getElementById('status-banner').innerText = '⚠️ Error: ' + e;
      }}
    }}

    async function launchSequentialTabs() {{
      const firstNote = document.getElementById('conn-p0');
      if (firstNote) {{
        await navigator.clipboard.writeText(firstNote.innerText);
      }}
      const topUrls = [
        "https://www.linkedin.com/in/llion-jones-96306423/",
        "https://www.linkedin.com/in/hardmaru/",
        "https://www.linkedin.com/in/johannes-hagemann/",
        "https://www.linkedin.com/in/jq/",
        "https://www.linkedin.com/in/beren-millidge-574351162/"
      ];
      topUrls.forEach(u => window.open(u, '_blank', 'noopener'));
      document.getElementById('status-banner').innerText =
        '✅ Copied Llion Jones note & opened top 5 Tier-1 Lab Founder profiles!';
    }}
  </script>
</body>
</html>"""
    return HTMLResponse(content=html)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "8001")), auto_port=False)
