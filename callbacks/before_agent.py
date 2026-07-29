import re
from typing import Any

try:
    from services.user_service import user_service
except ImportError:
    user_service = None


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _safe_read(obj: Any, key: str) -> Any:
    """
    Reads *key* from any dict-like or attribute-bearing object without
    raising. Tries .get(), then direct subscript, then getattr.
    """
    if obj is None:
        return None
    try:
        if hasattr(obj, "get"):
            val = obj.get(key)
            if val:
                return val
    except Exception:
        pass
    try:
        val = obj[key]
        if val:
            return val
    except Exception:
        pass
    try:
        val = getattr(obj, key, None)
        if val:
            return val
    except Exception:
        pass
    return None


def _safe_write(obj: Any, key: str, value: Any) -> bool:
    """
    Writes *key*=*value* to any dict-like or attribute-bearing object
    without raising. Returns True on success.
    """
    if obj is None:
        return False
    # Try subscript assignment first (covers dict, ADK State, Pydantic models…)
    try:
        obj[key] = value
        return True
    except Exception:
        pass
    # Try attribute assignment
    try:
        setattr(obj, key, value)
        return True
    except Exception:
        pass
    return False


# ---------------------------------------------------------------------------
# Extraction
# ---------------------------------------------------------------------------

def extract_user_id_from_context(context: Any) -> Any:
    """
    Extracts user_id from callback_context using a layered approach.

    Strategy order:
    1.  context.get_variable("user_id")          — CXAS SDK helper
    2.  context.state["user_id"]                 — ADK State / plain dict
                                                   (NO isinstance guard — ADK
                                                    State is NOT a plain dict)
    3.  context.session.params["user_id"]        — Dialogflow CX / CXAS style
    4.  context.variables["user_id"]             — generic variables bag
    5.  Regex on str(context)                    — last-resort string scan
    6.  model_dump() deep search                 — Pydantic model fallback
    """
    if context is None:
        return None

    # 1. Direct variable getter (CXAS SDK)
    if hasattr(context, "get_variable"):
        try:
            val = context.get_variable("user_id")
            if val:
                return val
        except Exception:
            pass

    # 2. State object — intentionally no isinstance(state, dict) check.
    #    In CXAS/ADK the state is an ADK State object, not a plain dict,
    #    so isinstance would silently skip this and miss the variable.
    if hasattr(context, "state") and context.state is not None:
        val = _safe_read(context.state, "user_id")
        if val:
            return val

    # 3. session.params — Dialogflow CX / CXAS canonical location
    if hasattr(context, "session") and context.session is not None:
        if hasattr(context.session, "params") and context.session.params is not None:
            val = _safe_read(context.session.params, "user_id")
            if val:
                return val

    # 4. Direct variables dict
    if hasattr(context, "variables") and context.variables is not None:
        val = _safe_read(context.variables, "user_id")
        if val:
            return val

    # 5. Regex scan on string representation of the context object
    try:
        ctx_str = str(context)
        match = re.search(r'["\']user_id["\']\s*:\s*["\']([^"\']+)["\']', ctx_str)
        if match:
            return match.group(1)
    except Exception:
        pass

    # 6. model_dump() deep search (Pydantic models)
    if hasattr(context, "model_dump"):
        try:
            raw_data = context.model_dump(by_alias=True)

            def deep_search(data: Any, key: str, depth: int = 5) -> Any:
                if depth <= 0 or not data:
                    return None
                if isinstance(data, dict):
                    if key in data and data[key]:
                        return data[key]
                    for v in data.values():
                        res = deep_search(v, key, depth - 1)
                        if res:
                            return res
                elif isinstance(data, list):
                    for item in data:
                        res = deep_search(item, key, depth - 1)
                        if res:
                            return res
                return None

            val = deep_search(raw_data, "user_id")
            if val:
                return val
        except Exception:
            pass

    return None


# ---------------------------------------------------------------------------
# Write-back
# ---------------------------------------------------------------------------

def _write_profile_to_context(context: Any, user_id: str, name: str, tier: str) -> None:
    """
    Writes user_id, user_name, and membership_tier to every known state
    bucket in the CXAS/ADK callback context so that {user_name} in the
    instruction template is reliably resolved.

    ⚠️  IMPORTANT: context.set_variable() is intentionally NOT used here.
        In CXAS, calling set_variable() emits a "set variable response" signal
        that the platform interprets as the agent's final response, which
        bypasses the LLM entirely. Only state/params writes are safe.

    Paths attempted (in order):
    1.  context.state[key]          — ADK State / dict (no isinstance guard)
    2.  context.session.params[key] — Dialogflow CX / CXAS canonical path
    3.  context.variables[key]      — generic variables bag
    4.  context["state"][key]       — context itself is a plain dict
    All failures are silently swallowed so the callback always returns None.
    """
    fields = {
        "user_id": user_id,
        "user_name": name,
        "membership_tier": tier,
    }

    # 1. ADK State / plain dict — intentionally no isinstance guard.
    #    In CXAS/ADK, context.state is a State object (not a plain dict)
    #    that supports item assignment and tracks changes for the runtime.
    if hasattr(context, "state") and context.state is not None:
        for k, v in fields.items():
            _safe_write(context.state, k, v)

    # 2. session.params — Dialogflow CX / CXAS canonical write path
    if hasattr(context, "session") and context.session is not None:
        if hasattr(context.session, "params") and context.session.params is not None:
            for k, v in fields.items():
                _safe_write(context.session.params, k, v)

    # 3. variables bag
    if hasattr(context, "variables") and context.variables is not None:
        for k, v in fields.items():
            _safe_write(context.variables, k, v)

    # 4. context itself is a plain dict (e.g. unit-test stub)
    if isinstance(context, dict):
        context.setdefault("state", {})
        for k, v in fields.items():
            context["state"][k] = v


# ---------------------------------------------------------------------------
# Callback entry-point
# ---------------------------------------------------------------------------

def before_agent_callback(callback_context: Any) -> Any:
    """
    Hook executed before agent invocation.

    Extracts user_id from the context payload, queries the user profile
    (via user_service or the built-in mock), and writes user_id, user_name,
    and membership_tier into every available state bucket so that the
    instruction template placeholders {user_id}, {user_name}, and
    {membership_tier} are resolved before the LLM call.

    Must return None to satisfy the CXAS _CallbackResult Optional[Content]
    contract.

    ⚠️  The entire body is wrapped in try/except to guarantee None is always
        returned. Any unhandled exception would propagate as a non-None value
        in some CXAS sandbox versions, causing the LLM call to be skipped.
    """
    try:
        context = callback_context

        user_id = extract_user_id_from_context(context)

        if isinstance(user_id, str):
            user_id = user_id.strip('"').strip("'").strip()

        if not user_id or user_id.lower() == "guest":
            return None

        # Fetch user profile
        if user_service:
            profile = user_service.get_user_profile(user_id)
        else:
            mock_users = {
                "u_1029": {"name": "Alex",   "membership_tier": "gold"},
                "u_1030": {"name": "Jordan", "membership_tier": "silver"},
                "u_1031": {"name": "Taylor", "membership_tier": "bronze"},
            }
            profile = mock_users.get(
                user_id,
                {"name": user_id.capitalize(), "membership_tier": "none"},
            )

        name = profile.get("user_name") or profile.get("name", "Shopper")
        tier = profile.get("membership_tier", "none")

        _write_profile_to_context(context, user_id, name, tier)

    except Exception:
        # Swallow all errors — the agent must always proceed to the LLM call
        pass

    # MUST return None — satisfies CXAS _CallbackResult Optional[Content] contract
    return None

