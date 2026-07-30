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
    test_cases_file = root / "evals" / "test_cases.json"
    with open(test_cases_file, "r") as f:
        test_cases = json.load(f)

    print("🧪 Running Multi-Agent Automated Simulation Evaluations & Scenarios...")
    passed = 0
    failed = 0

    for tc in test_cases:
        tc_id = tc["id"]
        desc = tc["description"]
        user_id = tc["user_id"]
        target_agent = tc.get("agent", "ShoppingAssistant")
        print(f"\n▶ Executing [{tc_id}] (Target Agent: {target_agent}): {desc}")

        context = {"state": {"user_id": user_id, "session_id": f"sess_{tc_id}"}}

        try:
            # 1. Initialize User Profile and Discount if present in user database
            profile = user_service.get_user_profile(user_id)
            if profile:
                after_tool_callback("get_user_profile", profile, context)
                discount = discount_service.get_discount_percentage(profile.get("membership_tier", "none"))
                after_tool_callback("get_discount", {"discount_pct": discount}, context)
                state = context["state"]
                print(
                    f"   Profile: Name='{state.get('user_name')}', Tier='{state.get('membership_tier')}', Discount={state.get('discount_pct')}%"
                )

            # 2. Iterate through scenario turns
            for turn_idx, turn in enumerate(tc["turns"], 1):
                agent = turn.get("agent", target_agent)
                user_input = turn.get("user_input", "")
                print(f"   Turn {turn_idx} [{agent}]: User='{user_input}'")

                # Verify expected profile / greeting state assertions
                if "expected_user_name" in turn:
                    assert (
                        context["state"].get("user_name") == turn["expected_user_name"]
                    ), f"User name mismatch: got '{context['state'].get('user_name')}', expected '{turn['expected_user_name']}'"
                if "expected_membership_tier" in turn:
                    assert (
                        context["state"].get("membership_tier") == turn["expected_membership_tier"]
                    ), f"Tier mismatch: got '{context['state'].get('membership_tier')}', expected '{turn['expected_membership_tier']}'"
                if "expected_discount_pct" in turn:
                    assert (
                        context["state"].get("discount_pct") == turn["expected_discount_pct"]
                    ), f"Discount % mismatch: got {context['state'].get('discount_pct')}, expected {turn['expected_discount_pct']}"

                # Handle search_catalog
                if "expected_matched_sku" in turn:
                    sku = turn["expected_matched_sku"]
                    product = catalog_service.get_product(sku)
                    assert product is not None, f"Product SKU {sku} not found"
                    after_tool_callback("search_catalog", {"products": [product]}, context)

                # Handle cart item addition
                if "items_to_add" in turn:
                    for item in turn["items_to_add"]:
                        cart = cart_service.add_item(
                            session_id=context["state"]["session_id"],
                            sku=item["sku"],
                            qty=item.get("qty", 1),
                            size=item.get("size"),
                        )
                        after_tool_callback("add_to_cart", {"cart": cart}, context)

                # Handle cart item removal
                if "sku_to_remove" in turn:
                    cart = cart_service.remove_item(
                        session_id=context["state"]["session_id"], sku=turn["sku_to_remove"]
                    )
                    after_tool_callback("remove_from_cart", {"cart": cart}, context)

                # Verify cart arithmetic assertions
                if "expected_subtotal" in turn or "expected_cart_total" in turn:
                    final_cart = context["state"].get("cart", {})
                    print(
                        f"     Cart Arithmetic: Subtotal=${final_cart.get('subtotal')}, Discount=-${final_cart.get('discount_amount')}, Total=${final_cart.get('total')}"
                    )

                    if "expected_subtotal" in turn:
                        assert (
                            final_cart.get("subtotal") == turn["expected_subtotal"]
                        ), f"Subtotal mismatch: got {final_cart.get('subtotal')}, expected {turn['expected_subtotal']}"
                    if "expected_discount_amount" in turn:
                        assert (
                            final_cart.get("discount_amount") == turn["expected_discount_amount"]
                        ), f"Discount amount mismatch: got {final_cart.get('discount_amount')}, expected {turn['expected_discount_amount']}"
                    if "expected_cart_total" in turn:
                        assert (
                            final_cart.get("total") == turn["expected_cart_total"]
                        ), f"Cart total mismatch: got {final_cart.get('total')}, expected {turn['expected_cart_total']}"

                # Handle feedback submission
                if "rating" in turn:
                    res = feedback_service.submit_feedback(user_id, turn["rating"], turn.get("comments", ""))
                    after_tool_callback("submit_feedback", res, context)
                    assert context["state"].get("feedback_submitted") is True
                    print(f"     Feedback: ID={res['feedback_id']}, Rating={res['rating']} stars, Status=Submitted")

            print(f"   STATUS: ✅ PASSED")
            passed += 1
        except Exception as e:
            print(f"   STATUS: ❌ FAILED ({e})")
            failed += 1

    print(f"\n==========================================")
    print(f"📊 Multi-Agent Scenario Eval Summary: Total={len(test_cases)} | Passed={passed} | Failed={failed}")
    print(f"==========================================")

    if failed > 0:
        sys.exit(1)


if __name__ == "__main__":
    run_evaluations()
