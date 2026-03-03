# Clara AI — Automation Pipeline

**Demo Call → Preliminary Retell Agent → Onboarding Updates → Agent Revision**

Zero-cost, locally-runnable pipeline that converts unstructured call transcripts into structured, versioned Retell AI agent configurations — automatically.

---

## 🏗️ Architecture and Data Flow

```text
Stage 1: Demo Call Transcript
        │
        ▼
  ┌─────────────┐
  │ Pipeline A  │  (scripts/pipeline_a.py)
  ├─────────────┤
  │ 1. Ingest transcript → normalize → assign account_id
  │ 2. LLM extraction (Groq free API) OR rule-based fallback
  │ 3. Build Account Memo JSON (v1)
  │ 4. Generate Retell Agent Spec (v1)
  │ 5. Save to outputs/accounts/<id>/v1/
  │ 6. Create task tracker item → tasks/<id>.json
  └─────────────┘
        │
        ▼  (onboarding call happens)
        │
Stage 2: Onboarding Transcript
        │
        ▼
  ┌─────────────┐
  │ Pipeline B  │  (scripts/pipeline_b.py)
  ├─────────────┤
  │ 1. Load v1 memo
  │ 2. Extract updates from onboarding transcript
  │ 3. Deep-patch v1 → v2 (non-destructive merge)
  │ 4. Generate Account Memo JSON (v2)
  │ 5. Generate Retell Agent Spec (v2)
  │ 6. Produce changelog (JSON + Markdown)
  │ 7. Save to outputs/accounts/<id>/v2/ + changelog/
  └─────────────┘
        │
        ▼
  Dashboard: docs/dashboard.html (zero-server static UI)
```

### LLM Strategy (Zero-Cost)
| Mode | When | How |
|---|---|---|
| AI (Groq) | `GROQ_API_KEY` is set | `moonshotai/kimi-k2-instruct` via Groq free tier |
| Rule-based | No API key / API fails | Regex pattern library (offline, no dependencies) |

Both modes produce **identical JSON schemas**. The pipeline never crashes — it always falls back cleanly.

---

## ⚡ Quick Start

### Prerequisites
```bash
python3 --version   # 3.9+ required, no pip packages needed
```

### 1. Clone and setup
```bash
git clone https://github.com/jessuiii/clara-ai-pipelinie.git
cd clara-ai-pipeline
```

### 2. Set Groq API key (highly recommended)
```bash
# Get a free key at console.groq.com — no credit card required
export GROQ_API_KEY=gsk_...        # Mac/Linux
$env:GROQ_API_KEY="gsk_..."        # Windows PowerShell
```

### 3. Run Pipeline A — Demo → v1 Agent
```bash
python scripts/pipeline_a.py sample_transcripts/demo_bens_electric.txt bens_electric
```
**Creates:**
- `outputs/accounts/bens_electric/v1/account_memo.json`
- `outputs/accounts/bens_electric/v1/agent_spec.json`
- `tasks/bens_electric.json` ← task tracker item

### 4. Run Pipeline B — Onboarding → v2 Agent
```bash
python scripts/pipeline_b.py sample_transcripts/onboarding_bens_electric.txt bens_electric
```
**Creates:**
- `outputs/accounts/bens_electric/v2/account_memo.json`
- `outputs/accounts/bens_electric/v2/agent_spec.json`
- `changelog/bens_electric_changelog.json`
- `changelog/bens_electric_changes.md`

### 5. Run the full batch (all 5 demo + 5 onboarding pairs)
```bash
python scripts/run_batch.py
```

### 6. View the dashboard
Open `docs/dashboard.html` in any browser — no server required.

---

## 🐳 Docker Setup (n8n + Pipeline Runner)

```bash
cp .env.example .env   # Add GROQ_API_KEY inside

docker-compose up -d
```

| Service | URL | Credentials |
|---|---|---|
| n8n orchestrator | http://localhost:5678 | admin / claraai123 |
| pipeline-runner | — | CLI (see below) |

### Import n8n workflow
1. Open http://localhost:5678
2. **Workflows → Import** → upload `workflows/clara_pipeline_n8n.json`
3. Activate

### Run batch via Docker
```bash
# Full batch
docker-compose run --rm pipeline-runner

# Single account
docker-compose run --rm pipeline-runner python scripts/pipeline_a.py sample_transcripts/demo_bens_electric.txt bens_electric
```
Outputs are live-mounted — `outputs/`, `logs/`, `tasks/` appear on your host immediately.

### Trigger via webhook
```bash
curl -X POST http://localhost:5678/webhook/batch
```

---

## 📂 How to Plug In Your Dataset Files

Place your transcripts in `sample_transcripts/` following this naming convention:
```
sample_transcripts/
├── demo_<account_id>.txt          # Pipeline A input
└── onboarding_<account_id>.txt    # Pipeline B input
```
Then run:
```bash
python scripts/run_batch.py --dataset-dir ./sample_transcripts
```
The batch runner auto-pairs `demo_X` with `onboarding_X` by filename.

If you have audio instead of transcripts, use [Whisper locally](https://github.com/openai/whisper):
```bash
pip install openai-whisper
whisper recording.mp3 --output_format txt
```

---

## 📤 Output Schemas

### `account_memo.json`
```json
{
  "account_id": "bens_electric",
  "version": "v1",
  "created_at": "2026-03-03T21:37:30Z",
  "source_file": "sample_transcripts/demo_bens_electric.txt",
  "company_name": "Ben's Electrical Solutions",
  "business_hours": { "days": ["Mon","Tue","Wed","Thu","Fri"], "start": null, "end": null, "timezone": null },
  "office_address": null,
  "services_supported": ["service calls", "EV chargers", "panel changes"],
  "emergency_definition": ["emergency calls from property managers"],
  "emergency_routing_rules": { "primary_contact": "Ben", "secondary_contact": null, "fallback": "defer to another service" },
  "non_emergency_routing_rules": { "action": null, "destination": null },
  "call_transfer_rules": { "timeout_seconds": null, "retries": null, "if_transfer_fails": null },
  "integration_constraints": ["don't use virtual receptionists"],
  "after_hours_flow_summary": "Ben is on call and may answer or defer",
  "office_hours_flow_summary": "Ben manages operations and answers calls",
  "questions_or_unknowns": ["What is the exact business hours and timezone?", "What is the office address?"],
  "notes": "Ben has 30 years experience. Uses Jobber as CRM."
}
```

### `agent_spec.json`
```json
{
  "agent_name": "Clara",
  "version": "v1",
  "account_id": "bens_electric",
  "voice_style": { "provider": "elevenlabs", "voice_id": "rachel", "speed": 1.0, "stability": 0.75 },
  "system_prompt": "...(full Clara voice agent prompt)...",
  "key_variables": { "timezone": null, "business_hours_start": null, "business_days": ["Mon","Tue","Wed","Thu","Fri"] },
  "tool_invocation_placeholders": { "transfer_call": {...}, "create_ticket": {...} },
  "call_transfer_protocol": { "timeout_seconds": 30, "retries": 1, "on_failure": "Take message, assure callback" },
  "fallback_protocol": { "message": "I wasn't able to connect you. I've noted your info and someone will follow up shortly.", "collect_before_fallback": ["name","phone"], "emergency_addition": ["address"] },
  "integration_constraints": ["don't use virtual receptionists"]
}
```

### `tasks/<account_id>.json` (Task Tracker)
```json
{
  "task_id": "CLARA-BENS_ELECTRIC",
  "account_id": "bens_electric",
  "company_name": "Ben's Electrical Solutions",
  "status": "pending_onboarding",
  "created_at": "2026-03-03T21:37:30Z",
  "agent_version": "v1",
  "open_questions": ["What is the exact business hours?", "What is the office address?"],
  "next_steps": ["Schedule onboarding call", "Confirm emergency routing contacts"]
}
```

### `changelog/bens_electric_changes.md`
```markdown
# Changelog: bens_electric
**Version:** v1 → v2  |  **Changes:** 8 field(s) updated

## Changes
### `business_hours.start`
- **Before:** null
- **After:** "8:00"
- **Type:** added
```

---

## 📌 Project Directory

```text
clara-ai-pipeline/
├── scripts/
│   ├── pipeline_a.py            # Demo transcript → v1 assets + task tracker
│   ├── pipeline_b.py            # Onboarding → v2 assets + changelog
│   └── run_batch.py             # Batch runner (all pairs)
├── workflows/
│   └── clara_pipeline_n8n.json  # n8n webhook workflow export
├── outputs/
│   └── accounts/
│       └── <account_id>/
│           ├── v1/
│           │   ├── account_memo.json
│           │   └── agent_spec.json
│           └── v2/
│               ├── account_memo.json
│               └── agent_spec.json
├── tasks/
│   └── <account_id>.json        # Task tracker item (pending_onboarding status)
├── logs/
│   └── <account_id>.log         # Timestamped per-account run log
├── changelog/
│   ├── <account_id>_changelog.json
│   └── <account_id>_changes.md
├── sample_transcripts/          # Input transcripts (.txt)
├── docs/
│   └── dashboard.html           # Static diff viewer + prompt viewer UI
├── docker-compose.yml           # n8n + pipeline-runner services
├── Dockerfile                   # Pipeline runner image
├── requirements.txt             # No external dependencies (stdlib only)
└── README.md
```

---

## 🔧 Retell Setup

Retell's free tier does **not** expose programmatic agent creation via API. This pipeline handles that as follows:

**What the pipeline does:** Generates a complete `agent_spec.json` per account that exactly mirrors Retell's agent configuration schema.

**Manual import steps:**
1. Log into [app.retellai.com](https://app.retellai.com)
2. Create → New Agent
3. Copy `system_prompt` from `agent_spec.json` into the agent's system prompt field
4. Set voice to `rachel` (ElevenLabs) at speed `1.0`, stability `0.75`
5. Configure transfer destinations from `emergency_routing_rules.primary_contact`
6. Set transfer timeout from `call_transfer_protocol.timeout_seconds`

**In production:** With a paid Retell plan, replace the `save_outputs()` step with a `POST /v2/create-agent` API call using the spec as payload.

---

## ⚠️ Known Limitations

| Limitation | Impact | Workaround |
|---|---|---|
| Groq free tier has rate limits | Batches > 10 calls may hit 429 | Rule-based fallback kicks in automatically |
| n8n webhook is local only | Cannot receive external webhooks | Use ngrok for public endpoint |
| Task tracker is local JSON | Not a real Asana/Linear integration | Drop-in replacement: add API call in `create_task_tracker_item()` |
| Transcript-only (no STT) | Audio files need pre-processing | Run Whisper locally first |
| Dashboard shows embedded data | Doesn't auto-reload after new runs | Refresh browser after running batch |

---

## 🚀 What I'd Improve With Production Access

1. **Real Retell API calls** — replace manual import with `POST /v2/create-agent` on paid plan
2. **Asana/Linear task creation** — swap `create_task_tracker_item()` for a real API call (structure already matches)
3. **Supabase storage** — replace local JSON files with Postgres-backed versioned records
4. **Retell webhook listener** — receive live call transcripts instead of file uploads
5. **Whisper transcription node** — add an n8n audio-to-text step for direct recording ingestion
6. **Conflict resolution UI** — flag and surface merge conflicts for human review before committing v2
7. **Multi-account dashboard** — real-time dashboard backed by Supabase queries

---

*Built for Clara AI — zero-cost, reproducible, end-to-end voice agent configuration pipeline.*
