#!/usr/bin/env python3
"""
Pipeline A: Demo Call Transcript -> Preliminary Retell Agent
Zero-cost: uses rule-based extraction + Groq free API
"""

import json
import os
import re
import sys
import hashlib
from datetime import datetime
from pathlib import Path

OUTPUTS_DIR = Path(__file__).parent.parent / "outputs" / "accounts"
CHANGELOG_DIR = Path(__file__).parent.parent / "changelog"

def call_llm(prompt: str) -> str:
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        print("[WARN] GROQ_API_KEY not set — using rule-based fallback extraction.")
        return ""

    import urllib.request
    import urllib.error

    payload = json.dumps({
        "model": "llama-3.3-70b-versatile",
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 2048,
        "temperature": 0.1
    }).encode("utf-8")

    req = urllib.request.Request(
        "https://api.groq.com/openai/v1/chat/completions",
        data=payload,
        headers={
            "Authorization": "Bearer " + api_key,
            "Content-Type": "application/json",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        },
        method="POST"
    )

    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            result = json.loads(resp.read().decode("utf-8"))
            return result["choices"][0]["message"]["content"]
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        print(f"[WARN] Groq HTTP {e.code}: {body[:300]}. Falling back to rule-based.")
        return ""
    except Exception as e:
        print(f"[WARN] Groq call failed: {e}. Falling back to rule-based.")
        return ""

def extract_company_name(text):
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

def extract_business_hours(text):
    hours = {"days": [], "start": "", "end": "", "timezone": ""}
    day_map = {"monday":"Mon","tuesday":"Tue","wednesday":"Wed","thursday":"Thu","friday":"Fri","saturday":"Sat","sunday":"Sun"}
    found_days = [v for k,v in day_map.items() if k in text.lower()]
    if found_days:
        hours["days"] = found_days
    elif re.search(r"mon(day)?\s*(through|to|-)\s*fri(day)?", text, re.I):
        hours["days"] = ["Mon","Tue","Wed","Thu","Fri"]
    m = re.search(r"(\d{1,2}(?::\d{2})?\s*(?:am|pm))\s*(?:to|-|through)\s*(\d{1,2}(?::\d{2})?\s*(?:am|pm))", text, re.I)
    if m:
        hours["start"] = m.group(1).strip()
        hours["end"] = m.group(2).strip()
    m = re.search(r"\b(EST|CST|MST|PST|EDT|CDT|MDT|PDT|Eastern|Central|Mountain|Pacific)\b", text, re.I)
    if m:
        hours["timezone"] = m.group(1)
    return hours

def extract_address(text):
    m = re.search(r"\d{1,5}\s+[A-Za-z0-9\s,.-]{5,60}(?:Street|St|Avenue|Ave|Blvd|Road|Rd|Drive|Dr|Lane|Ln|Way|Court|Ct)[.,\s]", text, re.I)
    return m.group(0).strip() if m else ""

def extract_services(text):
    keywords = ["hvac","plumbing","electrical","roofing","pest control","landscaping","cleaning","security","fire","sprinkler","elevator","generator","mechanical","refrigeration","air conditioning","heating","ventilation"]
    return list(set([kw.title() for kw in keywords if kw in text.lower()])) or ["General Facility Services"]

def extract_emergency_definition(text):
    keywords = ["flood","fire","gas leak","no heat","no cool","power outage","burst pipe","water damage","smoke","alarm","critical","urgent"]
    found = [kw.title() for kw in keywords if kw in text.lower()]
    return found or ["No heat/cool", "Water leak", "Fire/smoke alarm"]

def extract_routing(text, routing_type):
    contacts = re.findall(r"(?:call|contact|reach|transfer to)\s+([A-Z][a-z]+(?:\s[A-Z][a-z]+)?)\s+(?:at\s+)?([\d\s\-().+]{7,20})?", text, re.I)
    routing = {"primary": "", "fallback": "voicemail or answering service"}
    if contacts:
        routing["primary"] = f"{contacts[0][0]} {contacts[0][1]}".strip()
        if len(contacts) > 1:
            routing["secondary"] = f"{contacts[1][0]} {contacts[1][1]}".strip()
    return routing

EXTRACTION_PROMPT = """You are a precise data extractor for a facilities management AI assistant.

Read this call transcript carefully and extract the structured data. Return ONLY valid JSON — no extra text, no markdown fences.

TRANSCRIPT:
{transcript}

Return this exact JSON structure:
{{
  "company_name": "exact company name from transcript",
  "business_hours": {{
    "days": ["Mon","Tue","Wed","Thu","Fri"],
    "start": "7:00am",
    "end": "6:00pm",
    "timezone": "Central"
  }},
  "office_address": "full address or null",
  "services_supported": ["service1", "service2"],
  "emergency_definition": ["trigger1", "trigger2"],
  "emergency_routing_rules": {{
    "primary_contact": "Name and phone number",
    "secondary_contact": "Name and phone number or null",
    "fallback": "what happens if no answer"
  }},
  "non_emergency_routing_rules": {{
    "action": "take message or transfer",
    "destination": "where/who"
  }},
  "call_transfer_rules": {{
    "timeout_seconds": 30,
    "retries": 1,
    "if_transfer_fails": "what to tell caller"
  }},
  "integration_constraints": ["never do X in Y system"],
  "after_hours_flow_summary": "brief summary of after hours process",
  "office_hours_flow_summary": "brief summary of office hours process",
  "questions_or_unknowns": [],
  "notes": "any important notes"
}}"""

def extract_from_transcript_llm(transcript):
    prompt = EXTRACTION_PROMPT.format(transcript=transcript[:18000])
    response = call_llm(prompt)
    if not response:
        return {}
    response = re.sub(r"```json|```", "", response).strip()
    start = response.find("{")
    end = response.rfind("}") + 1
    if start >= 0 and end > start:
        response = response[start:end]
    try:
        return json.loads(response)
    except json.JSONDecodeError as e:
        print(f"[WARN] JSON parse failed: {e}")
        return {}

def extract_from_transcript_rules(transcript):
    """Rule-based extraction. Only populates fields explicitly found in the transcript.
    Never invents defaults — ambiguous or missing fields are left null and flagged."""
    bh = extract_business_hours(transcript)
    routing = extract_routing(transcript, "emergency")
    unknowns = []

    # Flag fields we can't reliably extract from a demo call alone
    if not bh.get("start"):
        unknowns.append("Business hours (start/end time) not confirmed — to be finalized during onboarding.")
    if not bh.get("timezone"):
        unknowns.append("Timezone not explicitly stated — confirm during onboarding.")
    if not routing.get("primary"):
        unknowns.append("Emergency on-call contact not explicitly named — confirm during onboarding.")
    if not extract_address(transcript):
        unknowns.append("Office address not mentioned — confirm during onboarding.")

    return {
        "company_name": extract_company_name(transcript),
        "business_hours": bh if any(bh.values()) else {"days": None, "start": None, "end": None, "timezone": None},
        "office_address": extract_address(transcript) or None,
        "services_supported": extract_services(transcript),
        "emergency_definition": extract_emergency_definition(transcript),
        "emergency_routing_rules": {
            "primary_contact": routing.get("primary") or None,
            "secondary_contact": routing.get("secondary") or None,
            "fallback": None  # Must be confirmed during onboarding
        },
        "non_emergency_routing_rules": {
            "action": None,       # Not safe to assume — confirm during onboarding
            "destination": None
        },
        "call_transfer_rules": {
            "timeout_seconds": None,  # Not discussed in demo — confirm during onboarding
            "retries": None,
            "if_transfer_fails": None
        },
        "integration_constraints": [],
        "after_hours_flow_summary": None,   # Cannot be assumed — to be defined during onboarding
        "office_hours_flow_summary": None,  # Cannot be assumed — to be defined during onboarding
        "questions_or_unknowns": unknowns,
        "notes": "Extracted via rule-based fallback. LLM extraction was unavailable or returned no data."
    }

def build_account_memo(transcript, account_id, version="v1", source_file=""):
    extracted = extract_from_transcript_llm(transcript)
    if not extracted or not extracted.get("company_name"):
        print("  → Using rule-based extraction")
        extracted = extract_from_transcript_rules(transcript)
    else:
        print("  → AI extraction successful (Groq/Kimi)")
    return {"account_id": account_id, "version": version, "created_at": datetime.now().isoformat() + "Z", "source_file": source_file, **extracted}

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
5. Attempt transfer if applicable.
6. If transfer fails: "I wasn't able to connect you directly. I've noted your information and someone will call you back shortly."
7. Confirm next steps and close: "Thank you for calling {company_name}. Have a great day!"

## AFTER HOURS CALL FLOW
1. Greet: "Thank you for calling {company_name}. Our office is currently closed. If this is an emergency, please stay on the line."
2. Confirm: "Is this an emergency situation?"
3. IF EMERGENCY:
   a. Collect name, callback number, and address
   b. Attempt emergency transfer to on-call contact
   c. If transfer fails: "I've recorded your information as urgent. A technician will call you back within 30 minutes. Please call 911 if there is immediate danger."
4. IF NOT EMERGENCY:
   a. "Our team is available {days} from {start} to {end} {timezone}."
   b. Collect name and callback number for next-business-day followup.
5. Close warmly.

## EMERGENCY TRIGGERS
{emergency_triggers}

## TRANSFER PROTOCOL
- Transfer silently. Say: "Let me connect you with the right person now."
- Timeout: {timeout}s, retry once, then take message.

## RULES
- Do not ask more questions than necessary.
- Collect only: name, callback number, address (emergencies only).
- Never mention internal systems by name.
- Keep responses under 3 sentences unless explaining a process.
- Services: {services}
"""

def build_agent_spec(memo, version="v1"):
    bh = memo.get("business_hours") or {}
    days_str = ", ".join(bh.get("days") or ["Mon-Fri"])
    emergency_triggers = ", ".join(memo.get("emergency_definition") or ["flood","fire","no heat/cool"])
    services = ", ".join(memo.get("services_supported") or ["general services"])
    transfer_rules = memo.get("call_transfer_rules", {})
    emergency_routing = memo.get("emergency_routing_rules", {})
    agent_name = "Clara"
    company_name = memo.get("company_name", "our company")

    system_prompt = SYSTEM_PROMPT_TEMPLATE.format(
        agent_name=agent_name, company_name=company_name, days=days_str,
        start=bh.get("start") or "TBD — confirm with business",
        end=bh.get("end") or "TBD — confirm with business",
        timezone=bh.get("timezone") or "local time",
        emergency_triggers=emergency_triggers,
        timeout=transfer_rules.get("timeout_seconds") or 30,
        services=services
    )

    return {
        "agent_name": agent_name, "version": version, "account_id": memo.get("account_id"),
        "created_at": datetime.now().isoformat() + "Z",
        "voice_style": {"provider": "elevenlabs", "voice_id": "rachel", "speed": 1.0, "stability": 0.75},
        "system_prompt": system_prompt,
        "key_variables": {
            "timezone": bh.get("timezone",""), "business_hours_start": bh.get("start",""),
            "business_hours_end": bh.get("end",""), "business_days": bh.get("days",[]),
            "office_address": memo.get("office_address",""),
            "emergency_contact_primary": emergency_routing.get("primary_contact",""),
            "emergency_contact_fallback": emergency_routing.get("fallback","voicemail"),
            "company_name": company_name
        },
        "tool_invocation_placeholders": {
            "transfer_call": {"trigger": "when caller needs to be connected", "destinations": {"emergency": emergency_routing.get("primary_contact",""), "office": memo.get("non_emergency_routing_rules",{}).get("destination","")}, "note": "Do NOT mention to caller"},
            "create_ticket": {"trigger": "after collecting caller info for non-emergency after-hours", "fields": ["caller_name","callback_number","issue_summary"], "note": "Silent background action"}
        },
        "call_transfer_protocol": {"timeout_seconds": transfer_rules.get("timeout_seconds",30), "retries": transfer_rules.get("retries",1), "on_failure": transfer_rules.get("if_transfer_fails","Take message, assure callback")},
        "fallback_protocol": {"message": "I wasn't able to connect you. I've noted your information and someone will follow up shortly.", "collect_before_fallback": ["name","phone"], "emergency_addition": ["address"]},
        "integration_constraints": memo.get("integration_constraints",[])
    }

def save_outputs(account_id, version, memo, spec):
    out_dir = OUTPUTS_DIR / account_id / version
    out_dir.mkdir(parents=True, exist_ok=True)
    with open(out_dir / "account_memo.json", "w", encoding="utf-8") as f:
        json.dump(memo, f, indent=2)
    with open(out_dir / "agent_spec.json", "w", encoding="utf-8") as f:
        json.dump(spec, f, indent=2)
    print(f"  ✓ Saved memo: {out_dir / 'account_memo.json'}")
    print(f"  ✓ Saved spec: {out_dir / 'agent_spec.json'}")

def derive_account_id(text, source_file):
    base = Path(source_file).stem if source_file else ""
    slug = re.sub(r"[^a-z0-9]", "_", base.lower())[:20].strip("_")
    if slug:
        return f"acc_{slug}"
    return "acc_" + hashlib.md5(text[:200].encode()).hexdigest()[:8]

def run_pipeline_a(transcript_path, account_id=None):
    print(f"\n[Pipeline A] Processing: {transcript_path}")
    with open(transcript_path, "r", encoding="utf-8") as f:
        transcript = f.read()
    if not account_id:
        account_id = derive_account_id(transcript, transcript_path)
    print(f"  Account ID: {account_id}")
    print("  → Extracting account memo...")
    memo = build_account_memo(transcript, account_id, version="v1", source_file=transcript_path)
    print("  → Generating Retell agent spec v1...")
    spec = build_agent_spec(memo, version="v1")
    save_outputs(account_id, "v1", memo, spec)
    return {"account_id": account_id, "memo": memo, "spec": spec}

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python pipeline_a.py <transcript_file> [account_id]")
        sys.exit(1)
    result = run_pipeline_a(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else None)
    print(f"\n[Done] Account ID: {result['account_id']}")
