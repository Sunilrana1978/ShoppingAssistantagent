import os
from typing import Any, Optional

Tool = Any
CallbackContext = Any

try:
    from services.cart_service import cart_service
except ImportError:
    cart_service = None

try:
    from google.cloud.aiplatform_v1beta1 import MemoryBankServiceClient  # type: ignore
    _MEMORY_BANK_AVAILABLE = True
except ImportError:
    try:
        from google.cloud.aiplatform.memory import MemoryBankServiceClient  # type: ignore
        _MEMORY_BANK_AVAILABLE = True
    except ImportError:
        _MEMORY_BANK_AVAILABLE = False

DEFAULT_REASONING_ENGINE_ID = "432575911913586688"


def _save_live_memory(user_id: str, fact_text: str, project_id: str = "ecom-cx-agent", location: str = "us-central1") -> None:
    """Save a long-term fact to live Vertex AI Memory Bank if available."""
    if not _MEMORY_BANK_AVAILABLE or not user_id or user_id.lower() in ("guest", "u_guest"):
        return
    try:
        endpoint = f"{location}-aiplatform.googleapis.com"
        client = MemoryBankServiceClient(client_options={"api_endpoint": endpoint})
        engine_id = os.getenv("REASONING_ENGINE_ID", DEFAULT_REASONING_ENGINE_ID)
        parent = f"projects/{project_id}/locations/{location}/reasoningEngines/{engine_id}"
        
        memory_payload = {
            "fact": fact_text,
            "scope": {"user_id": user_id}
        }
        client.create_memory(parent=parent, memory=memory_payload)
    except Exception:
        pass


def get_session_id(callback_context: Any) -> str:
    """Helper to extract active session ID from Agent Engine callback context."""
    if not callback_context:
        return ""
    if hasattr(callback_context, "session_id") and getattr(callback_context, "session_id"):
        return str(getattr(callback_context, "session_id"))
    if hasattr(callback_context, "session"):
        session = getattr(callback_context, "session")
        if hasattr(session, "id") and getattr(session, "id"):
            return str(getattr(session, "id"))
        if hasattr(session, "session_id") and getattr(session, "session_id"):
            return str(getattr(session, "session_id"))
        if isinstance(session, dict):
            return str(session.get("id") or session.get("session_id") or "")
    if isinstance(callback_context, dict):
        return str(callback_context.get("session_id") or callback_context.get("state", {}).get("session_id") or "")
    return ""


def get_state(callback_context: Any) -> dict:
    """Helper to retrieve state dict following CXAS Scrapi Design Guide standards."""
    if not callback_context:
        return {}
    if isinstance(callback_context, dict):
        if "state" in callback_context and callback_context["state"] is not None:
            return callback_context["state"]
        if "variables" in callback_context and callback_context["variables"] is not None:
            return callback_context["variables"]
        return callback_context

    if hasattr(callback_context, "state") and getattr(callback_context, "state") is not None:
        return getattr(callback_context, "state")
    if hasattr(callback_context, "variables") and getattr(callback_context, "variables") is not None:
        return getattr(callback_context, "variables")
    if hasattr(callback_context, "session"):
        session = getattr(callback_context, "session")
        if hasattr(session, "state") and getattr(session, "state") is not None:
            return getattr(session, "state")
        if hasattr(session, "variables") and getattr(session, "variables") is not None:
            return getattr(session, "variables")
        if hasattr(session, "parameters") and getattr(session, "parameters") is not None:
            return getattr(session, "parameters")
    return {}


def set_state_var(callback_context: Any, key: str, value: Any) -> None:
    """Helper to write state variable across all Python object/dict types in CXAS Agent Engine."""
    if not callback_context:
        return

    def _set_on_target(target: Any):
        if target is None:
            return
        if isinstance(target, dict):
            target[key] = value
            return
        try:
            target[key] = value
        except Exception:
            pass
        try:
            setattr(target, key, value)
        except Exception:
            pass
        for method in ("set_variable", "set_session_variable", "set_parameter", "update_variable", "add_variable"):
            if hasattr(target, method):
                try:
                    getattr(target, method)(key, value)
                except Exception:
                    pass

    _set_on_target(callback_context)

    state = get_state(callback_context)
    if state is not None and state is not callback_context:
        _set_on_target(state)

    for attr in ("state", "variables", "session_variables", "parameters"):
        if hasattr(callback_context, attr):
            _set_on_target(getattr(callback_context, attr))

    if hasattr(callback_context, "session"):
        session = getattr(callback_context, "session")
        _set_on_target(session)
        for attr in ("state", "variables", "session_variables", "parameters"):
            if hasattr(session, attr):
                _set_on_target(getattr(session, attr))


def after_tool_callback(
    tool: Tool,
    input: dict[str, Any],
    callback_context: CallbackContext,
    tool_response: dict[str, Any],
) -> Optional[dict[str, Any]]:
    """
    Executes after a tool call finishes to update session variables,
    recompute cart pricing, and commit state back to Agent Engine.
    """
    if tool_response is None and callback_context is not None:
        tool_name = str(tool)
        tool_output = input if isinstance(input, dict) else {}
        context_obj = callback_context
    else:
        tool_name = getattr(tool, "name", str(tool)) if tool else ""
        tool_output = tool_response if isinstance(tool_response, dict) else (input if isinstance(input, dict) else {})
        context_obj = callback_context if callback_context is not None else input

    state = get_state(context_obj)
    sid = get_session_id(context_obj) or state.get("session_id") or "sess_default"
    user_id = tool_output.get("user_id") or state.get("user_id", "")
    discount_pct = float(state.get("discount_pct") or (tool_output.get("cart", {}).get("discount_pct") if isinstance(tool_output.get("cart"), dict) else 0) or 0)

    if tool_name in ("add_to_cart", "remove_from_cart", "get_cart"):
        cart = tool_output.get("cart") or state.get("cart")
        if cart and isinstance(cart, dict):
            subtotal = float(cart.get("subtotal", 0.0))
            disc_amt = round(subtotal * (discount_pct / 100.0), 2)
            cart.update({
                "discount_pct": discount_pct,
                "discount_amount": disc_amt,
                "total": round(subtotal - disc_amt, 2),
            })
            set_state_var(context_obj, "cart", cart)
            tool_output["cart"] = cart
            tool_output["updatedVariables"] = {"cart": cart}
            tool_output["updated_variables"] = {"cart": cart}
            tool_output["variables"] = {"cart": cart}
            tool_output["x-ces-session-context"] = {
                "variables": {
                    "cart": cart
                }
            }

            # Save live memory fact to Vertex AI Memory Bank
            if user_id and tool_name == "add_to_cart" and cart.get("items"):
                item_summaries = [f"{i.get('name')} (size {i.get('size')})" for i in cart["items"]]
                fact = f"User added {', '.join(item_summaries)} to cart for ${cart.get('total')}."
                _save_live_memory(user_id, fact)

    elif tool_name == "get_discount":
        if "discount_pct" in tool_output:
            new_pct = tool_output["discount_pct"]
            set_state_var(context_obj, "discount_pct", new_pct)
            if cart_service:
                updated_cart = cart_service.update_cart_pricing(sid, new_pct)
                set_state_var(context_obj, "cart", updated_cart)
            elif state.get("cart"):
                cart = dict(state["cart"])
                subtotal = float(cart.get("subtotal", 0.0))
                disc_amt = round(subtotal * (new_pct / 100.0), 2)
                cart.update({
                    "discount_pct": new_pct,
                    "discount_amount": disc_amt,
                    "total": round(subtotal - disc_amt, 2),
                })
                set_state_var(context_obj, "cart", cart)

    elif tool_name == "get_user_profile":
        uid = tool_output.get("user_id") or user_id
        name = tool_output.get("user_name") or tool_output.get("name") or "Shopper"
        tier = tool_output.get("membership_tier", "none")
        if uid:
            set_state_var(context_obj, "user_id", uid)
        set_state_var(context_obj, "user_name", name)
        set_state_var(context_obj, "membership_tier", tier)

        # Restore long term memories for newly resolved user_id
        if uid and uid.lower() not in ("guest", "u_guest"):
            memories = tool_output.get("memories", [])
            prev_cart = tool_output.get("previous_cart", {})
            if prev_cart and prev_cart.get("items"):
                prev_items = [f"{i.get('name')} (size {i.get('size')}, qty {i.get('qty')})" for i in prev_cart["items"]]
                fact = f"User previously had items in cart in past chat: {', '.join(prev_items)} with Total ${prev_cart.get('total')}."
                if fact not in memories:
                    memories.append(fact)
            set_state_var(context_obj, "long_term_memories", memories)

    elif tool_name == "search_catalog":
        if "products" in tool_output:
            set_state_var(context_obj, "search_results", tool_output["products"])

    elif tool_name == "submit_feedback":
        if tool_output.get("status") == "success":
            set_state_var(context_obj, "feedback_submitted", True)
            set_state_var(context_obj, "last_feedback_id", tool_output.get("feedback_id"))
            if user_id:
                _save_live_memory(user_id, f"User submitted rating {tool_output.get('rating')} star feedback.")

    return tool_output
