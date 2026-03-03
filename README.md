# Clara AI — Automation Pipeline

**Demo Call → Retell Agent Draft → Onboarding Updates → Agent Revision**

Zero-cost, locally-runnable pipeline that processes call transcripts and generates versioned Retell AI agent configurations.

---

## Architecture

```
demo_transcript.txt
        │
        ▼
  [ Pipeline A ]
  ├── Extract account memo (LLM or rule-based)
  ├── Generate Retell Agent Spec v1
  └── outputs/accounts/<id>/v1/
             account_memo.json
             agent_spec.json
        │
        ▼
onboarding_transcript.txt
        │
        ▼
  [ Pipeline B ]
  ├── Extract updates from onboarding
  ├── Merge v1 → v2 (deep patch)
  ├── Generate diff + changelog
  ├── Generate Retell Agent Spec v2
  └── outputs/accounts/<id>/v2/
             account_memo.json
             agent_spec.json
  changelog/
    <id>_changelog.json
    <id>_changes.md
```

**LLM Strategy (Zero-Cost):**
- If `ANTHROPIC_API_KEY` is set: uses `claude-haiku-4-5` (cheapest model, ~$0.001/call, or use free credits)
- If no API key: falls back to rule-based regex extraction automatically
- Both paths produce identical output schemas

---

## Quick Start

### 1. Prerequisites

```bash
python3 --version   # 3.9+
pip install anthropic  # optional — only for LLM extraction
```

### 2. Clone and set up

```bash
git clone <your-repo-url>
cd clara-ai-pipeline
```

### 3. (Optional) Set API key for LLM extraction

```bash
export ANTHROPIC_API_KEY=sk-ant-...   # free tier works
```

Without this, rule-based extraction runs automatically. No cost either way.

### 4. Run Pipeline A (demo call → v1 agent)

```bash
python scripts/pipeline_a.py sample_transcripts/demo_1.txt acc_1
```

**Output:**
```
outputs/accounts/acc_1/v1/account_memo.json
outputs/accounts/acc_1/v1/agent_spec.json
```

### 5. Run Pipeline B (onboarding → v2 agent)

```bash
python scripts/pipeline_b.py sample_transcripts/onboarding_1.txt acc_1
```

**Output:**
```
outputs/accounts/acc_1/v2/account_memo.json
outputs/accounts/acc_1/v2/agent_spec.json
changelog/acc_1_changelog.json
changelog/acc_1_changes.md
```

### 6. Run Full Batch (all 10 files)

```bash
python scripts/run_batch.py --dataset-dir ./sample_transcripts
```

This auto-pairs `demo_N.txt` with `onboarding_N.txt` files and runs both pipelines.

---

## Plug In Your Dataset

Naming convention for auto-pairing:
```
sample_transcripts/
  demo_acmeplumbing.txt        → account: acc_acmeplumbing
  onboarding_acmeplumbing.txt  → matches above
  demo_arctic_hvac.txt
  onboarding_arctic_hvac.txt
  ...
```

Or use explicit file args:
```bash
python scripts/run_batch.py \
  --demo-files demo1.txt demo2.txt ... \
  --onboarding-files onboard1.txt onboard2.txt ...
```

---

## n8n Workflow (Self-Hosted, Free)

### Start n8n with Docker

```bash
cp .env.example .env
# Edit .env and add ANTHROPIC_API_KEY if desired

docker-compose up -d
```

n8n runs at http://localhost:5678 (login: admin / claraai123)

### Import workflow

1. Open n8n at http://localhost:5678
2. Click **Workflows → Import**
3. Select `workflows/clara_pipeline_n8n.json`
4. Activate the workflow

### Trigger via webhook

**Run Pipeline A:**
```bash
curl -X POST http://localhost:5678/webhook/pipeline-a \
  -H "Content-Type: application/json" \
  -d '{"transcript_path": "/data/clara-pipeline/sample_transcripts/demo_1.txt", "account_id": "acc_1"}'
```

**Run Pipeline B:**
```bash
curl -X POST http://localhost:5678/webhook/pipeline-b \
  -H "Content-Type: application/json" \
  -d '{"transcript_path": "/data/clara-pipeline/sample_transcripts/onboarding_1.txt", "account_id": "acc_1"}'
```

**Run Full Batch:**
```bash
curl -X POST http://localhost:5678/webhook/batch
```

---

## Output File Reference

### `account_memo.json`
```json
{
  "account_id": "acc_1",
  "version": "v1",
  "company_name": "AcmePlumbing Inc.",
  "business_hours": { "days": ["Mon","Fri"], "start": "7:00am", "end": "6:00pm", "timezone": "Central" },
  "office_address": "1452 Industrial Blvd, Houston TX 77002",
  "services_supported": ["Plumbing", "Drain Cleaning"],
  "emergency_definition": ["Burst Pipe", "Flooding"],
  "emergency_routing_rules": { "primary_contact": "...", "fallback": "..." },
  "non_emergency_routing_rules": { "action": "take message", "destination": "..." },
  "call_transfer_rules": { "timeout_seconds": 30, "retries": 1, "if_transfer_fails": "..." },
  "integration_constraints": ["Never create jobs in ServiceTrade"],
  "after_hours_flow_summary": "...",
  "office_hours_flow_summary": "...",
  "questions_or_unknowns": [],
  "notes": "..."
}
```

### `agent_spec.json`
```json
{
  "agent_name": "Clara",
  "version": "v1",
  "voice_style": { "provider": "elevenlabs", "voice_id": "rachel" },
  "system_prompt": "...(full generated prompt)...",
  "key_variables": { "timezone": "...", "business_hours_start": "...", ... },
  "tool_invocation_placeholders": { "transfer_call": {...}, "create_ticket": {...} },
  "call_transfer_protocol": { "timeout_seconds": 30, "retries": 1, "on_failure": "..." },
  "fallback_protocol": { "message": "...", "collect_before_fallback": ["name","phone"] },
  "integration_constraints": [...]
}
```

### `changelog/acc_1_changes.md`
```markdown
# Changelog: acc_1

**Generated:** 2025-02-01T...
**Version:** v1 → v2
**Summary:** 3 field(s) updated during onboarding

## Changes

### `business_hours.days`
- **Before:** `["Mon","Tue","Wed","Thu","Fri"]`
- **After:** `["Mon","Tue","Wed","Thu","Fri","Sat"]`
- **Type:** list_updated
```

---

## Retell Setup (Manual Import)

If Retell's free tier doesn't allow programmatic agent creation:

1. Create account at https://retell.ai
2. Go to **Agents → Create Agent**
3. Open `outputs/accounts/<id>/v2/agent_spec.json`
4. Copy `system_prompt` into the agent's System Prompt field
5. Configure:
   - Voice: ElevenLabs Rachel (or closest available)
   - Transfer number: from `key_variables.emergency_contact_primary`
   - Timezone: from `key_variables.timezone`
6. Save and test

---

## Dashboard

Open `docs/dashboard.html` in any browser — no server needed. Shows:
- All accounts with v1/v2 status
- Service tags, routing, hours
- v1 → v2 diff viewer
- Generated system prompts
- Raw JSON viewer

---

## File Structure

```
clara-ai-pipeline/
├── scripts/
│   ├── pipeline_a.py          # Demo transcript → v1 assets
│   ├── pipeline_b.py          # Onboarding → v2 assets + changelog
│   └── run_batch.py           # Batch runner for all files
├── workflows/
│   └── clara_pipeline_n8n.json  # n8n workflow export
├── outputs/
│   ├── accounts/
│   │   └── <account_id>/
│   │       ├── v1/
│   │       │   ├── account_memo.json
│   │       │   └── agent_spec.json
│   │       └── v2/
│   │           ├── account_memo.json
│   │           └── agent_spec.json
│   └── batch_summary.json
├── changelog/
│   ├── <id>_changelog.json
│   └── <id>_changes.md
├── sample_transcripts/
│   ├── demo_1.txt ... demo_5.txt
│   └── onboarding_1.txt ... onboarding_5.txt
├── docs/
│   └── dashboard.html         # Visual dashboard (open in browser)
├── docker-compose.yml         # n8n self-hosted setup
└── README.md
```

---

## Known Limitations

- **LLM extraction without API key**: Rule-based fallback is reliable for structured transcripts but may miss nuanced context or unusual phrasing. With `ANTHROPIC_API_KEY`, extraction quality improves significantly.
- **Audio transcription**: Not included. Accepts `.txt` / `.md` transcript files. For audio, run Whisper locally (`pip install openai-whisper`) and pipe output as a transcript file.
- **Retell API**: Free tier may not support programmatic agent creation. The `agent_spec.json` is designed for manual paste or Retell API v2 once available.
- **Idempotency**: Running twice overwrites outputs — no duplicate creation. Safe to re-run.

## What Would Improve With Production Access

- **Retell API integration**: Directly create/update agents via API instead of manual import.
- **Whisper transcription node**: Auto-transcribe audio uploads in the n8n workflow.
- **Webhook for task tracking**: Auto-create Asana/Linear tasks per account via API.
- **Supabase storage**: Replace local JSON files with Supabase for multi-user access and real-time sync.
- **Confidence scoring**: Flag low-confidence extractions for human review.
- **Prompt versioning**: Track prompt changes alongside config changes.

---

## Environment Variables

| Variable | Required | Description |
|---|---|---|
| `ANTHROPIC_API_KEY` | No | Enables LLM extraction (Haiku model, minimal cost) |

---

*Built for Clara AI intern assignment — zero-cost, reproducible, end-to-end.*
