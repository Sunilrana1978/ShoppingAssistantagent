from typing import Any, Optional, Dict, List


def get_state(callback_context: Any) -> dict:
    """Helper to retrieve state dict following CXAS Scrapi Design Guide standards."""
    if hasattr(callback_context, "state") and isinstance(getattr(callback_context, "state"), dict):
        return callback_context.state
    if hasattr(callback_context, "variables") and isinstance(getattr(callback_context, "variables"), dict):
        return callback_context.variables
    if isinstance(callback_context, dict):
        if "state" in callback_context and isinstance(callback_context["state"], dict):
            return callback_context["state"]
        if "variables" in callback_context and isinstance(callback_context["variables"], dict):
            return callback_context["variables"]
        return callback_context
    return {}


def after_model_callback(
    callback_context: Any,
    llm_response: Any,
) -> Optional[Any]:
    """
    Executes after the LLM responds to attach rich UI widget payloads
    (product cards, etc.) to the model response.
    """
    try:
        state = get_state(callback_context)
        discount_pct = float(state.get("discount_pct", 0))
        search_results = state.get("search_results", [])

        if not search_results:
            return None

        custom_payloads: List[Dict[str, Any]] = []

        for prod in search_results[:3]:
            orig_price = float(prod.get("price", 0.0))
            disc_price = round(orig_price * (1.0 - discount_pct / 100.0), 2)
            subtitle = f"${orig_price:.2f} → ${disc_price:.2f}"
            if discount_pct > 0:
                tier = str(state.get("membership_tier", "")).capitalize()
                subtitle += f" ({tier} {discount_pct:.0f}% off)"

            custom_payloads.append({
                "type": "info_card",
                "title": prod.get("name"),
                "subtitle": subtitle,
                "image_url": prod.get("image_url"),
                "badge": f"{discount_pct:.0f}% OFF" if discount_pct > 0 else None,
                "attributes": {
                    "Brand": prod.get("brand"),
                    "Category": prod.get("category", "").capitalize(),
                    "Sizes": ", ".join(map(str, prod.get("sizes", []))),
                },
                "actions": [
                    {
                        "label": "Add to Cart",
                        "action_type": "postback",
                        "payload": f"Add {prod.get('sku')} to cart",
                    }
                ],
            })

        if not custom_payloads:
            return None

        if hasattr(llm_response, "custom_payload"):
            llm_response.custom_payload = custom_payloads
        elif isinstance(llm_response, dict):
            llm_response["rich_widgets"] = custom_payloads

    except Exception:
        pass

    return None
