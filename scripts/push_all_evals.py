#!/usr/bin/env python3
"""
Script to push all evaluations in evaluations/<name>/<name>.json to CXAS.
Handles both Golden and Scenario evaluations, converting old legacy Golden
evaluations on GCP into true Scenario evaluations.
"""

import sys
import glob
import json
from pathlib import Path

# Add workspace to sys.path
root = Path(__file__).parent.parent
sys.path.insert(0, str(root))

from cxas_scrapi.core.evaluations import Evaluations

def push_all_evaluations(app_name: str):
    print(f"🚀 Pushing all evaluations from evaluations/ to App: {app_name}")
    eval_client = Evaluations(app_name=app_name)
    
    # 1. Fetch existing evaluations on GCP
    try:
        existing = eval_client.list_evaluations(app_name=app_name)
    except Exception as e:
        print(f"⚠️ Could not list existing evaluations on GCP: {e}")
        existing = []

    eval_files = glob.glob("evaluations/*/*.json")
    
    for filepath in sorted(eval_files):
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                eval_dict = json.load(f)
        except Exception as err:
            print(f"❌ Failed to load {filepath}: {err}")
            continue
            
        display_name = eval_dict.get("displayName")
        is_scenario = "scenario" in eval_dict
        is_golden = "golden" in eval_dict
        
        # If replacing an existing evaluation of different type on GCP, delete old first
        for e in existing:
            if e.display_name == display_name:
                if is_scenario and e.golden:
                    print(f"🗑️ Deleting legacy Golden evaluation '{e.display_name}' ({e.name}) to convert to Scenario...")
                    try:
                        eval_client.delete_evaluation(e.name)
                        print(f"✅ Deleted legacy Golden evaluation '{e.display_name}'.")
                    except Exception as del_err:
                        print(f"⚠️ Failed to delete '{e.name}': {del_err}")

        try:
            res = eval_client.update_evaluation(eval_dict, app_name=app_name)
            kind = "Scenario" if is_scenario else "Golden"
            print(f"✅ Pushed {kind} evaluation: '{res.display_name}' ({res.name})")
        except Exception as push_err:
            print(f"❌ Failed to push '{display_name}' from {filepath}: {push_err}")

if __name__ == "__main__":
    app_target = "projects/ecom-cx-agent/locations/us/apps/shopping-assistant-app-dev"
    if len(sys.argv) > 1:
        app_target = sys.argv[1]
    push_all_evaluations(app_target)
