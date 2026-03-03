#!/usr/bin/env python3
"""
Pipeline B: Onboarding Call Transcript -> Agent Modification (v1 -> v2)
Produces: updated memo, updated agent spec, changelog
"""

import json
import os
import re
import sys
from datetime import datetime
from pathlib import Path

# Import shared helpers from pipeline_a
sys.path.insert(0, str(Path(__file__).parent))
from pipeline_a import (
    OUTPUTS_DIR, CHANGELOG_DIR,
    extract_from_transcript_llm, extract_from_transcript_rules,
    build_agent_spec, call_llm, derive_account_id
)

# ── Diff utilities ─────────────────────────────────────────────────────────────
def deep_diff(old: dict, new: dict, path: str = "") -> list:
    """Recursively diff two dicts, return list of change records."""
    changes = []
    all_keys = set(list(old.keys()) + list(new.keys()))
    for key in sorted(all_keys):
        current_path = f"{path}.{key}" if path else key
        old_val = old.get(key)
        new_val = new.get(key)
        if old_val == new_val:
            continue
        if isinstance(old_val, dict) and isinstance(new_val, dict):
            changes.extend(deep_diff(old_val, new_val, current_path))
        elif isinstance(old_val, list) and isinstance(new_val, list):
            if old_val != new_val:
                changes.append({
                    "field": current_path,
                    "old": old_val,
                    "new": new_val,
                    "change_type": "list_updated"
                })
        else:
            changes.append({
                "field": current_path,
                "old": old_val,
                "new": new_val,
                "change_type": "value_updated" if (old_val and new_val) else ("added" if new_val else "removed")
            })
    return changes

def generate_changelog(account_id: str, old_memo: dict, new_memo: dict, changes: list, source_file: str) -> dict:
    return {
        "account_id": account_id,
        "changelog_generated_at": datetime.utcnow().isoformat() + "Z",
        "from_version": "v1",
        "to_version": "v2",
        "source_file": source_file,
        "summary": f"{len(changes)} field(s) updated during onboarding",
        "changes": changes
    }

# ── LLM-assisted update extraction ────────────────────────────────────────────
UPDATE_PROMPT = """You are updating an existing account configuration based on new onboarding call information.

EXISTING ACCOUNT MEMO (v1):
{existing_memo}

NEW ONBOARDING TRANSCRIPT:
{transcript}

Extract ONLY the fields that are NEW or DIFFERENT from the onboarding transcript.
Return ONLY valid JSON containing the fields that changed or were added.
Do NOT re-include fields that haven't changed.
Do NOT invent information — only include what is explicitly stated in the onboarding transcript.

Return JSON with any subset of these fields:
{{
  "company_name": "...",
  "business_hours": {{"days": [], "start": "", "end": "", "timezone": ""}},
  "office_address": "...",
  "services_supported": [],
  "emergency_definition": [],
  "emergency_routing_rules": {{}},
  "non_emergency_routing_rules": {{}},
  "call_transfer_rules": {{}},
  "integration_constraints": [],
  "after_hours_flow_summary": "...",
  "office_hours_flow_summary": "...",
  "questions_or_unknowns": [],
  "notes": "..."
}}"""

def extract_updates_llm(transcript: str, existing_memo: dict) -> dict:
    memo_str = json.dumps(existing_memo, indent=2)[:3000]
    prompt = UPDATE_PROMPT.format(existing_memo=memo_str, transcript=transcript[:6000])
    response = call_llm(prompt)
    if not response:
        return {}
    response = re.sub(r"```json|```", "", response).strip()
    try:
        return json.loads(response)
    except json.JSONDecodeError:
        return {}

def extract_updates_rules(transcript: str, existing_memo: dict) -> dict:
    """Rule-based: extract only fields that seem new/changed."""
    from pipeline_a import (extract_company_name, extract_business_hours,
                             extract_address, extract_services,
                             extract_emergency_definition, extract_routing)
    updates = {}

    new_hours = extract_business_hours(transcript)
    if new_hours.get("start") and new_hours != existing_memo.get("business_hours"):
        updates["business_hours"] = new_hours

    new_addr = extract_address(transcript)
    if new_addr and new_addr != existing_memo.get("office_address"):
        updates["office_address"] = new_addr

    new_services = extract_services(transcript)
    existing_services = existing_memo.get("services_supported", [])
    merged_services = list(set(existing_services + new_services))
    if merged_services != existing_services:
        updates["services_supported"] = merged_services

    new_emergency = extract_emergency_definition(transcript)
    if new_emergency and new_emergency != existing_memo.get("emergency_definition"):
        updates["emergency_definition"] = new_emergency

    # Look for integration constraints
    constraint_patterns = [
        r"(?:never|don't|do not)\s+(?:create|add|use|enter)\s+([^.]{5,60})",
        r"(?:must not|should not)\s+([^.]{5,60})"
    ]
    constraints = []
    for p in constraint_patterns:
        for m in re.finditer(p, transcript, re.I):
            constraints.append(m.group(0).strip())
    if constraints:
        updates["integration_constraints"] = constraints

    if updates:
        updates["notes"] = "Updated via rule-based onboarding extraction."

    return updates

def merge_memos(v1_memo: dict, updates: dict) -> dict:
    """Deep merge updates into v1 memo to produce v2."""
    import copy
    v2 = copy.deepcopy(v1_memo)
    for key, value in updates.items():
        if isinstance(value, dict) and isinstance(v2.get(key), dict):
            v2[key].update(value)
        elif isinstance(value, list) and isinstance(v2.get(key), list):
            # Merge lists (union)
            existing = v2[key]
            merged = existing + [x for x in value if x not in existing]
            v2[key] = merged
        else:
            v2[key] = value
    v2["version"] = "v2"
    v2["updated_at"] = datetime.utcnow().isoformat() + "Z"
    return v2

# ── Save utilities ─────────────────────────────────────────────────────────────
def save_v2_outputs(account_id: str, memo_v2: dict, spec_v2: dict, changelog: dict):
    from pipeline_a import OUTPUTS_DIR, CHANGELOG_DIR

    # Save v2 memo and spec
    out_dir = OUTPUTS_DIR / account_id / "v2"
    out_dir.mkdir(parents=True, exist_ok=True)
    with open(out_dir / "account_memo.json", "w") as f:
        json.dump(memo_v2, f, indent=2)
    with open(out_dir / "agent_spec.json", "w") as f:
        json.dump(spec_v2, f, indent=2)

    # Save changelog
    CHANGELOG_DIR.mkdir(parents=True, exist_ok=True)
    cl_path = CHANGELOG_DIR / f"{account_id}_changelog.json"
    with open(cl_path, "w") as f:
        json.dump(changelog, f, indent=2)

    # Also write human-readable changelog.md
    md_path = CHANGELOG_DIR / f"{account_id}_changes.md"
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(f"# Changelog: {account_id}\n\n")
        f.write(f"**Generated:** {changelog['changelog_generated_at']}\n")
        f.write(f"**Version:** v1 → v2\n")
        f.write(f"**Summary:** {changelog['summary']}\n\n")
        f.write("## Changes\n\n")
        for ch in changelog.get("changes", []):
            f.write(f"### `{ch['field']}`\n")
            f.write(f"- **Before:** `{ch['old']}`\n")
            f.write(f"- **After:** `{ch['new']}`\n")
            f.write(f"- **Type:** {ch['change_type']}\n\n")
        if not changelog.get("changes"):
            f.write("_No changes detected — onboarding confirmed existing configuration._\n")

    print(f"  ✓ Saved v2 memo: {out_dir}/account_memo.json")
    print(f"  ✓ Saved v2 spec: {out_dir}/agent_spec.json")
    print(f"  ✓ Saved changelog: {cl_path}")
    print(f"  ✓ Saved changes.md: {md_path}")

# ── Main Pipeline B ────────────────────────────────────────────────────────────
def run_pipeline_b(onboarding_transcript_path: str, account_id: str) -> dict:
    print(f"\n[Pipeline B] Processing onboarding for: {account_id}")
    print(f"  Onboarding file: {onboarding_transcript_path}")

    # Load existing v1 memo
    v1_memo_path = OUTPUTS_DIR / account_id / "v1" / "account_memo.json"
    if not v1_memo_path.exists():
        print(f"  [ERROR] No v1 memo found at {v1_memo_path}")
        print(f"  Run Pipeline A first for account: {account_id}")
        sys.exit(1)

    with open(v1_memo_path) as f:
        v1_memo = json.load(f)

    # Read onboarding transcript
    with open(onboarding_transcript_path, "r", encoding="utf-8") as f:
        transcript = f.read()

    # Extract updates
    print("  → Extracting updates from onboarding transcript...")
    updates = extract_updates_llm(transcript, v1_memo)
    if not updates:
        print("  → Using rule-based update extraction")
        updates = extract_updates_rules(transcript, v1_memo)

    if not updates:
        print("  → No changes detected, onboarding confirmed existing config")

    # Merge
    v2_memo = merge_memos(v1_memo, updates)

    # Generate diff
    changes = deep_diff(v1_memo, v2_memo)
    # Filter out metadata changes
    changes = [c for c in changes if c["field"] not in ("version", "updated_at", "created_at")]

    # Build v2 agent spec
    print("  → Generating Retell agent spec v2...")
    v2_spec = build_agent_spec(v2_memo, version="v2")

    # Build changelog
    changelog = generate_changelog(account_id, v1_memo, v2_memo, changes, onboarding_transcript_path)

    # Save everything
    save_v2_outputs(account_id, v2_memo, v2_spec, changelog)

    print(f"\n[Done] {len(changes)} change(s) applied — v1 → v2")
    return {"account_id": account_id, "changes": len(changes), "memo_v2": v2_memo}

# ── CLI entry ──────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python pipeline_b.py <onboarding_transcript> <account_id>")
        sys.exit(1)
    result = run_pipeline_b(sys.argv[1], sys.argv[2])
    print(f"\nChanges applied: {result['changes']}")
