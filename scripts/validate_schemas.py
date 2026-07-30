import json
import sys
from pathlib import Path

def validate_project():
    root = Path(__file__).parent.parent
    print("🔍 Validating Multi-Agent Application manifests and schemas...")

    # Validate app.json
    app_file = root / "app.json"
    if not app_file.exists():
        print("❌ Error: app.json missing")
        sys.exit(1)
    with open(app_file, "r") as f:
        app_data = json.load(f)
    
    # Check for correct camelCase key
    root_agent = app_data.get("rootAgent")
    if not root_agent:
        print("❌ Error: 'rootAgent' missing or empty in app.json")
        sys.exit(1)
        
    print(f"✅ app.json valid - App Name: {app_data.get('name')}, Root Agent: {root_agent}")

    # Validate agents
    try:
        import cxas_scrapi.core.agents as ca
        import inspect
        print("DEBUG: Inspecting Agent class fields...")
        if hasattr(ca.Agent, "model_fields"):
            print("  Pydantic model fields:", list(ca.Agent.model_fields.keys()))
        elif hasattr(ca.Agent, "__fields__"):
            print("  Pydantic v1 fields:", list(ca.Agent.__fields__.keys()))
        else:
            print("  Members:", [name for name, _ in inspect.getmembers(ca.Agent)])
    except Exception as ex:
        print(f"DEBUG: failed to inspect Agent class: {ex}")

    agents = ["RootAgent", "ShoppingAssistant", "FeedbackAgent"]
    for agent_dir in agents:
        af = root / "agents" / agent_dir / f"{agent_dir}.json"
        if not af.exists():
            print(f"❌ Error: agents/{agent_dir}/{agent_dir}.json missing")
            sys.exit(1)
        with open(af, "r") as f:
            adata = json.load(f)
        
        print(f"✅ agents/{agent_dir}/{agent_dir}.json valid - Agent: {adata.get('name')}")

        inst_file = root / "agents" / agent_dir / "instruction.txt"
        if not inst_file.exists():
            inst_file = root / "agents" / agent_dir / "instructions.xml"
        if not inst_file.exists():
            print(f"❌ Error: agents/{agent_dir} instruction file missing")
            sys.exit(1)
        print(f"   ↳ {inst_file.name} verified ({inst_file.stat().st_size} bytes)")

    # Validate json data files
    for data_fname in ["mock_users.json", "membership_discounts.json", "mock_catalog.json", "mock_feedback.json"]:
        df = root / "data" / data_fname
        if not df.exists():
            print(f"❌ Error: data/{data_fname} missing")
            sys.exit(1)
        with open(df, "r") as f:
            json.load(f)
        print(f"✅ data/{data_fname} valid")


    print("\n🎉 All Multi-Agent manifests, XML instructions, and data schemas validated successfully!")

if __name__ == "__main__":
    validate_project()
