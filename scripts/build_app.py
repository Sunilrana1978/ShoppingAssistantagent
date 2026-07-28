import argparse
import os
import shutil
import subprocess
import sys
from typing import List
from pathlib import Path

# Add project root to sys.path
root = Path(__file__).parent.parent
sys.path.insert(0, str(root))

def clean_pycache():
    for p in root.rglob("__pycache__"):
        if p.is_dir():
            shutil.rmtree(p, ignore_errors=True)

def sync_tools_and_agents(target_app_path: str):
    from cxas_scrapi.core.tools import Tools
    from cxas_scrapi.core.agents import Agents

    print(f"\n   Synchronizing Python Tools and Agent Instructions to {target_app_path}...")
    tools_client = Tools(app_name=target_app_path)
    agents_client = Agents(app_name=target_app_path)

    tools_def = [
        ('get_user_profile', 'Look up user profile details such as name and membership tier by user_id.'),
        ('get_discount', 'Get discount rate for a membership tier (Gold, Silver, Bronze, Guest).'),
        ('search_catalog', 'Search product catalog by query, category, and price range.'),
        ('add_to_cart', 'Add an item SKU and quantity to the active session shopping cart.'),
        ('get_cart', 'Retrieve active cart details, items, subtotals, and totals.'),
        ('remove_from_cart', 'Remove an item SKU from the active session shopping cart.'),
        ('submit_feedback', 'Submit customer rating (1-5 stars) and feedback comments.')
    ]

    created_tools = {
        'end_session': f"{target_app_path}/tools/end_session"
    }
    # Pre-populate created_tools with already existing tools (including end_session)
    try:
        for t in tools_client.list_tools():
            tool_id = t.name.split('/')[-1]
            created_tools[tool_id] = t.name
    except Exception as e:
        print(f"   ⚠️ Warning listing existing tools: {e}")

    # Synchronize client-side tools (like end_session)
    client_tools = ['end_session']
    for tool_id in client_tools:
        json_path = root / 'tools' / tool_id / f'{tool_id}.json'
        if not json_path.exists():
            continue
        import json
        try:
            with open(json_path, 'r') as f:
                tool_data = json.load(f)
            
            # Extract client_function payload conforming to Tool schema
            cf_data = tool_data.get('clientFunction', {})
            payload = {
                'name': tool_id,
                'client_function': {
                    'name': cf_data.get('name', tool_id),
                    'description': cf_data.get('description', '')
                }
            }
            # Attempt to register/create the client tool
            t = tools_client.create_tool(tool_id=tool_id, display_name=tool_id, payload=payload, tool_type='client_function')
            created_tools[tool_id] = t.name
            print(f"   ✅ Client Tool '{tool_id}' synchronized/created.")
        except Exception as e:
            # Fallback to check if it's already listable
            if tool_id not in created_tools:
                for t in tools_client.list_tools():
                    if t.display_name == tool_id or t.name.endswith('/tools/' + tool_id):
                        created_tools[tool_id] = t.name

    for tool_id, desc in tools_def:
        code_path = root / 'tools' / tool_id / 'python_function' / 'python_code.py'
        if not code_path.exists():
            continue
        code = code_path.read_text(encoding='utf-8')
        payload = {'name': tool_id, 'description': desc, 'python_code': code}
        try:
            t = tools_client.create_tool(tool_id=tool_id, display_name=tool_id, payload=payload, tool_type='python_function')
            created_tools[tool_id] = t.name
        except Exception:
            if tool_id not in created_tools:
                for t in tools_client.list_tools():
                    if t.display_name == tool_id or t.name.endswith('/tools/' + tool_id):
                        created_tools[tool_id] = t.name

    # Synchronize Callback resources in CX Agent Studio
    created_callbacks = {}
    callbacks_def = [
        ('before_agent_callback', 'callbacks/before_agent.py', 'before_agent'),
        ('before_tool_callback', 'callbacks/before_tool.py', 'before_tool'),
        ('after_tool_callback', 'callbacks/after_tool.py', 'after_tool'),
        ('after_model_callback', 'callbacks/after_model.py', 'after_model')
    ]

    try:
        from cxas_scrapi.core.callbacks import Callbacks
        callbacks_client = Callbacks(app_name=target_app_path)
        for cb_id, cb_rel_path, cb_event in callbacks_def:
            cb_file = root / cb_rel_path
            if not cb_file.exists():
                continue
            code = cb_file.read_text(encoding='utf-8')
            payload = {
                'name': cb_id,
                'event_type': cb_event,
                'python_code': code
            }
            try:
                cb = callbacks_client.create_callback(callback_id=cb_id, display_name=cb_id, payload=payload)
                created_callbacks[cb_id] = getattr(cb, 'name', f"{target_app_path}/callbacks/{cb_id}")
                print(f"   ✅ Callback '{cb_id}' synchronized/created.")
            except Exception:
                if hasattr(callbacks_client, 'list_callbacks'):
                    try:
                        for existing_cb in callbacks_client.list_callbacks():
                            if getattr(existing_cb, 'display_name', '') == cb_id or getattr(existing_cb, 'name', '').endswith('/callbacks/' + cb_id):
                                created_callbacks[cb_id] = existing_cb.name
                    except Exception:
                        pass
                if cb_id not in created_callbacks:
                    created_callbacks[cb_id] = f"{target_app_path}/callbacks/{cb_id}"
    except ImportError:
        for cb_id, _, _ in callbacks_def:
            created_callbacks[cb_id] = f"{target_app_path}/callbacks/{cb_id}"

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

    cb_code_map = {}
    for cb_id, cb_rel_path, _ in callbacks_def:
        cb_file = root / cb_rel_path
        if cb_file.exists():
            cb_code_map[cb_id] = cb_file.read_text(encoding='utf-8')

    for agent_display_name, target_tools in agent_tools_map.items():
        resource_name = agent_names_map.get(agent_display_name)
        if not resource_name:
            continue
        inst_file = root / 'agents' / agent_display_name / 'instruction.txt'
        instruction_text = inst_file.read_text(encoding='utf-8') if inst_file.exists() else ""
        resolved_tools = [created_tools[t] for t in target_tools if t in created_tools]
        resolved_children = [agent_names_map[c] for c in agent_children_map[agent_display_name] if c in agent_names_map]

        # Read model & callback configuration from JSON file
        model_name = None
        json_file = root / 'agents' / agent_display_name / f'{agent_display_name}.json'
        agent_config = {}
        if json_file.exists():
            try:
                import json
                with open(json_file, 'r', encoding='utf-8') as jf:
                    agent_config = json.load(jf)
                    model_name = agent_config.get("model")
            except Exception:
                pass

        default_cbs = agent_callbacks_map.get(agent_display_name, {})
        bac = agent_config.get("beforeAgentCallbacks", default_cbs.get("before_agent", []))
        btc = agent_config.get("beforeToolCallbacks", default_cbs.get("before_tool", []))
        atc = agent_config.get("afterToolCallbacks", default_cbs.get("after_tool", []))
        amc = agent_config.get("afterModelCallbacks", default_cbs.get("after_model", []))

        before_agent_cbs = [{"python_code": cb_code_map[cb], "description": cb} for cb in bac if cb in cb_code_map]
        before_tool_cbs = [{"python_code": cb_code_map[cb], "description": cb} for cb in btc if cb in cb_code_map]
        after_tool_cbs = [{"python_code": cb_code_map[cb], "description": cb} for cb in atc if cb in cb_code_map]
        after_model_cbs = [{"python_code": cb_code_map[cb], "description": cb} for cb in amc if cb in cb_code_map]

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
            print(f"   ✅ Agent '{agent_display_name}' synced (instruction, model={model_name or 'default'}, {len(resolved_tools)} tools & {total_cbs} callbacks attached).")
        except Exception as e:
            print(f"   ⚠️ Sync warning for '{agent_display_name}': {e}")

def run_cli_command(args: List[str]):
    clean_pycache()
    try:
        subprocess.run(args, check=True)
    except FileNotFoundError:
        if args[0] == "cxas":
            fallback_args = [sys.executable, "-m", "cxas_scrapi.cli"] + args[1:]
            try:
                subprocess.run(fallback_args, check=True)
            except Exception as e:
                print(f"❌ Failed to run 'cxas' CLI module: {e}", file=sys.stderr)
                sys.exit(1)
        else:
            print(f"❌ Command not found: {args[0]}", file=sys.stderr)
            sys.exit(1)

def build_and_deploy_cxas(env: str):
    config_file = root / "gecx-config.toml"
    config_data = {}
    if sys.version_info >= (3, 11):
        import tomllib
        with open(config_file, "rb") as f:
            config_data = tomllib.load(f)
    else:
        try:
            import tomli as tomllib
            with open(config_file, "rb") as f:
                config_data = tomllib.load(f)
        except ImportError:
            # Fallback simple parser for gecx-config.toml
            config_data = {
                "default": {"project_id": "ecom-cx-agent", "location": "us", "app_id": "shopping-assistant-app"},
                "profiles": {
                    "dev": {"app_id": "shopping-assistant-app-dev"},
                    "staging": {"app_id": "shopping-assistant-app-staging"},
                    "prod": {"app_id": "shopping-assistant-app-prod"}
                }
            }

    default_config = config_data.get("default", {})
    project_id = default_config.get("project_id", "ecom-cx-agent")
    location = default_config.get("location", "us")
    app_id = default_config.get("app_id", "shopping-assistant-app")

    profiles = config_data.get("profiles", {})
    profile_config = profiles.get(env, {}) if isinstance(profiles, dict) else {}
    if isinstance(profile_config, dict):
        project_id = profile_config.get("project_id", project_id)
        location = profile_config.get("location", location)
        app_id = profile_config.get("app_id", app_id)

    target_app_path = f"projects/{project_id}/locations/{location}/apps/{app_id}"

    print(f"🚀 Deploying to Gemini Enterprise for Customer Experience (CX Agent Studio)...")
    print(f"   Environment: {env.upper()}")
    print(f"   Target App:  {target_app_path}")

    try:
        print(f"\n   Pushing application state to {target_app_path}...")
        run_cli_command(["cxas", "push", "--to", target_app_path])
        sync_tools_and_agents(target_app_path)

        print(f"\n==========================================================================")
        print(f"🎉 SUCCESSFULLY DEPLOYED TO GEMINI ENTERPRISE FOR CX IN {project_id}!")
        print(f"==========================================================================")
    except Exception as e:
        print(f"\n❌ Deployment failed: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="CX Agent Studio Live Deployer")
    parser.add_argument("--env", default="dev", help="Target deployment environment profile")
    args = parser.parse_args()
    build_and_deploy_cxas(args.env)
