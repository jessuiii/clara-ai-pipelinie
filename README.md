# Clara AI — Automation Pipeline

**Demo Call → Retell Agent Draft → Onboarding Updates → Agent Revision**

Zero-cost, locally-runnable pipeline that processes call transcripts and generates versioned Retell AI agent configurations.

---

## 🏗️ Architecture Stack

The pipeline is designed to transform unstructured call transcripts into structured JSON specifications for AI voice agents (like Retell AI), automatically applying updates as the client goes through onboarding.

```text
demo_transcript.txt
        │
        ▼
  [ Pipeline A ]
  ├── Extract account memo (LLM via Groq API, or rule-based fallback)
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
  ├── Merge v1 → v2 (deep patch structure)
  ├── Generate diff + changelog
  ├── Generate Retell Agent Spec v2
  └── outputs/accounts/<id>/v2/
             account_memo.json
             agent_spec.json
  changelog/
    <id>_changelog.json
    <id>_changes.md
```

### LLM Extraction Strategy (Zero-Cost):
- If `GROQ_API_KEY` is set: The pipeline uses the highly capable `moonshotai/kimi-k2-instruct` model via Groq's high-speed, completely free API tier.
- If no API key is provided: The pipeline automatically falls back to local Regex rule-based extraction (completely offline, zero dependencies).
- **Both paths produce identical output schemas.**

---

## ⚡ Quick Start

### 1. Prerequisites
No heavy packages needed. The pipeline uses standard built-in Python libraries (`urllib`, `json`, `re`).
```bash
python3 --version   # 3.9+ recommended
```

### 2. Setup
```bash
git clone https://github.com/jessuiii/clara-ai-pipelinie.git
cd clara-ai-pipeline
```

### 3. Provide Groq API Key (Highly Recommended)
Using Groq enables intelligent LLM extraction parsing instead of static regex fallbacks.
```bash
export GROQ_API_KEY=gsk_...   # Get a free API key at console.groq.com
```

### 4. Run Pipeline A (Demo Call → v1 Agent)
Processes a demo transcript and generates the initial `v1` configuration for an account.
```bash
python scripts/pipeline_a.py sample_transcripts/demo_1.txt acc_1
```
Creates: `outputs/accounts/acc_1/v1/account_memo.json` and `agent_spec.json`

### 5. Run Pipeline B (Onboarding Call → v2 Agent)
Processes an onboarding transcript to extract updates, merge them with `v1`, and produce a `v2` configuration + changelog.
```bash
python scripts/pipeline_b.py sample_transcripts/onboarding_1.txt acc_1
```
Creates: `outputs/accounts/acc_1/v2/account_memo.json`, `agent_spec.json`, and markdown changelogs in the `changelog/` directory.

### 6. Run the Full Batch
Process a whole folder of paired `demo_N` and `onboarding_N` transcripts automatically:
```bash
python scripts/run_batch.py --dataset-dir ./sample_transcripts
```

---

## 📊 Dashboard Visualizer

A static HTML dashboard is included to review all generated accounts, see version comparisons, and explore prompt outputs! No server is required.

**How to open:**
Simply open the `docs/dashboard.html` file in your web browser.
- View generated system prompts.
- See a visual diff tracker showing the exact fields changed between `v1` and `v2`.
- View the active configurations (Hours, Routing, Services, etc.).

---

## ⚙️ n8n Workflow (Docker Setup)

This pipeline includes an n8n workflow for deploying this as a local web service.

### Start n8n container
```bash
cp .env.example .env
# Edit .env to add your GROQ_API_KEY

docker-compose up -d
```
1. Access n8n at `http://localhost:5678` (credentials: admin / claraai123)
2. Go to **Workflows → Import**, and upload the `workflows/clara_pipeline_n8n.json` file.
3. Activate the workflow!

### Trigger Endpoints:
```bash
curl -X POST http://localhost:5678/webhook/batch
```

---

## 📂 File Output Schemas

### `account_memo.json`
Stores the semantic state of the company's rules.
```json
{
  "account_id": "acc_1",
  "version": "v1",
  "created_at": "2026-03-03T12:23:03.626800Z",
  "source_file": "sample_transcripts/demo_1.txt",
  "company_name": "AcmePlumbing",
  "business_hours": { "days": ["Mon","Fri","Sat"], "start": "7am", "end": "6pm", "timezone": "Central" },
  "office_address": "1452 Industrial Blvd,",
  "services_supported": ["Cleaning", "Plumbing"],
  "emergency_definition": ["Flood", "Burst Pipe"],
  "emergency_routing_rules": { "primary": "...", "fallback": "...", "secondary": "..." },
  "non_emergency_routing_rules": { "action": "take message", "destination": "..." },
  "call_transfer_rules": { "timeout_seconds": 30, "retries": 1, "if_transfer_fails": "..." },
  "integration_constraints": [],
  "after_hours_flow_summary": "...",
  "office_hours_flow_summary": "...",
  "questions_or_unknowns": [],
  "notes": "..."
}
```

### `agent_spec.json`
The output schema designed for the AI voice agent configurations.
```json
{
  "agent_name": "Clara",
  "version": "v1",
  "account_id": "acc_1",
  "created_at": "2026-03-03T15:20:10.00Z",
  "voice_style": { "provider": "elevenlabs", "voice_id": "rachel", "speed": 1.0, "stability": 0.75 },
  "system_prompt": "...(full generated prompt)...",
  "key_variables": { "timezone": "...", "business_hours_start": "...", "business_days": ["Mon"] },
  "tool_invocation_placeholders": { "transfer_call": {...}, "create_ticket": {...} },
  "call_transfer_protocol": { "timeout_seconds": 30, "retries": 1, "on_failure": "..." },
  "fallback_protocol": { "message": "...", "collect_before_fallback": ["name","phone"], "emergency_addition": ["address"] },
  "integration_constraints": [...]
}
```

### `changelog/acc_1_changes.md`
Human-readable markdown diff of configuration updates.
```markdown
# Changelog: acc_1

**Generated:** 2026-03-03T15:20:10.0Z
**Version:** v1 → v2
**Summary:** 5 field(s) updated during onboarding

## Changes

### `business_hours.days`
- **Before:** `['Mon', 'Fri', 'Sat']`
- **After:** `['Sat']`
- **Type:** list_updated
```

---

## 📌 Project Directory

```text
clara-ai-pipeline/
├── scripts/
│   ├── pipeline_a.py            # Demo transcript → v1 assets
│   ├── pipeline_b.py            # Onboarding → v2 assets + changelog
│   └── run_batch.py             # Batch runner utility
├── workflows/
│   └── clara_pipeline_n8n.json  # n8n webhook workflow
├── outputs/
│   ├── accounts/
│   │   └── <account_id>/
│   │       ├── v1/ ...
│   │       └── v2/ ...
│   └── batch_summary.json
├── changelog/                   # Markdown and JSON changelog diffs
├── sample_transcripts/          # Testing text files (.txt)
├── docs/
│   └── dashboard.html           # Project visualization UI
├── docker-compose.yml           # Container setup for n8n API
├── test_groq.py                 # Tiny script to test Groq API Auth
└── README.md
```

*Built for Clara AI — zero-cost, reproducible, end-to-end processing pipeline.*
