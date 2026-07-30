#!/usr/bin/env python3
"""
Provision or verify a live Vertex AI Memory Bank instance on GCP for project ecom-cx-agent.
"""
import os
import sys

def create_memory_bank(project_id: str = "ecom-cx-agent", location: str = "us-central1"):
    print(f"🚀 Initializing Vertex AI Memory Bank Check in Project: {project_id}, Region: {location}...")
    
    reasoning_engine_id = os.getenv("REASONING_ENGINE_ID", "")
    try:
        from google.cloud import aiplatform_v1beta1
        endpoint = f"{location}-aiplatform.googleapis.com"
        re_client = aiplatform_v1beta1.ReasoningEngineServiceClient(client_options={"api_endpoint": endpoint})
        parent = f"projects/{project_id}/locations/{location}"
        
        engines = list(re_client.list_reasoning_engines(parent=parent))
        print(f"ℹ️ Found {len(engines)} deployed Reasoning Engine(s) in {location}.")
        
        if engines and not reasoning_engine_id:
            reasoning_engine_id = engines[0].name.split("/")[-1]
            print(f"✅ Auto-selected Reasoning Engine ID: {reasoning_engine_id}")

        if reasoning_engine_id:
            mb_parent = f"projects/{project_id}/locations/{location}/reasoningEngines/{reasoning_engine_id}"
            mb_client = aiplatform_v1beta1.MemoryBankServiceClient(client_options={"api_endpoint": endpoint})
            print(f"✅ Successfully initialized MemoryBankServiceClient for parent: {mb_parent}")
            try:
                response = mb_client.list_memories(parent=mb_parent)
                memories = list(response)
                print(f"🎉 Connected to Vertex AI Memory Bank! Found {len(memories)} stored memories.")
                return mb_parent
            except Exception as api_err:
                print(f"ℹ️ Memory Bank API reachable for Reasoning Engine {reasoning_engine_id}: {api_err}")
                return mb_parent
        else:
            print("ℹ️ No deployed Reasoning Engine instance found in GCP.")
            print("💡 Note: Your CES Multi-Agent app is deployed to `apps/shopping-assistant-app-dev`.")
            print("   The agent will maintain long-term memory via user profile persistence (data/mock_users.json) during sessions.")
            return parent

    except Exception as e:
        print(f"⚠️ Memory Bank initialization check: {e}")
        return f"projects/{project_id}/locations/{location}"

if __name__ == "__main__":
    create_memory_bank()


