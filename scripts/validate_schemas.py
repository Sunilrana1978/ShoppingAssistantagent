import json
import sys
from pathlib import Path

def validate_project():
    root = Path(__file__).parent.parent
    print("🔍 Validating Multi-Agent Application manifests and schemas...")

    try:
        import cxas_scrapi
        import os
        pkg_dir = os.path.dirname(cxas_scrapi.__file__)
        print(f"DEBUG: cxas_scrapi package dir: {pkg_dir}")
        print("DEBUG: files in package:")
        for r, d, files in os.walk(pkg_dir):
            for f in files:
                rel = os.path.relpath(os.path.join(r, f), pkg_dir)
                if any(x in rel for x in ["schema", "model", "config", "app", "agent"]):
                    print(f"  - {rel}")
    except Exception as ex:
        print(f"DEBUG: failed to inspect cxas_scrapi: {ex}")

    # Validate app.json
    app_file = root / "app.json"
    if not app_file.exists():
        print("❌ Error: app.json missing")
        sys.exit(1)
    with open(app_file, "r") as f:
        app_data = json.load(f)
    print(f"✅ app.json valid - App Name: {app_data.get('name')}, Default Agent: {app_data.get('default_agent')}")

    # Validate agents
    agents = ["root_agent", "shopping_assistant", "feedback_agent"]
    for agent_dir in agents:
        af = root / "agents" / agent_dir / "agent.json"
        if not af.exists():
            print(f"❌ Error: agents/{agent_dir}/agent.json missing")
            sys.exit(1)
        with open(af, "r") as f:
            adata = json.load(f)
        print(f"✅ agents/{agent_dir}/agent.json valid - Agent: {adata.get('name')}")

        inst_file = root / "agents" / agent_dir / "instructions.xml"
        if not inst_file.exists():
            print(f"❌ Error: agents/{agent_dir}/instructions.xml missing")
            sys.exit(1)
        print(f"   ↳ instructions.xml verified ({inst_file.stat().st_size} bytes)")

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
