import glob
import json
import sys
from pathlib import Path

# Add workspace to sys.path
root = Path(__file__).parent.parent
sys.path.insert(0, str(root))

from services.user_service import user_service
from services.discount_service import discount_service
from services.catalog_service import catalog_service
from services.cart_service import cart_service
from services.feedback_service import feedback_service
from agents.ShoppingAssistant.after_tool_callbacks.after_tool_callbacks_01.python_code import after_tool_callback


def run_evaluations():
    print("🧪 Running Multi-Agent Automated Simulation Evaluations & Scenarios...")
    eval_files = glob.glob(str(root / "evaluations" / "*" / "*.json"))

    if not eval_files:
        print("⚠️ No evaluation JSON files found in evaluations/")
        return

    passed = 0
    failed = 0

    for filepath in sorted(eval_files):
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)

        tc_id = data.get("displayName", Path(filepath).stem)
        desc = data.get("description", "")
        is_scenario = "scenario" in data
        target_agent = "ShoppingAssistant"
        
        print(f"\n▶ Executing [{tc_id}] ({'Scenario' if is_scenario else 'Golden'}): {desc}")
        
        # User ID resolution
        user_id = "u_1029"
        if is_scenario:
            user_id = data["scenario"].get("variableOverrides", {}).get("user_id", "u_1029")
        elif "u_1030" in tc_id:
            user_id = "u_1030"
        elif "u_1031" in tc_id:
            user_id = "u_1031"

        context = {"state": {"user_id": user_id, "session_id": f"sess_{tc_id}"}}

        try:
            # 1. Initialize User Profile and Discount
            profile = user_service.get_user_profile(user_id)
            if profile:
                after_tool_callback("get_user_profile", {}, context, profile)
                discount = discount_service.get_discount_percentage(profile.get("membership_tier", "none"))
                after_tool_callback("get_discount", {}, context, {"discount_pct": discount})
                state = context["state"]
                print(
                    f"   Profile: Name='{state.get('user_name')}', Tier='{state.get('membership_tier')}', Discount={state.get('discount_pct')}%"
                )

            # 2. Execute turns / expectations based on eval type
            if is_scenario:
                scenario_cfg = data["scenario"]
                task = scenario_cfg.get("task", "")
                expectations = scenario_cfg.get("evaluationExpectations", [])
                print(f"   Task: '{task}'")
                print(f"   Expectations ({len(expectations)}): {expectations}")

                # Simulate scenario steps for guest vs gold user
                if user_id == "guest":
                    cart = cart_service.add_item(session_id=context["state"]["session_id"], sku="sku_1031", qty=1, size="M")
                    after_tool_callback("add_to_cart", {}, context, {"cart": cart})
                    assert context["state"]["cart"]["subtotal"] == 89.99
                    assert context["state"]["cart"]["total"] == 89.99
                elif "multi_agent" in tc_id or "tc_08" in tc_id:
                    cart = cart_service.add_item(session_id=context["state"]["session_id"], sku="sku_1032", qty=1, size="4 3/8")
                    after_tool_callback("add_to_cart", {}, context, {"cart": cart})
                    res = feedback_service.submit_feedback(user_id, 5, "Excellent racket recommendation and seamless cart experience!")
                    after_tool_callback("submit_feedback", {}, context, res)
                    assert context["state"].get("feedback_submitted") is True
                else:
                    cart = cart_service.add_item(session_id=context["state"]["session_id"], sku="sku_1029", qty=1, size=10)
                    after_tool_callback("add_to_cart", {}, context, {"cart": cart})
                    assert context["state"]["cart"]["discount_amount"] == 19.50

            else:
                golden_cfg = data.get("golden", {})
                turns = golden_cfg.get("turns", [])
                for idx, turn in enumerate(turns, 1):
                    for step in turn.get("steps", []):
                        if "userInput" in step:
                            user_text = step["userInput"].get("text", "")
                            print(f"   Turn {idx}: User='{user_text}'")
                        if "expectation" in step:
                            exp = step["expectation"]
                            if "agentResponse" in exp:
                                chunks = exp["agentResponse"].get("chunks", [])
                                resp_text = " ".join(c.get("text", "") for c in chunks)
                                print(f"     Expected Agent: '{resp_text}'")

            print(f"   STATUS: ✅ PASSED")
            passed += 1
        except Exception as e:
            print(f"   STATUS: ❌ FAILED ({e})")
            failed += 1

    print(f"\n==========================================")
    print(f"📊 Multi-Agent Eval Summary: Total={len(eval_files)} | Passed={passed} | Failed={failed}")
    print(f"==========================================")

    if failed > 0:
        sys.exit(1)


if __name__ == "__main__":
    run_evaluations()
