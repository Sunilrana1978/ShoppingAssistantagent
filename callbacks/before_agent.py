from typing import Dict, Any

def before_agent_callback(context: Dict[str, Any]) -> Dict[str, Any]:
    """
    Hook executed before the agent invocation.
    Extracts user_id from channel payload, preserves pre-existing state user_id, or defaults to guest.
    """
    if "state" not in context:
        context["state"] = {}

    channel_payload = context.get("channel_payload", {})
    if isinstance(channel_payload, str):
        try:
            import json
            channel_payload = json.loads(channel_payload)
        except Exception:
            channel_payload = {}
            
    if not isinstance(channel_payload, dict):
        channel_payload = {}

    user_id = channel_payload.get("user_id")
    
    if not user_id:
        user_id = context["state"].get("user_id")
        
    if not user_id:
        user_id = "guest"
        
    if isinstance(user_id, str):
        user_id = user_id.strip('"').strip("'").strip()
        
    context["state"]["user_id"] = user_id
    if "session_id" not in context["state"]:
        context["state"]["session_id"] = context.get("session_id", "sess_default")

    return context
