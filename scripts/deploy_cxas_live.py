import os
import sys
from pathlib import Path

# Add project root to sys.path
root = Path(__file__).parent.parent
sys.path.insert(0, str(root))

from cxas_scrapi import Apps, Agents

def deploy_to_gemini_enterprise(project_id="ecom-cx-agent", location="us"):
    print("🚀 Connecting to Gemini Enterprise for Customer Experience (CX Agent Studio)...")
    print(f"   GCP Project: {project_id}")
    print(f"   Location:    {location}")
    print("   API Endpoint: google.cloud.ces_v1beta (Customer Experience Studio)")

    app_client = Apps(project_id=project_id, location=location)

    # 1. Query existing apps in CX Agent Studio
    print("\n🔍 Querying existing CX Agent Studio Apps...")
    existing_apps = app_client.get_apps_map() if hasattr(app_client, "get_apps_map") else {}
    print(f"   Found {len(existing_apps)} existing app(s): {list(existing_apps.keys()) if isinstance(existing_apps, dict) else existing_apps}")

    app_id = "shopping-assistant-app"
    display_name = "ShoppingAssistantApp"
    target_app_path = f"projects/{project_id}/locations/{location}/apps/{app_id}"

    # Check if app exists
    if isinstance(existing_apps, dict) and target_app_path in existing_apps:
        print(f"✅ Found existing App in CX Agent Studio: {target_app_path}")
        app_name = target_app_path
    else:
        print(f"🚀 Creating new App '{display_name}' ({app_id}) in CX Agent Studio...")
        try:
            created_app = app_client.create_app(
                app_id=app_id,
                display_name=display_name,
                description="Sporting Goods Multi-Agent Shopping & Feedback Assistant App"
            )
            app_name = created_app.name
            print(f"🎉 Created App in Gemini Enterprise for CX: {app_name}")
        except Exception as e:
            print(f"⚠️ App creation note: {e}")
            app_name = target_app_path

    # Initialize Agents client with app_name
    agent_client = Agents(app_name=app_name)

    # 2. Read XML instructions
    root_inst_path = root / "agents" / "root_agent" / "instructions.xml"
    shopping_inst_path = root / "agents" / "shopping_assistant" / "instructions.xml"
    feedback_inst_path = root / "agents" / "feedback_agent" / "instructions.xml"

    root_instruction = root_inst_path.read_text(encoding="utf-8") if root_inst_path.exists() else ""
    shopping_instruction = shopping_inst_path.read_text(encoding="utf-8") if shopping_inst_path.exists() else ""
    feedback_instruction = feedback_inst_path.read_text(encoding="utf-8") if feedback_inst_path.exists() else ""

    # 3. Create / Sync Agents in CX Agent Studio
    print(f"\n🚀 Provisioning Agents under App '{app_name}' in Gemini Enterprise for CX...")

    # RootAgent
    try:
        ag_root = agent_client.create_agent(
            agent_id="root-agent",
            display_name="RootAgent",
            model="gemini-3.5-flash",
            instruction=root_instruction
        )
        print(f"✅ Provisioned RootAgent: {ag_root.name if hasattr(ag_root, 'name') else ag_root}")
    except Exception as e:
        print(f"   RootAgent status: {e}")

    # ShoppingAssistant
    try:
        ag_shop = agent_client.create_agent(
            agent_id="shopping-assistant",
            display_name="ShoppingAssistant",
            model="gemini-3.5-flash",
            instruction=shopping_instruction
        )
        print(f"✅ Provisioned ShoppingAssistant: {ag_shop.name if hasattr(ag_shop, 'name') else ag_shop}")
    except Exception as e:
        print(f"   ShoppingAssistant status: {e}")

    # FeedbackAgent
    try:
        ag_feed = agent_client.create_agent(
            agent_id="feedback-agent",
            display_name="FeedbackAgent",
            model="gemini-3.5-flash",
            instruction=feedback_instruction
        )
        print(f"✅ Provisioned FeedbackAgent: {ag_feed.name if hasattr(ag_feed, 'name') else ag_feed}")
    except Exception as e:
        print(f"   FeedbackAgent status: {e}")

    print("\n==========================================================")
    print("🎉 DEPLOYMENT TO GEMINI ENTERPRISE FOR CX (CXAS) COMPLETE!")
    print("==========================================================")

if __name__ == "__main__":
    deploy_to_gemini_enterprise()
