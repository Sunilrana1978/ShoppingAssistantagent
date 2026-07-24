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
from callbacks.after_tool import after_tool_callback

def run_evaluations():
    test_cases_file = root / "evals" / "test_cases.json"
    with open(test_cases_file, "r") as f:
        test_cases = json.load(f)

    print("🧪 Running Multi-Agent Automated Simulation Evaluations...")
    passed = 0
    failed = 0

    for tc in test_cases:
        tc_id = tc["id"]
        desc = tc["description"]
        user_id = tc["user_id"]
        agent = tc.get("agent", "ShoppingAssistant")
        print(f"\n▶ Executing [{tc_id}] (Target Agent: {agent}): {desc}")

        context = {"state": {"user_id": user_id, "session_id": f"sess_{tc_id}"}}
        
        try:
            if agent == "ShoppingAssistant":
                profile = user_service.get_user_profile(user_id)
                after_tool_callback("get_user_profile", profile, context)

                discount = discount_service.get_discount_percentage(profile["membership_tier"])
                after_tool_callback("get_discount", {"discount_pct": discount}, context)

                state = context["state"]
                print(f"   Profile: Name='{state.get('user_name')}', Tier='{state.get('membership_tier')}', Discount={state.get('discount_pct')}%")

                if "expected_user_name" in tc["turns"][0]:
                    assert state.get("user_name") == tc["turns"][0]["expected_user_name"]
                if "expected_discount_pct" in tc["turns"][0]:
                    assert state.get("discount_pct") == tc["turns"][0]["expected_discount_pct"]

                if len(tc["turns"]) > 1:
                    turn2 = tc["turns"][1]
                    sku = turn2.get("expected_matched_sku", "sku_1029")
                    cart = cart_service.add_item(session_id=context["state"]["session_id"], sku=sku, qty=1, size=10)
                    after_tool_callback("add_to_cart", {"cart": cart}, context)

                    final_cart = context["state"]["cart"]
                    print(f"   Cart: Subtotal=${final_cart['subtotal']}, Discount=-${final_cart['discount_amount']}, Total=${final_cart['total']}")

                    if "expected_subtotal" in turn2:
                        assert final_cart["subtotal"] == turn2["expected_subtotal"]
                    if "expected_discount_amount" in turn2:
                        assert final_cart["discount_amount"] == turn2["expected_discount_amount"]
                    if "expected_cart_total" in turn2:
                        assert final_cart["total"] == turn2["expected_cart_total"]

            elif agent == "FeedbackAgent":
                turn = tc["turns"][0]
                res = feedback_service.submit_feedback(user_id, turn["rating"], turn["comments"])
                after_tool_callback("submit_feedback", res, context)
                assert context["state"].get("feedback_submitted") is True
                print(f"   Feedback: ID={res['feedback_id']}, Rating={res['rating']} stars, Status=Submitted")

            print(f"   STATUS: ✅ PASSED")
            passed += 1
        except Exception as e:
            print(f"   STATUS: ❌ FAILED ({e})")
            failed += 1

    print(f"\n==========================================")
    print(f"📊 Multi-Agent Eval Summary: Total={len(test_cases)} | Passed={passed} | Failed={failed}")
    print(f"==========================================")

    if failed > 0:
        sys.exit(1)

if __name__ == "__main__":
    run_evaluations()
