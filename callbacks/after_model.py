from typing import Optional, Any, Dict, List

from google.adk.agents.callback_context import CallbackContext
from google.genai import types


def after_model_callback(
    callback_context: CallbackContext,
    llm_response: Any,
) -> Optional[Any]:
    """
    Executes after the LLM responds to attach rich UI widget payloads
    (product cards, etc.) to the model response.

    ADK signature:
        callback_context — CallbackContext; use callback_context.variables for session vars
        llm_response     — the LlmResponse object returned by the model

    Returns:
        None            → the original llm_response is used as-is.
        LlmResponse     → this response replaces the model's output.
    """
    try:
        session_vars = callback_context.variables
        discount_pct = float(session_vars.get("discount_pct", 0))
        search_results = session_vars.get("search_results", [])

        if not search_results:
            return None

        custom_payloads: List[Dict[str, Any]] = []

        for prod in search_results[:3]:
            orig_price = float(prod.get("price", 0.0))
            disc_price = round(orig_price * (1.0 - discount_pct / 100.0), 2)
            subtitle = f"${orig_price:.2f} → ${disc_price:.2f}"
            if discount_pct > 0:
                tier = str(session_vars.get("membership_tier", "")).capitalize()
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

        # Attach rich widget payloads to the model response
        if hasattr(llm_response, "custom_payload"):
            llm_response.custom_payload = custom_payloads
        elif isinstance(llm_response, dict):
            llm_response["rich_widgets"] = custom_payloads

    except Exception:
        # Never block the response — return None to use llm_response as-is
        pass

    return None
