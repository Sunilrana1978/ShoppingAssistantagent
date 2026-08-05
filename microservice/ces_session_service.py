import os
import logging
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

# Check if cxas-scrapi (which wraps the CES Sessions API) is installed
try:
    from cxas_scrapi.core.sessions import Sessions
    _SESSIONS_AVAILABLE = True
except ImportError:
    _SESSIONS_AVAILABLE = False


class CesSessionService:
    """Service layer proxying chat turns from the custom web UI to the deployed
    CXAS app via the CES Sessions API (google-cloud-ces, through cxas_scrapi's
    Sessions wrapper — the same mechanism scripts/smoke_test_routing.py uses).
    """

    def __init__(self, project_id: Optional[str] = None):
        self.project_id = project_id or os.getenv("GCP_PROJECT_ID", "ecom-cx-agent")
        self.location = os.getenv("CES_LOCATION", "us")
        self.app_id = os.getenv("CES_APP_ID", "shopping-assistant-app-dev")
        self.app_name = f"projects/{self.project_id}/locations/{self.location}/apps/{self.app_id}"
        self.sessions = None

        if _SESSIONS_AVAILABLE:
            try:
                self.sessions = Sessions(app_name=self.app_name)
                logger.info(f"CES Sessions client initialized for app: {self.app_name}")
            except Exception as e:
                logger.warning(f"CES Sessions client init error: {e}. Chat proxy will be unavailable.")
                self.sessions = None
        else:
            logger.warning("cxas_scrapi package not available. Chat proxy will be unavailable.")

    def send_message(self, session_id: str, text: str, user_id: Optional[str] = None) -> Dict[str, Any]:
        """Sends one chat turn to the deployed CXAS app and returns a plain dict:
        {text, widget, session_ended, agent_transfer}.
        """
        if not self.sessions:
            raise RuntimeError("CES Sessions client is not available")

        variables = {"user_id": user_id} if user_id else None
        response = self.sessions.run(session_id=session_id, text=text, variables=variables)
        structured = self.sessions.get_structured_response(response)

        return {
            "text": structured.get("agent_text", ""),
            "widget": structured.get("payload"),
            "session_ended": structured.get("session_ended", False),
            "agent_transfer": _agent_transfer_name(structured.get("agent_transfer")),
        }


def _agent_transfer_name(agent_transfer: Any) -> Optional[str]:
    """get_structured_response returns agent_transfer as a raw AgentTransfer
    protobuf message (not a plain string) when a transfer occurred."""
    if agent_transfer is None or isinstance(agent_transfer, str):
        return agent_transfer
    return getattr(agent_transfer, "display_name", None) or str(agent_transfer)


ces_session_service = CesSessionService()
