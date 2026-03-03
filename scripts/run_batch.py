#!/usr/bin/env python3
"""
Batch runner: Process all demo + onboarding transcripts end-to-end.
Usage: python run_batch.py [--dataset-dir ./sample_transcripts]
"""

import json
import os
import sys
import time
import argparse
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent))
from pipeline_a import run_pipeline_a, derive_account_id
from pipeline_b import run_pipeline_b

OUTPUTS_DIR = Path(__file__).parent.parent / "outputs"
SUMMARY_PATH = OUTPUTS_DIR / "batch_summary.json"

def find_pairs(dataset_dir: Path) -> list:
    """Find demo+onboarding pairs. Naming convention:
       demo_<name>.txt  /  demo_<name>.md
       onboarding_<name>.txt  /  onboarding_<name>.md
    """
    pairs = {}
    for f in sorted(dataset_dir.glob("**/*")):
        if not f.is_file() or f.suffix not in (".txt", ".md", ".json"):
            continue
        name = f.stem.lower()
        if name.startswith("demo_"):
            key = name[5:]
            pairs.setdefault(key, {})["demo"] = f
        elif name.startswith("onboarding_"):
            key = name[11:]
            pairs.setdefault(key, {})["onboarding"] = f
        elif "demo" in name:
            pairs.setdefault(name, {})["demo"] = f
        elif "onboard" in name:
            pairs.setdefault(name, {})["onboarding"] = f

    return [(k, v) for k, v in pairs.items() if "demo" in v]

def run_batch(dataset_dir: str = None, demo_files: list = None, onboarding_files: list = None):
    """Run full batch. Accepts either a directory or explicit file lists."""
    start_time = datetime.utcnow()
    results = []
    errors = []

    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)

    if dataset_dir:
        ds_path = Path(dataset_dir)
        pairs = find_pairs(ds_path)
        print(f"\n{'='*60}")
        print(f"  Clara AI Pipeline — Batch Run")
        print(f"  Dataset: {ds_path}")
        print(f"  Found {len(pairs)} account(s)")
        print(f"{'='*60}")

        for name, files in pairs:
            demo_file = str(files["demo"])
            onboarding_file = str(files.get("onboarding", ""))

            # Derive account_id from filename
            account_id = f"acc_{name}"

            # Pipeline A
            try:
                a_result = run_pipeline_a(demo_file, account_id)
                results.append({"account_id": account_id, "pipeline_a": "success"})
            except Exception as e:
                print(f"  [ERROR] Pipeline A failed for {account_id}: {e}")
                errors.append({"account_id": account_id, "pipeline": "A", "error": str(e)})
                continue

            # Pipeline B (if onboarding exists)
            if onboarding_file and Path(onboarding_file).exists():
                try:
                    time.sleep(0.5)  # Rate limit buffer
                    b_result = run_pipeline_b(onboarding_file, account_id)
                    results[-1]["pipeline_b"] = "success"
                    results[-1]["changes"] = b_result.get("changes", 0)
                except Exception as e:
                    print(f"  [ERROR] Pipeline B failed for {account_id}: {e}")
                    errors.append({"account_id": account_id, "pipeline": "B", "error": str(e)})
            else:
                print(f"  [SKIP] No onboarding file for {account_id}")
                results[-1]["pipeline_b"] = "skipped"

    elif demo_files and onboarding_files:
        # Explicit file lists mode
        if len(demo_files) != len(onboarding_files):
            print("[WARN] Unequal number of demo and onboarding files")

        for i, demo_file in enumerate(demo_files):
            account_id = derive_account_id(open(demo_file).read(), demo_file)
            try:
                run_pipeline_a(demo_file, account_id)
                results.append({"account_id": account_id, "pipeline_a": "success"})
            except Exception as e:
                errors.append({"account_id": account_id, "pipeline": "A", "error": str(e)})
                continue

            if i < len(onboarding_files):
                try:
                    run_pipeline_b(onboarding_files[i], account_id)
                    results[-1]["pipeline_b"] = "success"
                except Exception as e:
                    errors.append({"account_id": account_id, "pipeline": "B", "error": str(e)})

    # Summary
    end_time = datetime.utcnow()
    duration = (end_time - start_time).total_seconds()

    summary = {
        "run_at": start_time.isoformat() + "Z",
        "duration_seconds": round(duration, 2),
        "total_accounts": len(results),
        "successful": len([r for r in results if r.get("pipeline_a") == "success"]),
        "errors": len(errors),
        "results": results,
        "errors_detail": errors
    }

    with open(SUMMARY_PATH, "w") as f:
        json.dump(summary, f, indent=2)

    print(f"\n{'='*60}")
    print(f"  Batch Complete in {duration:.1f}s")
    print(f"  Accounts processed: {summary['successful']}/{summary['total_accounts']}")
    print(f"  Errors: {summary['errors']}")
    print(f"  Summary saved: {SUMMARY_PATH}")
    print(f"{'='*60}\n")

    if errors:
        print("Errors:")
        for e in errors:
            print(f"  {e['account_id']} ({e['pipeline']}): {e['error']}")

    return summary

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Clara AI Pipeline Batch Runner")
    parser.add_argument("--dataset-dir", default="./sample_transcripts",
                        help="Directory containing demo_*.txt and onboarding_*.txt files")
    parser.add_argument("--demo-files", nargs="+", help="Explicit list of demo transcript files")
    parser.add_argument("--onboarding-files", nargs="+", help="Explicit list of onboarding transcript files")
    args = parser.parse_args()

    if args.demo_files:
        run_batch(demo_files=args.demo_files, onboarding_files=args.onboarding_files or [])
    else:
        run_batch(dataset_dir=args.dataset_dir)
