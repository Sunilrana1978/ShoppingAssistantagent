import json
import sys
from pathlib import Path

# Add project root to sys.path
root = Path(__file__).parent.parent
sys.path.insert(0, str(root))

from services.user_service import user_service
from services.discount_service import discount_service
from services.catalog_service import catalog_service
from services.cart_service import cart_service
from services.feedback_service import feedback_service
from callbacks.before_agent import before_agent_callback
from callbacks.after_tool import after_tool_callback
from callbacks.after_model import after_model_callback
from tools import search_catalog, add_to_cart, get_cart, submit_feedback

class MockCallbackContext:
    def __init__(self, variables=None):
        self.variables = variables if variables is not None else {}

def simulate_full_customer_journey():
    print("==========================================================")
    print("🛍️  SPORTING GOODS MULTI-AGENT INTERACTIVE DEMO SESSION")
    print("==========================================================\n")

    # Step 1: Session Init with user_id = u_1029 (Alex - Gold Member)
    ctx = MockCallbackContext(variables={"user_id": "u_1029", "session_id": "sess_demo_8899"})
    before_agent_callback(ctx)
    user_id = ctx.variables["user_id"]

    print("🤖 [RootAgent]: Welcome to Sporting Goods! Fetching customer profile...")
    profile = user_service.get_user_profile(user_id)
    after_tool_callback(tool=None, input={}, callback_context=ctx, tool_response=profile)

    discount_pct = discount_service.get_discount_percentage(profile["membership_tier"])
    after_tool_callback(tool=None, input={}, callback_context=ctx, tool_response={"discount_pct": discount_pct})

    vars_dict = ctx.variables
    print(f"👤 Connected User: {vars_dict['user_name']} | Tier: {vars_dict['membership_tier'].capitalize()} | Active Discount: {vars_dict.get('discount_pct', 0)}%\n")

    # Step 2: Customer Request 1 - Search Catalog
    print("💬 Customer: 'I need trail running shoes in size 10'")
    print("🤖 [ShoppingAssistant]: Searching catalog for trail running shoes...")
    search_res = search_catalog(query="trail running", category="shoes", size="10")
    after_tool_callback(tool="search_catalog", input={}, callback_context=ctx, tool_response=search_res)

    model_res = {"text": f"Hi {vars_dict['user_name']}! As a Gold member, you get 15% off today! Here are top trail running shoes:"}
    after_model_callback(callback_context=ctx, llm_response=model_res)

    print(f"   Response Text: \"{model_res['text']}\"")
    if "rich_widgets" in model_res:
        for w in model_res["rich_widgets"]:
            print(f"   🎴 Info Card Widget: [{w['title']}] - {w['subtitle']}")
    print()

    # Step 3: Customer Request 2 - Add to Cart
    print("💬 Customer: 'Add size 10 to my cart'")
    print("🤖 [ShoppingAssistant]: Adding TrailBlaze Pro Trail Runner (SKU: sku_1029, Size 10) to cart...")
    add_res = add_to_cart(session_id=vars_dict["session_id"], sku="sku_1029", qty=1, size="10")
    after_tool_callback(tool="add_to_cart", input={}, callback_context=ctx, tool_response=add_res)

    cart = vars_dict.get("cart", {})
    print("🛒 [Cart Update Server-Side Pricing Calculation]:")
    print(f"   - Items: {len(cart.get('items', []))} line item ({cart.get('items', [{}])[0].get('name', 'Product')}, Size {cart.get('items', [{}])[0].get('size', '10')})")
    print(f"   - Subtotal:        ${cart.get('subtotal', 0.0):.2f}")
    print(f"   - Gold 15% Off:   -${cart.get('discount_amount', 0.0):.2f}")
    print(f"   - Grand Total:     ${cart.get('total', 0.0):.2f}\n")

    # Step 4: Customer Request 3 - Submit Feedback
    print("💬 Customer: 'I'd like to leave feedback: 5 stars, amazing recommendation and discount!'")
    print("🤖 [FeedbackAgent]: Collecting customer feedback and rating...")
    fb_res = submit_feedback(user_id=user_id, rating=5, comments="amazing recommendation and discount!")
    after_tool_callback(tool="submit_feedback", input={}, callback_context=ctx, tool_response=fb_res)

    print(f"   STATUS: {fb_res['status'].upper()} | Feedback ID: {fb_res['feedback_id']} | Rating: {fb_res['rating']} ⭐")
    print(f"   Message: \"{fb_res['message']}\"\n")

    print("==========================================================")
    print("🎉 DEMO SESSION COMPLETED SUCCESSFULLY!")
    print("==========================================================")

if __name__ == "__main__":
    simulate_full_customer_journey()
