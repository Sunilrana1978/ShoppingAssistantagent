import os
import sys
import google.auth
from google.cloud import dialogflowcx_v3 as dialogflow
from google.api_core.client_options import ClientOptions

def create_agent_live(project_id="ecom-cx-agent", location="us", display_name="ShoppingAssistantApp"):
    # Force credentials with quota_project_id
    credentials, auth_project = google.auth.default(
        scopes=["https://www.googleapis.com/auth/cloud-platform"],
        quota_project_id=project_id
    )

    opts = ClientOptions(api_endpoint=f"{location}-dialogflow.googleapis.com:443" if location != "global" else None)
    client = dialogflow.AgentsClient(credentials=credentials, client_options=opts)
    parent = f"projects/{project_id}/locations/{location}"

    print(f"🔍 Querying live agents in {parent} (Project: {project_id})...")
    try:
        existing_agents = list(client.list_agents(parent=parent))
        print(f"Found {len(existing_agents)} existing agents:")
        for agent in existing_agents:
            print(f"  - {agent.display_name} ({agent.name})")
    except Exception as e:
        print(f"⚠️ Query note: {e}")
        existing_agents = []

    for agent in existing_agents:
        if agent.display_name in [display_name, "RootAgent"]:
            print(f"✅ Agent '{agent.display_name}' already exists: {agent.name}")
            return agent.name

    print(f"🚀 Creating Agent '{display_name}' in {parent}...")
    agent_spec = dialogflow.Agent(
        display_name=display_name,
        default_language_code="en",
        time_zone="America/Los_Angeles",
        description="Sporting Goods Multi-Agent Shopping & Feedback Assistant App"
    )

    created_agent = client.create_agent(parent=parent, agent=agent_spec)
    print(f"\n🎉 SUCCESS! Agent created live in GCP console!")
    print(f"   Display Name: {created_agent.display_name}")
    print(f"   Resource Name: {created_agent.name}")
    return created_agent.name

if __name__ == "__main__":
    create_agent_live()
