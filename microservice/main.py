import os
import logging
from typing import List, Optional
from fastapi import FastAPI, HTTPException, Path, Body
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from firestore_service import firestore_service

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger("shopping_user_service")

app = FastAPI(
    title="Shopping User Service API",
    description="Enterprise microservice hosting Firestore user profile, long-term memory, and preferences for the ShoppingAssistant/FeedbackAgent OpenAPI toolsets.",
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

class UpdatePreferencesRequest(BaseModel):
    preferred_categories: Optional[List[str]] = Field(None, description="Product categories the user favors (e.g. shoes, apparel, equipment)")
    preferred_sports: Optional[List[str]] = Field(None, description="Sports/activities the user is interested in")
    preferred_brands: Optional[List[str]] = Field(None, description="Brands the user favors")
    shoe_size: Optional[str] = Field(None, description="Preferred shoe size")
    apparel_size: Optional[str] = Field(None, description="Preferred apparel size")
    equipment_size: Optional[str] = Field(None, description="Preferred equipment size (e.g. racket grip)")
    price_max: Optional[float] = Field(None, description="Approximate budget ceiling the user is comfortable with")


@app.get("/health", tags=["Health"])
def health_check():
    """Health check endpoint for Cloud Run container probes."""
    return {"status": "ok", "service": "shopping-user-service", "firestore": firestore_service.db is not None}


@app.get("/api/v1/users/{user_id}", tags=["User Profile"])
def get_user_profile(user_id: str = Path(..., description="Unique user identifier")):
    """
    Fetch user profile metadata, long-term memory facts, and preferences from Firestore.
    """
    profile = firestore_service.get_user_profile(user_id)
    return {
        "status": "success",
        "user_id": profile.get("user_id", user_id),
        "user_name": profile.get("user_name") or profile.get("name", "Shopper"),
        "membership_tier": profile.get("membership_tier", "none"),
        "memories": profile.get("memories", []),
        "preferences": profile.get("preferences", {})
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


@app.post("/api/v1/users/{user_id}/preferences", tags=["Preferences"])
def update_user_preferences(
    user_id: str = Path(..., description="Unique user identifier"),
    payload: UpdatePreferencesRequest = Body(...)
):
    """
    Merge partial preference updates (categories, sports, brands, sizes, budget)
    into the user's profile in Firestore. List fields are unioned with existing
    values; scalar fields overwrite. Returns the full merged preferences object.
    """
    updates = payload.model_dump(exclude_none=True)
    preferences = firestore_service.update_user_preferences(user_id, updates)
    return {"status": "success", "user_id": user_id, "preferences": preferences}


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8080))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=True)
