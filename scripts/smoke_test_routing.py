#!/usr/bin/env python3
"""
Live routing smoke test against a deployed CXAS app.

evaluations/run_evals.py only simulates ShoppingAssistant's own callback
chain locally — it never exercises RootAgent's actual routing/transfer
behavior. That gap is exactly what let a real bug ship silently: RootAgent
was answering bare greetings itself instead of transferring to
ShoppingAssistant, so fetch_user_profile never ran and greetings were
never personalized.

This script drives real conversation turns against a deployed app via the
CES Sessions API (the same mechanism CX Agent Studio's Preview panel uses)
and checks that RootAgent routes correctly. It is not wired into CI (it
needs live GCP credentials and burns model quota) — run it manually after
any change to agents/*/instruction.txt or agents/*/*.json.

Usage:
    uv run python scripts/smoke_test_routing.py [--env dev|staging|prod]
"""

import argparse
import sys
import time
import uuid
from pathlib import Path

from google.api_core.exceptions import ResourceExhausted
from google.protobuf.json_format import MessageToDict

root = Path(__file__).parent.parent
sys.path.insert(0, str(root))


def _resolve_app_path(env: str) -> str:
    try:
        import tomllib
    except ImportError:
        import tomli as tomllib
    with open(root / "gecx-config.toml", "rb") as f:
        cfg = tomllib.load(f)
    app_id = cfg.get("profiles", {}).get(env, {}).get("app_id") or f"shopping-assistant-app-{env}"
    project = cfg["default"]["project_id"]
    location = cfg["default"]["location"]
    return f"projects/{project}/locations/{location}/apps/{app_id}"


def _run_turn(sessions, session_id: str, text: str, variables=None, max_retries: int = 5):
    for attempt in range(max_retries):
        try:
            resp = sessions.run(session_id=session_id, text=text, variables=variables)
            return MessageToDict(resp._original_response._pb)
        except ResourceExhausted:
            wait = 20 * (attempt + 1)
            print(f"   [retry] quota exhausted, waiting {wait}s...")
            time.sleep(wait)
    raise RuntimeError(f"Exhausted retries sending turn: {text!r}")


def _extract(result: dict):
    """Pulls agent text and any transfer target out of a run_session result."""
    text = ""
    transfers = []
    for out in result.get("outputs", []):
        text = out.get("text", "") or text
        for msg in out.get("diagnosticInfo", {}).get("messages", []):
            for chunk in msg.get("chunks", []):
                if "agentTransfer" in chunk:
                    transfers.append(chunk["agentTransfer"].get("displayName"))
    return text, transfers


def main():
    parser = argparse.ArgumentParser(description="Live routing smoke test")
    parser.add_argument("--env", default="dev", choices=["dev", "staging", "prod"])
    args = parser.parse_args()

    from cxas_scrapi.core.sessions import Sessions

    app_path = _resolve_app_path(args.env)
    print(f"🧪 Live routing smoke test against {app_path}\n")
    sessions = Sessions(app_name=app_path)

    passed = 0
    failed = 0

    def check(name: str, condition: bool, detail: str):
        nonlocal passed, failed
        status = "✅ PASS" if condition else "❌ FAIL"
        print(f"{status}: {name}")
        if not condition:
            print(f"        {detail}")
            failed += 1
        else:
            passed += 1

    # Test 1: a bare greeting from a known member must route to ShoppingAssistant
    # and come back personalized, not the generic RootAgent fallback text.
    session_id = f"smoke_greeting_{uuid.uuid4().hex[:8]}"
    result = _run_turn(sessions, session_id, "hello", variables={"user_id": "u_1029"})
    text, transfers = _extract(result)
    print(f"\n[Greeting] Agent said: {text!r}")
    check(
        "Bare greeting transfers to ShoppingAssistant",
        "ShoppingAssistant" in transfers,
        f"Expected a transfer to ShoppingAssistant, got transfers={transfers}",
    )
    check(
        "Bare greeting is personalized (not the generic fallback)",
        "Alex" in text and "Would you like to shop for products or share feedback" not in text,
        f"Expected personalized greeting mentioning 'Alex', got: {text!r}",
    )

    # Test 2: explicit shopping intent must route to ShoppingAssistant.
    session_id = f"smoke_shop_{uuid.uuid4().hex[:8]}"
    result = _run_turn(sessions, session_id, "I want to buy some running shoes", variables={"user_id": "u_1030"})
    text, transfers = _extract(result)
    print(f"\n[Shop intent] Agent said: {text!r}")
    check(
        "Explicit shop intent transfers to ShoppingAssistant",
        "ShoppingAssistant" in transfers,
        f"Expected a transfer to ShoppingAssistant, got transfers={transfers}",
    )

    # Test 3: explicit feedback intent must route to FeedbackAgent.
    session_id = f"smoke_feedback_{uuid.uuid4().hex[:8]}"
    result = _run_turn(sessions, session_id, "I'd like to leave some feedback", variables={"user_id": "u_1031"})
    text, transfers = _extract(result)
    print(f"\n[Feedback intent] Agent said: {text!r}")
    check(
        "Explicit feedback intent transfers to FeedbackAgent",
        "FeedbackAgent" in transfers,
        f"Expected a transfer to FeedbackAgent, got transfers={transfers}",
    )

    print(f"\n==========================================")
    print(f"📊 Routing Smoke Test: Passed={passed} | Failed={failed}")
    print(f"==========================================")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
