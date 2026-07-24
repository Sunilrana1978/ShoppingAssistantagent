import argparse
import subprocess
import sys
from pathlib import Path

# Add project root to sys.path
root = Path(__file__).parent.parent
sys.path.insert(0, str(root))

def run_cli_command(args: list[str]):
    # Try calling the CLI tool directly first
    try:
        subprocess.run(args, check=True)
    except FileNotFoundError:
        # If 'cxas' is not found, try running it as a python module
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
    if sys.version_info >= (3, 11):
        import tomllib
    else:
        import tomli as tomllib

    with open(config_file, "rb") as f:
        config_data = tomllib.load(f)

    # Resolve default configurations
    default_config = config_data.get("default", {})
    project_id = default_config.get("project_id", "ecom-cx-agent")
    location = default_config.get("location", "us")
    app_id = default_config.get("app_id", "shopping-assistant-app")

    # Apply profile overrides
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
        # Push the application configuration using cxas push --to
        print(f"\n   Pushing application state to {target_app_path}...")
        run_cli_command(["cxas", "push", "--to", target_app_path])

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
