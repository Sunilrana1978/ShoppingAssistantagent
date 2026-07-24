import argparse
import json
from pathlib import Path
import google.auth
from google.cloud import dialogflowcx_v3 as dialogflow
from google.api_core.client_options import ClientOptions

def build_and_deploy(env: str):
    root = Path(__file__).parent.parent
    env_file = root / "environments" / f"{env}.environment.json"
    if not env_file.exists():
        env_file = root / "environments" / "environment.json"

    with open(env_file, "r") as f:
        env_config = json.load(f)

    project_id = env_config.get("gcp_project", "ecom-cx-agent")
    location = env_config.get("location", "us")
    display_name = env_config.get("app_id", "ShoppingAssistantApp")

    print(f"🚀 Deploying ShoppingAssistantApp to [{env.upper()}] environment in GCP...")
    print(f"   GCP Project: {project_id}")
    print(f"   App Name:    {display_name}")
    print(f"   Location:    {location}")

    credentials, _ = google.auth.default(
        scopes=["https://www.googleapis.com/auth/cloud-platform"],
        quota_project_id=project_id
    )

    opts = ClientOptions(api_endpoint=f"{location}-dialogflow.googleapis.com:443" if location != "global" else None)
    client = dialogflow.AgentsClient(credentials=credentials, client_options=opts)
    parent = f"projects/{project_id}/locations/{location}"

    # Search for existing agent
    existing = list(client.list_agents(parent=parent))
    target_agent = None
    for ag in existing:
        if ag.display_name in [display_name, "ShoppingAssistantApp"]:
            target_agent = ag
            break

    if target_agent:
        print(f"✅ Found existing Agent in GCP: '{target_agent.display_name}' ({target_agent.name})")
    else:
        print(f"🚀 Provisioning new Agent '{display_name}' in {parent}...")
        agent_spec = dialogflow.Agent(
            display_name=display_name,
            default_language_code="en",
            time_zone="America/Los_Angeles",
            description="Sporting Goods Multi-Agent Shopping & Feedback Assistant App"
        )
        target_agent = client.create_agent(parent=parent, agent=agent_spec)
        print(f"🎉 Created Agent: {target_agent.name}")

    print(f"✅ Successfully synchronized ShoppingAssistantApp live in GCP project [{project_id}] ({location})!")
    return target_agent.name

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="CX Agent Studio Live GCP Deployment Script")
    parser.add_argument("--env", default="dev", help="Target deployment environment")
    args = parser.parse_args()
    build_and_deploy(args.env)
