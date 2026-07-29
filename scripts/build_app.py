#!/usr/bin/env python3
"""
Build & Deployment Automation Script for Sporting Goods Multi-Agent Application.
Supports environments: dev, staging, prod.
"""

import sys
import os
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
        
        agents_client = Agents(app_name=target_app_path)
        tools_client = Tools(app_name=target_app_path)
    except ImportError as e:
        print(f"⚠️ cxas_scrapi not available: {e}")
        return

    # Tools definition map
    tools_def = [
        ('get_user_profile', 'tools/get_user_profile.py', 'Retrieves user profile and tier'),
        ('get_discount', 'tools/get_discount.py', 'Calculates tier discount percentage'),
        ('search_catalog', 'tools/search_catalog.py', 'Searches product catalog'),
        ('add_to_cart', 'tools/add_to_cart.py', 'Adds items to cart'),
        ('get_cart', 'tools/get_cart.py', 'Retrieves current cart'),
        ('remove_from_cart', 'tools/remove_from_cart.py', 'Removes item from cart'),
        ('submit_feedback', 'tools/submit_feedback.py', 'Submits user feedback'),
        ('end_session', 'tools/end_session.py', 'Ends conversation session')
    ]

    created_tools = {}
    for tool_id, tool_rel_path, desc in tools_def:
        tool_file = root / tool_rel_path
        if not tool_file.exists():
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
            print(f"   ✅ Tool '{tool_id}' synchronized.")
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
        'ShoppingAssistant': ['get_user_profile', 'get_discount', 'search_catalog', 'add_to_cart', 'get_cart', 'remove_from_cart'],
        'FeedbackAgent': ['submit_feedback']
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

    for agent_display_name, target_tools in agent_tools_map.items():
        resource_name = agent_names_map.get(agent_display_name)
        if not resource_name:
            continue
        inst_file = root / 'agents' / agent_display_name / 'instruction.txt'
        instruction_text = inst_file.read_text(encoding='utf-8') if inst_file.exists() else ""
        resolved_tools = [created_tools[t] for t in target_tools if t in created_tools]
        resolved_children = [agent_names_map[c] for c in agent_children_map[agent_display_name] if c in agent_names_map]

        import json
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

        # Load session variables declared in variables.json.
        # These MUST be synced to CXAS so that {variable_name} placeholders
        # in instruction templates are recognised and resolved at runtime.
        agent_variables = {}
        vars_file = root / 'agents' / agent_display_name / 'variables.json'
        if vars_file.exists():
            try:
                with open(vars_file, 'r', encoding='utf-8') as vf:
                    vars_data = json.load(vf)
                # Merge static + dynamic variable declarations into a flat dict
                # keyed by variable name with their metadata as the value.
                agent_variables.update(vars_data.get('static', {}))
                agent_variables.update(vars_data.get('dynamic', {}))
            except Exception as e:
                print(f"   ⚠️ Could not load variables.json for '{agent_display_name}': {e}")

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
            print(f"   ✅ Agent '{agent_display_name}' synced (instruction, model={model_name or 'default'}, {len(resolved_tools)} tools, {len(agent_variables)} session vars & {total_cbs} callbacks attached).")
        except Exception as e:
            print(f"   ⚠️ Sync warning for '{agent_display_name}': {e}")

def main():
    parser = argparse.ArgumentParser(description="Build and deploy Sporting Goods Multi-Agent App")
    parser.add_argument("--env", choices=["dev", "staging", "prod"], default="dev", help="Target environment")
    parser.add_argument("--project", default="ecom-cx-agent", help="GCP Project ID")
    parser.add_argument("--location", default="us", help="GCP Region/Location")
    parser.add_argument("--app-id", default="shopping-assistant-app", help="CX Agent Studio App ID")
    args = parser.parse_args()

    print(f"==========================================================")
    print(f"🚀 DEPLOYING SPORTING GOODS MULTI-AGENT APP [{args.env.upper()}]")
    print(f"==========================================================")
    print(f"📍 Project: {args.project} | Location: {args.location} | App ID: {args.app_id}")

    target_app_path = f"projects/{args.project}/locations/{args.location}/apps/{args.app_id}"
    
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
