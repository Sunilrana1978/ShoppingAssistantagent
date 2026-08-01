import os
import json
import logging
from typing import Dict, Any, List, Optional
from fastapi import FastAPI, HTTPException, Request, Path, Body
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from firestore_service import firestore_service

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger("shopping_user_service")

app = FastAPI(
    title="Shopping User Service & CXAS Webhook API",
    description="Enterprise microservice hosting Firestore user profile, long-term memory, and CX Agent Studio webhooks.",
    version="1.0.0",
)

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Pydantic Schemas
class AddMemoryRequest(BaseModel):
    fact: str = Field(..., description="Memory fact string to store in Firestore")

class SaveCartRequest(BaseModel):
    cart: Dict[str, Any] = Field(..., description="Cart snapshot dict")

class WebhookRequest(BaseModel):
    session_id: Optional[str] = None
    user_id: Optional[str] = None
    state: Optional[Dict[str, Any]] = None
    variables: Optional[Dict[str, Any]] = None
    tool_name: Optional[str] = None
    tool_response: Optional[Dict[str, Any]] = None


@app.get("/health", tags=["Health"])
def health_check():
    """Health check endpoint for Cloud Run container probes."""
    return {"status": "ok", "service": "shopping-user-service", "firestore": firestore_service.db is not None}


@app.get("/api/v1/users/{user_id}", tags=["User Profile"])
def get_user_profile(user_id: str = Path(..., description="Unique user identifier")):
    """
    Fetch user profile metadata, long-term memory facts, and previous cart snapshot from Firestore.
    """
    profile = firestore_service.get_user_profile(user_id)
    return {
        "status": "success",
        "user_id": profile.get("user_id", user_id),
        "user_name": profile.get("user_name") or profile.get("name", "Shopper"),
        "membership_tier": profile.get("membership_tier", "none"),
        "memories": profile.get("memories", []),
        "previous_cart": profile.get("previous_cart", {})
    }


@app.post("/api/v1/users/{user_id}/memories", tags=["Memories"])
def add_user_memory(
    user_id: str = Path(..., description="Unique user identifier"),
    payload: AddMemoryRequest = Body(...)
):
    """
    Add a long-term memory fact to the user's profile in Firestore.
    """
    success = firestore_service.add_user_memory(user_id, payload.fact)
    if not success:
        raise HTTPException(status_code=400, detail="Failed to add memory fact")
    return {"status": "success", "user_id": user_id, "fact": payload.fact}


@app.post("/api/v1/users/{user_id}/cart", tags=["Cart"])
def save_user_cart(
    user_id: str = Path(..., description="Unique user identifier"),
    payload: SaveCartRequest = Body(...)
):
    """
    Save a cross-session cart snapshot for the user in Firestore.
    """
    success = firestore_service.save_user_cart(user_id, payload.cart)
    if not success:
        raise HTTPException(status_code=400, detail="Failed to save cart snapshot")
    return {"status": "success", "user_id": user_id, "cart": payload.cart}


@app.post("/api/v1/webhooks/before-agent", tags=["CXAS Webhooks"])
async def before_agent_webhook(request: Request):
    """
    CX Agent Studio BeforeAgent Callback Webhook Handler.
    Populates user profile, membership tier, and long-term memory facts into CXAS session state.
    """
    try:
        body = await request.json()
        logger.info(f"BeforeAgent webhook payload received: {body}")

        # Extract user_id from various CXAS payload structures
        state = body.get("state") or body.get("variables") or body.get("session", {}).get("state", {})
        user_id = state.get("user_id") or body.get("user_id") or "guest"
        if isinstance(user_id, str):
            user_id = user_id.strip('"').strip("'").strip()

        profile = firestore_service.get_user_profile(user_id)
        name = profile.get("user_name") or profile.get("name", "Shopper")
        tier = profile.get("membership_tier", "none")
        memories = profile.get("memories", [])
        previous_cart = profile.get("previous_cart", {})

        # Include previous session cart in recalled memories if present
        if previous_cart and previous_cart.get("items"):
            prev_items = [f"{i.get('name')} (size {i.get('size')}, qty {i.get('qty')})" for i in previous_cart["items"]]
            cart_fact = f"User previously had items in cart in past chat: {', '.join(prev_items)} with Total ${previous_cart.get('total')}."
            if cart_fact not in memories:
                memories.append(cart_fact)

        updated_vars = {
            "user_id": user_id,
            "user_name": name,
            "membership_tier": tier,
            "long_term_memories": json.dumps(memories)
        }

        return {
            "status": "success",
            "updatedVariables": updated_vars,
            "updated_variables": updated_vars,
            "x-ces-session-context": {
                "variables": updated_vars
            }
        }
    except Exception as e:
        logger.error(f"BeforeAgent webhook error: {e}")
        return {"status": "error", "message": str(e)}


@app.post("/api/v1/webhooks/after-tool", tags=["CXAS Webhooks"])
async def after_tool_webhook(request: Request):
    """
    CX Agent Studio AfterTool Callback Webhook Handler.
    Persists live cart additions and interaction memory facts to Firestore.
    """
    try:
        body = await request.json()
        logger.info(f"AfterTool webhook payload received: {body}")

        tool_name = body.get("tool_name") or body.get("tool", "")
        tool_response = body.get("tool_response") or body.get("response", {})
        state = body.get("state") or body.get("variables") or body.get("session", {}).get("state", {})
        user_id = state.get("user_id") or body.get("user_id") or ""

        if isinstance(user_id, str):
            user_id = user_id.strip('"').strip("'").strip()

        # Handle cart snapshot persistence
        if tool_name in ("add_to_cart", "remove_from_cart", "get_cart") and user_id:
            cart = tool_response.get("cart") or state.get("cart")
            if cart and isinstance(cart, dict):
                firestore_service.save_user_cart(user_id, cart)
                if tool_name == "add_to_cart" and cart.get("items"):
                    item_summaries = [f"{i.get('name')} (size {i.get('size')})" for i in cart["items"]]
                    fact = f"User added {', '.join(item_summaries)} to cart for ${cart.get('total')}."
                    firestore_service.add_user_memory(user_id, fact)

        elif tool_name == "submit_feedback" and user_id:
            if tool_response.get("status") == "success":
                firestore_service.add_user_memory(user_id, f"User submitted rating {tool_response.get('rating')} star feedback.")

        return {
            "status": "success",
            "message": "AfterTool webhook processed successfully"
        }
    except Exception as e:
        logger.error(f"AfterTool webhook error: {e}")
        return {"status": "error", "message": str(e)}


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8080))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=True)
