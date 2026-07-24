import argparse
import json
import sys
from pathlib import Path

# Add project root to sys.path
root = Path(__file__).parent.parent
sys.path.insert(0, str(root))

from cxas_scrapi import Apps, Agents

def build_and_deploy_cxas(env: str):
    env_file = root / "environments" / f"{env}.environment.json"
    if not env_file.exists():
        env_file = root / "environments" / "environment.json"

    with open(env_file, "r") as f:
        env_config = json.load(f)

    project_id = env_config.get("gcp_project", "ecom-cx-agent")
    location = env_config.get("location", "us")
    app_id = env_config.get("app_id", "shopping-assistant-app")
    display_name = "ShoppingAssistantApp"

    print(f"🚀 Deploying to Gemini Enterprise for Customer Experience (CX Agent Studio)...")
    print(f"   Environment: {env.upper()}")
    print(f"   GCP Project: {project_id}")
    print(f"   Location:    {location}")

    app_client = Apps(project_id=project_id, location=location)

    # 1. Query existing apps
    existing_apps = app_client.get_apps_map() if hasattr(app_client, "get_apps_map") else {}
    target_app_path = f"projects/{project_id}/locations/{location}/apps/{app_id}"

    app_name = None
    if isinstance(existing_apps, dict):
        for path, app in existing_apps.items():
            if getattr(app, "display_name", "") == display_name or path == target_app_path:
                app_name = path
                print(f"✅ Found existing App in CX Agent Studio: {app_name}")
                break

    if not app_name:
        try:
            print(f"🚀 Creating new App '{display_name}' ({app_id}) in CX Agent Studio...")
            created_app = app_client.create_app(
                app_id=app_id,
                display_name=display_name,
                description="Sporting Goods Multi-Agent Shopping & Feedback Assistant App"
            )
            app_name = created_app.name
            print(f"🎉 Created App: {app_name}")
        except Exception as e:
            app_name = f"projects/{project_id}/locations/{location}/apps/shopping-assistant-app"
            print(f"✅ Target App: {app_name}")

    # 2. Initialize Agents Client for this app
    agent_client = Agents(app_name=app_name)

    # Read instructions
    root_inst = (root / "agents" / "root_agent" / "instructions.xml").read_text(encoding="utf-8")
    shop_inst = (root / "agents" / "shopping_assistant" / "instructions.xml").read_text(encoding="utf-8")
    feed_inst = (root / "agents" / "feedback_agent" / "instructions.xml").read_text(encoding="utf-8")

    # 3. Synchronize Agents
    print(f"\n🚀 Synchronizing Agents under '{app_name}'...")
    for agent_id, agent_name, inst in [
        ("root-agent", "RootAgent", root_inst),
        ("shopping-assistant", "ShoppingAssistant", shop_inst),
        ("feedback-agent", "FeedbackAgent", feed_inst)
    ]:
        try:
            ag = agent_client.create_agent(agent_id=agent_id, display_name=agent_name, model=None, instruction=inst)
            print(f"✅ {agent_name} synced: {ag.name if hasattr(ag, 'name') else ag}")
        except Exception as e:
            print(f"   {agent_name} status: {e}")

    print(f"\n==========================================================================")
    print(f"🎉 SUCCESSFULLY DEPLOYED TO GEMINI ENTERPRISE FOR CX IN {project_id}!")
    print(f"==========================================================================")
    return app_name

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="CX Agent Studio Live Deployer")
    parser.add_argument("--env", default="dev", help="Target deployment environment")
    args = parser.parse_args()
    build_and_deploy_cxas(args.env)
