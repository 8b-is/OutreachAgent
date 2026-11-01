//! `OutreachAgent` — Pure-Rust `g8t.is` Function Capsules
//!
//! Made with love from within (`8b-is // Project Omni`).
//! Obeys all `g8t.is` C64 & `8b-is` Zero-Float constraints (`zero_unsafe`, `zero_floats`, `zero_external_crates`).

/// Standalone pure-Rust function capsule 1: LinkedIn 300-character budget & citation gate.
/// Evaluates `char_len`, `citation_count`, and `slop_hits` into a packed verdict:
/// - Returns `0` (`Neg` / Reject) if `char_len == 0`, `char_len > 300`, `citation_count == 0`, or `slop_hits > 0`.
/// - Otherwise returns `(300 - char_len) + (citation_count * 1024)` (headroom + citation density score).
pub fn outreach_char_budget_trit_gate(char_len: u64, citation_count: u64, slop_hits: u64) -> u64 {
    if char_len == 0 || char_len > 300 || citation_count == 0 || slop_hits > 0 {
        return 0;
    }
    let headroom = 300 - char_len;
    let capped_citations = if citation_count > 16 { 16 } else { citation_count };
    headroom.saturating_add(capped_citations.saturating_mul(1024))
}

/// Standalone pure-Rust function capsule 2: Multi-touch sequence cadence interval calculator (hours).
/// Maps touch index (`0 = Connection Note`, `1 = Day 1 DM`, `2 = Day 3 Artifact Drop`, `3 = Day 7 CTA`)
/// and prospect track (`0 = In-Person Tokyo Hardware`, `1 = Frontier Lab RL/SSM`, `2 = B2B Turnkey Sprint`)
/// to deterministic integer wait hours before next touch.
pub fn outreach_cadence_delay_hours(touch_index: u64, track_kind: u64) -> u64 {
    let base_hours = if touch_index == 0 {
        0
    } else if touch_index == 1 {
        24
    } else if touch_index == 2 {
        72
    } else {
        168
    };
    if track_kind == 0 {
        base_hours / 2
    } else if track_kind == 2 {
        (base_hours * 3) / 4
    } else {
        base_hours
    }
}
