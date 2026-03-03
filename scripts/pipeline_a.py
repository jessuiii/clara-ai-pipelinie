#!/usr/bin/env python3
"""
Pipeline A: Demo Call Transcript -> Preliminary Retell Agent
Zero-cost: uses rule-based extraction + Anthropic API (free tier via claude.ai API or local)
"""

import json
import os
import re
import sys
import uuid
import hashlib
from datetime import datetime
from pathlib import Path

# ── Config ────────────────────────────────────────────────────────────────────
OUTPUTS_DIR = Path(__file__).parent.parent / "outputs" / "accounts"
CHANGELOG_DIR = Path(__file__).parent.parent / "changelog"

# ── LLM Client (zero-cost: uses Anthropic free-tier API key from env) ─────────
def call_llm(prompt: str) -> str:
    """Call Claude API. Set ANTHROPIC_API_KEY in env (free tier)."""
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("[WARN] ANTHROPIC_API_KEY not set — using rule-based fallback extraction.")
        return ""

    try:
        import anthropic
        client = anthropic.Anthropic(api_key=api_key)
        message = client.messages.create(
            model="claude-haiku-4-5-20251001",  # cheapest / free-tier friendly
            max_tokens=2048,
            messages=[{"role": "user", "content": prompt}]
        )
        return message.content[0].text
    except Exception as e:
        print(f"[WARN] LLM call failed: {e}. Falling back to rule-based extraction.")
        return ""

# ── Rule-based extraction helpers ─────────────────────────────────────────────
def extract_company_name(text: str) -> str:
    patterns = [
        r"(?:company|business|account|client)[:\s]+([A-Z][A-Za-z0-9\s&,.-]{2,40})",
        r"(?:this is|calling from|with)\s+([A-Z][A-Za-z0-9\s&]{2,30})",
        r"([A-Z][A-Za-z0-9\s&]{2,30})\s+(?:LLC|Inc|Corp|Ltd|Co\.)",
    ]
    for p in patterns:
        m = re.search(p, text)
        if m:
            return m.group(1).strip()
    return "Unknown Company"

def extract_business_hours(text: str) -> dict:
    hours = {"days": [], "start": "", "end": "", "timezone": ""}
    # Days
    day_map = {"monday":"Mon","tuesday":"Tue","wednesday":"Wed","thursday":"Thu",
               "friday":"Fri","saturday":"Sat","sunday":"Sun"}
    found_days = [v for k,v in day_map.items() if k in text.lower()]
    if found_days:
        hours["days"] = found_days
    elif re.search(r"mon(day)?\s*(through|to|-)\s*fri(day)?", text, re.I):
        hours["days"] = ["Mon","Tue","Wed","Thu","Fri"]

    # Hours
    time_pattern = r"(\d{1,2}(?::\d{2})?\s*(?:am|pm))\s*(?:to|-|through)\s*(\d{1,2}(?::\d{2})?\s*(?:am|pm))"
    m = re.search(time_pattern, text, re.I)
    if m:
        hours["start"] = m.group(1).strip()
        hours["end"] = m.group(2).strip()

    # Timezone
    tz_pattern = r"\b(EST|CST|MST|PST|EDT|CDT|MDT|PDT|Eastern|Central|Mountain|Pacific)\b"
    m = re.search(tz_pattern, text, re.I)
    if m:
        hours["timezone"] = m.group(1)

    return hours

def extract_address(text: str) -> str:
    addr_pattern = r"\d{1,5}\s+[A-Za-z0-9\s,.-]{5,60}(?:Street|St|Avenue|Ave|Blvd|Road|Rd|Drive|Dr|Lane|Ln|Way|Court|Ct)[.,\s]"
    m = re.search(addr_pattern, text, re.I)
    return m.group(0).strip() if m else ""

def extract_services(text: str) -> list:
    services = []
    keywords = ["hvac","plumbing","electrical","roofing","pest control","landscaping",
                "cleaning","security","fire","sprinkler","elevator","generator",
                "mechanical","refrigeration","air conditioning","heating","ventilation"]
    for kw in keywords:
        if kw in text.lower():
            services.append(kw.title())
    return list(set(services)) or ["General Facility Services"]

def extract_emergency_definition(text: str) -> list:
    triggers = []
    keywords = ["flood","fire","gas leak","no heat","no cool","power outage","burst pipe",
                "water damage","smoke","alarm","critical","urgent","after hours emergency"]
    for kw in keywords:
        if kw in text.lower():
            triggers.append(kw.title())
    return triggers or ["No heat/cool", "Water leak", "Fire/smoke alarm"]

def extract_routing(text: str, routing_type: str) -> dict:
    contacts = re.findall(r"(?:call|contact|reach|transfer to)\s+([A-Z][a-z]+(?:\s[A-Z][a-z]+)?)\s+(?:at\s+)?([\d\s\-().+]{7,20})?", text, re.I)
    routing = {"primary": "", "fallback": "voicemail or answering service"}
    if contacts:
        routing["primary"] = f"{contacts[0][0]} {contacts[0][1]}".strip()
        if len(contacts) > 1:
            routing["secondary"] = f"{contacts[1][0]} {contacts[1][1]}".strip()
    return routing

# ── LLM-based extraction (preferred when API key available) ───────────────────
EXTRACTION_PROMPT = """You are a precise data extractor for a facilities management AI assistant setup.

Given the following call transcript, extract structured information and return ONLY valid JSON with these exact fields. Do NOT invent information — use null or empty list if missing.

TRANSCRIPT:
{transcript}

Return JSON with this exact structure:
{{
  "company_name": "string or null",
  "business_hours": {{
    "days": ["Mon","Tue",...],
    "start": "8:00am",
    "end": "5:00pm",
    "timezone": "EST"
  }},
  "office_address": "string or null",
  "services_supported": ["list of services"],
  "emergency_definition": ["list of emergency trigger types"],
  "emergency_routing_rules": {{
    "primary_contact": "name and number",
    "secondary_contact": "name and number or null",
    "fallback": "what to do if no answer"
  }},
  "non_emergency_routing_rules": {{
    "action": "take message / transfer / schedule",
    "destination": "who/where"
  }},
  "call_transfer_rules": {{
    "timeout_seconds": 30,
    "retries": 1,
    "if_transfer_fails": "what to say"
  }},
  "integration_constraints": ["list of constraints like never create X jobs in Y system"],
  "after_hours_flow_summary": "one paragraph summary",
  "office_hours_flow_summary": "one paragraph summary",
  "questions_or_unknowns": ["only truly missing critical info"],
  "notes": "short notes"
}}"""

def extract_from_transcript_llm(transcript: str) -> dict:
    prompt = EXTRACTION_PROMPT.format(transcript=transcript[:8000])
    response = call_llm(prompt)
    if not response:
        return {}
    # Strip markdown fences if present
    response = re.sub(r"```json|```", "", response).strip()
    try:
        return json.loads(response)
    except json.JSONDecodeError:
        return {}

def extract_from_transcript_rules(transcript: str) -> dict:
    """Fallback rule-based extraction."""
    return {
        "company_name": extract_company_name(transcript),
        "business_hours": extract_business_hours(transcript),
        "office_address": extract_address(transcript),
        "services_supported": extract_services(transcript),
        "emergency_definition": extract_emergency_definition(transcript),
        "emergency_routing_rules": extract_routing(transcript, "emergency"),
        "non_emergency_routing_rules": {"action": "take message", "destination": "office voicemail"},
        "call_transfer_rules": {"timeout_seconds": 30, "retries": 1, "if_transfer_fails": "Take a detailed message and assure callback within 30 minutes"},
        "integration_constraints": [],
        "after_hours_flow_summary": "Greet caller, confirm emergency status, collect name/number/address, attempt transfer to on-call tech, leave message if unavailable.",
        "office_hours_flow_summary": "Greet caller, collect name and callback number, route to appropriate department or take message.",
        "questions_or_unknowns": [],
        "notes": "Extracted via rule-based fallback."
    }

# ── Account Memo builder ───────────────────────────────────────────────────────
def build_account_memo(transcript: str, account_id: str, version: str = "v1", source_file: str = "") -> dict:
    # Try LLM first, fall back to rules
    extracted = extract_from_transcript_llm(transcript)
    if not extracted or not extracted.get("company_name"):
        print("  → Using rule-based extraction")
        extracted = extract_from_transcript_rules(transcript)

    memo = {
        "account_id": account_id,
        "version": version,
        "created_at": datetime.utcnow().isoformat() + "Z",
        "source_file": source_file,
        **extracted
    }
    return memo

# ── Retell Agent Spec builder ──────────────────────────────────────────────────
SYSTEM_PROMPT_TEMPLATE = """You are {agent_name}, a professional AI receptionist for {company_name}.

## IDENTITY
- You are a helpful, professional phone receptionist.
- Never mention that you are an AI or use terms like "function call", "transfer tool", or "API".
- Speak naturally and concisely.

## OFFICE HOURS
- Business hours: {days}, {start} to {end} {timezone}

## OFFICE HOURS CALL FLOW
1. Greet: "Thank you for calling {company_name}, this is {agent_name}. How can I help you today?"
2. Listen and identify the nature of the call.
3. Collect caller's first name and best callback number.
4. If routine inquiry: "I'll make sure the right person gets back to you."
5. Attempt transfer if applicable: [TRANSFER: {{destination}}]
6. If transfer fails: "I wasn't able to connect you directly. I've noted your information and someone will call you back shortly. Is there anything else I can help you with?"
7. Confirm next steps and close: "Thank you for calling {company_name}. Have a great day!"

## AFTER HOURS CALL FLOW
1. Greet: "Thank you for calling {company_name}. Our office is currently closed. If this is an emergency, please stay on the line."
2. Confirm: "Is this an emergency situation?" 
3. IF EMERGENCY:
   a. "I'm going to connect you with our on-call technician. First, can I get your name, best callback number, and the address of the issue?"
   b. Collect: name, phone, address
   c. Attempt emergency transfer: [TRANSFER: {{emergency_contact}}]
   d. If transfer fails: "I was unable to reach our on-call team directly. I've recorded your information as urgent and a technician will call you back within 30 minutes. Please call 911 if there is immediate danger."
4. IF NOT EMERGENCY:
   a. "Our team is available {days} from {start} to {end} {timezone}. Can I take your name and number so someone can follow up with you first thing?"
   b. Collect name and callback number.
   c. "We'll be in touch during business hours. Is there anything else?"
5. Close: "Thank you for calling {company_name}. Have a good night."

## EMERGENCY TRIGGERS
The following qualify as emergencies: {emergency_triggers}

## TRANSFER PROTOCOL
- Attempt transfer silently without telling the caller you are "transferring" by name.
- Say: "Let me connect you with the right person now."
- If no answer after {timeout}s: retry once, then take message.
- Never leave the caller without a clear next step.

## RULES
- Do not ask more questions than necessary.
- Only collect: name, callback number, and address (emergencies only).
- Do not mention internal systems, tools, or software by name.
- Keep responses under 3 sentences unless explaining a process.
- Services supported: {services}
"""

def build_agent_spec(memo: dict, version: str = "v1") -> dict:
    bh = memo.get("business_hours", {})
    days_str = ", ".join(bh.get("days", ["Mon-Fri"]))
    emergency_triggers = ", ".join(memo.get("emergency_definition", ["flood", "fire", "no heat/cool"]))
    services = ", ".join(memo.get("services_supported", ["general services"]))
    transfer_rules = memo.get("call_transfer_rules", {})
    emergency_routing = memo.get("emergency_routing_rules", {})

    agent_name = "Clara"
    company_name = memo.get("company_name", "our company")

    system_prompt = SYSTEM_PROMPT_TEMPLATE.format(
        agent_name=agent_name,
        company_name=company_name,
        days=days_str,
        start=bh.get("start", "8:00am"),
        end=bh.get("end", "5:00pm"),
        timezone=bh.get("timezone", "local time"),
        emergency_triggers=emergency_triggers,
        timeout=transfer_rules.get("timeout_seconds", 30),
        services=services
    )

    spec = {
        "agent_name": agent_name,
        "version": version,
        "account_id": memo.get("account_id"),
        "created_at": datetime.utcnow().isoformat() + "Z",
        "voice_style": {
            "provider": "elevenlabs",
            "voice_id": "rachel",  # professional female voice
            "speed": 1.0,
            "stability": 0.75
        },
        "system_prompt": system_prompt,
        "key_variables": {
            "timezone": bh.get("timezone", ""),
            "business_hours_start": bh.get("start", ""),
            "business_hours_end": bh.get("end", ""),
            "business_days": bh.get("days", []),
            "office_address": memo.get("office_address", ""),
            "emergency_contact_primary": emergency_routing.get("primary_contact", ""),
            "emergency_contact_fallback": emergency_routing.get("fallback", "voicemail"),
            "company_name": company_name
        },
        "tool_invocation_placeholders": {
            "transfer_call": {
                "trigger": "when caller needs to be connected to a person",
                "destinations": {
                    "emergency": emergency_routing.get("primary_contact", ""),
                    "office": memo.get("non_emergency_routing_rules", {}).get("destination", "")
                },
                "note": "Do NOT mention this tool to the caller by name"
            },
            "create_ticket": {
                "trigger": "after collecting caller info for non-emergency after-hours",
                "fields": ["caller_name", "callback_number", "issue_summary"],
                "note": "Silent background action"
            }
        },
        "call_transfer_protocol": {
            "timeout_seconds": transfer_rules.get("timeout_seconds", 30),
            "retries": transfer_rules.get("retries", 1),
            "on_failure": transfer_rules.get("if_transfer_fails", "Take message, assure callback")
        },
        "fallback_protocol": {
            "message": "I wasn't able to connect you. I've noted your information and someone will follow up shortly.",
            "collect_before_fallback": ["name", "phone"],
            "emergency_addition": ["address"]
        },
        "integration_constraints": memo.get("integration_constraints", [])
    }
    return spec

# ── File I/O ───────────────────────────────────────────────────────────────────
def save_outputs(account_id: str, version: str, memo: dict, spec: dict):
    out_dir = OUTPUTS_DIR / account_id / version
    out_dir.mkdir(parents=True, exist_ok=True)

    memo_path = out_dir / "account_memo.json"
    spec_path = out_dir / "agent_spec.json"

    with open(memo_path, "w") as f:
        json.dump(memo, f, indent=2)
    with open(spec_path, "w") as f:
        json.dump(spec, f, indent=2)

    print(f"  ✓ Saved memo: {memo_path}")
    print(f"  ✓ Saved spec: {spec_path}")
    return memo_path, spec_path

def derive_account_id(text: str, source_file: str) -> str:
    """Derive a stable account_id from filename or content hash."""
    base = Path(source_file).stem if source_file else ""
    # Try to get company slug from filename
    slug = re.sub(r"[^a-z0-9]", "_", base.lower())[:20].strip("_")
    if slug:
        return f"acc_{slug}"
    # Fall back to content hash
    h = hashlib.md5(text[:200].encode()).hexdigest()[:8]
    return f"acc_{h}"

# ── Main Pipeline A ────────────────────────────────────────────────────────────
def run_pipeline_a(transcript_path: str, account_id: str = None) -> dict:
    print(f"\n[Pipeline A] Processing: {transcript_path}")

    with open(transcript_path, "r", encoding="utf-8") as f:
        transcript = f.read()

    if not account_id:
        account_id = derive_account_id(transcript, transcript_path)

    print(f"  Account ID: {account_id}")

    # Step 1: Extract
    print("  → Extracting account memo...")
    memo = build_account_memo(transcript, account_id, version="v1", source_file=transcript_path)

    # Step 2: Generate agent spec
    print("  → Generating Retell agent spec v1...")
    spec = build_agent_spec(memo, version="v1")

    # Step 3: Save
    save_outputs(account_id, "v1", memo, spec)

    return {"account_id": account_id, "memo": memo, "spec": spec}

# ── CLI entry ──────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python pipeline_a.py <transcript_file> [account_id]")
        sys.exit(1)
    transcript_file = sys.argv[1]
    acc_id = sys.argv[2] if len(sys.argv) > 2 else None
    result = run_pipeline_a(transcript_file, acc_id)
    print(f"\n[Done] Account ID: {result['account_id']}")
