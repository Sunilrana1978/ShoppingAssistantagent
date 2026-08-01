#!/usr/bin/env python3
"""
Build & Deployment Automation Script for Sporting Goods Multi-Agent Application.
Pre-flight testing runner + native SCRAPI CLI deployment (`cxas push`).

Supports environments: dev, staging, prod.
"""

import sys
import os
import argparse
import subprocess
from pathlib import Path

def clean_pycache():
    """Removes __pycache__ directories to ensure clean execution."""
    root = Path(__file__).parent.parent
    for p in root.rglob('__pycache__'):
        try:
            import shutil
            shutil.rmtree(p)
        except Exception:
            pass

def reconcile_agent_toolsets(target_app_path: str) -> None:
    """
    Workaround for a cxas-scrapi push limitation: `cxas push` creates/updates
    Toolset resources (e.g. OpenAPI toolsets under toolsets/<name>/) correctly,
    but silently drops the agent-level `toolsets` binding declared in
    agents/*/*.json. Re-applies those bindings directly via the Agent Service
    API after every push so toolset-backed tools (like fetch_user_profile)
    stay attached to their agent in CX Agent Studio.
    """
    import json as _json
    from cxas_scrapi.core.tools import Tools
    from google.cloud.ces_v1beta import types
    from google.protobuf import field_mask_pb2

    tools_client = Tools(app_name=target_app_path)
    toolset_resource_by_display_name = {
        tool.display_name: tool.name
        for tool in tools_client.list_tools()
        if "/toolsets/" in tool.name
    }
    if not toolset_resource_by_display_name:
        return

    agents_dir = Path(__file__).parent.parent / "agents"
    for agent_json in sorted(agents_dir.glob("*/*.json")):
        config = _json.loads(agent_json.read_text())
        declared = config.get("toolsets")
        if not declared:
            continue

        agent_toolsets = []
        for entry in declared:
            resource_name = toolset_resource_by_display_name.get(entry["toolset"])
            if not resource_name:
                print(f"⚠️ Could not resolve toolset '{entry['toolset']}' for agent '{config['name']}' — skipping.")
                continue
            agent_toolsets.append(types.Agent.AgentToolset(
                toolset=resource_name,
                tool_ids=entry.get("toolIds", []),
            ))

        if not agent_toolsets:
            continue

        agent = types.Agent(
            name=f"{target_app_path}/agents/{config['name']}",
            toolsets=agent_toolsets,
        )
        request = types.UpdateAgentRequest(
            agent=agent,
            update_mask=field_mask_pb2.FieldMask(paths=["toolsets"]),
        )
        tools_client.client.update_agent(request=request)
        print(f"✅ Reconciled toolsets binding for agent '{config['name']}'.")

def main():
    parser = argparse.ArgumentParser(description="Build and deploy Sporting Goods Multi-Agent App")
    parser.add_argument("--env", choices=["dev", "staging", "prod"], default="dev", help="Target environment")
    parser.add_argument("--project", default="ecom-cx-agent", help="GCP Project ID")
    parser.add_argument("--location", default="us", help="GCP Region/Location")
    parser.add_argument("--app-id", default=None, help="CX Agent Studio App ID")
    parser.add_argument("--skip-tests", action="store_true", help="Skip pre-flight unit testing")
    args = parser.parse_args()

    app_id = args.app_id
    if not app_id:
        config_path = Path(__file__).parent.parent / "gecx-config.toml"
        if config_path.exists():
            try:
                try:
                    import tomllib
                except ImportError:
                    import tomli as tomllib
                with open(config_path, "rb") as f:
                    cfg = tomllib.load(f)
                app_id = cfg.get("profiles", {}).get(args.env, {}).get("app_id")
            except Exception:
                pass
        if not app_id:
            app_id = f"shopping-assistant-app-{args.env}" if args.env != "prod" else "shopping-assistant-app"

    print(f"==========================================================")
    print(f"🚀 DEPLOYING SPORTING GOODS MULTI-AGENT APP [{args.env.upper()}]")
    print(f"==========================================================")
    print(f"📍 Project: {args.project} | Location: {args.location} | App ID: {app_id}")

    target_app_path = f"projects/{args.project}/locations/{args.location}/apps/{app_id}"

    # 1. Clean pycache
    clean_pycache()
    print("✅ Pycache cleaned.")

    # 2. Pre-flight Quality Gates (Unit Tests & Schema Validation)
    if not args.skip_tests:
        print("\n🧪 Running Pre-Flight Service & Callback Test Suite...")
        try:
            subprocess.run([sys.executable, "-m", "unittest", "discover", "tests/"], check=True)
            print("✅ Unit tests passed.")
        except subprocess.CalledProcessError:
            print("❌ Unit tests failed! Aborting deployment.")
            sys.exit(1)

        print("\n🔍 Validating Manifests & Data Schemas...")
        try:
            subprocess.run([sys.executable, "scripts/validate_schemas.py"], check=True)
            print("✅ Schema validation passed.")
        except subprocess.CalledProcessError:
            print("❌ Schema validation failed! Aborting deployment.")
            sys.exit(1)
    else:
        print("\n⚠️ Skipping pre-flight tests as requested (--skip-tests).")

    # 3. Synchronize via native SCRAPI CLI `cxas push`
    print(f"\n☁️ Pushing resources natively via SCRAPI CLI to {target_app_path}...")
    cxas_bin = Path(sys.executable).parent / "cxas"
    push_bin = str(cxas_bin) if cxas_bin.exists() else "cxas"
    push_cmd = [push_bin, "push", "--to", target_app_path]
    try:
        subprocess.run(push_cmd, check=True)
    except subprocess.CalledProcessError as e:
        print(f"❌ SCRAPI CLI push failed with exit code {e.returncode}!")
        sys.exit(e.returncode)

    # 4. Reconcile agent-level toolset bindings (cxas push workaround)
    print("\n🔧 Reconciling agent toolset bindings...")
    try:
        reconcile_agent_toolsets(target_app_path)
    except Exception as e:
        print(f"⚠️ Toolset reconciliation failed: {e}")
        print("   Toolset-backed tools may not appear attached to their agent in Studio.")

    print("\n==========================================================")
    print("🎉 DEPLOYMENT COMPLETED SUCCESSFULLY VIA NATIVE SCRAPI CLI!")
    print("==========================================================")

if __name__ == "__main__":
    main()
