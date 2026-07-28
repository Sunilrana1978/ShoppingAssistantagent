from typing import Dict, Any, List

def after_model_callback(arg1: Any = None, arg2: Any = None, *args, **kwargs) -> Any:
    """
    Hook executed after the model responds to format and attach structured JSON widget payloads.
    Supports both (callback_context, model_response) and (model_response, callback_context) signatures.
    """
    if hasattr(arg1, "state") or hasattr(arg1, "variables"):
        context = arg1
        model_response = arg2 if isinstance(arg2, dict) else {}
    elif hasattr(arg2, "state") or hasattr(arg2, "variables"):
        model_response = arg1 if isinstance(arg1, dict) else {}
        context = arg2
    else:
        model_response = arg1 if isinstance(arg1, dict) else {}
        context = arg2

    if not isinstance(model_response, dict):
        model_response = {}

    if hasattr(context, "state") and context.state is not None:
        state = context.state
    elif isinstance(context, dict):
        state = context.get("state", {})
    else:
        state = {}

    if not isinstance(state, dict):
        state = {}

    discount_pct = float(state.get("discount_pct", 0))
    custom_payloads: List[Dict[str, Any]] = []

    # Check if search results exist and format product cards
    if "search_results" in state and state["search_results"]:
        for prod in state["search_results"][:3]:
            orig_price = float(prod.get("price", 0.0))
            disc_price = round(orig_price * (1.0 - discount_pct / 100.0), 2)
            subtitle = f"${orig_price:.2f} → ${disc_price:.2f}"
            if discount_pct > 0:
                subtitle += f" ({state.get('membership_tier', '').capitalize()} {discount_pct:.0f}% off)"

            custom_payloads.append({
                "type": "info_card",
                "title": prod.get("name"),
                "subtitle": subtitle,
                "image_url": prod.get("image_url"),
                "badge": f"{discount_pct:.0f}% OFF" if discount_pct > 0 else None,
                "attributes": {
                    "Brand": prod.get("brand"),
                    "Category": prod.get("category", "").capitalize(),
                    "Sizes": ", ".join(map(str, prod.get("sizes", [])))
                },
                "actions": [
                    {
                        "label": "Add to Cart",
                        "action_type": "postback",
                        "payload": f"Add {prod.get('sku')} to cart"
                    }
                ]
            })

    if custom_payloads:
        model_response["rich_widgets"] = custom_payloads

    return model_response
