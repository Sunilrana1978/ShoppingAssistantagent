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
    print(f"🚀 Deploying to Gemini Enterprise for Customer Experience (CX Agent Studio)...")
    print(f"   Environment Profile: {env.upper()}")

    try:
        # 1. Set the active profile in the workspace config
        print(f"\n   Setting workspace profile to '{env}'...")
        run_cli_command(["cxas", "workspace", "set", "--profile", env])

        # 2. Push the application to CX Agent Studio
        print(f"\n   Pushing application state (agents, instructions, tools, callbacks)...")
        run_cli_command(["cxas", "push"])

        print(f"\n==========================================================================")
        print(f"🎉 SUCCESSFULLY DEPLOYED TO GEMINI ENTERPRISE FOR CX IN PROFILE {env.upper()}!")
        print(f"==========================================================================")
    except Exception as e:
        print(f"\n❌ Deployment failed: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="CX Agent Studio Live Deployer")
    parser.add_argument("--env", default="dev", help="Target deployment environment profile")
    args = parser.parse_args()
    build_and_deploy_cxas(args.env)
