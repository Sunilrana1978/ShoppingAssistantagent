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

    print("\n==========================================================")
    print("🎉 DEPLOYMENT COMPLETED SUCCESSFULLY VIA NATIVE SCRAPI CLI!")
    print("==========================================================")

if __name__ == "__main__":
    main()
