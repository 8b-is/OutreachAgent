# /// script
# requires-python = ">=3.11"
# dependencies = [
#   "pydantic>=2.0.0",
#   "agentfield>=0.1.35",
#   "playwright>=1.48.0",
#   "cloakbrowser>=0.6.0",
#   "httpx>=0.27.0",
#   "fastapi>=0.110.0",
# ]
# ///
"""Automated CloakBrowser E2E LinkedIn Outreach Dispatcher for Peter Lodri (`8b-is // Project Omni`).

Features:
1. Syncs `peter.lodri@gmail.com` (`~/Library/Application Support/Google/Chrome/Default`) profile data
   (Bookmarks, Preferences, Local Storage, IndexedDB, and live LinkedIn session cookies) into
   CloakBrowser's stealth persistent context (`~/.config/8b-linkedin-outreach/cloak-profile-v145`).
2. Executes E2E LinkedIn outreach across all 16 verified targets (`--run-all`) or a single target
   (`--prospect "Johannes Hagemann"`), or `--copy-and-open` for instant clipboard + browser tab.
3. After each target outreach completes, captures a full-viewport PNG screenshot in `./screenshots/`
   and dispatches a real-time confirmation message + screenshot into the WhatsApp
   "little dude(s) and Angels" group (`120363413133092554@g.us`) via `wa-stream` (`127.0.0.1:8790/agy`).
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import random
import re
import shutil
import socket
import subprocess
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from cli import build_offline_campaign_pack
from reasoners.helpers import PROSPECT_DOSSIER_CATALOG

# Canonical LinkedIn Profile URLs & Search Fallbacks for all 16 Targets
TARGET_LINKEDIN_URLS: dict[str, dict[str, str]] = {
    "llion jones": {
        "linkedin_url": "https://www.linkedin.com/in/llion-jones-96306423/",
        "search_url": "https://www.linkedin.com/search/results/people/?keywords=Llion%20Jones%20Sakana%20AI",
    },
    "david ha": {
        "linkedin_url": "https://www.linkedin.com/in/hardmaru/",
        "search_url": "https://www.linkedin.com/search/results/people/?keywords=David%20Ha%20Sakana%20AI",
    },
    "luke darlow": {
        "linkedin_url": "https://www.linkedin.com/in/luke-darlow/",
        "search_url": "https://www.linkedin.com/search/results/people/?keywords=Luke%20Darlow%20Sakana%20AI",
    },
    "johannes hagemann": {
        "linkedin_url": "https://www.linkedin.com/in/johannes-hagemann-393b72142/",
        "search_url": "https://www.linkedin.com/search/results/people/?keywords=Johannes%20Hagemann%20Prime%20Intellect",
    },
    "vincent weisser": {
        "linkedin_url": "https://www.linkedin.com/in/vincentweisser/",
        "search_url": "https://www.linkedin.com/search/results/people/?keywords=Vincent%20Weisser%20Prime%20Intellect",
    },
    "will brown": {
        "linkedin_url": "https://www.linkedin.com/in/willccbb/",
        "search_url": "https://www.linkedin.com/search/results/people/?keywords=Will%20Brown%20Prime%20Intellect",
    },
    "jeffrey quesnelle": {
        "linkedin_url": "https://www.linkedin.com/in/jq/",
        "search_url": "https://www.linkedin.com/search/results/people/?keywords=Jeffrey%20Quesnelle%20Nous%20Research",
    },
    "ryan teknium": {
        "linkedin_url": "https://www.linkedin.com/search/results/people/?keywords=Ryan%20Teknium%20Nous%20Research",
        "search_url": "https://www.linkedin.com/search/results/people/?keywords=Ryan%20Teknium%20Nous%20Research",
    },
    "karan malhotra": {
        "linkedin_url": "https://www.linkedin.com/in/karanmalhotra1/",
        "search_url": "https://www.linkedin.com/search/results/people/?keywords=Karan%20Malhotra%20Nous%20Research",
    },
    "beren millidge": {
        "linkedin_url": "https://www.linkedin.com/in/beren-millidge-377065142/",
        "search_url": "https://www.linkedin.com/search/results/people/?keywords=Beren%20Millidge%20Zyphra",
    },
    "quentin anthony": {
        "linkedin_url": "https://www.linkedin.com/in/quentin-anthony/",
        "search_url": "https://www.linkedin.com/search/results/people/?keywords=Quentin%20Anthony%20Zyphra",
    },
    "krithik puthalath": {
        "linkedin_url": "https://www.linkedin.com/in/krithik-puthalath/",
        "search_url": "https://www.linkedin.com/search/results/people/?keywords=Krithik%20Puthalath%20Zyphra",
    },
    "eiso kant": {
        "linkedin_url": "https://www.linkedin.com/in/eisokant/",
        "search_url": "https://www.linkedin.com/search/results/people/?keywords=Eiso%20Kant%20Poolside",
    },
    "jason warner": {
        "linkedin_url": "https://www.linkedin.com/in/jasoncwarner/",
        "search_url": "https://www.linkedin.com/search/results/people/?keywords=Jason%20Warner%20Poolside",
    },
    "tokyo b2b lead": {
        "linkedin_url": "https://www.linkedin.com/search/results/people/?keywords=VP%20Engineering%20AI%20Tokyo",
        "search_url": "https://www.linkedin.com/search/results/people/?keywords=VP%20Engineering%20AI%20Tokyo",
    },
    "joe rogan / comedy mothership": {
        "linkedin_url": "https://www.linkedin.com/search/results/people/?keywords=Brian%20Redban%20Comedy%20Mothership",
        "search_url": "https://www.linkedin.com/search/results/people/?keywords=Jamie%20Vernon%20Joe%20Rogan",
    },
}

LOG_PATH = Path(os.getenv("OUTREACH_LOG_PATH", str(Path(__file__).parent / "outreach_dispatch_log.json")))
SCREENSHOT_DIR = Path(os.getenv("OUTREACH_SCREENSHOT_DIR", str(Path(__file__).parent / "screenshots")))
CHROME_DEFAULT_DIR = Path(
    os.getenv(
        "OUTREACH_CHROME_PROFILE_DIR",
        str(Path.home() / "Library/Application Support/Google/Chrome/Default"),
    )
)
CHROME_BRIDGE_DIR = Path(
    os.getenv(
        "OUTREACH_CHROME_BRIDGE_DIR",
        str(Path.home() / ".config" / "8b-linkedin-outreach" / "chrome-bridge"),
    )
)
CLOAK_PROFILE_DIR = Path(
    os.getenv(
        "OUTREACH_CLOAK_PROFILE_DIR",
        str(Path.home() / ".config" / "8b-linkedin-outreach" / "cloak-profile-v145"),
    )
)
PROFILE_DIR = CLOAK_PROFILE_DIR
OUTREACH_ACCOUNT_LABEL = os.getenv("OUTREACH_ACCOUNT_LABEL", "Peter Lodri (via CloakBrowser)")
OUTREACH_WA_JID = os.getenv("OUTREACH_WA_JID", "")


def slugify(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", text.lower()).strip("_")


def append_dispatch_log(entry: dict[str, Any]) -> None:
    existing: list[dict[str, Any]] = []
    if LOG_PATH.exists():
        try:
            existing = json.loads(LOG_PATH.read_text(encoding="utf-8"))
        except Exception:
            existing = []
    entry["timestamp_utc"] = datetime.now(timezone.utc).isoformat()
    existing.append(entry)
    LOG_PATH.write_text(json.dumps(existing, indent=2), encoding="utf-8")


def send_whatsapp_outreach_confirmation(
    idx: int,
    total: int,
    dossier: dict[str, Any],
    result: dict[str, Any],
    screenshot_path: Path | None,
    note_text: str,
) -> bool:
    """Sends a confirmation message + PNG screenshot into the configured WhatsApp group via wa-stream."""
    status_emoji = "✅" if "SENT" in result.get("status", "") or "PENDING" in result.get("status", "") or "FOLLOWED" in result.get("status", "") else "📸"
    caption = (
        f"{status_emoji} *LINKEDIN OUTREACH [{idx}/{total}] — {dossier['prospect_name']}*\n"
        f"✦ *Lab / Co:* {dossier['company_or_lab']} ({dossier['role']})\n"
        f"✦ *Track:* `{dossier['recommended_track']}`\n"
        f"✦ *Account:* {OUTREACH_ACCOUNT_LABEL}\n"
        f"✦ *Status:* `{result.get('status', 'DONE')}`\n"
        f"✦ *Profile:* {result.get('url', '')}\n"
        f"✦ *Note ({len(note_text)}/300 chars):*\n_{note_text}_"
    )

    payload: dict[str, Any] = {
        "dir": "out",
        "force": True,
        "text": caption,
        "caption": caption,
    }
    if OUTREACH_WA_JID:
        payload["jid"] = OUTREACH_WA_JID
    if screenshot_path and screenshot_path.exists():
        payload["type"] = "image"
        payload["imageFile"] = str(screenshot_path.resolve())
        payload["mimeType"] = "image/png"

    body_bytes = json.dumps(payload).encode("utf-8")
    for port in (8790, 8791, 8792):
        try:
            req = urllib.request.Request(
                f"http://127.0.0.1:{port}/agy",
                data=body_bytes,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=8.0) as resp:
                if resp.status == 200:
                    return True
        except Exception:
            continue

    # Fallback to raw duplex TCP socket (8797 / 8788)
    for raw_port in (8797, 8788):
        try:
            with socket.create_connection(("127.0.0.1", raw_port), timeout=3.0) as sock:
                sock.sendall(body_bytes + b"\n")
                return True
        except Exception:
            continue
    return False


async def sync_chrome_profile_to_cloakbrowser() -> list[dict[str, Any]]:
    """Copies safe profile data (Bookmarks, Local Storage, IndexedDB) from Chrome's `Default`
    (`peter.lodri@gmail.com`) profile and bridges all live LinkedIn session cookies into CloakBrowser.
    """
    from playwright.async_api import async_playwright

    CLOAK_PROFILE_DIR.mkdir(parents=True, exist_ok=True)
    cloak_default = CLOAK_PROFILE_DIR / "Default"
    cloak_default.mkdir(parents=True, exist_ok=True)

    # Copy Bookmarks from Chrome Default (peter.lodri@gmail.com) once without clobbering active session storage
    if CHROME_DEFAULT_DIR.exists() and not (cloak_default / "Bookmarks").exists():
        for item_name in ("Bookmarks", "Local Storage", "IndexedDB"):
            src = CHROME_DEFAULT_DIR / item_name
            dst = cloak_default / item_name
            try:
                if src.is_dir():
                    if dst.exists():
                        shutil.rmtree(dst, ignore_errors=True)
                    shutil.copytree(src, dst, ignore_dangling_symlinks=True)
                elif src.is_file():
                    shutil.copy2(src, dst)
            except Exception:
                pass

    CHROME_BRIDGE_DIR.mkdir(parents=True, exist_ok=True)
    bridge_default = CHROME_BRIDGE_DIR / "Default"
    bridge_default.mkdir(parents=True, exist_ok=True)

    # Only seed CHROME_BRIDGE_DIR from Chrome Default if bridge_default/Cookies doesn't exist yet
    if not (bridge_default / "Cookies").exists() and CHROME_DEFAULT_DIR.exists():
        for cname in (
            "Cookies",
            "Cookies-journal",
            "Cookies-wal",
            "Cookies-shm",
            "Login Data",
            "Login Data For Account",
            "Web Data",
            "Preferences",
        ):
            csrc = CHROME_DEFAULT_DIR / cname
            if csrc.exists():
                try:
                    shutil.copy2(csrc, bridge_default / cname)
                except Exception:
                    pass

    cookies: list[dict[str, Any]] = []
    async with async_playwright() as p:
        ctx = await p.chromium.launch_persistent_context(
            user_data_dir=str(CHROME_BRIDGE_DIR),
            channel="chrome",
            headless=False,
            ignore_default_args=["--use-mock-keychain", "--password-store=basic"],
        )
        bpage = ctx.pages[0] if ctx.pages else await ctx.new_page()
        await bpage.goto("https://www.linkedin.com/feed/", wait_until="domcontentloaded", timeout=30000)
        await asyncio.sleep(2.0)
        cookies = await ctx.cookies()
        await ctx.close()

    return [
        c
        for c in cookies
        if any(d in c.get("domain", "") for d in ("linkedin.com", "licdn.com", "google.com"))
    ]


async def send_connection_note_on_page(
    page: Any,
    idx: int,
    prospect_name: str,
    company_or_lab: str,
    linkedin_url: str,
    search_url: str,
    note_text: str,
    dry_run: bool = False,
) -> tuple[dict[str, Any], Path]:
    """Resolves the target's LinkedIn profile via the authenticated SPA Global Search bar
    (avoiding cold /404 or authwall redirects), opens the Connect modal, fills the <=300 char
    note, clicks Send, and captures a proof screenshot.
    """
    SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)
    shot_path = SCREENSHOT_DIR / f"outreach_{idx:02d}_{slugify(prospect_name)}.png"

    # Build SPA search query
    if "tokyo b2b" in prospect_name.lower():
        search_query = "VP Engineering AI Tokyo"
    elif "joe rogan" in prospect_name.lower():
        search_query = "Brian Redban Comedy Mothership"
    else:
        clean_co = company_or_lab.split("(")[0].strip()
        search_query = f"{prospect_name} {clean_co}"

    # Ensure we are on a clean authenticated page (no lingering #interop-outlet modal)
    await page.keyboard.press("Escape")
    await asyncio.sleep(0.4)

    # 1. Try direct /in/ profile URL first if configured; fall back to Global Search only if /404 or search URL
    used_direct = False
    if "/in/" in linkedin_url:
        await page.goto(linkedin_url, wait_until="domcontentloaded", timeout=35000)
        await asyncio.sleep(3.8)
        if "/404" not in page.url and "page-not-found" not in page.url and "/in/" in page.url:
            used_direct = True

    if not used_direct:
        if "/feed" not in page.url:
            await page.goto("https://www.linkedin.com/feed/", wait_until="domcontentloaded", timeout=35000)
            await asyncio.sleep(2.8)

        search_input = page.locator("input[placeholder*='Search']").first
        if await search_input.count() > 0:
            await search_input.click(force=True)
            await search_input.evaluate("(el, val) => { el.value = ''; }", search_query)
            await search_input.fill(search_query)
            await search_input.press("Enter")
            await asyncio.sleep(4.0)

            # Find the best matching /in/ profile link from the search results
            name_tokens = [
                t.lower()
                for t in re.split(r"[^a-zA-Z0-9]+", prospect_name)
                if len(t) >= 3 and t.lower() not in ("tokyo", "lead", "b2b", "joe", "rogan", "comedy", "mothership")
            ]
            cand_links = await page.locator("main a[href*='/in/']").evaluate_all(
                "els => els.map(e => ({href: e.href.split('?')[0], text: e.innerText.trim()}))"
            )
            chosen_href = ""
            for item in cand_links:
                h_low = item["href"].lower()
                t_low = item["text"].lower()
                if name_tokens and all(tok in h_low or tok in t_low for tok in name_tokens[:1]):
                    chosen_href = item["href"]
                    break
            if not chosen_href and cand_links:
                chosen_href = cand_links[0]["href"]

            if chosen_href:
                await page.goto(chosen_href, wait_until="domcontentloaded", timeout=35000)
                await asyncio.sleep(3.8)

    # Extract vanity slug from current URL if on /in/<slug>/
    m_vanity = re.search(r"/in/([^/?#]+)", page.url)
    vanity_slug = m_vanity.group(1) if m_vanity else ""

    # Check if already Pending or Connected
    pending_btn = page.locator(
        "main button:has-text('Pending'), "
        "main button[aria-label*='Pending'], "
        "main a[aria-label*='Pending']"
    ).first
    if await pending_btn.count() > 0 and await pending_btn.is_visible():
        await page.screenshot(path=str(shot_path), full_page=False)
        return (
            {
                "prospect": prospect_name,
                "url": page.url,
                "status": "ALREADY_PENDING",
                "note_sent": note_text[:300],
                "screenshot": str(shot_path),
            },
            shot_path,
        )

    clicked_connect = False

    # 1. Primary 2026 LinkedIn selector: strict match on target's vanity_slug
    if vanity_slug:
        custom_invite_loc = page.locator(
            f"a[href*='/preload/custom-invite/?vanityName={vanity_slug}']"
        ).first
        if await custom_invite_loc.count() > 0:
            await custom_invite_loc.evaluate("el => el.click()")
            clicked_connect = True
        else:
            # Open More popover (with force=True so React/Ember mounts the dropdown items)
            more_btn = page.locator(
                "main button[aria-label='More'], main button[aria-label*='More actions']"
            ).first
            if await more_btn.count() > 0:
                await more_btn.click(force=True)
                await asyncio.sleep(1.5)
                custom_invite_after = page.locator(
                    f"a[href*='/preload/custom-invite/?vanityName={vanity_slug}']"
                ).first
                if await custom_invite_after.count() > 0:
                    await custom_invite_after.evaluate("el => el.click()")
                    clicked_connect = True
                else:
                    await page.keyboard.press("Escape")
                    await asyncio.sleep(0.4)

    if not clicked_connect:
        follow_btn = page.locator(
            "main button[aria-label*='Follow'], main a[aria-label*='Follow']"
        ).first
        status_code = "PROFILE_OPENED_READY"
        if await follow_btn.count() > 0:
            btn_txt = (await follow_btn.inner_text()).strip()
            if "follow" in btn_txt.lower() and "following" not in btn_txt.lower():
                await follow_btn.evaluate("el => el.click()")
                await asyncio.sleep(1.2)
                status_code = "FOLLOWED_CREATOR_MODE_PROFILE"
            else:
                status_code = "ALREADY_FOLLOWING_CREATOR_PROFILE"
        await page.screenshot(path=str(shot_path), full_page=False)
        return (
            {
                "prospect": prospect_name,
                "url": page.url,
                "status": status_code,
                "note_sent": note_text[:300],
                "screenshot": str(shot_path),
            },
            shot_path,
        )

    await asyncio.sleep(2.2)

    # Click 'Add a note' button in the invitation modal
    add_note_btn = page.locator(
        "button[aria-label='Add a note'], button:has-text('Add a note')"
    ).first
    filled_note = False
    if await add_note_btn.count() > 0:
        await add_note_btn.evaluate("el => el.click()")
        await asyncio.sleep(1.2)
        textarea = page.locator(
            "textarea#custom-message, textarea[name='message'], div[role='dialog'] textarea, textarea"
        ).first
        if await textarea.count() > 0:
            await textarea.fill(note_text[:300])
            filled_note = True
            await asyncio.sleep(1.0)

    if dry_run:
        await page.screenshot(path=str(shot_path), full_page=False)
        return (
            {
                "prospect": prospect_name,
                "url": page.url,
                "status": "DRY_RUN_FILLED_READY_TO_SEND" if filled_note else "DRY_RUN_MODAL_OPEN",
                "note_sent": note_text[:300],
                "char_count": len(note_text[:300]),
                "screenshot": str(shot_path),
            },
            shot_path,
        )

    # Click 'Send' / 'Send invitation' / 'Send without a note'
    send_btn = page.locator(
        "button[aria-label='Send invitation'], "
        "button[aria-label='Send now'], "
        "div[role='dialog'] button:has-text('Send'), "
        "button[aria-label='Send without a note'], "
        "button:has-text('Send without a note')"
    ).first

    if await send_btn.count() > 0 and await send_btn.is_enabled():
        await send_btn.evaluate("el => el.click()")
        await asyncio.sleep(2.5)

        # Handle monthly personalized-note quota upsell modal if it appears
        upsell_without_note = page.locator(
            "button:has-text('Send without a note'), button[aria-label*='Send without a note']"
        ).first
        if await upsell_without_note.count() > 0 and await upsell_without_note.is_visible():
            await upsell_without_note.evaluate("el => el.click()")
            await asyncio.sleep(2.0)
            filled_note = False

        await page.screenshot(path=str(shot_path), full_page=False)
        return (
            {
                "prospect": prospect_name,
                "url": page.url,
                "status": "SENT_CONNECTION_WITH_NOTE" if filled_note else "SENT_CONNECTION_INVITE",
                "note_sent": note_text[:300],
                "char_count": len(note_text[:300]),
                "screenshot": str(shot_path),
            },
            shot_path,
        )

    await page.screenshot(path=str(shot_path), full_page=False)
    return (
        {
            "prospect": prospect_name,
            "url": page.url,
            "status": "MODAL_CAPTURED_REVIEW",
            "note_sent": note_text[:300],
            "screenshot": str(shot_path),
        },
        shot_path,
    )


async def run_playwright_campaign(
    target_keys: list[str],
    li_at_cookie: str | None = None,
    dry_run: bool = False,
    headless: bool = False,
    notify_whatsapp: bool = True,
    start_index: int = 1,
) -> list[dict[str, Any]]:
    import cloakbrowser

    CLOAK_PROFILE_DIR.mkdir(parents=True, exist_ok=True)
    results: list[dict[str, Any]] = []
    context = await cloakbrowser.launch_persistent_context_async(
        user_data_dir=str(CLOAK_PROFILE_DIR),
        headless=headless,
        humanize=True,
        viewport={"width": 1360, "height": 900},
    )

    if li_at_cookie:
        await context.add_cookies(
            [
                {
                    "name": "li_at",
                    "value": li_at_cookie,
                    "domain": ".www.linkedin.com",
                    "path": "/",
                    "httpOnly": True,
                    "secure": True,
                }
            ]
        )

    page = context.pages[0] if context.pages else await context.new_page()
    await page.goto("https://www.linkedin.com/feed/", wait_until="domcontentloaded", timeout=35000)
    await asyncio.sleep(3.0)

    # Only run the Chrome Default bridge if CloakBrowser is not already authenticated on /feed/
    is_logged_in = (
        "/feed" in page.url
        and await page.locator("input[placeholder*='Search'], .global-nav, a[href*='/mynetwork/']").count() > 0
    )
    if not is_logged_in:
        print(
            "[CLOAKBROWSER] Session not yet active; syncing peter.lodri@gmail.com Chrome Default profile..."
        )
        bridged_cookies = await sync_chrome_profile_to_cloakbrowser()
        if bridged_cookies:
            await context.add_cookies(bridged_cookies)
            await page.goto("https://www.linkedin.com/feed/", wait_until="domcontentloaded", timeout=35000)
            await asyncio.sleep(3.0)

    print(f"[CLOAKBROWSER] Authenticated LinkedIn session active: {page.url} ({await page.title()})")

    total = len(target_keys)
    for idx, key in enumerate(target_keys, start=1):
        if idx < start_index:
            continue
        dossier = PROSPECT_DOSSIER_CATALOG[key]
        pack = build_offline_campaign_pack(
            prospect_name=dossier["prospect_name"],
            company_or_lab=dossier["company_or_lab"],
        )
        url_info = TARGET_LINKEDIN_URLS.get(key, {})
        note_300 = pack["final_sequence"]["connection_note_300"]

        print(
            f"\n[{idx}/{total}] Dispatching via CloakBrowser -> {dossier['prospect_name']} "
            f"({dossier['company_or_lab']}) [{len(note_300)}/300 chars]..."
        )
        shot_path: Path | None = None
        try:
            res, shot_path = await send_connection_note_on_page(
                page=page,
                idx=idx,
                prospect_name=dossier["prospect_name"],
                company_or_lab=dossier["company_or_lab"],
                linkedin_url=url_info.get("linkedin_url", "https://www.linkedin.com/feed/"),
                search_url=url_info.get("search_url", "https://www.linkedin.com/feed/"),
                note_text=note_300,
                dry_run=dry_run,
            )
        except Exception as exc:
            shot_path = SCREENSHOT_DIR / f"outreach_{idx:02d}_{slugify(dossier['prospect_name'])}_err.png"
            try:
                await page.screenshot(path=str(shot_path), full_page=False)
            except Exception:
                shot_path = None
            res = {
                "prospect": dossier["prospect_name"],
                "url": page.url,
                "status": "ERROR",
                "error": str(exc),
                "screenshot": str(shot_path) if shot_path else None,
            }

        append_dispatch_log(res)
        results.append(res)
        print(f"   Status: {res['status']} | Screenshot: {res.get('screenshot')}")

        if notify_whatsapp:
            wa_ok = send_whatsapp_outreach_confirmation(
                idx=idx,
                total=total,
                dossier=dossier,
                result=res,
                screenshot_path=shot_path,
                note_text=note_300,
            )
            print(f"   WhatsApp ('little dude(s) and Angels') confirmation + screenshot sent: {wa_ok}")

        if idx < total:
            await asyncio.sleep(random.uniform(3.5, 6.0))

    await context.close()
    return results


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Automated CloakBrowser LinkedIn Outreach Dispatcher (Peter Lodri / 8b-is)"
    )
    parser.add_argument("--run-all", action="store_true", help="Dispatch to all 16 targets E2E")
    parser.add_argument("--prospect", type=str, default="", help="Dispatch to a single prospect")
    parser.add_argument(
        "--tier1-labs-only",
        action="store_true",
        help="Dispatch to the 14 founders/researchers across the 5 Tier-1 AI Labs",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Open Connect modal and fill the <=300 char note without clicking Send",
    )
    parser.add_argument(
        "--headless",
        action="store_true",
        help="Run CloakBrowser in headless mode",
    )
    parser.add_argument(
        "--no-whatsapp",
        action="store_true",
        help="Disable per-target WhatsApp screenshot + confirmation notifications",
    )
    parser.add_argument(
        "--li-at",
        type=str,
        default=os.getenv("LI_AT", ""),
        help="Optional LinkedIn li_at session cookie override",
    )
    parser.add_argument("--list-urls", action="store_true", help="List all target LinkedIn URLs")
    parser.add_argument(
        "--start-index",
        type=int,
        default=1,
        help="1-based index to resume batch dispatch from",
    )
    parser.add_argument(
        "--copy-and-open",
        action="store_true",
        help="Copy connection note to macOS clipboard (pbcopy) and open profile URL in default browser",
    )
    args = parser.parse_args()

    if args.list_urls:
        for idx, (k, d) in enumerate(PROSPECT_DOSSIER_CATALOG.items(), start=1):
            u = TARGET_LINKEDIN_URLS.get(k, {}).get("linkedin_url", "")
            print(f"{idx:2d}. {d['prospect_name']:28s} | {d['company_or_lab']:20s} | {u}")
        return

    if args.prospect:
        norm = args.prospect.strip().lower()
        keys = [k for k in PROSPECT_DOSSIER_CATALOG if norm in k or k in norm]
        if not keys:
            raise SystemExit(f"No matching prospect in catalog for: {args.prospect}")
    elif args.tier1_labs_only:
        keys = [
            k
            for k in PROSPECT_DOSSIER_CATALOG
            if k not in ("tokyo b2b lead", "joe rogan / comedy mothership")
        ]
    else:
        keys = list(PROSPECT_DOSSIER_CATALOG.keys())

    if args.copy_and_open:
        first_key = keys[0]
        dossier = PROSPECT_DOSSIER_CATALOG[first_key]
        pack = build_offline_campaign_pack(
            prospect_name=dossier["prospect_name"],
            company_or_lab=dossier["company_or_lab"],
        )
        note_300 = pack["final_sequence"]["connection_note_300"]
        url = TARGET_LINKEDIN_URLS.get(first_key, {}).get(
            "linkedin_url", "https://www.linkedin.com/feed/"
        )
        subprocess.run(["pbcopy"], input=note_300.encode("utf-8"), check=False)
        subprocess.run(["open", url], check=False)
        print(
            f"[COPIED TO CLIPBOARD & OPENED] {dossier['prospect_name']} ({dossier['company_or_lab']}) "
            f"[{len(note_300)}/300 chars]\nURL: {url}\nNote: {note_300}"
        )
        return

    results = asyncio.run(
        run_playwright_campaign(
            target_keys=keys,
            li_at_cookie=args.li_at or None,
            dry_run=args.dry_run,
            headless=args.headless,
            notify_whatsapp=not args.no_whatsapp,
            start_index=args.start_index,
        )
    )
    print(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()
