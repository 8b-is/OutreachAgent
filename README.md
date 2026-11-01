# OutreachAgent — made with love from within

> **8b-is // Project Omni** — Depth-4 Composite-Intelligence Multi-Reasoner Outreach Engine, CloakBrowser Stealth E2E Dispatcher & Real-Time WhatsApp Proof-Screenshot Bridge.

[![GitHub](https://img.shields.io/badge/GitHub-8b--is%2FOutreachAgent-00e5ff?style=flat-square)](https://github.com/8b-is/OutreachAgent)
[![Codeberg](https://img.shields.io/badge/Codeberg-peterlodri--sec%2FOutreachAgent-2185d0?style=flat-square)](https://codeberg.org/peterlodri-sec/OutreachAgent)
[![g8t.is](https://img.shields.io/badge/g8t.is-outreach--agent-10b981?style=flat-square)](https://g8t.is/g8t/projects/outreach-agent)

**OutreachAgent** researches, drafts, adversarially audits (`HUNT -> PROVE`), character-verifies (`<= 300` chars), and autonomously dispatches peer-to-peer technical outreach campaigns across LinkedIn using **[CloakHQ/CloakBrowser](https://github.com/CloakHQ/CloakBrowser)** stealth Chromium contexts, streaming real-time confirmation captions + full-viewport PNG proof screenshots into WhatsApp via **`wa-stream`**.

---

## Highlights

1. **Depth-4 AgentField Composite Intelligence (`main.py` + `reasoners/`)**:
   - **Dynamic Track Routing & Conditional Escalation**: Routes prospects across `tokyo_in_person_hardware`, `verifiable_rl_environments`, `ssm_hardware_codesign`, `swe_agent_compression`, and `b2b_turnkey_sprint`.
   - **4x Parallel Specialist Hunters**: Simultaneously extracts technical bridges (CTM, Hermes 4, INTELLECT-3/TOPLOC, Zamba2/ZAYA1-8B, Laguna/RLCEF, Comedy Mothership), commercial/collab offers, `<= 300`-char connection notes, and Day 1 / Day 3 / Day 7 follow-up sequences.
   - **2-Stage `HUNT -> PROVE` Adversarial Challenger**: Deterministically enforces zero AI-slop phrases, verifies every `[CIT-*]` proof claim against the canonical `8b-is` citation registry, and guarantees LinkedIn's strict `300`-character connection-note ceiling.
2. **CloakBrowser Stealth E2E Dispatcher (`dispatcher.py`)**:
   - Bridges live Chrome profile state (`Bookmarks`, `Local Storage`, `IndexedDB`, and authenticated session cookies) into an isolated CloakBrowser stealth context (`--headless` or headed) without triggering Chromium version-skew `SIGTRAP` traps.
   - Navigates 2026 LinkedIn profile DOMs (`1st` / `2nd` / `3rd` degree connections), automatically handles top-card `Connect` and `More -> Connect` (`preload/custom-invite`) flows, injects the `<= 300`-char note, and falls back to `Follow` or `Message` when required.
3. **Real-Time WhatsApp Proof Bridge (`wa-stream` `:8790/agy`)**:
   - Captures a `1440x900` proof screenshot after every single prospect outreach and dispatches the PNG + structured telemetry caption directly into WhatsApp.
4. **Pure-Rust `g8t.is` Verified Capsules (`capsules/outreach_capsules.rs`)**:
   - Ships `outreach_char_budget_trit_gate` and `outreach_cadence_delay_hours` obeying the `8b-is` Zero-Float Law (`zero_unsafe`, `zero_floats`, `zero_external_crates`).

---

## Quickstart

### 1. Install Dependencies (`uv`)

```bash
uv sync
```

### 2. Instant CLI & Playbook Generator (`cli.py`)

```bash
# List all 16 preloaded Tier-1 AI Lab, Tokyo B2B & Austin targets
uv run python cli.py --list

# Generate a single prospect campaign pack
uv run python cli.py --prospect "Llion Jones" --lab "Sakana AI"

# Export all sequences to Markdown + JSON
uv run python cli.py --all \
  --export-md ./8b_linkedin_outreach_playbook.md \
  --export-json ./8b_linkedin_outreach_packs.json
```

### 3. Automated E2E CloakBrowser Outreach Dispatch (`dispatcher.py`)

```bash
# Copy a prospect's <=300-char note to macOS clipboard & open their LinkedIn profile
uv run python dispatcher.py --prospect "Johannes Hagemann" --copy-and-open

# Run automated E2E CloakBrowser outreach for a single prospect + WhatsApp screenshot proof
uv run python dispatcher.py --prospect "Johannes Hagemann"

# Run automated E2E CloakBrowser outreach across all 16 targets sequentially
uv run python dispatcher.py --run-all
```

### 4. Run the Full AgentField Control Plane + Aurora Operator Dashboard

```bash
cp .env.example .env
# Set OPENROUTER_API_KEY (or OPENAI_API_KEY / ANTHROPIC_API_KEY) in .env
docker compose up --build
```

- **Aurora Operator Web UI**: `http://localhost:8001/dashboard`
- **AgentField Control Plane**: `http://localhost:18080`

```bash
# Verify control-plane health & registered reasoners
curl -fsS http://localhost:18080/api/v1/health | jq
curl -fsS http://localhost:18080/api/v1/discovery/capabilities \
  | jq '.capabilities[] | select(.agent_id=="linkedin-outreach-agent")'
```

---

## Sovereign Mirrors

- **GitHub (`8b-is`)**: `https://github.com/8b-is/OutreachAgent`
- **GitHub (`peterlodri-sec`)**: `https://github.com/peterlodri-sec/OutreachAgent`
- **Codeberg**: `https://codeberg.org/peterlodri-sec/OutreachAgent`
- **`g8t.is`**: `https://g8t.is/g8t/projects/outreach-agent` (`https://g8t.is/git/8b-is/OutreachAgent`)

---

*OutreachAgent — made with love from within (`8b-is`).*
