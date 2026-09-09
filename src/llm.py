import requests
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)

class OllamaLLM:
    """Client for local Ollama LLM inference."""

    def __init__(self, model_name: str = "llama3:latest", base_url: str = "http://localhost:11434"):
        self.model_name = model_name
        self.base_url = base_url.rstrip("/")

    def check_connection(self) -> Dict[str, Any]:
        """
        Check if Ollama service is reachable and if configured model is available.
        
        Returns:
            {"available": bool, "message": str, "installed_models": list}
        """
        try:
            resp = requests.get(f"{self.base_url}/api/tags", timeout=3)
            if resp.status_code == 200:
                data = resp.json()
                models = [m.get("name") for m in data.get("models", [])]
                
                # Check if exact model or model prefix exists (e.g. 'llama3:latest' or 'llama3')
                has_model = any(
                    self.model_name == m or self.model_name.split(":")[0] == m.split(":")[0] 
                    for m in models
                )
                
                if not has_model:
                    return {
                        "available": False,
                        "message": f"Ollama is running, but model '{self.model_name}' was not found. Installed models: {models}",
                        "installed_models": models
                    }

                return {
                    "available": True,
                    "message": f"Connected to Ollama. Model '{self.model_name}' ready.",
                    "installed_models": models
                }
            else:
                return {
                    "available": False,
                    "message": f"Ollama returned HTTP status {resp.status_code}.",
                    "installed_models": []
                }
        except requests.exceptions.RequestException as e:
            return {
                "available": False,
                "message": f"Could not connect to Ollama at '{self.base_url}'. Make sure 'ollama serve' is running.",
                "installed_models": []
            }

    def generate(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        """
        Generate text response from Ollama model.
        """
        conn_status = self.check_connection()
        if not conn_status["available"]:
            return (
                f"⚠️ **Local LLM Error**: {conn_status['message']}\n\n"
                f"Please ensure Ollama is running (`ollama serve`) and the model is pulled (`ollama pull {self.model_name}`)."
            )

        endpoint = f"{self.base_url}/api/generate"
        payload = {
            "model": self.model_name,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": 0.1,  # Low temperature for deterministic, factual grounded answers
                "top_p": 0.9
            }
        }

        if system_prompt:
            payload["system"] = system_prompt

        try:
            logger.info(f"Sending prompt to Ollama model '{self.model_name}'...")
            resp = requests.post(endpoint, json=payload, timeout=60)
            if resp.status_code == 200:
                result = resp.json()
                return result.get("response", "").strip()
            else:
                logger.error(f"Ollama generation failed: {resp.status_code} - {resp.text}")
                return f"⚠️ LLM API Error ({resp.status_code}): Could not generate response."
        except Exception as e:
            logger.error(f"Ollama request error: {str(e)}")
            return f"⚠️ Connection Error while communicating with Ollama: {str(e)}"
