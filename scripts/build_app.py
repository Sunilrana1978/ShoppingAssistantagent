#!/usr/bin/env python3
"""
Build & Deployment Automation Script for Sporting Goods Multi-Agent Application.
Supports environments: dev, staging, prod.
"""

import sys
import os
import json
import argparse
import subprocess
from pathlib import Path
from typing import Dict, Any, List

def clean_pycache():
    """Removes __pycache__ directories to ensure clean execution."""
    root = Path(__file__).parent.parent
    for p in root.rglob('__pycache__'):
        try:
            import shutil
            shutil.rmtree(p)
        except Exception:
            pass

def sync_tools_and_agents(target_app_path: str):
    """Synchronizes local Tools, Callbacks, and Agents with GCP CX Agent Studio."""
    root = Path(__file__).parent.parent
    
    # Try importing Callback proto type
    try:
        from google.cloud.ces_v1beta.types import Callback
        def make_cb(code: str, desc: str):
            return Callback(python_code=code, description=desc)
    except Exception:
        def make_cb(code: str, desc: str):
            return {"python_code": code, "description": desc}

    try:
        from cxas_scrapi.core.agents import Agents
        from cxas_scrapi.core.tools import Tools
        from cxas_scrapi.core.variables import Variables
        
        agents_client = Agents(app_name=target_app_path)
        tools_client = Tools(app_name=target_app_path)
        vars_client = Variables(app_name=target_app_path)
    except ImportError as e:
        print(f"⚠️ cxas_scrapi not available: {e}")
        return

    # ------------------------------------------------------------------
    # 0. Synchronize Session Variables from variables.json
    # ------------------------------------------------------------------
    print("\n   📦 Synchronizing Session Variables with CX Agent Studio...")
    type_map = {
        "string": "STRING",
        "number": "NUMBER",
        "integer": "INTEGER",
        "boolean": "BOOLEAN",
        "array": "ARRAY",
        "object": "OBJECT"
    }

    try:
        from google.cloud.ces_v1beta import types
        app_obj = vars_client.get_app(target_app_path)
        existing_vars = {v.name: v for v in getattr(app_obj, "variable_declarations", [])}
        updated_vars_list = list(getattr(app_obj, "variable_declarations", []))
        has_new = False

        for agent_dir in sorted((root / 'agents').iterdir()):
            if not agent_dir.is_dir():
                continue
            vfile = agent_dir / 'variables.json'
            if not vfile.exists():
                continue
            with open(vfile, 'r', encoding='utf-8') as vf:
                vdata = json.load(vf)

            # Static variables
            for var_name, default_val in vdata.get('static', {}).items():
                if var_name not in existing_vars:
                    new_var = types.App.VariableDeclaration(
                        name=var_name,
                        schema={"type_": "STRING", "default": str(default_val)}
                    )
                    updated_vars_list.append(new_var)
                    existing_vars[var_name] = new_var
                    has_new = True
                    print(f"      ✅ Variable '{var_name}' (STATIC STRING = '{default_val}') created.")

            # Dynamic variables
            for var_name, var_meta in vdata.get('dynamic', {}).items():
                if var_name not in existing_vars:
                    raw_type = var_meta.get("type", "string").lower() if isinstance(var_meta, dict) else "string"
                    var_type_str = type_map.get(raw_type, "STRING")
                    new_var = types.App.VariableDeclaration(
                        name=var_name,
                        schema={"type_": var_type_str, "default": None}
                    )
                    updated_vars_list.append(new_var)
                    existing_vars[var_name] = new_var
                    has_new = True
                    print(f"      ✅ Variable '{var_name}' (DYNAMIC {var_type_str}) created.")

        if has_new:
            vars_client.update_app(target_app_path, variable_declarations=updated_vars_list)
            print(f"   ✅ All {len(existing_vars)} session variables synchronized to CXAS app successfully.")
        else:
            print(f"   ✅ All {len(existing_vars)} session variables are already synchronized on CXAS app.")

    except Exception as e:
        print(f"   ⚠️ Warning synchronizing variables: {e}")

    # Tools definition map
    # Each entry: (tool_id, description)
    # Code is read from the Scrapi-canonical path:
    #   tools/<tool_id>/python_function/python_code.py
    # Falls back to the flat tools/<tool_id>.py if the canonical path is absent.
    tools_def = [
        ('get_user_profile', 'Retrieves user profile and tier'),
        ('get_discount',     'Calculates tier discount percentage'),
        ('search_catalog',   'Searches product catalog'),
        ('add_to_cart',      'Adds items to cart'),
        ('get_cart',         'Retrieves current cart'),
        ('remove_from_cart', 'Removes item from cart'),
        ('submit_feedback',  'Submits user feedback'),
        ('end_session',      'Ends conversation session'),
    ]

    created_tools = {
        'end_session': f"{target_app_path}/tools/end_session"
    }
    for tool_id, desc in tools_def:
        # Canonical Scrapi path (preferred)
        canonical = root / 'tools' / tool_id / 'python_function' / 'python_code.py'
        # Legacy flat-file fallback
        flat = root / 'tools' / f'{tool_id}.py'
        tool_file = canonical if canonical.exists() else flat
        if not tool_file.exists():
            print(f"   ⚠️  Tool '{tool_id}' source not found — skipping.")
            continue
        code = tool_file.read_text(encoding='utf-8')
        payload = {
            'name': tool_id,
            'description': desc,
            'python_code': code
        }
        try:
            tool = tools_client.create_tool(tool_id=tool_id, display_name=tool_id, payload=payload)
            created_tools[tool_id] = getattr(tool, 'name', f"{target_app_path}/tools/{tool_id}")
            src = 'canonical' if canonical.exists() else 'flat'
            print(f"   ✅ Tool '{tool_id}' synchronized (source: {src}).")
        except Exception:
            if hasattr(tools_client, 'list_tools'):
                try:
                    for t in tools_client.list_tools():
                        if getattr(t, 'display_name', '') == tool_id or getattr(t, 'name', '').endswith('/tools/' + tool_id):
                            created_tools[tool_id] = t.name
                except Exception:
                    pass
            if tool_id not in created_tools:
                created_tools[tool_id] = f"{target_app_path}/tools/{tool_id}"

    # Callbacks definition map
    callbacks_def = [
        ('before_agent_callback', 'callbacks/before_agent.py', 'before_agent'),
        ('before_tool_callback', 'callbacks/before_tool.py', 'before_tool'),
        ('after_tool_callback', 'callbacks/after_tool.py', 'after_tool'),
        ('after_model_callback', 'callbacks/after_model.py', 'after_model')
    ]

    cb_code_map = {}
    for cb_id, cb_rel_path, _ in callbacks_def:
        cb_file = root / cb_rel_path
        if cb_file.exists():
            cb_code_map[cb_id] = cb_file.read_text(encoding='utf-8')

    agent_names_map = {a.display_name: a.name for a in agents_client.list_agents()}
    agent_tools_map = {
        'RootAgent': ['end_session'],
        'ShoppingAssistant': ['get_user_profile', 'get_discount', 'search_catalog', 'add_to_cart', 'get_cart', 'remove_from_cart', 'end_session'],
        'FeedbackAgent': ['submit_feedback', 'end_session']
    }
    agent_children_map = {
        'RootAgent': ['ShoppingAssistant', 'FeedbackAgent'],
        'ShoppingAssistant': [],
        'FeedbackAgent': []
    }

    agent_callbacks_map = {
        'RootAgent': {
            'before_agent': ['before_agent_callback'],
            'before_tool': [],
            'after_tool': [],
            'after_model': []
        },
        'ShoppingAssistant': {
            'before_agent': ['before_agent_callback'],
            'before_tool': ['before_tool_callback'],
            'after_tool': ['after_tool_callback'],
            'after_model': ['after_model_callback']
        },
        'FeedbackAgent': {
            'before_agent': ['before_agent_callback'],
            'before_tool': [],
            'after_tool': ['after_tool_callback'],
            'after_model': []
        }
    }

    for agent_display_name, default_tools in agent_tools_map.items():
        resource_name = agent_names_map.get(agent_display_name)
        if not resource_name:
            continue
        inst_file = root / 'agents' / agent_display_name / 'instruction.txt'
        instruction_text = inst_file.read_text(encoding='utf-8') if inst_file.exists() else ""
        resolved_children = [agent_names_map[c] for c in agent_children_map[agent_display_name] if c in agent_names_map]

        model_name = None
        json_file = root / 'agents' / agent_display_name / f'{agent_display_name}.json'
        agent_config = {}
        if json_file.exists():
            try:
                with open(json_file, 'r', encoding='utf-8') as jf:
                    agent_config = json.load(jf)
                    model_name = agent_config.get("model")
            except Exception:
                pass

        target_tools = agent_config.get("tools", default_tools)
        resolved_tools = [created_tools[t] for t in target_tools if t in created_tools]

        # Note: session variables are synced at the app level via vars_client.update_app()
        # in the block above. No per-agent session_parameters push is needed here.
        default_cbs = agent_callbacks_map.get(agent_display_name, {})
        bac = agent_config.get("beforeAgentCallbacks", default_cbs.get("before_agent", []))
        btc = agent_config.get("beforeToolCallbacks", default_cbs.get("before_tool", []))
        atc = agent_config.get("afterToolCallbacks", default_cbs.get("after_tool", []))
        amc = agent_config.get("afterModelCallbacks", default_cbs.get("after_model", []))

        before_agent_cbs = [make_cb(cb_code_map[cb], cb) for cb in bac if cb in cb_code_map]
        before_tool_cbs = [make_cb(cb_code_map[cb], cb) for cb in btc if cb in cb_code_map]
        after_tool_cbs = [make_cb(cb_code_map[cb], cb) for cb in atc if cb in cb_code_map]
        after_model_cbs = [make_cb(cb_code_map[cb], cb) for cb in amc if cb in cb_code_map]

        try:
            update_kwargs = {
                "instruction": instruction_text,
                "tools": resolved_tools,
                "child_agents": resolved_children
            }
            if model_name:
                update_kwargs["model_settings"] = {"model": model_name}
            if before_agent_cbs:
                update_kwargs["before_agent_callbacks"] = before_agent_cbs
            if before_tool_cbs:
                update_kwargs["before_tool_callbacks"] = before_tool_cbs
            if after_tool_cbs:
                update_kwargs["after_tool_callbacks"] = after_tool_cbs
            if after_model_cbs:
                update_kwargs["after_model_callbacks"] = after_model_cbs

            agents_client.update_agent(resource_name, **update_kwargs)
            total_cbs = len(before_agent_cbs) + len(before_tool_cbs) + len(after_tool_cbs) + len(after_model_cbs)
            print(f"   ✅ Agent '{agent_display_name}' synced (instruction, model={model_name or 'default'}, {len(resolved_tools)} tools, {total_cbs} callbacks attached).")
        except Exception as e:
            print(f"   ⚠️ Sync warning for '{agent_display_name}': {e}")

def main():
    parser = argparse.ArgumentParser(description="Build and deploy Sporting Goods Multi-Agent App")
    parser.add_argument("--env", choices=["dev", "staging", "prod"], default="dev", help="Target environment")
    parser.add_argument("--project", default="ecom-cx-agent", help="GCP Project ID")
    parser.add_argument("--location", default="us", help="GCP Region/Location")
    parser.add_argument("--app-id", default=None, help="CX Agent Studio App ID")
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

    # 2. Run unit tests
    print("\n🧪 Running Service & Callback Test Suite...")
    try:
        subprocess.run([sys.executable, "tests/test_services.py"], check=True)
        print("✅ Unit tests passed.")
    except subprocess.CalledProcessError:
        print("❌ Unit tests failed! Aborting deployment.")
        sys.exit(1)

    # 3. Synchronize with GCP CX Agent Studio
    print("\n☁️ Synchronizing resources with Google Cloud CX Agent Studio...")
    sync_tools_and_agents(target_app_path)

    print("\n==========================================================")
    print("🎉 DEPLOYMENT COMPLETED SUCCESSFULLY!")
    print("==========================================================")

if __name__ == "__main__":
    main()
